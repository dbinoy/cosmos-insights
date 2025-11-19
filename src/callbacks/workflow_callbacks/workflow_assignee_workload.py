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
    def apply_assignee_workload_filters(work_items, stored_selections):
        """
        Apply filters to assignee workload data using pandas
        FIXED: Updated to match the actual stored_selections format
        """
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrame and create explicit copy
        df_work_items = pd.DataFrame(work_items).copy()
        
        # print(f"📊 Initial assignee workload data: {len(df_work_items)} tickets")
        
        # FIXED: Apply date range filters using correct keys
        day_from = stored_selections.get('Day_From')
        day_to = stored_selections.get('Day_To')
        
        if day_from:
            df_work_items = df_work_items[pd.to_datetime(df_work_items['CreatedOn']) >= pd.to_datetime(day_from)]
            # print(f"📅 After Day_From filter ({day_from}): {len(df_work_items)} tickets")
        
        if day_to:
            df_work_items = df_work_items[pd.to_datetime(df_work_items['CreatedOn']) <= pd.to_datetime(day_to)]
            # print(f"📅 After Day_To filter ({day_to}): {len(df_work_items)} tickets")
        
        # FIXED: Apply categorical filters using correct keys and handling comma-separated values
        
        # AOR filter
        aor_filter = stored_selections.get('AOR', '').strip()
        if aor_filter:
            aor_values = [val.strip() for val in aor_filter.split(',') if val.strip()]
            if aor_values:
                df_work_items = df_work_items[df_work_items['AorShortName'].isin(aor_values)]
                # print(f"🏢 After AOR filter ({aor_values}): {len(df_work_items)} tickets")

        # Case Types filter
        case_types_filter = stored_selections.get('CaseTypes', '').strip()
        if case_types_filter:
            case_types_values = [val.strip() for val in case_types_filter.split(',') if val.strip()]
            if case_types_values:
                df_work_items = df_work_items[df_work_items['WorkItemDefinitionShortCode'].isin(case_types_values)]
                # print(f"📋 After CaseTypes filter ({case_types_values}): {len(df_work_items)} tickets")

        # Status filter
        status_filter = stored_selections.get('Status', '').strip()
        if status_filter:
            status_values = [val.strip() for val in status_filter.split(',') if val.strip()]
            if status_values:
                df_work_items = df_work_items[df_work_items['WorkItemStatus'].isin(status_values)]
                # print(f"📊 After Status filter ({status_values}): {len(df_work_items)} tickets")

        # Priority filter
        priority_filter = stored_selections.get('Priority', '').strip()
        if priority_filter:
            priority_values = [val.strip() for val in priority_filter.split(',') if val.strip()]
            if priority_values:
                df_work_items = df_work_items[df_work_items['Priority'].isin(priority_values)]
                # print(f"⚡ After Priority filter ({priority_values}): {len(df_work_items)} tickets")

        # Origins filter (CaseOrigin)
        origins_filter = stored_selections.get('Origins', '').strip()
        if origins_filter:
            origins_values = [val.strip() for val in origins_filter.split(',') if val.strip()]
            if origins_values:
                df_work_items = df_work_items[df_work_items['CaseOrigin'].isin(origins_values)]
                # print(f"🌐 After Origins filter ({origins_values}): {len(df_work_items)} tickets")

        # Products filter
        products_filter = stored_selections.get('Products', '').strip()
        if products_filter:
            products_values = [val.strip() for val in products_filter.split(',') if val.strip()]
            if products_values:
                df_work_items = df_work_items[df_work_items['Product'].isin(products_values)]
                # print(f"📦 After Products filter ({products_values}): {len(df_work_items)} tickets")

        # Features filter
        features_filter = stored_selections.get('Features', '').strip()
        if features_filter:
            features_values = [val.strip() for val in features_filter.split(',') if val.strip()]
            if features_values:
                df_work_items = df_work_items[df_work_items['Feature'].isin(features_values)]
                # print(f"🔧 After Features filter ({features_values}): {len(df_work_items)} tickets")

        # Modules filter
        modules_filter = stored_selections.get('Modules', '').strip()
        if modules_filter:
            modules_values = [val.strip() for val in modules_filter.split(',') if val.strip()]
            if modules_values:
                df_work_items = df_work_items[df_work_items['Module'].isin(modules_values)]
                # print(f"🧩 After Modules filter ({modules_values}): {len(df_work_items)} tickets")

        # Issues filter
        issues_filter = stored_selections.get('Issues', '').strip()
        if issues_filter:
            issues_values = [val.strip() for val in issues_filter.split(',') if val.strip()]
            if issues_values:
                df_work_items = df_work_items[df_work_items['Issue'].isin(issues_values)]
                # print(f"🐛 After Issues filter ({issues_values}): {len(df_work_items)} tickets")

        # Note: CaseReason (Reasons) is not available in the work_items query, so skipping it
        reasons_filter = stored_selections.get('Reasons', '').strip()
        # if reasons_filter:
        #     print(f"⚠️ Reasons filter requested ({reasons_filter}) but CaseReason not available in work_items data")
        
        # print(f"📊 Final filtered assignee workload data: {len(df_work_items)} tickets")
        return df_work_items

    @monitor_performance("Assignee Workload Data Preparation")
    def prepare_assignee_workload_data(filtered_data, top_count=10):
        """
        Prepare assignee workload analysis data
        Creates workload distribution with 3 status buckets: Closed, Active, Non-Actionable
        UPDATED: Enhanced status classification for better workload insights
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
                    # print(f"⚠️ Unknown status encountered: '{status}' - defaulting to Active")
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
            
            # Sort by total tickets and get top N
            assignee_metrics = assignee_metrics.sort_values('total_tickets', ascending=False).head(top_count)
            
            # UPDATED: Enhanced summary statistics
            total_closed = df[df['StatusCategory'] == 'Closed'].shape[0]
            total_active = df[df['StatusCategory'] == 'Active'].shape[0]
            total_non_actionable = df[df['StatusCategory'] == 'Non-Actionable'].shape[0]
            
            summary_stats = {
                'total_assignees': len(df['AssigneeDisplay'].unique()),
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
            
            # print(f"📊 Prepared assignee workload data: {len(assignee_metrics)} assignees, {len(df)} total tickets")
            # print(f"📊 Status distribution: {total_closed} Closed, {total_active} Active, {total_non_actionable} Non-Actionable")
            return assignee_metrics, summary_stats
            
        except Exception as e:
            print(f"❌ Error preparing assignee workload data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), {}

    @monitor_chart_performance("Assignee Workload Chart")
    def create_assignee_workload_chart(workload_data, summary_stats, top_count=10):
        """
        Create comprehensive assignee workload visualization
        REDESIGNED: Stacked bars + total line on same scale for clear comparison
        Answers: "Who has most total tickets?" and "Who has most active work?"
        """
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
            
            # Prepare assignee names (truncate if too long for better display)
            assignee_names = [name[:15] + '...' if len(name) > 15 else name for name in workload_data.index]
            
            # REDESIGNED: Create stacked bar chart with total line overlay
            fig = go.Figure()
            
            # STACKED BARS: Bottom to top - Closed, Active, Non-Actionable
            
            # 1. Closed tickets (Green - bottom layer)
            fig.add_trace(go.Bar(
                name='Closed',
                x=assignee_names,
                y=workload_data['Closed'],
                marker=dict(color='#27ae60'),
                hoverinfo='skip'  # Will use unified hover
            ))
            
            # 2. Active tickets (Blue - middle layer) 
            fig.add_trace(go.Bar(
                name='Active',
                x=assignee_names,
                y=workload_data['Active'],
                marker=dict(color='#3498db'),
                hoverinfo='skip'  # Will use unified hover
            ))
            
            # 3. Non-Actionable tickets (Orange - top layer)
            fig.add_trace(go.Bar(
                name='Non-Actionable',
                x=assignee_names,
                y=workload_data['Non-Actionable'],
                marker=dict(color='#f39c12'),
                hoverinfo='skip'  # Will use unified hover
            ))
            
            # TOTAL LINE: Red line showing total tickets (same scale as bars)
            fig.add_trace(go.Scatter(
                name='Total',
                x=assignee_names,
                y=workload_data['total_tickets'],
                mode='markers+lines',
                marker=dict(
                    color='#e74c3c',
                    size=8,
                    symbol='circle',
                    line=dict(width=2, color='white')  # White border for visibility
                ),
                line=dict(
                    color='#e74c3c',
                    width=3
                ),
                hoverinfo='skip'  # Will use unified hover
            ))
            
            # UNIFIED HOVER: Single hover box with all information
            # Add invisible scatter plot for unified hover
            fig.add_trace(go.Scatter(
                x=assignee_names,
                y=workload_data['total_tickets'],
                mode='markers',
                marker=dict(
                    color='rgba(0,0,0,0)',  # Transparent
                    size=20  # Large hover area
                ),
                showlegend=False,
                hovertemplate=(
                    "<b>%{x}</b><br>" +
                    "─────────────────<br>" +
                    "📊 <b>Total Tickets:</b> %{customdata[0]}<br>" +
                    "✅ <b>Closed:</b> %{customdata[1]} (%{customdata[2]:.1f}%)<br>" +
                    "🔄 <b>Active:</b> %{customdata[3]} (%{customdata[4]:.1f}%)<br>" +
                    "⏸️ <b>Non-Actionable:</b> %{customdata[5]}<br>" +
                    "─────────────────<br>" +
                    "⚡ <b>Escalated:</b> %{customdata[6]} (%{customdata[7]:.1f}%)<br>" +
                    "🎯 <b>Common Priority:</b> %{customdata[8]}<br>" +
                    "<extra></extra>"
                ),
                customdata=list(zip(
                    workload_data['total_tickets'],        # 0
                    workload_data['Closed'],               # 1
                    workload_data['closure_rate'],         # 2
                    workload_data['Active'],               # 3
                    workload_data['active_rate'],          # 4
                    workload_data['Non-Actionable'],       # 5
                    workload_data['escalated_tickets'],    # 6
                    workload_data['escalation_rate'],      # 7
                    workload_data['common_priority']       # 8
                ))
            ))
            
            # Calculate summary stats for title
            total_assignees = summary_stats.get('total_assignees', 0)
            total_closed = summary_stats.get('total_closed_tickets', 0)
            total_active = summary_stats.get('total_active_tickets', 0)
            total_non_actionable = summary_stats.get('total_non_actionable_tickets', 0)
            avg_closure_rate = summary_stats.get('closure_rate_avg', 0)
            
            # Enhanced title with key metrics
            title_text = (
                f"Assignee Workload Analysis (Top {top_count} of {total_assignees})"
            )
            
            # Calculate dynamic parameters
            num_assignees = len(workload_data)
            max_total = workload_data['total_tickets'].max()
            
            # Update layout
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 13, 'color': '#2c3e50'}
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
                    'range': [0, max_total * 1.1]  # Add 10% padding at top
                },
                height=450,
                margin={'l': 60, 'r': 50, 't': 100, 'b': 100},
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
                barmode='stack',  # STACKED: Shows composition clearly
                hovermode='x unified'  # Unified hover for cleaner experience
            )
            
            # Add key insights as annotations
            if len(workload_data) > 0:
                # Highlight assignee with most total tickets
                top_total_assignee = workload_data.index[0]
                top_total_count = workload_data['total_tickets'].iloc[0]
                
                # Highlight assignee with most active tickets
                top_active_idx = workload_data['Active'].idxmax()
                top_active_count = workload_data.loc[top_active_idx, 'Active']
                top_active_pos = list(workload_data.index).index(top_active_idx)
                
                # Annotation for most total tickets
                fig.add_annotation(
                    x=assignee_names[0],
                    y=top_total_count + (max_total * 0.05),
                    text=f"Most Total<br>{top_total_count}",
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
            
            # print(f"📊 Created stacked bar + total line chart: {len(workload_data)} assignees displayed")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating assignee workload chart: {e}")
            import traceback
            traceback.print_exc()
            return create_error_figure("Error creating assignee workload chart")
                      
    @monitor_performance("Assignee Workload Insights Generation")
    def generate_assignee_workload_insights(workload_data, summary_stats, top_count=10):
        """
        Generate automated insights from assignee workload analysis
        """
        if workload_data.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No assignee workload data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see workload distribution", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("👥 Data will appear when tickets have assignee information", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        try:
            insights = []
            
            # Insight 1: Overall workload distribution
            total_assignees = summary_stats.get('total_assignees', 0)
            total_tickets = summary_stats.get('total_tickets', 0)
            avg_tickets = summary_stats.get('avg_tickets_per_assignee', 0)
            top_assignee = summary_stats.get('top_assignee', 'N/A')
            top_count_tickets = summary_stats.get('top_assignee_count', 0)
            
            insights.append(f"📊 Workload Overview: {total_tickets:,} tickets distributed across {total_assignees} assignees (avg: {avg_tickets:.1f} tickets/assignee)")
            
            # Insight 2: Top performer analysis
            if len(workload_data) > 0:
                # Calculate workload imbalance
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
            else:
                insights.append(f"🎯 Top Performer: '{top_assignee}' handles {top_count_tickets:,} tickets")
            
            # Insight 3: Performance metrics analysis
            avg_escalation_rate = summary_stats.get('escalation_rate_avg', 0)
            avg_closure_rate = summary_stats.get('closure_rate_avg', 0)
            unassigned_tickets = summary_stats.get('unassigned_tickets', 0)
            
            if unassigned_tickets > 0:
                unassigned_note = f", {unassigned_tickets:,} tickets unassigned"
            else:
                unassigned_note = ""
                
            # Assess performance indicators
            if avg_escalation_rate > 15:
                escalation_status = "high escalation rates indicate potential capacity issues"
            elif avg_escalation_rate > 8:
                escalation_status = "moderate escalation rates suggest balanced workload"
            else:
                escalation_status = "low escalation rates indicate effective ticket handling"
            
            insights.append(f"📈 Performance Metrics: {avg_closure_rate:.1f}% avg closure rate, {avg_escalation_rate:.1f}% avg escalation rate - {escalation_status}{unassigned_note}")
            
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

    # Main callback for assignee workload chart
    @callback(
        [Output("workflow-assignee-workload-chart", "figure"),
         Output("workflow-assignee-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
         Input("workflow-assignee-count-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Assignee Workload Chart Update")
    def update_assignee_workload_chart(stored_selections, top_count):
        """
        Update assignee workload chart based on filter selections and top count
        """
        # print(f"Stored selections for assignee workload update: {stored_selections}")
        try:
            if top_count is None:
                top_count = 10

            # print(f"🔄 Updating assignee workload analysis: top {top_count}")
            
            # Get base data
            base_data = get_assignee_workload_base_data()
            
            # Apply filters
            filtered_data = apply_assignee_workload_filters(base_data['work_items'], stored_selections)
            
            # Prepare analysis data
            workload_data, summary_stats = prepare_assignee_workload_data(filtered_data, top_count)
            
            # Create visualization
            fig = create_assignee_workload_chart(workload_data, summary_stats, top_count)
            
            # Generate insights
            insights = generate_assignee_workload_insights(workload_data, summary_stats, top_count)

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

    # Modal callback for enlarged view
    @callback(
        [Output("workflow-assignee-workload-modal", "is_open"),
         Output("workflow-assignee-workload-modal-chart", "figure")],
        [Input("workflow-assignee-workload-chart", "clickData"),
         Input("workflow-assignee-workload-modal-close", "n_clicks")],
        [State("workflow-assignee-workload-modal", "is_open"),
         State("workflow-filtered-query-store", "data"),
         State("workflow-assignee-count-dropdown", "value")],
        prevent_initial_call=True
    )
    def toggle_assignee_workload_modal(click_data, close_clicks, is_open, stored_selections, top_count):
        """
        Toggle modal window for enlarged assignee workload view
        """
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "workflow-assignee-workload-chart" and click_data:
            # Open modal with enlarged chart
            try:
                # Get base data and prepare enlarged chart
                base_data = get_assignee_workload_base_data()
                filtered_data = apply_assignee_workload_filters(base_data['work_items'], stored_selections)
                workload_data, summary_stats = prepare_assignee_workload_data(filtered_data, top_count or 10)
                
                # Create enlarged chart
                fig = create_assignee_workload_chart(workload_data, summary_stats, top_count or 10)
                fig.update_layout(height=600)  # Larger height for modal
                
                return True, fig
                
            except Exception as e:
                print(f"❌ Error creating modal chart: {e}")
                return True, create_error_figure("Error loading enlarged chart")
        
        elif triggered_id == "workflow-assignee-workload-modal-close":
            # Close modal
            return False, go.Figure()
        
        return is_open, go.Figure()