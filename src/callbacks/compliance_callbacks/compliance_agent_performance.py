from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters
from src.utils.performance import monitor_performance, monitor_chart_performance
import copy
from datetime import datetime, timedelta

def register_compliance_agent_performance_callbacks(app):
    """Register agent performance callbacks"""
    
    @monitor_chart_performance("Agent Performance Chart")
    def create_agent_performance_chart(agent_data, summary_stats, metric_type, top_count):
        """Create agent performance chart based on metric type"""
        
        if agent_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No agent performance data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': "Agent Performance - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        # Take top N agents
        top_agents = agent_data.head(top_count)
        
        if metric_type == "count":
            # Active caseload bar chart
            fig = go.Figure(data=[go.Bar(
                x=top_agents['Agent'],
                y=top_agents['ActiveCases'],
                marker=dict(
                    color=top_agents['ActiveCases'],
                    colorscale='Reds',
                    showscale=True,
                    colorbar=dict(title="Cases", len=0.5, y=0.8)
                ),
                text=top_agents['ActiveCases'],
                textposition='outside',
                hovertemplate="<b>%{x}</b><br>" +
                            "Active Cases: %{y}<br>" +
                            "Total Violations: %{customdata[0]}<br>" +
                            "<extra></extra>",
                customdata=top_agents[['TotalViolations']].values
            )])
            
            fig.update_layout(
                title={
                    'text': f"Top {top_count} Agents by Active Caseload",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Compliance Agent",
                yaxis_title="Number of Active Cases",
                height=500,  # Fixed height
                xaxis=dict(tickangle=45)  # Rotate agent names for better readability
            )
            
        elif metric_type == "open":
            # Open cases with trend indicators
            colors = ['#e74c3c' if cases >= 20 else '#f39c12' if cases >= 10 else '#27ae60' 
                     for cases in top_agents['ActiveCases']]
            
            fig = go.Figure(data=[go.Bar(
                x=top_agents['Agent'],
                y=top_agents['ActiveCases'],
                marker=dict(color=colors),
                text=top_agents['ActiveCases'],
                textposition='outside',
                hovertemplate="<b>%{x}</b><br>" +
                            "Active Cases: %{y}<br>" +
                            "Avg Resolution Time: %{customdata[0]:.1f} days<br>" +
                            "Resolution Rate: %{customdata[1]:.1f}%<br>" +
                            "<extra></extra>",
                customdata=top_agents[['AvgResolutionTime', 'ResolutionRate']].values
            )])
            
            fig.update_layout(
                title={
                    'text': f"Top {top_count} Agents by Active Cases<br><sub>Color: Red>20, Yellow>10, Green≤10</sub>",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Compliance Agent",
                yaxis_title="Number of Active Cases",
                height=500,  # Fixed height
                xaxis=dict(tickangle=45)
            )
                       
        elif metric_type == "efficiency":
            # Risk Assessment Matrix - Risk Score vs Active Cases
            fig = go.Figure()
            
            # Add bubbles for each agent
            fig.add_trace(go.Scatter(
                x=top_agents['RiskScore'],           # X: Risk Score (3.51 to 44.48 - excellent spread)
                y=top_agents['ActiveCases'],         # Y: Active Cases (0 to 169 - good spread)
                mode='markers+text',
                marker=dict(
                    size=top_agents['TotalCasesHandled']/100,  # Size = Experience (normalized)
                    color=top_agents['AvgComplexityScore'],    # Color = Case Complexity
                    colorscale='Viridis',  # Purple = low complexity, Yellow = high complexity
                    showscale=True,
                    colorbar=dict(title="Avg Case<br>Complexity", len=0.5, y=0.8),
                    line=dict(width=2, color='white'),
                    sizemode='diameter',
                    sizemin=15
                ),
                text=top_agents['AgentInitials'],
                textposition='middle center',
                textfont=dict(color='white', size=10, family="Arial Black"),
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Risk Score: %{x:.1f}<br>" +
                            "Active Cases: %{y}<br>" +
                            "Experience: %{customdata[1]:,} cases<br>" +
                            "Avg Complexity: %{customdata[2]:.1f}<br>" +
                            "Avg Resolution Time: %{customdata[3]:.1f} days<br>" +
                            "<extra></extra>",
                customdata=top_agents[['Agent', 'TotalCasesHandled', 'AvgComplexityScore', 'AvgResolutionTime']].values
            ))
            
            # Add quadrant reference lines
            avg_risk = top_agents['RiskScore'].median()  # Use median for better split
            avg_workload = top_agents['ActiveCases'].median()
            
            # Vertical line for median risk score
            fig.add_vline(
                x=avg_risk, 
                line_dash="dash", 
                line_color="gray", 
                opacity=0.5,
                annotation_text=f"Median Risk: {avg_risk:.1f}",
                annotation_position="top"
            )
            
            # Horizontal line for median workload
            fig.add_hline(
                y=avg_workload, 
                line_dash="dash", 
                line_color="gray", 
                opacity=0.5,
                annotation_text=f"Median Workload: {avg_workload:.0f} cases",
                annotation_position="right"
            )
            
            fig.update_layout(
                title={
                    'text': f"Agent Risk Assessment Matrix (Top {top_count})<br>" +
                            "<sub>Bubble Size = Experience | Color = Case Complexity | Lines = Medians</sub>",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Risk Score (Lower = Better Performance)",
                yaxis_title="Current Workload (Active Cases)",
                height=500,
                showlegend=False,
                xaxis=dict(range=[0, max(50, top_agents['RiskScore'].max() * 1.1)]),
                yaxis=dict(range=[0, top_agents['ActiveCases'].max() * 1.1])
            )

        elif metric_type == "handled":
            # Total handled cases (since CitationFee is unreliable)
            fig = go.Figure(data=[go.Bar(
                x=top_agents['Agent'],
                y=top_agents['TotalCasesHandled'],
                marker=dict(
                    color=top_agents['TotalCasesHandled'],
                    colorscale='Blues',
                    showscale=True,
                    colorbar=dict(title="Cases", len=0.5, y=0.8)
                ),
                text=top_agents['TotalCasesHandled'],
                textposition='outside',
                hovertemplate="<b>%{x}</b><br>" +
                            "Total Cases Handled: %{y}<br>" +
                            "Resolution Rate: %{customdata[0]:.1f}%<br>" +
                            "Avg Complexity: %{customdata[1]:.1f}<br>" +
                            "<extra></extra>",
                customdata=top_agents[['ResolutionRate', 'AvgComplexityScore']].values
            )])
            
            fig.update_layout(
                title={
                    'text': f"Top {top_count} Agents by Total Cases Handled",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Compliance Agent",
                yaxis_title="Total Cases Handled",
                height=500,  # Fixed height
                xaxis=dict(tickangle=45)
            )
        
        # Common layout updates
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#2c3e50'},
            margin={'l': 50, 'r': 50, 't': 80, 'b': 120}  # Increased bottom margin for rotated labels
        )
        
        return fig
    
    @monitor_performance("Agent Performance Analysis")
    def analyze_agent_performance(df):
        """Analyze internal compliance agent performance"""
        
        if df.empty:
            return pd.DataFrame(), {}
        
        # Current active workload per compliance agent
        active_cases = df[
            (df['Status'] != 'Closed') | 
            (df['Disposition'].isna()) |
            (df['ClosedOn'].isna())
        ]
        
        agent_workload = active_cases.groupby('AssignedUser').agg({
            'ID': 'count',  # Active cases
            'ViolationName': lambda x: sum(len(v) if isinstance(v, list) else 0 for v in x)  # Total violations
        }).rename(columns={'ID': 'ActiveCases', 'ViolationName': 'TotalViolations'})
        
        # Historical performance analysis
        agent_performance = df.groupby('AssignedUser').agg({
            'ID': 'count',  # Total cases handled
            'CreatedOn': 'min',  # First case date (tenure indicator)
            'Status': lambda x: (x == 'Closed').sum(),  # Closed cases count
            'ClosedOn': lambda x: pd.notna(x).sum()  # Alternative closed count
        }).rename(columns={
            'ID': 'TotalCasesHandled', 
            'CreatedOn': 'FirstCaseDate',
            'Status': 'ClosedCasesStatus',
            'ClosedOn': 'ClosedCasesDate'
        })
        
        # Use the more reliable closed cases count
        agent_performance['ClosedCases'] = agent_performance[['ClosedCasesStatus', 'ClosedCasesDate']].max(axis=1)
        
        # Calculate resolution rate
        agent_performance['ResolutionRate'] = (
            agent_performance['ClosedCases'] / agent_performance['TotalCasesHandled'] * 100
        ).fillna(0)
        
        # Calculate average resolution time for closed cases
        closed_cases = df[df['Status'] == 'Closed'].copy()
        if not closed_cases.empty:
            closed_cases['ResolutionDays'] = (
                pd.to_datetime(closed_cases['ClosedOn'], errors='coerce') - 
                pd.to_datetime(closed_cases['CreatedOn'], errors='coerce')
            ).dt.days
            
            resolution_times = closed_cases.groupby('AssignedUser')['ResolutionDays'].mean().rename('AvgResolutionTime')
        else:
            resolution_times = pd.Series(dtype=float, name='AvgResolutionTime')
        
        # Case complexity scoring
        def calculate_complexity_score(group):
            """Calculate average case complexity for agent workload balancing"""
            complexity_scores = []
            
            for _, row in group.iterrows():
                violation_count = len(row['ViolationName']) if isinstance(row['ViolationName'], list) else 0
                num_events = row.get('NumCaseEvents', 0) if pd.notna(row.get('NumCaseEvents')) else 0
                num_reports = row.get('NumReportIds', 0) if pd.notna(row.get('NumReportIds')) else 0
                
                # Days open calculation
                created_on = pd.to_datetime(row['CreatedOn'], errors='coerce')
                if pd.notna(created_on):
                    if pd.notna(row.get('ClosedOn')):
                        duration = (pd.to_datetime(row['ClosedOn'], errors='coerce') - created_on).days
                    else:
                        duration = (pd.Timestamp.now() - created_on).days
                else:
                    duration = 0
                
                # Weighted complexity score (0-100)
                score = (
                    violation_count * 10 +      # Multiple violations = more complex
                    num_events * 0.5 +          # More events = more activity/complexity
                    num_reports * 5 +           # Multiple reports = more complex
                    min(duration * 0.1, 20)     # Age factor (capped at 20)
                )
                complexity_scores.append(min(score, 100))
            
            return pd.Series(complexity_scores).mean()
        
        agent_complexity = df.groupby('AssignedUser').apply(calculate_complexity_score, include_groups=False).rename('AvgComplexityScore')
        
        # Combine all metrics
        combined_metrics = agent_workload.join(agent_performance, how='outer')
        combined_metrics = combined_metrics.join(resolution_times, how='outer')
        combined_metrics = combined_metrics.join(agent_complexity, how='outer')
        
        # Fill missing values
        combined_metrics = combined_metrics.fillna({
            'ActiveCases': 0,
            'TotalViolations': 0,
            'TotalCasesHandled': 0,
            'ClosedCases': 0,
            'ResolutionRate': 0,
            'AvgResolutionTime': 0,
            'AvgComplexityScore': 0
        })
        
        # Calculate risk score (0-100)
        def calculate_risk_score(row):
            """Calculate composite risk score for agent workload management"""
            if row['TotalCasesHandled'] == 0:
                return 0
            
            # Normalize metrics to 0-1 scale
            max_active = combined_metrics['ActiveCases'].max() if combined_metrics['ActiveCases'].max() > 0 else 1
            max_resolution_time = combined_metrics['AvgResolutionTime'].max() if combined_metrics['AvgResolutionTime'].max() > 0 else 1
            max_complexity = combined_metrics['AvgComplexityScore'].max() if combined_metrics['AvgComplexityScore'].max() > 0 else 1
            
            workload_factor = row['ActiveCases'] / max_active * 40  # 40% weight
            efficiency_factor = (100 - row['ResolutionRate']) / 100 * 30  # 30% weight (inverse of resolution rate)
            speed_factor = row['AvgResolutionTime'] / max_resolution_time * 20  # 20% weight
            complexity_factor = row['AvgComplexityScore'] / max_complexity * 10  # 10% weight
            
            return min(workload_factor + efficiency_factor + speed_factor + complexity_factor, 100)
        
        combined_metrics['RiskScore'] = combined_metrics.apply(calculate_risk_score, axis=1)
        
        # Clean up agent names
        combined_metrics = combined_metrics.reset_index()
        combined_metrics['Agent'] = combined_metrics['AssignedUser'].apply(
            lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != '' else 'Unassigned'
        )
        
        # Create agent initials for risk matrix
        def get_initials(name):
            if name == 'Unassigned' or pd.isna(name):
                return 'UA'
            words = str(name).split()
            if len(words) >= 2:
                return f"{words[0][0]}{words[1][0]}".upper()
            elif len(words) == 1:
                return words[0][:2].upper()
            else:
                return 'XX'
        
        combined_metrics['AgentInitials'] = combined_metrics['Agent'].apply(get_initials)
        
        # Remove unassigned or invalid entries for meaningful analysis
        combined_metrics = combined_metrics[
            (combined_metrics['Agent'] != 'Unassigned') & 
            (combined_metrics['TotalCasesHandled'] > 0)
        ].copy()
        
        # Calculate summary statistics
        total_agents = len(combined_metrics)
        avg_active_cases = combined_metrics['ActiveCases'].mean()
        avg_resolution_rate = combined_metrics['ResolutionRate'].mean()
        avg_resolution_time = combined_metrics['AvgResolutionTime'].mean()
        
        # Identify performance categories
        high_performers = combined_metrics[combined_metrics['ResolutionRate'] >= 80]
        overloaded_agents = combined_metrics[combined_metrics['ActiveCases'] > avg_active_cases * 1.5]
        at_risk_agents = combined_metrics[combined_metrics['RiskScore'] >= 60]
        
        summary_stats = {
            'total_agents': total_agents,
            'avg_active_cases': avg_active_cases,
            'avg_resolution_rate': avg_resolution_rate,
            'avg_resolution_time': avg_resolution_time,
            'high_performers_count': len(high_performers),
            'overloaded_agents_count': len(overloaded_agents),
            'at_risk_agents_count': len(at_risk_agents),
            'total_active_cases': combined_metrics['ActiveCases'].sum(),
            'workload_distribution': {
                'balanced': len(combined_metrics[
                    (combined_metrics['ActiveCases'] >= avg_active_cases * 0.7) & 
                    (combined_metrics['ActiveCases'] <= avg_active_cases * 1.3)
                ]),
                'underloaded': len(combined_metrics[combined_metrics['ActiveCases'] < avg_active_cases * 0.7]),
                'overloaded': len(overloaded_agents)
            }
        }
        
        return combined_metrics, summary_stats
    
    @monitor_performance("Agent Performance Insights Generation")
    def generate_agent_performance_insights(agent_data, summary_stats, metric_type, top_count):
        """Generate insights for agent performance"""
        
        if agent_data.empty:
            return html.Div([
                html.Div([
                    html.Span("👥 ", style={'fontSize': '16px'}),
                    html.Span("**No Agent Data**: No compliance agent performance data available", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        insights = []
        
        # Overall team summary
        total_agents = summary_stats.get('total_agents', 0)
        avg_active = summary_stats.get('avg_active_cases', 0)
        avg_resolution_rate = summary_stats.get('avg_resolution_rate', 0)
        
        insights.append(
            html.Div([
                html.Span("👥 ", style={'fontSize': '16px'}),
                html.Span(f"**Team Overview**: {total_agents} active agents with avg {avg_active:.1f} cases each ({avg_resolution_rate:.1f}% resolution rate)", style={'fontSize': '13px'})
            ], className="mb-2")
        )
        
        # Workload distribution insight
        workload_dist = summary_stats.get('workload_distribution', {})
        balanced = workload_dist.get('balanced', 0)
        overloaded = workload_dist.get('overloaded', 0)
        underloaded = workload_dist.get('underloaded', 0)
        
        if overloaded > 0:
            insights.append(
                html.Div([
                    html.Span("⚠️ ", style={'fontSize': '16px'}),
                    html.Span(f"**Workload Alert**: {overloaded} agents overloaded, {balanced} balanced, {underloaded} underutilized", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Top performer insight
        if not agent_data.empty:
            if metric_type == "count":
                top_agent = agent_data.iloc[0]
                insights.append(
                    html.Div([
                        html.Span("🏆 ", style={'fontSize': '16px'}),
                        html.Span(f"**Highest Caseload**: {top_agent['Agent']} handles {top_agent['ActiveCases']} active cases", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            elif metric_type == "open":
                top_agent = agent_data.iloc[0]
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Top Performer**: {top_agent['Agent']} - {top_agent['ActiveCases']} cases, {top_agent['ResolutionRate']:.1f}% resolution rate", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            elif metric_type == "efficiency":
                high_risk = agent_data[agent_data['RiskScore'] >= 60]
                if not high_risk.empty:
                    insights.append(
                        html.Div([
                            html.Span("🚨 ", style={'fontSize': '16px'}),
                            html.Span(f"**Risk Alert**: {len(high_risk)} agents with high risk scores need attention", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
        
        # Performance insights
        high_performers = summary_stats.get('high_performers_count', 0)
        if high_performers > 0:
            insights.append(
                html.Div([
                    html.Span("⭐ ", style={'fontSize': '16px'}),
                    html.Span(f"**Excellence**: {high_performers} agents maintain >80% resolution rates", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        # Efficiency insight
        avg_resolution_time = summary_stats.get('avg_resolution_time', 0)
        if avg_resolution_time > 0:
            insights.append(
                html.Div([
                    html.Span("⏱️ ", style={'fontSize': '16px'}),
                    html.Span(f"**Resolution Speed**: Average case resolution time is {avg_resolution_time:.1f} days", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        return html.Div(insights, className="insights-container")
    
    @monitor_chart_performance("Enlarged Agent Performance Chart")
    def create_enlarged_agent_performance_chart(original_figure):
        """Create an enlarged version of the agent performance chart for modal display"""
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            enlarged_fig = copy.deepcopy(original_figure)
            enlarged_fig['layout'].update({
                'height': 700,
                'margin': {'l': 200, 'r': 100, 't': 120, 'b': 100},
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
                        'filename': 'compliance_agent_performance_chart',
                        'height': 700,
                        'width': 1400,
                        'scale': 1
                    }
                },
                style={'height': '700px'}
            )
        except Exception as e:
            return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")
    
    # Main chart and insights callback
    @callback(
        [Output("compliance-agent-performance-chart", "figure"),
         Output("compliance-agent-performance-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-agent-metric-dropdown", "value"),
         Input("compliance-agent-count-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Agent Performance Chart Update")
    def update_agent_performance_chart(filter_selections, metric_type, top_count):
        """Update agent performance chart and insights"""
        
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
                    title={'text': "Agent Performance - No Data", 'x': 0.5, 'xanchor': 'center'},
                    height=400
                )
                return fig, html.Div("No data available for analysis.", className="text-muted")
            
            # Apply filters using shared utility
            filtered_data = apply_compliance_filters(base_data, filter_selections)
            
            # Analyze agent performance
            agent_data, summary_stats = analyze_agent_performance(filtered_data)
            
            if agent_data.empty:
                fig = go.Figure()
                fig.add_annotation(
                    text="No agent performance data available with current filters",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=14, color="orange")
                )
                fig.update_layout(
                    title={'text': "Agent Performance - No Data", 'x': 0.5, 'xanchor': 'center'},
                    height=400
                )
                return fig, html.Div("No agent performance data with current filters.", className="text-muted")
            
            # Sort by selected metric
            if metric_type == "count":
                agent_data = agent_data.sort_values('ActiveCases', ascending=False)
            elif metric_type == "handled":
                agent_data = agent_data.sort_values('TotalCasesHandled', ascending=False)
            elif metric_type == "open":
                agent_data = agent_data.sort_values('ActiveCases', ascending=False)
            elif metric_type == "efficiency":
                agent_data = agent_data.sort_values('RiskScore', ascending=False)
            
            # Create chart
            fig = create_agent_performance_chart(agent_data, summary_stats, metric_type, top_count)
            
            # Generate insights
            insights = generate_agent_performance_insights(agent_data, summary_stats, metric_type, top_count)
            
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating agent performance chart: {e}")
            import traceback
            traceback.print_exc()
            
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading agent performance data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Agent Performance - Error", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to load agent performance data", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
    
    # Chart modal callback
    # @callback(
    #     [
    #         Output("compliance-chart-modal", "is_open", allow_duplicate=True),
    #         Output("compliance-modal-chart-content", "children", allow_duplicate=True)
    #     ],
    #     [
    #         Input("compliance-agent-performance-chart", "clickData")
    #     ],
    #     [
    #         State("compliance-agent-performance-chart", "figure"),
    #         State("compliance-chart-modal", "is_open")
    #     ],
    #     prevent_initial_call=True
    # )
    # def toggle_agent_performance_chart_modal(click_data, chart_figure, is_open_state):
    #     """Toggle enlarged agent performance chart modal when chart is clicked"""
    #     if click_data and not is_open_state:
    #         enlarged_chart = create_enlarged_agent_performance_chart(chart_figure)
    #         return True, enlarged_chart
        
    #     return no_update, no_update
    @callback(
        [
            Output("compliance-chart-modal", "is_open", allow_duplicate=True),
            Output("compliance-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("compliance-agent-performance-chart-wrapper", "n_clicks")  
        ],
        [
            State("compliance-agent-performance-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_agent_performance_chart_modal(wrapper_clicks, chart_figure, is_open_state):
        """Toggle enlarged agent performance chart modal on chart wrapper click"""
        
        if wrapper_clicks and not is_open_state and chart_figure:
            enlarged_chart = create_enlarged_agent_performance_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update    

    print("✅ Compliance agent performance callbacks registered")