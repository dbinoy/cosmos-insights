from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import copy
from src.utils.db import run_queries
from inflection import titleize
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

def register_workflow_user_performance_callbacks(app):

    @monitor_query_performance("User Performance Base Data")
    def get_user_performance_base_data():
        queries = {
            "work_items": """
                SELECT 
                    WorkItemId,
                    AssignedTo,
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
            "duration_summary": """
                SELECT WorkItemId, OpenToClosed_Min
                FROM [consumable].[Fact_DurationSummary]
            """,
            "workflow_history": """
                SELECT WorkItemId, ChangedBy, ChangedField
                FROM [consumable].[Fact_WorkFlowHistory]
            """
        }
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("User Performance Filter Application")
    def apply_user_performance_filters(work_items, stored_selections):
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

    @monitor_performance("User Performance Data Preparation")
    def prepare_user_performance_data(base_data, filtered_work_items, chart_type):
        work_items = filtered_work_items.copy()
        duration_summary = pd.DataFrame(base_data['duration_summary'])
        workflow_history = pd.DataFrame(base_data['workflow_history'])

        if chart_type == "tickets_handled":
            ticket_counts = work_items.groupby('AssignedTo').size().reset_index(name='TicketsHandled')
            ticket_counts = ticket_counts.sort_values('TicketsHandled', ascending=False)
            return ticket_counts

        elif chart_type == "avg_resolution":
            df = work_items.merge(duration_summary, on='WorkItemId', how='left')
            avg_resolution = df.groupby('AssignedTo')['OpenToClosed_Min'].mean().reset_index()
            avg_resolution['AvgResolutionHours'] = (avg_resolution['OpenToClosed_Min'] / 60).round(2)
            avg_resolution = avg_resolution.sort_values('AvgResolutionHours')
            return avg_resolution

        elif chart_type == "notes_tasks":
            df = workflow_history.copy()
            notes_tasks = df[df['ChangedBy'].isin(work_items['AssignedTo']) & df['ChangedField'].isin(['Note', 'Task'])].groupby('ChangedBy').size().reset_index(name='NotesTasksCompleted')
            notes_tasks = notes_tasks.sort_values('NotesTasksCompleted', ascending=False)
            return notes_tasks

        elif chart_type == "top_performers":
            tickets = work_items.groupby('AssignedTo').size().reset_index(name='TicketsHandled')
            avg_res = work_items.merge(duration_summary, on='WorkItemId', how='left').groupby('AssignedTo')['OpenToClosed_Min'].mean().reset_index()
            avg_res['AvgResolutionHours'] = (avg_res['OpenToClosed_Min'] / 60).round(2)
            merged = tickets.merge(avg_res[['AssignedTo', 'AvgResolutionHours']], on='AssignedTo', how='left')
            merged = merged.sort_values(['TicketsHandled', 'AvgResolutionHours'], ascending=[False, True])
            return merged

        return pd.DataFrame()

    @monitor_chart_performance("User Performance Chart")
    def create_user_performance_chart(data, chart_type):
        if data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No user activity data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(title="User Activity & Performance", height=400)
            return fig

        if chart_type == "tickets_handled":
            fig = go.Figure(go.Bar(
                x=[titleize(u) for u in data['AssignedTo']],
                y=data['TicketsHandled'],
                text=data['TicketsHandled'],
                textposition='auto',
                marker=dict(color='#2ecc71'),
                hovertemplate="<b>%{x}</b><br>Tickets: %{y}<extra></extra>"
            ))
            fig.update_layout(title="Tickets Handled by User", xaxis_title="User", yaxis_title="Tickets", height=400)
            return fig

        elif chart_type == "avg_resolution":
            fig = go.Figure(go.Bar(
                x=[titleize(u) for u in data['AssignedTo']],
                y=data['AvgResolutionHours'],
                text=data['AvgResolutionHours'],
                textposition='auto',
                marker=dict(color='#3498db'),
                hovertemplate="<b>%{x}</b><br>Avg Resolution (hrs): %{y}<extra></extra>"
            ))
            fig.update_layout(title="Average Resolution Time by User", xaxis_title="User", yaxis_title="Avg Resolution (hrs)", height=400)
            return fig

        elif chart_type == "notes_tasks":
            fig = go.Figure(go.Bar(
                x=[titleize(u) for u in data['ChangedBy']],
                y=data['NotesTasksCompleted'],
                text=data['NotesTasksCompleted'],
                textposition='auto',
                marker=dict(color='#f39c12'),
                hovertemplate="<b>%{x}</b><br>Notes/Tasks: %{y}<extra></extra>"
            ))
            fig.update_layout(title="Notes/Tasks Completed by User", xaxis_title="User", yaxis_title="Notes/Tasks", height=400)
            return fig

        elif chart_type == "top_performers":
            fig = go.Figure(go.Scatter(
                x=[titleize(u) for u in data['AssignedTo']],
                y=data['TicketsHandled'],
                mode='markers',
                marker=dict(
                    size=data['TicketsHandled'],
                    color=data['AvgResolutionHours'],
                    colorscale='Viridis',
                    showscale=True
                ),
                text=[f"Avg Resolution: {v} hrs" for v in data['AvgResolutionHours']],
                hovertemplate="<b>%{x}</b><br>Tickets: %{y}<br>Avg Resolution: %{marker.color} hrs<extra></extra>"
            ))
            fig.update_layout(title="Top Performers (Tickets vs Resolution)", xaxis_title="User", yaxis_title="Tickets Handled", height=400)
            return fig

        return go.Figure()

    @monitor_performance("User Performance Insights Generation")
    def generate_user_performance_insights(data, chart_type):
        if data.empty:
            return html.Div([
                html.Div("📊 No user activity data available for current filter selection", className="mb-2", style={'fontSize': '13px'}),
                html.Div("🔍 Try adjusting your filters to see user performance insights", className="mb-2", style={'fontSize': '13px'})
            ], className="insights-container")
        insights = []
        if chart_type == "tickets_handled":
            top_user = data.iloc[0]
            insights.append(f"🏆 {titleize(top_user['AssignedTo'])} has handled the most tickets ({top_user['TicketsHandled']:,}).")
        elif chart_type == "avg_resolution":
            fastest_user = data.iloc[0]
            insights.append(f"⏱️ {titleize(fastest_user['AssignedTo'])} resolves tickets fastest (avg {fastest_user['AvgResolutionHours']} hrs).")
        elif chart_type == "notes_tasks":
            top_notes = data.iloc[0]
            insights.append(f"📝 {titleize(top_notes['ChangedBy'])} has completed the most notes/tasks ({top_notes['NotesTasksCompleted']:,}).")
        elif chart_type == "top_performers":
            top_perf = data.iloc[0]
            insights.append(f"🌟 Top performer: {titleize(top_perf['AssignedTo'])} ({top_perf['TicketsHandled']} tickets, avg {top_perf['AvgResolutionHours']} hrs resolution).")
            low_perf = data.iloc[-1]
            insights.append(f"⚠️ {titleize(low_perf['AssignedTo'])} may need support/training ({low_perf['TicketsHandled']} tickets, avg {low_perf['AvgResolutionHours']} hrs resolution).")
        return html.Div([html.Div(i, className="mb-2", style={'fontSize': '13px'}) for i in insights], className="insights-container")

    @callback(
        [
            Output("workflow-user-performance-chart", "figure"),
            Output("workflow-performance-insights", "children"),
        ],
        [
            Input("workflow-user-performance-view-dropdown", "value"),
            Input("workflow-filtered-query-store", "data"),
        ],
        prevent_initial_call=False
    )
    def update_user_performance_chart(chart_type, stored_selections):
        base_data = get_user_performance_base_data()

        filtered_work_items = apply_user_performance_filters(base_data['work_items'], stored_selections)
        data = prepare_user_performance_data(base_data, filtered_work_items, chart_type)
        fig = create_user_performance_chart(data, chart_type)
        insights = generate_user_performance_insights(data, chart_type)
        return fig, insights

    @monitor_chart_performance("Enlarged User Performance Chart")
    def create_enlarged_user_performance_chart(original_figure):
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
                        'filename': 'workflow_user_performance_chart',
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
        [Input("workflow-user-performance-chart", "clickData"),
         Input("workflow-chart-modal", "is_open")],
        [State("workflow-user-performance-chart", "figure"),
         State("workflow-chart-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_user_performance_chart_modal(chart_click, modal_is_open, chart_figure, is_open_state):
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        if triggered_id == "workflow-user-performance-chart" and chart_click and not is_open_state:
            enlarged_chart = create_enlarged_user_performance_chart(chart_figure)
            return True, enlarged_chart
        return (no_update, no_update)