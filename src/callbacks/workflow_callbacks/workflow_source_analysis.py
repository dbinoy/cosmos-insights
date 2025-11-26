from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import copy
from src.utils.db import run_queries
from inflection import titleize, pluralize
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
                    # print(f"📅 Applying date filter: From {start_dt.date()} To {end_dt.date()}")
                    df_work_items = df_work_items.loc[
                        (df_work_items['CreatedOn'] >= start_dt) & 
                        (df_work_items['ClosedOn'] <= end_dt)
                    ].copy()
                    # print(f"📅 Date filter applied: {len(df_work_items)} work item records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Apply other filters
        if selected_aor is not None and len(selected_aor) > 0 and "All" not in selected_aor:
            df_work_items = df_work_items.loc[df_work_items['AorShortName'].isin(selected_aor)].copy()
            # print(f"🎯 AOR filter applied: {len(df_work_items)} records")

        if selected_case_types is not None and len(selected_case_types) > 0 and "All" not in selected_case_types:
            df_work_items = df_work_items.loc[df_work_items['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
            # print(f"📋 Case Type filter applied: {len(df_work_items)} records")

        if selected_products is not None and len(selected_products) > 0 and "All" not in selected_products:
            df_work_items = df_work_items.loc[df_work_items['Product'].isin(selected_products)].copy()
            print(f"🛍️ Product filter applied: {len(df_work_items)} records")

        if selected_modules is not None and len(selected_modules) > 0 and "All" not in selected_modules:
            df_work_items = df_work_items.loc[df_work_items['Module'].isin(selected_modules)].copy()
            # print(f"🧩 Module filter applied: {len(df_work_items)} records")
            
        if selected_features is not None and len(selected_features) > 0 and "All" not in selected_features:
            df_work_items = df_work_items.loc[df_work_items['Feature'].isin(selected_features)].copy()
            print(f"⭐ Feature filter applied: {len(df_work_items)} records")

        if selected_issues is not None and len(selected_issues) > 0 and "All" not in selected_issues:
            df_work_items = df_work_items.loc[df_work_items['Issue'].isin(selected_issues)].copy()
            # print(f"🐛 Issue filter applied: {len(df_work_items)} records")

        if selected_origins is not None and len(selected_origins) > 0 and "All" not in selected_origins:
            df_work_items = df_work_items.loc[df_work_items['CaseOrigin'].isin(selected_origins)].copy()
            # print(f"📍 Origin filter applied: {len(df_work_items)} records")

        if selected_reasons is not None and len(selected_reasons) > 0 and "All" not in selected_reasons:
            df_work_items = df_work_items.loc[df_work_items['CaseReason'].isin(selected_reasons)].copy()
            # print(f"📝 Reason filter applied: {len(df_work_items)} records")

        if selected_status is not None and len(selected_status) > 0 and "All" not in selected_status:
            df_work_items = df_work_items.loc[df_work_items['WorkItemStatus'].isin(selected_status)].copy()
            # print(f"📊 Status filter applied: {len(df_work_items)} records")

        if selected_priority is not None and len(selected_priority) > 0 and "All" not in selected_priority:
            df_work_items = df_work_items.loc[df_work_items['Priority'].isin(selected_priority)].copy()
            # print(f"⚡ Priority filter applied: {len(df_work_items)} records")

        return df_work_items

    def map_case_origin_group(origin):
        origin = origin.lower() if isinstance(origin, str) else ''
        if origin in ['phone-call']:
            return 'Phone Call'
        elif origin in ['chat']:
            return 'Chat'
        elif origin in [
            'support-email', 'association-support-email', 'email', 
            'compliance-email', 'training-request-email', 'legal-email', 'ceo-email'
        ]:
            return 'Email'
        elif origin in ['crmls-staff']:
            return 'Staff Reported'
        elif origin in ['voicemail']:
            return 'Voicemail'
        else:
            return 'Others'
    
    @monitor_performance("Source Analysis Data Preparation")
    def prepare_source_analysis_data(filtered_data):
        """
        Prepare source/origin analysis data for visualization
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        df = filtered_data.copy()
        df['OriginGroup'] = df['CaseOrigin'].apply(map_case_origin_group)
        grouped = df.groupby('OriginGroup').agg(
            TicketCount=('CaseOrigin', 'count')
        ).reset_index()
        grouped['Percentage'] = (grouped['TicketCount'] / grouped['TicketCount'].sum() * 100).round(1)
        # For hover details: collect all sub-origins per group
        sub_origin_details = (
            df.groupby('OriginGroup')['CaseOrigin']
            .value_counts()
            .groupby(level=0)
            .apply(lambda x: "<br>".join([f"{pluralize(titleize(k[1]))}: {v}" for k, v in x.items()]))
        )
        grouped['Details'] = grouped['OriginGroup'].map(sub_origin_details)
        # Sort by TicketCount descending for top, ascending for least
        grouped_sorted_desc = grouped.sort_values('TicketCount', ascending=False).reset_index(drop=True)
        grouped_sorted_asc = grouped.sort_values('TicketCount', ascending=True).reset_index(drop=True)
        summary_stats = {
            'total_tickets': grouped['TicketCount'].sum(),
            'num_groups': len(grouped),
            'top_group': grouped_sorted_desc.iloc[0]['OriginGroup'] if len(grouped_sorted_desc) > 0 else 'N/A',
            'top_group_count': grouped_sorted_desc.iloc[0]['TicketCount'] if len(grouped_sorted_desc) > 0 else 0,
            'least_group': grouped_sorted_asc.iloc[0]['OriginGroup'] if len(grouped_sorted_asc) > 0 else 'N/A',
            'least_group_count': grouped_sorted_asc.iloc[0]['TicketCount'] if len(grouped_sorted_asc) > 0 else 0
        }
        return grouped, summary_stats    
        
    def generate_source_analysis_insights(origin_counts, summary_stats, filtered_data=None):
        """
        Generate insights for source/origin analysis.
        Shows least used original channel (not consolidated group).
        """
        if origin_counts.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No source/origin data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see source channel insights", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        try:
            insights = []
            total = summary_stats['total_tickets']
            top_group = summary_stats['top_group']
            top_group_count = summary_stats['top_group_count']
            num_groups = summary_stats['num_groups']
            insights.append(f"📊 {total:,} tickets submitted via {num_groups} channels.")
            if top_group:
                pct = (top_group_count / total * 100) if total > 0 else 0
                insights.append(f"🏆 Top Channel: '{top_group}' with {top_group_count:,} tickets ({pct:.1f}%)")
            # Find least used original CaseOrigin
            if filtered_data is not None and not filtered_data.empty:
                origin_counts_raw = (
                    filtered_data['CaseOrigin']
                    .value_counts()
                    .reset_index()
                )
                origin_counts_raw.columns = ['CaseOrigin', 'TicketCount']
                origin_counts_raw = origin_counts_raw.sort_values('TicketCount', ascending=True)
                least_origin_row = origin_counts_raw.iloc[0]
                least_origin = pluralize(titleize(least_origin_row['CaseOrigin']))
                least_count = least_origin_row['TicketCount']
                insights.append(f"🔻 Least Used Channel: '{least_origin}' with {least_count:,} tickets")                
            return html.Div([html.Div(html.Span(i, style={'fontSize': '13px'}), className="mb-2") for i in insights], className="insights-container")
        except Exception as e:
            print(f"❌ Error generating insights::: {e}")
            return html.Div(f"Error generating insights: {str(e)}", className="text-danger p-2")

    @monitor_chart_performance("Source Analysis Chart")
    def create_source_analysis_chart(grouped, summary_stats):
        """
        Create pie chart for grouped ticket source/origin analysis
        """
        if grouped.empty:
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
        fig.add_trace(go.Pie(
            labels=grouped['OriginGroup'],
            values=grouped['TicketCount'],
            textinfo='label+percent',
            hovertemplate="<b>%{label}</b><br>Tickets: %{value}<br>Percent: %{percent}<br><br>Details:<br> %{customdata}<extra></extra>",
            customdata=grouped['Details'],
            marker=dict(line=dict(color='white', width=2))
        ))
        fig.update_layout(
            title={'text': "Ticket Source/Origin Analysis", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            height=400,
            margin={'l': 30, 'r': 30, 't': 60, 'b': 30},
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True
        )
        return fig        


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
            insights = generate_source_analysis_insights(origin_counts, summary_stats, filtered_data)
            return fig, insights
        except Exception as e:
            print(f"❌ Error updating source analysis chart: {e}")
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

    @callback(
        [Output("workflow-source-details-modal", "is_open"),
        Output("workflow-source-details-content", "children")],
        [Input("workflow-source-details-btn", "n_clicks"),
        Input("workflow-source-details-close-btn", "n_clicks")],
        [State("workflow-source-details-modal", "is_open"),
        State("workflow-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    def toggle_source_details_modal(open_click, close_click, is_open, stored_selections):
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if triggered_id == "workflow-source-details-btn" and open_click:
            # Prepare details table
            base_data = get_source_analysis_base_data()
            filtered_data = apply_source_analysis_filters(base_data['work_items'], stored_selections)
            df = filtered_data.copy()
            df['OriginGroup'] = df['CaseOrigin'].apply(map_case_origin_group)
            # Aggregate ticket counts
            agg = (
                df.groupby(['OriginGroup', 'CaseOrigin'])
                .size()
                .reset_index(name='TicketCount')
            )
            # Get total tickets per OriginGroup for sorting
            group_totals = agg.groupby('OriginGroup')['TicketCount'].sum().reset_index()
            # Merge totals for sorting
            agg = agg.merge(group_totals, on='OriginGroup', suffixes=('', '_GroupTotal'))
            # Sort by group total descending, then CaseOrigin ticket count descending
            agg = agg.sort_values(['TicketCount_GroupTotal', 'TicketCount'], ascending=[False, False])
            table = html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Origin Group"),
                        html.Th("CaseOrigin"),
                        html.Th("Ticket Count")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(row['OriginGroup']),
                        html.Td(pluralize(titleize(row['CaseOrigin']))),
                        html.Td(row['TicketCount'])
                    ]) for _, row in agg.iterrows()
                ])
            ], className="table table-hover")
            return True, table
        elif triggered_id == "workflow-source-details-close-btn" and close_click:
            return False, no_update
        return is_open, no_update    