from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance
# ✅ REMOVED: import numpy as np
# ✅ REMOVED: from scipy import stats

def register_training_session_scheduling_callbacks(app):
    """
    Register session scheduling trend callbacks
    Matches the component IDs from the layout file
    """
    
    @monitor_query_performance("Session Scheduling Base Data")
    def get_session_scheduling_base_data():
        """
        Fetch base data for session scheduling trend analysis
        Uses consumable fact tables with minimal joins
        """
        
        queries = {
            # Get training class data with scheduling info
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
                AND [AorShortName] IS NOT NULL
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

    @monitor_performance("Session Scheduling Filter Application")
    def apply_scheduling_filters(base_data, query_selections):
        """
        Apply filters to base session scheduling data using pandas
        """
        if not query_selections:
            query_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_classes = pd.DataFrame(base_data.get('training_classes', [])).copy()
        df_topics = pd.DataFrame(base_data.get('topic_assignments', [])).copy()
        df_aor_offices = pd.DataFrame(base_data.get('aor_offices', [])).copy()
        
        # print(f"📊 Starting scheduling filtering: {len(df_classes)} class records, {len(df_topics)} topic assignments")
        
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
        if not df_classes.empty and 'StartTime' in df_classes.columns:
            df_classes = df_classes.copy()
            
            # Handle different datetime formats
            if df_classes['StartTime'].dtype == 'object':
                df_classes.loc[:, 'ParsedStartTime'] = df_classes['StartTime'].apply(parse_custom_datetime)
            else:
                df_classes.loc[:, 'ParsedStartTime'] = pd.to_datetime(df_classes['StartTime'])
            
            df_classes = df_classes.dropna(subset=['ParsedStartTime']).copy()
            
            # Apply date range filter if specified
            start_date = query_selections.get('Day_From')
            end_date = query_selections.get('Day_To')
            
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df_classes = df_classes.loc[
                        (df_classes['ParsedStartTime'] >= start_dt) & 
                        (df_classes['ParsedStartTime'] <= end_dt)
                    ].copy()
                    # print(f"📅 Date filter applied: {len(df_classes)} class records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Apply AOR filter
        if aor_list:
            if not df_classes.empty:
                df_classes = df_classes.loc[df_classes['AorShortName'].isin(aor_list)].copy()
            if not df_topics.empty:
                # Filter topic assignments by AorId - need to map AorShortName to AorId
                aor_id_mapping = df_aor_offices.set_index('AorShortName')['AorID'].to_dict() if not df_aor_offices.empty else {}
                aor_ids = [aor_id_mapping.get(aor) for aor in aor_list if aor_id_mapping.get(aor)]
                if aor_ids:
                    df_topics = df_topics.loc[df_topics['AorId'].isin(aor_ids)].copy()
            # print(f"🎯 AOR filter applied: {len(df_classes)} classes, {len(df_topics)} topic assignments")
        
        # Apply Office filter (via AOR mapping)
        if office_list and not df_aor_offices.empty:
            office_aors = df_aor_offices.loc[df_aor_offices['OfficeCode'].isin(office_list), 'AorShortName'].unique()
            if len(office_aors) > 0 and not df_classes.empty:
                df_classes = df_classes.loc[df_classes['AorShortName'].isin(office_aors)].copy()
            # print(f"🏢 Office filter applied: {len(df_classes)} classes")
        
        # Apply Topic filter
        if topic_list and not df_topics.empty:
            df_topics = df_topics.loc[df_topics['TrainingTopicId'].astype(str).isin(topic_list)].copy()
            # Filter classes to only those with matching topics
            if not df_classes.empty:
                matching_class_ids = df_topics['TrainingClassId'].unique()
                df_classes = df_classes.loc[df_classes['TrainingClassId'].isin(matching_class_ids)].copy()
            # print(f"📚 Topic filter applied: {len(df_classes)} classes, {len(df_topics)} topic assignments")
        
        # Apply Instructor filter
        if instructor_list:
            if not df_classes.empty:
                df_classes = df_classes.loc[df_classes['InstructorId'].astype(str).isin(instructor_list)].copy()
            if not df_topics.empty:
                df_topics = df_topics.loc[df_topics['InstructorId'].astype(str).isin(instructor_list)].copy()
            # print(f"👨‍🏫 Instructor filter applied: {len(df_classes)} classes")
        
        # Apply Location filter
        if location_list and not df_classes.empty:
            df_classes = df_classes.loc[df_classes['LocationId'].astype(str).isin(location_list)].copy()
            # print(f"📍 Location filter applied: {len(df_classes)} classes")
        
        return {
            "training_classes": df_classes,
            "topic_assignments": df_topics,
            "aor_offices": df_aor_offices
        }

    @monitor_performance("Scheduling Time Series Data Preparation")
    def prepare_scheduling_time_series_data(filtered_data, aggregation_level, trend_type):
        """
        Prepare time series data for scheduling trend analysis
        """
        df_classes = filtered_data.get('training_classes', pd.DataFrame())
        df_topics = filtered_data.get('topic_assignments', pd.DataFrame())
        
        if df_classes.empty:
            return pd.DataFrame()
        
        try:
            # Create time period columns
            df_classes = df_classes.copy()
            df_classes.loc[:, 'YearNumber'] = df_classes['ParsedStartTime'].dt.year
            df_classes.loc[:, 'MonthNumber'] = df_classes['ParsedStartTime'].dt.month
            df_classes.loc[:, 'QuarterNumber'] = df_classes['ParsedStartTime'].dt.quarter
            
            # Create time period labels
            if aggregation_level == "monthly":
                df_classes.loc[:, 'TimePeriod'] = df_classes['ParsedStartTime'].dt.to_period('M')
                df_classes.loc[:, 'TimeLabel'] = df_classes['ParsedStartTime'].dt.strftime('%Y-%m')
            elif aggregation_level == "quarterly":
                df_classes.loc[:, 'TimePeriod'] = df_classes['ParsedStartTime'].dt.to_period('Q')
                df_classes.loc[:, 'TimeLabel'] = df_classes.apply(
                    lambda x: f"{x['YearNumber']}-Q{x['QuarterNumber']}", axis=1
                )
            else:  # yearly
                df_classes.loc[:, 'TimePeriod'] = df_classes['ParsedStartTime'].dt.to_period('Y')
                df_classes.loc[:, 'TimeLabel'] = df_classes['YearNumber'].astype(str)
            
            # Determine grouping based on trend type
            if trend_type == "all":
                # All sessions grouped together
                time_series = df_classes.groupby('TimeLabel').agg({
                    'TrainingClassId': 'nunique'  # Count unique sessions
                }).reset_index()
                time_series.loc[:, 'GroupName'] = 'All Sessions'
                
            elif trend_type == "by_aor":
                # Group by AOR
                time_series = df_classes.groupby(['TimeLabel', 'AorShortName']).agg({
                    'TrainingClassId': 'nunique'
                }).reset_index()
                time_series = time_series.rename(columns={'AorShortName': 'GroupName'})
                
            elif trend_type == "by_topic":
                # Group by topic - need to join with topic assignments
                if not df_topics.empty:
                    class_topics = df_classes.merge(
                        df_topics[['TrainingClassId', 'TrainingTopicName']], 
                        on='TrainingClassId', 
                        how='left'
                    )
                    time_series = class_topics.groupby(['TimeLabel', 'TrainingTopicName']).agg({
                        'TrainingClassId': 'nunique'
                    }).reset_index()
                    time_series = time_series.rename(columns={'TrainingTopicName': 'GroupName'})
                else:
                    # Fallback to all sessions if no topic data
                    time_series = df_classes.groupby('TimeLabel').agg({
                        'TrainingClassId': 'nunique'
                    }).reset_index()
                    time_series.loc[:, 'GroupName'] = 'All Sessions'
                    
            elif trend_type == "by_instructor":
                # Group by instructor
                time_series = df_classes.groupby(['TimeLabel', 'InstructorName']).agg({
                    'TrainingClassId': 'nunique'
                }).reset_index()
                time_series = time_series.rename(columns={'InstructorName': 'GroupName'})
            
            else:
                # Default to all sessions
                time_series = df_classes.groupby('TimeLabel').agg({
                    'TrainingClassId': 'nunique'
                }).reset_index()
                time_series.loc[:, 'GroupName'] = 'All Sessions'
            
            # Rename the metric column
            time_series = time_series.rename(columns={'TrainingClassId': 'SessionCount'})
            
            # Add metadata
            time_series.loc[:, 'MetricName'] = 'Sessions Scheduled'
            time_series.loc[:, 'TrendType'] = trend_type
            time_series.loc[:, 'AggregationLevel'] = aggregation_level
            
            # print(f"📊 Prepared scheduling time series: {len(time_series)} records")
            return time_series
            
        except Exception as e:
            print(f"❌ Error preparing scheduling time series data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @monitor_chart_performance("Session Scheduling Chart")
    def create_scheduling_trend_chart(time_series_data, trend_type):
        """
        Create interactive scheduling trend chart
        ✅ REMOVED: show_forecast parameter and all forecast logic
        """
        if time_series_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No scheduling data available for selected filters and time period",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Training Session Scheduling Trends",
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
            metric_name = time_series_data['MetricName'].iloc[0] if not time_series_data.empty else 'Sessions Scheduled'
            
            # Create dynamic title
            if trend_type == "all":
                chart_title = f"Training Session Scheduling Trends: {metric_name}"
            elif trend_type == "by_aor":
                chart_title = f"Training Session Scheduling Trends: {metric_name} (By AOR)"
            elif trend_type == "by_topic":
                chart_title = f"Training Session Scheduling Trends: {metric_name} (By Topic)"
            elif trend_type == "by_instructor":
                chart_title = f"Training Session Scheduling Trends: {metric_name} (By Instructor)"
            else:
                chart_title = f"Training Session Scheduling Trends: {metric_name}"
            
            # Create figure
            fig = go.Figure()
            
            # Get unique groups for color assignment
            unique_groups = time_series_data['GroupName'].unique()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            # Add trend lines for each group
            for i, group in enumerate(unique_groups):
                group_data = time_series_data[time_series_data['GroupName'] == group].sort_values('TimeLabel')
                
                hover_template = f"<b>{group}</b><br>Time: %{{x}}<br>{metric_name}: %{{y:,.0f}}<extra></extra>"
                
                fig.add_trace(go.Scatter(
                    x=group_data['TimeLabel'],
                    y=group_data['SessionCount'],
                    mode='lines+markers',
                    name=str(group),
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6),
                    hovertemplate=hover_template
                ))
                
                # ✅ REMOVED: All forecast generation logic
            
            # Add average line if multiple groups
            if len(time_series_data) > 1:
                avg_value = time_series_data['SessionCount'].mean()
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
            
            # print(f"📊 Created scheduling trend chart with {len(unique_groups)} trend lines")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating scheduling trend chart: {e}")
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
                    'text': "Training Session Scheduling Trends - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_performance("Scheduling Insights Generation")
    def generate_scheduling_insights(time_series_data, trend_type):
        """
        Generate automated insights from scheduling trend data
        ✅ REMOVED: show_forecast parameter and forecast-related insights
        """
        if time_series_data.empty:
            return html.Div("No insights available - insufficient scheduling data.", 
                          style={'color': 'gray'})
        
        try:
            insights = []
            
            # Calculate overall statistics
            total_sessions = time_series_data['SessionCount'].sum()
            avg_sessions = time_series_data['SessionCount'].mean()
            time_periods = time_series_data['TimeLabel'].nunique()
            
            # Top performer analysis
            if trend_type != "all":
                top_performer_data = time_series_data.groupby('GroupName')['SessionCount'].sum().reset_index()
                top_performer_data = top_performer_data.sort_values('SessionCount', ascending=False)
                
                if not top_performer_data.empty:
                    top_performer = top_performer_data.iloc[0]
                    top_name = top_performer['GroupName']
                    top_sessions = top_performer['SessionCount']
                    
                    if trend_type == "by_aor":
                        entity_type = "AOR"
                    elif trend_type == "by_topic":
                        entity_type = "Topic"
                    elif trend_type == "by_instructor":
                        entity_type = "Instructor"
                    else:
                        entity_type = "Entity"
                    
                    # ✅ REMOVED: Scheduling Overview insight for grouped views
                    insights.extend([
                        f"🏆 **Top {entity_type}**: {top_name} scheduled {top_sessions} sessions",
                        f"📈 **Average Rate**: {avg_sessions:.1f} sessions per period"
                    ])
            else:
                # Only show overview for "All Sessions" view
                insights.extend([
                    f"📊 **Total Sessions**: {total_sessions} sessions scheduled across {time_periods} time periods",
                    f"📈 **Average Rate**: {avg_sessions:.1f} sessions per period"
                ])
            
            # Growth trend analysis
            if time_periods > 1:
                time_series_sorted = time_series_data.sort_values('TimeLabel')
                recent_periods = time_series_sorted['TimeLabel'].unique()[-3:]  # Last 3 periods
                recent_data = time_series_sorted[time_series_sorted['TimeLabel'].isin(recent_periods)]
                
                if len(recent_data) >= 2:
                    recent_avg = recent_data['SessionCount'].mean()
                    overall_avg = time_series_data['SessionCount'].mean()
                    
                    if recent_avg > overall_avg * 1.1:
                        insights.append("📈 **Recent Trend**: Scheduling activity is trending upward")
                    elif recent_avg < overall_avg * 0.9:
                        insights.append("📉 **Recent Trend**: Scheduling activity is trending downward")
                    else:
                        insights.append("📊 **Recent Trend**: Scheduling activity remains stable")
            
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
            print(f"❌ Error generating scheduling insights: {e}")
            return html.Div("Unable to generate insights due to data processing error.", 
                          style={'color': 'red'})

    @callback(
        [Output("session-scheduling-trends-chart", "figure"),
         Output("scheduling-insights-summary", "children")],
        [Input("training-filtered-query-store", "data"),
         Input("scheduling-aggregation-dropdown", "value"),
         Input("scheduling-trend-type-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Session Scheduling Trends Update")
    def update_session_scheduling_trends(query_selections, aggregation_level, trend_type):
        """
        Update session scheduling trends chart based on filter selections
        """
        try:
            # print(f"🔄 Updating scheduling trends: aggregation={aggregation_level}, trend={trend_type}")
            
            # Get base data
            base_data = get_session_scheduling_base_data()
            
            # Apply filters
            filtered_data = apply_scheduling_filters(base_data, query_selections)
            
            # Prepare time series data
            time_series_data = prepare_scheduling_time_series_data(filtered_data, aggregation_level, trend_type)
            
            # Create visualization
            fig = create_scheduling_trend_chart(time_series_data, trend_type)
            
            # Generate insights
            insights = generate_scheduling_insights(time_series_data, trend_type)
            
            # print(f"✅ Session scheduling trends updated successfully")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating session scheduling trends: {e}")
            
            # Return error chart and message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading scheduling trend data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Training Session Scheduling Trends - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=500,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig, html.Div(f"Error generating insights: {str(e)}", style={'color': 'red'})

def register_training_session_scheduling_modal_callbacks(app):
    """
    Register callbacks for training session scheduling chart modal functionality
    """
    
    @monitor_chart_performance("Enlarged Scheduling Chart")
    def create_enlarged_scheduling_chart(original_figure):
        """
        Create an enlarged version of the scheduling trends chart for modal display
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
            
            # Create the chart component
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True, 
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'training_scheduling_trends_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged scheduling chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )
            
    @callback(
        [Output("training-chart-modal", "is_open", allow_duplicate=True),
        Output("training-modal-chart-content", "children", allow_duplicate=True)],
        [Input("scheduling-chart-wrapper", "n_clicks")],
        [State("training-chart-modal", "is_open"),
        State("session-scheduling-trends-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Scheduling Modal Toggle")
    def toggle_scheduling_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of scheduling chart modal using SHARED modal
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "scheduling-chart-wrapper" and chart_wrapper_clicks and not is_open:
            
            if not chart_figure or not chart_figure.get('data'):
                return no_update, no_update
            
            enlarged_chart = create_enlarged_scheduling_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update

# print("✅ Training session scheduling trend callbacks registered")