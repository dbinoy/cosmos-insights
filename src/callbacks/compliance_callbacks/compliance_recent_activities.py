from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters, prepare_recent_activities_data, get_case_flow_with_lifecycle_stages
from src.utils.performance import monitor_performance, monitor_chart_performance
import time
import copy

def register_compliance_recent_activities_callbacks(app):
    """Register recent activities callbacks"""
    
    @monitor_chart_performance("Recent Activities Chart")
    def create_recent_activities_chart(recent_events, summary_stats, view_state, timeframe):
        """Create recent activities chart based on view state"""
        
        if recent_events.empty:
            fig = go.Figure()
            fig.add_annotation(
                text=f"No recent activities found in {summary_stats.get('timeframe_label', 'selected timeframe')}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': "Recent Activities - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        if view_state == "timeline":
            # Timeline view - daily activity volume
            daily_activities = recent_events.groupby(recent_events['ActionDate'].dt.date).size().reset_index()
            daily_activities.columns = ['Date', 'Count']
            daily_activities['Date'] = pd.to_datetime(daily_activities['Date'])
            
            fig = go.Figure(data=[
                go.Scatter(
                    x=daily_activities['Date'],
                    y=daily_activities['Count'],
                    mode='lines+markers',
                    line=dict(color='#3498db', width=3),
                    marker=dict(size=8, color='#3498db'),
                    hovertemplate="<b>%{x}</b><br>Activities: %{y}<extra></extra>"
                )
            ])
            
            fig.update_layout(
                title={
                    'text': f"Daily Activity Timeline ({summary_stats.get('timeframe_label', 'Recent')})",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Date",
                yaxis_title="Number of Activities",
                height=400
            )
            
        elif view_state == "activity_type":
            # Activity type breakdown using exact notebook lifecycle stages
            type_counts = recent_events['LifecycleStage'].value_counts().reset_index()
            type_counts.columns = ['ActivityType', 'Count']
            
            # Color mapping for different activity types based on notebook stages
            color_map = {
                'Note Update': '#95a5a6',
                'Case Creation': '#2ecc71',
                'Case Update': '#3498db', 
                'Case Closure': '#e74c3c',
                'Case Reopening': '#f39c12',
                'Investigation Start': '#f39c12',
                'Investigation Status Change': '#e67e22',  
                'Review Status Change': '#9b59b6',
                'Notice Creation': '#8e44ad',
                'Invoice Creation': '#27ae60',
                'Invoice Link': '#27ae60',  
                'Invoice Status Change': '#27ae60',
                'Payment Invoice Creation': '#16a085',  
                'Payment Record Creation': '#16a085',
                'Payment Record Update': '#16a085',
                'Report Association': '#34495e',
                'Report Update': '#2c3e50',
                'Report Disposition Change': '#2c3e50',  
                'Report Reason Change': '#2c3e50',  
                'Assignee Change': '#7f8c8d',
                'Member Change': '#95a5a6',
                'Case Link': '#9b59b6',  
                'Case Unlink': '#9b59b6',  
                'Listing Change': '#e67e22',  
                'Test Stage': '#bdc3c7',  
                'Other': '#bdc3c7'
            }
            
            colors = [color_map.get(act, '#7f8c8d') for act in type_counts['ActivityType']]
            
            fig = go.Figure(data=[go.Bar(
                x=type_counts['Count'],
                y=type_counts['ActivityType'],
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{y}</b><br>Activities: %{x}<extra></extra>",
                text=type_counts['Count'],
                textposition='inside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Activities by Type ({summary_stats.get('total_activities', 0):,} Total)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Number of Activities",
                yaxis_title="",
                height=400,
                margin={'l': 150, 'r': 50, 't': 80, 'b': 50}
            )
            
        elif view_state == "volume":
            # Daily volume with trend
            daily_activities = recent_events.groupby(recent_events['ActionDate'].dt.date).size().reset_index()
            daily_activities.columns = ['Date', 'Count']
            daily_activities['Date'] = pd.to_datetime(daily_activities['Date'])
            
            # Calculate 7-day moving average
            daily_activities = daily_activities.sort_values('Date')
            daily_activities['MovingAvg'] = daily_activities['Count'].rolling(window=7, center=True).mean()
            
            fig = go.Figure()
            
            # Add daily bars
            fig.add_trace(go.Bar(
                x=daily_activities['Date'],
                y=daily_activities['Count'],
                name='Daily Activities',
                marker_color='#3498db',
                opacity=0.7,
                hovertemplate="<b>%{x}</b><br>Activities: %{y}<extra></extra>"
            ))
            
            # Add trend line if we have enough data
            if len(daily_activities) >= 7:
                fig.add_trace(go.Scatter(
                    x=daily_activities['Date'],
                    y=daily_activities['MovingAvg'],
                    mode='lines',
                    name='7-Day Trend',
                    line=dict(color='#e74c3c', width=3),
                    hovertemplate="<b>%{x}</b><br>7-Day Avg: %{y:.1f}<extra></extra>"
                ))
            
            fig.update_layout(
                title={
                    'text': f"Daily Activity Volume with Trend ({summary_stats.get('timeframe_label', 'Recent')})",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Date",
                yaxis_title="Number of Activities",
                height=400,
                showlegend=True
            )
            
        elif view_state == "case_activity":
            # Case-level activity distribution
            case_activities = recent_events.groupby('CaseNumber').size().reset_index()
            case_activities.columns = ['CaseNumber', 'ActivityCount']
            
            # Create distribution buckets
            def categorize_activity_count(count):
                if count == 1:
                    return "1 Activity"
                elif count <= 3:
                    return "2-3 Activities"
                elif count <= 5:
                    return "4-5 Activities"
                elif count <= 10:
                    return "6-10 Activities"
                else:
                    return "10+ Activities"
            
            case_activities['ActivityBucket'] = case_activities['ActivityCount'].apply(categorize_activity_count)
            bucket_counts = case_activities['ActivityBucket'].value_counts().reset_index()
            bucket_counts.columns = ['ActivityLevel', 'CaseCount']
            
            # Sort buckets logically
            bucket_order = ["1 Activity", "2-3 Activities", "4-5 Activities", "6-10 Activities", "10+ Activities"]
            bucket_counts['SortOrder'] = bucket_counts['ActivityLevel'].map({b: i for i, b in enumerate(bucket_order)})
            bucket_counts = bucket_counts.sort_values('SortOrder').drop('SortOrder', axis=1)
            
            colors = px.colors.sequential.Blues_r[:len(bucket_counts)]
            
            fig = go.Figure(data=[go.Pie(
                labels=bucket_counts['ActivityLevel'],
                values=bucket_counts['CaseCount'],
                hole=0.4,
                marker=dict(colors=colors, line=dict(color='white', width=2)),
                hovertemplate="<b>%{label}</b><br>Cases: %{value}<br>Percent: %{percent}<extra></extra>"
            )])
            
            # Add center text
            total_cases = summary_stats.get('unique_cases', 0)
            fig.add_annotation(
                text=f"<b>{total_cases:,}</b><br>Active Cases",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False
            )
            
            fig.update_layout(
                title={
                    'text': f"Case Activity Distribution ({total_cases:,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                height=400
            )
        
        # Common layout updates
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#2c3e50'},
            margin={'l': 50, 'r': 50, 't': 80, 'b': 50}
        )
        
        return fig
    
    @monitor_chart_performance("Enlarged Recent Activities Chart")
    def create_enlarged_recent_activities_chart(original_figure):
        """Create an enlarged version of the recent activities chart for modal display"""
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            enlarged_fig = copy.deepcopy(original_figure)
            enlarged_fig['layout'].update({
                'height': 600,
                'margin': {'l': 80, 'r': 80, 't': 100, 'b': 100},
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}
                }
            })
            
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'compliance_recent_activities_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
        except Exception as e:
            return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")
    
    def create_recent_activities_details_table(recent_events, summary_stats, view_state, timeframe):
        """Create detailed breakdown table for modal display"""
        if recent_events.empty:
            return html.Div([
                html.H4("No Recent Activities", className="text-info mb-3"),
                html.P(f"No compliance activities found in {summary_stats.get('timeframe_label', 'selected timeframe')}.", className="text-muted")
            ], className="text-center p-4")
        
        try:
            # Create summary cards
            total_activities = summary_stats.get('total_activities', 0)
            unique_cases = summary_stats.get('unique_cases', 0)
            daily_avg = summary_stats.get('daily_average', 0)
            most_active_day = summary_stats.get('most_active_day', 'N/A')
            
            summary_cards = dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📊 Total Activities", className="text-primary mb-1"),
                            html.H4(f"{total_activities:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-primary")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📁 Active Cases", className="text-info mb-1"),
                            html.H4(f"{unique_cases:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-info")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📈 Daily Average", className="text-success mb-1"),
                            html.H4(f"{daily_avg:.1f}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-success")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("🏆 Most Active Day", className="text-warning mb-1"),
                            html.H6(f"{most_active_day}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-warning")
                ], width=3)
            ], className="mb-4")
            
            # Recent activities table (last 50 activities)
            recent_sample = recent_events.head(50).copy()
            recent_sample['FormattedDate'] = recent_sample['ActionDate'].dt.strftime('%m/%d/%Y %H:%M')
            
            table_rows = []
            for i, row in recent_sample.iterrows():
                # Color coding based on lifecycle stage from notebook
                stage_colors = {
                    'Case Creation': 'table-success',
                    'Case Closure': 'table-danger',
                    'Case Reopening': 'table-warning',
                    'Case Update': 'table-primary',
                    'Investigation Start': 'table-warning',
                    'Investigation Status Change': 'table-warning',  
                    'Notice Creation': 'table-info',
                    'Review Status Change': 'table-info',
                    'Invoice Creation': 'table-success',
                    'Invoice Link': 'table-success',  
                    'Invoice Status Change': 'table-success',  
                    'Payment Invoice Creation': 'table-success',  
                    'Payment Record Creation': 'table-success',
                    'Payment Record Update': 'table-success',
                    'Case Link': 'table-primary',  
                    'Case Unlink': 'table-secondary',  
                    'Listing Change': 'table-warning',  
                    'Test Stage': 'table-light',  
                    'Report Association': 'table-info',
                    'Report Update': 'table-info',
                    'Report Disposition Change': 'table-info',  
                    'Report Reason Change': 'table-info',  
                    'Assignee Change': 'table-secondary',
                    'Member Change': 'table-secondary',
                    'Note Update': 'table-light'  
                }
                
                row_class = stage_colors.get(row['LifecycleStage'], '')
                
                cells = [
                    html.Td(row['CaseNumber'], style={'fontSize': '12px', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                    # html.Td(row['EventSummary'], style={'fontSize': '12px', 'maxWidth': '300px'}),         
                    html.Td([
                        html.Div([
                            html.Span(
                                row['EventSummary'],
                                id=f"event-summary-{i}",
                                style={
                                    'fontSize': '12px',
                                    'cursor': 'help',
                                    'borderBottom': '1px dotted #007bff',
                                    'color': '#007bff',
                                    'position': 'relative'
                                }
                            ),
                            html.Span(
                                " 📄",  # Document icon for "full details"
                                style={
                                    'fontSize': '10px',
                                    'opacity': '0.8',
                                    'marginLeft': '4px'
                                }
                            ),                            
                            dbc.Tooltip(
                                html.Div([
                                    html.Span(
                                        row.get('Detail', ''),
                                        style={'fontSize': '11px', 'lineHeight': '1.4', 'fontStyle': 'italic'}
                                    )
                                ], style={'maxWidth': '500px', 'textAlign': 'left'}),
                                target=f"event-summary-{i}",
                                placement="top",
                                style={'maxWidth': '450px'}
                            )
                        ])
                    ], style={'maxWidth': '300px'}),                    #  Event Summary with tooltip      
                    html.Td([
                        html.Span(get_stage_icon(row['LifecycleStage']), style={'marginRight': '8px'}),
                        html.Span(row['LifecycleStage'], style={'fontWeight': 'bold' if i < 10 else 'normal'})
                    ]),
                    html.Td(row['FormattedDate'], style={'fontSize': '12px'})                    
                ]
                
                table_rows.append(html.Tr(cells, className=row_class))
            
            headers = [
                html.Th("Case Number", style={'width': '15%'}),                
                html.Th("Event", style={'width': '40%'}),
                html.Th("Activity Type", style={'width': '25%'}),
                html.Th("Date & Time", style={'width': '20%'})                
            ]
            
            return html.Div([
                html.H4(f"Recent Activities - {summary_stats.get('timeframe_label', 'Overview')}", className="mb-3 text-primary"),
                
                # Summary cards
                summary_cards,
                
                html.P([
                    html.Span([
                        html.I(className="fas fa-calendar me-2"),
                        f"Period: {summary_stats.get('date_range', 'N/A')}"
                    ], className="me-4"),
                    html.Span([
                        html.I(className="fas fa-chart-line me-2"),
                        f"Showing latest {len(recent_sample)} activities"
                    ])
                ], className="text-muted mb-4"),
                
                html.Table([
                    html.Thead([
                        html.Tr(headers, style={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'})
                    ]),
                    html.Tbody(table_rows)
                ], className="table table-hover table-striped table-sm"),
                
            ], className="p-3")
            
        except Exception as e:
            return html.Div([
                html.H4("Error Creating Activity Details", className="text-danger mb-3"),
                html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
            ], className="text-center p-4")
    
    def get_stage_icon(stage):
        """Get icon for lifecycle stage - using exact notebook stages"""
        icons = {
            'Note Update': '📝',
            'Case Creation': '🆕',
            'Case Update': '✏️',
            'Case Closure': '✅',
            'Case Reopening': '🔄',
            'Investigation Start': '🔍',
            'Investigation Status Change': '🔬',  
            'Review Status Change': '📋',
            'Notice Creation': '📢',
            'Invoice Creation': '💰',
            'Invoice Link': '🔗',  
            'Invoice Status Change': '💱',  
            'Payment Invoice Creation': '💳',  
            'Payment Record Creation': '💳',
            'Payment Record Update': '💳',
            'Report Association': '📊',
            'Report Update': '📈',
            'Report Disposition Change': '⚖️',  
            'Report Reason Change': '📝',  
            'Assignee Change': '👥',
            'Member Change': '👤',
            'Case Link': '🔗',  
            'Case Unlink': '🔓',  
            'Listing Change': '🏠',  
            'Test Stage': '🧪',  
            'Other': '📌'
        }
        return icons.get(stage, '📌')
    
    @monitor_performance("Recent Activities Insights Generation")
    def generate_recent_activities_insights(recent_events, summary_stats, view_state):
        """Generate insights for recent activities"""
        
        if recent_events.empty:
            return html.Div([
                html.Div([
                    html.Span("📅 ", style={'fontSize': '16px'}),
                    html.Span(f"**No Recent Activity**: No activities found in {summary_stats.get('timeframe_label', 'selected timeframe')}", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        insights = []
        
        # Overall activity summary
        total_activities = summary_stats.get('total_activities', 0)
        unique_cases = summary_stats.get('unique_cases', 0)
        daily_avg = summary_stats.get('daily_average', 0)
        
        insights.append(
            html.Div([
                html.Span("📊 ", style={'fontSize': '16px'}),
                html.Span(f"**Activity Summary**: {total_activities:,} activities across {unique_cases:,} cases (avg {daily_avg:.1f}/day)", style={'fontSize': '13px'})
            ], className="mb-2")
        )
        
        # Most common activity type using notebook stages
        if not recent_events.empty:
            top_activity = recent_events['LifecycleStage'].value_counts().iloc[0]
            top_activity_type = recent_events['LifecycleStage'].value_counts().index[0]
            activity_pct = (top_activity / total_activities * 100)
            
            insights.append(
                html.Div([
                    html.Span("🎯 ", style={'fontSize': '16px'}),
                    html.Span(f"**Most Common**: {top_activity_type} accounts for {top_activity:,} activities ({activity_pct:.1f}%)", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Investigation activity using notebook stages
        investigation_activities = recent_events[
            recent_events['LifecycleStage'].isin(['Investigation_Start', 'Investigation_Status_Change'])
        ]
        if not investigation_activities.empty:
            inv_count = len(investigation_activities)
            inv_cases = investigation_activities['CaseNumber'].nunique()
            insights.append(
                html.Div([
                    html.Span("🔍 ", style={'fontSize': '16px'}),
                    html.Span(f"**Investigation Activity**: {inv_count:,} investigation events across {inv_cases:,} cases", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Case closure activity using notebook stages
        closure_activities = recent_events[recent_events['LifecycleStage'] == 'Case Closure']
        if not closure_activities.empty:
            closure_count = len(closure_activities)
            insights.append(
                html.Div([
                    html.Span("✅ ", style={'fontSize': '16px'}),
                    html.Span(f"**Case Resolutions**: {closure_count:,} cases closed recently", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Notice creation activity using notebook stages
        notice_activities = recent_events[recent_events['LifecycleStage'] == 'Notice Creation']
        if not notice_activities.empty:
            notice_count = len(notice_activities)
            insights.append(
                html.Div([
                    html.Span("📢 ", style={'fontSize': '16px'}),
                    html.Span(f"**Notice Activity**: {notice_count:,} notices created", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Most active day
        most_active_day = summary_stats.get('most_active_day')
        if most_active_day:
            day_activities = len(recent_events[recent_events['ActionDate'].dt.date == most_active_day])
            insights.append(
                html.Div([
                    html.Span("🏆 ", style={'fontSize': '16px'}),
                    html.Span(f"**Peak Activity**: {most_active_day} had {day_activities:,} activities (busiest day)", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        return html.Div(insights, className="insights-container")
    
    # View state toggle callbacks
    @callback(
        [Output("compliance-recent-activities-view-state", "data"),
         Output("activities-timeline-view-btn", "active"),
         Output("activities-type-view-btn", "active"),
         Output("activities-volume-view-btn", "active"),
         Output("activities-case-view-btn", "active")],
        [Input("activities-timeline-view-btn", "n_clicks"),
         Input("activities-type-view-btn", "n_clicks"),
         Input("activities-volume-view-btn", "n_clicks"),
         Input("activities-case-view-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def toggle_recent_activities_view(timeline_clicks, type_clicks, volume_clicks, case_clicks):
        """Toggle between different recent activities analysis views"""
        triggered = ctx.triggered
        if not triggered:
            return "timeline", True, False, False, False
            
        triggered_id = triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "activities-timeline-view-btn":
            return "timeline", True, False, False, False
        elif triggered_id == "activities-type-view-btn":
            return "activity_type", False, True, False, False
        elif triggered_id == "activities-volume-view-btn":
            return "volume", False, False, True, False
        elif triggered_id == "activities-case-view-btn":
            return "case_activity", False, False, False, True
        
        return "timeline", True, False, False, False
    
    # Details modal callback
    @callback(
        [Output("compliance-activities-details-modal", "is_open"),
         Output("compliance-activities-details-content", "children")],
        [Input("compliance-activities-details-btn", "n_clicks")],
        [State("compliance-activities-details-modal", "is_open"),
         State("compliance-filtered-query-store", "data"),
         State("compliance-recent-activities-view-state", "data"),
         State("compliance-recent-activities-timeframe-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Recent Activities Details Modal Toggle")
    def toggle_recent_activities_details_modal(details_btn_clicks, is_open, filter_selections, view_state, timeframe):
        """Handle opening of recent activities details modal"""
        if details_btn_clicks:
            if not is_open:
                try:
                    # Get filtered data - now much faster since heavy processing is cached
                    base_data = get_compliance_base_data()
                    filtered_data = apply_compliance_filters(base_data, filter_selections or {})
                    recent_events, summary_stats = prepare_recent_activities_data(filtered_data, timeframe)
                    
                    # Create detailed table
                    detailed_table = create_recent_activities_details_table(recent_events, summary_stats, view_state, timeframe)
                    
                    return True, detailed_table
                    
                except Exception as e:
                    print(f"❌ Error generating recent activities details: {e}")
                    error_content = html.Div([
                        html.H4("Error Loading Activity Details", className="text-danger mb-3"),
                        html.P(f"Unable to load detailed breakdown: {str(e)}", className="text-muted")
                    ], className="text-center p-4")
                    return True, error_content
            else:
                return False, no_update
        
        return no_update, no_update
    
    # Main chart and insights callback - NOW MUCH FASTER
    @callback(
        [Output("compliance-recent-activities-chart", "figure"),
         Output("compliance-recent-activities-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-recent-activities-view-state", "data"),
         Input("compliance-recent-activities-timeframe-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Recent Activities Chart Update")
    def update_recent_activities_chart(filter_selections, view_state, timeframe):
        """Update recent activities chart and insights - now using cached processing"""
        
        try:
            # Get filter selections or use defaults
            if not filter_selections:
                filter_selections = {}
            
            # Get base data using shared utility - cached and fast
            base_data = get_compliance_base_data()
            
            if base_data.empty:
                fig = go.Figure()
                fig.add_annotation(
                    text="No compliance data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
                fig.update_layout(
                    title={'text': "Recent Activities - No Data", 'x': 0.5, 'xanchor': 'center'},
                    height=400
                )
                return fig, html.Div("No data available for analysis.", className="text-muted")
            
            # Apply filters using shared utility
            filtered_data = apply_compliance_filters(base_data, filter_selections)
            
            # Prepare recent activities data - now uses cached event history processing
            recent_events, summary_stats = prepare_recent_activities_data(filtered_data, timeframe or "30d")
            
            # Create chart
            fig = create_recent_activities_chart(recent_events, summary_stats, view_state, timeframe)
            
            # Generate insights
            insights = generate_recent_activities_insights(recent_events, summary_stats, view_state)
            
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating recent activities chart: {e}")
            import traceback
            traceback.print_exc()
            
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading activities data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Recent Activities - Error", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to load activities data", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
    
    # Chart modal callback
    @callback(
        [
            Output("compliance-chart-modal", "is_open", allow_duplicate=True),
            Output("compliance-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("compliance-recent-activities-chart-wrapper", "n_clicks"),
            Input("compliance-chart-modal", "is_open")
        ],
        [
            State("compliance-recent-activities-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_recent_activities_chart_modal(wrapper_clicks, modal_is_open, chart_figure, is_open_state):
        """Toggle enlarged recent activities chart modal"""
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        if triggered_id == "compliance-recent-activities-chart-wrapper" and wrapper_clicks and not is_open_state:
            enlarged_chart = create_enlarged_recent_activities_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
        
    @callback(
        Output("compliance-activities-details-modal", "is_open", allow_duplicate=True),
        [Input("compliance-activities-details-close-btn", "n_clicks")],
        [State("compliance-activities-details-modal", "is_open")],
        prevent_initial_call=True
    )
    def close_activities_details_modal(close_clicks, is_open):
        """Close the activities details modal when close button is clicked"""
        if close_clicks and is_open:
            return False
        return no_update

    print("✅ Compliance recent activities callbacks registered")