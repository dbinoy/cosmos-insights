from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import copy
from inflection import titleize
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_workflow_trends_case_reasons_issues_callbacks(app):

    @monitor_query_performance("Trends Case Reasons & Issues Base Data")
    def get_trends_case_reasons_issues_base_data():
        queries = {
            "work_items": """
                SELECT 
                    WorkItemId,
                    CreatedOn,
                    ClosedOn,
                    WorkItemStatus,
                    WorkItemDefinitionShortCode,
                    AorShortName,
                    CaseOrigin,
                    CaseReason,
                    Feature,
                    Issue,
                    Module,
                    Priority,
                    Product
                FROM [consumable].[Fact_WorkFlowItems]
            """,
            "date_dim": """
                SELECT 
                    DateKey,
                    WeekNumber,
                    MonthNumber,
                    MonthName,
                    QuarterNumber,
                    YearNumber
                FROM [consumable].[Dim_Date]
            """
        }
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("Trends Case Reasons & Issues Filter Application")
    def apply_trends_case_reasons_issues_filters(work_items, stored_selections):
        if not stored_selections:
            stored_selections = {}

        df = pd.DataFrame(work_items).copy()
        if df.empty:
            return df

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

    @monitor_performance("Trends Case Reasons & Issues Data Preparation")
    def prepare_trends_case_reasons_issues_data(base_data, filtered_work_items, view_type, time_granularity):
        work_items = filtered_work_items.copy()
        date_dim = pd.DataFrame(base_data['date_dim'])
        if work_items.empty or date_dim.empty:
            return pd.DataFrame(), []

        # Merge with date dimension for time grouping
        work_items['DateKey'] = work_items['CreatedOn'].dt.date
        date_dim['DateKey'] = pd.to_datetime(date_dim['DateKey']).dt.date
        df = work_items.merge(date_dim, on='DateKey', how='left')

        # Choose grouping column
        if time_granularity == 'month':
            df['Period'] = df['YearNumber'].astype(str) + '-' + df['MonthNumber'].astype(str).str.zfill(2)
        elif time_granularity == 'quarter':
            df['Period'] = df['YearNumber'].astype(str) + '-Q' + df['QuarterNumber'].astype(str)
        elif time_granularity == 'year':
            df['Period'] = df['YearNumber'].astype(str)
        elif time_granularity == 'week':
            df['Period'] = df['YearNumber'].astype(str) + '-W' + df['WeekNumber'].astype(str).str.zfill(2)
        else:
            df['Period'] = df['YearNumber'].astype(str) + '-' + df['MonthNumber'].astype(str).str.zfill(2)

        # Select CaseReason or Issue
        col = 'CaseReason' if view_type == 'case_reason' else 'Issue'
        df = df[df[col].notnull() & (df[col] != '')].copy()

        # Get all unique items for chart filtering in callback
        all_items = df[col].value_counts().index.tolist()

        # Aggregate for chart: count per period per reason/issue
        chart_df = df.groupby(['Period', col]).size().reset_index(name='Count')
        chart_df = chart_df.sort_values(['Period', 'Count'], ascending=[True, False])

        return chart_df, all_items    

    @monitor_chart_performance("Trends Case Reasons & Issues Chart")
    def create_trends_case_reasons_issues_chart(chart_df, view_type, time_granularity, top_items):
        if chart_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(title="Trends in Case Reasons & Issues", height=400)
            return fig

        # Line chart for each top reason/issue
        fig = go.Figure()
        col = 'CaseReason' if view_type == 'case_reason' else 'Issue'
        for item in top_items:
            item_df = chart_df[chart_df[col] == item]
            fig.add_trace(go.Scatter(
                x=item_df['Period'],
                y=item_df['Count'],
                mode='lines+markers',
                name=titleize(item)
            ))
        fig.update_layout(
            title=f"Trends in {'Case Reasons' if view_type == 'case_reason' else 'Issues'} Over Time",
            xaxis_title="Period",
            yaxis_title="Count",
            height=400
        )
        return fig

    @monitor_performance("Trends Case Reasons & Issues Insights Generation")
    def generate_trends_case_reasons_issues_insights(chart_df, view_type, all_items):
        if chart_df.empty:
            return html.Div([
                html.Div("📊 No data available for current filter selection", className="mb-2", style={'fontSize': '13px'}),
                html.Div("🔍 Try adjusting your filters to see trends", className="mb-2", style={'fontSize': '13px'})
            ], className="insights-container")

        insights = []
        col = 'CaseReason' if view_type == 'case_reason' else 'Issue'

        # 1. Most common reasons/issues for case creation
        overall_counts = chart_df.groupby(col)['Count'].sum().sort_values(ascending=False)
        top_items = overall_counts.index[:3].tolist()
        top_counts = overall_counts.iloc[:3].tolist()
        top_summary = ', '.join([f"'{titleize(item)}' ({count})" for item, count in zip(top_items, top_counts)])
        insights.append(f"🏆 Most common {'Case Reasons' if view_type == 'case_reason' else 'Issues'}: {top_summary}.")

        # 2. Emerging or recurring issues over time (trend in last 2 periods)
        periods = sorted(chart_df['Period'].unique())
        if len(periods) >= 2:
            recent_period = periods[-1]
            prev_period = periods[-2]
            recent_counts = chart_df[chart_df['Period'] == recent_period].groupby(col)['Count'].sum()
            prev_counts = chart_df[chart_df['Period'] == prev_period].groupby(col)['Count'].sum()
            changes = []
            for item in top_items:
                recent = recent_counts.get(item, 0)
                prev = prev_counts.get(item, 0)
                item_title = titleize(item)
                if recent > prev:
                    changes.append(f"'{item_title}' rising ({prev}→{recent})")
                elif recent < prev:
                    changes.append(f"'{item_title}' falling ({prev}→{recent})")
                else:
                    changes.append(f"'{item_title}' stable ({recent})")
            insights.append(f"📈 Recent trend: " + ', '.join(changes))
        else:
            insights.append("📈 Not enough data to show recent trends.")

        # 3. How do case reasons/issues trend across periods (volatility/consistency)
        volatility = []
        for item in top_items:
            item_counts = chart_df[chart_df[col] == item].sort_values('Period')['Count']
            if len(item_counts) > 1:
                std = item_counts.std()
                volatility.append((titleize(item), std))
        if volatility:
            most_volatile = max(volatility, key=lambda x: x[1])
            most_consistent = min(volatility, key=lambda x: x[1])
            insights.append(
                f"🔄 '{most_volatile[0]}' shows most fluctuation (std dev: {most_volatile[1]:.1f}); "
                f"'{most_consistent[0]}' is most consistent (std dev: {most_consistent[1]:.1f})."
            )
        else:
            insights.append("🔄 Not enough data to assess volatility/consistency.")

        return html.Div([html.Div(i, className="mb-2", style={'fontSize': '13px'}) for i in insights], className="insights-container")
    
    @callback(
        [
            Output("workflow-trends-case-reasons-issues-chart", "figure"),
            Output("workflow-trends-case-reasons-issues-insights", "children"),
            Output("workflow-trends-case-count-top-dropdown", "value"),
            Output("workflow-trends-case-count-bottom-dropdown", "value"),
        ],
        [
            Input("workflow-trends-case-view-dropdown", "value"),
            Input("workflow-trends-case-time-dropdown", "value"),
            Input("workflow-trends-case-count-top-dropdown", "value"),
            Input("workflow-trends-case-count-bottom-dropdown", "value"),
            Input("workflow-filtered-query-store", "data"),
        ],
        prevent_initial_call=False
    )
    @monitor_performance("Trends Case Reasons & Issues Chart Update")
    def update_trends_case_reasons_issues_chart(view_type, time_granularity, count_top, count_bottom, stored_selections):
        ctx_trigger = ctx.triggered_id if hasattr(ctx, "triggered_id") else None

        # Sync dropdowns: only one of top/bottom is active at a time
        if ctx_trigger == "workflow-trends-case-count-top-dropdown" and count_top != "all":
            count_bottom = "all"
        elif ctx_trigger == "workflow-trends-case-count-bottom-dropdown" and count_bottom != "all":
            count_top = "all"

        base_data = get_trends_case_reasons_issues_base_data()
        filtered_work_items = apply_trends_case_reasons_issues_filters(base_data['work_items'], stored_selections)
        # chart_df, top_items = prepare_trends_case_reasons_issues_data(base_data, filtered_work_items, view_type, time_granularity)
        chart_df, all_items = prepare_trends_case_reasons_issues_data(base_data, filtered_work_items, view_type, time_granularity)

        # Apply top/bottom filtering for chart only
        if isinstance(chart_df, pd.DataFrame) and not chart_df.empty:
            col = 'CaseReason' if view_type == 'case_reason' else 'Issue'
            unique_items = all_items
            top_n = None if count_top == "all" else int(count_top)
            bottom_n = None if count_bottom == "all" else int(count_bottom)
            if top_n:
                selected_items = unique_items[:top_n]
            elif bottom_n:
                selected_items = unique_items[-bottom_n:]
            else:
                selected_items = unique_items
            chart_df = chart_df[chart_df[col].isin(selected_items)]

        fig = create_trends_case_reasons_issues_chart(chart_df, view_type, time_granularity, selected_items)
        insights = generate_trends_case_reasons_issues_insights(chart_df, view_type, all_items)
        return fig, insights, count_top, count_bottom
    

    @monitor_chart_performance("Enlarged Trends Case Reasons & Issues Chart")
    def create_enlarged_trends_case_reasons_issues_chart(original_figure):
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
                        'filename': 'workflow_trends_case_reasons_issues_chart',
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
        [
            Output("workflow-chart-modal", "is_open", allow_duplicate=True),
            Output("workflow-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("workflow-trends-case-reasons-issues-chart-wrapper", "n_clicks"),
            Input("workflow-chart-modal", "is_open")
        ],
        [
            State("workflow-trends-case-reasons-issues-chart", "figure"),
            State("workflow-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_trends_case_reasons_issues_chart_modal(wrapper_clicks, modal_is_open, chart_figure, is_open_state):
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if triggered_id == "workflow-trends-case-reasons-issues-chart-wrapper" and wrapper_clicks and not is_open_state:
            enlarged_chart = create_enlarged_trends_case_reasons_issues_chart(chart_figure)
            return True, enlarged_chart
        return no_update, no_update