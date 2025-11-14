from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_workflow_ticket_volume_callbacks(app):
    """
    Register ticket volume over time callbacks
    Matches the component IDs from the layout file
    """
    @monitor_query_performance("Ticket Volume Base Data")
    def get_ticket_volume_base_data():
        """
        Fetch base data for ticket volume analysis
        Uses consumable fact tables with minimal joins
        """
        
        queries = {
            # Get work items data with time series info
            "work_items": """
                SELECT 
                    w.WorkItemId,
                    w.CreatedOn,
                    w.ClosedOn,
                    w.EscalatedOn,
                    w.WorkItemDefinitionShortCode,
                    w.WorkItemStatus,
                    w.IsEscalated,
                    w.AssignedTo,
                    w.AorShortName,
                    w.CaseOrigin,
                    w.CaseReason,
                    w.Feature,
                    w.Issue,
                    w.Module,
                    w.Priority,
                    w.Product
                FROM [consumable].[Fact_WorkFlowItems] w
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

        return run_queries(queries, 'workflow', len(queries))

    def apply_ticket_volume_filters(base_data, stored_selections):
        """
        Apply filters to base ticket volume data using pandas
        Same pattern as workflow summary cards
        """
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_work_items = pd.DataFrame(base_data.get('work_items', [])).copy()
        
        print(f"📊 Starting ticket volume filtering: {len(df_work_items)} work item records")
        
        if df_work_items.empty:
            return df_work_items
        
        # Parse filter values (same logic as summary cards)
        selected_aor = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('AOR', '').split(', ') if item.strip("'")]
        selected_case_types = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('CaseTypes', '').split(', ') if item.strip("'")]
        selected_status = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Status', '').split(', ') if item.strip("'")]
        selected_priority = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Priority', '').split(', ') if item.strip("'")]
        selected_origins = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Origins', '').split(', ') if item.strip("'")]
        selected_reasons = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Reasons', '').split(', ') if item.strip("'")]
        selected_products = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Products', '').split(', ') if item.strip("'")]
        selected_features = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Features', '').split(', ') if item.strip("'")]
        selected_modules = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Modules', '').split(', ') if item.strip("'")]
        selected_issues = [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Issues', '').split(', ') if item.strip("'")]
        start_date = stored_selections.get('StartDate')
        end_date = stored_selections.get('EndDate')
        
        # Parse dates
        if not df_work_items.empty:
            df_work_items['CreatedOn'] = pd.to_datetime(df_work_items['CreatedOn'], errors='coerce')
            df_work_items['ClosedOn'] = pd.to_datetime(df_work_items['ClosedOn'], errors='coerce')
            df_work_items = df_work_items.dropna(subset=['CreatedOn']).copy()
            df_work_items = df_work_items[df_work_items['ClosedOn'] >= df_work_items['CreatedOn']].copy()

            # Apply date range filter if specified
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df_work_items = df_work_items.loc[
                        (df_work_items['CreatedOn'] >= start_dt) & 
                        (df_work_items['CreatedOn'] <= end_dt)
                    ].copy()
                    print(f"📅 Date filter applied: {len(df_work_items)} work item records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Apply other filters
        if selected_aor is not None and len(selected_aor) > 0 and "All" not in selected_aor:
            df_work_items = df_work_items.loc[df_work_items['AorShortName'].isin(selected_aor)].copy()
            print(f"🎯 AOR filter applied: {len(df_work_items)} records")

        if selected_case_types is not None and len(selected_case_types) > 0 and "All" not in selected_case_types:
            df_work_items = df_work_items.loc[df_work_items['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
            print(f"📋 Case Type filter applied: {len(df_work_items)} records")

        if selected_products is not None and len(selected_products) > 0 and "All" not in selected_products:
            df_work_items = df_work_items.loc[df_work_items['Product'].isin(selected_products)].copy()
            print(f"🛍️ Product filter applied: {len(df_work_items)} records")

        if selected_modules is not None and len(selected_modules) > 0 and "All" not in selected_modules:
            df_work_items = df_work_items.loc[df_work_items['Module'].isin(selected_modules)].copy()
            print(f"🧩 Module filter applied: {len(df_work_items)} records")
            
        if selected_features is not None and len(selected_features) > 0 and "All" not in selected_features:
            df_work_items = df_work_items.loc[df_work_items['Feature'].isin(selected_features)].copy()
            print(f"⭐ Feature filter applied: {len(df_work_items)} records")

        if selected_issues is not None and len(selected_issues) > 0 and "All" not in selected_issues:
            df_work_items = df_work_items.loc[df_work_items['Issue'].isin(selected_issues)].copy()
            print(f"🐛 Issue filter applied: {len(df_work_items)} records")

        if selected_origins is not None and len(selected_origins) > 0 and "All" not in selected_origins:
            df_work_items = df_work_items.loc[df_work_items['CaseOrigin'].isin(selected_origins)].copy()
            print(f"📍 Origin filter applied: {len(df_work_items)} records")

        if selected_reasons is not None and len(selected_reasons) > 0 and "All" not in selected_reasons:
            df_work_items = df_work_items.loc[df_work_items['CaseReason'].isin(selected_reasons)].copy()
            print(f"📝 Reason filter applied: {len(df_work_items)} records")

        if selected_status is not None and len(selected_status) > 0 and "All" not in selected_status:
            df_work_items = df_work_items.loc[df_work_items['WorkItemStatus'].isin(selected_status)].copy()
            print(f"📊 Status filter applied: {len(df_work_items)} records")

        if selected_priority is not None and len(selected_priority) > 0 and "All" not in selected_priority:
            df_work_items = df_work_items.loc[df_work_items['Priority'].isin(selected_priority)].copy()
            print(f"⚡ Priority filter applied: {len(df_work_items)} records")
        
        return df_work_items

    @monitor_performance("Ticket Volume Time Series Preparation")
    def prepare_ticket_volume_time_series(filtered_data, time_granularity):
        """
        Prepare time series data for ticket volume analysis
        """
        # print(f"📊 Preparing ticket volume time series: granularity={time_granularity}, records={len(filtered_data)}")
        if filtered_data.empty:
            return pd.DataFrame()
        
        try:
            df = filtered_data.copy()
            
            # Create time period columns based on granularity
            if time_granularity == "daily":
                df['TimePeriod'] = df['CreatedOn'].dt.date
                df['TimeLabel'] = df['CreatedOn'].dt.strftime('%Y-%m-%d')
                df['SortKey'] = df['CreatedOn'].dt.date
            elif time_granularity == "weekly":
                df['TimePeriod'] = df['CreatedOn'].dt.to_period('W')
                df['TimeLabel'] = df['CreatedOn'].dt.strftime('Week of %Y-%m-%d')
                df['SortKey'] = df['CreatedOn'].dt.to_period('W').dt.start_time
            else:  # monthly
                df['TimePeriod'] = df['CreatedOn'].dt.to_period('M')
                df['TimeLabel'] = df['CreatedOn'].dt.strftime('%Y-%m')
                df['SortKey'] = df['CreatedOn'].dt.to_period('M').dt.start_time
            
            # Calculate tickets created by time period
            created_series = df.groupby('TimeLabel').agg({
                'WorkItemId': 'count',
                'SortKey': 'first'
            }).reset_index()
            created_series = created_series.rename(columns={'WorkItemId': 'TicketsCreated'})
            
            # Calculate tickets closed by time period
            closed_df = df[df['ClosedOn'].notna()].copy()
            if not closed_df.empty:
                if time_granularity == "daily":
                    closed_df['ClosedTimePeriod'] = closed_df['ClosedOn'].dt.date
                    closed_df['ClosedTimeLabel'] = closed_df['ClosedOn'].dt.strftime('%Y-%m-%d')
                    closed_df['ClosedSortKey'] = closed_df['ClosedOn'].dt.date
                elif time_granularity == "weekly":
                    closed_df['ClosedTimePeriod'] = closed_df['ClosedOn'].dt.to_period('W')
                    closed_df['ClosedTimeLabel'] = closed_df['ClosedOn'].dt.strftime('Week of %Y-%m-%d')
                    closed_df['ClosedSortKey'] = closed_df['ClosedOn'].dt.to_period('W').dt.start_time
                else:  # monthly
                    closed_df['ClosedTimePeriod'] = closed_df['ClosedOn'].dt.to_period('M')
                    closed_df['ClosedTimeLabel'] = closed_df['ClosedOn'].dt.strftime('%Y-%m')
                    closed_df['ClosedSortKey'] = closed_df['ClosedOn'].dt.to_period('M').dt.start_time
                
                closed_series = closed_df.groupby('ClosedTimeLabel').agg({
                    'WorkItemId': 'count',
                    'ClosedSortKey': 'first'
                }).reset_index()
                closed_series = closed_series.rename(columns={
                    'WorkItemId': 'TicketsClosed',
                    'ClosedTimeLabel': 'TimeLabel',
                    'ClosedSortKey': 'SortKey'
                })
            else:
                closed_series = pd.DataFrame(columns=['TimeLabel', 'TicketsClosed', 'SortKey'])
            
            # Merge created and closed data
            time_series = created_series.merge(closed_series, on='TimeLabel', how='outer', suffixes=('', '_closed'))
            time_series['TicketsCreated'] = time_series['TicketsCreated'].fillna(0)
            time_series['TicketsClosed'] = time_series['TicketsClosed'].fillna(0)
            time_series['SortKey'] = time_series['SortKey'].fillna(time_series['SortKey_closed'])
            
            # Calculate active tickets (cumulative)
            time_series = time_series.sort_values('SortKey').reset_index(drop=True)
            time_series['NetChange'] = time_series['TicketsCreated'] - time_series['TicketsClosed']
            time_series['ActiveTickets'] = time_series['NetChange'].cumsum()
            
            # Ensure active tickets don't go negative
            time_series['ActiveTickets'] = time_series['ActiveTickets'].clip(lower=0)
            
            print(f"📊 Prepared ticket volume time series: {len(time_series)} time periods")
            return time_series
            
        except Exception as e:
            print(f"❌ Error preparing ticket volume time series: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @monitor_chart_performance("Ticket Volume Chart")
    def create_ticket_volume_chart(time_series_data, time_granularity):
        """
        Create interactive ticket volume chart using plotly.graph_objects
        """
        if time_series_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No ticket volume data available for selected filters and time period",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Ticket Volume Over Time",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, showticklabels=False),
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            # Sort data by time
            df = time_series_data.sort_values('SortKey').reset_index(drop=True)
            
            # Create figure
            fig = go.Figure()
            
            # Add tickets created trace
            fig.add_trace(go.Scatter(
                x=df['TimeLabel'],
                y=df['TicketsCreated'],
                mode='lines+markers',
                name='Tickets Created',
                line=dict(color='#2E86AB', width=2),
                marker=dict(size=6),
                hovertemplate="<b>Tickets Created</b><br>Time: %{x}<br>Count: %{y:,.0f}<extra></extra>"
            ))
            
            # Add tickets closed trace
            fig.add_trace(go.Scatter(
                x=df['TimeLabel'],
                y=df['TicketsClosed'],
                mode='lines+markers',
                name='Tickets Closed',
                line=dict(color='#A23B72', width=2),
                marker=dict(size=6),
                hovertemplate="<b>Tickets Closed</b><br>Time: %{x}<br>Count: %{y:,.0f}<extra></extra>"
            ))
            
            # Add active tickets trace
            fig.add_trace(go.Scatter(
                x=df['TimeLabel'],
                y=df['ActiveTickets'],
                mode='lines+markers',
                name='Active Tickets',
                line=dict(color='#F18F01', width=2, dash='dot'),
                marker=dict(size=6),
                hovertemplate="<b>Active Tickets</b><br>Time: %{x}<br>Count: %{y:,.0f}<extra></extra>"
            ))
            
            # Update layout
            granularity_title = time_granularity.title()
            fig.update_layout(
                title={
                    'text': f"Ticket Volume Over Time ({granularity_title})",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': 'Time Period',
                    'showgrid': False,
                    'tickfont': {'size': 10},
                    'tickangle': -45
                },
                yaxis={
                    'title': 'Number of Tickets',
                    'showgrid': True,
                    'gridcolor': '#f0f0f0'
                },
                height=400,
                margin={'l': 60, 'r': 50, 't': 80, 'b': 100},
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
                hovermode='x unified'
            )
            
            print(f"📊 Created ticket volume chart with {len(df)} time periods")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating ticket volume chart: {e}")
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
                    'text': "Ticket Volume Over Time - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_performance("Ticket Volume Insights Generation")
    def generate_ticket_volume_insights(time_series_data, time_granularity):
        """
        Generate automated insights from ticket volume data
        """
        if time_series_data.empty:
            return "No insights available - insufficient data."
        
        try:
            insights = []
            df = time_series_data.sort_values('SortKey').reset_index(drop=True)
            
            # Overall statistics
            total_created = df['TicketsCreated'].sum()
            total_closed = df['TicketsClosed'].sum()
            avg_created = df['TicketsCreated'].mean()
            avg_closed = df['TicketsClosed'].mean()
            current_active = df['ActiveTickets'].iloc[-1] if len(df) > 0 else 0
            
            # Peak analysis
            peak_created_idx = df['TicketsCreated'].idxmax()
            peak_created_period = df.loc[peak_created_idx, 'TimeLabel']
            peak_created_count = df.loc[peak_created_idx, 'TicketsCreated']
            
            # Trend analysis
            if len(df) > 1:
                recent_periods = min(3, len(df))
                recent_avg_created = df['TicketsCreated'].tail(recent_periods).mean()
                earlier_avg_created = df['TicketsCreated'].head(recent_periods).mean()
                
                if earlier_avg_created > 0:
                    trend_pct = ((recent_avg_created - earlier_avg_created) / earlier_avg_created) * 100
                    trend_direction = "increasing" if trend_pct > 5 else "decreasing" if trend_pct < -5 else "stable"
                else:
                    trend_direction = "stable"
                
                insights.extend([
                    f"📊 **Volume Overview**: {total_created:,.0f} tickets created, {total_closed:,.0f} closed ({time_granularity.lower()})",
                    f"🏆 **Peak Period**: {peak_created_period} had highest volume with {peak_created_count:,.0f} tickets created",
                    f"📈 **Current Trend**: Ticket creation is {trend_direction} with {current_active:,.0f} currently active"
                ])
            else:
                insights.extend([
                    f"📊 **Volume Overview**: {total_created:,.0f} tickets created, {total_closed:,.0f} closed",
                    f"📈 **Current Status**: {current_active:,.0f} tickets currently active"
                ])
            
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
            print(f"❌ Error generating ticket volume insights: {e}")
            return "Unable to generate insights due to data processing error."

    # Time granularity button callbacks
    @callback(
        [Output("workflow-volume-daily-btn", "active"),
         Output("workflow-volume-weekly-btn", "active"),
         Output("workflow-volume-monthly-btn", "active")],
        [Input("workflow-volume-daily-btn", "n_clicks"),
         Input("workflow-volume-weekly-btn", "n_clicks"),
         Input("workflow-volume-monthly-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def update_volume_granularity_buttons(daily_clicks, weekly_clicks, monthly_clicks):
        """Update button states for time granularity selection"""
        triggered = ctx.triggered
        if not triggered:
            return False, True, False  # Default to weekly
        
        button_id = triggered[0]['prop_id'].split('.')[0]
        
        if button_id == "workflow-volume-daily-btn":
            return True, False, False
        elif button_id == "workflow-volume-monthly-btn":
            return False, False, True
        else:  # weekly or default
            return False, True, False

    @callback(
        [Output("workflow-ticket-volume-chart", "figure"),
         Output("workflow-volume-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
         Input("workflow-volume-daily-btn", "n_clicks"),
         Input("workflow-volume-weekly-btn", "n_clicks"),
         Input("workflow-volume-monthly-btn", "n_clicks")],
        prevent_initial_call=False
    )
    @monitor_performance("Ticket Volume Chart Update")
    def update_ticket_volume_chart(stored_selections, daily_clicks, weekly_clicks, monthly_clicks):
        """
        Update ticket volume chart based on filter selections and time granularity
        """
        try:
            # Determine time granularity from button clicks
            triggered = ctx.triggered
            if triggered and len(triggered) > 0:
                button_id = triggered[0]['prop_id'].split('.')[0]
                if button_id == "workflow-volume-daily-btn":
                    time_granularity = "daily"
                elif button_id == "workflow-volume-monthly-btn":
                    time_granularity = "monthly"
                else:
                    time_granularity = "weekly"
            else:
                time_granularity = "weekly"  # default
            
            print(f"🔄 Updating ticket volume chart: granularity={time_granularity}")
            
            # Get base data
            base_data = get_ticket_volume_base_data()
            
            # Apply filters
            filtered_data = apply_ticket_volume_filters(base_data, stored_selections)
            
            # Prepare time series data
            time_series_data = prepare_ticket_volume_time_series(filtered_data, time_granularity)
            
            # Create visualization
            fig = create_ticket_volume_chart(time_series_data, time_granularity)
            
            # Generate insights
            insights = generate_ticket_volume_insights(time_series_data, time_granularity)
            
            print(f"✅ Ticket volume chart updated successfully ({time_granularity})")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating ticket volume chart: {e}")
            
            # Return error chart and message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading ticket volume data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Ticket Volume Over Time - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig, f"Error generating insights: {str(e)}"

    print("✅ Workflow ticket volume callbacks registered")

def register_workflow_ticket_volume_modal_callbacks(app):
    """
    Register callbacks for workflow ticket volume chart modal functionality
    """
    print("Registering Workflow Ticket Volume Chart Modal callbacks...")
    
    @monitor_chart_performance("Enlarged Ticket Volume Chart")
    def create_enlarged_ticket_volume_chart(original_figure):
        """
        Create an enlarged version of the ticket volume chart for modal display
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
                        'filename': 'workflow_ticket_volume_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged ticket volume chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )
            
    @callback(
        [Output("workflow-chart-modal", "is_open", allow_duplicate=True),
        Output("workflow-modal-chart-content", "children", allow_duplicate=True)],
        [Input("workflow-volume-chart-wrapper", "n_clicks")],
        [State("workflow-chart-modal", "is_open"),
        State("workflow-ticket-volume-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Ticket Volume Modal Toggle")
    def toggle_ticket_volume_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of ticket volume chart modal using SHARED modal
        Same approach as training charts
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        print(f"🔄 Ticket Volume Modal callback triggered by: {triggered_id}")
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "workflow-volume-chart-wrapper" and chart_wrapper_clicks and not is_open:
            print("📊 Ticket volume chart wrapper clicked! Opening modal...")
            
            if not chart_figure or not chart_figure.get('data'):
                print("⚠️ No ticket volume chart figure data available")
                return no_update, no_update
            
            print("✅ Opening ticket volume modal with chart data")
            enlarged_chart = create_enlarged_ticket_volume_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
    
    print("✅ Workflow Ticket Volume Chart Modal callbacks registered successfully")