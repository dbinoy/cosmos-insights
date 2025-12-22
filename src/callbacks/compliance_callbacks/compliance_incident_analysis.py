from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters
from src.utils.performance import monitor_performance, monitor_chart_performance
import numpy as np
from collections import Counter
import copy

def register_compliance_incident_analysis_callbacks(app):
    """Register incident analysis callbacks"""
    
    @monitor_chart_performance("Incident Analysis Chart")
    def create_incident_analysis_chart(filtered_df, view_type):
        """Create incident analysis chart based on view type"""
        
        if filtered_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No incident data found for the selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': "Incident Analysis - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        if view_type == "category":
            
            # Count by violation category
            category_counts = filtered_df['ViolationCategory'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            # Create horizontal bar chart
            colors = px.colors.qualitative.Set1[:len(category_counts)]
            
            fig = go.Figure(data=[go.Bar(
                y=category_counts['Category'],
                x=category_counts['Count'],
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=category_counts['Count'] / category_counts['Count'].sum() * 100,
                text=category_counts['Count'],
                textposition='inside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Compliance Incidents by Category ({category_counts['Count'].sum():,} Total Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Number of Cases",
                yaxis_title="",
                height=400,
                margin={'l': 200, 'r': 50, 't': 80, 'b': 50}
            )
            
        elif view_type == "rule":
            # Count by detailed rule category
            rule_counts = filtered_df['DetailedRuleCategory'].value_counts().reset_index()
            rule_counts.columns = ['RuleCategory', 'Count']
            
            # Create treemap or grouped bar chart
            if len(rule_counts) <= 8:
                # Use pie chart for smaller number of categories
                colors = px.colors.qualitative.Set2[:len(rule_counts)]
                
                fig = go.Figure(data=[go.Pie(
                    labels=rule_counts['RuleCategory'],
                    values=rule_counts['Count'],
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    hovertemplate="<b>%{label}</b><br>Cases: %{value}<br>Percent: %{percent}<extra></extra>"
                )])
                
                # Add center text
                total_cases = rule_counts['Count'].sum()
                fig.add_annotation(
                    text=f"<b>{total_cases:,}</b><br>Total Cases",
                    x=0.5, y=0.5,
                    font_size=14,
                    showarrow=False
                )
                
                fig.update_layout(
                    title={
                        'text': f"Incidents by Rule Type ({total_cases:,} Cases)",
                        'x': 0.5, 'xanchor': 'center'
                    },
                    height=400
                )
            else:
                # Use horizontal bar chart for many categories
                colors = px.colors.qualitative.Set3[:len(rule_counts)]
                
                fig = go.Figure(data=[go.Bar(
                    y=rule_counts['RuleCategory'],
                    x=rule_counts['Count'],
                    orientation='h',
                    marker=dict(color=colors, line=dict(color='white', width=1)),
                    hovertemplate="<b>%{y}</b><br>Cases: %{x}<extra></extra>",
                    text=rule_counts['Count'],
                    textposition='inside'
                )])
                
                fig.update_layout(
                    title={
                        'text': f"Incidents by Rule Type ({rule_counts['Count'].sum():,} Cases)",
                        'x': 0.5, 'xanchor': 'center'
                    },
                    xaxis_title="Number of Cases",
                    yaxis_title="",
                    height=400,
                    margin={'l': 250, 'r': 50, 't': 80, 'b': 50}
                )
            
        elif view_type == "disposition":
            # Analyze by case disposition/resolution patterns
            disposition_counts = filtered_df['Disposition'].value_counts().reset_index()
            disposition_counts.columns = ['Disposition', 'Count']
            
            # Create stacked bar chart to show disposition distribution
            # Color mapping for different dispositions
            disposition_colors = {
                'Citation': '#dc3545',  # Red - serious
                'Warning': '#fd7e14',   # Orange - moderate
                'Corrected': '#28a745', # Green - resolved
                'No Violation': '#6c757d', # Gray - dismissed
                'Investigation': '#007bff', # Blue - in progress
                'Duplicate': '#6f42c1',    # Purple - administrative
                'Withdrawn': '#20c997',     # Teal - voluntary
            }
            
            # Assign colors
            colors = [disposition_colors.get(disp, '#6c757d') for disp in disposition_counts['Disposition']]
            
            fig = go.Figure(data=[go.Bar(
                x=disposition_counts['Disposition'],
                y=disposition_counts['Count'],
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=disposition_counts['Count'] / disposition_counts['Count'].sum() * 100,
                text=disposition_counts['Count'],
                textposition='outside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Incidents by Disposition ({disposition_counts['Count'].sum():,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Disposition Type",
                yaxis_title="Number of Cases",
                height=400
            )
            
        elif view_type == "violation":
            # Get top 15 most frequent violations
            violation_counts = filtered_df['FirstViolation'].value_counts().reset_index()
            violation_counts.columns = ['Violation', 'Count']
            
            # Create horizontal bar chart
            colors = px.colors.sequential.Blues_r[:len(violation_counts)]
            
            fig = go.Figure(data=[go.Bar(
                y=violation_counts['Violation'],
                x=violation_counts['Count'],
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=violation_counts['Count'] / filtered_df.shape[0] * 100,
                text=violation_counts['Count'],
                textposition='inside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Top 15 Most Frequent Violations ({violation_counts['Count'].sum():,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Number of Cases",
                yaxis_title="",
                height=400,
                margin={'l': 300, 'r': 50, 't': 80, 'b': 50}
            )
        
        # Common layout updates
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#2c3e50'},
            margin={'t': 80, 'b': 50}
        )
        
        return fig
    
    @monitor_chart_performance("Enlarged Incident Analysis Chart")
    def create_enlarged_incident_analysis_chart(original_figure):
        """Create an enlarged version of the incident analysis chart for modal display"""
        
        if not original_figure or 'data' not in original_figure:
            return {}
        
        # Create enlarged version with updated layout
        enlarged_fig = copy.deepcopy(original_figure)
        
        # Update layout for modal display
        enlarged_fig['layout'].update({
            'height': 600,  # Larger height for modal
            'margin': {'l': 80, 'r': 80, 't': 100, 'b': 70},
            'title': {
                'text': enlarged_fig['layout'].get('title', {}).get('text', 'Incident Analysis'),
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            'xaxis': {
                'title': {**enlarged_fig['layout'].get('xaxis', {}).get('title', {}), 'font': {'size': 14}},
                'tickfont': {'size': 12}
            },
            'yaxis': {
                'title': {**enlarged_fig['layout'].get('yaxis', {}).get('title', {}), 'font': {'size': 14}},
                'tickfont': {'size': 12}
            }
        })
        
        # Adjust margins for different chart types
        if 'margin' in enlarged_fig['layout']:
            current_margin = enlarged_fig['layout']['margin']
            if current_margin.get('l', 0) > 200:  # Horizontal bar charts need more left margin
                enlarged_fig['layout']['margin']['l'] = max(current_margin['l'] + 50, 350)
        
        return enlarged_fig
    
    @monitor_performance("Incident Analysis Insights Generation")
    def generate_incident_analysis_insights(filtered_df, view_type):
        """Generate insights for incident analysis"""
        
        if filtered_df.empty:
            return html.Div([
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span("**No Data**: No incident data available for analysis", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        insights = []
        total_cases = len(filtered_df)
        
        try:
            if view_type == "category":
                # Use pre-computed ViolationCategory column
                if 'ViolationCategory' not in filtered_df.columns:
                    insights.append(
                        html.Div([
                            html.Span("⚠️ ", style={'fontSize': '16px'}),
                            html.Span("**Data Processing**: Violation categories are being computed. Please refresh in a moment.", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                    return html.Div(insights, className="insights-container")
                
                category_counts = filtered_df['ViolationCategory'].value_counts()
                
                # Most problematic category
                top_category = category_counts.index[0]
                top_count = category_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("🎯 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Problematic Category**: {top_category} accounts for {top_count:,} cases ({top_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Category distribution
                unique_categories = len(category_counts)
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Category Distribution**: {unique_categories} violation categories identified across all incidents", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Second most common category
                if len(category_counts) > 1:
                    second_category = category_counts.index[1]
                    second_count = category_counts.iloc[1]
                    insights.append(
                        html.Div([
                            html.Span("📈 ", style={'fontSize': '16px'}),
                            html.Span(f"**Secondary Issue**: {second_category} represents {second_count:,} cases ({second_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                # Additional category insights based on actual categories
                if "General Citations" in category_counts.index:
                    general_pct = category_counts["General Citations"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("📋 ", style={'fontSize': '16px'}),
                            html.Span(f"**Citation Pattern**: {general_pct:.1f}% of incidents are general citations requiring standard processing", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                if "Listing Management" in category_counts.index:
                    listing_pct = category_counts["Listing Management"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🏠 ", style={'fontSize': '16px'}),
                            html.Span(f"**Listing Issues**: {listing_pct:.1f}% of violations relate to listing management and procedures", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
            elif view_type == "rule":
                # Use pre-computed DetailedRuleCategory column
                if 'DetailedRuleCategory' not in filtered_df.columns:
                    insights.append(
                        html.Div([
                            html.Span("⚠️ ", style={'fontSize': '16px'}),
                            html.Span("**Data Processing**: Detailed rule categories are being computed. Please refresh in a moment.", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                    return html.Div(insights, className="insights-container")
                
                rule_counts = filtered_df['DetailedRuleCategory'].value_counts()
                
                # Most violated rule category
                top_rule_category = rule_counts.index[0]
                top_rule_count = rule_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("⚖️ ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Violated Rules**: {top_rule_category} with {top_rule_count:,} incidents ({top_rule_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Rule coverage
                unique_rule_categories = len(rule_counts)
                insights.append(
                    html.Div([
                        html.Span("📋 ", style={'fontSize': '16px'}),
                        html.Span(f"**Rule Coverage**: {unique_rule_categories} different rule categories involved in compliance incidents", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Specific rule insights based on actual detailed categories
                listing_rules = [rule for rule in rule_counts.index if rule.startswith('7.')]
                if listing_rules:
                    listing_total = sum(rule_counts[rule] for rule in listing_rules)
                    listing_pct = listing_total / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🏠 ", style={'fontSize': '16px'}),
                            html.Span(f"**Listing Rule Impact**: {listing_pct:.1f}% of incidents involve listing rules (7.x series)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                mls_rules = [rule for rule in rule_counts.index if rule.startswith('12.')]
                if mls_rules:
                    mls_total = sum(rule_counts[rule] for rule in mls_rules)
                    mls_pct = mls_total / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🗂️ ", style={'fontSize': '16px'}),
                            html.Span(f"**MLS Rule Impact**: {mls_pct:.1f}% of incidents involve MLS usage rules (12.x series)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                media_rules = [rule for rule in rule_counts.index if rule.startswith('11.')]
                if media_rules:
                    media_total = sum(rule_counts[rule] for rule in media_rules)
                    media_pct = media_total / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("📸 ", style={'fontSize': '16px'}),
                            html.Span(f"**Media Rule Impact**: {media_pct:.1f}% of incidents involve media and photography rules (11.x series)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
            elif view_type == "disposition":
                # Disposition-specific insights (no pre-computed column needed - this is raw data)
                disposition_counts = filtered_df['Disposition'].value_counts()
                
                # Most common disposition
                top_disposition = disposition_counts.index[0]
                top_disp_count = disposition_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Common Resolution**: {top_disposition} accounts for {top_disp_count:,} cases ({top_disp_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Resolution effectiveness analysis
                serious_dispositions = ['Citation', 'Disciplinary']
                serious_count = sum(disposition_counts.get(disp, 0) for disp in serious_dispositions)
                if serious_count > 0:
                    insights.append(
                        html.Div([
                            html.Span("🚨 ", style={'fontSize': '16px'}),
                            html.Span(f"**Serious Actions**: {serious_count:,} cases resulted in citations or disciplinary action ({serious_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                # Proactive resolution patterns
                positive_dispositions = ['Corrected', 'Withdrawn', 'No Violation']
                positive_count = sum(disposition_counts.get(disp, 0) for disp in positive_dispositions)
                if positive_count > 0:
                    insights.append(
                        html.Div([
                            html.Span("✅ ", style={'fontSize': '16px'}),
                            html.Span(f"**Positive Resolutions**: {positive_count:,} cases were corrected, withdrawn, or found without violation ({positive_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                # Process efficiency
                pending_dispositions = ['Investigation', 'Pending', 'Open']
                pending_count = sum(disposition_counts.get(disp, 0) for disp in pending_dispositions)
                if pending_count > 0:
                    insights.append(
                        html.Div([
                            html.Span("⏳ ", style={'fontSize': '16px'}),
                            html.Span(f"**Active Cases**: {pending_count:,} cases still under investigation or pending resolution ({pending_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
            elif view_type == "violation":
                # Use pre-computed FirstViolation column
                if 'FirstViolation' not in filtered_df.columns:
                    insights.append(
                        html.Div([
                            html.Span("⚠️ ", style={'fontSize': '16px'}),
                            html.Span("**Data Processing**: Violation data is being computed. Please refresh in a moment.", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                    return html.Div(insights, className="insights-container")
                
                violation_counts = filtered_df['FirstViolation'].value_counts()
                
                # Most frequent violation
                top_violation = violation_counts.index[0]
                top_violation_count = violation_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("🔥 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Frequent Violation**: {top_violation} with {top_violation_count:,} incidents ({top_violation_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Frequency concentration analysis
                top_5_count = violation_counts.head(5).sum()
                insights.append(
                    html.Div([
                        html.Span("📈 ", style={'fontSize': '16px'}),
                        html.Span(f"**Concentration Analysis**: Top 5 violation types account for {top_5_count:,} incidents ({top_5_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Diversity analysis
                unique_violations = len(violation_counts)
                if unique_violations <= 10:
                    insights.append(
                        html.Div([
                            html.Span("🔍 ", style={'fontSize': '16px'}),
                            html.Span(f"**Focused Issues**: Only {unique_violations} distinct violation types - suggests concentrated compliance problems", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                else:
                    insights.append(
                        html.Div([
                            html.Span("🌐 ", style={'fontSize': '16px'}),
                            html.Span(f"**Diverse Issues**: {unique_violations} different violation types identified across incidents", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                # Pattern recognition for common issues
                citation_violations = [v for v in violation_counts.index if 'Citation' in v or 'citation' in v.lower()]
                if citation_violations:
                    citation_total = sum(violation_counts[v] for v in citation_violations)
                    citation_pct = citation_total / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("📝 ", style={'fontSize': '16px'}),
                            html.Span(f"**Citation Patterns**: {citation_pct:.1f}% of violations involve citation-related issues", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                    
        except Exception as e:
            print(f"Error generating incident analysis insights: {e}")
            insights = [
                html.Div([
                    html.Span("🔄 ", style={'fontSize': '16px'}),
                    html.Span("**Processing**: Incident analysis is being processed...", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span(f"**Dataset**: Analyzing {total_cases:,} compliance incidents", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📋 ", style={'fontSize': '16px'}),
                    html.Span(f"**View**: Showing incident analysis by {view_type}", style={'fontSize': '13px'})
                ], className="mb-2")
            ]
        
        # Ensure we always have at least 3 insights
        while len(insights) < 3:
            if len(insights) == 0:
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Analysis Scope**: Examining {total_cases:,} incidents across multiple violation categories", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            elif len(insights) == 1:
                insights.append(
                    html.Div([
                        html.Span("🎯 ", style={'fontSize': '16px'}),
                        html.Span(f"**View Focus**: Current analysis shows incidents grouped by {view_type} patterns", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            elif len(insights) == 2:
                insights.append(
                    html.Div([
                        html.Span("🔍 ", style={'fontSize': '16px'}),
                        html.Span("**Data Quality**: Analysis based on complete incident records with full categorization", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
        
        return html.Div(insights, className="insights-container")
   
    # Main callback for updating chart and insights
    @callback(
        [Output("compliance-incident-analysis-chart", "figure"),
         Output("compliance-incident-analysis-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-incident-view-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Incident Analysis Chart Update")
    def update_incident_analysis_chart(filter_selections, view_type):
        """Update incident analysis chart and insights"""
        
        try:
            # Get base compliance data
            base_df = get_compliance_base_data()
            
            if base_df.empty:
                return {}, html.Div("No compliance data available")
            
            # Apply filters if any
            if filter_selections:
                filtered_df = apply_compliance_filters(base_df, filter_selections)
            else:
                filtered_df = base_df
            
            # Generate chart and insights
            chart_figure = create_incident_analysis_chart(filtered_df, view_type or "category")
            insights_content = generate_incident_analysis_insights(filtered_df, view_type or "category")
            
            return chart_figure, insights_content
            
        except Exception as e:
            print(f"Error updating incident analysis: {e}")
            return {}, html.Div(f"Error: {str(e)}", className="text-danger")
    
    # Chart modal callback for enlarged view
    @callback(
        [
            Output("compliance-chart-modal", "is_open", allow_duplicate=True),
            Output("compliance-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("compliance-incident-analysis-chart-wrapper", "n_clicks")
        ],
        [
            State("compliance-incident-analysis-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_incident_analysis_chart_modal(wrapper_clicks, chart_figure, is_open_state):
        """Toggle enlarged incident analysis chart modal on chart wrapper click"""
        
        if wrapper_clicks and not is_open_state and chart_figure:
            enlarged_chart = create_enlarged_incident_analysis_chart(chart_figure)
            return True, dcc.Graph(
                figure=enlarged_chart,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 
                                           'drawcircle', 'drawrect', 'eraseshape'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'incident_analysis_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 2
                    }
                }
            )
        
        return no_update, no_update

    # print("✅ Compliance incident analysis callbacks registered")