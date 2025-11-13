from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_training_gap_analysis_callbacks(app):
    """
    Register registration vs attendance gap analysis callbacks
    Matches the component IDs from the layout file
    """
    
    @monitor_query_performance("Gap Analysis Base Data")
    def get_gap_analysis_base_data():
        """
        Fetch base data for registration vs attendance gap analysis
        Uses consumable fact tables with minimal joins
        """
        
        queries = {
            # Get detailed class attendance data for registration vs attendance analysis
            "class_attendance": """
                SELECT 
                    [AttendanceID],
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
                WHERE [RegisteredOn] IS NOT NULL
                AND [StartTime] IS NOT NULL
                AND [IsDeleted] != 'True'
            """,
            
            # Get training classes for additional context
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
                WHERE [StartTime] IS NOT NULL
                AND [IsDeleted] != 'True'
            """,
            
            # Get topic assignments to link classes to topics
            "topic_assignments": """
                SELECT 
                    [TrainingClassId],
                    [TrainingTopicId],
                    [TrainingTopicName],
                    [AorId],
                    [InstructorId],
                    [InstructorName],
                    [StartTime],
                    [EndTime]
                FROM [consumable].[Fact_TopicAssignments]
                WHERE [TrainingClassId] IS NOT NULL
                AND [TrainingTopicId] IS NOT NULL
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

    @monitor_performance("Gap Analysis Filter Application")
    def apply_gap_analysis_filters(base_data, query_selections):
        """
        Apply filters to base gap analysis data using pandas
        """
        if not query_selections:
            query_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_class_attendance = pd.DataFrame(base_data.get('class_attendance', [])).copy()
        df_training_classes = pd.DataFrame(base_data.get('training_classes', [])).copy()
        df_topics = pd.DataFrame(base_data.get('topic_assignments', [])).copy()
        df_aor_offices = pd.DataFrame(base_data.get('aor_offices', [])).copy()
        
        # print(f"📊 Starting gap analysis filtering: {len(df_class_attendance)} attendance records")
        
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
        
        # Parse dates from class attendance data
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
        
        # Apply AOR filter
        if aor_list:
            if not df_class_attendance.empty:
                df_class_attendance = df_class_attendance.loc[df_class_attendance['AorShortName'].isin(aor_list)].copy()
            if not df_topics.empty:
                # Filter topic assignments by AorId - need to map AorShortName to AorId
                aor_id_mapping = df_aor_offices.set_index('AorShortName')['AorID'].to_dict() if not df_aor_offices.empty else {}
                aor_ids = [aor_id_mapping.get(aor) for aor in aor_list if aor_id_mapping.get(aor)]
                if aor_ids:
                    df_topics = df_topics.loc[df_topics['AorId'].isin(aor_ids)].copy()
            # print(f"🎯 AOR filter applied: {len(df_class_attendance)} attendance records")
        
        # Apply Office filter (via AOR mapping)
        if office_list and not df_aor_offices.empty:
            office_aors = df_aor_offices.loc[df_aor_offices['OfficeCode'].isin(office_list), 'AorShortName'].unique()
            if len(office_aors) > 0 and not df_class_attendance.empty:
                df_class_attendance = df_class_attendance.loc[df_class_attendance['AorShortName'].isin(office_aors)].copy()
            # print(f"🏢 Office filter applied: {len(df_class_attendance)} attendance records")
        
        # Apply Topic filter
        if topic_list and not df_topics.empty:
            df_topics = df_topics.loc[df_topics['TrainingTopicId'].astype(str).isin(topic_list)].copy()
            # Filter attendance to only those with matching topics
            if not df_class_attendance.empty:
                matching_class_ids = df_topics['TrainingClassId'].unique()
                df_class_attendance = df_class_attendance.loc[df_class_attendance['TrainingClassId'].isin(matching_class_ids)].copy()
            # print(f"📚 Topic filter applied: {len(df_class_attendance)} attendance records")
        
        # Apply Instructor filter
        if instructor_list:
            if not df_class_attendance.empty:
                df_class_attendance = df_class_attendance.loc[df_class_attendance['InstructorId'].astype(str).isin(instructor_list)].copy()
            # print(f"👨‍🏫 Instructor filter applied: {len(df_class_attendance)} attendance records")
        
        # Apply Location filter
        if location_list and not df_class_attendance.empty:
            df_class_attendance = df_class_attendance.loc[df_class_attendance['LocationId'].astype(str).isin(location_list)].copy()
            # print(f"📍 Location filter applied: {len(df_class_attendance)} attendance records")
        
        return {
            "class_attendance": df_class_attendance,
            "training_classes": df_training_classes,
            "topic_assignments": df_topics,
            "aor_offices": df_aor_offices
        }

    @monitor_performance("Gap Analysis Data Preparation")
    def prepare_gap_analysis_data(filtered_data, analysis_level, sort_by):
        """
        Prepare gap analysis data comparing registrations vs attendances
        """
        df_class_attendance = filtered_data.get('class_attendance', pd.DataFrame())
        df_topics = filtered_data.get('topic_assignments', pd.DataFrame())
        
        if df_class_attendance.empty:
            return pd.DataFrame()
        
        try:
            # Calculate registration vs attendance metrics
            df_class_attendance = df_class_attendance.copy()
            
            # Add topic information if analyzing by topic
            if analysis_level == "topic" and not df_topics.empty:
                df_class_attendance = df_class_attendance.merge(
                    df_topics[['TrainingClassId', 'TrainingTopicName']], 
                    on='TrainingClassId', 
                    how='left'
                )
            
            # Group by the specified analysis level
            if analysis_level == "class":
                group_cols = ['TrainingClassId', 'ClassName']
                gap_data = df_class_attendance.groupby(group_cols).agg({
                    'AttendanceID': 'count',  # Total registrations
                    'WasPresent': lambda x: (x == 'True').sum()  # Total attendances
                }).reset_index()
                gap_data = gap_data.rename(columns={
                    'ClassName': 'CategoryName',
                    'AttendanceID': 'Registrations',
                    'WasPresent': 'Attendances'
                })
                
            elif analysis_level == "topic":
                if 'TrainingTopicName' in df_class_attendance.columns:
                    gap_data = df_class_attendance.groupby('TrainingTopicName').agg({
                        'AttendanceID': 'count',
                        'WasPresent': lambda x: (x == 'True').sum()
                    }).reset_index()
                    gap_data = gap_data.rename(columns={
                        'TrainingTopicName': 'CategoryName',
                        'AttendanceID': 'Registrations',
                        'WasPresent': 'Attendances'
                    })
                else:
                    # Fallback to class level if no topic data
                    gap_data = df_class_attendance.groupby(['TrainingClassId', 'ClassName']).agg({
                        'AttendanceID': 'count',
                        'WasPresent': lambda x: (x == 'True').sum()
                    }).reset_index()
                    gap_data = gap_data.rename(columns={
                        'ClassName': 'CategoryName',
                        'AttendanceID': 'Registrations',
                        'WasPresent': 'Attendances'
                    })
                    
            elif analysis_level == "instructor":
                gap_data = df_class_attendance.groupby('InstructorName').agg({
                    'AttendanceID': 'count',
                    'WasPresent': lambda x: (x == 'True').sum()
                }).reset_index()
                gap_data = gap_data.rename(columns={
                    'InstructorName': 'CategoryName',
                    'AttendanceID': 'Registrations',
                    'WasPresent': 'Attendances'
                })
                
            elif analysis_level == "location":
                gap_data = df_class_attendance.groupby('LocationName').agg({
                    'AttendanceID': 'count',
                    'WasPresent': lambda x: (x == 'True').sum()
                }).reset_index()
                gap_data = gap_data.rename(columns={
                    'LocationName': 'CategoryName',
                    'AttendanceID': 'Registrations',
                    'WasPresent': 'Attendances'
                })
                
            elif analysis_level == "aor":
                gap_data = df_class_attendance.groupby('AorShortName').agg({
                    'AttendanceID': 'count',
                    'WasPresent': lambda x: (x == 'True').sum()
                }).reset_index()
                gap_data = gap_data.rename(columns={
                    'AorShortName': 'CategoryName',
                    'AttendanceID': 'Registrations',
                    'WasPresent': 'Attendances'
                })
                
            else:
                # Default to class level
                gap_data = df_class_attendance.groupby(['TrainingClassId', 'ClassName']).agg({
                    'AttendanceID': 'count',
                    'WasPresent': lambda x: (x == 'True').sum()
                }).reset_index()
                gap_data = gap_data.rename(columns={
                    'ClassName': 'CategoryName',
                    'AttendanceID': 'Registrations',
                    'WasPresent': 'Attendances'
                })
            
            # Calculate gap metrics
            gap_data.loc[:, 'NoShows'] = gap_data['Registrations'] - gap_data['Attendances']
            gap_data.loc[:, 'AttendanceRate'] = (gap_data['Attendances'] / gap_data['Registrations'] * 100).fillna(0)
            gap_data.loc[:, 'GapPercent'] = (gap_data['NoShows'] / gap_data['Registrations'] * 100).fillna(0)
            
            # Add metadata
            gap_data.loc[:, 'AnalysisLevel'] = analysis_level
            
            # Apply sorting
            if sort_by == "gap_percent_desc":
                gap_data = gap_data.sort_values('GapPercent', ascending=False)
            elif sort_by == "gap_percent_asc":
                gap_data = gap_data.sort_values('GapPercent', ascending=True)
            elif sort_by == "registrations_desc":
                gap_data = gap_data.sort_values('Registrations', ascending=False)
            elif sort_by == "attendances_desc":
                gap_data = gap_data.sort_values('Attendances', ascending=False)
            else:
                gap_data = gap_data.sort_values('GapPercent', ascending=False)
            
            # print(f"📊 Prepared gap analysis data: {len(gap_data)} categories for {analysis_level} level")
            return gap_data
            
        except Exception as e:
            print(f"❌ Error preparing gap analysis data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @monitor_chart_performance("Registration vs Attendance Comparison Chart")
    def create_registration_attendance_comparison_chart(gap_data, analysis_level):
        """
        Create interactive registration vs attendance comparison chart
        """
        if gap_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No registration vs attendance data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Registration vs Attendance Comparison",
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
            # Limit to top 15 categories for readability
            display_data = gap_data.head(15).copy()
            
            # Create figure with grouped bars
            fig = go.Figure()
            
            # Add registrations bars
            fig.add_trace(go.Bar(
                name='Registrations',
                x=display_data['CategoryName'],
                y=display_data['Registrations'],
                marker_color='#3498db',
                hovertemplate="<b>%{x}</b><br>Registrations: %{y:,.0f}<extra></extra>"
            ))
            
            # Add attendances bars
            fig.add_trace(go.Bar(
                name='Attendances',
                x=display_data['CategoryName'],
                y=display_data['Attendances'],
                marker_color='#2ecc71',
                hovertemplate="<b>%{x}</b><br>Attendances: %{y:,.0f}<extra></extra>"
            ))
            
            # Add no-shows bars
            fig.add_trace(go.Bar(
                name='No-Shows',
                x=display_data['CategoryName'],
                y=display_data['NoShows'],
                marker_color='#e74c3c',
                hovertemplate="<b>%{x}</b><br>No-Shows: %{y:,.0f}<extra></extra>"
            ))
            
            # Create title based on analysis level
            level_labels = {
                "class": "Training Classes",
                "topic": "Topics",
                "instructor": "Instructors", 
                "location": "Locations",
                "aor": "AORs"
            }
            chart_title = f"Registration vs Attendance by {level_labels.get(analysis_level, 'Category')}"
            
            # Update layout
            fig.update_layout(
                title={
                    'text': chart_title,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': level_labels.get(analysis_level, 'Category'),
                    'tickangle': -45,
                    'showgrid': False,
                    'tickfont': {'size': 10}
                },
                yaxis={
                    'title': 'Count',
                    'showgrid': True,
                    'gridcolor': '#f0f0f0'
                },
                height=500,
                margin={'l': 60, 'r': 50, 't': 80, 'b': 120},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                barmode='group',
                hovermode='x unified'
            )
            
            # print(f"📊 Created registration vs attendance comparison chart with {len(display_data)} categories")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating registration vs attendance comparison chart: {e}")
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
                    'text': "Registration vs Attendance Comparison - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_chart_performance("Attendance Rate Gauge")
    def create_attendance_rate_gauge(gap_data):
        """
        Create attendance rate gauge chart
        """
        try:
            if gap_data.empty:
                overall_rate = 0
                total_registrations = 0
                total_attendances = 0
            else:
                total_registrations = gap_data['Registrations'].sum()
                total_attendances = gap_data['Attendances'].sum()
                overall_rate = (total_attendances / total_registrations * 100) if total_registrations > 0 else 0
            
            # Determine gauge color based on rate
            if overall_rate >= 85:
                gauge_color = "#2ecc71"  # Green
            elif overall_rate >= 70:
                gauge_color = "#f39c12"  # Orange
            else:
                gauge_color = "#e74c3c"  # Red
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=overall_rate,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Overall Attendance Rate", 'font': {'size': 16}},
                delta={'reference': 85, 'suffix': "%"},
                gauge={
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': gauge_color, 'thickness': 0.3},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': '#ffebee'},
                        {'range': [50, 70], 'color': '#fff3e0'},
                        {'range': [70, 85], 'color': '#f3e5f5'},
                        {'range': [85, 100], 'color': '#e8f5e8'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 85
                    }
                },
                number={'suffix': "%", 'font': {'size': 24}}
            ))
            
            fig.update_layout(
                height=400,
                margin={'l': 20, 'r': 20, 't': 60, 'b': 20},
                plot_bgcolor='white',
                paper_bgcolor='white',
                font={'color': "darkblue", 'family': "Arial"}
            )
            
            # print(f"📊 Created attendance rate gauge: {overall_rate:.1f}%")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating attendance rate gauge: {e}")
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=0,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Overall Attendance Rate - Error"}
            ))
            fig.update_layout(
                height=400,
                margin={'l': 20, 'r': 20, 't': 60, 'b': 20},
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_performance("Gap Analysis Insights Generation")
    def generate_gap_analysis_insights(gap_data, analysis_level):
        """
        Generate automated insights from gap analysis data
        Always shows exactly 3 insights
        """
        if gap_data.empty:
            return html.Div("No insights available - insufficient gap analysis data.", 
                          style={'color': 'gray'})
        
        try:
            insights = []
            
            # Calculate overall metrics
            total_registrations = gap_data['Registrations'].sum()
            total_attendances = gap_data['Attendances'].sum()
            total_no_shows = gap_data['NoShows'].sum()
            overall_attendance_rate = (total_attendances / total_registrations * 100) if total_registrations > 0 else 0
            avg_gap_percent = gap_data['GapPercent'].mean()
            
            # Insight 1: Overall performance
            insights.append(
                f"📊 **Overall Attendance**: {overall_attendance_rate:.1f}% attendance rate ({total_attendances:,} of {total_registrations:,} registered)"
            )
            
            # Insight 2: Worst performer (highest gap)
            if not gap_data.empty:
                worst_performer = gap_data.iloc[0]  # Already sorted by gap
                worst_name = worst_performer['CategoryName']
                worst_gap = worst_performer['GapPercent']
                
                level_labels = {
                    "class": "Class",
                    "topic": "Topic", 
                    "instructor": "Instructor",
                    "location": "Location",
                    "aor": "AOR"
                }
                entity_type = level_labels.get(analysis_level, "Entity")
                
                insights.append(
                    f"⚠️ **Highest Gap**: {worst_name} has {worst_gap:.1f}% no-show rate ({entity_type.lower()} with largest attendance gap)"
                )
            
            # Insight 3: Performance distribution or best performer
            if len(gap_data) > 1:
                # Find categories with excellent attendance (>90%)
                excellent_performers = len(gap_data[gap_data['AttendanceRate'] >= 90])
                if excellent_performers > 0:
                    insights.append(
                        f"⭐ **Excellence**: {excellent_performers} of {len(gap_data)} {analysis_level}s achieve 90%+ attendance rates"
                    )
                else:
                    # Show best performer if no excellent ones
                    best_performer = gap_data.loc[gap_data['AttendanceRate'].idxmax()]
                    best_name = best_performer['CategoryName']
                    best_rate = best_performer['AttendanceRate']
                    insights.append(
                        f"🏆 **Best Performer**: {best_name} leads with {best_rate:.1f}% attendance rate"
                    )
            else:
                insights.append(f"📈 **Average Gap**: {avg_gap_percent:.1f}% no-show rate across all categories")
            
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
            print(f"❌ Error generating gap analysis insights: {e}")
            return html.Div("Unable to generate insights due to data processing error.", 
                          style={'color': 'red'})

    @callback(
        [Output("registration-attendance-comparison-chart", "figure"),
         Output("attendance-rate-gauge", "figure"),
         Output("gap-analysis-insights-summary", "children")],
        [Input("training-filtered-query-store", "data"),
         Input("gap-analysis-level-dropdown", "value"),
         Input("gap-analysis-sort-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Gap Analysis Update")
    def update_gap_analysis(query_selections, analysis_level, sort_by):
        """
        Update gap analysis charts and insights based on filter selections
        """
        try:
            # print(f"🔄 Updating gap analysis: level={analysis_level}, sort={sort_by}")
            
            # Get base data
            base_data = get_gap_analysis_base_data()
            
            # Apply filters
            filtered_data = apply_gap_analysis_filters(base_data, query_selections)
            
            # Prepare gap analysis data
            gap_data = prepare_gap_analysis_data(filtered_data, analysis_level, sort_by)
            
            # Create visualizations
            comparison_fig = create_registration_attendance_comparison_chart(gap_data, analysis_level)
            gauge_fig = create_attendance_rate_gauge(gap_data)
            
            # Generate insights
            insights = generate_gap_analysis_insights(gap_data, analysis_level)
            
            # print(f"✅ Gap analysis updated successfully")
            return comparison_fig, gauge_fig, insights
            
        except Exception as e:
            print(f"❌ Error updating gap analysis: {e}")
            
            # Return error charts and message
            error_fig = go.Figure()
            error_fig.add_annotation(
                text=f"Error loading gap analysis data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            error_fig.update_layout(
                title={
                    'text': "Registration vs Attendance Analysis - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            error_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=0,
                title={'text': "Error Loading Data"}
            ))
            error_gauge.update_layout(height=400, plot_bgcolor='white', paper_bgcolor='white')
            
            return error_fig, error_gauge, html.Div(f"Error generating insights: {str(e)}", style={'color': 'red'})

def register_training_gap_analysis_modal_callbacks(app):
    """
    Register callbacks for training gap analysis chart modal functionality
    """
    
    @monitor_chart_performance("Enlarged Gap Analysis Chart")
    def create_enlarged_gap_analysis_chart(original_figure):
        """
        Create an enlarged version of the gap analysis chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            # Create a deep copy of the original figure
            enlarged_fig = copy.deepcopy(original_figure)
            
            # Update layout for larger modal display
            enlarged_fig['layout'].update({
                'height': 600,  
                'margin': {'l': 100, 'r': 80, 't': 100, 'b': 140},  
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
                },
                'legend': {
                    **enlarged_fig['layout'].get('legend', {}),
                    'font': {'size': 12}
                }
            })
            
            # Create the chart component
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True, 
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'registration_attendance_gap_analysis_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged gap analysis chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )
    
    @callback(
        [Output("training-chart-modal", "is_open", allow_duplicate=True),
        Output("training-modal-chart-content", "children", allow_duplicate=True)],
        [Input("registration-comparison-chart-wrapper", "n_clicks")],
        [State("training-chart-modal", "is_open"),
        State("registration-attendance-comparison-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Gap Analysis Modal Toggle")
    def toggle_gap_analysis_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of gap analysis chart modal using SHARED modal
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "registration-comparison-chart-wrapper" and chart_wrapper_clicks and not is_open:
            
            if not chart_figure or not chart_figure.get('data'):
                return no_update, no_update
            
            enlarged_chart = create_enlarged_gap_analysis_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update

# print("✅ Training gap analysis callbacks registered")