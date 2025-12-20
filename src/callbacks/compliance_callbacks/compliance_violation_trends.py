from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters, classify_case_severity
from src.utils.performance import monitor_performance, monitor_chart_performance
import numpy as np
from datetime import datetime, timedelta
import copy

def register_compliance_violation_trends_callbacks(app):
    """Register violation trends callbacks"""
    
    @monitor_chart_performance("Violation Trends Chart")
    def create_violation_trends_chart(filtered_df, period, metric):
        """Create violation trends chart based on period and metric"""
        
        if filtered_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No violation data found for the selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': "Violation Trends - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        # Prepare time periods
        period_mapping = {
            'daily': {'freq': 'D', 'format': '%Y-%m-%d', 'label': 'Daily'},
            'weekly': {'freq': 'W', 'format': '%Y-W%U', 'label': 'Weekly'},  
            'monthly': {'freq': 'M', 'format': '%Y-%m', 'label': 'Monthly'},
            'quarterly': {'freq': 'Q', 'format': '%Y-Q%q', 'label': 'Quarterly'}
        }
        
        period_config = period_mapping.get(period, period_mapping['monthly'])
        
        # Ensure we have date column
        if 'CreatedOn' not in filtered_df.columns:
            fig = go.Figure()
            fig.add_annotation(text="Date information not available", 
                             xref="paper", yref="paper", x=0.5, y=0.5,
                             showarrow=False, font=dict(size=14, color="gray"))
            fig.update_layout(title="Violation Trends - Date Data Missing", height=400)
            return fig
        
        # Convert dates and filter recent data (last 2 years for trends)
        df_trends = filtered_df.copy()
        df_trends['CreatedOn'] = pd.to_datetime(df_trends['CreatedOn'], errors='coerce')
        df_trends = df_trends.dropna(subset=['CreatedOn'])
        
        if df_trends.empty:
            fig = go.Figure()
            fig.add_annotation(text="No valid date data found", 
                             xref="paper", yref="paper", x=0.5, y=0.5,
                             showarrow=False, font=dict(size=14, color="gray"))
            fig.update_layout(title="Violation Trends - Invalid Dates", height=400)
            return fig
        
        # Filter to last 2 years for meaningful trends
        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=730)
        df_trends = df_trends[df_trends['CreatedOn'] >= cutoff_date]
        
        if df_trends.empty:
            fig = go.Figure()
            fig.add_annotation(text="No recent violation data (last 2 years)", 
                             xref="paper", yref="paper", x=0.5, y=0.5,
                             showarrow=False, font=dict(size=14, color="gray"))
            fig.update_layout(title="Violation Trends - No Recent Data", height=400)
            return fig
        
        # Create period column
        if period == 'daily':
            df_trends['Period'] = df_trends['CreatedOn'].dt.date
        elif period == 'weekly':
            df_trends['Period'] = df_trends['CreatedOn'].dt.to_period('W').dt.start_time.dt.date
        elif period == 'monthly':
            df_trends['Period'] = df_trends['CreatedOn'].dt.to_period('M').dt.start_time.dt.date
        elif period == 'quarterly':
            df_trends['Period'] = df_trends['CreatedOn'].dt.to_period('Q').dt.start_time.dt.date
        
        # Generate chart based on metric
        if metric == "violation_types":
            # Track top violation types over time
            def get_first_violation(violation_list):
                if isinstance(violation_list, list) and len(violation_list) > 0:
                    return violation_list[0] if violation_list[0] is not None else "Other"
                return "Other"
            
            df_trends['FirstViolation'] = df_trends['ViolationName'].apply(get_first_violation)
            
            # Get top 10 violation types overall
            top_violations = df_trends['FirstViolation'].value_counts().head(10).index.tolist()
            df_trends['ViolationCategory'] = df_trends['FirstViolation'].apply(
                lambda x: x if x in top_violations else "Other"
            )
            
            # Group by period and violation type
            violation_trends = df_trends.groupby(['Period', 'ViolationCategory']).size().reset_index(name='Count')
            violation_pivot = violation_trends.pivot(index='Period', columns='ViolationCategory', values='Count').fillna(0)
            
            # Create stacked area chart
            fig = go.Figure()
            
            colors = px.colors.qualitative.Set3[:len(violation_pivot.columns)]
            
            for i, violation_type in enumerate(violation_pivot.columns):
                if violation_type != "Other":  # Show "Other" last
                    fig.add_trace(go.Scatter(
                        x=violation_pivot.index,
                        y=violation_pivot[violation_type],
                        mode='lines',
                        name=violation_type,
                        fill='tonexty' if i > 0 else 'tozeroy',
                        line=dict(width=1, color=colors[i % len(colors)]),
                        hovertemplate=f"<b>{violation_type}</b><br>Date: %{{x}}<br>Count: %{{y}}<extra></extra>"
                    ))
            
            # Add "Other" category last if it exists
            if "Other" in violation_pivot.columns:
                fig.add_trace(go.Scatter(
                    x=violation_pivot.index,
                    y=violation_pivot["Other"],
                    mode='lines',
                    name="Other",
                    fill='tonexty',
                    line=dict(width=1, color='lightgray'),
                    hovertemplate="<b>Other</b><br>Date: %{x}<br>Count: %{y}<extra></extra>"
                ))
            
            fig.update_layout(
                title=f"{period_config['label']} Violation Type Trends (Top 10)",
                xaxis_title="Time Period",
                yaxis_title="Number of Cases",
                hovermode='x unified'
            )
            
        elif metric == "rule_categories":
            # Group violations by rule number categories (7.x, 12.x, etc.)
            def categorize_rule(rule_list):
                if not isinstance(rule_list, list) or len(rule_list) == 0:
                    return "Other"
                
                # Get first rule number
                first_rule = rule_list[0] if rule_list[0] is not None else ""
                if not first_rule:
                    return "Other"
                
                rule_str = str(first_rule)
                
                # Extract rule family
                if rule_str.startswith('7.'):
                    return "7.x - Listing Rules"
                elif rule_str.startswith('12.'):
                    return "12.x - MLS Usage Rules"
                elif rule_str.startswith('11.'):
                    return "11.x - Media Rules"
                elif rule_str.startswith('8.'):
                    return "8.x - Documentation Rules"
                elif rule_str.startswith('9.'):
                    return "9.x - Showing Rules"
                elif rule_str.startswith('13.'):
                    return "13.x - Lockbox Rules"
                elif rule_str.startswith('14.'):
                    return "14.x - Information Rules"
                elif rule_str.startswith('4.') or rule_str.startswith('5.'):
                    return "4-5.x - Participation Rules"
                elif rule_str.startswith('10.'):
                    return "10.x - Coming Soon Rules"
                else:
                    return "Other Rules"
            
            df_trends['RuleCategory'] = df_trends['RuleNumber'].apply(categorize_rule)
            
            # Group by period and rule category
            rule_trends = df_trends.groupby(['Period', 'RuleCategory']).size().reset_index(name='Count')
            
            # Create multi-line chart
            fig = go.Figure()
            
            rule_categories = rule_trends['RuleCategory'].unique()
            colors = px.colors.qualitative.Set1[:len(rule_categories)]
            
            for i, rule_cat in enumerate(sorted(rule_categories)):
                if rule_cat != "Other":  # Show "Other" last
                    cat_data = rule_trends[rule_trends['RuleCategory'] == rule_cat]
                    fig.add_trace(go.Scatter(
                        x=cat_data['Period'],
                        y=cat_data['Count'],
                        mode='lines+markers',
                        name=rule_cat,
                        line=dict(width=3, color=colors[i % len(colors)]),
                        marker=dict(size=6),
                        hovertemplate=f"<b>{rule_cat}</b><br>Date: %{{x}}<br>Cases: %{{y}}<extra></extra>"
                    ))
            
            # Add "Other" category last if it exists
            if "Other" in rule_categories:
                other_data = rule_trends[rule_trends['RuleCategory'] == "Other"]
                fig.add_trace(go.Scatter(
                    x=other_data['Period'],
                    y=other_data['Count'],
                    mode='lines+markers',
                    name="Other Rules",
                    line=dict(width=2, color='gray', dash='dash'),
                    marker=dict(size=4),
                    hovertemplate="<b>Other Rules</b><br>Date: %{x}<br>Cases: %{y}<extra></extra>"
                ))
            
            fig.update_layout(
                title=f"{period_config['label']} Violation Trends by Rule Category",
                xaxis_title="Time Period",
                yaxis_title="Number of Cases",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
        elif metric == "violation_volume":
            # Simple volume trend with moving average
            volume_trends = df_trends.groupby('Period').size().reset_index(name='Count')
            volume_trends['Period'] = pd.to_datetime(volume_trends['Period'])
            volume_trends = volume_trends.sort_values('Period')
            
            # Calculate moving average (adjust window based on period)
            window_size = {'daily': 7, 'weekly': 4, 'monthly': 3, 'quarterly': 2}
            ma_window = window_size.get(period, 3)
            
            volume_trends['MovingAvg'] = volume_trends['Count'].rolling(window=ma_window, center=True).mean()
            
            fig = go.Figure()
            
            # Add volume bars
            fig.add_trace(go.Bar(
                x=volume_trends['Period'],
                y=volume_trends['Count'],
                name=f'{period_config["label"]} Volume',
                marker_color='#3498db',
                opacity=0.7,
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<extra></extra>"
            ))
            
            # Add trend line if we have enough data
            if len(volume_trends) >= ma_window:
                fig.add_trace(go.Scatter(
                    x=volume_trends['Period'],
                    y=volume_trends['MovingAvg'],
                    mode='lines',
                    name=f'{ma_window}-Period Trend',
                    line=dict(color='#e74c3c', width=3),
                    hovertemplate="<b>%{x}</b><br>Avg: %{y:.1f}<extra></extra>"
                ))
            
            fig.update_layout(
                title=f"{period_config['label']} Violation Volume Trends",
                xaxis_title="Time Period",
                yaxis_title="Number of Cases",
                showlegend=True
            )
            
        elif metric == "severity_trends":
            # Analyze case severity distribution over time
            df_classified = classify_case_severity(df_trends)
            
            if 'FinalSeverity' not in df_classified.columns:
                fig = go.Figure()
                fig.add_annotation(text="Severity classification not available", 
                                 xref="paper", yref="paper", x=0.5, y=0.5,
                                 showarrow=False, font=dict(size=14, color="gray"))
                fig.update_layout(title="Severity Trends - Classification Error", height=400)
                return fig
            
            # Group by period and severity
            severity_trends = df_classified.groupby(['Period', 'FinalSeverity']).size().reset_index(name='Count')
            severity_pivot = severity_trends.pivot(index='Period', columns='FinalSeverity', values='Count').fillna(0)
            
            # Create stacked bar chart
            fig = go.Figure()
            
            severity_colors = {
                'CRITICAL': '#dc3545',  # Red
                'HIGH': '#fd7e14',      # Orange
                'MEDIUM': '#ffc107',    # Yellow
                'LOW': '#28a745',       # Green
                'RESOLVED': '#6c757d',  # Gray
                'DATA_ISSUE': '#e9ecef' # Light gray
            }
            
            severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'RESOLVED', 'DATA_ISSUE']
            
            for severity in severity_order:
                if severity in severity_pivot.columns:
                    fig.add_trace(go.Bar(
                        x=severity_pivot.index,
                        y=severity_pivot[severity],
                        name=severity,
                        marker_color=severity_colors.get(severity, '#6c757d'),
                        hovertemplate=f"<b>{severity}</b><br>Date: %{{x}}<br>Cases: %{{y}}<extra></extra>"
                    ))
            
            fig.update_layout(
                title=f"{period_config['label']} Case Severity Distribution Trends",
                xaxis_title="Time Period", 
                yaxis_title="Number of Cases",
                barmode='stack',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
        
        # Common layout updates
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#2c3e50'},
            height=400,
            margin={'l': 50, 'r': 50, 't': 80, 'b': 50}
        )
        
        return fig
    
    @monitor_chart_performance("Enlarged Violation Trends Chart")
    def create_enlarged_violation_trends_chart(original_figure):
        """Create an enlarged version of the violation trends chart for modal display"""
        
        if not original_figure or 'data' not in original_figure:
            return {}
        
        # Create enlarged version with updated layout
        enlarged_fig = copy.deepcopy(original_figure)
        
        # Update layout for modal display
        enlarged_fig['layout'].update({
            'height': 600,  # Larger height for modal
            'margin': {'l': 70, 'r': 70, 't': 100, 'b': 70},
            'title': {
                'text': enlarged_fig['layout'].get('title', {}).get('text', 'Violation Trends'),
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': 1.02,
                'xanchor': 'center',
                'x': 0.5,
                'bgcolor': 'rgba(255,255,255,0.8)',
                'bordercolor': '#ddd',
                'borderwidth': 1
            },
            'xaxis': {
                'title': {'font': {'size': 14}},
                'tickfont': {'size': 12}
            },
            'yaxis': {
                'title': {'font': {'size': 14}},
                'tickfont': {'size': 12}
            }
        })
        
        # Enhanced hover templates for larger display
        if 'data' in enlarged_fig:
            for trace in enlarged_fig['data']:
                if 'hovertemplate' in trace:
                    # Keep existing hover templates but could enhance if needed
                    pass
        
        return enlarged_fig

    @monitor_performance("Violation Trends Insights Generation")
    def generate_violation_trends_insights(filtered_df, period, metric):
        """Generate insights for violation trends"""
        
        if filtered_df.empty:
            return html.Div([
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span("**No Data**: No violation data available for analysis", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        # Prepare data for insights
        df_analysis = filtered_df.copy()
        df_analysis['CreatedOn'] = pd.to_datetime(df_analysis['CreatedOn'], errors='coerce')
        df_analysis = df_analysis.dropna(subset=['CreatedOn'])
        
        if df_analysis.empty:
            return html.Div([
                html.Div([
                    html.Span("📅 ", style={'fontSize': '16px'}),
                    html.Span("**Date Issue**: Invalid date data for trend analysis", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        # Filter to last 2 years for insights
        cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=730)
        df_analysis = df_analysis[df_analysis['CreatedOn'] >= cutoff_date]
        
        if len(df_analysis) < 2:
            return html.Div([
                html.Div([
                    html.Span("⚠️ ", style={'fontSize': '16px'}),
                    html.Span("**Insufficient Data**: Not enough data for trend analysis", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        insights = []
        
        try:
            if metric == "violation_types":
                # Most common violation type
                def get_first_violation(violation_list):
                    if isinstance(violation_list, list) and len(violation_list) > 0:
                        return violation_list[0] if violation_list[0] is not None else "Other"
                    return "Other"
                
                df_analysis['FirstViolation'] = df_analysis['ViolationName'].apply(get_first_violation)
                violation_counts = df_analysis['FirstViolation'].value_counts()
                top_violation = violation_counts.index[0]
                top_count = violation_counts.iloc[0]
                total_cases = len(df_analysis)
                
                insights.append(
                    html.Div([
                        html.Span("🎯 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Common Violation**: {top_violation} ({top_count:,} cases, {top_count/total_cases*100:.1f}% of all violations)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Growth trend comparison
                recent_30d = df_analysis[df_analysis['CreatedOn'] >= pd.Timestamp.now() - pd.Timedelta(days=30)]
                previous_30d = df_analysis[
                    (df_analysis['CreatedOn'] >= pd.Timestamp.now() - pd.Timedelta(days=60)) &
                    (df_analysis['CreatedOn'] < pd.Timestamp.now() - pd.Timedelta(days=30))
                ]
                
                if len(previous_30d) > 0:
                    growth = (len(recent_30d) - len(previous_30d)) / len(previous_30d) * 100
                    if growth > 5:
                        insights.append(
                            html.Div([
                                html.Span("📈 ", style={'fontSize': '16px'}),
                                html.Span(f"**Trending Up**: Violation cases increased {growth:.1f}% in the last 30 days", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                    elif growth < -5:
                        insights.append(
                            html.Div([
                                html.Span("📉 ", style={'fontSize': '16px'}),
                                html.Span(f"**Trending Down**: Violation cases decreased {abs(growth):.1f}% in the last 30 days", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                    else:
                        insights.append(
                            html.Div([
                                html.Span("📊 ", style={'fontSize': '16px'}),
                                html.Span(f"**Stable Trend**: Violation volume relatively stable ({growth:+.1f}% change)", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                
                # Violation diversity insight
                unique_violations = len(violation_counts)
                if unique_violations >= 5:
                    top_5_pct = violation_counts.head(5).sum() / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🌐 ", style={'fontSize': '16px'}),
                            html.Span(f"**Violation Diversity**: {unique_violations} different violation types, top 5 represent {top_5_pct:.1f}% of cases", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                else:
                    insights.append(
                        html.Div([
                            html.Span("🔍 ", style={'fontSize': '16px'}),
                            html.Span(f"**Focused Issues**: Only {unique_violations} violation types detected - concentrated compliance issues", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
            
            elif metric == "rule_categories":
                # Rule category analysis
                def categorize_rule(rule_list):
                    if not isinstance(rule_list, list) or len(rule_list) == 0:
                        return "Other"
                    first_rule = str(rule_list[0]) if rule_list[0] is not None else ""
                    if first_rule.startswith('7.'):
                        return "7.x - Listing Rules"
                    elif first_rule.startswith('12.'):
                        return "12.x - MLS Usage Rules"
                    elif first_rule.startswith('11.'):
                        return "11.x - Media Rules"
                    elif first_rule.startswith('8.'):
                        return "8.x - Documentation Rules"
                    elif first_rule.startswith('9.'):
                        return "9.x - Showing Rules"
                    elif first_rule.startswith('13.'):
                        return "13.x - Lockbox Rules"
                    elif first_rule.startswith('14.'):
                        return "14.x - Information Rules"
                    else:
                        return "Other Rules"
                
                df_analysis['RuleCategory'] = df_analysis['RuleNumber'].apply(categorize_rule)
                rule_counts = df_analysis['RuleCategory'].value_counts()
                top_category = rule_counts.index[0]
                category_count = rule_counts.iloc[0]
                total_cases = len(df_analysis)
                
                insights.append(
                    html.Div([
                        html.Span("⚖️ ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Problematic Rule Category**: {top_category} ({category_count:,} cases, {category_count/total_cases*100:.1f}% of violations)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Rule category distribution
                unique_categories = len(rule_counts)
                insights.append(
                    html.Div([
                        html.Span("📋 ", style={'fontSize': '16px'}),
                        html.Span(f"**Rule Category Spread**: {unique_categories} different rule categories affected", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Specific rule insights
                if "7.x - Listing Rules" in rule_counts.index:
                    listing_pct = rule_counts["7.x - Listing Rules"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🏠 ", style={'fontSize': '16px'}),
                            html.Span(f"**Listing Compliance**: {listing_pct:.1f}% of violations involve listing rule issues", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                elif "12.x - MLS Usage Rules" in rule_counts.index:
                    mls_pct = rule_counts["12.x - MLS Usage Rules"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🗂️ ", style={'fontSize': '16px'}),
                            html.Span(f"**MLS Compliance**: {mls_pct:.1f}% of violations involve MLS usage issues", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                elif "11.x - Media Rules" in rule_counts.index:
                    media_pct = rule_counts["11.x - Media Rules"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("📸 ", style={'fontSize': '16px'}),
                            html.Span(f"**Media Compliance**: {media_pct:.1f}% of violations involve media rule issues", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                else:
                    insights.append(
                        html.Div([
                            html.Span("📊 ", style={'fontSize': '16px'}),
                            html.Span(f"**Category Analysis**: Showing {period} trends for {unique_categories} rule categories", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
            
            elif metric == "violation_volume":
                # Volume insights
                monthly_avg = len(df_analysis) / 24  # 2 years = 24 months
                recent_month = len(df_analysis[df_analysis['CreatedOn'] >= pd.Timestamp.now() - pd.Timedelta(days=30)])
                
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Volume Overview**: Average monthly violations: {monthly_avg:.1f} cases over 2-year period", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Current volume vs average
                if recent_month > monthly_avg * 1.2:
                    insights.append(
                        html.Div([
                            html.Span("🚨 ", style={'fontSize': '16px'}),
                            html.Span(f"**High Volume Alert**: Current month ({recent_month} cases) is {((recent_month/monthly_avg-1)*100):+.1f}% above average", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                elif recent_month < monthly_avg * 0.8:
                    insights.append(
                        html.Div([
                            html.Span("✅ ", style={'fontSize': '16px'}),
                            html.Span(f"**Low Volume Period**: Current month ({recent_month} cases) is {((1-recent_month/monthly_avg)*100):.1f}% below average", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                else:
                    insights.append(
                        html.Div([
                            html.Span("📈 ", style={'fontSize': '16px'}),
                            html.Span(f"**Normal Volume**: Current month ({recent_month} cases) is within normal range of average", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                # Peak activity analysis
                daily_counts = df_analysis.groupby(df_analysis['CreatedOn'].dt.date).size()
                if not daily_counts.empty:
                    max_day_count = daily_counts.max()
                    max_day_date = daily_counts.idxmax()
                    insights.append(
                        html.Div([
                            html.Span("🏆 ", style={'fontSize': '16px'}),
                            html.Span(f"**Peak Activity**: Highest single-day volume was {max_day_count} cases on {max_day_date}", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
            
            elif metric == "severity_trends":
                # Severity analysis
                df_classified = classify_case_severity(df_analysis)
                if 'FinalSeverity' in df_classified.columns:
                    severity_counts = df_classified['FinalSeverity'].value_counts()
                    total_cases = len(df_classified)
                    
                    # Critical cases insight
                    critical_count = severity_counts.get('CRITICAL', 0)
                    if critical_count > 0:
                        insights.append(
                            html.Div([
                                html.Span("🚨 ", style={'fontSize': '16px'}),
                                html.Span(f"**Critical Cases**: {critical_count:,} cases ({critical_count/total_cases*100:.1f}%) require immediate attention", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                    else:
                        insights.append(
                            html.Div([
                                html.Span("✅ ", style={'fontSize': '16px'}),
                                html.Span("**No Critical Issues**: No critical severity cases detected in current period", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                    
                    # High priority insight
                    high_count = severity_counts.get('HIGH', 0)
                    if high_count > 0:
                        insights.append(
                            html.Div([
                                html.Span("⚠️ ", style={'fontSize': '16px'}),
                                html.Span(f"**High Priority**: {high_count:,} cases ({high_count/total_cases*100:.1f}%) need urgent review", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                    else:
                        insights.append(
                            html.Div([
                                html.Span("🟡 ", style={'fontSize': '16px'}),
                                html.Span("**Manageable Load**: No high-priority cases in current severity analysis", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                    
                    # Overall severity distribution
                    medium_low_count = severity_counts.get('MEDIUM', 0) + severity_counts.get('LOW', 0)
                    if medium_low_count > 0:
                        insights.append(
                            html.Div([
                                html.Span("📊 ", style={'fontSize': '16px'}),
                                html.Span(f"**Standard Cases**: {medium_low_count:,} cases ({medium_low_count/total_cases*100:.1f}%) are medium/low severity", style={'fontSize': '13px'})
                            ], className="mb-2")
                        )
                else:
                    insights.append(
                        html.Div([
                            html.Span("🔧 ", style={'fontSize': '16px'}),
                            html.Span("**Classification Issue**: Unable to classify case severity at this time", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                    
                    insights.append(
                        html.Div([
                            html.Span("📋 ", style={'fontSize': '16px'}),
                            html.Span(f"**Case Count**: Analyzing {len(df_analysis):,} cases for severity trends", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                    
                    insights.append(
                        html.Div([
                            html.Span("📈 ", style={'fontSize': '16px'}),
                            html.Span(f"**Period Analysis**: Showing {period} severity distribution patterns", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
        except Exception as e:
            print(f"Error generating violation trends insights: {e}")
            insights = [
                html.Div([
                    html.Span("🔄 ", style={'fontSize': '16px'}),
                    html.Span("**Processing**: Trend analysis is being processed...", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span(f"**Dataset**: Analyzing {len(filtered_df):,} violation cases", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📅 ", style={'fontSize': '16px'}),
                    html.Span(f"**Timeframe**: Showing {period} violation trends", style={'fontSize': '13px'})
                ], className="mb-2")
            ]
        
        if len(insights) == 0:
            insights = [
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span(f"**Analysis Ready**: Showing {period} violation trends for {metric.replace('_', ' ')}", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📈 ", style={'fontSize': '16px'}),
                    html.Span(f"**Data Coverage**: {len(filtered_df):,} cases included in trend analysis", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("🎯 ", style={'fontSize': '16px'}),
                    html.Span("**Interactive Chart**: Click chart elements for detailed breakdown", style={'fontSize': '13px'})
                ], className="mb-2")
            ]
        elif len(insights) < 3:
            while len(insights) < 3:
                if len(insights) == 1:
                    insights.append(
                        html.Div([
                            html.Span("📅 ", style={'fontSize': '16px'}),
                            html.Span(f"**Time Period**: Analysis covers {period} trends in violation patterns", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                elif len(insights) == 2:
                    insights.append(
                        html.Div([
                            html.Span("🔍 ", style={'fontSize': '16px'}),
                            html.Span(f"**Metric Focus**: Current view shows {metric.replace('_', ' ')} analysis", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
        
        return html.Div(insights, className="insights-container")
   
    # Main callback for updating chart and insights
    @callback(
        [Output("compliance-violation-trends-chart", "figure"),
         Output("compliance-violation-trends-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-trends-period-dropdown", "value"),
         Input("compliance-trends-metric-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Violation Trends Chart Update")
    def update_violation_trends_chart(filter_selections, period, metric):
        """Update violation trends chart and insights"""
        
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
            chart_figure = create_violation_trends_chart(filtered_df, period or "monthly", metric or "violation_types")
            insights_content = generate_violation_trends_insights(filtered_df, period or "monthly", metric or "violation_types")
            
            return chart_figure, insights_content
            
        except Exception as e:
            print(f"Error updating violation trends: {e}")
            return {}, html.Div(f"Error: {str(e)}", className="text-danger")

    # Chart modal callback for enlarged view
    # @callback(
    #     [
    #         Output("compliance-chart-modal", "is_open", allow_duplicate=True),
    #         Output("compliance-modal-chart-content", "children", allow_duplicate=True)
    #     ],
    #     [
    #         Input("compliance-violation-trends-chart", "clickData") 
    #     ],
    #     [
    #         State("compliance-violation-trends-chart", "figure"),  
    #         State("compliance-chart-modal", "is_open")
    #     ],
    #     prevent_initial_call=True
    # )
    # def toggle_violation_trends_chart_modal(click_data, chart_figure, is_open_state):
    #     """Toggle enlarged violation trends chart modal on chart click"""
        
    #     if click_data and not is_open_state and chart_figure:
    #         enlarged_chart = create_enlarged_violation_trends_chart(chart_figure)
    #         return True, dcc.Graph(
    #             figure=enlarged_chart,
    #             config={
    #                 'displayModeBar': True,
    #                 'displaylogo': False,
    #                 'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 
    #                                        'drawcircle', 'drawrect', 'eraseshape'],
    #                 'toImageButtonOptions': {
    #                     'format': 'png',
    #                     'filename': 'violation_trends_chart',
    #                     'height': 600,
    #                     'width': 1000,
    #                     'scale': 2
    #                 }
    #             }
    #         )
        
    #     return no_update, no_update
    @callback(
        [
            Output("compliance-chart-modal", "is_open", allow_duplicate=True),
            Output("compliance-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("compliance-violation-trends-chart-wrapper", "n_clicks")  # Changed to wrapper
        ],
        [
            State("compliance-violation-trends-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_violation_trends_chart_modal(wrapper_clicks, chart_figure, is_open_state):
        """Toggle enlarged violation trends chart modal on chart wrapper click"""
        
        if wrapper_clicks and not is_open_state and chart_figure:
            enlarged_chart = create_enlarged_violation_trends_chart(chart_figure)
            return True, dcc.Graph(
                figure=enlarged_chart,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 
                                           'drawcircle', 'drawrect', 'eraseshape'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'violation_trends_chart',
                        'height': 600,
                        'width': 1000,
                        'scale': 2
                    }
                }
            )
        
        return no_update, no_update    
    
    # print("✅ Compliance violation trends callbacks registered")