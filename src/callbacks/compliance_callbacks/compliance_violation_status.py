from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters
from src.utils.performance import monitor_performance, monitor_chart_performance
import time
import copy

def register_compliance_violation_status_callbacks(app):
    """Register violation status overview callbacks"""
    
    @monitor_performance("Violation Status Data Preparation")
    def prepare_violation_status_data(df, view_state):
        """Prepare data based on selected view"""
        if df.empty:
            return pd.DataFrame(), {}
        
        if view_state == "status":
            # Group by Status
            status_counts = df['Status'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "disposition":
            # Group by Disposition
            status_counts = df['Disposition'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "combined":
            # Group by Status and Disposition combination
            combined_counts = df.groupby(['Status', 'Disposition']).size().reset_index(name='Count')
            combined_counts['Category'] = combined_counts['Status'] + ' - ' + combined_counts['Disposition']
            status_counts = combined_counts[['Category', 'Count']].sort_values('Count', ascending=False)
        
        # Calculate summary stats
        summary_stats = {
            'total_cases': len(df),
            'open_cases': len(df[df['Status'] != 'Closed']) if 'Status' in df.columns else 0,
            'closed_cases': len(df[df['Status'] == 'Closed']) if 'Status' in df.columns else 0,
            'unique_categories': len(status_counts)
        }
        
        return status_counts, summary_stats
    
    @monitor_chart_performance("Violation Status Chart")
    def create_violation_status_chart(status_counts, summary_stats, view_state):
        """Create violation status chart based on view state"""
        
        if status_counts.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No violation status data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': f"Violation {view_state.title()} Overview - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        # Color scheme based on view
        if view_state == "status":
            color_map = {
                'Open': '#e74c3c',      # Red for open
                'Closed': '#27ae60',    # Green for closed
                'In Progress': '#f39c12', # Orange for in progress
                'On Hold': '#95a5a6',   # Gray for on hold
            }
            colors = [color_map.get(cat, '#3498db') for cat in status_counts['Category']]
        else:
            # Use a color sequence for disposition and combined views
            colors = px.colors.qualitative.Set3[:len(status_counts)]
        
        # Create pie chart
        fig = go.Figure(data=[go.Pie(
            labels=status_counts['Category'],
            values=status_counts['Count'],
            hole=0.3,
            textinfo='label+percent+value',
            textposition='outside',
            marker=dict(colors=colors, line=dict(color='white', width=2)),
            hovertemplate="<b>%{label}</b><br>Cases: %{value}<br>Percent: %{percent}<extra></extra>"
        )])
        
        fig.update_layout(
            title={
                'text': f"Violation {view_state.title()} Overview ({summary_stats['total_cases']:,} Total Cases)", 
                'x': 0.5, 
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            height=400,
            margin={'l': 50, 'r': 50, 't': 80, 'b': 50},
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        
        return fig
    
    @monitor_performance("Violation Status Insights Generation")
    def generate_violation_status_insights(status_counts, summary_stats, view_state):
        """Generate insights for violation status overview"""
        
        if status_counts.empty:
            return html.Div("No data available for insights generation.", className="text-muted")
        
        insights = []
        
        # Overall summary
        insights.append(
            html.Div([
                html.Span("📊 ", style={'fontSize': '16px'}),
                html.Span(f"**Total Cases**: {summary_stats['total_cases']:,} cases analyzed", style={'fontSize': '13px'})
            ], className="mb-2")
        )
        
        if view_state == "status":
            # Status-specific insights
            if summary_stats['open_cases'] > 0:
                open_pct = (summary_stats['open_cases'] / summary_stats['total_cases']) * 100
                insights.append(
                    html.Div([
                        html.Span("🔴 ", style={'fontSize': '16px'}),
                        html.Span(f"**Open Cases**: {summary_stats['open_cases']:,} ({open_pct:.1f}%) require attention", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            
            if summary_stats['closed_cases'] > 0:
                closed_pct = (summary_stats['closed_cases'] / summary_stats['total_cases']) * 100
                insights.append(
                    html.Div([
                        html.Span("✅ ", style={'fontSize': '16px'}),
                        html.Span(f"**Closed Cases**: {summary_stats['closed_cases']:,} ({closed_pct:.1f}%) have been resolved", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
        
        # Top categories
        top_category = status_counts.iloc[0] if len(status_counts) > 0 else None
        if top_category is not None:
            top_pct = (top_category['Count'] / summary_stats['total_cases']) * 100
            insights.append(
                html.Div([
                    html.Span("🎯 ", style={'fontSize': '16px'}),
                    html.Span(f"**Most Common**: {top_category['Category']} accounts for {top_category['Count']:,} cases ({top_pct:.1f}%)", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Distribution insights
        if len(status_counts) > 1:
            insights.append(
                html.Div([
                    html.Span("📈 ", style={'fontSize': '16px'}),
                    html.Span(f"**Distribution**: Cases are spread across {len(status_counts)} different {view_state} categories", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        return html.Div(insights, className="insights-container")
    
    # View state toggle callbacks
    @callback(
        [Output("compliance-violation-status-view-state", "data"),
         Output("violation-status-view-btn", "active"),
         Output("violation-disposition-view-btn", "active"),
         Output("violation-combined-view-btn", "active")],
        [Input("violation-status-view-btn", "n_clicks"),
         Input("violation-disposition-view-btn", "n_clicks"),
         Input("violation-combined-view-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def toggle_violation_status_view(status_clicks, disposition_clicks, combined_clicks):
        """Toggle between different violation status views"""
        triggered = ctx.triggered
        if not triggered:
            return "status", True, False, False
            
        triggered_id = triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "violation-status-view-btn":
            return "status", True, False, False
        elif triggered_id == "violation-disposition-view-btn":
            return "disposition", False, True, False
        elif triggered_id == "violation-combined-view-btn":
            return "combined", False, False, True
        
        return "status", True, False, False
    
    # Main chart and insights callback
    @callback(
        [Output("compliance-violation-status-chart", "figure"),
         Output("compliance-violation-status-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-violation-status-view-state", "data")],
        prevent_initial_call=False
    )
    @monitor_performance("Violation Status Chart Update")
    def update_violation_status_chart(filter_selections, view_state):
        """Update violation status chart and insights based on filters and view state"""
        
        try:
            # Get filter selections or use defaults
            if not filter_selections:
                filter_selections = {}
            
            # Get base data using shared utility
            base_data = get_compliance_base_data()
            
            if base_data.empty:
                fig = go.Figure()
                fig.add_annotation(
                    text="No violation status data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
                fig.update_layout(
                    title={'text': "Violation Status Overview - No Data", 'x': 0.5, 'xanchor': 'center'},
                    height=400
                )
                return fig, html.Div("No data available for analysis.", className="text-muted")
            
            # Apply filters using shared utility
            filtered_data = apply_compliance_filters(base_data, filter_selections)
            
            # Prepare data based on view state
            status_counts, summary_stats = prepare_violation_status_data(filtered_data, view_state)
            
            # Create chart
            fig = create_violation_status_chart(status_counts, summary_stats, view_state)
            
            # Generate insights
            insights = generate_violation_status_insights(status_counts, summary_stats, view_state)
            
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating violation status chart: {e}")
            import traceback
            traceback.print_exc()
            
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading violation status data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Violation Status Overview - Error", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to load violation status data", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
    
    print("✅ Compliance violation status callbacks registered")