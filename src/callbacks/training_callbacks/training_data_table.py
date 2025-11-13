from dash import callback, ctx, dcc, html, Input, Output, State, no_update, dash_table
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
import base64
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance

def register_training_data_table_callbacks(app):
    """
    Register training data table callbacks with export functionality
    Matches the component IDs from the layout file
    """
    
    @monitor_query_performance("Training Data Table Base Data")
    def get_training_data_table_base_data():
        """
        Fetch comprehensive base data for all report types
        Uses consumable fact tables optimized for reporting
        """
        
        queries = {
            # Member engagement data for member activity summary
            "member_engagement": """
                SELECT TOP 5000
                    [MemberID],
                    [MemberName],
                    [FirstName],
                    [LastName],
                    [OfficeCode],
                    [AorShortName],
                    [LoginId],
                    [MemberStatus],
                    [MemberType],
                    [ContactType],
                    [TotalSessionsRegistered],
                    [TotalSessionsAttended],
                    [MissedSessions],
                    [AttendanceRate],
                    [LastRegisteredOn],
                    [LastConfirmedOn]
                FROM [consumable].[Fact_MemberEngagement]
                WHERE [MemberID] IS NOT NULL
                ORDER BY [TotalSessionsAttended] DESC
            """,
            
            # Class attendance details
            "class_attendance": """
                SELECT TOP 5000
                    [AttendanceID],
                    [TrainingClassId],
                    [ClassName],
                    [StartTime],
                    [EndTime],
                    [Status],
                    [PresentationType],
                    [AorShortName],
                    [LocationName],
                    [InstructorName],
                    [MemberID],
                    [MemberName],
                    [MemberOffice],
                    [RegisteredOn],
                    [ConfirmedOn],
                    [WasPresent],
                    [AttendeeEmail],
                    [ContactType],
                    [MemberType],
                    [MemberStatus],
                    [CreatedOn],
                    [ModifiedOn]
                FROM [consumable].[Fact_ClassAttendance]
                WHERE [TrainingClassId] IS NOT NULL
                AND [IsDeleted] != 'True'
                ORDER BY [StartTime] DESC
            """,
            
            # Instructor performance data
            "instructor_performance": """
                SELECT 
                    [InstructorID],
                    [InstructorName],
                    [InstructorEmail],
                    [InstructorStatus],
                    [Role],
                    [Title],
                    [Phone],
                    [Color],
                    [PhotoURL],
                    [SurveyURL],
                    [TotalSessions],
                    [TotalAttendeesPresent],
                    [UniqueAttendees],
                    [AverageAttendanceRate],
                    [LastSessionCreatedOn],
                    [LastSessionModifiedOn],
                    [IsDeleted]
                FROM [consumable].[Fact_InstructorPerformance]
                WHERE [InstructorID] IS NOT NULL
                AND [IsDeleted] != 'True'
                ORDER BY [TotalSessions] DESC
            """,
            
            # Office participation summary (from attendance stats)
            "office_participation": """
                SELECT 
                    [AorShortName],
                    [MemberOffice],
                    COUNT(DISTINCT [TrainingClassId]) as ClassesOffered,
                    SUM([MembersAttended]) as TotalMembersAttended,
                    SUM([TotalAttendances]) as TotalAttendances,
                    COUNT(DISTINCT [InstructorId]) as UniqueInstructors,
                    COUNT(DISTINCT [LocationId]) as UniqueLocations,
                    AVG(CAST([MembersAttended] as FLOAT)) as AvgMembersPerClass
                FROM [consumable].[Fact_AttendanceStats]
                WHERE [AorShortName] IS NOT NULL
                AND [MemberOffice] IS NOT NULL
                GROUP BY [AorShortName], [MemberOffice]
                ORDER BY TotalAttendances DESC
            """,
            
            # ✅ REMOVED: recent_activity query entirely
            
            # AOR offices mapping for filtering
            "aor_offices": """
                SELECT DISTINCT 
                    [AorShortName],
                    [OfficeCode],
                    [AorName],
                    [AorID]
                FROM [consumable].[Dim_Aors]
                WHERE [OfficeCode] IS NOT NULL
                AND [AorShortName] IS NOT NULL
            """
        }
        
        return run_queries(queries, 'training', len(queries))

    def parse_custom_datetime(date_str):
        """
        Parse custom datetime format: 'Feb-04-25@6 PM' -> datetime object
        Same parsing logic as other components
        """
        if not date_str or pd.isna(date_str):
            return None
            
        try:
            if '@' in str(date_str):
                date_part, time_part = str(date_str).split('@')
                date_components = date_part.split('-')
                if len(date_components) == 3:
                    month_str, day_str, year_str = date_components
                    year = int('20' + year_str) if len(year_str) == 2 else int(year_str)
                    formatted_date = f"{month_str} {day_str} {year}"
                    time_str = time_part.strip()
                    full_datetime_str = f"{formatted_date} {time_str}"
                    return pd.to_datetime(full_datetime_str, format='%b %d %Y %I %p')
            
            return pd.to_datetime(date_str, errors='coerce')
            
        except Exception as e:
            print(f"⚠️ Error parsing date '{date_str}': {e}")
            return None

    @monitor_performance("Training Data Table Filter Application")
    def apply_data_table_filters(base_data, query_selections):
        """
        Apply filters to base training data using pandas
        """
        if not query_selections:
            query_selections = {}
        
        # Convert to DataFrames and create explicit copies
        filtered_data = {}
        for key, data in base_data.items():
            if data is not None and len(data) > 0:
                filtered_data[key] = pd.DataFrame(data).copy()
            else:
                filtered_data[key] = pd.DataFrame()
        
        # print(f"📊 Starting data table filtering")
        
        # Parse filter values
        aors_filter = query_selections.get('AORs', '')
        aor_list = [aor.strip("'\"") for aor in aors_filter.split(',') if aor.strip("'\"")]
        
        offices_filter = query_selections.get('Offices', '')
        office_list = [office.strip("'\"") for office in offices_filter.split(',') if office.strip("'\"")]
        
        instructors_filter = query_selections.get('Instructors', '')
        instructor_list = [instructor.strip("'\"") for instructor in instructors_filter.split(',') if instructor.strip("'\"")]
        
        # Apply date range filter where applicable
        start_date = query_selections.get('Day_From')
        end_date = query_selections.get('Day_To')
        
        # Apply filters to each dataset
        df_aor_offices = filtered_data.get('aor_offices', pd.DataFrame())
        
        # Office filter (via AOR mapping)
        office_aors = []
        if office_list and not df_aor_offices.empty:
            office_aors = df_aor_offices.loc[df_aor_offices['OfficeCode'].isin(office_list), 'AorShortName'].unique().tolist()
        
        # Apply filters to member engagement data
        df_member = filtered_data.get('member_engagement', pd.DataFrame())
        if not df_member.empty:
            if aor_list:
                df_member = df_member.loc[df_member['AorShortName'].isin(aor_list)].copy()
            if office_aors:
                df_member = df_member.loc[df_member['AorShortName'].isin(office_aors)].copy()
            if office_list:  # Direct office code filter
                df_member = df_member.loc[df_member['OfficeCode'].isin(office_list)].copy()
            filtered_data['member_engagement'] = df_member
        
        # Apply filters to class attendance data
        df_attendance = filtered_data.get('class_attendance', pd.DataFrame())
        if not df_attendance.empty:
            # Parse dates for attendance data
            if 'StartTime' in df_attendance.columns:
                df_attendance = df_attendance.copy()
                if df_attendance['StartTime'].dtype == 'object':
                    df_attendance.loc[:, 'ParsedStartTime'] = df_attendance['StartTime'].apply(parse_custom_datetime)
                else:
                    df_attendance.loc[:, 'ParsedStartTime'] = pd.to_datetime(df_attendance['StartTime'])
                
                df_attendance = df_attendance.dropna(subset=['ParsedStartTime'])
                
                # Apply date filter
                if start_date and end_date:
                    try:
                        start_dt = pd.to_datetime(start_date)
                        end_dt = pd.to_datetime(end_date)
                        df_attendance = df_attendance.loc[
                            (df_attendance['ParsedStartTime'] >= start_dt) & 
                            (df_attendance['ParsedStartTime'] <= end_dt)
                        ].copy()
                    except Exception as e:
                        print(f"❌ Error applying date filter: {e}")
            
            if aor_list:
                df_attendance = df_attendance.loc[df_attendance['AorShortName'].isin(aor_list)].copy()
            if office_aors:
                df_attendance = df_attendance.loc[df_attendance['AorShortName'].isin(office_aors)].copy()
            if instructor_list:
                df_attendance = df_attendance.loc[df_attendance['InstructorName'].isin(instructor_list)].copy()
            filtered_data['class_attendance'] = df_attendance
        
        # Apply filters to office participation data
        df_office = filtered_data.get('office_participation', pd.DataFrame())
        if not df_office.empty:
            if aor_list:
                df_office = df_office.loc[df_office['AorShortName'].isin(aor_list)].copy()
            if office_aors:
                df_office = df_office.loc[df_office['AorShortName'].isin(office_aors)].copy()
            filtered_data['office_participation'] = df_office
        
        # ✅ REMOVED: All recent_activity filtering logic
        
        # print(f"📊 Data table filtering completed")
        return filtered_data

    @monitor_performance("Training Data Table Preparation")
    def prepare_data_table_report(filtered_data, report_type):  # ✅ REMOVED: search_term parameter
        """
        Prepare data table based on selected report type
        """
        try:
            if report_type == "member_summary":
                df = filtered_data.get('member_engagement', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                # Select and rename columns for member summary - ensure columns exist
                available_columns = df.columns.tolist()
                required_columns = ['MemberName', 'OfficeCode', 'AorShortName', 'MemberType', 
                                  'TotalSessionsRegistered', 'TotalSessionsAttended', 'MissedSessions', 
                                  'AttendanceRate', 'LastRegisteredOn']
                
                # Only select columns that actually exist
                select_columns = [col for col in required_columns if col in available_columns]
                
                if not select_columns:
                    # print(f"⚠️ No required columns found for member_summary. Available: {available_columns}")
                    return pd.DataFrame()
                
                report_df = df[select_columns].copy()
                
                # Create column mapping only for existing columns
                column_mapping = {
                    'MemberName': 'Member Name',
                    'OfficeCode': 'Office',
                    'AorShortName': 'AOR',
                    'MemberType': 'Member Type',
                    'TotalSessionsRegistered': 'Registered',
                    'TotalSessionsAttended': 'Attended',
                    'MissedSessions': 'Missed',
                    'AttendanceRate': 'Attendance %',
                    'LastRegisteredOn': 'Last Registration'
                }
                
                # Only rename columns that exist
                rename_mapping = {k: v for k, v in column_mapping.items() if k in report_df.columns}
                report_df = report_df.rename(columns=rename_mapping)
                
                # Format numeric columns if they exist
                if 'Attendance %' in report_df.columns:
                    report_df['Attendance %'] = pd.to_numeric(report_df['Attendance %'], errors='coerce').round(1)
                
            elif report_type == "class_details":
                df = filtered_data.get('class_attendance', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                # Select and rename columns for class details - ensure columns exist
                available_columns = df.columns.tolist()
                required_columns = ['ClassName', 'StartTime', 'PresentationType', 'AorShortName', 
                                  'LocationName', 'InstructorName', 'MemberName', 'WasPresent', 
                                  'RegisteredOn', 'AttendeeEmail']
                
                select_columns = [col for col in required_columns if col in available_columns]
                
                if not select_columns:
                    # print(f"⚠️ No required columns found for class_details. Available: {available_columns}")
                    return pd.DataFrame()
                
                report_df = df[select_columns].copy()
                
                column_mapping = {
                    'ClassName': 'Class Name',
                    'StartTime': 'Start Time',
                    'PresentationType': 'Type',
                    'AorShortName': 'AOR',
                    'LocationName': 'Location',
                    'InstructorName': 'Instructor',
                    'MemberName': 'Member Name',
                    'WasPresent': 'Attended',
                    'RegisteredOn': 'Registered On',
                    'AttendeeEmail': 'Email'
                }
                
                rename_mapping = {k: v for k, v in column_mapping.items() if k in report_df.columns}
                report_df = report_df.rename(columns=rename_mapping)
                
            elif report_type == "instructor_details":
                df = filtered_data.get('instructor_performance', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                available_columns = df.columns.tolist()
                # print(f"📋 Available instructor performance columns: {available_columns}")
                
                # Updated column names to match the actual schema
                required_columns = ['InstructorName', 'Role', 'Title', 'InstructorEmail', 'Phone',
                                  'TotalSessions', 'TotalAttendeesPresent', 'UniqueAttendees', 
                                  'AverageAttendanceRate', 'LastSessionCreatedOn', 'InstructorStatus']
                
                select_columns = [col for col in required_columns if col in available_columns]
                
                if not select_columns:
                    # print(f"⚠️ No required columns found for instructor_details. Available: {available_columns}")
                    # Fallback: Use all available columns if none of the expected ones exist
                    select_columns = available_columns[:10]  # Take first 10 columns as fallback
                
                if not select_columns:
                    return pd.DataFrame()
                
                report_df = df[select_columns].copy()
                
                # Updated column mapping to match schema
                column_mapping = {
                    'InstructorName': 'Instructor Name',
                    'Role': 'Role',
                    'Title': 'Title', 
                    'InstructorEmail': 'Email',
                    'Phone': 'Phone',
                    'InstructorStatus': 'Status',
                    'TotalSessions': 'Total Sessions',
                    'TotalAttendeesPresent': 'Total Attendees',
                    'UniqueAttendees': 'Unique Attendees',
                    'AverageAttendanceRate': 'Avg Attendance %',
                    'LastSessionCreatedOn': 'Last Session Created',
                    'LastSessionModifiedOn': 'Last Session Modified',
                    'Color': 'Color',
                    'PhotoURL': 'Photo URL',
                    'SurveyURL': 'Survey URL'
                }
                
                rename_mapping = {k: v for k, v in column_mapping.items() if k in report_df.columns}
                report_df = report_df.rename(columns=rename_mapping)
                
                # Format numeric columns if they exist
                if 'Avg Attendance %' in report_df.columns:
                    report_df['Avg Attendance %'] = pd.to_numeric(report_df['Avg Attendance %'], errors='coerce').round(1)
                
            elif report_type == "office_summary":
                df = filtered_data.get('office_participation', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                available_columns = df.columns.tolist()
                required_columns = ['AorShortName', 'MemberOffice', 'ClassesOffered', 'TotalMembersAttended',
                                  'TotalAttendances', 'UniqueInstructors', 'UniqueLocations', 'AvgMembersPerClass']
                
                select_columns = [col for col in required_columns if col in available_columns]
                
                if not select_columns:
                    # print(f"⚠️ No required columns found for office_summary. Available: {available_columns}")
                    return pd.DataFrame()
                
                report_df = df[select_columns].copy()
                
                column_mapping = {
                    'AorShortName': 'AOR',
                    'MemberOffice': 'Office',
                    'ClassesOffered': 'Classes Offered',
                    'TotalMembersAttended': 'Members Attended',
                    'TotalAttendances': 'Total Attendances',
                    'UniqueInstructors': 'Instructors',
                    'UniqueLocations': 'Locations',
                    'AvgMembersPerClass': 'Avg Members/Class'
                }
                
                rename_mapping = {k: v for k, v in column_mapping.items() if k in report_df.columns}
                report_df = report_df.rename(columns=rename_mapping)
                
                # Format numeric columns if they exist
                if 'Avg Members/Class' in report_df.columns:
                    report_df['Avg Members/Class'] = pd.to_numeric(report_df['Avg Members/Class'], errors='coerce').round(1)
                
            else:
                return pd.DataFrame()
            
            # ✅ REMOVED: Search filter logic entirely since columns have native filtering
            
            # Format datetime columns
            datetime_columns = report_df.select_dtypes(include=['datetime64[ns]']).columns
            for col in datetime_columns:
                report_df[col] = report_df[col].dt.strftime('%Y-%m-%d %H:%M')
            
            # print(f"📊 Prepared {report_type} report: {len(report_df)} records")
            return report_df
            
        except Exception as e:
            print(f"❌ Error preparing data table report: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @callback(
        Output("training-data-table-container", "children"),
        [Input("training-filtered-query-store", "data"),
         Input("data-table-report-type-dropdown", "value"),
         Input("table-page-size-dropdown", "value")],  # ✅ REMOVED: table-search-input from inputs
        prevent_initial_call=False
    )
    @monitor_performance("Training Data Table Update")
    def update_training_data_table(query_selections, report_type, page_size):  # ✅ REMOVED: search_term parameter
        """
        Update training data table based on selections
        """
        try:
            # print(f"🔄 Updating training data table: report={report_type}, page_size={page_size}")
            
            # Get base data
            base_data = get_training_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_data_table_report(filtered_data, report_type)  # ✅ REMOVED: search_term argument
            
            if report_df.empty:
                return html.Div([
                    html.P("No data available for the selected filters and report type.", 
                           className="text-muted text-center p-4")
                ])
            
            # Create data table columns
            columns = []
            for col in report_df.columns:
                col_config = {
                    "name": col,
                    "id": col,
                    "deletable": False,
                    "selectable": False
                }
                
                # Format numeric columns
                if col in ['Attendance %', 'Avg Attendance %', 'Avg Members/Class']:
                    col_config.update({
                        "type": "numeric",
                        "format": {"specifier": ".1f"}
                    })
                elif col in ['Registered', 'Attended', 'Missed', 'Total Sessions', 'Total Attendees', 
                           'Unique Attendees', 'Classes Offered', 'Members Attended', 'Total Attendances', 
                           'Instructors', 'Locations']:
                    col_config.update({
                        "type": "numeric",
                        "format": {"specifier": ","}
                    })
                
                columns.append(col_config)
            
            # Create clean conditional styling
            style_data_conditional = [
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }
            ]
            
            # Create the data table
            data_table = dash_table.DataTable(
                id="training-data-table",
                columns=columns,
                data=report_df.to_dict('records'),
                page_size=page_size,
                sort_action="native",
                sort_mode="multi",
                filter_action="native",  # ✅ This provides per-column filtering
                style_table={
                    'overflowX': 'auto',
                    'minWidth': '100%'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'border': '1px solid #dee2e6'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'color': '#495057',
                    'border': '1px solid #dee2e6'
                },
                style_data_conditional=style_data_conditional,
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'background-color: grey; font-family: monospace; color: white'
                }]
            )
            
            # Add summary information
            summary_info = html.Div([
                html.P([
                    html.Strong(f"Showing {len(report_df):,} records"),
                    f" • Report: {report_type.replace('_', ' ').title()}",
                    f" • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ], className="text-muted small mb-3")
            ])
            
            return html.Div([summary_info, data_table])
            
        except Exception as e:
            print(f"❌ Error updating training data table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div([
                html.P(f"Error loading data table: {str(e)}", 
                       className="text-danger text-center p-4")
            ])
        
    @callback(
        Output("download-csv", "data"),
        Input("export-csv-btn", "n_clicks"),
        [State("training-filtered-query-store", "data"),
         State("data-table-report-type-dropdown", "value")],  # ✅ REMOVED: table-search-input from states
        prevent_initial_call=True
    )
    @monitor_performance("CSV Export")
    def export_csv(n_clicks, query_selections, report_type):  # ✅ REMOVED: search_term parameter
        """
        Export current data table view as CSV
        """
        if not n_clicks:
            return no_update
        
        try:
            # print(f"📥 Exporting CSV: report={report_type}")
            
            # Get base data
            base_data = get_training_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_data_table_report(filtered_data, report_type)  # ✅ REMOVED: search_term argument
            
            if report_df.empty:
                return no_update
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"training_{report_type}_{timestamp}.csv"
            
            return dcc.send_data_frame(report_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"❌ Error exporting CSV: {e}")
            return no_update

    @callback(
        Output("download-excel", "data"),
        Input("export-excel-btn", "n_clicks"),
        [State("training-filtered-query-store", "data"),
         State("data-table-report-type-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Excel Export")
    def export_excel(n_clicks, query_selections, report_type):
        """
        Export current data table view as Excel
        """
        if not n_clicks:
            return no_update
        
        try:
            # print(f"📥 Exporting Excel: report={report_type}")
            
            # Get base data
            base_data = get_training_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_data_table_report(filtered_data, report_type)
            
            if report_df.empty:
                # print("❌ No data to export")
                return no_update
            
            # print(f"✅ Preparing Excel export with {len(report_df)} records")
            
            # ✅ FIXED: Create Excel file using BytesIO buffer
            import io
            try:
                # Try using openpyxl engine first
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    sheet_name = report_type.replace('_', ' ').title()[:31]  # Excel sheet name limit
                    report_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                buffer.seek(0)
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"training_{report_type}_{timestamp}.xlsx"
                
                # print(f"✅ Excel file created successfully: {filename}")
                
                # ✅ FIXED: Use dcc.send_bytes instead of send_data_frame
                return dcc.send_bytes(
                    buffer.getvalue(),
                    filename=filename
                )
                
            except ImportError:
                print("⚠️ openpyxl not available, trying xlsxwriter")
                # Fallback to xlsxwriter
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    sheet_name = report_type.replace('_', ' ').title()[:31]
                    report_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                buffer.seek(0)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"training_{report_type}_{timestamp}.xlsx"
                
                return dcc.send_bytes(
                    buffer.getvalue(),
                    filename=filename
                )
                
        except Exception as e:
            print(f"❌ Error exporting Excel: {e}")
            import traceback
            traceback.print_exc()
            
            # ✅ FALLBACK: If Excel fails, export as CSV with .xlsx extension
            try:
                # print("⚠️ Falling back to CSV export with Excel extension")
                base_data = get_training_data_table_base_data()
                filtered_data = apply_data_table_filters(base_data, query_selections)
                report_df = prepare_data_table_report(filtered_data, report_type)
                
                if not report_df.empty:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"training_{report_type}_{timestamp}_fallback.csv"
                    return dcc.send_data_frame(report_df.to_csv, filename, index=False)
                    
            except Exception as fallback_error:
                print(f"❌ Fallback export also failed: {fallback_error}")
            
            return no_update
        
    @callback(
        Output("download-pdf", "data"),
        Input("export-pdf-btn", "n_clicks"),
        [State("training-filtered-query-store", "data"),
         State("data-table-report-type-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("PDF Export")
    def export_pdf(n_clicks, query_selections, report_type):
        """
        Export current data table view as a nicely formatted PDF with proper text wrapping
        """
        if not n_clicks:
            return no_update
        
        try:
            # print(f"📄 Exporting PDF: report={report_type}")
            
            # Get base data
            base_data = get_training_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_data_table_report(filtered_data, report_type)
            
            if report_df.empty:
                # print("❌ No data to export")
                return no_update
            
            # print(f"✅ Preparing PDF export with {len(report_df)} records")
            
            # Create PDF buffer
            buffer = io.BytesIO()
            
            # Determine page orientation based on number of columns
            if len(report_df.columns) > 6:
                page_size = landscape(A4)
                page_width = landscape(A4)[0]
            else:
                page_size = A4
                page_width = A4[0]
            
            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=page_size,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=1*inch,
                bottomMargin=0.5*inch
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=0.3*inch
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=0.2*inch
            )
            
            # ✅ NEW: Create text styles for table cells with proper wrapping
            cell_text_style = ParagraphStyle(
                'CellText',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.black,
                alignment=TA_LEFT,
                leading=10,  # Line spacing
                leftIndent=2,
                rightIndent=2,
                spaceAfter=2,
                wordWrap='LTR'  # Left-to-right word wrapping
            )
            
            cell_numeric_style = ParagraphStyle(
                'CellNumeric',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.black,
                alignment=TA_RIGHT,
                leading=10,
                leftIndent=2,
                rightIndent=2,
                spaceAfter=2
            )
            
            cell_center_style = ParagraphStyle(
                'CellCenter',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.black,
                alignment=TA_CENTER,
                leading=10,
                leftIndent=2,
                rightIndent=2,
                spaceAfter=2
            )
            
            header_style = ParagraphStyle(
                'HeaderText',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.whitesmoke,
                alignment=TA_CENTER,
                leading=11,
                fontName='Helvetica-Bold',
                leftIndent=2,
                rightIndent=2
            )
            
            # Create content elements
            elements = []
            
            # Title
            report_title = report_type.replace('_', ' ').title()
            title = Paragraph(f"Training Activity Report: {report_title}", title_style)
            elements.append(title)
            
            # Subtitle with metadata
            current_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            subtitle = Paragraph(f"Generated on {current_time} • {len(report_df):,} records", subtitle_style)
            elements.append(subtitle)
            
            # Add some space
            elements.append(Spacer(1, 0.2*inch))
            
            # ✅ ENHANCED: Intelligent column width calculation
            headers = list(report_df.columns)
            num_cols = len(headers)
            available_width = page_width - 1*inch  # Account for margins
            
            # Calculate optimal column widths based on content
            def calculate_column_widths(df, headers, available_width):
                """Calculate column widths based on content length and type"""
                min_width = 1.0*inch  # Increased minimum width for wrapping
                max_width = 3.0*inch  # Increased maximum width for long text columns
                
                column_weights = {}
                
                for col in headers:
                    # Get sample of data for analysis (first 20 rows)
                    sample_data = df[col].head(20).astype(str)
                    
                    # Calculate average character length
                    avg_length = sample_data.str.len().mean()
                    max_length = sample_data.str.len().max()
                    header_length = len(col)
                    
                    # Determine column type and appropriate width
                    if col.lower() in ['email', 'attendee email', 'instructor email']:
                        # Email columns need more space for wrapping
                        weight = min(max_width, max(2.2*inch, avg_length * 0.06*inch))
                    elif any(keyword in col.lower() for keyword in ['name', 'class name', 'member name', 'instructor name']):
                        # Name columns need medium-large space
                        weight = min(max_width, max(1.8*inch, avg_length * 0.05*inch))
                    elif any(keyword in col.lower() for keyword in ['location', 'office']):
                        # Location columns need medium space  
                        weight = min(2.5*inch, max(1.5*inch, avg_length * 0.04*inch))
                    elif any(keyword in col.lower() for keyword in ['%', 'rate', 'count', 'total', 'sessions', 'attendees']):
                        # Numeric columns need less space (no wrapping needed)
                        weight = min(1.3*inch, max(1.0*inch, max(header_length * 0.12*inch, 1.0*inch)))
                    elif any(keyword in col.lower() for keyword in ['date', 'time', 'on']):
                        # Date/time columns need medium space
                        weight = min(1.8*inch, max(1.3*inch, header_length * 0.1*inch))
                    elif col.lower() in ['type', 'status', 'role', 'title']:
                        # Short categorical columns
                        weight = min(1.5*inch, max(1.0*inch, max(avg_length * 0.08*inch, header_length * 0.1*inch)))
                    else:
                        # Default sizing based on content
                        weight = min(max_width, max(min_width, avg_length * 0.05*inch))
                    
                    column_weights[col] = weight
                
                # Normalize weights to fit available width
                total_weight = sum(column_weights.values())
                if total_weight > available_width:
                    # Scale down proportionally
                    scale_factor = available_width / total_weight
                    column_weights = {col: weight * scale_factor for col, weight in column_weights.items()}
                elif total_weight < available_width:
                    # Distribute extra space proportionally
                    extra_space = available_width - total_weight
                    for col in column_weights:
                        column_weights[col] += extra_space / num_cols
                
                return [column_weights[col] for col in headers]
            
            # Calculate intelligent column widths
            col_widths = calculate_column_widths(report_df, headers, available_width)
            
            # ✅ NEW: Prepare table data with Paragraph objects for text wrapping
            table_data = []
            
            # Add headers with Paragraph objects
            header_row = []
            for header in headers:
                header_paragraph = Paragraph(str(header), header_style)
                header_row.append(header_paragraph)
            table_data.append(header_row)
            
            # ✅ NEW: Add data rows with Paragraph objects for automatic wrapping
            max_rows = 100
            for i, row in report_df.head(max_rows).iterrows():
                row_data = []
                for col_idx, val in enumerate(row):
                    col_name = headers[col_idx]
                    
                    if pd.isna(val):
                        cell_content = ""
                        cell_paragraph = Paragraph(cell_content, cell_text_style)
                    elif isinstance(val, (int, float)):
                        if isinstance(val, float) and val == int(val):
                            cell_content = str(int(val))
                        else:
                            cell_content = str(val)
                        # Use numeric style for numbers
                        cell_paragraph = Paragraph(cell_content, cell_numeric_style)
                    else:
                        # ✅ PRESERVE ALL TEXT: No truncation, just clean the text
                        text = str(val).strip()
                        
                        # Clean up text for PDF (escape special characters)
                        text = text.replace('&', '&amp;')
                        text = text.replace('<', '&lt;')
                        text = text.replace('>', '&gt;')
                        text = text.replace('"', '&quot;')
                        text = text.replace("'", '&#39;')
                        
                        # Determine appropriate style based on column type
                        if any(keyword in col_name.lower() for keyword in ['%', 'rate', 'count', 'total', 'sessions', 'attendees', 'registered', 'attended', 'missed']):
                            cell_paragraph = Paragraph(text, cell_numeric_style)
                        elif any(keyword in col_name.lower() for keyword in ['date', 'time', 'on']):
                            cell_paragraph = Paragraph(text, cell_center_style)
                        else:
                            cell_paragraph = Paragraph(text, cell_text_style)
                    
                    row_data.append(cell_paragraph)
                
                table_data.append(row_data)
            
            # ✅ ENHANCED: Create table with calculated widths and automatic row heights
            table = Table(
                table_data,
                colWidths=col_widths,
                repeatRows=1,  # Repeat header on each page
                splitByRow=True  # ✅ NEW: Allow table to split across pages by row
            )
            
            # ✅ ENHANCED: Apply table styling optimized for text wrapping
            table_style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Data rows styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                
                # ✅ ENHANCED: Generous padding for text wrapping
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                
                # ✅ CRITICAL: Vertical alignment for wrapped text
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for all cells
                
                # ✅ NEW: Grid lines for better readability with wrapped text
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),  # Thicker line below header
                ('LINEBEFORE', (0, 0), (0, -1), 2, colors.black), # Left border
                ('LINEAFTER', (-1, 0), (-1, -1), 2, colors.black), # Right border
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black), # Bottom border
            ])
            
            table.setStyle(table_style)
            elements.append(table)
            
            # Add footer note if data was truncated
            if len(report_df) > max_rows:
                footer_style = ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=TA_CENTER
                )
                elements.append(Spacer(1, 0.2*inch))
                footer_text = f"Note: Showing first {max_rows} records of {len(report_df):,} total records. Use Excel export for complete data."
                footer = Paragraph(footer_text, footer_style)
                elements.append(footer)
            
            # ✅ NEW: Add note about text wrapping
            wrap_note_style = ParagraphStyle(
                'WrapNote',
                parent=styles['Normal'],
                fontSize=7,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=0.1*inch
            )
            elements.append(Spacer(1, 0.1*inch))
            wrap_note = Paragraph("All text content is preserved with automatic wrapping for readability.", wrap_note_style)
            elements.append(wrap_note)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"training_{report_type}_{timestamp}.pdf"
            
            # print(f"✅ PDF file created successfully: {filename}")
            
            return dcc.send_bytes(
                buffer.getvalue(),
                filename=filename
            )
            
        except Exception as e:
            print(f"❌ Error exporting PDF: {e}")
            import traceback
            traceback.print_exc()
            return no_update
                       
# print("✅ Training data table callbacks registered")