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
            # Count by violation category and sort in descending order
            category_counts = filtered_df['ViolationCategory'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            # Create vertical bar chart
            colors = px.colors.qualitative.Set1[:len(category_counts)]
            
            fig = go.Figure(data=[go.Bar(
                x=category_counts['Category'],
                y=category_counts['Count'],
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=category_counts['Count'] / category_counts['Count'].sum() * 100,
                text=category_counts['Count'],
                textposition='outside',
                textfont=dict(size=12, color='black')
            )])
            
            # Ensure text labels are always visible
            max_count = category_counts['Count'].max()
            fig.update_traces(
                textposition='outside',
                cliponaxis=False
            )
            
            fig.update_layout(
                title={
                    'text': f"Compliance Incidents by Category ({category_counts['Count'].sum():,} Total Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Violation Categories",
                yaxis_title="Number of Cases",
                height=400,
                margin={'l': 50, 'r': 50, 't': 80, 'b': 120},
                xaxis=dict(
                    tickangle=-45,
                    automargin=True
                ),
                yaxis=dict(
                    range=[0, max_count * 1.15]  # Add extra space for text labels
                )
            )
            
        elif view_type == "rule":
            # Count by detailed rule category and sort in descending order
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
                # Use vertical bar chart for many categories
                colors = px.colors.qualitative.Set3[:len(rule_counts)]
                
                max_count = rule_counts['Count'].max()
                
                fig = go.Figure(data=[go.Bar(
                    x=rule_counts['RuleCategory'],
                    y=rule_counts['Count'],
                    marker=dict(color=colors, line=dict(color='white', width=1)),
                    hovertemplate="<b>%{x}</b><br>Cases: %{y}<extra></extra>",
                    text=rule_counts['Count'],
                    textposition='outside',
                    textfont=dict(size=10, color='black')
                )])
                
                # Ensure text labels are always visible
                fig.update_traces(
                    textposition='outside',
                    cliponaxis=False
                )
                
                fig.update_layout(
                    title={
                        'text': f"Incidents by Rule Type ({rule_counts['Count'].sum():,} Cases)",
                        'x': 0.5, 'xanchor': 'center'
                    },
                    xaxis_title="Rule Categories",
                    yaxis_title="Number of Cases",
                    height=400,
                    margin={'l': 50, 'r': 50, 't': 80, 'b': 150},
                    xaxis=dict(
                        tickangle=-45,
                        automargin=True,
                        tickfont=dict(size=9)
                    ),
                    yaxis=dict(
                        range=[0, max_count * 1.15]  # Add extra space for text labels
                    )
                )
            
        elif view_type == "disposition":
            # Analyze by case disposition/resolution patterns (keep as vertical already)
            disposition_counts = filtered_df['Disposition'].value_counts().reset_index()
            disposition_counts.columns = ['Disposition', 'Count']
            
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
            max_count = disposition_counts['Count'].max()
            
            fig = go.Figure(data=[go.Bar(
                x=disposition_counts['Disposition'],
                y=disposition_counts['Count'],
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=disposition_counts['Count'] / disposition_counts['Count'].sum() * 100,
                text=disposition_counts['Count'],
                textposition='outside',
                textfont=dict(size=12, color='black')
            )])
            
            # Ensure text labels are always visible
            fig.update_traces(
                textposition='outside',
                cliponaxis=False
            )
            
            fig.update_layout(
                title={
                    'text': f"Incidents by Disposition ({disposition_counts['Count'].sum():,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Disposition Type",
                yaxis_title="Number of Cases",
                height=400,
                margin={'l': 50, 'r': 50, 't': 80, 'b': 100},
                yaxis=dict(
                    range=[0, max_count * 1.15]  # Add extra space for text labels
                )
            )
            
        elif view_type == "violation":
            # Get top 15 most frequent violations and sort in descending order
            violation_counts = filtered_df['FirstViolation'].value_counts().head(15).reset_index()
            violation_counts.columns = ['Violation', 'Count']
            
            # Create vertical bar chart
            colors = px.colors.sequential.Blues_r[:len(violation_counts)]
            max_count = violation_counts['Count'].max()
            
            fig = go.Figure(data=[go.Bar(
                x=violation_counts['Violation'],
                y=violation_counts['Count'],
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=violation_counts['Count'] / filtered_df.shape[0] * 100,
                text=violation_counts['Count'],
                textposition='outside',
                textfont=dict(size=10, color='black')
            )])
            
            # Ensure text labels are always visible
            fig.update_traces(
                textposition='outside',
                cliponaxis=False
            )
            
            fig.update_layout(
                title={
                    'text': f"Top 15 Most Common Violations ({violation_counts['Count'].sum():,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Violation Types",
                yaxis_title="Number of Cases",
                height=400,
                margin={'l': 50, 'r': 50, 't': 80, 'b': 200},
                xaxis=dict(
                    tickangle=-45,
                    automargin=True,
                    tickfont=dict(size=8)
                ),
                yaxis=dict(
                    range=[0, max_count * 1.15]  # Add extra space for text labels
                )
            )
        
        # Common layout updates
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#2c3e50'},
            showlegend=False if view_type != "rule" or len(rule_counts) > 8 else True
        )
        
        return fig
   
    @monitor_chart_performance("Enlarged Incident Analysis Chart")
    def create_enlarged_incident_analysis_chart(original_figure):
        """Create an enlarged version of the incident analysis chart for modal display"""
        
        if not original_figure or 'data' not in original_figure:
            return {}
        
        enlarged_fig = copy.deepcopy(original_figure)
        
        original_margin = enlarged_fig['layout'].get('margin', {})
        original_bottom = original_margin.get('b', 50)
        
        if original_bottom >= 150:  # Violation charts with long labels
            enlarged_margins = {'l': 80, 'r': 80, 't': 120, 'b': 250}
        elif original_bottom >= 120:  # Category charts with angled labels  
            enlarged_margins = {'l': 80, 'r': 80, 't': 120, 'b': 150}
        else:  # Disposition and pie charts
            enlarged_margins = {'l': 80, 'r': 80, 't': 120, 'b': 100}
        
        # Update layout for modal display
        enlarged_fig['layout'].update({
            'height': 650,  # Larger height for modal
            'margin': enlarged_margins,
            'title': {
                'text': enlarged_fig['layout'].get('title', {}).get('text', 'Incident Analysis'),
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            'xaxis': {
                **enlarged_fig['layout'].get('xaxis', {}),
                'title': {
                    **enlarged_fig['layout'].get('xaxis', {}).get('title', {}), 
                    'font': {'size': 16}
                },
                'tickfont': {'size': 13}
            },
            'yaxis': {
                **enlarged_fig['layout'].get('yaxis', {}),
                'title': {
                    **enlarged_fig['layout'].get('yaxis', {}).get('title', {}), 
                    'font': {'size': 16}
                },
                'tickfont': {'size': 13}
            }
        })
        
        # Adjust text labels for better visibility in enlarged view
        if 'data' in enlarged_fig and enlarged_fig['data']:
            for trace in enlarged_fig['data']:
                if 'textfont' in trace:
                    trace['textfont'].update({'size': 14, 'color': 'black'})
        
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
   
    def create_case_number_cell(case_number, description, index):
        """Create case number cell with tooltip for description"""
        return html.Td([
            html.Div([
                html.Span(
                    case_number, 
                    id=f"incident-case-number-{index}",
                    style={
                        'fontSize': '12px', 
                        'fontFamily': 'monospace', 
                        'fontWeight': 'bold',
                        'cursor': 'help',
                        'borderBottom': '1px dotted #28a745',
                        'color': '#28a745'
                    }
                ),
                html.Span(
                    " 📋", 
                    style={
                        'fontSize': '10px',
                        'opacity': '0.7',
                        'marginLeft': '4px'
                    }
                ),
                dbc.Tooltip(
                    html.Div([
                        html.Div([
                            html.Strong("Case Description:", className="me-2"),
                            html.Span(description if description and description.strip() else "No description available")
                        ], style={
                            'fontSize': '12px', 
                            'lineHeight': '1.5',
                            'color': '#495057',
                            'margin': '0'
                        })
                    ], style={
                        'maxWidth': '400px', 
                        'textAlign': 'left',
                        'padding': '12px',
                        'backgroundColor': '#f8f9fa',
                        'border': '1px solid #28a745',
                        'borderRadius': '6px'
                    }),
                    target=f"incident-case-number-{index}",
                    placement="top",
                    style={'maxWidth': '450px'}
                )
            ])
        ])

    @monitor_performance("Incident Analysis Details Table Creation")
    def create_incident_analysis_details_table(filtered_df, view_type):
        """Create detailed breakdown table for modal display"""
        if filtered_df.empty:
            return html.Div([
                html.H4("No Incident Data", className="text-info mb-3"),
                html.P("No compliance incidents found for the selected filters.", className="text-muted")
            ], className="text-center p-4")
        
        try:
            # Get latest 50 cases by CreatedOn
            latest_cases = filtered_df.nlargest(50, 'CreatedOn').copy()
            
            # Summary metrics
            total_cases = len(filtered_df)
            showing_count = len(latest_cases)
            
            # Create summary cards
            summary_cards = dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📊 Total Cases", className="text-primary mb-1"),
                            html.H4(f"{total_cases:,}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-primary")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📋 Showing Latest", className="text-info mb-1"),
                            html.H4(f"{showing_count}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-info")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("🎯 View Type", className="text-success mb-1"),
                            html.H6(f"By {view_type.title()}", className="mb-0")
                        ], className="text-center py-2")
                    ], className="border-success")
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("📅 Date Range", className="text-warning mb-1"),
                            html.H6(f"{latest_cases['CreatedOn'].min().strftime('%m/%d/%Y')}", className="mb-0", style={'fontSize': '12px'})
                        ], className="text-center py-2")
                    ], className="border-warning")
                ], width=3)
            ], className="mb-4")
            
            # Prepare data based on view type
            table_data = latest_cases.copy()
            table_data['FormattedDate'] = table_data['CreatedOn'].dt.strftime('%m/%d/%Y')
            
            # Define columns based on view type
            if view_type == "category":
                headers = [
                    html.Th("Case Number", style={'width': '20%'}),
                    html.Th("Rule Number", style={'width': '15%'}),
                    html.Th("Rule Title", style={'width': '35%'}),
                    html.Th("Violation Category", style={'width': '20%'}),
                    html.Th("Created", style={'width': '10%'})
                ]
                
                def get_row_data(row, i):
                    # Get first rule number and title for display
                    rule_number = row['RuleNumber'][0] if isinstance(row['RuleNumber'], list) and row['RuleNumber'] else 'N/A'
                    rule_title = row['RuleTitle'][0] if isinstance(row['RuleTitle'], list) and row['RuleTitle'] else 'N/A'
                    violation_category = row.get('ViolationCategory', 'Unknown')
                    
                    return [
                        create_case_number_cell(row['CaseNumber'], row.get('Description', ''), i),
                        html.Td(rule_number, style={'fontSize': '12px', 'fontFamily': 'monospace'}),
                        html.Td(rule_title, style={'fontSize': '12px'}),
                        html.Td(violation_category, style={'fontSize': '12px', 'fontWeight': 'bold'}),
                        html.Td(row['FormattedDate'], style={'fontSize': '11px'})
                    ]
            
            elif view_type == "rule":
                headers = [
                    html.Th("Case Number", style={'width': '20%'}),
                    html.Th("Rule Number", style={'width': '15%'}),
                    html.Th("Rule Title", style={'width': '35%'}),
                    html.Th("Detailed Rule Category", style={'width': '20%'}),
                    html.Th("Created", style={'width': '10%'})
                ]
                
                def get_row_data(row, i):
                    rule_number = row['RuleNumber'][0] if isinstance(row['RuleNumber'], list) and row['RuleNumber'] else 'N/A'
                    rule_title = row['RuleTitle'][0] if isinstance(row['RuleTitle'], list) and row['RuleTitle'] else 'N/A'
                    detailed_rule_category = row.get('DetailedRuleCategory', 'Unknown')
                    
                    return [
                        create_case_number_cell(row['CaseNumber'], row.get('Description', ''), i),
                        html.Td(rule_number, style={'fontSize': '12px', 'fontFamily': 'monospace'}),
                        html.Td(rule_title, style={'fontSize': '12px'}),
                        html.Td(detailed_rule_category, style={'fontSize': '12px', 'fontWeight': 'bold'}),
                        html.Td(row['FormattedDate'], style={'fontSize': '11px'})
                    ]
            
            elif view_type == "violation":
                headers = [
                    html.Th("Case Number", style={'width': '20%'}),
                    html.Th("Rule Number", style={'width': '15%'}),
                    html.Th("Rule Title", style={'width': '25%'}),
                    html.Th("Violation Name", style={'width': '30%'}),
                    html.Th("Created", style={'width': '10%'})
                ]
                
                def get_row_data(row, i):
                    rule_number = row['RuleNumber'][0] if isinstance(row['RuleNumber'], list) and row['RuleNumber'] else 'N/A'
                    rule_title = row['RuleTitle'][0] if isinstance(row['RuleTitle'], list) and row['RuleTitle'] else 'N/A'
                    # Get first violation name for display
                    first_violation = row.get('FirstViolation', 'Unknown')
                    
                    return [
                        create_case_number_cell(row['CaseNumber'], row.get('Description', ''), i),
                        html.Td(rule_number, style={'fontSize': '12px', 'fontFamily': 'monospace'}),
                        html.Td(rule_title, style={'fontSize': '12px'}),
                        html.Td(first_violation, style={'fontSize': '12px', 'fontWeight': 'bold'}),
                        html.Td(row['FormattedDate'], style={'fontSize': '11px'})
                    ]
            
            elif view_type == "disposition":
                headers = [
                    html.Th("Case Number", style={'width': '25%'}),
                    html.Th("Disposition", style={'width': '20%'}),
                    html.Th("Status", style={'width': '15%'}),
                    html.Th("Assigned User", style={'width': '25%'}),
                    html.Th("Created", style={'width': '15%'})
                ]
                
                def get_row_data(row, i):
                    disposition = row.get('Disposition', 'Unknown')
                    status = row.get('Status', 'Unknown')
                    assigned_user = row.get('AssignedUser', 'Unassigned')
                    
                    # Color coding for disposition
                    disposition_colors = {
                        'Citation': 'text-danger',
                        'Warning': 'text-warning',
                        'Corrected': 'text-success',
                        'No Violation': 'text-secondary',
                        'Investigation': 'text-primary',
                        'Duplicate': 'text-info',
                        'Withdrawn': 'text-muted'
                    }
                    disposition_class = disposition_colors.get(disposition, 'text-dark')
                    
                    return [
                        create_case_number_cell(row['CaseNumber'], row.get('Description', ''), i),
                        html.Td(disposition, className=disposition_class, style={'fontSize': '12px', 'fontWeight': 'bold'}),
                        html.Td(status, style={'fontSize': '12px'}),
                        html.Td(assigned_user, style={'fontSize': '12px'}),
                        html.Td(row['FormattedDate'], style={'fontSize': '11px'})
                    ]
            
            # Create table rows
            table_rows = []
            for i, (_, row) in enumerate(table_data.iterrows()):
                cells = get_row_data(row, i)
                table_rows.append(html.Tr(cells, className=""))
            
            return html.Div([
                html.H4(f"Incident Analysis Details - {view_type.title()} View", className="mb-3 text-primary"),
                
                # Summary cards
                summary_cards,
                
                html.P([
                    html.Span([
                        html.I(className="fas fa-calendar me-2"),
                        f"Latest {showing_count} incidents from {total_cases:,} total cases"
                    ], className="me-4"),
                    html.Span([
                        html.I(className="fas fa-filter me-2"),
                        f"Filtered by {view_type} analysis"
                    ])
                ], className="text-muted mb-4"),
                
                html.Table([
                    html.Thead([
                        html.Tr(headers, style={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'})
                    ]),
                    html.Tbody(table_rows)
                ], className="table table-hover table-striped table-sm"),
                
            ], className="p-3")
            
        except Exception as e:
            return html.Div([
                html.H4("Error Creating Incident Details", className="text-danger mb-3"),
                html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
            ], className="text-center p-4")

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
                fig = go.Figure()
                fig.add_annotation(
                    text="No compliance data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=14, color="gray")
                )
                fig.update_layout(
                    title={'text': "Incident Analysis - No Data", 'x': 0.5, 'xanchor': 'center'},
                    height=400
                )
                return fig, html.Div("No data available")
            
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
            
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Incident Analysis - Error", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to load incident data", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
   
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

    @callback(
        [Output("compliance-incident-details-modal", "is_open"),
        Output("compliance-incident-details-content", "children")],
        [Input("compliance-incident-details-btn", "n_clicks")],
        [State("compliance-incident-details-modal", "is_open"),
        State("compliance-filtered-query-store", "data"),
        State("compliance-incident-view-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Incident Analysis Details Modal Toggle")
    def toggle_incident_details_modal(details_btn_clicks, is_open, filter_selections, view_type):
        """Handle opening of incident analysis details modal"""
        if details_btn_clicks:
            if not is_open:
                try:
                    # Get filtered data
                    base_data = get_compliance_base_data()
                    
                    if base_data.empty:
                        error_content = html.Div([
                            html.H4("No Data Available", className="text-warning mb-3"),
                            html.P("No compliance data is currently available for analysis.", className="text-muted")
                        ], className="text-center p-4")
                        return True, error_content
                    
                    filtered_data = apply_compliance_filters(base_data, filter_selections or {})
                    
                    if filtered_data.empty:
                        error_content = html.Div([
                            html.H4("No Matching Data", className="text-info mb-3"),
                            html.P("No incidents match the current filter criteria.", className="text-muted")
                        ], className="text-center p-4")
                        return True, error_content
                    
                    # Create detailed table
                    detailed_table = create_incident_analysis_details_table(filtered_data, view_type or "category")
                    
                    return True, detailed_table
                    
                except Exception as e:
                    print(f"❌ Error generating incident analysis details: {e}")
                    error_content = html.Div([
                        html.H4("Error Loading Incident Details", className="text-danger mb-3"),
                        html.P(f"Unable to load detailed breakdown: {str(e)}", className="text-muted")
                    ], className="text-center p-4")
                    return True, error_content
            else:
                return False, no_update
        
        return no_update, no_update

    @callback(
        Output("compliance-incident-details-modal", "is_open", allow_duplicate=True),
        [Input("compliance-incident-details-close-btn", "n_clicks")],
        [State("compliance-incident-details-modal", "is_open")],
        prevent_initial_call=True
    )
    def close_incident_details_modal(close_clicks, is_open):
        """Close the incident details modal when close button is clicked"""
        if close_clicks and is_open:
            return False
        return no_update
    
    # print("✅ Compliance incident analysis callbacks registered")