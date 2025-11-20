from dash import callback, Input, Output, State, ctx, html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance
from inflection import titleize

def register_workflow_escalated_tickets_callbacks(app):
    
    @monitor_query_performance("Escalated Tickets Base Data")
    def get_escalated_tickets_base_data():
        """
        Get base data for escalated tickets analysis
        Uses Fact_WorkFlowItems and related tables for escalation information
        """
        queries = {
            "work_items": """
                SELECT 
                    w.WorkItemId,
                    w.Title,
                    w.CreatedOn,
                    w.ModifiedOn,
                    w.ClosedOn,
                    w.EscalatedOn,
                    w.WorkItemDefinitionShortCode,
                    w.WorkItemStatus,
                    w.IsEscalated,
                    w.AssignedTo,
                    w.AorShortName,
                    w.CaseOrigin,
                    w.CaseReason,
                    w.Priority,
                    w.Product,
                    w.Module,
                    w.Feature,
                    w.Issue,
                    -- Calculate escalation duration
                    CASE 
                        WHEN w.EscalatedOn IS NOT NULL AND w.ClosedOn IS NOT NULL
                        THEN DATEDIFF(MINUTE, w.EscalatedOn, w.ClosedOn)
                        WHEN w.EscalatedOn IS NOT NULL AND w.ClosedOn IS NULL
                        THEN DATEDIFF(MINUTE, w.EscalatedOn, GETDATE())
                        ELSE NULL
                    END as EscalationDurationMinutes,
                    -- Calculate time to escalation
                    CASE 
                        WHEN w.CreatedOn IS NOT NULL AND w.EscalatedOn IS NOT NULL
                        THEN DATEDIFF(MINUTE, w.CreatedOn, w.EscalatedOn)
                        ELSE NULL
                    END as TimeToEscalationMinutes
                FROM [consumable].[Fact_WorkFlowItems] w
                WHERE (w.IsEscalated = '1' OR w.EscalatedOn IS NOT NULL 
                       OR w.WorkItemStatus IN ('Escalated', 'Existing Escalation', 'Escalation Resolved', 'Escalation Canceled'))
            """,
            
            "status_transitions": """
                SELECT 
                    st.WorkItemId,
                    st.StatusFromDate,
                    st.StatusToDate,
                    st.FromStatusName,
                    st.ToStatusName,
                    st.DurationMinutes,
                    st.ChangedByUser
                FROM [consumable].[Fact_StatusTransitions] st
                WHERE st.ToStatusName IN ('Escalated', 'Existing Escalation')
                   OR st.FromStatusName IN ('Escalated', 'Existing Escalation')
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

    @monitor_performance("Escalated Tickets Filter Application")
    def apply_escalated_tickets_filters(work_items, stored_selections):
        """
        Apply filters to escalated tickets data using pandas
        """
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrame and create explicit copy
        df_work_items = pd.DataFrame(work_items).copy()
        
        print(f"📊 Initial escalated tickets data: {len(df_work_items)} tickets")
        
        # Apply date range filters
        day_from = stored_selections.get('Day_From')
        day_to = stored_selections.get('Day_To')
        
        if day_from:
            df_work_items = df_work_items[pd.to_datetime(df_work_items['CreatedOn']) >= pd.to_datetime(day_from)]
            print(f"📅 After Day_From filter ({day_from}): {len(df_work_items)} tickets")
        
        if day_to:
            df_work_items = df_work_items[pd.to_datetime(df_work_items['CreatedOn']) <= pd.to_datetime(day_to)]
            print(f"📅 After Day_To filter ({day_to}): {len(df_work_items)} tickets")
        
        # Apply categorical filters
        aor_filter = stored_selections.get('AOR', '').strip()
        if aor_filter:
            aor_values = [val.strip() for val in aor_filter.split(',') if val.strip()]
            if aor_values:
                df_work_items = df_work_items[df_work_items['AorShortName'].isin(aor_values)]
                print(f"🏢 After AOR filter ({aor_values}): {len(df_work_items)} tickets")

        case_types_filter = stored_selections.get('CaseTypes', '').strip()
        if case_types_filter:
            case_types_values = [val.strip() for val in case_types_filter.split(',') if val.strip()]
            if case_types_values:
                df_work_items = df_work_items[df_work_items['WorkItemDefinitionShortCode'].isin(case_types_values)]
                print(f"📋 After CaseTypes filter ({case_types_values}): {len(df_work_items)} tickets")

        status_filter = stored_selections.get('Status', '').strip()
        if status_filter:
            status_values = [val.strip() for val in status_filter.split(',') if val.strip()]
            if status_values:
                df_work_items = df_work_items[df_work_items['WorkItemStatus'].isin(status_values)]
                print(f"📊 After Status filter ({status_values}): {len(df_work_items)} tickets")

        priority_filter = stored_selections.get('Priority', '').strip()
        if priority_filter:
            priority_values = [val.strip() for val in priority_filter.split(',') if val.strip()]
            if priority_values:
                df_work_items = df_work_items[df_work_items['Priority'].isin(priority_values)]
                print(f"⚡ After Priority filter ({priority_values}): {len(df_work_items)} tickets")

        origins_filter = stored_selections.get('Origins', '').strip()
        if origins_filter:
            origins_values = [val.strip() for val in origins_filter.split(',') if val.strip()]
            if origins_values:
                df_work_items = df_work_items[df_work_items['CaseOrigin'].isin(origins_values)]
                print(f"🌐 After Origins filter ({origins_values}): {len(df_work_items)} tickets")

        products_filter = stored_selections.get('Products', '').strip()
        if products_filter:
            products_values = [val.strip() for val in products_filter.split(',') if val.strip()]
            if products_values:
                df_work_items = df_work_items[df_work_items['Product'].isin(products_values)]
                print(f"📦 After Products filter ({products_values}): {len(df_work_items)} tickets")

        features_filter = stored_selections.get('Features', '').strip()
        if features_filter:
            features_values = [val.strip() for val in features_filter.split(',') if val.strip()]
            if features_values:
                df_work_items = df_work_items[df_work_items['Feature'].isin(features_values)]
                print(f"🔧 After Features filter ({features_values}): {len(df_work_items)} tickets")

        modules_filter = stored_selections.get('Modules', '').strip()
        if modules_filter:
            modules_values = [val.strip() for val in modules_filter.split(',') if val.strip()]
            if modules_values:
                df_work_items = df_work_items[df_work_items['Module'].isin(modules_values)]
                print(f"🧩 After Modules filter ({modules_values}): {len(df_work_items)} tickets")

        issues_filter = stored_selections.get('Issues', '').strip()
        if issues_filter:
            issues_values = [val.strip() for val in issues_filter.split(',') if val.strip()]
            if issues_values:
                df_work_items = df_work_items[df_work_items['Issue'].isin(issues_values)]
                print(f"🐛 After Issues filter ({issues_values}): {len(df_work_items)} tickets")

        print(f"📊 Final filtered escalated tickets data: {len(df_work_items)} tickets")
        return df_work_items

    @monitor_performance("Escalated Tickets Data Preparation")
    def prepare_escalated_tickets_data(filtered_data, view_type='current', time_period=30, selected_categories=None):
        """
        Prepare escalated tickets analysis data based on view type
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        
        if selected_categories is None:
            selected_categories = ['current_escalated', 'recently_resolved']
        
        try:
            df = filtered_data.copy()
            
            # Clean and format assignee names
            def format_assignee_name(assignee):
                if pd.isna(assignee) or assignee == '' or assignee.lower() == 'unassigned':
                    return 'Unassigned'
                cleaned = str(assignee).split('@')[0].replace('.', ' ').replace('_', ' ').replace('\r', ' ').replace('\n', ' ')
                return titleize(cleaned)
            
            df['AssigneeDisplay'] = df['AssignedTo'].apply(format_assignee_name)
            
            # Convert date columns
            df['CreatedOn'] = pd.to_datetime(df['CreatedOn'], errors='coerce')
            df['EscalatedOn'] = pd.to_datetime(df['EscalatedOn'], errors='coerce')
            df['ClosedOn'] = pd.to_datetime(df['ClosedOn'], errors='coerce')
            df['ModifiedOn'] = pd.to_datetime(df['ModifiedOn'], errors='coerce')
            
            # Categorize escalation status
            def categorize_escalation_status(row):
                is_escalated = str(row['IsEscalated']).strip() in ['1', 'True', 'true']
                status = str(row['WorkItemStatus']).strip()
                closed_on = row['ClosedOn']
                escalated_on = row['EscalatedOn']
                
                # Currently escalated
                if is_escalated and pd.isna(closed_on) and status in ['Escalated', 'Existing Escalation']:
                    return 'current_escalated'
                
                # Recently resolved escalations
                elif not pd.isna(closed_on) and status in ['Escalation Resolved', 'Escalation Canceled']:
                    return 'recently_resolved'
                
                # Long duration escalations (more than 7 days)
                elif is_escalated and not pd.isna(escalated_on):
                    if pd.isna(closed_on):
                        days_escalated = (datetime.now() - escalated_on).days
                    else:
                        days_escalated = (closed_on - escalated_on).days
                    
                    if days_escalated > 7:
                        return 'long_duration'
                    else:
                        return 'current_escalated'
                
                else:
                    return 'other_escalated'
            
            df['EscalationCategory'] = df.apply(categorize_escalation_status, axis=1)
            
            # Apply time period filter
            if time_period != 'all':
                cutoff_date = datetime.now() - timedelta(days=time_period)
                df = df[df['CreatedOn'] >= cutoff_date]
            
            # Format duration for display
            def format_duration(minutes):
                if pd.isna(minutes) or minutes == 0:
                    return "0h"
                
                hours = int(minutes / 60)
                remaining_minutes = int(minutes % 60)
                days = int(hours / 24)
                remaining_hours = hours % 24
                
                if days > 0:
                    return f"{days}d {remaining_hours}h"
                elif hours > 0:
                    return f"{hours}h {remaining_minutes}m"
                else:
                    return f"{remaining_minutes}m"
            
            df['EscalationDurationFormatted'] = df['EscalationDurationMinutes'].apply(format_duration)
            df['TimeToEscalationFormatted'] = df['TimeToEscalationMinutes'].apply(format_duration)
            
            # Prepare data based on view type
            if view_type == 'current':
                # Current escalated tickets
                current_escalated = df[df['EscalationCategory'] == 'current_escalated'].copy()
                current_escalated = current_escalated.sort_values('EscalatedOn', ascending=True)
                
                visualization_data = current_escalated[['WorkItemId', 'AssigneeDisplay', 'Priority', 'EscalationDurationFormatted', 
                                                     'WorkItemDefinitionShortCode', 'EscalatedOn', 'Product', 'Feature']].head(20)
                
            elif view_type == 'trends':
                # Escalation trends over time
                df['EscalationWeek'] = df['EscalatedOn'].dt.to_period('W').astype(str)
                trends_data = df.groupby(['EscalationWeek', 'EscalationCategory']).size().unstack(fill_value=0).reset_index()
                visualization_data = trends_data
                
            elif view_type == 'assignee':
                # Escalations by assignee
                assignee_data = df.groupby(['AssigneeDisplay', 'EscalationCategory']).size().unstack(fill_value=0)
                assignee_data['total_escalated'] = assignee_data.sum(axis=1)
                assignee_data = assignee_data.sort_values('total_escalated', ascending=False).head(15)
                visualization_data = assignee_data
                
            elif view_type == 'duration':
                # Duration analysis
                duration_bins = pd.cut(df['EscalationDurationMinutes'].fillna(0), 
                                     bins=[0, 60, 480, 1440, 10080, float('inf')], 
                                     labels=['<1h', '1h-8h', '8h-1d', '1d-1w', '>1w'])
                duration_data = df.groupby([duration_bins, 'EscalationCategory']).size().unstack(fill_value=0)
                visualization_data = duration_data
            
            else:
                visualization_data = df
            
            # Calculate summary statistics
            total_escalated = len(df)
            currently_escalated = len(df[df['EscalationCategory'] == 'current_escalated'])
            avg_escalation_duration = df['EscalationDurationMinutes'].mean()
            avg_time_to_escalation = df['TimeToEscalationMinutes'].mean()
            
            summary_stats = {
                'total_escalated_tickets': total_escalated,
                'currently_escalated': currently_escalated,
                'recently_resolved': len(df[df['EscalationCategory'] == 'recently_resolved']),
                'long_duration_escalated': len(df[df['EscalationCategory'] == 'long_duration']),
                'avg_escalation_duration_hours': avg_escalation_duration / 60 if pd.notna(avg_escalation_duration) else 0,
                'avg_time_to_escalation_hours': avg_time_to_escalation / 60 if pd.notna(avg_time_to_escalation) else 0,
                'top_assignee_escalated': df['AssigneeDisplay'].value_counts().index[0] if len(df) > 0 else 'N/A',
                'critical_priority_count': len(df[df['Priority'].isin(['Critical', 'High', 'Urgent'])]),
                'escalation_rate': (total_escalated / len(df) * 100) if len(df) > 0 else 0,
                'view_type': view_type,
                'time_period': time_period,
                'selected_categories': selected_categories
            }
            
            print(f"📊 Prepared escalated tickets data: {len(visualization_data)} records for {view_type} view")
            return visualization_data, summary_stats
            
        except Exception as e:
            print(f"❌ Error preparing escalated tickets data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), {}

    @monitor_chart_performance("Escalated Tickets Chart")
    def create_escalated_tickets_chart(escalation_data, summary_stats, view_type='current', selected_categories=None):
        """
        Create escalated tickets visualization based on view type
        """
        if selected_categories is None:
            selected_categories = ['current_escalated', 'recently_resolved']
        
        if escalation_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No escalated tickets data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Escalated Tickets Overview",
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
            fig = go.Figure()
            
            if view_type == 'current':
                # Current escalated tickets - horizontal bar chart
                y_labels = [f"#{row['WorkItemId']} - {row['AssigneeDisplay'][:15]}" for _, row in escalation_data.iterrows()]
                duration_minutes = [0] * len(escalation_data)  # Placeholder for bar length
                
                # Color by priority
                colors = []
                for _, row in escalation_data.iterrows():
                    priority = str(row['Priority']).lower()
                    if priority in ['critical', 'urgent']:
                        colors.append('#e74c3c')  # Red
                    elif priority in ['high', 'important']:
                        colors.append('#f39c12')  # Orange
                    elif priority in ['medium', 'normal']:
                        colors.append('#3498db')  # Blue
                    else:
                        colors.append('#95a5a6')  # Gray
                
                fig.add_trace(go.Bar(
                    y=y_labels,
                    x=[1] * len(y_labels),  # Equal bars for display
                    orientation='h',
                    marker=dict(color=colors),
                    name='Current Escalated',
                    hovertemplate='<b>%{y}</b><br>' +
                                'Priority: %{customdata[0]}<br>' +
                                'Duration: %{customdata[1]}<br>' +
                                'Product: %{customdata[2]}<br>' +
                                '<extra></extra>',
                    customdata=[[row['Priority'], row['EscalationDurationFormatted'], row['Product']] 
                               for _, row in escalation_data.iterrows()]
                ))
                
                title_text = f"Currently Escalated Tickets ({len(escalation_data)} tickets)"
                
            elif view_type == 'trends':
                # Escalation trends over time - line chart
                for category in selected_categories:
                    if category in escalation_data.columns:
                        color_map = {
                            'current_escalated': '#e74c3c',
                            'recently_resolved': '#27ae60',
                            'long_duration': '#f39c12',
                            'other_escalated': '#95a5a6'
                        }
                        
                        fig.add_trace(go.Scatter(
                            x=escalation_data['EscalationWeek'],
                            y=escalation_data[category],
                            mode='lines+markers',
                            name=category.replace('_', ' ').title(),
                            line=dict(color=color_map.get(category, '#3498db'), width=3),
                            marker=dict(size=8),
                            hovertemplate='<b>%{fullData.name}</b><br>' +
                                        'Week: %{x}<br>' +
                                        'Count: %{y}<br>' +
                                        '<extra></extra>'
                        ))
                
                title_text = "Escalation Trends Over Time"
                
            elif view_type == 'assignee':
                # Escalations by assignee - stacked bar chart
                assignees = escalation_data.index[:15]  # Top 15 assignees
                
                for category in selected_categories:
                    if category in escalation_data.columns:
                        color_map = {
                            'current_escalated': '#e74c3c',
                            'recently_resolved': '#27ae60',
                            'long_duration': '#f39c12',
                            'other_escalated': '#95a5a6'
                        }
                        
                        fig.add_trace(go.Bar(
                            name=category.replace('_', ' ').title(),
                            x=assignees,
                            y=escalation_data.loc[assignees, category],
                            marker=dict(color=color_map.get(category, '#3498db')),
                            hovertemplate='<b>%{x}</b><br>' +
                                        '%{fullData.name}: %{y}<br>' +
                                        '<extra></extra>'
                        ))
                
                title_text = f"Escalated Tickets by Assignee (Top {len(assignees)})"
                
            elif view_type == 'duration':
                # Duration analysis - stacked bar chart
                duration_labels = escalation_data.index
                
                for category in selected_categories:
                    if category in escalation_data.columns:
                        color_map = {
                            'current_escalated': '#e74c3c',
                            'recently_resolved': '#27ae60',
                            'long_duration': '#f39c12',
                            'other_escalated': '#95a5a6'
                        }
                        
                        fig.add_trace(go.Bar(
                            name=category.replace('_', ' ').title(),
                            x=duration_labels,
                            y=escalation_data[category],
                            marker=dict(color=color_map.get(category, '#3498db')),
                            hovertemplate='<b>%{x}</b><br>' +
                                        '%{fullData.name}: %{y}<br>' +
                                        '<extra></extra>'
                        ))
                
                title_text = "Escalation Duration Analysis"
            
            # Update layout
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 14, 'color': '#2c3e50'}
                },
                height=450,
                margin={'l': 60, 'r': 50, 't': 80, 'b': 80},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True if view_type != 'current' else False,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=10)
                ),
                barmode='stack' if view_type in ['assignee', 'duration'] else 'group',
                hovermode='closest'
            )
            
            # Customize axes based on view type
            if view_type == 'current':
                fig.update_xaxes(title='Priority Level', showgrid=True, gridcolor='#f0f0f0')
                fig.update_yaxes(title='Escalated Tickets', tickfont={'size': 10})
            elif view_type == 'trends':
                fig.update_xaxes(title='Week', tickangle=-45)
                fig.update_yaxes(title='Number of Tickets')
            elif view_type == 'assignee':
                fig.update_xaxes(title='Assignee', tickangle=-45, tickfont={'size': 10})
                fig.update_yaxes(title='Number of Escalated Tickets')
            elif view_type == 'duration':
                fig.update_xaxes(title='Escalation Duration')
                fig.update_yaxes(title='Number of Tickets')
            
            print(f"📊 Created escalated tickets chart: {view_type} view with {len(escalation_data)} records")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating escalated tickets chart: {e}")
            import traceback
            traceback.print_exc()
            return create_error_figure("Error creating escalated tickets chart")

    @monitor_performance("Escalated Tickets Insights Generation")
    def generate_escalated_tickets_insights(escalation_data, summary_stats, view_type='current', selected_categories=None):
        """
        Generate automated insights from escalated tickets analysis
        """
        if escalation_data.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No escalated tickets data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see escalation analysis", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("⚡ Escalated tickets will appear when escalation data is available", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        if selected_categories is None:
            selected_categories = ['current_escalated', 'recently_resolved']
        
        try:
            insights = []
            
            # Insight 1: Current escalation status
            total_escalated = summary_stats.get('total_escalated_tickets', 0)
            currently_escalated = summary_stats.get('currently_escalated', 0)
            recently_resolved = summary_stats.get('recently_resolved', 0)
            long_duration = summary_stats.get('long_duration_escalated', 0)
            
            insights.append(f"🔴 Escalation Status: {currently_escalated:,} tickets currently escalated, {recently_resolved:,} recently resolved, {long_duration:,} long-duration escalations")
            
            # Insight 2: Performance metrics
            avg_escalation_duration = summary_stats.get('avg_escalation_duration_hours', 0)
            avg_time_to_escalation = summary_stats.get('avg_time_to_escalation_hours', 0)
            
            if avg_escalation_duration > 48:
                duration_status = "concerning escalation resolution times"
            elif avg_escalation_duration > 24:
                duration_status = "moderate escalation resolution times"
            else:
                duration_status = "good escalation resolution times"
            
            insights.append(f"⏱️ Performance Metrics: Avg escalation duration {avg_escalation_duration:.1f}h, avg time to escalation {avg_time_to_escalation:.1f}h - {duration_status}")
            
            # Insight 3: Critical analysis based on view type
            if view_type == 'current':
                critical_count = summary_stats.get('critical_priority_count', 0)
                critical_pct = (critical_count / max(currently_escalated, 1) * 100)
                
                if critical_pct > 50:
                    priority_status = "high proportion of critical priority escalations"
                elif critical_pct > 25:
                    priority_status = "moderate critical priority escalations"
                else:
                    priority_status = "low critical priority escalations"
                
                insights.append(f"⚡ Priority Analysis: {critical_count:,} critical/high priority escalations ({critical_pct:.1f}% of current) - {priority_status}")
                
            elif view_type == 'assignee':
                top_assignee = summary_stats.get('top_assignee_escalated', 'N/A')
                if len(escalation_data) > 0:
                    max_escalations = escalation_data.iloc[0].sum() if hasattr(escalation_data.iloc[0], 'sum') else 0
                    insights.append(f"👥 Workload Analysis: '{top_assignee}' handles most escalations ({max_escalations:,} tickets) - consider workload balancing")
                
            elif view_type == 'trends':
                # Trend analysis would require time series data
                insights.append(f"📈 Trend Analysis: Escalation patterns over selected time period show variation in ticket volume")
                
            elif view_type == 'duration':
                # Duration analysis
                insights.append(f"⏰ Duration Analysis: Escalation resolution times vary significantly - focus on long-duration cases")
            
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
            print(f"❌ Error generating escalated tickets insights: {e}")
            return html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate escalation insights", style={'fontSize': '13px'})], className="mb-2"),
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
                'text': "Escalated Tickets Analysis - Error",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig

    # Quick select callbacks
    @callback(
        Output("workflow-escalated-categories-dropdown", "value"),
        [Input("btn-escalated-active", "n_clicks"),
         Input("btn-escalated-critical", "n_clicks"), 
         Input("btn-escalated-all", "n_clicks")],
        prevent_initial_call=True
    )
    def handle_escalated_quick_select(btn_active, btn_critical, btn_all):
        """Handle quick select buttons for escalated ticket categories"""
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "btn-escalated-active":
            return ['current_escalated']
        elif triggered_id == "btn-escalated-critical":
            return ['current_escalated', 'long_duration']
        elif triggered_id == "btn-escalated-all":
            return ['current_escalated', 'recently_resolved', 'long_duration', 'all']
        
        return ['current_escalated', 'recently_resolved']

    # Main update callback
    @callback(
        [Output("workflow-escalated-tickets-chart", "figure"),
         Output("workflow-escalated-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
         Input("workflow-escalated-view-dropdown", "value"),
         Input("workflow-escalated-period-dropdown", "value"),
         Input("workflow-escalated-categories-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Escalated Tickets Chart Update")
    def update_escalated_tickets_chart(stored_selections, view_type, time_period, selected_categories):
        """
        Update escalated tickets chart based on filter selections and display options
        """
        try:
            # Handle None or invalid values
            if view_type is None:
                view_type = 'current'
            if time_period is None:
                time_period = 30
            if selected_categories is None or len(selected_categories) == 0:
                selected_categories = ['current_escalated', 'recently_resolved']
            
            print(f"🔄 Updating escalated tickets analysis: view = {view_type}, period = {time_period}, categories = {selected_categories}")
            
            # Get base data
            base_data = get_escalated_tickets_base_data()
            
            # Apply filters
            filtered_data = apply_escalated_tickets_filters(base_data['work_items'], stored_selections)
            
            # Prepare analysis data
            escalation_data, summary_stats = prepare_escalated_tickets_data(filtered_data, view_type, time_period, selected_categories)
            
            # Create visualization
            fig = create_escalated_tickets_chart(escalation_data, summary_stats, view_type, selected_categories)
            
            # Generate insights
            insights = generate_escalated_tickets_insights(escalation_data, summary_stats, view_type, selected_categories)

            print(f"✅ Escalated tickets analysis updated: {len(escalation_data)} records displayed")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating escalated tickets chart: {e}")
            import traceback
            traceback.print_exc()
            
            # Return error chart and message
            fig = create_error_figure(f"Error loading escalated tickets data: {str(e)}")
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate escalation insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights

    # Modal callback
    @callback(
        [Output("workflow-escalated-tickets-modal", "is_open"),
         Output("workflow-escalated-tickets-modal-chart", "figure")],
        [Input("workflow-escalated-tickets-chart", "clickData"),
         Input("workflow-escalated-tickets-modal-close", "n_clicks")],
        [State("workflow-escalated-tickets-modal", "is_open"),
         State("workflow-filtered-query-store", "data"),
         State("workflow-escalated-view-dropdown", "value"),
         State("workflow-escalated-period-dropdown", "value"),
         State("workflow-escalated-categories-dropdown", "value")],
        prevent_initial_call=True
    )
    def toggle_escalated_tickets_modal(click_data, close_clicks, is_open, stored_selections, view_type, time_period, selected_categories):
        """
        Toggle modal window for enlarged escalated tickets view
        """
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "workflow-escalated-tickets-chart" and click_data:
            # Open modal with enlarged chart
            try:
                if selected_categories is None or len(selected_categories) == 0:
                    selected_categories = ['current_escalated', 'recently_resolved']
                
                # Get base data and prepare enlarged chart
                base_data = get_escalated_tickets_base_data()
                filtered_data = apply_escalated_tickets_filters(base_data['work_items'], stored_selections)
                escalation_data, summary_stats = prepare_escalated_tickets_data(filtered_data, view_type or 'current', time_period or 30, selected_categories)
                
                # Create enlarged chart
                fig = create_escalated_tickets_chart(escalation_data, summary_stats, view_type or 'current', selected_categories)
                
                # Enhanced modal height
                fig.update_layout(height=600)
                
                return True, fig
                
            except Exception as e:
                print(f"❌ Error creating modal chart: {e}")
                return True, create_error_figure("Error loading enlarged chart")
        
        elif triggered_id == "workflow-escalated-tickets-modal-close":
            # Close modal
            return False, go.Figure()
        
        return is_open, go.Figure()