from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance
from inflection import titleize
import dash_bootstrap_components as dbc

def register_workflow_escalated_tickets_callbacks(app):
    
    @monitor_query_performance("Escalated Tickets Base Data")
    def get_escalated_tickets_base_data():
        """
        Get base data for escalated tickets analysis
        Uses only Fact_WorkFlowItems for escalation information
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
                    -- Calculate escalation duration (excluding placeholder dates)
                    CASE 
                        WHEN w.EscalatedOn IS NOT NULL 
                            AND CAST(w.EscalatedOn AS DATE) != CAST('1900-01-01' AS DATE)
                            AND w.ClosedOn IS NOT NULL 
                            AND CAST(w.ClosedOn AS DATE) != CAST('1900-01-01' AS DATE)
                        THEN DATEDIFF(MINUTE, w.EscalatedOn, w.ClosedOn)
                        WHEN w.EscalatedOn IS NOT NULL 
                            AND CAST(w.EscalatedOn AS DATE) != CAST('1900-01-01' AS DATE)
                            AND (w.ClosedOn IS NULL OR CAST(w.ClosedOn AS DATE) = CAST('1900-01-01' AS DATE))
                        THEN DATEDIFF(MINUTE, w.EscalatedOn, GETDATE())
                        ELSE NULL
                    END as EscalationDurationMinutes,
                    -- Calculate time to escalation (excluding placeholder dates)
                    CASE 
                        WHEN w.CreatedOn IS NOT NULL 
                            AND CAST(w.CreatedOn AS DATE) != CAST('1900-01-01' AS DATE)
                            AND w.EscalatedOn IS NOT NULL 
                            AND CAST(w.EscalatedOn AS DATE) != CAST('1900-01-01' AS DATE)
                        THEN DATEDIFF(MINUTE, w.CreatedOn, w.EscalatedOn)
                        ELSE NULL
                    END as TimeToEscalationMinutes
                FROM [consumable].[Fact_WorkFlowItems] w
                WHERE (w.IsEscalated = '1')
            """,
            
            # Get case type name mapping
            "case_type_mapping": """
                SELECT DISTINCT CaseTypeCode, CaseTypeName
                FROM [consumable].[Dim_WorkItemAttributes]
                WHERE CaseTypeCode IS NOT NULL AND CaseTypeName IS NOT NULL
            """
        }
        
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("Escalated Tickets Filter Application")
    def apply_escalated_tickets_filters(work_items, stored_selections):
        """
        Apply filters to escalated tickets data using pandas, properly handling placeholder dates
        """
        print(f"📊 Applying filters to escalated tickets data: {stored_selections}")
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrame and create explicit copy
        df_work_items = pd.DataFrame(work_items).copy()
        
        print(f"📊 Initial escalated tickets data: {len(df_work_items)} tickets")
        
        # Clean placeholder dates (convert 1900-01-01T00:00:00.0000000 to NaT)
        date_columns = ['CreatedOn', 'ModifiedOn', 'ClosedOn', 'EscalatedOn']
        for col in date_columns:
            if col in df_work_items.columns:
                df_work_items[col] = pd.to_datetime(df_work_items[col], errors='coerce')
                # Replace dates that start with 1900-01-01 with NaT
                mask_1900 = df_work_items[col].dt.strftime('%Y-%m-%d').eq('1900-01-01')
                df_work_items.loc[mask_1900, col] = pd.NaT
                print(f"🧹 Cleaned {mask_1900.sum()} placeholder dates from {col}")
        
        # Apply date range filters using CreatedOn (respecting Day_From and Day_To)
        day_from = stored_selections.get('Day_From')
        day_to = stored_selections.get('Day_To')
        
        if day_from:
            day_from_dt = pd.to_datetime(day_from)
            df_work_items = df_work_items[df_work_items['CreatedOn'] >= day_from_dt]
            print(f"📅 After Day_From filter ({day_from}): {len(df_work_items)} tickets")
        
        if day_to:
            day_to_dt = pd.to_datetime(day_to)
            # Add one day to include the entire day_to date
            day_to_end = day_to_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df_work_items = df_work_items[df_work_items['CreatedOn'] <= day_to_end]
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
    def prepare_escalated_tickets_data(filtered_data, case_type_mapping, view_type='current', time_period=30, selected_categories=None, stored_selections=None):
        """
        Prepare escalated tickets analysis data with proper duration buckets and case type names
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        
        if selected_categories is None:
            selected_categories = ['current_escalated', 'recently_resolved']
        
        if stored_selections is None:
            stored_selections = {}
        
        try:
            df = filtered_data.copy()
            
            # Clean and format assignee names
            def format_assignee_name(assignee):
                if pd.isna(assignee) or assignee == '' or assignee.lower() == 'unassigned':
                    return 'Unassigned'
                cleaned = str(assignee).split('@')[0].replace('.', ' ').replace('_', ' ').replace('\r', ' ').replace('\n', ' ')
                return titleize(cleaned)
            
            df['AssigneeDisplay'] = df['AssignedTo'].apply(format_assignee_name)
            
            # Map case type codes to names using the dimension table
            # FIX: Proper DataFrame check
            if case_type_mapping is not None and not case_type_mapping.empty:
                case_type_dict = dict(zip(case_type_mapping['CaseTypeCode'], case_type_mapping['CaseTypeName']))
                case_type_dict['Unspecified'] = 'Unspecified'
                case_type_dict[''] = 'Unspecified'
                
                def map_case_type(code):
                    if pd.isna(code) or code == '':
                        return 'Unspecified'
                    return case_type_dict.get(str(code), titleize(str(code)))
                
                df['CaseTypeName'] = df['WorkItemDefinitionShortCode'].apply(map_case_type)
            else:
                # Fallback to titleized code
                df['CaseTypeName'] = df['WorkItemDefinitionShortCode'].apply(
                    lambda x: 'Unspecified' if pd.isna(x) or x == '' else titleize(str(x))
                )
            
            # Create detailed duration buckets for escalation analysis
            def categorize_escalation_duration(minutes):
                if pd.isna(minutes):
                    return 'No Duration Data'
                elif minutes < 60:
                    return '<1h'
                elif minutes < 120:
                    return '1-2h'
                elif minutes < 180:
                    return '2-3h'
                elif minutes < 360:
                    return '3-6h'
                elif minutes < 720:
                    return '6-12h'
                elif minutes < 1440:
                    return '12-24h'
                elif minutes < 2880:
                    return '1-2d'
                elif minutes < 4320:
                    return '2-3d'
                elif minutes < 7200:
                    return '3-5d'
                elif minutes < 14400:
                    return '5-10d'
                elif minutes < 43200:
                    return '10-30d'
                elif minutes < 86400:
                    return '1-2m'
                elif minutes < 129600:
                    return '2-3m'
                elif minutes < 259200:
                    return '3-6m'
                elif minutes < 525600:  
                    return '6-12m'
                else:
                    return '>12m'
            
            df['EscalationDurationBucket'] = df['EscalationDurationMinutes'].apply(categorize_escalation_duration)
            
            # Categorize escalation status (with proper date handling)
            def categorize_escalation_status(row):
                is_escalated = str(row['IsEscalated']).strip() in ['1', 'True', 'true']
                status = str(row['WorkItemStatus']).strip()
                closed_on = row['ClosedOn']
                escalated_on = row['EscalatedOn']
                
                # Currently escalated (not closed or closed date is placeholder)
                if is_escalated and pd.isna(closed_on) and status in ['Escalated', 'Existing Escalation']:
                    return 'current_escalated'
                
                # Recently resolved escalations (proper close date)
                elif not pd.isna(closed_on) and status in ['Escalation Resolved', 'Escalation Canceled']:
                    return 'recently_resolved'
                
                # Long duration escalations (more than 7 days, excluding placeholder dates)
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
            
            # For current view, prepare stacked bar chart data by priority vs duration buckets
            if view_type == 'current':
                # Create cross-tabulation for stacked bar chart: Duration buckets x Priority
                priority_duration_cross = pd.crosstab(
                    df['EscalationDurationBucket'], 
                    df['Priority'], 
                    margins=False
                ).fillna(0)
                
                # Ensure proper ordering of duration buckets
                duration_order = ['<1h', '1-2h', '2-3h', '3-6h', '6-12h', '12-24h', 
                                '1-2d', '2-3d', '3-5d', '5-10d', '10-30d', '1-2m', 
                                '2-3m', '3-6m', '6-12m', '>12m', 'No Duration Data']
                
                # Reindex to ensure proper order and include missing buckets
                existing_buckets = [bucket for bucket in duration_order if bucket in priority_duration_cross.index]
                priority_duration_cross = priority_duration_cross.reindex(existing_buckets, fill_value=0)
                
                visualization_data = priority_duration_cross
                
            else:
                # For other view types, use existing logic
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
                'selected_categories': selected_categories,
                'detailed_data': df  # Store the full dataframe for modal table
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
        Create stacked bar chart showing priority distribution across escalation duration buckets
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
                # Create stacked bar chart: Duration buckets x Priority
                
                # Define priority colors
                priority_colors = {
                    'critical': '#e74c3c',      # Red
                    'high': '#f39c12',          # Orange  
                    'medium': '#3498db',        # Blue
                    'low': '#95a5a6',           # Gray
                    'association-support': '#9b59b6',  # Purple
                    'in-house-support': '#1abc9c'      # Teal
                }
                
                # Get priorities in the data and sort by criticality
                priorities = escalation_data.columns.tolist()
                priority_order = ['critical', 'high', 'medium', 'low', 'association-support', 'in-house-support']
                
                # Sort priorities by the defined order, with unknown priorities at the end
                sorted_priorities = []
                for priority in priority_order:
                    if priority in priorities:
                        sorted_priorities.append(priority)
                for priority in priorities:
                    if priority not in sorted_priorities:
                        sorted_priorities.append(priority)
                
                # Create stacked bars for each priority
                for priority in sorted_priorities:
                    if priority in escalation_data.columns:
                        color = priority_colors.get(priority.lower(), '#7f8c8d')
                        
                        # Calculate percentages for hover
                        total_counts = escalation_data.sum(axis=1)
                        percentages = ((escalation_data[priority] / total_counts) * 100).fillna(0)
                        
                        fig.add_trace(go.Bar(
                            name=priority.title(),
                            x=escalation_data.index,
                            y=escalation_data[priority],
                            marker_color=color,
                            hovertemplate='<b>%{fullData.name} Priority</b><br>' +
                                        'Duration: %{x}<br>' +
                                        'Count: %{y}<br>' +
                                        'Percentage: %{customdata:.1f}%<br>' +
                                        '<extra></extra>',
                            customdata=percentages
                        ))
                
                title_text = f"Escalated Tickets by Priority & Duration ({escalation_data.sum().sum():,.0f} tickets)"
                
                # Update layout for stacked bar chart
                fig.update_layout(
                    title={
                        'text': title_text,
                        'x': 0.5,
                        'xanchor': 'center',
                        'font': {'size': 14, 'color': '#2c3e50'}
                    },
                    xaxis_title="Escalation Duration",
                    yaxis_title="Number of Tickets",
                    height=450,
                    margin={'l': 60, 'r': 50, 't': 80, 'b': 120},  # More space for x-axis labels
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
                    hovermode='closest',
                    xaxis=dict(
                        tickangle=45,
                        tickfont={'size': 10}
                    )
                )
                
            else:
                # For other view types, create a simple message
                fig.add_annotation(
                    text="Stacked bar view is only available for 'Escalated' view type",
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
            
            print(f"📊 Created escalated tickets chart: {view_type} view with {len(escalation_data)} records")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating escalated tickets chart: {e}")
            import traceback
            traceback.print_exc()
            return create_error_figure("Error creating escalated tickets chart")

    def create_escalated_tickets_table(detailed_data):
        """
        Create a detailed table for the modal showing all escalated tickets with filtering
        """
        if detailed_data.empty:
            return html.Div("No escalated tickets data available", className="text-center text-muted p-4")
        
        try:
            # Sort by escalation duration descending (longest first)
            df_sorted = detailed_data.sort_values('EscalationDurationMinutes', ascending=False, na_position='last').reset_index(drop=True)
            
            # Get unique values for filter dropdowns
            unique_priorities = sorted([p for p in df_sorted['Priority'].dropna().unique() if p])
            unique_durations = sorted([d for d in df_sorted['EscalationDurationBucket'].dropna().unique() if d], 
                                    key=lambda x: ['<1h', '1-2h', '2-3h', '3-6h', '6-12h', '12-24h', 
                                                 '1-2d', '2-3d', '3-5d', '5-10d', '10-30d', '1-2m', 
                                                 '2-3m', '3-6m', '6-12m', '>12m', 'No Duration Data'].index(x) 
                                                 if x in ['<1h', '1-2h', '2-3h', '3-6h', '6-12h', '12-24h', 
                                                         '1-2d', '2-3d', '3-5d', '5-10d', '10-30d', '1-2m', 
                                                         '2-3m', '3-6m', '6-12m', '>12m', 'No Duration Data'] else 999)
            unique_case_types = sorted([c for c in df_sorted['CaseTypeName'].dropna().unique() if c])
            unique_statuses = sorted([s for s in df_sorted['WorkItemStatus'].dropna().unique() if s])
            
            # Create filter controls - Updated layout to accommodate Status filter
            filter_controls = dbc.Row([
                dbc.Col([
                    html.Label("Priority:", className="form-label mb-1", style={'fontSize': '12px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="escalated-modal-priority-filter",
                        options=[{'label': 'All Priorities', 'value': 'all'}] + 
                               [{'label': p, 'value': p} for p in unique_priorities],
                        value='all',
                        clearable=False,
                        style={'fontSize': '11px'}
                    )
                ], width=2),
                dbc.Col([
                    html.Label("Duration:", className="form-label mb-1", style={'fontSize': '12px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="escalated-modal-duration-filter",
                        options=[{'label': 'All Durations', 'value': 'all'}] + 
                               [{'label': d, 'value': d} for d in unique_durations],
                        value='all',
                        clearable=False,
                        style={'fontSize': '11px'}
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Case Type:", className="form-label mb-1", style={'fontSize': '12px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="escalated-modal-casetype-filter",
                        options=[{'label': 'All Case Types', 'value': 'all'}] + 
                               [{'label': c, 'value': c} for c in unique_case_types],
                        value='all',
                        clearable=False,
                        style={'fontSize': '11px'}
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Status:", className="form-label mb-1", style={'fontSize': '12px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="escalated-modal-status-filter",
                        options=[{'label': 'All Statuses', 'value': 'all'}] + 
                               [{'label': s, 'value': s} for s in unique_statuses],
                        value='all',
                        clearable=False,
                        style={'fontSize': '11px'}
                    )
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.Label("Results:", className="form-label mb-1", style={'fontSize': '12px', 'fontWeight': '500'}),
                        html.Div(f"{len(df_sorted):,} tickets", 
                               id="escalated-modal-results-count",
                               style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#2c3e50'})
                    ])
                ], width=2)
            ], className="mb-3")
            
            # Create the initial table with all data (will be updated by callback when filters change)
            initial_table = create_filtered_escalated_table(df_sorted)
            
            return html.Div([
                # Header with summary
                # html.H4("Escalated Tickets Details", className="mb-3 text-primary"),
                html.P([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Total: {len(df_sorted):,} escalated tickets"
                ], className="text-muted mb-3"),
                
                # Filter controls
                filter_controls,
                
                # Table container with initial data
                html.Div(id="escalated-modal-table-container", children=initial_table),
                
                # Store the data for the callback
                dcc.Store(id="escalated-modal-data-store", data=df_sorted.to_dict('records'))
            ], className="p-3")
            
        except Exception as e:
            print(f"❌ Error creating escalated tickets table: {e}")
            return html.Div([
                # html.H4("Error Creating Escalated Tickets Details", className="text-danger mb-3"),
                html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
            ], className="text-center p-4")

    def create_filtered_escalated_table(filtered_df):
        """
        Create the actual table from filtered data
        """
        if filtered_df.empty:
            return html.Div("No tickets match the current filter selection.", className="text-center text-muted p-4")
        
        # Limit to first 100 rows for performance
        display_df = filtered_df.head(100)
        show_more_message = len(filtered_df) > 100
        
        # Create table rows
        table_rows = []
        for i, row in display_df.iterrows():
            # Priority color
            priority_colors = {
                'critical': '#e74c3c', 'high': '#f39c12', 'medium': '#3498db',
                'low': '#95a5a6', 'association-support': '#9b59b6', 'in-house-support': '#1abc9c'
            }
            priority_color = priority_colors.get(str(row['Priority']).lower(), '#7f8c8d')
            
            # Status color
            status_color = '#e74c3c' if 'escalated' in str(row['WorkItemStatus']).lower() else '#3498db'
            
            # Prepare title for hover - truncate if too long and clean it
            title_text = str(row['Title']) if pd.notna(row['Title']) else 'No title available'
            # Clean title text for display
            title_text = title_text.replace('\n', ' ').replace('\r', ' ').strip()
            # Truncate very long titles for better hover display
            if len(title_text) > 200:
                title_text = title_text[:197] + "..."
            
            table_rows.append(
                html.Tr([
                    # Ticket ID with Title hover tooltip
                    html.Td([
                        html.Span(
                            f"#{row['WorkItemId']}", 
                            title=title_text,  # This creates the hover tooltip
                            style={
                                'fontWeight': 'bold', 
                                'fontSize': '12px',
                                'cursor': 'help',  # Changes cursor to indicate hoverable content
                                'textDecoration': 'underline',  # Subtle visual cue
                                'textDecorationStyle': 'dotted'  # Makes it clear it's hoverable
                            }
                        )
                    ]),
                    html.Td([
                        html.Span(str(row['Priority']), className="badge rounded-pill", style={
                            'backgroundColor': priority_color, 'color': 'white', 'fontSize': '10px'
                        })
                    ], className="text-center"),
                    html.Td([
                        html.Span(row['EscalationDurationBucket'], className="badge rounded-pill", style={
                            'backgroundColor': '#6c757d', 'color': 'white', 'fontSize': '10px'
                        })
                    ], className="text-center"),
                    html.Td(str(row['CaseTypeName']), style={'fontSize': '12px'}),
                    html.Td(str(row['AssigneeDisplay']), style={'fontSize': '12px'}),
                    html.Td([
                        html.Span(str(row['WorkItemStatus']), className="badge rounded-pill", style={
                            'backgroundColor': status_color, 'color': 'white', 'fontSize': '10px'
                        })
                    ], className="text-center"),
                    html.Td(str(row['EscalationDurationFormatted']), className="text-end", style={'fontSize': '12px'}),
                    html.Td(row['EscalatedOn'].strftime('%Y-%m-%d %H:%M') if pd.notna(row['EscalatedOn']) else '—', 
                           className="text-center", style={'fontSize': '11px'})
                ], style={'fontSize': '12px', 'verticalAlign': 'middle'})
            )
        
        # Table component
        table_component = html.Table([
            html.Thead([
                html.Tr([
                    html.Th([
                        html.Span("Ticket ID", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                        html.Small(" (hover for title)", style={'fontSize': '10px', 'color': '#6c757d', 'fontStyle': 'italic'})
                    ]),
                    html.Th("Priority", className="text-center", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Th("Duration", className="text-center", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Th("Case Type", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Th("Assignee", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Th("Status", className="text-center", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Th("Duration", className="text-end", style={'fontSize': '12px', 'fontWeight': 'bold'}),
                    html.Th("Escalated On", className="text-center", style={'fontSize': '12px', 'fontWeight': 'bold'})
                ], style={'backgroundColor': '#f8f9fa'})
            ]),
            html.Tbody(table_rows)
        ], className="table table-hover table-sm")
        
        # Create container with table and optional "showing limited results" message
        components = [table_component]
        
        if show_more_message:
            components.append(
                html.Div([
                    html.I(className="fas fa-info-circle me-2"),
                    f"Showing first 100 of {len(filtered_df):,} tickets. Use filters above to refine results."
                ], className="alert alert-info mt-2", style={'fontSize': '12px'})
            )
        
        return html.Div(components, style={'maxHeight': '500px', 'overflowY': 'auto', 'border': '1px solid #dee2e6', 'borderRadius': '8px'})
    
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
            
            # Insight 1: Duration distribution analysis
            if view_type == 'current' and hasattr(escalation_data, 'sum'):
                total_tickets = escalation_data.sum().sum()
                
                # Find duration bucket with most tickets
                duration_totals = escalation_data.sum(axis=1).sort_values(ascending=False)
                top_duration = duration_totals.index[0] if len(duration_totals) > 0 else 'Unknown'
                top_duration_count = duration_totals.iloc[0] if len(duration_totals) > 0 else 0
                top_duration_pct = (top_duration_count / total_tickets * 100) if total_tickets > 0 else 0
                
                insights.append(f"⏱️ Duration Pattern: Most escalations are in '{top_duration}' duration ({top_duration_count:,} tickets, {top_duration_pct:.1f}% of total)")
                
                # Find priority with most escalations
                priority_totals = escalation_data.sum(axis=0).sort_values(ascending=False)
                top_priority = priority_totals.index[0] if len(priority_totals) > 0 else 'Unknown'
                top_priority_count = priority_totals.iloc[0] if len(priority_totals) > 0 else 0
                top_priority_pct = (top_priority_count / total_tickets * 100) if total_tickets > 0 else 0
                
                insights.append(f"🚨 Priority Distribution: '{top_priority.title()}' priority tickets lead escalations ({top_priority_count:,} tickets, {top_priority_pct:.1f}% of total)")
                
                # Critical duration analysis
                long_duration_buckets = ['10-30d', '1-2m', '2-3m', '3-6m', '6-12m', '>12m']
                long_duration_tickets = sum(escalation_data.loc[bucket].sum() 
                                          for bucket in long_duration_buckets 
                                          if bucket in escalation_data.index)
                long_duration_pct = (long_duration_tickets / total_tickets * 100) if total_tickets > 0 else 0
                
                if long_duration_pct > 20:
                    duration_concern = "high concern - many long-running escalations"
                elif long_duration_pct > 10:
                    duration_concern = "moderate concern - some extended escalations"
                else:
                    duration_concern = "good - most escalations resolved quickly"
                
                insights.append(f"📊 Escalation Health: {long_duration_tickets:,} tickets escalated >10 days ({long_duration_pct:.1f}% of total) - {duration_concern}")
            
            else:
                # Fallback insights for non-current views
                total_escalated = summary_stats.get('total_escalated_tickets', 0)
                currently_escalated = summary_stats.get('currently_escalated', 0)
                recently_resolved = summary_stats.get('recently_resolved', 0)
                avg_duration = summary_stats.get('avg_escalation_duration_hours', 0)
                
                insights.append(f"🔴 Current Status: {currently_escalated:,} tickets currently escalated, {recently_resolved:,} recently resolved")
                insights.append(f"⏱️ Average Duration: {avg_duration:.1f} hours typical escalation resolution time")
                insights.append(f"📈 Escalation Volume: {total_escalated:,} total escalated tickets in current selection")
            
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
            return ['current_escalated', 'recently_resolved', 'long_duration']
        
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
            
            # Prepare analysis data with case type mapping
            escalation_data, summary_stats = prepare_escalated_tickets_data(
                filtered_data, base_data['case_type_mapping'], view_type, time_period, selected_categories, stored_selections
            )
            
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

    # Update the modal callback to handle the missing import and ensure proper fallback
    @callback(
        [Output("escalated-modal-table-container", "children"),
         Output("escalated-modal-results-count", "children")],
        [Input("escalated-modal-priority-filter", "value"),
         Input("escalated-modal-duration-filter", "value"),
         Input("escalated-modal-casetype-filter", "value"),
         Input("escalated-modal-status-filter", "value")],  # Added Status filter input
        [State("escalated-modal-data-store", "data")],
        prevent_initial_call=True
    )
    def update_escalated_modal_table(priority_filter, duration_filter, casetype_filter, status_filter, stored_data):
        """
        Update the modal table based on filter selections including Status filter
        """
        if not stored_data:
            return html.Div("No data available"), "0 tickets"
        
        try:
            # Convert back to DataFrame
            df = pd.DataFrame(stored_data)
            
            # Apply Priority filter
            if priority_filter and priority_filter != 'all':
                df = df[df['Priority'] == priority_filter]
                
            # Apply Duration filter
            if duration_filter and duration_filter != 'all':
                df = df[df['EscalationDurationBucket'] == duration_filter]
                
            # Apply Case Type filter
            if casetype_filter and casetype_filter != 'all':
                df = df[df['CaseTypeName'] == casetype_filter]
            
            # Apply Status filter
            if status_filter and status_filter != 'all':
                df = df[df['WorkItemStatus'] == status_filter]
            
            # Convert date columns back to datetime
            if 'EscalatedOn' in df.columns:
                df['EscalatedOn'] = pd.to_datetime(df['EscalatedOn'])
            
            # Create filtered table
            table = create_filtered_escalated_table(df)
            results_text = f"{len(df):,} tickets"
            
            return table, results_text
            
        except Exception as e:
            print(f"❌ Error updating escalated modal table: {e}")
            return html.Div(f"Error filtering data: {str(e)}"), "Error"
        
    # Modal toggle callback
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
        Toggle modal window for escalated tickets details table
        """
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == "workflow-escalated-tickets-chart" and click_data:
            # Open modal with details table
            try:
                if selected_categories is None or len(selected_categories) == 0:
                    selected_categories = ['current_escalated', 'recently_resolved']
                
                # Get base data and prepare table
                base_data = get_escalated_tickets_base_data()
                filtered_data = apply_escalated_tickets_filters(base_data['work_items'], stored_selections)
                escalation_data, summary_stats = prepare_escalated_tickets_data(
                    filtered_data, base_data['case_type_mapping'], view_type or 'current', time_period or 30, selected_categories, stored_selections
                )
                
                # Get detailed data for table
                detailed_data = summary_stats.get('detailed_data', pd.DataFrame())
                
                # Create table content
                table_content = create_escalated_tickets_table(detailed_data)
                
                # Return modal opened with table content (not chart)
                return True, go.Figure()  # Empty figure since we're showing table
                
            except Exception as e:
                print(f"❌ Error creating modal table: {e}")
                return True, create_error_figure("Error loading escalated tickets details")
        
        elif triggered_id == "workflow-escalated-tickets-modal-close":
            # Close modal
            return False, go.Figure()
        
        return is_open, go.Figure()
    

    # Details modal callback
    @callback(
        [Output("workflow-escalated-details-modal", "is_open"),
         Output("workflow-escalated-details-content", "children")],
        [Input("workflow-escalated-details-btn", "n_clicks")],
        [State("workflow-escalated-details-modal", "is_open"),
         State("workflow-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    @monitor_performance("Escalated Details Modal Toggle")
    def toggle_escalated_details_modal(details_btn_clicks, is_open, stored_selections):
        """Handle opening of escalated tickets details modal with filterable table"""
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        if triggered_id == "workflow-escalated-details-btn" and details_btn_clicks:
            if not is_open:
                # Opening modal - generate fresh data
                try:
                    print("🔄 Generating fresh escalated tickets data for details modal...")
                    
                    # Get base data
                    base_data = get_escalated_tickets_base_data()
                    
                    # Apply filters
                    filtered_data = apply_escalated_tickets_filters(base_data['work_items'], stored_selections)
                    
                    # Prepare escalated data
                    escalation_data, summary_stats = prepare_escalated_tickets_data(
                        filtered_data, base_data['case_type_mapping'], 'current', 30, ['current_escalated'], stored_selections
                    )
                    
                    # Get detailed data
                    detailed_data = summary_stats.get('detailed_data', pd.DataFrame())
                    
                    # Create detailed table
                    detailed_table = create_escalated_tickets_table(detailed_data)
                    
                    print("✅ Opening escalated details modal with fresh data")
                    return True, detailed_table
                    
                except Exception as e:
                    print(f"❌ Error generating escalated details: {e}")
                    import traceback
                    traceback.print_exc()
                    error_content = html.Div([
                        html.H4("Error Loading Escalated Details", className="text-danger mb-3"),
                        html.P(f"Unable to load detailed breakdown: {str(e)}", className="text-muted")
                    ], className="text-center p-4")
                    return True, error_content
            else:
                # Closing modal
                return False, no_update
        
        return no_update, no_update
    
    # Close button callback for details modal
    @callback(
        Output("workflow-escalated-details-modal", "is_open", allow_duplicate=True),
        [Input("workflow-escalated-details-close-btn", "n_clicks")],
        [State("workflow-escalated-details-modal", "is_open")],
        prevent_initial_call=True
    )
    def close_escalated_details_modal(close_clicks, is_open):
        """Close the escalated details modal when close button is clicked"""
        if close_clicks and is_open:
            return False
        return no_update    