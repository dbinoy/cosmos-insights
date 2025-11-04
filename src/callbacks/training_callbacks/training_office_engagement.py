from dash import callback, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
from functools import wraps

def monitor_performance(func_name="Unknown"):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                print(f"⏱️ {func_name} completed in {duration:.2f} seconds")
                return result
            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ {func_name} failed after {duration:.2f} seconds: {str(e)}")
                raise
        return wrapper
    return decorator

def register_training_office_engagement_callbacks(app):
    """
    Register office engagement trend callbacks
    """

    def get_office_engagement_base_data():
        """
        Fetch base data for office engagement trend analysis
        Uses consumable fact tables with minimal joins
        """
        
        queries = {
            # Get attendance data with time series info
            "attendance_data": """
                SELECT 
                    [AorShortName],
                    [MemberOffice],
                    [TrainingClassId],
                    [TrainingTopicId],
                    [TrainingTopicName],
                    [LocationId],
                    [InstructorId],
                    [MembersAttended],
                    [TotalAttendances],
                    [StartTime]
                FROM [consumable].[Fact_AttendanceStats]
                WHERE [MemberOffice] IS NOT NULL
                AND [AorShortName] IS NOT NULL
                AND [StartTime] IS NOT NULL
            """,
            
            # Get member engagement data for unique counts and rates
            "member_engagement": """
                SELECT 
                    [MemberID],
                    [AorShortName],
                    [OfficeCode],
                    [MemberStatus],
                    [TotalSessionsRegistered],
                    [TotalSessionsAttended],
                    [AttendanceRate]
                FROM [consumable].[Fact_MemberEngagement]
                WHERE [OfficeCode] IS NOT NULL
                AND [AorShortName] IS NOT NULL
                AND [MemberStatus] = 'Active'
            """,
            
            # Get AOR-Office mapping
            "aor_offices": """
                SELECT DISTINCT 
                    [AorShortName],
                    [OfficeCode],
                    [AorName]
                FROM [consumable].[Dim_Aors]
                WHERE [OfficeCode] IS NOT NULL
                AND [AorShortName] IS NOT NULL
            """,
            
            # Get date dimension for proper time series
            "date_info": """
                SELECT DISTINCT
                    [DateKey],
                    [YearNumber],
                    [QuarterNumber],
                    [MonthNumber],
                    [MonthName],
                    [WeekNumber]
                FROM [consumable].[Dim_Date]
                WHERE [DateKey] >= '2020-01-01'
                ORDER BY [DateKey]
            """
        }
        
        return run_queries(queries, len(queries))

    def parse_custom_datetime(date_str):
        """
        Parse custom datetime format: 'Feb-04-25@6 PM' -> datetime object
        Same parsing logic as in training_summary_cards.py
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

    def apply_office_engagement_filters(base_data, query_selections):
        """
        Apply filters to base office engagement data using pandas
        """
        if not query_selections:
            query_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_attendance = pd.DataFrame(base_data.get('attendance_data', [])).copy()
        df_members = pd.DataFrame(base_data.get('member_engagement', [])).copy()
        df_aor_offices = pd.DataFrame(base_data.get('aor_offices', [])).copy()
        
        print(f"📊 Starting office engagement filtering: {len(df_attendance)} attendance records, {len(df_members)} member records")
        
        # Parse filter values (same logic as training_summary_cards.py)
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
        
        # Parse dates from attendance data
        if not df_attendance.empty and 'StartTime' in df_attendance.columns:
            df_attendance = df_attendance.copy()
            df_attendance.loc[:, 'ParsedStartTime'] = df_attendance['StartTime'].apply(parse_custom_datetime)
            df_attendance = df_attendance.dropna(subset=['ParsedStartTime']).copy()
            
            # Apply date range filter if specified
            start_date = query_selections.get('Day_From')
            end_date = query_selections.get('Day_To')
            
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df_attendance = df_attendance.loc[
                        (df_attendance['ParsedStartTime'] >= start_dt) & 
                        (df_attendance['ParsedStartTime'] <= end_dt)
                    ].copy()
                    print(f"📅 Date filter applied: {len(df_attendance)} attendance records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Apply AOR filter
        if aor_list:
            if not df_attendance.empty:
                df_attendance = df_attendance.loc[df_attendance['AorShortName'].isin(aor_list)].copy()
            if not df_members.empty:
                df_members = df_members.loc[df_members['AorShortName'].isin(aor_list)].copy()
            print(f"🎯 AOR filter applied: {len(df_attendance)} attendance, {len(df_members)} members")
        
        # Apply Office filter
        if office_list:
            if not df_attendance.empty:
                df_attendance = df_attendance.loc[df_attendance['MemberOffice'].isin(office_list)].copy()
            if not df_members.empty:
                df_members = df_members.loc[df_members['OfficeCode'].isin(office_list)].copy()
            print(f"🏢 Office filter applied: {len(df_attendance)} attendance, {len(df_members)} members")
        
        # Apply Topic filter
        if topic_list and not df_attendance.empty and 'TrainingTopicId' in df_attendance.columns:
            df_attendance = df_attendance.loc[df_attendance['TrainingTopicId'].astype(str).isin(topic_list)].copy()
            print(f"📚 Topic filter applied: {len(df_attendance)} attendance records")
        
        # Apply Instructor filter
        if instructor_list and not df_attendance.empty and 'InstructorId' in df_attendance.columns:
            df_attendance = df_attendance.loc[df_attendance['InstructorId'].astype(str).isin(instructor_list)].copy()
            print(f"👨‍🏫 Instructor filter applied: {len(df_attendance)} attendance records")
        
        # Apply Location filter
        if location_list and not df_attendance.empty and 'LocationId' in df_attendance.columns:
            df_attendance = df_attendance.loc[df_attendance['LocationId'].astype(str).isin(location_list)].copy()
            print(f"📍 Location filter applied: {len(df_attendance)} attendance records")
        
        return {
            "attendance_data": df_attendance,
            "member_engagement": df_members,
            "aor_offices": df_aor_offices
        }

    def prepare_time_series_data(filtered_data, grouping_level, time_granularity, metric_type):
        """
        Prepare time series data for trend analysis
        """
        df_attendance = filtered_data.get('attendance_data', pd.DataFrame())
        df_members = filtered_data.get('member_engagement', pd.DataFrame())
        df_aor_offices = filtered_data.get('aor_offices', pd.DataFrame())
        
        if df_attendance.empty:
            return pd.DataFrame()
        
        try:
            # Create time period columns
            df_attendance = df_attendance.copy()
            df_attendance.loc[:, 'YearNumber'] = df_attendance['ParsedStartTime'].dt.year
            df_attendance.loc[:, 'MonthNumber'] = df_attendance['ParsedStartTime'].dt.month
            df_attendance.loc[:, 'QuarterNumber'] = df_attendance['ParsedStartTime'].dt.quarter
            
            # Create time period labels
            if time_granularity == "monthly":
                df_attendance.loc[:, 'TimePeriod'] = df_attendance['ParsedStartTime'].dt.to_period('M')
                df_attendance.loc[:, 'TimeLabel'] = df_attendance['ParsedStartTime'].dt.strftime('%Y-%m')
            elif time_granularity == "quarterly":
                df_attendance.loc[:, 'TimePeriod'] = df_attendance['ParsedStartTime'].dt.to_period('Q')
                df_attendance.loc[:, 'TimeLabel'] = df_attendance.apply(
                    lambda x: f"{x['YearNumber']}-Q{x['QuarterNumber']}", axis=1
                )
            else:  # yearly
                df_attendance.loc[:, 'TimePeriod'] = df_attendance['ParsedStartTime'].dt.to_period('Y')
                df_attendance.loc[:, 'TimeLabel'] = df_attendance['YearNumber'].astype(str)
            
            # Determine grouping column
            if grouping_level == "aor":
                group_col = 'AorShortName'
                group_label = 'AOR'
            else:  # office or top performers
                group_col = 'MemberOffice'
                group_label = 'Office'
                # Create office labels
                df_attendance.loc[:, 'OfficeLabel'] = df_attendance.apply(
                    lambda row: f"{row['AorShortName']}-{row['MemberOffice']}", axis=1
                )
                if grouping_level == "office":
                    group_col = 'OfficeLabel'
            
            # Calculate metrics by time period and group
            if metric_type == "total_attendances":
                time_series = df_attendance.groupby(['TimeLabel', group_col]).agg({
                    'TotalAttendances': 'sum'
                }).reset_index()
                time_series = time_series.rename(columns={'TotalAttendances': 'MetricValue'})
                metric_name = 'Total Attendances'
                
            elif metric_type == "unique_members":
                time_series = df_attendance.groupby(['TimeLabel', group_col]).agg({
                    'MembersAttended': 'sum'
                }).reset_index()
                time_series = time_series.rename(columns={'MembersAttended': 'MetricValue'})
                metric_name = 'Unique Members Trained'
                
            elif metric_type == "classes_per_member":
                # Calculate classes per member from member engagement data
                if not df_members.empty:
                    member_summary = df_members.groupby(['AorShortName', 'OfficeCode']).agg({
                        'TotalSessionsAttended': 'mean'
                    }).reset_index()
                    
                    # Create a simplified time series (since member data may not have time dimension)
                    time_series = member_summary.copy()
                    time_series.loc[:, 'TimeLabel'] = 'Overall'  # Single time point
                    
                    if grouping_level == "aor":
                        time_series = time_series.groupby(['TimeLabel', 'AorShortName']).agg({
                            'TotalSessionsAttended': 'mean'
                        }).reset_index()
                        time_series = time_series.rename(columns={'AorShortName': group_col})
                    else:
                        time_series.loc[:, 'OfficeLabel'] = time_series.apply(
                            lambda row: f"{row['AorShortName']}-{row['OfficeCode']}", axis=1
                        )
                        time_series = time_series.rename(columns={'OfficeCode': 'MemberOffice'})
                        if grouping_level == "office":
                            group_col = 'OfficeLabel'
                    
                    time_series = time_series.rename(columns={'TotalSessionsAttended': 'MetricValue'})
                    metric_name = 'Classes per Member'
                else:
                    return pd.DataFrame()
                    
            else:  # avg_attendance_rate
                if not df_members.empty:
                    member_summary = df_members.groupby(['AorShortName', 'OfficeCode']).agg({
                        'AttendanceRate': 'mean'
                    }).reset_index()
                    
                    time_series = member_summary.copy()
                    time_series.loc[:, 'TimeLabel'] = 'Overall'
                    
                    if grouping_level == "aor":
                        time_series = time_series.groupby(['TimeLabel', 'AorShortName']).agg({
                            'AttendanceRate': 'mean'
                        }).reset_index()
                        time_series = time_series.rename(columns={'AorShortName': group_col})
                    else:
                        time_series.loc[:, 'OfficeLabel'] = time_series.apply(
                            lambda row: f"{row['AorShortName']}-{row['OfficeCode']}", axis=1
                        )
                        if grouping_level == "office":
                            group_col = 'OfficeLabel'
                    
                    time_series = time_series.rename(columns={'AttendanceRate': 'MetricValue'})
                    time_series.loc[:, 'MetricValue'] = time_series['MetricValue'] * 100  # Convert to percentage
                    metric_name = 'Average Attendance Rate (%)'
                else:
                    return pd.DataFrame()
            
            # Handle top/bottom performers
            if grouping_level in ["top10", "bottom10"]:
                # Calculate total metric value per group
                group_totals = time_series.groupby(group_col).agg({
                    'MetricValue': 'sum'
                }).reset_index().sort_values('MetricValue', ascending=(grouping_level == "bottom10"))
                
                # Take top/bottom 10
                top_groups = group_totals.head(10)[group_col].tolist()
                time_series = time_series.loc[time_series[group_col].isin(top_groups)].copy()
            
            # Add metadata
            time_series.loc[:, 'MetricName'] = metric_name
            time_series.loc[:, 'GroupLevel'] = group_label
            
            print(f"📊 Prepared time series: {len(time_series)} records, {metric_name}")
            return time_series
            
        except Exception as e:
            print(f"❌ Error preparing time series data: {e}")
            return pd.DataFrame()

    def create_engagement_trend_chart(time_series_data, grouping_level, metric_type, show_benchmarks):
        """
        Create interactive trend line chart
        """
        if time_series_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for selected filters and time period",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title="Training Engagement Trends",
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                height=500
            )
            return fig
        
        try:
            # Determine group column
            if grouping_level == "aor":
                group_col = 'AorShortName'
            elif grouping_level in ["top10", "bottom10"]:
                group_col = 'OfficeLabel' if 'OfficeLabel' in time_series_data.columns else 'MemberOffice'
            else:  # office
                group_col = 'OfficeLabel' if 'OfficeLabel' in time_series_data.columns else 'MemberOffice'
            
            metric_name = time_series_data['MetricName'].iloc[0] if not time_series_data.empty else metric_type
            
            # Create multi-line trend chart
            fig = px.line(
                time_series_data,
                x='TimeLabel',
                y='MetricValue',
                color=group_col,
                title=f"Training Engagement Trends: {metric_name}",
                markers=True
            )
            
            # Add benchmark lines if requested
            if show_benchmarks in ["average", "both"] and len(time_series_data) > 1:
                avg_value = time_series_data['MetricValue'].mean()
                fig.add_hline(
                    y=avg_value,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Average: {avg_value:.1f}"
                )
            
            if show_benchmarks in ["target", "both"]:
                # Add target line (example: 80% of max value)
                target_value = time_series_data['MetricValue'].max() * 0.8
                fig.add_hline(
                    y=target_value,
                    line_dash="dot",
                    line_color="green",
                    annotation_text=f"Target: {target_value:.1f}"
                )
            
            # Update layout
            fig.update_layout(
                height=500,
                margin=dict(l=50, r=50, t=80, b=50),
                xaxis_title="Time Period",
                yaxis_title=metric_name,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                hovermode='x unified'
            )
            
            # Format hover template
            if metric_type == "avg_attendance_rate":
                hover_template = "%{fullData.name}<br>Time: %{x}<br>" + metric_name + ": %{y:.1f}%<extra></extra>"
            elif metric_type == "classes_per_member":
                hover_template = "%{fullData.name}<br>Time: %{x}<br>" + metric_name + ": %{y:.1f}<extra></extra>"
            else:
                hover_template = "%{fullData.name}<br>Time: %{x}<br>" + metric_name + ": %{y:,.0f}<extra></extra>"
            
            fig.update_traces(hovertemplate=hover_template)
            
            print(f"📊 Created trend chart with {len(time_series_data[group_col].unique())} trend lines")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating trend chart: {e}")
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title="Training Engagement Trends - Error",
                height=500
            )
            return fig

    def generate_engagement_insights(time_series_data, grouping_level, metric_type):
        """
        Generate automated insights from trend data
        """
        if time_series_data.empty:
            return "No insights available - insufficient data."
        
        try:
            insights = []
            
            # Determine group column
            if grouping_level == "aor":
                group_col = 'AorShortName'
                entity_type = "AOR"
            else:
                group_col = 'OfficeLabel' if 'OfficeLabel' in time_series_data.columns else 'MemberOffice'
                entity_type = "Office"
            
            # Calculate overall statistics
            total_entities = time_series_data[group_col].nunique()
            avg_metric = time_series_data['MetricValue'].mean()
            metric_name = time_series_data['MetricName'].iloc[0]
            
            # Top performer
            top_performer = time_series_data.groupby(group_col)['MetricValue'].mean().idxmax()
            top_value = time_series_data.groupby(group_col)['MetricValue'].mean().max()
            
            # Growth analysis (if multiple time periods)
            time_periods = time_series_data['TimeLabel'].nunique()
            if time_periods > 1:
                # Calculate trend for each entity
                trends = []
                for entity in time_series_data[group_col].unique():
                    entity_data = time_series_data[time_series_data[group_col] == entity].sort_values('TimeLabel')
                    if len(entity_data) > 1:
                        first_val = entity_data['MetricValue'].iloc[0]
                        last_val = entity_data['MetricValue'].iloc[-1]
                        if first_val > 0:
                            growth_rate = ((last_val - first_val) / first_val) * 100
                            trends.append({'entity': entity, 'growth': growth_rate, 'latest': last_val})
                
                if trends:
                    trends_df = pd.DataFrame(trends)
                    fastest_growing = trends_df.loc[trends_df['growth'].idxmax()]
                    
                    insights.extend([
                        f"📊 **Performance Overview**: {total_entities} {entity_type}s tracked with average {metric_name.lower()} of {avg_metric:.1f}",
                        f"🏆 **Top Performer**: {top_performer} leads with {top_value:.1f} {metric_name.lower()}",
                        f"📈 **Fastest Growing**: {fastest_growing['entity']} shows {fastest_growing['growth']:.1f}% growth"
                    ])
            else:
                insights.extend([
                    f"📊 **Current Performance**: {total_entities} {entity_type}s with average {metric_name.lower()} of {avg_metric:.1f}",
                    f"🏆 **Top Performer**: {top_performer} leads with {top_value:.1f} {metric_name.lower()}"
                ])
            
            return " | ".join(insights)
            
        except Exception as e:
            print(f"❌ Error generating insights: {e}")
            return "Unable to generate insights due to data processing error."

    # Main callback for engagement trends
    @callback(
        [Output("engagement-trends-chart", "figure"),
         Output("engagement-insights-summary", "children")],
        [Input("training-filtered-query-store", "data"),
         Input("engagement-grouping-dropdown", "value"),
         Input("engagement-time-granularity-dropdown", "value"),
         Input("office-engagement-metric-dropdown", "value"),
         Input("engagement-benchmark-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Office Engagement Trends Update")
    def update_office_engagement_trends(query_selections, grouping_level, time_granularity, metric_type, show_benchmarks):
        """
        Update office engagement trends chart based on filter selections
        """
        try:
            print(f"🔄 Updating engagement trends: grouping={grouping_level}, granularity={time_granularity}, metric={metric_type}")
            
            # Get base data
            base_data = get_office_engagement_base_data()
            
            # Apply filters
            filtered_data = apply_office_engagement_filters(base_data, query_selections)
            
            # Prepare time series data
            time_series_data = prepare_time_series_data(filtered_data, grouping_level, time_granularity, metric_type)
            
            # Create visualization
            fig = create_engagement_trend_chart(time_series_data, grouping_level, metric_type, show_benchmarks)
            
            # Generate insights
            insights = generate_engagement_insights(time_series_data, grouping_level, metric_type)
            
            print(f"✅ Office engagement trends updated successfully")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating office engagement trends: {e}")
            
            # Return error chart and message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading engagement trend data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title="Training Engagement Trends - Error",
                height=500
            )
            return fig, f"Error generating insights: {str(e)}"

    print("✅ Training office engagement trend callbacks registered")