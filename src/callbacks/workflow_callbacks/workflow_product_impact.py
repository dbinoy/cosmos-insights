from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import copy
from src.utils.db import run_queries
from inflection import titleize, pluralize
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_workflow_product_impact_callbacks(app):

    @monitor_query_performance("Product Impact Base Data")
    def get_product_impact_base_data():
        """
        Fetch base data for product/feature impact from Fact_WorkFlowItems
        """
        queries = {
            "work_items": """
                SELECT 
                    WorkItemId,
                    CreatedOn,
                    ClosedOn,
                    Product,
                    Feature,
                    CaseOrigin,
                    WorkItemStatus,
                    Priority,
                    WorkItemDefinitionShortCode,
                    AorShortName,
                    CaseReason,
                    Issue,
                    Module
                FROM [consumable].[Fact_WorkFlowItems]
            """
        }
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("Product Impact Filter Application")
    def apply_product_impact_filters(work_items, stored_selections):
        """
        Apply filters to product impact data using pandas
        Follows the same pattern as apply_source_analysis_filters
        """
        if not stored_selections:
            stored_selections = {}

        df = pd.DataFrame(work_items).copy()
        if df.empty:
            return df

        # Parse filter values
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
        if not df.empty:
            df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
            df['ClosedOn'] = pd.to_datetime(df['ClosedOn'], errors='coerce')
            df = df.dropna(subset=['CreatedOn']).copy()

            # Apply date range filter if specified
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df.loc[
                        (df['CreatedOn'] >= start_dt) & 
                        (df['ClosedOn'] <= end_dt)
                    ].copy()
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")

        # Apply other filters
        if selected_aor and "All" not in selected_aor:
            df = df.loc[df['AorShortName'].isin(selected_aor)].copy()
        if selected_case_types and "All" not in selected_case_types:
            df = df.loc[df['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
        if selected_products and "All" not in selected_products:
            df = df.loc[df['Product'].isin(selected_products)].copy()
        if selected_modules and "All" not in selected_modules:
            df = df.loc[df['Module'].isin(selected_modules)].copy()
        if selected_features and "All" not in selected_features:
            df = df.loc[df['Feature'].isin(selected_features)].copy()
        if selected_issues and "All" not in selected_issues:
            df = df.loc[df['Issue'].isin(selected_issues)].copy()
        if selected_origins and "All" not in selected_origins:
            df = df.loc[df['CaseOrigin'].isin(selected_origins)].copy()
        if selected_reasons and "All" not in selected_reasons:
            df = df.loc[df['CaseReason'].isin(selected_reasons)].copy()
        if selected_status and "All" not in selected_status:
            df = df.loc[df['WorkItemStatus'].isin(selected_status)].copy()
        if selected_priority and "All" not in selected_priority:
            df = df.loc[df['Priority'].isin(selected_priority)].copy()

        return df    
    
    @monitor_performance("Product Impact Data Preparation")
    def prepare_product_impact_data(filtered_data, top_count=15):
        """
        Prepare product/feature impact data for visualization
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        df = filtered_data.copy()
        # Group by Product and Feature, count tickets
        impact_counts = (
            df.groupby(['Product', 'Feature'])
            .size()
            .reset_index(name='TicketCount')
            .sort_values('TicketCount', ascending=False)
        )
        # Top N by ticket count
        impact_counts = impact_counts.head(top_count)
        summary_stats = {
            'total_tickets': df.shape[0],
            'num_products': df['Product'].nunique(),
            'num_features': df['Feature'].nunique(),
            'top_product': impact_counts.iloc[0]['Product'] if len(impact_counts) > 0 else 'N/A',
            'top_feature': impact_counts.iloc[0]['Feature'] if len(impact_counts) > 0 else 'N/A',
            'top_count': impact_counts.iloc[0]['TicketCount'] if len(impact_counts) > 0 else 0
        }
        return impact_counts, summary_stats

    @monitor_chart_performance("Product Impact Chart")
    def create_product_impact_bar_chart(impact_counts, summary_stats):
        """
        Create bar chart for product/feature impact
        """
        if impact_counts.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No product/feature data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={'text': "Product/Feature Impact", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[f"{titleize(row['Product'])} / {titleize(row['Feature'])}" for _, row in impact_counts.iterrows()],
            y=impact_counts['TicketCount'],
            text=impact_counts['TicketCount'],
            textposition='auto',
            marker=dict(color='#3498db'),
            hovertemplate="<b>%{x}</b><br>Tickets: %{y}<extra></extra>"
        ))
        fig.update_layout(
            title={'text': "Product/Feature Impact", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            height=400,
            margin={'l': 40, 'r': 40, 't': 60, 'b': 80},
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis_title="Product / Feature",
            yaxis_title="Ticket Count"
        )
        return fig

    @monitor_chart_performance("Product Impact Stacked Chart")
    def create_product_impact_stacked_chart(filtered_data, top_count):
        df = filtered_data.copy()
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No product/feature data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(title="Product/Feature Impact (Stacked Bar)", height=400)
            return fig

        top_products = (
            df.groupby('Product').size().reset_index(name='TicketCount')
            .sort_values('TicketCount', ascending=False)
            .head(top_count)['Product']
            .tolist()
        )
        df_top = df[df['Product'].isin(top_products)]
        grouped = df_top.groupby(['Product', 'Feature']).size().reset_index(name='TicketCount')

        fig = go.Figure()
        for feature in grouped['Feature'].unique():
            feature_data = grouped[grouped['Feature'] == feature]
            fig.add_trace(go.Bar(
                x=feature_data['Product'],
                y=feature_data['TicketCount'],
                name=titleize(feature),
                text=feature_data['TicketCount'],
                textposition='auto'
            ))
        fig.update_layout(
            barmode='stack',
            title={'text': "Product/Feature Impact (Stacked Bar)", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            height=400,
            margin={'l': 40, 'r': 40, 't': 60, 'b': 80},
            xaxis_title="Product",
            yaxis_title="Ticket Count",
            legend_title="Feature"
        )
        return fig

    @monitor_chart_performance("Product Impact Bubble Chart")
    def create_product_impact_bubble_chart(filtered_data, top_count):
        df = filtered_data.copy()
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No product/feature data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(title="Product/Feature Impact (Bubble Chart)", height=400)
            return fig

        grouped = (
            df.groupby(['Product', 'Feature'])
            .size()
            .reset_index(name='TicketCount')
            .sort_values('TicketCount', ascending=False)
            .head(top_count)
        )
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=grouped['Product'],
            y=grouped['Feature'],
            mode='markers',
            marker=dict(
                size=grouped['TicketCount'],
                sizemode='area',
                sizeref=max(grouped['TicketCount'])/60 if max(grouped['TicketCount']) > 0 else 1,
                color=grouped['TicketCount'],
                colorscale='Blues',
                showscale=True,
                line=dict(width=2, color='DarkSlateGrey')
            ),
            text=[f"Tickets: {v}" for v in grouped['TicketCount']],
            hovertemplate="<b>%{x}</b> / %{y}<br>Tickets: %{marker.size}<extra></extra>"
        ))
        fig.update_layout(
            title={'text': "Product/Feature Impact (Bubble Chart)", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            height=400,
            margin={'l': 40, 'r': 40, 't': 60, 'b': 80},
            xaxis_title="Product",
            yaxis_title="Feature"
        )
        return fig

    @monitor_chart_performance("Product Impact Treemap Chart")
    def create_product_impact_treemap_chart(filtered_data, top_count):
        df = filtered_data.copy()
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No product/feature data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(title="Product/Feature Impact (Treemap)", height=400)
            return fig

        grouped = (
            df.groupby(['Product', 'Feature'])
            .size()
            .reset_index(name='TicketCount')
            .sort_values('TicketCount', ascending=False)
            .head(top_count)
        )

        fig = px.treemap(
            grouped,
            path=['Product', 'Feature'],
            values='TicketCount',
            title="Product/Feature Impact (Treemap)",
            color='TicketCount',
            color_continuous_scale='Blues',
            height=400
        )
        fig.update_layout(margin={'l': 40, 'r': 40, 't': 60, 'b': 80})
        return fig
     
    @monitor_performance("Product Impact Insights Generation")
    def generate_product_impact_insights(impact_counts, summary_stats, filtered_data=None):
        """
        Generate meaningful insights for product/feature impact.
        """ 

        if impact_counts.empty or not summary_stats:
            return html.Div([
                html.Div("📊 No product/feature data available for current filter selection", className="mb-2", style={'fontSize': '13px'}),
                html.Div("🔍 Try adjusting your filters to see product/feature insights", className="mb-2", style={'fontSize': '13px'})
            ], className="insights-container")
        try:
            insights = []

            # 1. Product with highest total ticket volume
            if filtered_data is not None and not filtered_data.empty:
                product_ticket_counts = (
                    filtered_data.groupby('Product')
                    .size()
                    .reset_index(name='TicketCount')
                    .sort_values('TicketCount', ascending=False)
                )
                top_product_row = product_ticket_counts.iloc[0]
                top_product = titleize(top_product_row['Product'])
                top_product_count = top_product_row['TicketCount']
                insights.append(
                    f"📈 '{top_product}' generates the highest total number of tickets ({top_product_count:,}). "
                    f"Consider prioritizing support and improvement efforts for this product."
                )

                # 2. Product with most number of different features generating tickets
                product_feature_counts = (
                    filtered_data.groupby('Product')['Feature']
                    .nunique()
                    .reset_index(name='FeatureCount')
                    .sort_values('FeatureCount', ascending=False)
                )
                most_features_row = product_feature_counts.iloc[0]
                most_features_product = titleize(most_features_row['Product'])
                most_features_count = most_features_row['FeatureCount']
                insights.append(
                    f"🧩 '{most_features_product}' has the widest range of features generating tickets ({most_features_count} features). "
                    f"This may indicate complexity or broad usage, and could benefit from targeted feature-level analysis."
                )

                # 3. Recurring issues tied to specific products/features
                recurring_issues = (
                    filtered_data.groupby(['Product', 'Feature', 'Issue'])
                    .size()
                    .reset_index(name='Count')
                    .sort_values('Count', ascending=False)
                )
                recurring_issues = recurring_issues[recurring_issues['Issue'].notna() & (recurring_issues['Issue'] != '')]
                if not recurring_issues.empty:
                    top_issue_row = recurring_issues.iloc[0]
                    issue_product = titleize(top_issue_row['Product'])
                    issue_feature = titleize(top_issue_row['Feature'])
                    issue_name = titleize(top_issue_row['Issue'])
                    issue_count = top_issue_row['Count']
                    insights.append(
                        f"🔁 The most frequently reported issue is '{issue_name}' for the '{issue_feature}' feature of '{issue_product}' ({issue_count:,} tickets). "
                        f"Addressing this issue could reduce overall ticket volume."
                    )
                else:
                    insights.append("No recurring issues were identified for any product or feature in the current selection.")

            return html.Div([html.Div(i, className="mb-2", style={'fontSize': '13px'}) for i in insights], className="insights-container")
        except Exception as e:
            return html.Div(f"Error generating insights: {str(e)}", className="text-danger p-2")

    @callback(
        [
            Output("workflow-product-impact-chart", "figure"),
            Output("workflow-product-insights", "children"),
            Output("product-impact-bar-btn", "active"),
            Output("product-impact-stacked-btn", "active"),
            Output("product-impact-bubble-btn", "active"),
            Output("product-impact-treemap-btn", "active"),
        ],
        [
            Input("workflow-product-count-dropdown", "value"),
            Input("workflow-filtered-query-store", "data"),
            Input("workflow-product-impact-chart-type", "data"),
        ],
        prevent_initial_call=False
    )
    @monitor_performance("Product Impact Chart Update")
    def update_product_impact_chart(top_count, stored_selections, chart_type):
        base_data = get_product_impact_base_data()
        filtered_data = apply_product_impact_filters(base_data['work_items'], stored_selections)
        impact_counts, summary_stats = prepare_product_impact_data(filtered_data, top_count)
        if chart_type == "bar":
            fig = create_product_impact_bar_chart(impact_counts, summary_stats)
        elif chart_type == "stacked":
            fig = create_product_impact_stacked_chart(filtered_data, top_count)
        elif chart_type == "bubble":
            fig = create_product_impact_bubble_chart(filtered_data, top_count)
        elif chart_type == "treemap":
            fig = create_product_impact_treemap_chart(filtered_data, top_count)
        else:
            fig = create_product_impact_bar_chart(impact_counts, summary_stats)
        insights = generate_product_impact_insights(impact_counts, summary_stats, filtered_data)
        return (
            fig, insights,
            chart_type == "bar",
            chart_type == "stacked",
            chart_type == "bubble",
            chart_type == "treemap"
        )    

    # Enlarged chart modal callback
    @monitor_chart_performance("Enlarged Product Impact Chart")
    def create_enlarged_product_impact_chart(original_figure):
        """
        Create an enlarged version of the product impact chart for modal display
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
                'xaxis': {
                    **enlarged_fig['layout'].get('xaxis', {}),
                    'tickfont': {'size': 13},
                    'title': {
                        **enlarged_fig['layout'].get('xaxis', {}).get('title', {}),
                        'font': {'size': 15}
                    }
                },
                'yaxis': {
                    **enlarged_fig['layout'].get('yaxis', {}),
                    'tickfont': {'size': 13},
                    'title': {
                        **enlarged_fig['layout'].get('yaxis', {}).get('title', {}),
                        'font': {'size': 15}
                    }
                },
                'legend': {
                    **enlarged_fig['layout'].get('legend', {}),
                    'font': {'size': 13}
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
                        'filename': 'workflow_product_impact_chart',
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
        [Input("workflow-product-impact-chart", "clickData"),
         Input("workflow-chart-modal", "is_open")],
        [State("workflow-product-impact-chart", "figure"),
         State("workflow-chart-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_product_impact_chart_modal(chart_click, modal_is_open, chart_figure, is_open_state):
        """
        Open enlarged chart modal when chart is clicked
        """
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if triggered_id == "workflow-product-impact-chart" and chart_click and not is_open_state:
            enlarged_chart = create_enlarged_product_impact_chart(chart_figure)
            return True, enlarged_chart
        return no_update, no_update
    
    @callback(
        Output("workflow-product-impact-chart-type", "data"),
        [
            Input("product-impact-bar-btn", "n_clicks"),
            Input("product-impact-stacked-btn", "n_clicks"),
            Input("product-impact-bubble-btn", "n_clicks"),
            Input("product-impact-treemap-btn", "n_clicks"),
        ],
        State("workflow-product-impact-chart-type", "data"),
        prevent_initial_call=True
    )
    def set_chart_type(bar, stacked, bubble, treemap, current_type):
        triggered = ctx.triggered_id
        if triggered == "product-impact-bar-btn":
            return "bar"
        elif triggered == "product-impact-stacked-btn":
            return "stacked"
        elif triggered == "product-impact-bubble-btn":
            return "bubble"
        elif triggered == "product-impact-treemap-btn":
            return "treemap"
        return current_type    