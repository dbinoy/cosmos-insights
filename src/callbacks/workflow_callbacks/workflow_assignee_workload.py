from dash import callback, Input, Output, State, ctx, html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance
from inflection import titleize

def register_workflow_assignee_workload_callbacks(app):
    
    @monitor_query_performance("Assignee Workload Base Data")
    def get_assignee_workload_base_data():
        """
        Get base data for assignee workload analysis
        Uses Fact_WorkFlowItems to get current assignments and workload distribution
        """
        queries = {
            "work_items": """
                SELECT 
                    w.WorkItemId,
                    w.CreatedOn,
                    w.ClosedOn,
                    w.EscalatedOn,
                    w.WorkItemDefinitionShortCode,
                    w.WorkItemStatus,
                    w.IsEscalated,
                    w.AssignedTo,
                    w.AorShortName,
                    w.CaseOrigin,
                    w.Priority,
                    w.Product,
                    w.Module,
                    w.Feature,
                    w.Issue
                FROM [consumable].[Fact_WorkFlowItems] w
                WHERE w.AssignedTo IS NOT NULL AND w.AssignedTo != ''
            """,
            
            "case_types": """
                SELECT DISTINCT 
                    CaseTypeCode,
                    CaseTypeName
                FROM [consumable].[Dim_WorkItemAttributes]
                WHERE CaseTypeCode IS NOT NULL
            """,
            
            "users": """
                SELECT DISTINCT
                    Name,
                    UserDetail,
                    UserRole
                FROM [consumable].[Dim_Users]
                WHERE Name IS NOT NULL
            """
        }
        
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("Assignee Workload Filter Application")
    def apply_assignee_workload_filters(work_items, query_selections):
        """
        Filter assignee workload DataFrame based on all supported fields.
        Uses the same extraction logic as apply_workflow_data_table_filters.
        """
        df = pd.DataFrame(work_items)
        if df.empty:
            return df

        # Extract filter values (same logic as apply_workflow_data_table_filters)
        selected_aor = [item.strip("'") for item in query_selections.get('AOR', '').split(', ') if item.strip("'")]
        selected_case_types = [item.strip("'") for item in query_selections.get('CaseTypes', '').split(', ') if item.strip("'")]
        selected_status = [item.strip("'") for item in query_selections.get('Status', '').split(', ') if item.strip("'")]
        selected_priority = [item.strip("'") for item in query_selections.get('Priority', '').split(', ') if item.strip("'")]
        selected_origins = [item.strip("'") for item in query_selections.get('Origins', '').split(', ') if item.strip("'")]
        selected_reasons = [item.strip("'") for item in query_selections.get('Reasons', '').split(', ') if item.strip("'")]
        selected_products = [item.strip("'") for item in query_selections.get('Products', '').split(', ') if item.strip("'")]
        selected_features = [item.strip("'") for item in query_selections.get('Features', '').split(', ') if item.strip("'")]
        selected_modules = [item.strip("'") for item in query_selections.get('Modules', '').split(', ') if item.strip("'")]
        selected_issues = [item.strip("'") for item in query_selections.get('Issues', '').split(', ') if item.strip("'")]
        start_date = query_selections.get('Day_From')
        end_date = query_selections.get('Day_To')

        # Date filter
        if 'CreatedOn' in df.columns:
            df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
            df = df.dropna(subset=['CreatedOn']).copy()
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    df = df.loc[(df['CreatedOn'] >= start_dt) & (df['CreatedOn'] <= end_dt)].copy()
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")

        # Apply other filters
        if selected_aor and "All" not in selected_aor and 'AorShortName' in df.columns:
            df = df[df['AorShortName'].isin(selected_aor)].copy()
        if selected_case_types and "All" not in selected_case_types and 'WorkItemDefinitionShortCode' in df.columns:
            df = df[df['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
        if selected_status and "All" not in selected_status and 'WorkItemStatus' in df.columns:
            df = df[df['WorkItemStatus'].isin(selected_status)].copy()
        if selected_priority and "All" not in selected_priority and 'Priority' in df.columns:
            df = df[df['Priority'].isin(selected_priority)].copy()
        if selected_origins and "All" not in selected_origins and 'CaseOrigin' in df.columns:
            df = df[df['CaseOrigin'].isin(selected_origins)].copy()
        if selected_reasons and "All" not in selected_reasons and 'CaseReason' in df.columns:
            df = df[df['CaseReason'].isin(selected_reasons)].copy()
        if selected_products and "All" not in selected_products and 'Product' in df.columns:
            df = df[df['Product'].isin(selected_products)].copy()
        if selected_features and "All" not in selected_features and 'Feature' in df.columns:
            df = df[df['Feature'].isin(selected_features)].copy()
        if selected_modules and "All" not in selected_modules and 'Module' in df.columns:
            df = df[df['Module'].isin(selected_modules)].copy()
        if selected_issues and "All" not in selected_issues and 'Issue' in df.columns:
            df = df[df['Issue'].isin(selected_issues)].copy()

        return df

    @monitor_performance("Assignee Workload Data Preparation")
    def prepare_assignee_workload_data(filtered_data, top_count=10):
        """
        Prepare assignee workload analysis data
        Creates workload distribution with 3 status buckets: Closed, Active, Non-Actionable
        UPDATED: Enhanced to handle 'all' option for displaying all assignees
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        
        try:
            df = filtered_data.copy()
            
            # Clean and format assignee names
            def format_assignee_name(assignee):
                if pd.isna(assignee) or assignee == '' or assignee.lower() == 'unassigned':
                    return 'Unassigned'
                # Clean up assignee names - remove domain info, format properly
                cleaned = str(assignee).split('@')[0].replace('.', ' ').replace('_', ' ').replace('\r', ' ').replace('\n', ' ')
                return titleize(cleaned)
            
            df['AssigneeDisplay'] = df['AssignedTo'].apply(format_assignee_name)
            
            # UPDATED: Categorize WorkItemStatus into 3 meaningful buckets
            def categorize_status(status):
                if pd.isna(status):
                    return 'Non-Actionable'
                
                status = str(status).strip()
                
                # CLOSED: Tickets that are completed/resolved
                closed_statuses = {
                    'Closed', 'First Call Closed', 'Self-Fix', 'Resolved', 
                    'Escalation Resolved', 'Done', 'Canceled', 'Escalation Canceled'
                }
                
                # ACTIVE: Tickets that require action/work
                active_statuses = {
                    'Not Started', 'In Progress', 'Open', 'Scheduled', 
                    'Escalated', 'Pending', 'Pending Verification', 'Existing Escalation'
                }
                
                # NON-ACTIONABLE: Tickets that are blocked/suspended/insufficient
                non_actionable_statuses = {
                    'On Hold', 'Insufficient Details'
                }
                
                if status in closed_statuses:
                    return 'Closed'
                elif status in active_statuses:
                    return 'Active'
                elif status in non_actionable_statuses:
                    return 'Non-Actionable'
                else:
                    # Unknown status - default to Active for safety
                    return 'Active'
            
            # Apply status categorization
            df['StatusCategory'] = df['WorkItemStatus'].apply(categorize_status)
            
            # UPDATED: Convert date columns for escalation analysis
            df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
            df['EscalatedOn'] = pd.to_datetime(df['EscalatedOn'], errors='coerce')
            
            # Enhanced escalation check
            def is_escalated_ticket(row):
                # Check both IsEscalated flag and status
                is_flag_escalated = str(row['IsEscalated']).strip() in ['1', 'True', 'true']
                is_status_escalated = str(row['WorkItemStatus']).strip() in ['Escalated', 'Existing Escalation', 'Escalation Resolved', 'Escalation Canceled']
                return is_flag_escalated or is_status_escalated
            
            df['IsActuallyEscalated'] = df.apply(is_escalated_ticket, axis=1)
            
            # UPDATED: Calculate comprehensive workload metrics per assignee
            assignee_metrics = df.groupby('AssigneeDisplay').agg({
                'WorkItemId': 'count',  # Total tickets
                'IsActuallyEscalated': lambda x: x.sum(),  # Escalated tickets
                'StatusCategory': lambda x: (x == 'Closed').sum(),  # Closed tickets
                'CreatedOn': ['min', 'max'],  # Date range for activity
                'Priority': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Unknown'  # Most common priority
            })
            
            # Add status category counts
            status_counts = df.groupby(['AssigneeDisplay', 'StatusCategory']).size().unstack(fill_value=0)
            
            # Ensure all status categories exist (even if 0)
            for status_cat in ['Closed', 'Active', 'Non-Actionable']:
                if status_cat not in status_counts.columns:
                    status_counts[status_cat] = 0
            
            # Flatten main metrics column names
            assignee_metrics.columns = [
                'total_tickets', 'escalated_tickets', 'closed_tickets_alt', 
                'first_ticket_date', 'last_ticket_date', 'common_priority'
            ]
            
            # UPDATED: Merge with status category counts
            assignee_metrics = assignee_metrics.merge(status_counts, left_index=True, right_index=True, how='left')
            
            # Fill any missing status counts with 0
            assignee_metrics['Closed'] = assignee_metrics['Closed'].fillna(0).astype(int)
            assignee_metrics['Active'] = assignee_metrics['Active'].fillna(0).astype(int)
            assignee_metrics['Non-Actionable'] = assignee_metrics['Non-Actionable'].fillna(0).astype(int)
            
            # Calculate performance metrics
            assignee_metrics['escalation_rate'] = (
                assignee_metrics['escalated_tickets'] / assignee_metrics['total_tickets'] * 100
            ).round(1)
            
            assignee_metrics['closure_rate'] = (
                assignee_metrics['Closed'] / assignee_metrics['total_tickets'] * 100
            ).round(1)
            
            assignee_metrics['active_rate'] = (
                assignee_metrics['Active'] / assignee_metrics['total_tickets'] * 100
            ).round(1)
            
            # UPDATED: Sort by total tickets and handle 'all' vs top N
            assignee_metrics = assignee_metrics.sort_values('total_tickets', ascending=False)
            
            # Apply top count filter (if not 'all')
            if top_count != 'all' and isinstance(top_count, int):
                assignee_metrics = assignee_metrics.head(top_count)
            # If top_count is 'all', we keep all assignees (no filtering)
            
            # UPDATED: Enhanced summary statistics
            total_closed = df[df['StatusCategory'] == 'Closed'].shape[0]
            total_active = df[df['StatusCategory'] == 'Active'].shape[0]
            total_non_actionable = df[df['StatusCategory'] == 'Non-Actionable'].shape[0]
            
            summary_stats = {
                'total_assignees': len(df['AssigneeDisplay'].unique()),
                'displayed_assignees': len(assignee_metrics),  # ADDED: How many are actually displayed
                'total_tickets': len(df),
                'total_closed_tickets': int(total_closed),
                'total_active_tickets': int(total_active),
                'total_non_actionable_tickets': int(total_non_actionable),
                'avg_tickets_per_assignee': (len(df) / len(df['AssigneeDisplay'].unique())),
                'top_assignee': assignee_metrics.index[0] if len(assignee_metrics) > 0 else 'N/A',
                'top_assignee_count': assignee_metrics['total_tickets'].iloc[0] if len(assignee_metrics) > 0 else 0,
                'unassigned_tickets': len(df[df['AssigneeDisplay'] == 'Unassigned']),
                'escalation_rate_avg': assignee_metrics['escalation_rate'].mean(),
                'closure_rate_avg': assignee_metrics['closure_rate'].mean(),
                'active_rate_avg': assignee_metrics['active_rate'].mean()
            }
            
            # print(f"📊 Prepared assignee workload data: {len(assignee_metrics)} assignees displayed (of {len(df['AssigneeDisplay'].unique())} total), {len(df)} total tickets")
            return assignee_metrics, summary_stats
            
        except Exception as e:
            print(f"❌ Error preparing assignee workload data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), {}

    @monitor_chart_performance("Assignee Workload Chart")
    def create_assignee_workload_chart(workload_data, summary_stats, top_count=10, selected_categories=None):
        """
        Create comprehensive assignee workload visualization
        ENHANCED: Support selective category display for better visibility
        """
        if selected_categories is None:
            selected_categories = ['Closed', 'Active', 'Non-Actionable', 'Total']
        
        if workload_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No assignee workload data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Workload Distribution by Assignee",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            # Sort data by total tickets (descending for better readability)
            workload_data = workload_data.sort_values('total_tickets', ascending=False)
            
            # Smart name truncation based on number of assignees
            num_assignees = len(workload_data)
            if num_assignees > 25:
                assignee_names = [name[:10] + '...' if len(name) > 10 else name for name in workload_data.index]
            elif num_assignees > 15:
                assignee_names = [name[:12] + '...' if len(name) > 12 else name for name in workload_data.index]
            else:
                assignee_names = [name[:15] + '...' if len(name) > 15 else name for name in workload_data.index]

            # Create figure
            fig = go.Figure()
            
            # ENHANCED: Add traces based on selected categories
            traces_added = []
            
            # 1. Closed tickets (Green - bottom layer)
            if 'Closed' in selected_categories:
                fig.add_trace(go.Bar(
                    name='Closed',
                    x=assignee_names,
                    y=workload_data['Closed'],
                    marker=dict(color='#27ae60'),
                    hoverinfo='skip'
                ))
                traces_added.append('Closed')
            
            # 2. Active tickets (Blue - middle/bottom layer depending on what's shown)
            if 'Active' in selected_categories:
                fig.add_trace(go.Bar(
                    name='Active',
                    x=assignee_names,
                    y=workload_data['Active'],
                    marker=dict(color='#3498db'),
                    hoverinfo='skip'
                ))
                traces_added.append('Active')
            
            # 3. Non-Actionable tickets (Orange - top layer)
            if 'Non-Actionable' in selected_categories:
                fig.add_trace(go.Bar(
                    name='Non-Actionable',
                    x=assignee_names,
                    y=workload_data['Non-Actionable'],
                    marker=dict(color='#f39c12'),
                    hoverinfo='skip'
                ))
                traces_added.append('Non-Actionable')
            
            # 4. Total Line (Red line - only if selected)
            if 'Total' in selected_categories:
                fig.add_trace(go.Scatter(
                    name='Total',
                    x=assignee_names,
                    y=workload_data['total_tickets'],
                    mode='markers+lines',
                    marker=dict(
                        color='#e74c3c',
                        size=8,
                        symbol='circle',
                        line=dict(width=2, color='white')
                    ),
                    line=dict(
                        color='#e74c3c',
                        width=3
                    ),
                    hoverinfo='skip'
                ))
                traces_added.append('Total')
            
            # ENHANCED: Calculate appropriate Y-axis range based on selected categories
            if traces_added:
                if 'Total' in selected_categories:
                    # If Total line is shown, use total tickets for range
                    max_value = workload_data['total_tickets'].max()
                else:
                    # Otherwise, use the sum of selected categories
                    selected_cols = [col for col in ['Closed', 'Active', 'Non-Actionable'] if col in selected_categories]
                    if selected_cols:
                        max_value = workload_data[selected_cols].sum(axis=1).max()
                    else:
                        max_value = 10  # Fallback
            else:
                max_value = 10  # Fallback
            
            # ENHANCED: Unified hover with dynamic content based on selected categories
            hover_lines = ["<b>%{x}</b><br>", "─────────────────<br>"]
            
            # Build custom data array for hover
            customdata_arrays = []
            hover_index = 2  # Start after name and separator
            
            if 'Total' in selected_categories or len([col for col in ['Closed', 'Active', 'Non-Actionable'] if col in selected_categories]) > 1:
                hover_lines.append("📊 <b>Total Tickets:</b> %{customdata[0]}<br>")
                customdata_arrays.append(workload_data['total_tickets'])
                hover_index += 1
            
            if 'Closed' in selected_categories:
                hover_lines.append("✅ <b>Closed:</b> %{customdata[" + str(len(customdata_arrays)) + "]} (%{customdata[" + str(len(customdata_arrays)+1) + "]:.1f}%)<br>")
                customdata_arrays.extend([workload_data['Closed'], workload_data['closure_rate']])
            
            if 'Active' in selected_categories:
                hover_lines.append("🔄 <b>Active:</b> %{customdata[" + str(len(customdata_arrays)) + "]} (%{customdata[" + str(len(customdata_arrays)+1) + "]:.1f}%)<br>")
                customdata_arrays.extend([workload_data['Active'], workload_data['active_rate']])
            
            if 'Non-Actionable' in selected_categories:
                hover_lines.append("⏸️ <b>Non-Actionable:</b> %{customdata[" + str(len(customdata_arrays)) + "]}<br>")
                customdata_arrays.append(workload_data['Non-Actionable'])
            
            hover_lines.extend([
                "─────────────────<br>",
                "⚡ <b>Escalated:</b> %{customdata[" + str(len(customdata_arrays)) + "]} (%{customdata[" + str(len(customdata_arrays)+1) + "]:.1f}%)<br>",
                "🎯 <b>Common Priority:</b> %{customdata[" + str(len(customdata_arrays)+2) + "]}<br>",
                "<extra></extra>"
            ])
            
            customdata_arrays.extend([
                workload_data['escalated_tickets'],
                workload_data['escalation_rate'],
                workload_data['common_priority']
            ])
            
            # Add invisible scatter plot for unified hover
            fig.add_trace(go.Scatter(
                x=assignee_names,
                y=workload_data['total_tickets'] if 'Total' in selected_categories else workload_data[['Closed', 'Active', 'Non-Actionable']].sum(axis=1),
                mode='markers',
                marker=dict(color='rgba(0,0,0,0)', size=20),
                showlegend=False,
                hovertemplate=''.join(hover_lines),
                customdata=list(zip(*customdata_arrays))
            ))
            
            # Enhanced title with category information
            total_assignees = summary_stats.get('total_assignees', 0)
            displayed_assignees = summary_stats.get('displayed_assignees', 0)
            
            if top_count == 'all':
                title_base = f"Assignee Workload Analysis (All {displayed_assignees} Assignees)"
            else:
                title_base = f"Assignee Workload Analysis (Top {top_count} of {total_assignees})"
            
            # Add category info to title
            category_labels = {'Closed': '✅', 'Active': '🔄', 'Non-Actionable': '⏸️', 'Total': '📊'}
            shown_categories = [f"{category_labels.get(cat, '')} {cat}" for cat in selected_categories]
            title_text = f"{title_base} | Showing: {', '.join(shown_categories)}"
            
            # Update layout
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 12, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': 'Assignee',
                    'tickangle': -45 if num_assignees > 8 else 0,
                    'tickfont': {'size': 10}
                },
                yaxis={
                    'title': 'Number of Tickets',
                    'showgrid': True,
                    'gridcolor': '#f0f0f0',
                    'range': [0, max_value * 1.1]
                },
                height=450,
                margin={'l': 60, 'r': 50, 't': 120, 'b': 100},  # Extra top margin for longer title
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=10)
                ),
                barmode='stack',
                hovermode='x unified'
            )
            
            # Add annotations only for reasonable number of assignees
            if len(workload_data) > 0 and num_assignees <= 25:
                if 'Total' in selected_categories:
                    annotation_y = workload_data['total_tickets'].iloc[0] + (max_value * 0.05)
                    annotation_text = f"Most Total<br>{workload_data['total_tickets'].iloc[0]}"
                else:
                    # Use the highest visible category stack
                    visible_cols = [col for col in ['Closed', 'Active', 'Non-Actionable'] if col in selected_categories]
                    if visible_cols:
                        stack_height = workload_data[visible_cols].sum(axis=1).iloc[0]
                        annotation_y = stack_height + (max_value * 0.05)
                        annotation_text = f"Most Tickets<br>{int(stack_height)}"
                    else:
                        annotation_y = max_value * 0.1
                        annotation_text = "Top Assignee"
                
                fig.add_annotation(
                    x=assignee_names[0],
                    y=annotation_y,
                    text=annotation_text,
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#e74c3c",
                    bgcolor="#fff",
                    bordercolor="#e74c3c",
                    borderwidth=1,
                    font=dict(size=9),
                    ax=0,
                    ay=-40
                )
            
            # print(f"📊 Created assignee workload chart: {len(workload_data)} assignees, showing categories: {selected_categories}")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating assignee workload chart: {e}")
            import traceback
            traceback.print_exc()
            return create_error_figure("Error creating assignee workload chart")

    @monitor_performance("Assignee Workload Insights Generation")
    def generate_assignee_workload_insights(workload_data, summary_stats, top_count=10, selected_categories=None):
        """
        Generate automated insights from assignee workload analysis
        ENHANCED: Adapt insights based on selected categories
        """
        if workload_data.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No assignee workload data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see workload distribution", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("👥 Data will appear when tickets have assignee information", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        if selected_categories is None:
            selected_categories = ['Closed', 'Active', 'Non-Actionable', 'Total']
        
        try:
            insights = []
            
            # Insight 1: Overall workload distribution (adapt based on selected categories)
            total_assignees = summary_stats.get('total_assignees', 0)
            total_tickets = summary_stats.get('total_tickets', 0)
            avg_tickets = summary_stats.get('avg_tickets_per_assignee', 0)
            top_assignee = summary_stats.get('top_assignee', 'N/A')
            top_count_tickets = summary_stats.get('top_assignee_count', 0)
            
            category_focus = ""
            if len(selected_categories) < 4:
                category_labels = {'Closed': 'closed', 'Active': 'active', 'Non-Actionable': 'non-actionable', 'Total': 'total'}
                shown_cats = [category_labels.get(cat, cat.lower()) for cat in selected_categories if cat != 'Total']
                if shown_cats:
                    category_focus = f" (focusing on {' + '.join(shown_cats)} tickets)"
            
            insights.append(f"📊 Workload Overview{category_focus}: {total_tickets:,} tickets distributed across {total_assignees} assignees (avg: {avg_tickets:.1f} tickets/assignee)")
            
            # Insight 2: Category-specific analysis
            if 'Active' in selected_categories and 'Non-Actionable' in selected_categories and 'Closed' not in selected_categories:
                # Focus on open items
                total_active = summary_stats.get('total_active_tickets', 0)
                total_non_actionable = summary_stats.get('total_non_actionable_tickets', 0)
                open_items = total_active + total_non_actionable
                insights.append(f"🔄 Open Items Analysis: {open_items:,} open tickets ({total_active:,} active + {total_non_actionable:,} non-actionable) require attention")
                
            elif 'Active' in selected_categories and len(selected_categories) == 2 and 'Total' in selected_categories:
                # Active-only focus
                total_active = summary_stats.get('total_active_tickets', 0)
                active_pct = (total_active / total_tickets * 100) if total_tickets > 0 else 0
                insights.append(f"🔄 Active Tickets Focus: {total_active:,} active tickets ({active_pct:.1f}% of total workload) currently in progress")
                
            else:
                # Standard top performer analysis
                if len(workload_data) > 0:
                    min_tickets = workload_data['total_tickets'].min()
                    max_tickets = workload_data['total_tickets'].max()
                    workload_ratio = max_tickets / max(min_tickets, 1)
                    
                    if workload_ratio > 5:
                        balance_status = "significant imbalance detected"
                    elif workload_ratio > 3:
                        balance_status = "moderate imbalance detected"
                    else:
                        balance_status = "relatively balanced distribution"
                        
                    insights.append(f"🎯 Top Performer: '{top_assignee}' handles {top_count_tickets:,} tickets ({(top_count_tickets/total_tickets*100):.1f}% of total) - {balance_status}")
            
            # Insight 3: Performance metrics (adapt based on visible categories)
            avg_escalation_rate = summary_stats.get('escalation_rate_avg', 0)
            
            if 'Closed' in selected_categories:
                avg_closure_rate = summary_stats.get('closure_rate_avg', 0)
                closure_insight = f"{avg_closure_rate:.1f}% avg closure rate, "
            else:
                closure_insight = ""
            
            if 'Active' in selected_categories or 'Non-Actionable' in selected_categories:
                escalation_insight = f"{avg_escalation_rate:.1f}% avg escalation rate"
                
                if avg_escalation_rate > 15:
                    escalation_status = "high escalation rates indicate potential capacity issues"
                elif avg_escalation_rate > 8:
                    escalation_status = "moderate escalation rates suggest balanced workload"
                else:
                    escalation_status = "low escalation rates indicate effective ticket handling"
            else:
                escalation_insight = ""
                escalation_status = ""
            
            unassigned_tickets = summary_stats.get('unassigned_tickets', 0)
            unassigned_note = f", {unassigned_tickets:,} tickets unassigned" if unassigned_tickets > 0 else ""
            
            performance_text = f"📈 Performance Metrics: {closure_insight}{escalation_insight}"
            if escalation_status:
                performance_text += f" - {escalation_status}"
            performance_text += unassigned_note
            
            insights.append(performance_text)
            
            # Create styled insight cards
            insight_components = []
            for insight in insights:
                insight_components.append(
                    html.Div([
                        html.Span(insight, style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            
            return html.Div(insight_components, className="insights-container")
        
        except Exception as e:
            print(f"❌ Error generating assignee workload insights: {e}")
            return html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate workload insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
                                    
    def create_error_figure(error_message):
        """Helper function to create consistent error figures"""
        fig = go.Figure()
        fig.add_annotation(
            text=error_message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            title={
                'text': "Assignee Workload Analysis - Error",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

    @callback(
        Output("workflow-assignee-categories-dropdown", "value"),
        [Input("btn-cat-all", "n_clicks"),
        Input("btn-cat-closed", "n_clicks"), 
        Input("btn-cat-open", "n_clicks")],
        prevent_initial_call=True
    )
    def handle_category_quick_select(btn_all, btn_closed, btn_open):
        """Handle quick select buttons for category combinations"""
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "btn-cat-all":
            # Show all categories
            return ['Closed', 'Active', 'Non-Actionable', 'Total']
        elif triggered_id == "btn-cat-closed":
            # Show only Closed tickets
            return ['Closed']
        elif triggered_id == "btn-cat-open":
            # Show Active + Non-Actionable (open items)
            return ['Active', 'Non-Actionable']
        
        return ['Closed', 'Active', 'Non-Actionable', 'Total']

    @callback(
        [Output("workflow-assignee-workload-chart", "figure"),
        Output("workflow-assignee-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
        Input("workflow-assignee-count-dropdown", "value"),
        Input("workflow-assignee-categories-dropdown", "value")],  # ADDED: Categories input
        prevent_initial_call=False
    )
    @monitor_performance("Assignee Workload Chart Update")
    def update_assignee_workload_chart(stored_selections, top_count, selected_categories):
        """
        Update assignee workload chart based on filter selections, top count, and selected categories
        ENHANCED: Support selective category display
        """
        try:
            # Handle None or invalid values
            if top_count is None:
                top_count = 10
            if selected_categories is None or len(selected_categories) == 0:
                selected_categories = ['Closed', 'Active', 'Non-Actionable', 'Total']
            
            # print(f"🔄 Updating assignee workload analysis: display = {top_count}, categories = {selected_categories}")
            
            # Get base data
            base_data = get_assignee_workload_base_data()
            
            # Apply filters
            filtered_data = apply_assignee_workload_filters(base_data['work_items'], stored_selections)
            
            # Prepare analysis data
            workload_data, summary_stats = prepare_assignee_workload_data(filtered_data, top_count)
            
            # Create visualization with selected categories
            fig = create_assignee_workload_chart(workload_data, summary_stats, top_count, selected_categories)
            
            # Generate insights (enhanced to reflect category selection)
            insights = generate_assignee_workload_insights(workload_data, summary_stats, top_count, selected_categories)

            # print(f"✅ Assignee workload analysis updated: {len(workload_data)} assignees displayed")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating assignee workload chart: {e}")
            
            # Return error chart and message
            fig = create_error_figure(f"Error loading assignee workload data: {str(e)}")
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate workload insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
            
    @callback(
        [
            Output("workflow-assignee-workload-modal", "is_open"),
            Output("workflow-assignee-workload-modal-chart", "figure")
        ],
        [
            Input("workflow-assignee-workload-chart-wrapper", "n_clicks"),
            Input("workflow-assignee-workload-modal-close", "n_clicks")
        ],
        [
            State("workflow-assignee-workload-modal", "is_open"),
            State("workflow-filtered-query-store", "data"),
            State("workflow-assignee-count-dropdown", "value"),
            State("workflow-assignee-categories-dropdown", "value")
        ],
        prevent_initial_call=True
    )
    def toggle_assignee_workload_modal(wrapper_clicks, close_clicks, is_open, stored_selections, top_count, selected_categories):
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        if triggered_id == "workflow-assignee-workload-chart-wrapper" and wrapper_clicks and not is_open:
            # Open modal with enlarged chart
            try:
                if selected_categories is None or len(selected_categories) == 0:
                    selected_categories = ['Closed', 'Active', 'Non-Actionable', 'Total']
                base_data = get_assignee_workload_base_data()
                filtered_data = apply_assignee_workload_filters(base_data['work_items'], stored_selections)
                workload_data, summary_stats = prepare_assignee_workload_data(filtered_data, top_count or 10)
                fig = create_assignee_workload_chart(workload_data, summary_stats, top_count or 10, selected_categories)
                fig.update_layout(height=600)
                return True, fig
            except Exception as e:
                print(f"❌ Error creating modal chart: {e}")
                return True, create_error_figure("Error loading enlarged chart")
        elif triggered_id == "workflow-assignee-workload-modal-close":
            # Close modal
            return False, go.Figure()
        return is_open, go.Figure()
        
    