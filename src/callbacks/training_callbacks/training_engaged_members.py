from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import plotly.graph_objects as go
import pandas as pd
import copy
from datetime import datetime
import time
from functools import wraps
import logging
from src.utils.db import run_queries

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

def register_training_engaged_members_callbacks(app):
    """
    Register server-side callback for top engaged members chart using Fact_MemberEngagement
    """
    # print("Registering Training Engaged Members callback (server-side)...")

    @callback(
        Output("top-engaged-members-chart", "figure"),
        [
            Input("training-filtered-query-store", "data"),
            Input("engagement-metric-dropdown", "value"),
            Input("top-members-count-dropdown", "value")
        ],
        prevent_initial_call=True
    
    )
    # @monitor_performance("Engaged Members Chart Update")
    def update_engaged_members_chart(query_selections, engagement_metric, top_count):
        """
        Update the top engaged members chart using Fact_MemberEngagement and filtered attendance data
        """
        # print(f"🔄 Updating engaged members chart - Metric: {engagement_metric}, Top Count: {top_count}")
        # print(f"📋 Query selections: {query_selections}")
        
        # Set defaults
        engagement_metric = engagement_metric or 'sessions_attended'
        top_count = top_count or 20
        
        
        try:
            queries = {
                "attendance_stats": 'SELECT [TrainingClassId],[StartTime],[TrainingTopicId],[LocationId],[InstructorId],[AorShortName],[MemberOffice],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]',
                "active_members": "SELECT [MemberID],[MemberName],[OfficeCode],[TotalSessionsRegistered],[TotalSessionsAttended],[MissedSessions],[AttendanceRate] FROM [consumable].[Fact_MemberEngagement] WHERE ([TotalSessionsRegistered] > 0 OR [TotalSessionsAttended] > 0) AND [MemberStatus] = 'Active'"            
            }
            
            # Execute all queries at once
            results = run_queries(queries, 1)

            df_members = results["active_members"]
            df_attendance = results["attendance_stats"]
            
            if df_members.empty:
                # print("⚠️ No member engagement data available")
                return create_empty_chart("No Member Data", "No member engagement data found")
            
            # Apply user filters to both datasets
            df_members_filtered = apply_member_filters(df_members, query_selections)
            df_attendance_filtered = apply_attendance_filters(df_attendance, query_selections)
            
            if df_members_filtered.empty:
                # print("⚠️ No members after applying filters")
                return create_empty_chart("No Data After Filtering", "No members match the selected filters")
            
            # print(f"📊 Members after filtering: {len(df_members_filtered)}")
            # print(f"📊 Attendance records after filtering: {len(df_attendance_filtered)}")
            
            # Get member IDs that are active in the filtered attendance data (if date filters applied)
            active_member_ids = None
            if not df_attendance_filtered.empty and query_selections and ('Day_From' in query_selections or 'Day_To' in query_selections):
                # Get unique offices from filtered attendance to further filter members
                active_offices = set(df_attendance_filtered['MemberOffice'].dropna().unique()) if 'MemberOffice' in df_attendance_filtered.columns else set()
                if active_offices:
                    df_members_filtered = df_members_filtered[df_members_filtered['OfficeCode'].isin(active_offices)]
                    # print(f"📊 Members after date-based office filtering: {len(df_members_filtered)}")
            
            # Calculate engagement metrics and get top members
            top_members = calculate_top_members(df_members_filtered, engagement_metric, top_count)
            
            if top_members.empty:
                # print("⚠️ No engagement data calculated")
                return create_empty_chart("No Engagement Data", "Unable to calculate engagement metrics")
            
            # Create chart
            fig = create_members_chart(top_members, engagement_metric, top_count)
            
            # print(f"✅ Engaged members chart created with {len(top_members)} members")
            return fig
            
        except Exception as e:
            # print(f"❌ Error creating engaged members chart: {str(e)}")
            import traceback
            traceback.print_exc()
            return create_empty_chart("Chart Error", f"Error processing data: {str(e)}")

def apply_member_filters(df_members, query_selections):
    """
    Apply user filter selections to member engagement data
    """
    if not query_selections:
        # print("📋 No query selections for members - returning all data")
        return df_members
    
    df_filtered = df_members.copy()
    # print(f"📊 Starting with {len(df_filtered)} member records")
    
    # Apply Office filter (members have OfficeCode)
    offices_filter = query_selections.get('Offices', '')
    if offices_filter and offices_filter.strip():
        office_list = [office.strip().strip("'\"") for office in offices_filter.split(',')]
        office_list = [office for office in office_list if office]
        
        if office_list and 'OfficeCode' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['OfficeCode'].isin(office_list)]
            # print(f"🏢 Office filter ({office_list}): {before_count} → {len(df_filtered)} members")
    
    # print(f"✅ Final filtered members: {len(df_filtered)} records")
    return df_filtered

def apply_attendance_filters(df_attendance, query_selections):
    """
    Apply user filter selections to attendance stats for context
    """
    if not query_selections:
        # print("📋 No query selections for attendance - returning all data")
        return df_attendance
    
    df_filtered = df_attendance.copy()
    # print(f"📊 Starting with {len(df_filtered)} attendance records")
    
    # Apply date range filter using StartTime
    start_date = query_selections.get('Day_From')
    end_date = query_selections.get('Day_To')
    
    if start_date and end_date and 'StartTime' in df_filtered.columns:
        # Convert StartTime to datetime if it's not already
        df_filtered['StartTime'] = pd.to_datetime(df_filtered['StartTime'], errors='coerce')
        start_dt = pd.to_datetime(start_date).normalize()
        end_dt = pd.to_datetime(end_date).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        # print(f"📅 Applying date filter: {start_dt} to {end_dt}")
        
        before_count = len(df_filtered)
        df_filtered = df_filtered[
            (df_filtered['StartTime'] >= start_dt) & 
            (df_filtered['StartTime'] <= end_dt)
        ]
        # print(f"📅 Date filter: {before_count} → {len(df_filtered)} attendance records")
    
    # Apply AOR filter
    aors_filter = query_selections.get('AORs', '')
    if aors_filter and aors_filter.strip():
        aor_list = [aor.strip().strip("'\"") for aor in aors_filter.split(',')]
        aor_list = [aor for aor in aor_list if aor]
        # print(f"🔍 Applying AOR filter: {aor_list}")
        if aor_list and 'AorShortName' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['AorShortName'].isin(aor_list)]
            # print(f"🎯 AOR filter ({aor_list}): {before_count} → {len(df_filtered)} attendance records")
    
    # Apply Office filter
    offices_filter = query_selections.get('Offices', '')
    if offices_filter and offices_filter.strip():
        office_list = [office.strip().strip("'\"") for office in offices_filter.split(',')]
        office_list = [office for office in office_list if office]
        # print(f"🔍 Applying Office filter: {office_list}")
        if office_list and 'MemberOffice' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['MemberOffice'].isin(office_list)]
            # print(f"🏢 Office filter ({office_list}): {before_count} → {len(df_filtered)} attendance records")
    
    # Apply Topics filter
    topics_filter = query_selections.get('Topics', '')
    if topics_filter and topics_filter.strip():
        topic_list = [topic.strip().strip("'\"") for topic in topics_filter.split(',')]
        topic_list = [topic for topic in topic_list if topic]
        # print(f"🔍 Applying Topic filter: {topic_list}")
        if topic_list and 'TrainingTopicId' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['TrainingTopicId'].isin(topic_list)]
            # print(f"📚 Topic filter ({topic_list}): {before_count} → {len(df_filtered)} attendance records")

    # Apply Instructors filter
    instructors_filter = query_selections.get('Instructors', '')
    if instructors_filter and instructors_filter.strip():
        instructor_list = [inst.strip().strip("'\"") for inst in instructors_filter.split(',')]
        instructor_list = [inst for inst in instructor_list if inst]
        # print(f"🔍 Applying Instructor filter: {instructor_list}")
        if instructor_list and 'InstructorId' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['InstructorId'].isin(instructor_list)]
            # print(f"👨‍🏫 Instructor filter ({instructor_list}): {before_count} → {len(df_filtered)} attendance records")
    
    # Apply Locations filter
    locations_filter = query_selections.get('Locations', '')
    if locations_filter and locations_filter.strip():
        location_list = [loc.strip().strip("'\"") for loc in locations_filter.split(',')]
        location_list = [loc for loc in location_list if loc]
        # print(f"🔍 Applying Location filter: {location_list}")
        if location_list and 'LocationId' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['LocationId'].isin(location_list)]
            # print(f"📍 Location filter ({location_list}): {before_count} → {len(df_filtered)} attendance records")
    
    # Apply Classes filter
    classes_filter = query_selections.get('Classes', '')
    if classes_filter and classes_filter.strip():
        class_list = [cls.strip().strip("'\"") for cls in classes_filter.split(',')]
        class_list = [cls for cls in class_list if cls]
        # print(f"🔍 Applying Class filter: {class_list}")
        if class_list and 'TrainingClassId' in df_filtered.columns:
            before_count = len(df_filtered)
            df_filtered = df_filtered[df_filtered['TrainingClassId'].isin(class_list)]
            # print(f"📋 Class filter ({class_list}): {before_count} → {len(df_filtered)} attendance records")
    
    # print(f"✅ Final filtered attendance: {len(df_filtered)} records")
    return df_filtered

def calculate_top_members(df_members, metric, top_count):
    """
    Calculate top members based on selected engagement metric from Fact_MemberEngagement
    """
    # print(f"📊 Calculating top members using metric: {metric}")
    # print(f"📋 Available columns: {list(df_members.columns)}")
    
    # Ensure we have the required columns
    required_columns = ['MemberID', 'MemberName', 'TotalSessionsRegistered','TotalSessionsAttended', 'MissedSessions','AttendanceRate']
    missing_columns = [col for col in required_columns if col not in df_members.columns]
    
    if missing_columns:
        # print(f"❌ Missing required columns: {missing_columns}")
        return pd.DataFrame()
    
    # Calculate metric values
    df_calc = df_members.copy()
    
    # Fill any null values with defaults
    df_calc['TotalSessionsRegistered'] = df_calc.get('TotalSessionsRegistered', 0).fillna(0)
    df_calc['TotalSessionsAttended'] = df_calc.get('TotalSessionsAttended', 0).fillna(0)
    df_calc['AttendanceRate'] = df_calc.get('AttendanceRate', 0).fillna(0)
    df_calc['MissedSessions'] = df_calc.get('MissedSessions', 0).fillna(0)
    
    # Calculate training hours (estimate: 1 hour per session attended)
    df_calc['training_hours'] = df_calc['TotalSessionsAttended'] * 1.0
    
    # For topics completed, we'd need additional data - use a placeholder calculation
    # This could be enhanced by joining with attendance_stats to count unique topics
    df_calc['topics_completed'] = (df_calc['TotalSessionsAttended'] / 2).apply(lambda x: max(1, int(x)))
    
    # Select metric value based on user selection
    if metric == 'sessions_attended':
        df_calc['metric_value'] = df_calc['TotalSessionsAttended']
        metric_label = ''
    elif metric == 'training_hours':
        df_calc['metric_value'] = df_calc['training_hours']
        metric_label = ' hrs'
    elif metric == 'topics_completed':
        df_calc['metric_value'] = df_calc['topics_completed']
        metric_label = ''
    else:
        df_calc['metric_value'] = df_calc['TotalSessionsAttended']  # Default
        metric_label = ''
    
    # Sort by metric value and get top N
    df_sorted = df_calc.sort_values('metric_value', ascending=False)
    top_members = df_sorted.head(top_count)
    
    # Add metric label for display
    top_members = top_members.copy()
    top_members['metric_label'] = metric_label
    
    # print(f"📊 Calculated top {len(top_members)} members by {metric}")
    return top_members

def create_members_chart(top_members, metric, top_count):
    """
    Create Plotly chart for top engaged members with vertical bars (matching Azure cost drivers style)
    """
    if top_members.empty:
        return create_empty_chart("No Data", "No member data available")
    
    # Prepare chart data
    member_names = top_members['MemberName'].tolist()
    values = top_members['metric_value'].tolist()
    metric_label = top_members['metric_label'].iloc[0] if 'metric_label' in top_members.columns else ''
    
    # Truncate long names for better display on x-axis
    display_names = [name[:15] + '...' if len(name) > 15 else name for name in member_names]
    
    # Create hover text with detailed information
    hover_texts = []
    for _, member in top_members.iterrows():
        hover_text = (
            f"<b>{member['MemberName']}</b><br>"
            f"Office: {member.get('OfficeCode', 'Unknown')}<br>"
            f"Sessions Attended: {member.get('TotalSessionsAttended', 0)}<br>"
            f"Sessions Registered: {member.get('TotalSessionsRegistered', 0)}<br>"
            f"Attendance Rate: {member.get('AttendanceRate', 0):.1f}%<br>"
            f"Missed Sessions: {member.get('MissedSessions', 0)}<br>"
            f"Est. Training Hours: {member.get('training_hours', 0):.1f}<br>"
            f"<extra></extra>"
        )
        hover_texts.append(hover_text)
    
    # Determine chart title and axis label based on metric
    metric_info = {
        'sessions_attended': {'title': 'Top Members by Sessions Attended', 'label': 'Sessions Attended'},
        'training_hours': {'title': 'Top Members by Training Hours', 'label': 'Estimated Training Hours'},
        'topics_completed': {'title': 'Top Members by Topics Completed', 'label': 'Estimated Topics Completed'}
    }
    
    info = metric_info.get(metric, metric_info['sessions_attended'])
    
    fig = go.Figure(data=[
        go.Bar(
            x=display_names,  
            y=values,        
            text=[f"{v}{metric_label}" for v in values],
            textposition='outside',
            hovertemplate=hover_texts,
            name='',
            marker=dict(
                color=values,
                colorscale='Viridis',
                showscale=False,
                line=dict(color='rgba(54, 162, 235, 1.0)', width=1)
            )
        )
    ])
    
    fig.update_layout(
        title={
            'text': f"{info['title']} (Top {top_count})",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis={
            'title': 'Member Name',  
            'showgrid': False,
            'tickangle': -45,       
            'tickfont': {'size': 10}
        },
        yaxis={
            'title': info['label'],  
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100}, 
        height=500,  
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        clickmode='event+select'
    )
    
    fig.update_traces(
        hovertemplate=hover_texts
    )
    
    return fig

def create_empty_chart(title, message):
    """
    Create an empty chart with a message (matching vertical bar chart style)
    """
    fig = go.Figure()
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#2c3e50'}
        },
        xaxis={
            'title': 'Member Name',
            'showgrid': False,
            'tickfont': {'size': 10}
        },
        yaxis={
            'title': 'Engagement Metric',
            'showgrid': True,
            'gridcolor': '#f0f0f0'
        },
        showlegend=False,
        height=500,  
        margin={'l': 60, 'r': 50, 't': 80, 'b': 100},  
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[{
            'text': message,
            'xref': 'paper',
            'yref': 'paper',
            'x': 0.5,
            'y': 0.5,
            'xanchor': 'center',
            'yanchor': 'middle',
            'showarrow': False,
            'font': {'size': 14, 'color': 'gray'}
        }]
    )
    return fig
                
def register_training_chart_modal_callbacks(app):
    """
    Register callbacks for training chart modal functionality - SIMPLIFIED
    """
    # print("Registering Training Chart Modal callbacks...")
    
    @callback(
        [Output("training-chart-modal", "is_open"),
        Output("training-modal-chart-content", "children")],
        [Input("chart-wrapper", "n_clicks")],  # ✅ Only chart clicks, no close button
        [State("training-chart-modal", "is_open"),
        State("top-engaged-members-chart", "figure")],
        prevent_initial_call=True
    )
    def toggle_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of chart modal - closing handled automatically by default X button
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # print(f"🔄 Modal callback triggered by: {triggered_id}")
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "chart-wrapper" and chart_wrapper_clicks and not is_open:
            # print("📊 Chart wrapper clicked! Opening modal...")
            
            if not chart_figure or not chart_figure.get('data'):
                # print("⚠️ No chart figure data available")
                return no_update, no_update
            
            # print("✅ Opening modal with chart data")
            enlarged_chart = create_enlarged_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update    
    
    # print("✅ Training Chart Modal callbacks registered successfully")
        
def create_enlarged_chart(original_figure):
    """
    Create an enlarged version of the chart for modal display
    """
    if not original_figure:
        return html.Div("No chart data available", className="text-center p-4")
    
    try:
        # Create a deep copy of the original figure
        enlarged_fig = copy.deepcopy(original_figure)
        
        # Update layout for larger modal display
        enlarged_fig['layout'].update({
            'height': 600,  
            'margin': {'l': 80, 'r': 60, 't': 100, 'b': 120},  
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
                if trace.get('type') == 'bar':
                    # Make text larger and more visible
                    trace.update({
                        'textfont': {'size': 12},
                        'marker': {
                            **trace.get('marker', {}),
                            'line': {'width': 2, 'color': 'rgba(54, 162, 235, 1.0)'}
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
                    'filename': 'training_engagement_chart',
                    'height': 600,
                    'width': 1000,
                    'scale': 1
                }
            },
            style={'height': '600px'}
        )
        
    except Exception as e:
        # print(f"❌ Error creating enlarged chart: {str(e)}")
        return html.Div(
            f"Error displaying chart: {str(e)}", 
            className="text-center p-4 text-danger"
        )

 
    
    # print("✅ Training Engaged Members callback registered successfully")