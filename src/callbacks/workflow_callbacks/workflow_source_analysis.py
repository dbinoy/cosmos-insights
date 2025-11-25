from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import copy
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_workflow_source_analysis_callbacks(app):

    @monitor_query_performance("Source Analysis Base Data")
    def get_source_analysis_base_data():
        """
        Fetch base data for source/origin analysis from Fact_WorkFlowItems
        """
        queries = {
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
            """
        }
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("Source Analysis Filter Application")
    def apply_source_analysis_filters(work_items, stored_selections):
        """
        Apply filters to base status distribution data using pandas
        Same pattern as workflow ticket volume
        """
        # print(f"🔍 Applying status distribution filters: {stored_selections}")
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_work_items = pd.DataFrame(work_items).copy()
        
        # print(f"📊 Starting status distribution filtering: {len(df_work_items)} work item records")
        
        if df_work_items.empty:
            return df_work_items
        
        # Parse filter values (same logic as ticket volume)
        selected_aor = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('AOR', '').split(', ') if item.strip("'")]
        selected_case_types = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('CaseTypes', '').split(', ') if item.strip("'")]
        selected_status = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Status', '').split(', ') if item.strip("'")]
        selected_priority = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Priority', '').split(', ') if item.strip("'")]
        selected_origins = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Origins', '').split(', ') if item.strip("'")]
        selected_reasons = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Reasons', '').split(', ') if item.strip("'")]
        selected_products = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Products', '').split(', ') if item.strip("'")]
        selected_features = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Features', '').split(', ') if item.strip("'")]
        selected_modules = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Modules', '').split(', ') if item.strip("'")]
        selected_issues = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Issues', '').split(', ') if item.strip("'")]
        start_date = stored_selections.get('Day_From')
        end_date = stored_selections.get('Day_To')
        
        # Parse dates
        if not df_work_items.empty:
            df_work_items['CreatedOn'] = pd.to_datetime(df_work_items['CreatedOn'], errors='coerce')
            df_work_items['ClosedOn'] = pd.to_datetime(df_work_items['ClosedOn'], errors='coerce')
            df_work_items = df_work_items.dropna(subset=['CreatedOn']).copy()

            # Apply date range filter if specified
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    print(f"📅 Applying date filter: From {start_dt.date()} To {end_dt.date()}")
                    df_work_items = df_work_items.loc[
                        (df_work_items['CreatedOn'] >= start_dt) & 
                        (df_work_items['ClosedOn'] <= end_dt)
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

    @monitor_performance("Source Analysis Data Preparation")
    def prepare_source_analysis_data(filtered_data):
        """
        Prepare source/origin analysis data for visualization
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        df = filtered_data.copy()
        # Group by CaseOrigin and count tickets
        origin_counts = df['CaseOrigin'].value_counts().reset_index()
        origin_counts.columns = ['CaseOrigin', 'TicketCount']
        # Calculate percentages
        total = origin_counts['TicketCount'].sum()
        origin_counts['Percentage'] = (origin_counts['TicketCount'] / total * 100).round(1)
        summary_stats = {
            'total_tickets': total,
            'num_origins': len(origin_counts),
            'top_origin': origin_counts.iloc[0]['CaseOrigin'] if len(origin_counts) > 0 else 'N/A',
            'top_origin_count': origin_counts.iloc[0]['TicketCount'] if len(origin_counts) > 0 else 0
        }
        return origin_counts, summary_stats

    @monitor_chart_performance("Source Analysis Chart")
    def create_source_analysis_chart(origin_counts, summary_stats):
        """
        Create pie/bar chart for ticket source/origin analysis
        """
        if origin_counts.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No source/origin data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={'text': "Ticket Source/Origin Analysis", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

        fig = go.Figure()
        # Pie chart for distribution
        fig.add_trace(go.Pie(
            labels=origin_counts['CaseOrigin'],
            values=origin_counts['TicketCount'],
            textinfo='label+percent',
            hovertemplate="<b>%{label}</b><br>Tickets: %{value}<br>Percent: %{percent}<extra></extra>",
            marker=dict(line=dict(color='white', width=2))
        ))
        fig.update_layout(
            title={'text': "Ticket Source/Origin Analysis", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            height=400,
            margin={'l': 30, 'r': 30, 't': 60, 'b': 30},
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True,
            # legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=11))
        )
        return fig

    def generate_source_analysis_insights(origin_counts, summary_stats):
        """
        Generate insights for source/origin analysis
        """
        if origin_counts.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No source/origin data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see source channel insights", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        try:
            insights = []
            total = summary_stats['total_tickets']
            top_origin = summary_stats['top_origin']
            top_count = summary_stats['top_origin_count']
            num_origins = summary_stats['num_origins']
            insights.append(f"📊 {total:,} tickets submitted via {num_origins} channels.")
            if top_origin:
                pct = (top_count / total * 100) if total > 0 else 0
                insights.append(f"🏆 Top Channel: '{top_origin}' with {top_count:,} tickets ({pct:.1f}%)")
            if num_origins > 1:
                least_origin = origin_counts.iloc[-1]['CaseOrigin']
                least_count = origin_counts.iloc[-1]['TicketCount']
                insights.append(f"🔻 Least Used Channel: '{least_origin}' with {least_count:,} tickets")
            return html.Div([html.Div(html.Span(i, style={'fontSize': '13px'}), className="mb-2") for i in insights], className="insights-container")
        except Exception as e:
            return html.Div(f"Error generating insights: {str(e)}", className="text-danger p-2")

    # Main chart and insights callback
    @callback(
        [Output("workflow-source-analysis-chart", "figure"),
         Output("workflow-source-insights", "children")],
        [Input("workflow-filtered-query-store", "data")],
        prevent_initial_call=False
    )
    @monitor_performance("Source Analysis Chart Update")
    def update_source_analysis_chart(stored_selections):
        """
        Update source/origin chart and insights based on filters
        """
        try:
            base_data = get_source_analysis_base_data()
            filtered_data = apply_source_analysis_filters(base_data['work_items'], stored_selections)
            origin_counts, summary_stats = prepare_source_analysis_data(filtered_data)
            fig = create_source_analysis_chart(origin_counts, summary_stats)
            insights = generate_source_analysis_insights(origin_counts, summary_stats)
            return fig, insights
        except Exception as e:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading source analysis data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Ticket Source/Origin Analysis - Error", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig, html.Div("Error generating insights", className="text-danger p-2")

    # Enlarged chart modal callback
    @monitor_chart_performance("Enlarged Source Analysis Chart")
    def create_enlarged_source_analysis_chart(original_figure):
        """
        Create an enlarged version of the source analysis chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        try:
            enlarged_fig = copy.deepcopy(original_figure)
            enlarged_fig['layout'].update({
                'height': 600,
                'margin': {'l': 80, 'r': 80, 't': 100, 'b': 120},
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}
                },
                'legend': {
                    **enlarged_fig['layout'].get('legend', {}),
                    'font': {'size': 13}
                }
            })
            # Update pie chart for better visibility
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') == 'pie':
                        trace.update({
                            'textfont': {'size': 13},
                            'marker': {
                                **trace.get('marker', {}),
                                'line': {'color': 'white', 'width': 3}
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
                        'filename': 'workflow_source_analysis_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
        except Exception as e:
            return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")

    @callback(
        [Output("workflow-chart-modal", "is_open", allow_duplicate=True),
         Output("workflow-modal-chart-content", "children", allow_duplicate=True)],
        [Input("workflow-source-analysis-chart", "clickData"),
         Input("workflow-chart-modal", "is_open")],
        [State("workflow-source-analysis-chart", "figure"),
         State("workflow-chart-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_source_analysis_chart_modal(chart_click, modal_is_open, chart_figure, is_open_state):
        """
        Open enlarged chart modal when chart is clicked
        """
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if triggered_id == "workflow-source-analysis-chart" and chart_click and not is_open_state:
            enlarged_chart = create_enlarged_source_analysis_chart(chart_figure)
            return True, enlarged_chart
        return no_update, no_update