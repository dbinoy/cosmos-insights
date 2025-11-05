from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_training_office_engagement_callbacks(app):
    """
    Register office engagement trend callbacks
    Matches the component IDs from the layout file
    """
    @monitor_query_performance("Office Engagement Base Data")
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
                    [AttendanceRate],
                    [LastRegisteredOn],
                    [LastConfirmedOn]
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
                    [WeekNumber],
                    [DayName],
                    [DayOfWeek],
                    [DayOfMonth],
                    [DayOfYear]
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

    @monitor_performance("Office Engagement Filter Application")
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
        
        # print(f"📊 Starting office engagement filtering: {len(df_attendance)} attendance records, {len(df_members)} member records")
        
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
            
            # Check if StartTime needs custom parsing or is already datetime
            if df_attendance['StartTime'].dtype == 'object':
                # Use custom parsing for format like 'Feb-04-25@6 PM'
                df_attendance.loc[:, 'ParsedStartTime'] = df_attendance['StartTime'].apply(parse_custom_datetime)
            else:
                # StartTime is already datetime2, use directly
                df_attendance.loc[:, 'ParsedStartTime'] = pd.to_datetime(df_attendance['StartTime'])
            
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
                    # print(f"📅 Date filter applied: {len(df_attendance)} attendance records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Apply AOR filter
        if aor_list:
            if not df_attendance.empty:
                df_attendance = df_attendance.loc[df_attendance['AorShortName'].isin(aor_list)].copy()
            if not df_members.empty:
                df_members = df_members.loc[df_members['AorShortName'].isin(aor_list)].copy()
            # print(f"🎯 AOR filter applied: {len(df_attendance)} attendance, {len(df_members)} members")
        
        # Apply Office filter
        if office_list:
            if not df_attendance.empty:
                df_attendance = df_attendance.loc[df_attendance['MemberOffice'].isin(office_list)].copy()
            if not df_members.empty:
                df_members = df_members.loc[df_members['OfficeCode'].isin(office_list)].copy()
            # print(f"🏢 Office filter applied: {len(df_attendance)} attendance, {len(df_members)} members")
        
        # Apply Topic filter
        if topic_list and not df_attendance.empty and 'TrainingTopicId' in df_attendance.columns:
            df_attendance = df_attendance.loc[df_attendance['TrainingTopicId'].astype(str).isin(topic_list)].copy()
            # print(f"📚 Topic filter applied: {len(df_attendance)} attendance records")
        
        # Apply Instructor filter
        if instructor_list and not df_attendance.empty and 'InstructorId' in df_attendance.columns:
            df_attendance = df_attendance.loc[df_attendance['InstructorId'].astype(str).isin(instructor_list)].copy()
            # print(f"👨‍🏫 Instructor filter applied: {len(df_attendance)} attendance records")
        
        # Apply Location filter
        if location_list and not df_attendance.empty and 'LocationId' in df_attendance.columns:
            df_attendance = df_attendance.loc[df_attendance['LocationId'].astype(str).isin(location_list)].copy()
            # print(f"📍 Location filter applied: {len(df_attendance)} attendance records")
        
        return {
            "attendance_data": df_attendance,
            "member_engagement": df_members,
            "aor_offices": df_aor_offices
        }

    @monitor_performance("Time Series Data Preparation")
    def prepare_time_series_data(filtered_data, grouping_level, time_granularity, metric_type):
        """
        Prepare time series data for trend analysis
        Updated to handle sessions_held metric and removed problematic metrics
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
            
            # Updated grouping logic to handle top3, top5, top10
            if grouping_level == "aor":
                group_col = 'AorShortName'
                group_label = 'AOR'
            else:  # office or top performers (top3, top5, top10)
                group_col = 'MemberOffice'
                group_label = 'Office'
                # Create office labels for better identification
                df_attendance.loc[:, 'OfficeLabel'] = df_attendance.apply(
                    lambda row: f"{row['AorShortName']}-{row['MemberOffice']}", axis=1
                )
                if grouping_level in ["office", "top3", "top5", "top10"]:
                    group_col = 'OfficeLabel'
            
            # ✅ Updated metric calculations - removed problematic metrics, added sessions_held
            if metric_type == "sessions_held":
                time_series = df_attendance.groupby(['TimeLabel', group_col]).agg({
                    'TrainingClassId': 'nunique'  # Count unique training sessions/classes
                }).reset_index()
                time_series = time_series.rename(columns={'TrainingClassId': 'MetricValue'})
                metric_name = 'Training Sessions Held'
                
            elif metric_type == "total_attendances":
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
                metric_name = 'Members Trained'
                
            else:
                # Fallback to sessions_held if unknown metric type
                time_series = df_attendance.groupby(['TimeLabel', group_col]).agg({
                    'TrainingClassId': 'nunique'
                }).reset_index()
                time_series = time_series.rename(columns={'TrainingClassId': 'MetricValue'})
                metric_name = 'Training Sessions Held'
            
            # Updated top performers logic to handle top3, top5, top10
            if grouping_level in ["top3", "top5", "top10"]:
                # Extract the number from the grouping level
                top_count = int(grouping_level.replace("top", ""))
                
                # Calculate total metric value per group
                group_totals = time_series.groupby(group_col).agg({
                    'MetricValue': 'sum'
                }).reset_index().sort_values('MetricValue', ascending=False)
                
                # Take top N performers
                top_groups = group_totals.head(top_count)[group_col].tolist()
                time_series = time_series.loc[time_series[group_col].isin(top_groups)].copy()
                
                # print(f"📊 Filtered to top {top_count} performers: {top_groups}")
            
            # Add metadata
            time_series.loc[:, 'MetricName'] = metric_name
            time_series.loc[:, 'GroupLevel'] = group_label

            # print(f"📊 Prepared time series: {len(time_series)} records, {metric_name}")
            return time_series
            
        except Exception as e:
            print(f"❌ Error preparing time series data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @monitor_chart_performance("Engagement Trend Chart")
    def create_engagement_trend_chart(time_series_data, grouping_level, metric_type):
        """
        Create interactive trend line chart using plotly.graph_objects
        Always displays average line overlay
        Updated to handle new metric types and removed problematic ones
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
                title={
                    'text': "Training Engagement Trends",
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
            # Updated group column logic to handle top3, top5, top10
            if grouping_level == "aor":
                group_col = 'AorShortName'
            else:  # office or top performers (top3, top5, top10)
                group_col = 'OfficeLabel' if 'OfficeLabel' in time_series_data.columns else 'MemberOffice'
            
            metric_name = time_series_data['MetricName'].iloc[0] if not time_series_data.empty else metric_type
            
            # Create dynamic title based on grouping level
            if grouping_level in ["top3", "top5", "top10"]:
                top_count = grouping_level.replace("top", "")
                chart_title = f"Training Engagement Trends: {metric_name} (Top {top_count} Performers)"
            elif grouping_level == "aor":
                chart_title = f"Training Engagement Trends: {metric_name} (By AOR)"
            else:
                chart_title = f"Training Engagement Trends: {metric_name} (By Office)"
            
            # Create figure
            fig = go.Figure()
            
            # Get unique groups for color assignment
            unique_groups = time_series_data[group_col].unique()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            # Add trend lines for each group
            for i, group in enumerate(unique_groups):
                group_data = time_series_data[time_series_data[group_col] == group].sort_values('TimeLabel')
                
                # ✅ Updated hover template - simplified for the 3 remaining metrics
                if metric_type == "sessions_held":
                    hover_template = f"<b>{group}</b><br>Time: %{{x}}<br>{metric_name}: %{{y:,.0f}}<extra></extra>"
                elif metric_type == "unique_members":
                    hover_template = f"<b>{group}</b><br>Time: %{{x}}<br>{metric_name}: %{{y:,.0f}}<extra></extra>"
                else:  # total_attendances
                    hover_template = f"<b>{group}</b><br>Time: %{{x}}<br>{metric_name}: %{{y:,.0f}}<extra></extra>"
                
                fig.add_trace(go.Scatter(
                    x=group_data['TimeLabel'],
                    y=group_data['MetricValue'],
                    mode='lines+markers',
                    name=str(group),
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6),
                    hovertemplate=hover_template
                ))
            
            # Always add average line
            if len(time_series_data) > 1:
                avg_value = time_series_data['MetricValue'].mean()
                fig.add_hline(
                    y=avg_value,
                    line_dash="dash",
                    line_color="#FF6B6B",
                    line_width=3,
                    annotation_text=f"Average: {avg_value:.1f}",
                    annotation_position="top right",
                    annotation_font=dict(size=12, color="#FF6B6B")
                )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': chart_title,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': 'Time Period',
                    'showgrid': False,
                    'tickfont': {'size': 10}
                },
                yaxis={
                    'title': metric_name,
                    'showgrid': True,
                    'gridcolor': '#f0f0f0'
                },
                height=500,
                margin={'l': 60, 'r': 50, 't': 80, 'b': 100},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                hovermode='x unified'
            )
            
            # print(f"📊 Created trend chart with {len(unique_groups)} trend lines and average line")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating trend chart: {e}")
            # Return proper error figure
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
                    'text': "Training Engagement Trends - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_performance("Office Engagement Insights Generation")
    def generate_engagement_insights(time_series_data, grouping_level, metric_type):
        """
        Generate automated insights from trend data
        Updated to handle top3, top5, top10 grouping levels
        """
        if time_series_data.empty:
            return "No insights available - insufficient data."
        
        try:
            insights = []
            
            # ✅ Updated group column logic to handle top3, top5, top10
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
            
            # ✅ Enhanced insights for top performers
            if grouping_level in ["top3", "top5", "top10"]:
                top_count = grouping_level.replace("top", "")
                overview_text = f"Top {top_count} {entity_type}s"
            elif grouping_level == "aor":
                overview_text = f"{total_entities} {entity_type}s"
            else:
                overview_text = f"{total_entities} {entity_type}s"
            
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
                        f"📊 **Performance Overview**: {overview_text} tracked with average {metric_name.lower()} of {avg_metric:.1f}",
                        f"🏆 **Top Performer**: {top_performer} leads with {top_value:.1f} {metric_name.lower()}",
                        f"📈 **Fastest Growing**: {fastest_growing['entity']} shows {fastest_growing['growth']:.1f}% growth"
                    ])
            else:
                insights.extend([
                    f"📊 **Current Performance**: {overview_text} with average {metric_name.lower()} of {avg_metric:.1f}",
                    f"🏆 **Top Performer**: {top_performer} leads with {top_value:.1f} {metric_name.lower()}"
                ])
            
            # return " | ".join(insights)
            # Create styled insight cards
            insight_components = []
            for insight in insights:
                insight_components.append(
                    html.Div([
                        html.Span(insight, style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            
            return html.Div(insight_components, className="insights-container")            
            
        except Exception as e:
            print(f"❌ Error generating insights: {e}")
            return "Unable to generate insights due to data processing error."

    @callback(
        [Output("engagement-trends-chart", "figure"),
         Output("engagement-insights-summary", "children")],
        [Input("training-filtered-query-store", "data"),
         Input("engagement-grouping-dropdown", "value"),
         Input("engagement-time-granularity-dropdown", "value"),
         Input("office-engagement-metric-dropdown", "value")],
        prevent_initial_call=False
    )
    # @monitor_performance("Office Engagement Trends Update")
    def update_office_engagement_trends(query_selections, grouping_level, time_granularity, metric_type):
        """
        Update office engagement trends chart based on filter selections
        Always displays average line - no benchmarks dropdown needed
        Updated to handle top3, top5, top10 grouping levels with top3 as default
        """
        try:
            # print(f"🔄 Updating engagement trends: grouping={grouping_level}, granularity={time_granularity}, metric={metric_type}")
            
            # Get base data
            base_data = get_office_engagement_base_data()
            
            # Apply filters
            filtered_data = apply_office_engagement_filters(base_data, query_selections)
            
            # Prepare time series data
            time_series_data = prepare_time_series_data(filtered_data, grouping_level, time_granularity, metric_type)
            
            # Create visualization - now handles top3, top5, top10
            fig = create_engagement_trend_chart(time_series_data, grouping_level, metric_type)
            
            # Generate insights
            insights = generate_engagement_insights(time_series_data, grouping_level, metric_type)
            
            # print(f"✅ Office engagement trends updated successfully with average line (showing {grouping_level})")
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
                title={
                    'text': "Training Engagement Trends - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig, f"Error generating insights: {str(e)}"

    # print("✅ Training office engagement trend callbacks registered")

def register_training_office_engagement_modal_callbacks(app):
    """
    Register callbacks for training office engagement chart modal functionality
    """
    # print("Registering Training Office Engagement Chart Modal callbacks...")
    
    @monitor_chart_performance("Enlarged Engagement Chart")
    def create_enlarged_engagement_chart(original_figure):
        """
        Create an enlarged version of the engagement trends chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            # Create a deep copy of the original figure
            enlarged_fig = copy.deepcopy(original_figure)
            
            # Update layout for larger modal display
            enlarged_fig['layout'].update({
                'height': 600,  
                'margin': {'l': 100, 'r': 80, 't': 100, 'b': 120},  
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
            
            # Update traces for better visibility in larger chart
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') == 'scatter':
                        # Make line chart elements more visible
                        trace.update({
                            'line': {
                                **trace.get('line', {}),
                                'width': 3  # Thicker lines
                            },
                            'marker': {
                                **trace.get('marker', {}),
                                'size': 8  # Larger markers
                            }
                        })
            
            # Update average line annotation if present
            if 'shapes' in enlarged_fig['layout']:
                for shape in enlarged_fig['layout']['shapes']:
                    if shape.get('type') == 'line':
                        shape.update({'line': {'width': 4}})  # Thicker average line
            
            # Create the chart component
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True, 
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'training_engagement_trends_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged engagement chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )
            
    @callback(
        [Output("training-chart-modal", "is_open", allow_duplicate=True),
        Output("training-modal-chart-content", "children", allow_duplicate=True)],
        [Input("engagement-chart-wrapper", "n_clicks")],
        [State("training-chart-modal", "is_open"),
        State("engagement-trends-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Engagement Modal Toggle")
    def toggle_engagement_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of engagement chart modal using SHARED modal
        Same approach as engaged members chart
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # print(f"🔄 Engagement Modal callback triggered by: {triggered_id}")
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "engagement-chart-wrapper" and chart_wrapper_clicks and not is_open:
            # print("📊 Engagement chart wrapper clicked! Opening modal...")
            
            if not chart_figure or not chart_figure.get('data'):
                # print("⚠️ No engagement chart figure data available")
                return no_update, no_update
            
            # print("✅ Opening engagement modal with chart data")
            enlarged_chart = create_enlarged_engagement_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
    
    # print("✅ Training Office Engagement Chart Modal callbacks registered successfully")
