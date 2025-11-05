from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_training_instructor_performance_callbacks(app):
    """
    Register instructor performance analysis callbacks
    Matches the component IDs from the layout file
    """
    
    @monitor_query_performance("Instructor Performance Base Data")
    def get_instructor_performance_base_data():
        """
        Fetch base data for instructor performance analysis
        Uses consumable fact tables with minimal joins
        """
        
        queries = {
            # Get instructor performance data from fact table
            "instructor_performance": """
                SELECT 
                    [InstructorID],
                    [InstructorName],
                    [InstructorEmail],
                    [InstructorStatus],
                    [Role],
                    [Title],
                    [Phone],
                    [TotalSessions],
                    [TotalAttendeesPresent],
                    [UniqueAttendees],
                    [AverageAttendanceRate],
                    [LastSessionCreatedOn],
                    [LastSessionModifiedOn]
                FROM [consumable].[Fact_InstructorPerformance]
                WHERE [InstructorStatus] = 'Active'
                AND [IsDeleted] != 'True'
            """,
            
            # Get detailed class attendance data for additional metrics
            "class_attendance": """
                SELECT 
                    [TrainingClassId],
                    [ClassName],
                    [StartTime],
                    [EndTime],
                    [Duration],
                    [Status],
                    [PresentationType],
                    [AorId],
                    [AorShortName],
                    [AorName],
                    [LocationId],
                    [LocationName],
                    [LocationCapacity],
                    [InstructorId],
                    [InstructorName],
                    [MemberID],
                    [MemberName],
                    [MemberOffice],
                    [WasPresent],
                    [RegisteredOn],
                    [ConfirmedOn],
                    [AttendeeEmail],
                    [ContactType],
                    [MemberType],
                    [MemberStatus]
                FROM [consumable].[Fact_ClassAttendance]
                WHERE [InstructorId] IS NOT NULL
                AND [InstructorName] IS NOT NULL
                AND [StartTime] IS NOT NULL
                AND [IsDeleted] != 'True'
            """,
            
            # Get training classes for session counts and scheduling info
            "training_classes": """
                SELECT 
                    [TrainingClassId],
                    [TrainingClassName],
                    [PresentationType],
                    [Status],
                    [StartTime],
                    [EndTime],
                    [Duration],
                    [Capacity],
                    [SeatsAvailable],
                    [AttendeeCount],
                    [AorId],
                    [AorName],
                    [AorShortName],
                    [InstructorId],
                    [InstructorName],
                    [LocationId],
                    [LocationName],
                    [CreatedOn],
                    [ModifiedOn]
                FROM [consumable].[Fact_TrainingClasses]
                WHERE [InstructorId] IS NOT NULL
                AND [InstructorName] IS NOT NULL
                AND [StartTime] IS NOT NULL
                AND [IsDeleted] != 'True'
            """,
            
            # Get AOR-Office mapping
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
        
        return run_queries(queries, len(queries))

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

    @monitor_performance("Instructor Performance Filter Application")
    def apply_instructor_performance_filters(base_data, query_selections):
        """
        Apply filters to base instructor performance data using pandas
        """
        if not query_selections:
            query_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_instructor_perf = pd.DataFrame(base_data.get('instructor_performance', [])).copy()
        df_class_attendance = pd.DataFrame(base_data.get('class_attendance', [])).copy()
        df_training_classes = pd.DataFrame(base_data.get('training_classes', [])).copy()
        df_aor_offices = pd.DataFrame(base_data.get('aor_offices', [])).copy()
        
        # print(f"📊 Starting instructor performance filtering: {len(df_instructor_perf)} instructor records, {len(df_class_attendance)} attendance records")
        
        # Parse filter values
        aors_filter = query_selections.get('AORs', '')
        aor_list = [aor.strip("'\"") for aor in aors_filter.split(',') if aor.strip("'\"")]
        
        offices_filter = query_selections.get('Offices', '')
        office_list = [office.strip("'\"") for office in offices_filter.split(',') if office.strip("'\"")]
        
        topics_filter = query_selections.get('Topics', '')
        topic_list = [topic.strip("'\"") for topic in topics_filter.split(',') if topic.strip("'\"")]
        
        instructors_filter = query_selections.get('Instructors', '')
        instructor_list = [instructor.strip("'\"") for instructor in instructors_filter.split(',') if instructor.strip("'\"")]
        
        locations_filter = query_selections.get('Locations', '')
        location_list = [location.strip("'\"") for location in locations_filter.split(',') if location.strip("'\"")]
        
        # Parse dates from class data
        if not df_class_attendance.empty and 'StartTime' in df_class_attendance.columns:
            df_class_attendance = df_class_attendance.copy()
            
            # Handle different datetime formats
            if df_class_attendance['StartTime'].dtype == 'object':
                df_class_attendance.loc[:, 'ParsedStartTime'] = df_class_attendance['StartTime'].apply(parse_custom_datetime)
            else:
                df_class_attendance.loc[:, 'ParsedStartTime'] = pd.to_datetime(df_class_attendance['StartTime'])
            
            df_class_attendance = df_class_attendance.dropna(subset=['ParsedStartTime']).copy()
            
            # Apply date range filter if specified
            start_date = query_selections.get('Day_From')
            end_date = query_selections.get('Day_To')
            
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df_class_attendance = df_class_attendance.loc[
                        (df_class_attendance['ParsedStartTime'] >= start_dt) & 
                        (df_class_attendance['ParsedStartTime'] <= end_dt)
                    ].copy()
                    # print(f"📅 Date filter applied: {len(df_class_attendance)} attendance records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Parse dates from training classes
        if not df_training_classes.empty and 'StartTime' in df_training_classes.columns:
            df_training_classes = df_training_classes.copy()
            
            if df_training_classes['StartTime'].dtype == 'object':
                df_training_classes.loc[:, 'ParsedStartTime'] = df_training_classes['StartTime'].apply(parse_custom_datetime)
            else:
                df_training_classes.loc[:, 'ParsedStartTime'] = pd.to_datetime(df_training_classes['StartTime'])
            
            df_training_classes = df_training_classes.dropna(subset=['ParsedStartTime']).copy()
            
            # Apply same date filter to training classes
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df_training_classes = df_training_classes.loc[
                        (df_training_classes['ParsedStartTime'] >= start_dt) & 
                        (df_training_classes['ParsedStartTime'] <= end_dt)
                    ].copy()
                except Exception as e:
                    print(f"❌ Error applying date filter to training classes: {e}")
        
        # Apply AOR filter
        if aor_list:
            if not df_class_attendance.empty:
                df_class_attendance = df_class_attendance.loc[df_class_attendance['AorShortName'].isin(aor_list)].copy()
            if not df_training_classes.empty:
                df_training_classes = df_training_classes.loc[df_training_classes['AorShortName'].isin(aor_list)].copy()
            # print(f"🎯 AOR filter applied: {len(df_class_attendance)} attendance, {len(df_training_classes)} classes")
        
        # Apply Office filter (via AOR mapping)
        if office_list and not df_aor_offices.empty:
            office_aors = df_aor_offices.loc[df_aor_offices['OfficeCode'].isin(office_list), 'AorShortName'].unique()
            if len(office_aors) > 0:
                if not df_class_attendance.empty:
                    df_class_attendance = df_class_attendance.loc[df_class_attendance['AorShortName'].isin(office_aors)].copy()
                if not df_training_classes.empty:
                    df_training_classes = df_training_classes.loc[df_training_classes['AorShortName'].isin(office_aors)].copy()
            # print(f"🏢 Office filter applied: {len(df_class_attendance)} attendance, {len(df_training_classes)} classes")
        
        # Apply Instructor filter
        if instructor_list:
            # Filter instructor performance data
            if not df_instructor_perf.empty:
                df_instructor_perf = df_instructor_perf.loc[df_instructor_perf['InstructorID'].astype(str).isin(instructor_list)].copy()
            if not df_class_attendance.empty:
                df_class_attendance = df_class_attendance.loc[df_class_attendance['InstructorId'].astype(str).isin(instructor_list)].copy()
            if not df_training_classes.empty:
                df_training_classes = df_training_classes.loc[df_training_classes['InstructorId'].astype(str).isin(instructor_list)].copy()
            # print(f"👨‍🏫 Instructor filter applied: {len(df_instructor_perf)} instructors, {len(df_class_attendance)} attendance")
        
        # Apply Location filter
        if location_list:
            if not df_class_attendance.empty:
                df_class_attendance = df_class_attendance.loc[df_class_attendance['LocationId'].astype(str).isin(location_list)].copy()
            if not df_training_classes.empty:
                df_training_classes = df_training_classes.loc[df_training_classes['LocationId'].astype(str).isin(location_list)].copy()
            # print(f"📍 Location filter applied: {len(df_class_attendance)} attendance, {len(df_training_classes)} classes")
        
        return {
            "instructor_performance": df_instructor_perf,
            "class_attendance": df_class_attendance,
            "training_classes": df_training_classes,
            "aor_offices": df_aor_offices
        }

    @monitor_performance("Instructor Performance Data Preparation")
    def prepare_instructor_performance_data(filtered_data, performance_metric):
        """
        Prepare instructor performance data for analysis
        """
        df_instructor_perf = filtered_data.get('instructor_performance', pd.DataFrame())
        df_class_attendance = filtered_data.get('class_attendance', pd.DataFrame())
        df_training_classes = filtered_data.get('training_classes', pd.DataFrame())
        
        if df_instructor_perf.empty and df_class_attendance.empty:
            return pd.DataFrame()
        
        try:
            # Start with instructor performance data as base
            if not df_instructor_perf.empty:
                performance_data = df_instructor_perf.copy()
            else:
                # Create minimal instructor data from class attendance if no performance data
                if df_class_attendance.empty:
                    return pd.DataFrame()
                
                instructor_summary = df_class_attendance.groupby(['InstructorId', 'InstructorName']).first().reset_index()
                performance_data = instructor_summary[['InstructorId', 'InstructorName']].copy()
                performance_data = performance_data.rename(columns={'InstructorId': 'InstructorID'})
            
            # Calculate additional metrics from class attendance and training classes data
            if not df_class_attendance.empty:
                # Calculate metrics from detailed attendance data
                attendance_metrics = df_class_attendance.groupby('InstructorId').agg({
                    'TrainingClassId': 'nunique',  # Classes conducted
                    'MemberID': 'nunique',  # Unique students
                    'WasPresent': lambda x: (x == 'True').sum(),  # Total attendees present
                    'AttendeeEmail': 'count'  # Total registrations
                }).reset_index()
                
                attendance_metrics = attendance_metrics.rename(columns={
                    'InstructorId': 'InstructorID',
                    'TrainingClassId': 'ClassesConductedFromAttendance',
                    'MemberID': 'UniqueStudents',
                    'WasPresent': 'AttendeesPresent',
                    'AttendeeEmail': 'TotalRegistrations'
                })
                
                # Calculate attendance rate
                attendance_metrics.loc[:, 'CalculatedAttendanceRate'] = (
                    attendance_metrics['AttendeesPresent'] / attendance_metrics['TotalRegistrations'] * 100
                ).fillna(0)
                
                # Calculate average class size
                class_sizes = df_class_attendance.groupby(['InstructorId', 'TrainingClassId']).agg({
                    'MemberID': 'nunique'
                }).reset_index()
                avg_class_size = class_sizes.groupby('InstructorId')['MemberID'].mean().reset_index()
                avg_class_size = avg_class_size.rename(columns={
                    'InstructorId': 'InstructorID',
                    'MemberID': 'AverageClassSize'
                })
                
                # Merge attendance metrics
                performance_data = performance_data.merge(attendance_metrics, on='InstructorID', how='left')
                performance_data = performance_data.merge(avg_class_size, on='InstructorID', how='left')
            
            # Calculate sessions per month from training classes
            if not df_training_classes.empty:
                # Calculate time span and sessions per month
                classes_with_dates = df_training_classes.dropna(subset=['ParsedStartTime']).copy()
                if not classes_with_dates.empty:
                    instructor_sessions = classes_with_dates.groupby('InstructorId').agg({
                        'TrainingClassId': 'nunique',
                        'ParsedStartTime': ['min', 'max']
                    }).reset_index()
                    
                    instructor_sessions.columns = ['InstructorID', 'TotalClassesFromClasses', 'FirstSession', 'LastSession']
                    
                    # Calculate months between first and last session
                    instructor_sessions.loc[:, 'MonthsActive'] = (
                        (instructor_sessions['LastSession'] - instructor_sessions['FirstSession']).dt.days / 30.44
                    ).fillna(1).apply(lambda x: max(1, x))  # At least 1 month
                    
                    instructor_sessions.loc[:, 'SessionsPerMonth'] = (
                        instructor_sessions['TotalClassesFromClasses'] / instructor_sessions['MonthsActive']
                    )
                    
                    # Merge with performance data
                    performance_data = performance_data.merge(
                        instructor_sessions[['InstructorID', 'SessionsPerMonth']], 
                        on='InstructorID', 
                        how='left'
                    )
            
            # Use the best available data for each metric
            performance_data.loc[:, 'FinalClassesConducted'] = performance_data.get('TotalSessions', performance_data.get('ClassesConductedFromAttendance', 0)).fillna(0)
            performance_data.loc[:, 'FinalAttendanceRate'] = performance_data.get('AverageAttendanceRate', performance_data.get('CalculatedAttendanceRate', 0)).fillna(0)
            performance_data.loc[:, 'FinalUniqueStudents'] = performance_data.get('UniqueAttendees', performance_data.get('UniqueStudents', 0)).fillna(0)
            performance_data.loc[:, 'FinalAverageClassSize'] = performance_data.get('AverageClassSize', 0).fillna(0)
            performance_data.loc[:, 'FinalSessionsPerMonth'] = performance_data.get('SessionsPerMonth', 0).fillna(0)
            
            # ✅ REMOVED: Apply minimum classes filter - no longer filtering by min_classes
            
            # Select the requested metric
            if performance_metric == "attendance_rate":
                performance_data.loc[:, 'MetricValue'] = performance_data['FinalAttendanceRate']
                metric_name = "Attendance Rate (%)"
                
            elif performance_metric == "total_students":
                performance_data.loc[:, 'MetricValue'] = performance_data['FinalUniqueStudents']
                metric_name = "Total Students Taught"
                
            elif performance_metric == "avg_class_size":
                performance_data.loc[:, 'MetricValue'] = performance_data['FinalAverageClassSize']
                metric_name = "Average Class Size"
                
            elif performance_metric == "classes_conducted":
                performance_data.loc[:, 'MetricValue'] = performance_data['FinalClassesConducted']
                metric_name = "Classes Conducted"
                
            elif performance_metric == "sessions_per_month":
                performance_data.loc[:, 'MetricValue'] = performance_data['FinalSessionsPerMonth']
                metric_name = "Sessions per Month"
                
            else:
                # Default to attendance rate
                performance_data.loc[:, 'MetricValue'] = performance_data['FinalAttendanceRate']
                metric_name = "Attendance Rate (%)"
            
            # Add metadata
            performance_data.loc[:, 'MetricName'] = metric_name
            
            # Sort by metric value (descending for better visualization)
            performance_data = performance_data.sort_values('MetricValue', ascending=False)
            
            # print(f"📊 Prepared instructor performance data: {len(performance_data)} instructors, metric: {metric_name}")
            return performance_data
            
        except Exception as e:
            print(f"❌ Error preparing instructor performance data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @monitor_chart_performance("Instructor Performance Chart")
    def create_instructor_performance_chart(performance_data, performance_metric, chart_type):
        """
        Create interactive instructor performance chart
        """
        if performance_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No instructor performance data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Instructor Performance Analysis",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            metric_name = performance_data['MetricName'].iloc[0] if not performance_data.empty else performance_metric
            
            # Create figure based on chart type
            fig = go.Figure()
            
            # Prepare data - limit to top 20 instructors for readability
            display_data = performance_data.head(20).copy()
            
            if chart_type == "bar":
                # Vertical bar chart
                hover_template = f"<b>%{{x}}</b><br>{metric_name}: %{{y:,.1f}}<extra></extra>"
                
                fig.add_trace(go.Bar(
                    x=display_data['InstructorName'],
                    y=display_data['MetricValue'],
                    marker_color='#1f77b4',
                    hovertemplate=hover_template,
                    name=metric_name
                ))
                
                fig.update_layout(
                    xaxis={'title': 'Instructors', 'tickangle': -45},
                    yaxis={'title': metric_name}
                )
                
            elif chart_type == "horizontal_bar":
                # Horizontal bar chart (better for long names)
                hover_template = f"<b>%{{y}}</b><br>{metric_name}: %{{x:,.1f}}<extra></extra>"
                
                fig.add_trace(go.Bar(
                    x=display_data['MetricValue'],
                    y=display_data['InstructorName'],
                    orientation='h',
                    marker_color='#ff7f0e',
                    hovertemplate=hover_template,
                    name=metric_name
                ))
                
                fig.update_layout(
                    xaxis={'title': metric_name},
                    yaxis={'title': 'Instructors'},
                    height=max(500, len(display_data) * 30)  # Adjust height for number of instructors
                )
                
            elif chart_type == "scatter":
                # Scatter plot (metric vs classes conducted)
                hover_template = f"<b>%{{text}}</b><br>Classes: %{{x:,.0f}}<br>{metric_name}: %{{y:,.1f}}<extra></extra>"
                
                fig.add_trace(go.Scatter(
                    x=display_data['FinalClassesConducted'],
                    y=display_data['MetricValue'],
                    mode='markers',
                    marker=dict(
                        size=12,
                        color=display_data['MetricValue'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title=metric_name)
                    ),
                    text=display_data['InstructorName'],
                    hovertemplate=hover_template,
                    name="Instructors"
                ))
                
                fig.update_layout(
                    xaxis={'title': 'Classes Conducted'},
                    yaxis={'title': metric_name}
                )
            
            # Add average line for bar charts
            if chart_type in ["bar", "horizontal_bar"] and len(display_data) > 1:
                avg_value = display_data['MetricValue'].mean()
                
                if chart_type == "bar":
                    fig.add_hline(
                        y=avg_value,
                        line_dash="dash",
                        line_color="#FF6B6B",
                        line_width=3,
                        annotation_text=f"Average: {avg_value:.1f}",
                        annotation_position="top right"
                    )
                else:  # horizontal_bar
                    fig.add_vline(
                        x=avg_value,
                        line_dash="dash",
                        line_color="#FF6B6B",
                        line_width=3,
                        annotation_text=f"Average: {avg_value:.1f}",
                        annotation_position="top right"
                    )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': f"Instructor Performance Analysis: {metric_name}",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500 if chart_type != "horizontal_bar" else max(500, len(display_data) * 30),
                margin={'l': 60, 'r': 50, 't': 80, 'b': 120},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=False,
                hovermode='closest'
            )
            
            # print(f"📊 Created instructor performance chart: {chart_type} with {len(display_data)} instructors")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating instructor performance chart: {e}")
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Instructor Performance Analysis - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_performance("Instructor Performance Insights Generation")
    def generate_instructor_performance_insights(performance_data, performance_metric):
        """
        Generate automated insights from instructor performance data
        Always shows exactly 3 insights regardless of metric chosen
        ✅ REMOVED: min_classes parameter and related references
        """
        if performance_data.empty:
            return html.Div("No insights available - insufficient instructor performance data.", 
                          style={'color': 'gray'})
        
        try:
            insights = []
            
            metric_name = performance_data['MetricName'].iloc[0]
            total_instructors = len(performance_data)
            avg_metric = performance_data['MetricValue'].mean()
            
            # Top performer (always shown as first insight)
            top_performer = performance_data.iloc[0]
            top_name = top_performer['InstructorName']
            top_value = top_performer['MetricValue']
            
            insights.append(
                f"🏆 **Top Performer**: {top_name} leads with {top_value:.1f} {metric_name.lower()}"
            )
            
            # Metric-specific insights (choose 2 most relevant based on metric type)
            if performance_metric == "attendance_rate":
                # Insight 2: Excellence threshold
                excellent_rate = len(performance_data[performance_data['MetricValue'] >= 90])
                insights.append(
                    f"✅ **Excellence Rate**: {excellent_rate} of {total_instructors} instructors achieve 90%+ attendance rates"
                )
                
                # Insight 3: Performance distribution
                if len(performance_data) > 1:
                    top_quartile = performance_data['MetricValue'].quantile(0.75)
                    high_performers = len(performance_data[performance_data['MetricValue'] >= top_quartile])
                    insights.append(
                        f"📊 **High Performers**: {high_performers} instructors in top quartile (≥{top_quartile:.1f}% attendance)"
                    )
                else:
                    insights.append(f"📈 **Average Performance**: {avg_metric:.1f}% attendance rate across all instructors")
                    
            elif performance_metric == "total_students":
                # Insight 2: High impact threshold
                impactful_instructors = len(performance_data[performance_data['MetricValue'] >= 100])
                insights.append(
                    f"🌟 **High Impact**: {impactful_instructors} of {total_instructors} instructors have taught 100+ students"
                )
                
                # Insight 3: Total reach
                total_students_taught = performance_data['MetricValue'].sum()
                insights.append(
                    f"📈 **Total Reach**: {total_students_taught:,.0f} students taught collectively by all instructors"
                )
                
            elif performance_metric == "avg_class_size":
                # Insight 2: Optimal class size analysis
                optimal_size_instructors = len(performance_data[(performance_data['MetricValue'] >= 8) & (performance_data['MetricValue'] <= 15)])
                insights.append(
                    f"🎯 **Optimal Size**: {optimal_size_instructors} of {total_instructors} instructors maintain ideal class sizes (8-15 students)"
                )
                
                # Insight 3: Average comparison
                insights.append(
                    f"📊 **Average Class Size**: {avg_metric:.1f} students per class across all instructors"
                )
                
            elif performance_metric == "classes_conducted":
                # Insight 2: Experience levels
                experienced_instructors = len(performance_data[performance_data['MetricValue'] >= 20])
                insights.append(
                    f"🎓 **Experienced Instructors**: {experienced_instructors} of {total_instructors} instructors have conducted 20+ classes"
                )
                
                # Insight 3: Total activity
                total_classes = performance_data['MetricValue'].sum()
                insights.append(
                    f"📈 **Total Activity**: {total_classes:,.0f} classes conducted collectively by all instructors"
                )
                
            elif performance_metric == "sessions_per_month":
                # Insight 2: High activity threshold
                highly_active = len(performance_data[performance_data['MetricValue'] >= 4])
                insights.append(
                    f"⚡ **Highly Active**: {highly_active} of {total_instructors} instructors conduct 4+ sessions per month"
                )
                
                # Insight 3: Activity distribution
                if len(performance_data) > 1:
                    median_activity = performance_data['MetricValue'].median()
                    above_median = len(performance_data[performance_data['MetricValue'] >= median_activity])
                    insights.append(
                        f"📊 **Activity Distribution**: {above_median} instructors above median rate ({median_activity:.1f} sessions/month)"
                    )
                else:
                    insights.append(f"📈 **Average Activity**: {avg_metric:.1f} sessions per month across all instructors")
            
            else:
                # Fallback for unknown metrics (should not happen, but safety net)
                insights.extend([
                    f"📊 **Overview**: {total_instructors} instructors analyzed",
                    f"📈 **Average Performance**: {avg_metric:.1f} {metric_name.lower()} across all instructors"
                ])
            
            # Ensure we always have exactly 3 insights
            insights = insights[:3]
            
            # Create styled insight components
            insight_components = []
            for insight in insights:
                insight_components.append(
                    html.Div([
                        html.Span(insight, style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            
            return html.Div(insight_components, className="insights-container")
            
        except Exception as e:
            print(f"❌ Error generating instructor performance insights: {e}")
            return html.Div("Unable to generate insights due to data processing error.", 
                          style={'color': 'red'})

    @callback(
        [Output("instructor-performance-chart", "figure"),
         Output("instructor-performance-insights-summary", "children")],
        [Input("training-filtered-query-store", "data"),
         Input("instructor-performance-metric-dropdown", "value"),
         Input("instructor-chart-type-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Instructor Performance Analysis Update")
    def update_instructor_performance_analysis(query_selections, performance_metric, chart_type):
        """
        Update instructor performance analysis based on filter selections
        """
        try:
            # print(f"🔄 Updating instructor performance: metric={performance_metric}, chart={chart_type}")
            
            # Get base data
            base_data = get_instructor_performance_base_data()
            
            # Apply filters
            filtered_data = apply_instructor_performance_filters(base_data, query_selections)
            
            # Prepare performance data
            performance_data = prepare_instructor_performance_data(filtered_data, performance_metric)
            
            # Create visualization
            fig = create_instructor_performance_chart(performance_data, performance_metric, chart_type)
            
            # Generate insights
            insights = generate_instructor_performance_insights(performance_data, performance_metric)
            
            # print(f"✅ Instructor performance analysis updated successfully")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating instructor performance analysis: {e}")
            
            # Return error chart and message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading instructor performance data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Instructor Performance Analysis - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig, html.Div(f"Error generating insights: {str(e)}", style={'color': 'red'})

def register_training_instructor_performance_modal_callbacks(app):
    """
    Register callbacks for training instructor performance chart modal functionality
    """
    
    @monitor_chart_performance("Enlarged Instructor Performance Chart")
    def create_enlarged_instructor_performance_chart(original_figure):
        """
        Create an enlarged version of the instructor performance chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            # Create a deep copy of the original figure
            enlarged_fig = copy.deepcopy(original_figure)
            
            # Update layout for larger modal display
            enlarged_fig['layout'].update({
                'height': 600,  
                'margin': {'l': 120, 'r': 80, 't': 100, 'b': 140},  
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}  
                },
                'xaxis': {
                    **enlarged_fig['layout'].get('xaxis', {}),
                    'title': {
                        **enlarged_fig['layout'].get('xaxis', {}).get('title', {}),
                        'font': {'size': 14}
                    },
                    'tickfont': {'size': 12}  
                },
                'yaxis': {
                    **enlarged_fig['layout'].get('yaxis', {}),
                    'title': {
                        **enlarged_fig['layout'].get('yaxis', {}).get('title', {}),
                        'font': {'size': 14}
                    },
                    'tickfont': {'size': 12} 
                }
            })
            
            # Update traces for better visibility in larger chart
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') in ['bar', 'scatter']:
                        # Make chart elements more visible
                        if trace.get('type') == 'scatter':
                            trace.update({
                                'marker': {
                                    **trace.get('marker', {}),
                                    'size': 15  # Larger markers for scatter plots
                                }
                            })
                        # Bar charts will automatically scale with the larger size
            
            # Create the chart component
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True, 
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'instructor_performance_analysis_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged instructor performance chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )
            
    @callback(
        [Output("training-chart-modal", "is_open", allow_duplicate=True),
        Output("training-modal-chart-content", "children", allow_duplicate=True)],
        [Input("instructor-performance-chart-wrapper", "n_clicks")],
        [State("training-chart-modal", "is_open"),
        State("instructor-performance-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Instructor Performance Modal Toggle")
    def toggle_instructor_performance_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of instructor performance chart modal using SHARED modal
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "instructor-performance-chart-wrapper" and chart_wrapper_clicks and not is_open:
            
            if not chart_figure or not chart_figure.get('data'):
                return no_update, no_update
            
            enlarged_chart = create_enlarged_instructor_performance_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update

# print("✅ Training instructor performance callbacks registered")