from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters, prepare_outstanding_issues_data
from src.utils.performance import monitor_performance, monitor_chart_performance
import time
import copy

def register_compliance_outstanding_issues_callbacks(app):
    """Register outstanding issues callbacks"""
    
    @monitor_chart_performance("Outstanding Issues Chart")
    def create_outstanding_issues_chart(status_counts, summary_stats, view_state):
        """Create outstanding issues chart based on view state"""
        
        if status_counts.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="🎉 No outstanding issues found!",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="green")
            )
            fig.update_layout(
                title={'text': "Outstanding Issues - All Clear!", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        # Color schemes based on view
        if view_state == "severity":
            color_map = {
                'CRITICAL': '#e74c3c',      # Red - immediate attention
                'HIGH': '#f39c12',          # Orange - urgent
                'MEDIUM': '#3498db',        # Blue - standard priority
                'LOW': '#27ae60',           # Green - routine
                'DATA_ISSUE': '#95a5a6'     # Gray - data problems
            }
            colors = [color_map.get(cat, '#7f8c8d') for cat in status_counts['Category']]
            
        elif view_state == "age":
            color_map = {
                "≤7 days (Fresh)": '#27ae60',        # Green - good
                "8-30 days (Recent)": '#f39c12',     # Orange - attention needed
                "31-90 days (Aging)": '#e67e22',     # Dark orange - concern
                ">90 days (Stale)": '#c0392b'        # Dark red - critical
            }
            colors = [color_map.get(cat, '#7f8c8d') for cat in status_counts['Category']]
            
        elif view_state == "assignment":
            # Special handling for assignment view
            colors = []
            for cat in status_counts['Category']:
                if '🚨 Unassigned' in cat:
                    colors.append('#e74c3c')  # Red for unassigned
                else:
                    colors.append('#3498db')  # Blue for assigned
                    
        else:  # violation view
            colors = px.colors.qualitative.Set3[:len(status_counts)]
        
        # Create horizontal bar chart for better readability with longer labels
        fig = go.Figure(data=[go.Bar(
            y=status_counts['Category'][::-1],  # Reverse for top-to-bottom importance
            x=status_counts['Count'][::-1],
            orientation='h',
            marker=dict(color=colors[::-1], line=dict(color='white', width=1)),
            hovertemplate="<b>%{y}</b><br>Cases: %{x}<br><extra></extra>",
            text=status_counts['Count'][::-1],
            textposition='inside',
            textfont=dict(color='white', size=12)
        )])
        
        # Chart titles
        view_titles = {
            'severity': 'Outstanding Issues by Severity Level',
            'age': 'Outstanding Issues by Age',
            'assignment': 'Outstanding Issues by Assignment Status',
            'violation': 'Outstanding Issues by Violation Type'
        }
        
        total_outstanding = summary_stats.get('outstanding_cases', 0)
        fig.update_layout(
            title={
                'text': f"{view_titles.get(view_state, 'Outstanding Issues')} ({total_outstanding:,} Total)", 
                'x': 0.5, 
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            xaxis_title="Number of Cases",
            yaxis_title="",
            height=400,
            margin={'l': 120, 'r': 50, 't': 80, 'b': 50},
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(gridcolor='lightgray', gridwidth=0.5),
            yaxis=dict(tickfont=dict(size=11))
        )
        
        return fig
    
    @monitor_chart_performance("Enlarged Outstanding Issues Chart")
    def create_enlarged_outstanding_issues_chart(original_figure):
        """Create an enlarged version of the outstanding issues chart for modal display"""
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            enlarged_fig = copy.deepcopy(original_figure)
            enlarged_fig['layout'].update({
                'height': 600,
                'margin': {'l': 150, 'r': 80, 't': 100, 'b': 100},
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}
                },
                'xaxis': {
                    **enlarged_fig['layout'].get('xaxis', {}),
                    'title': {'font': {'size': 14}},
                    'tickfont': {'size': 12}
                },
                'yaxis': {
                    **enlarged_fig['layout'].get('yaxis', {}),
                    'tickfont': {'size': 12}
                }
            })
            
            # Update bar chart for better visibility
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') == 'bar':
                        trace.update({
                            'textfont': {'size': 14, 'color': 'white'}
                        })
            
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'compliance_outstanding_issues_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
        except Exception as e:
            return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")
    
    def create_outstanding_issues_details_table(status_counts, view_state, summary_stats):
        """Create detailed breakdown table for modal display"""
        if status_counts.empty:
            return html.Div([
                html.H4("🎉 No Outstanding Issues!", className="text-success mb-3"),
                html.P("All compliance cases appear to be resolved or closed.", className="text-muted")
            ], className="text-center p-4")
        
        try:
            # Enhanced data for table
            table_data = status_counts.copy()
            
            # Add percentage calculation
            total_outstanding = table_data['Count'].sum()
            table_data['Percentage'] = (table_data['Count'] / total_outstanding * 100).round(1)
            
            # Add priority indicators based on view
            priority_indicators = []
            for _, row in table_data.iterrows():
                category = row['Category']
                if view_state == "severity":
                    if category == "CRITICAL":
                        priority_indicators.append("🚨 Immediate")
                    elif category == "HIGH":
                        priority_indicators.append("⚠️ Urgent")
                    elif category == "MEDIUM":
                        priority_indicators.append("📋 Standard")
                    elif category == "LOW":
                        priority_indicators.append("📝 Routine")
                    else:
                        priority_indicators.append("❓ Review")
                elif view_state == "age":
                    if ">90 days" in category:
                        priority_indicators.append("🚨 Stale")
                    elif "31-90 days" in category:
                        priority_indicators.append("⚠️ Aging")
                    elif "8-30 days" in category:
                        priority_indicators.append("📋 Recent")
                    else:
                        priority_indicators.append("✅ Fresh")
                elif view_state == "assignment":
                    if "🚨 Unassigned" in category:
                        priority_indicators.append("🚨 Needs Assignment")
                    else:
                        priority_indicators.append("👤 Assigned")
                else:  # violation
                    priority_indicators.append("📋 Review")
            
            table_data['Priority'] = priority_indicators
            
            # Create table rows with enhanced styling
            table_rows = []
            for i, row in table_data.iterrows():
                # Determine row styling based on priority
                if "🚨" in row['Priority']:
                    row_class = "table-danger"
                elif "⚠️" in row['Priority']:
                    row_class = "table-warning"
                elif i < 3:
                    row_class = "table-info"
                else:
                    row_class = ""
                
                # Create row cells
                cells = [
                    html.Td([
                        html.Span(row['Priority'], style={'marginRight': '8px'}),
                        html.Span(row['Category'], style={'fontWeight': 'bold' if i < 5 else 'normal'})
                    ]),
                    html.Td(f"{row['Count']:,}", className="text-end fw-bold"),
                    html.Td(f"{row['Percentage']:.1f}%", className="text-end")
                ]
                
                table_rows.append(html.Tr(cells, className=row_class))
            
            # Create headers
            headers = [
                html.Th("Category", style={'width': '50%'}),
                html.Th("Outstanding Cases", className="text-end", style={'width': '25%'}),
                html.Th("Percentage", className="text-end", style={'width': '25%'})
            ]
            
            # View-specific titles
            view_names = {
                'severity': 'Severity Level',
                'age': 'Case Age',
                'assignment': 'Assignment Status',
                'violation': 'Violation Type'
            }
            
            # Create summary cards
            critical_cases = summary_stats.get('critical_cases', 0)
            high_cases = summary_stats.get('high_cases', 0)
            unassigned_cases = summary_stats.get('unassigned_cases', 0)
            stale_cases = summary_stats.get('stale_cases', 0)
            
            summary_cards = dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("🚨 Critical", className="text-danger mb-1"),
                            html.H4(f"{critical_cases:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-danger")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("⚠️ High Priority", className="text-warning mb-1"),
                            html.H4(f"{high_cases:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-warning")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("👤 Unassigned", className="text-info mb-1"),
                            html.H4(f"{unassigned_cases:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-info")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("⏰ Stale (>90d)", className="text-secondary mb-1"),
                            html.H4(f"{stale_cases:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-secondary")
                ], width=3)
            ], className="mb-4")
            
            return html.Div([
                html.H4(f"Outstanding Issues by {view_names.get(view_state, 'Category')}", className="mb-3 text-primary"),
                
                # Summary cards
                summary_cards,
                
                html.P([
                    html.Span([
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        f"Total Outstanding: {total_outstanding:,} cases"
                    ], className="me-4"),
                    html.Span([
                        html.I(className="fas fa-clock me-2"),
                        f"Average Age: {summary_stats.get('avg_days_open', 0):.0f} days"
                    ])
                ], className="text-muted mb-4"),
                
                html.Table([
                    html.Thead([
                        html.Tr(headers, style={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'})
                    ]),
                    html.Tbody(table_rows)
                ], className="table table-hover table-striped"),
                
            ], className="p-3")
            
        except Exception as e:
            print(f"❌ Error creating outstanding issues details table: {e}")
            return html.Div([
                html.H4("Error Creating Breakdown", className="text-danger mb-3"),
                html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
            ], className="text-center p-4")
    
    @monitor_performance("Outstanding Issues Insights Generation")
    def generate_outstanding_issues_insights(status_counts, summary_stats, view_state):
        """Generate insights for outstanding issues"""
        
        if status_counts.empty:
            return html.Div([
                html.Div([
                    html.Span("✅ ", style={'fontSize': '16px'}),
                    html.Span("**All Clear**: No outstanding compliance issues found", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        insights = []
        
        # Overall summary
        total_cases = summary_stats.get('total_cases', 0)
        outstanding_cases = summary_stats.get('outstanding_cases', 0)
        outstanding_pct = summary_stats.get('outstanding_percentage', 0)
        
        insights.append(
            html.Div([
                html.Span("📊 ", style={'fontSize': '16px'}),
                html.Span(f"**Outstanding Issues**: {outstanding_cases:,} of {total_cases:,} total cases ({outstanding_pct:.1f}%)", style={'fontSize': '13px'})
            ], className="mb-2")
        )
        
        # Critical issues alert
        critical_cases = summary_stats.get('critical_cases', 0)
        if critical_cases > 0:
            insights.append(
                html.Div([
                    html.Span("🚨 ", style={'fontSize': '16px'}),
                    html.Span(f"**Critical Issues**: {critical_cases:,} cases require immediate attention", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Unassigned cases alert
        unassigned_cases = summary_stats.get('unassigned_cases', 0)
        if unassigned_cases > 0:
            unassigned_pct = (unassigned_cases / outstanding_cases * 100) if outstanding_cases > 0 else 0
            insights.append(
                html.Div([
                    html.Span("👤 ", style={'fontSize': '16px'}),
                    html.Span(f"**Unassigned Cases**: {unassigned_cases:,} cases ({unassigned_pct:.1f}%) need assignment", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Aging cases concern
        stale_cases = summary_stats.get('stale_cases', 0)
        if stale_cases > 0:
            stale_pct = (stale_cases / outstanding_cases * 100) if outstanding_cases > 0 else 0
            insights.append(
                html.Div([
                    html.Span("⏰ ", style={'fontSize': '16px'}),
                    html.Span(f"**Stale Cases**: {stale_cases:,} cases ({stale_pct:.1f}%) are over 90 days old", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # View-specific insights
        if not status_counts.empty:
            top_category = status_counts.iloc[0]
            top_pct = (top_category['Count'] / outstanding_cases * 100) if outstanding_cases > 0 else 0
            
            if view_state == "severity":
                insights.append(
                    html.Div([
                        html.Span("🎯 ", style={'fontSize': '16px'}),
                        html.Span(f"**Top Severity**: {top_category['Category']} level has {top_category['Count']:,} cases ({top_pct:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            elif view_state == "assignment":
                if "Unassigned" in top_category['Category']:
                    insights.append(
                        html.Div([
                            html.Span("⚠️ ", style={'fontSize': '16px'}),
                            html.Span(f"**Assignment Priority**: {top_category['Count']:,} unassigned cases need immediate assignment", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
        
        return html.Div(insights, className="insights-container")
    
    # View state toggle callbacks
    @callback(
        [Output("compliance-outstanding-issues-view-state", "data"),
         Output("outstanding-severity-view-btn", "active"),
         Output("outstanding-age-view-btn", "active"),
         Output("outstanding-assignment-view-btn", "active"),
         Output("outstanding-violation-view-btn", "active")],
        [Input("outstanding-severity-view-btn", "n_clicks"),
         Input("outstanding-age-view-btn", "n_clicks"),
         Input("outstanding-assignment-view-btn", "n_clicks"),
         Input("outstanding-violation-view-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def toggle_outstanding_issues_view(severity_clicks, age_clicks, assignment_clicks, violation_clicks):
        """Toggle between different outstanding issues analysis views"""
        triggered = ctx.triggered
        if not triggered:
            return "severity", True, False, False, False
            
        triggered_id = triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "outstanding-severity-view-btn":
            return "severity", True, False, False, False
        elif triggered_id == "outstanding-age-view-btn":
            return "age", False, True, False, False
        elif triggered_id == "outstanding-assignment-view-btn":
            return "assignment", False, False, True, False
        elif triggered_id == "outstanding-violation-view-btn":
            return "violation", False, False, False, True
        
        return "severity", True, False, False, False
    
    # Details modal callback
    @callback(
        [Output("compliance-outstanding-details-modal", "is_open"),
         Output("compliance-outstanding-details-content", "children")],
        [Input("compliance-outstanding-details-btn", "n_clicks")],
        [State("compliance-outstanding-details-modal", "is_open"),
         State("compliance-filtered-query-store", "data"),
         State("compliance-outstanding-issues-view-state", "data")],
        prevent_initial_call=True
    )
    @monitor_performance("Outstanding Issues Details Modal Toggle")
    def toggle_outstanding_issues_details_modal(details_btn_clicks, is_open, filter_selections, view_state):
        """Handle opening of outstanding issues details modal"""
        if details_btn_clicks:
            if not is_open:
                try:
                    # Get fresh data
                    base_data = get_compliance_base_data()
                    filtered_data = apply_compliance_filters(base_data, filter_selections or {})
                    status_counts, summary_stats = prepare_outstanding_issues_data(filtered_data, view_state)
                    
                    # Create detailed table
                    detailed_table = create_outstanding_issues_details_table(status_counts, view_state, summary_stats)
                    
                    return True, detailed_table
                    
                except Exception as e:
                    print(f"❌ Error generating outstanding issues details: {e}")
                    error_content = html.Div([
                        html.H4("Error Loading Details", className="text-danger mb-3"),
                        html.P(f"Unable to load detailed breakdown: {str(e)}", className="text-muted")
                    ], className="text-center p-4")
                    return True, error_content
            else:
                return False, no_update
        
        return no_update, no_update
    
    # Main chart and insights callback
    @callback(
        [Output("compliance-outstanding-issues-chart", "figure"),
         Output("compliance-outstanding-issues-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-outstanding-issues-view-state", "data")],
        prevent_initial_call=False
    )
    @monitor_performance("Outstanding Issues Chart Update")
    def update_outstanding_issues_chart(filter_selections, view_state):
        """Update outstanding issues chart and insights based on filters and view state"""
        
        try:
            # Get filter selections or use defaults
            if not filter_selections:
                filter_selections = {}
            
            # Get base data using shared utility
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
                    title={'text': "Outstanding Issues - No Data", 'x': 0.5, 'xanchor': 'center'},
                    height=400
                )
                return fig, html.Div("No data available for analysis.", className="text-muted")
            
            # Apply filters using shared utility
            filtered_data = apply_compliance_filters(base_data, filter_selections)
            
            # Prepare outstanding issues data based on view state
            status_counts, summary_stats = prepare_outstanding_issues_data(filtered_data, view_state)
            
            # Create chart
            fig = create_outstanding_issues_chart(status_counts, summary_stats, view_state)
            
            # Generate insights
            insights = generate_outstanding_issues_insights(status_counts, summary_stats, view_state)
            
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating outstanding issues chart: {e}")
            import traceback
            traceback.print_exc()
            
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading outstanding issues data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Outstanding Issues - Error", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to load outstanding issues data", style={'fontSize': '13px'})], className="mb-2"),
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
            Input("compliance-outstanding-issues-chart-wrapper", "n_clicks"),
            Input("compliance-chart-modal", "is_open")
        ],
        [
            State("compliance-outstanding-issues-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_outstanding_issues_chart_modal(wrapper_clicks, modal_is_open, chart_figure, is_open_state):
        """Toggle enlarged outstanding issues chart modal"""
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        if triggered_id == "compliance-outstanding-issues-chart-wrapper" and wrapper_clicks and not is_open_state:
            enlarged_chart = create_enlarged_outstanding_issues_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
        
    @callback(
        Output("compliance-outstanding-details-modal", "is_open", allow_duplicate=True),
        [Input("compliance-outstanding-details-close-btn", "n_clicks")],
        [State("compliance-outstanding-details-modal", "is_open")],
        prevent_initial_call=True
    )
    def close_outstanding_details_modal(close_clicks, is_open):
        """Close the outstanding details modal when close button is clicked"""
        if close_clicks and is_open:
            return False
        return no_update

    print("✅ Compliance outstanding issues callbacks registered")