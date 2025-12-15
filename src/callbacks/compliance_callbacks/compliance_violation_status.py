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
        
        if view_state == "disposition":
            # Group by Disposition (case status)
            status_counts = df['Disposition'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "violation":
            # Group by first ViolationName in list
            def get_first_violation(violation_list):
                if isinstance(violation_list, list) and len(violation_list) > 0:
                    return violation_list[0] if violation_list[0] is not None else "No Violation"
                return "No Violation"
            
            df['FirstViolation'] = df['ViolationName'].apply(get_first_violation)
            status_counts = df['FirstViolation'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "violation_grouped":
            # Group violations into logical categories
            def categorize_violation(violation_list):
                if isinstance(violation_list, list) and len(violation_list) > 0:
                    violation = violation_list[0] if violation_list[0] is not None else "No Violation"
                else:
                    violation = "No Violation"
                
                # Logical groupings based on your analysis
                if violation in ['Citation', 'Combined Citation', 'Citation: Unresolved']:
                    return 'Active Citations'
                elif violation in ['Citation - Dismissed by review panel', 'Corrected', 'Corrected Prior to Review']:
                    return 'Citation Outcomes'
                elif violation in ['Disciplinary Complaint', 'Disciplinary Complaint Dismissed', 'Disciplinary Complaint Upheld']:
                    return 'Disciplinary Actions'
                elif violation in ['Investigation Created', 'Escalated', 'Warning']:
                    return 'Investigations'
                elif violation in ['Call', 'Chat', 'Left Voicemail']:
                    return 'Communication'
                elif violation in ['AOR/MLS Referral', 'Transferred to OM/DB', 'Modification', 'Violation Override']:
                    return 'Administrative'
                elif violation in ['No Violation', 'Unable to Verify', 'Duplicate', 'Aged Report', 'Withdrawn']:
                    return 'Resolution/Closure'
                elif violation in ['Null', None, '']:
                    return 'Data Issues'
                else:
                    return 'Other'
            
            df['ViolationCategory'] = df['ViolationName'].apply(categorize_violation)
            status_counts = df['ViolationCategory'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "rules":
            # Group by first RuleNumber in list
            def get_first_rule(rule_list):
                if isinstance(rule_list, list) and len(rule_list) > 0:
                    return rule_list[0] if rule_list[0] is not None else "No Rule"
                return "No Rule"
            
            df['FirstRule'] = df['RuleNumber'].apply(get_first_rule)
            status_counts = df['FirstRule'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "citation_fees":
            # Group by first CitationFee (no bucketization as requested)
            def get_first_fee(fee_list):
                if isinstance(fee_list, list) and len(fee_list) > 0:
                    fee = fee_list[0] if fee_list[0] is not None else "No Fee"
                    # Format fee values for display
                    if str(fee).replace('.', '').replace('0', '').strip():
                        return f"${fee}" if not str(fee).startswith('$') else fee
                    else:
                        return "No Fee"
                return "No Fee"
            
            df['FirstFee'] = df['CitationFee'].apply(get_first_fee)
            status_counts = df['FirstFee'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
        elif view_state == "report_count":
            def get_report_count_label(count):
                if pd.isna(count) or count == 0:
                    return "No Reports"
                elif count >= 10:
                    return "10+ Reports"
                else:
                    return f"{int(count)} Report{'s' if count != 1 else ''}"
            
            df['ReportCountLabel'] = df['NumReportIds'].apply(get_report_count_label)
            status_counts = df['ReportCountLabel'].value_counts().reset_index()
            status_counts.columns = ['Category', 'Count']
            
            # Sort by actual report count for logical ordering
            def extract_report_number(label):
                if label == "No Reports":
                    return '00'
                else:
                    return str(int(label.split(' ')[0].replace('+', ''))).zfill(2)
            
            status_counts['SortKey'] = status_counts['Category'].apply(extract_report_number)
            status_counts = status_counts.sort_values('SortKey').drop('SortKey', axis=1).reset_index(drop=True)            
        
        # Calculate summary stats
        summary_stats = {
            'total_cases': len(df),
            'open_cases': len(df[df['Disposition'] != 'Closed']) if 'Disposition' in df.columns else 0,
            'closed_cases': len(df[df['Disposition'] == 'Closed']) if 'Disposition' in df.columns else 0,
            'unique_categories': len(status_counts)
        }
        
        # Sort by count descending
        status_counts = status_counts.sort_values('Count', ascending=False).reset_index(drop=True)
        
        return status_counts, summary_stats
    
    @monitor_chart_performance("Violation Status Chart")
    def create_violation_status_chart(status_counts, summary_stats, view_state):
        """Create violation status chart based on view state"""
        
        if status_counts.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No violation data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': f"Violation Analysis - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        # Color schemes based on view
        if view_state == "disposition":
            color_map = {
                'Open': '#e74c3c', 'Closed': '#27ae60', 'In Progress': '#f39c12', 
                'On Hold': '#95a5a6', 'Pending': '#3498db'
            }
            colors = [color_map.get(cat, '#7f8c8d') for cat in status_counts['Category']]
        elif view_state == "violation_grouped":
            color_map = {
                'Active Citations': '#e74c3c',      # Red - urgent
                'Citation Outcomes': '#f39c12',     # Orange - outcomes
                'Disciplinary Actions': '#8e44ad',  # Purple - serious
                'Investigations': '#3498db',        # Blue - active work
                'Communication': '#2ecc71',         # Green - routine
                'Administrative': '#95a5a6',        # Gray - procedural
                'Resolution/Closure': '#27ae60',    # Dark green - resolved
                'Data Issues': '#e67e22'            # Dark orange - needs attention
            }
            colors = [color_map.get(cat, '#7f8c8d') for cat in status_counts['Category']]
        elif view_state == "report_count":
            color_map = {
                'No Reports': '#95a5a6',      # Gray - no activity
                '1 Report': '#3498db',        # Blue - single report
                '2 Reports': '#2ecc71',       # Green 
                '3 Reports': '#f39c12',       # Orange
                '4 Reports': '#e67e22',       # Dark orange
                '5 Reports': '#e74c3c',       # Red
                '6 Reports': '#8e44ad',       # Purple
                '7 Reports': '#c0392b',       # Dark red
                '8 Reports': '#7f8c8d',       # Dark gray
                '9 Reports': '#d35400',       # Dark orange
                '10+ Reports': '#2c3e50'       # Very dark blue
            }
            colors = [color_map.get(cat, '#34495e') for cat in status_counts['Category']]            
        else:
            # Use qualitative color palette for other views
            colors = px.colors.qualitative.Set3[:len(status_counts)]
        
        # Create donut chart
        fig = go.Figure(data=[go.Pie(
            labels=status_counts['Category'],
            values=status_counts['Count'],
            hole=0.4,
            textinfo='percent',
            textposition='inside',
            marker=dict(colors=colors, line=dict(color='white', width=2)),
            hovertemplate="<b>%{label}</b><br>Cases: %{value}<br>Percent: %{percent}<extra></extra>",
            sort=False  # Keep our sorted order
        )])
        
        # Add center text
        center_text = f"<b>{summary_stats['total_cases']:,}</b><br>Total Cases<br><span style='font-size:12px'>{summary_stats['unique_categories']} Categories</span>"
        fig.add_annotation(
            text=center_text,
            x=0.5, y=0.5,
            font_size=14,
            showarrow=False
        )
        
        # Chart titles
        view_titles = {
            'disposition': 'Cases by Disposition',
            'violation': 'Cases by Violation Type',
            'violation_grouped': 'Cases by Violation Category',
            'rules': 'Cases by Rule Number',
            'citation_fees': 'Cases by Citation Fee',
            'report_count': 'Cases by Report Count'
        }
        
        fig.update_layout(
            title={
                'text': f"{view_titles.get(view_state, 'Violation Analysis')} ({summary_stats['total_cases']:,} Total Cases)", 
                'x': 0.5, 
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            height=400,
            margin={'l': 50, 'r': 50, 't': 80, 'b': 50},
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False  # Disable legend for cleaner look
        )
        
        return fig
    
    @monitor_chart_performance("Enlarged Violation Status Chart")
    def create_enlarged_violation_status_chart(original_figure):
        """
        Create an enlarged version of the violation status chart for modal display
        Following the exact workflow pattern
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
                        'filename': 'compliance_violation_status_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
        except Exception as e:
            return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")
            
    def create_violation_details_table(status_counts, view_state, df):
        """Create detailed breakdown table for modal display"""
        if status_counts.empty:
            return html.Div("No violation data available", className="text-center text-muted p-4")
        
        try:
            # Enhanced data for table
            table_data = status_counts.copy()
            
            # Add percentage calculation
            total_cases = table_data['Count'].sum()
            table_data['Percentage'] = (table_data['Count'] / total_cases * 100).round(1)
            
            # Add additional metrics based on view
            if view_state == "violation" and not df.empty:
                # Add case details for individual violations
                violation_details = []
                for _, row in table_data.iterrows():
                    violation = row['Category']
                    # Get cases with this violation as first violation
                    df_temp = df.copy()
                    df_temp['FirstViolation'] = df_temp['ViolationName'].apply(
                        lambda x: x[0] if isinstance(x, list) and len(x) > 0 and x[0] is not None else "No Violation"
                    )
                    matching_cases = df_temp[df_temp['FirstViolation'] == violation]
                    
                    # Calculate metrics
                    open_count = len(matching_cases[matching_cases['Disposition'] != 'Closed'])
                    avg_reports = matching_cases['NumReportIds'].mean() if 'NumReportIds' in matching_cases.columns else 0
                    
                    violation_details.append({
                        'OpenCases': open_count,
                        'AvgReports': avg_reports
                    })
                
                details_df = pd.DataFrame(violation_details)
                for col in details_df.columns:
                    table_data[col] = details_df[col].values
            
            # Create table rows with enhanced styling
            table_rows = []
            for i, row in table_data.iterrows():
                # Determine row styling
                row_class = "table-warning" if i < 3 else ""
                
                # Create row cells
                cells = [
                    html.Td([
                        html.Span("🔸", style={'color': '#3498db', 'marginRight': '8px'}),
                        html.Span(row['Category'], style={'fontWeight': 'bold' if i < 5 else 'normal'})
                    ]),
                    html.Td(f"{row['Count']:,}", className="text-end fw-bold"),
                    html.Td(f"{row['Percentage']:.1f}%", className="text-end")
                ]
                
                # Add view-specific columns
                if 'OpenCases' in row:
                    cells.append(html.Td(f"{row['OpenCases']:,}", className="text-end"))
                if 'AvgReports' in row:
                    cells.append(html.Td(f"{row['AvgReports']:.1f}", className="text-end"))
                
                table_rows.append(html.Tr(cells, className=row_class))
            
            # Create headers
            headers = [
                html.Th("Category", style={'width': '40%'}),
                html.Th("Cases", className="text-end", style={'width': '20%'}),
                html.Th("Percentage", className="text-end", style={'width': '15%'})
            ]
            
            if 'OpenCases' in table_data.columns:
                headers.append(html.Th("Open Cases", className="text-end", style={'width': '15%'}))
            if 'AvgReports' in table_data.columns:
                headers.append(html.Th("Avg Reports", className="text-end", style={'width': '10%'}))
            
            # View-specific titles
            view_names = {
                'disposition': 'Disposition',
                'violation': 'Violation Type',
                'violation_grouped': 'Violation Category',
                'rules': 'Rule Number',
                'citation_fees': 'Citation Fee',
                'report_count': 'Report Count'
            }
            
            return html.Div([
                html.H4(f"Complete {view_names.get(view_state, 'Violation')} Breakdown", className="mb-3 text-primary"),
                html.P([
                    html.Span([
                        html.I(className="fas fa-gavel me-2"),
                        f"Total: {total_cases:,} cases across {len(table_data)} categories"
                    ], className="me-4"),
                    html.Span([
                        html.I(className="fas fa-chart-pie me-2"),
                        f"Top 3 categories account for {table_data.head(3)['Percentage'].sum():.1f}% of cases"
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
            print(f"❌ Error creating violation details table: {e}")
            return html.Div([
                html.H4("Error Creating Breakdown", className="text-danger mb-3"),
                html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
            ], className="text-center p-4")
    
    @monitor_performance("Violation Status Insights Generation")
    def generate_violation_status_insights(status_counts, summary_stats, view_state, df):
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
        
        # View-specific insights
        if view_state == "disposition":
            if summary_stats['open_cases'] > 0:
                open_pct = (summary_stats['open_cases'] / summary_stats['total_cases']) * 100
                insights.append(
                    html.Div([
                        html.Span("🔴 ", style={'fontSize': '16px'}),
                        html.Span(f"**Open Cases**: {summary_stats['open_cases']:,} ({open_pct:.1f}%) require attention", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
        elif view_state == "violation_grouped":
            # Focus on high-severity categories
            high_severity = status_counts[status_counts['Category'].isin(['Active Citations', 'Disciplinary Actions'])]
            if not high_severity.empty:
                severity_count = high_severity['Count'].sum()
                severity_pct = (severity_count / summary_stats['total_cases']) * 100
                insights.append(
                    html.Div([
                        html.Span("⚠️ ", style={'fontSize': '16px'}),
                        html.Span(f"**High Severity**: {severity_count:,} cases ({severity_pct:.1f}%) involve citations or disciplinary actions", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
        
        elif view_state == "report_count" and not df.empty:
            # Complex cases insight
            complex_cases = len(df[df['NumReportIds'] >= 4]) if 'NumReportIds' in df.columns else 0
            if complex_cases > 0:
                complex_pct = (complex_cases / summary_stats['total_cases']) * 100
                insights.append(
                    html.Div([
                        html.Span("🔍 ", style={'fontSize': '16px'}),
                        html.Span(f"**Complex Cases**: {complex_cases:,} cases ({complex_pct:.1f}%) have 4+ associated reports", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
        
        # Top category insight
        top_category = status_counts.iloc[0] if len(status_counts) > 0 else None
        if top_category is not None:
            top_pct = (top_category['Count'] / summary_stats['total_cases']) * 100
            insights.append(
                html.Div([
                    html.Span("🎯 ", style={'fontSize': '16px'}),
                    html.Span(f"**Most Common**: {top_category['Category']} accounts for {top_category['Count']:,} cases ({top_pct:.1f}%)", style={'fontSize': '13px'})
                ], className="mb-2")
            )
        
        return html.Div(insights, className="insights-container")
    
    # View state toggle callbacks
    @callback(
        [Output("compliance-violation-status-view-state", "data"),
         Output("violation-disposition-view-btn", "active"),
         Output("violation-types-view-btn", "active"),
         Output("violation-categories-view-btn", "active"),
         Output("violation-rules-view-btn", "active"),
         Output("violation-fees-view-btn", "active"),
         Output("violation-reports-view-btn", "active")],
        [Input("violation-disposition-view-btn", "n_clicks"),
         Input("violation-types-view-btn", "n_clicks"),
         Input("violation-categories-view-btn", "n_clicks"),
         Input("violation-rules-view-btn", "n_clicks"),
         Input("violation-fees-view-btn", "n_clicks"),
         Input("violation-reports-view-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def toggle_violation_status_view(disp_clicks, types_clicks, cats_clicks, rules_clicks, fees_clicks, reports_clicks):
        """Toggle between different violation analysis views"""
        triggered = ctx.triggered
        if not triggered:
            return "disposition", True, False, False, False, False, False
            
        triggered_id = triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "violation-disposition-view-btn":
            return "disposition", True, False, False, False, False, False
        elif triggered_id == "violation-types-view-btn":
            return "violation", False, True, False, False, False, False
        elif triggered_id == "violation-categories-view-btn":
            return "violation_grouped", False, False, True, False, False, False
        elif triggered_id == "violation-rules-view-btn":
            return "rules", False, False, False, True, False, False
        elif triggered_id == "violation-fees-view-btn":
            return "citation_fees", False, False, False, False, True, False
        elif triggered_id == "violation-reports-view-btn":
            return "report_count", False, False, False, False, False, True
        
        return "disposition", True, False, False, False, False, False
    
    # Details modal callback
    @callback(
        [Output("compliance-violation-details-modal", "is_open"),
         Output("compliance-violation-details-content", "children")],
        [Input("compliance-violation-details-btn", "n_clicks")],
        [State("compliance-violation-details-modal", "is_open"),
         State("compliance-filtered-query-store", "data"),
         State("compliance-violation-status-view-state", "data")],
        prevent_initial_call=True
    )
    @monitor_performance("Violation Details Modal Toggle")
    def toggle_violation_details_modal(details_btn_clicks, is_open, filter_selections, view_state):
        """Handle opening of violation details modal with complete breakdown table"""
        if details_btn_clicks:
            if not is_open:
                try:
                    # Get fresh data
                    base_data = get_compliance_base_data()
                    filtered_data = apply_compliance_filters(base_data, filter_selections or {})
                    status_counts, summary_stats = prepare_violation_status_data(filtered_data, view_state)
                    
                    # Create detailed table
                    detailed_table = create_violation_details_table(status_counts, view_state, filtered_data)
                    
                    return True, detailed_table
                    
                except Exception as e:
                    print(f"❌ Error generating violation details: {e}")
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
                    text="No violation data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
                fig.update_layout(
                    title={'text': "Violation Analysis - No Data", 'x': 0.5, 'xanchor': 'center'},
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
            insights = generate_violation_status_insights(status_counts, summary_stats, view_state, filtered_data)
            
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating violation status chart: {e}")
            import traceback
            traceback.print_exc()
            
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading violation data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={'text': "Violation Analysis - Error", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to load violation data", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
    
    @callback(
        [
            Output("compliance-chart-modal", "is_open", allow_duplicate=True),
            Output("compliance-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("compliance-violation-status-chart-wrapper", "n_clicks"),
            Input("compliance-chart-modal", "is_open")
        ],
        [
            State("compliance-violation-status-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_violation_status_chart_modal(wrapper_clicks, modal_is_open, chart_figure, is_open_state):
        """Toggle enlarged violation status chart modal - exact workflow pattern"""
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        if triggered_id == "compliance-violation-status-chart-wrapper" and wrapper_clicks and not is_open_state:
            enlarged_chart = create_enlarged_violation_status_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
        
    @callback(
        Output("compliance-violation-details-modal", "is_open", allow_duplicate=True),
        [Input("compliance-violation-details-close-btn", "n_clicks")],
        [State("compliance-violation-details-modal", "is_open")],
        prevent_initial_call=True
    )
    def close_violation_details_modal(close_clicks, is_open):
        """Close the violation details modal when close button is clicked"""
        if close_clicks and is_open:
            # print("📊 Closing violation details modal via close button")
            return False
        return no_update

    # print("✅ Compliance violation status callbacks registered")