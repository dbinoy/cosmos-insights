from dash import callback, Input, Output, State, ctx, html, dcc, no_update
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance
from inflection import titleize
import dash_bootstrap_components as dbc
import copy

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
        # print(f"📊 Applying filters to escalated tickets data: {stored_selections}")
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrame and create explicit copy
        df_work_items = pd.DataFrame(work_items).copy()
        
        # print(f"📊 Initial escalated tickets data: {len(df_work_items)} tickets")
        
        # Clean placeholder dates (convert 1900-01-01T00:00:00.0000000 to NaT)
        date_columns = ['CreatedOn', 'ModifiedOn', 'ClosedOn', 'EscalatedOn']
        for col in date_columns:
            if col in df_work_items.columns:
                df_work_items[col] = pd.to_datetime(df_work_items[col], errors='coerce')
                # Replace dates that start with 1900-01-01 with NaT
                mask_1900 = df_work_items[col].dt.strftime('%Y-%m-%d').eq('1900-01-01')
                df_work_items.loc[mask_1900, col] = pd.NaT
                # print(f"🧹 Cleaned {mask_1900.sum()} placeholder dates from {col}")
        
        # Apply date range filters using CreatedOn (respecting Day_From and Day_To)
        day_from = stored_selections.get('Day_From')
        day_to = stored_selections.get('Day_To')
        
        if day_from:
            day_from_dt = pd.to_datetime(day_from)
            df_work_items = df_work_items[df_work_items['CreatedOn'] >= day_from_dt]
            # print(f"📅 After Day_From filter ({day_from}): {len(df_work_items)} tickets")
        
        if day_to:
            day_to_dt = pd.to_datetime(day_to)
            # Add one day to include the entire day_to date
            day_to_end = day_to_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df_work_items = df_work_items[df_work_items['CreatedOn'] <= day_to_end]
            # print(f"📅 After Day_To filter ({day_to}): {len(df_work_items)} tickets")
        
        # Apply categorical filters
        aor_filter = stored_selections.get('AOR', '').strip()
        if aor_filter:
            aor_values = [val.strip() for val in aor_filter.split(',') if val.strip()]
            if aor_values:
                df_work_items = df_work_items[df_work_items['AorShortName'].isin(aor_values)]
                # print(f"🏢 After AOR filter ({aor_values}): {len(df_work_items)} tickets")

        case_types_filter = stored_selections.get('CaseTypes', '').strip()
        if case_types_filter:
            case_types_values = [val.strip() for val in case_types_filter.split(',') if val.strip()]
            if case_types_values:
                df_work_items = df_work_items[df_work_items['WorkItemDefinitionShortCode'].isin(case_types_values)]
                # print(f"📋 After CaseTypes filter ({case_types_values}): {len(df_work_items)} tickets")

        status_filter = stored_selections.get('Status', '').strip()
        if status_filter:
            status_values = [val.strip() for val in status_filter.split(',') if val.strip()]
            if status_values:
                df_work_items = df_work_items[df_work_items['WorkItemStatus'].isin(status_values)]
                # print(f"📊 After Status filter ({status_values}): {len(df_work_items)} tickets")

        priority_filter = stored_selections.get('Priority', '').strip()
        if priority_filter:
            priority_values = [val.strip() for val in priority_filter.split(',') if val.strip()]
            if priority_values:
                df_work_items = df_work_items[df_work_items['Priority'].isin(priority_values)]
                # print(f"⚡ After Priority filter ({priority_values}): {len(df_work_items)} tickets")

        origins_filter = stored_selections.get('Origins', '').strip()
        if origins_filter:
            origins_values = [val.strip() for val in origins_filter.split(',') if val.strip()]
            if origins_values:
                df_work_items = df_work_items[df_work_items['CaseOrigin'].isin(origins_values)]
                # print(f"🌐 After Origins filter ({origins_values}): {len(df_work_items)} tickets")

        products_filter = stored_selections.get('Products', '').strip()
        if products_filter:
            products_values = [val.strip() for val in products_filter.split(',') if val.strip()]
            if products_values:
                df_work_items = df_work_items[df_work_items['Product'].isin(products_values)]
                # print(f"📦 After Products filter ({products_values}): {len(df_work_items)} tickets")

        features_filter = stored_selections.get('Features', '').strip()
        if features_filter:
            features_values = [val.strip() for val in features_filter.split(',') if val.strip()]
            if features_values:
                df_work_items = df_work_items[df_work_items['Feature'].isin(features_values)]
                # print(f"🔧 After Features filter ({features_values}): {len(df_work_items)} tickets")

        modules_filter = stored_selections.get('Modules', '').strip()
        if modules_filter:
            modules_values = [val.strip() for val in modules_filter.split(',') if val.strip()]
            if modules_values:
                df_work_items = df_work_items[df_work_items['Module'].isin(modules_values)]
                # print(f"🧩 After Modules filter ({modules_values}): {len(df_work_items)} tickets")

        issues_filter = stored_selections.get('Issues', '').strip()
        if issues_filter:
            issues_values = [val.strip() for val in issues_filter.split(',') if val.strip()]
            if issues_values:
                df_work_items = df_work_items[df_work_items['Issue'].isin(issues_values)]
                # print(f"🐛 After Issues filter ({issues_values}): {len(df_work_items)} tickets")

        # print(f"📊 Final filtered escalated tickets data: {len(df_work_items)} tickets")
        return df_work_items

    # Updated data preparation function to handle priority filtering
    def prepare_escalated_tickets_data(filtered_data, case_type_mapping, view_type='current', time_period=30, selected_categories=None, stored_selections=None, selected_priorities=None):
        """
        Prepare escalated tickets analysis data with proper duration buckets and case type names
        Updated to handle priority filtering for Escalated view
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        
        if selected_categories is None:
            selected_categories = ['current_escalated', 'recently_resolved']
        
        if stored_selections is None:
            stored_selections = {}
        
        try:
            df = filtered_data.copy()
            
            # Apply priority filtering for Escalated view
            if view_type == 'current' and selected_priorities is not None and len(selected_priorities) > 0:
                df = df[df['Priority'].isin(selected_priorities)]
                # print(f"🔽 Filtered to selected priorities: {selected_priorities}, {len(df)} tickets remaining")
            
            # Clean and format assignee names
            def format_assignee_name(assignee):
                if pd.isna(assignee) or assignee == '' or assignee.lower() == 'unassigned':
                    return 'Unassigned'
                cleaned = str(assignee).split('@')[0].replace('.', ' ').replace('_', ' ').replace('\r', ' ').replace('\n', ' ')
                return titleize(cleaned)
            
            df['AssigneeDisplay'] = df['AssignedTo'].apply(format_assignee_name)
            
            # Map case type codes to names using the dimension table
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
                
                if not is_escalated:
                    return 'other_escalated'
                
                # Check if ticket was escalated and is now closed (regardless of specific status)
                if not pd.isna(closed_on) and not pd.isna(escalated_on):
                    # This is a closed escalated ticket
                    return 'recently_resolved'
                
                # Currently open escalated tickets
                elif pd.isna(closed_on) and not pd.isna(escalated_on):
                    # Calculate days since escalation for long duration check
                    days_escalated = (datetime.now() - escalated_on).days
                    if days_escalated > 5:  # Using 5-day threshold
                        return 'long_duration'
                    else:
                        return 'current_escalated'
                
                # Escalated but missing escalation date (data quality issue)
                elif is_escalated:
                    return 'other_escalated'
                
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
            
            # Prepare visualization data based on view type
            if view_type == 'current':
                # Create cross-tabulation for stacked bar chart: Duration buckets x Priority
                priority_duration_cross = pd.crosstab(
                    df['EscalationDurationBucket'], 
                    df['Priority'], 
                    margins=False
                ).fillna(0)
                
                duration_order = ['<1h', '1-2h', '2-3h', '3-6h', '6-12h', '12-24h', 
                                '1-2d', '2-3d', '3-5d', '5-10d', '10-30d', '1-2m', 
                                '2-3m', '3-6m', '6-12m', '>12m', 'No Duration Data']
                
                existing_buckets = [bucket for bucket in duration_order if bucket in priority_duration_cross.index]
                priority_duration_cross = priority_duration_cross.reindex(existing_buckets, fill_value=0)
                
                visualization_data = priority_duration_cross
                
            else:
                # For other view types (trends, assignee, duration), return the processed DataFrame
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
                'selected_priorities': selected_priorities,  # Add selected priorities to summary
                'detailed_data': df,  # Store the full dataframe for all view types
                'stored_selections': stored_selections  # Add stored selections to summary stats
            }
            
            # print(f"📊 Prepared escalated tickets data: {len(visualization_data)} records for {view_type} view")
            return visualization_data, summary_stats
            
        except Exception as e:
            print(f"❌ Error preparing escalated tickets data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), {}
 
    @monitor_chart_performance("Escalated Tickets Chart")
    def create_escalated_tickets_chart(escalation_data, summary_stats, view_type='current', time_period=30, selected_categories=None, assignee_count=None):
        """
        Create different chart types based on view_type selection
        """
        if selected_categories is None:
            selected_categories = ['current_escalated', 'recently_resolved']
        
        if escalation_data.empty and view_type == 'current':
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
                # Stacked bar chart: Duration buckets x Priority (existing code)
                priority_colors = {
                    'critical': '#e74c3c',      # Red
                    'high': '#f39c12',          # Orange  
                    'medium': '#3498db',        # Blue
                    'low': '#95a5a6',           # Gray
                    'association-support': '#9b59b6',  # Purple
                    'in-house-support': '#1abc9c'      # Teal
                }
                
                priorities = escalation_data.columns.tolist()
                priority_order = ['critical', 'high', 'medium', 'low', 'association-support', 'in-house-support']
                
                sorted_priorities = []
                for priority in priority_order:
                    if priority in priorities:
                        sorted_priorities.append(priority)
                for priority in priorities:
                    if priority not in sorted_priorities:
                        sorted_priorities.append(priority)
                
                for priority in sorted_priorities:
                    if priority in escalation_data.columns:
                        color = priority_colors.get(priority.lower(), '#7f8c8d')
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
                
                fig.update_layout(
                    title={'text': title_text, 'x': 0.5, 'xanchor': 'center', 'font': {'size': 14, 'color': '#2c3e50'}},
                    xaxis_title="Escalation Duration",
                    yaxis_title="Number of Tickets",
                    height=450,
                    margin={'l': 60, 'r': 50, 't': 80, 'b': 120},
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
                    barmode='stack',
                    hovermode='closest',
                    xaxis=dict(tickangle=45, tickfont={'size': 10})
                )
                
            elif view_type == 'trends':
                # Time series chart showing escalation trends over time with dynamic granularity
                detailed_data = summary_stats.get('detailed_data', pd.DataFrame())
                if not detailed_data.empty:
                    # Determine the effective end date (either Day_To filter or current date)
                    stored_selections = summary_stats.get('stored_selections', {}) or stored_selections or {}
                    day_to = stored_selections.get('Day_To')
                    if day_to:
                        end_date = pd.to_datetime(day_to)
                    else:
                        end_date = pd.Timestamp.now().normalize()
                    
                    # Filter data based on time period selection
                    if time_period != 'all':
                        # Calculate start date based on period and end date
                        if time_period == 7:
                            start_date = end_date - pd.Timedelta(days=6)  # 7 days total including end date
                            granularity = 'D'  # Daily
                            date_format = '%Y-%m-%d'
                            title_period = f"Last {time_period} Days"
                        elif time_period == 30:
                            start_date = end_date - pd.Timedelta(days=29)  # 30 days total
                            granularity = 'D'  # Daily
                            date_format = '%Y-%m-%d'
                            title_period = f"Last {time_period} Days"
                        elif time_period == 90:
                            start_date = end_date - pd.Timedelta(days=89)  # 90 days total
                            granularity = 'W'  # Weekly
                            date_format = '%Y-W%U'
                            title_period = f"Last {time_period} Days"
                        
                        # Filter detailed_data to the calculated time window using EscalatedOn
                        mask = (detailed_data['EscalatedOn'] >= start_date) & (detailed_data['EscalatedOn'] <= end_date + pd.Timedelta(days=1))
                        filtered_detailed_data = detailed_data[mask].copy()
                    else:
                        # 'all' time period - determine granularity based on data span
                        filtered_detailed_data = detailed_data.copy()
                        if not filtered_detailed_data.empty and not filtered_detailed_data['EscalatedOn'].isna().all():
                            data_start = filtered_detailed_data['EscalatedOn'].min()
                            data_end = filtered_detailed_data['EscalatedOn'].max()
                            data_span_days = (data_end - data_start).days
                            
                            if data_span_days <= 365:  # Less than or equal to 1 year
                                granularity = 'W'  # Weekly
                                date_format = '%Y-W%U'
                            else:  # More than 1 year
                                granularity = 'M'  # Monthly
                                date_format = '%Y-%m'
                            title_period = "All Time"
                        else:
                            granularity = 'W'
                            date_format = '%Y-W%U'
                            title_period = "All Time"
                    
                    if not filtered_detailed_data.empty:
                        # Create time period column based on granularity
                        if granularity == 'D':
                            filtered_detailed_data['TimePeriod'] = filtered_detailed_data['EscalatedOn'].dt.strftime(date_format)
                        elif granularity == 'W':
                            filtered_detailed_data['TimePeriod'] = filtered_detailed_data['EscalatedOn'].dt.to_period('W').astype(str)
                        elif granularity == 'M':
                            filtered_detailed_data['TimePeriod'] = filtered_detailed_data['EscalatedOn'].dt.to_period('M').astype(str)
                        
                        # Group by time period and escalation category
                        trends_data = filtered_detailed_data.groupby(['TimePeriod', 'EscalationCategory']).size().unstack(fill_value=0)
                        
                        # Sort the time periods properly
                        if granularity == 'D':
                            # For daily, convert back to datetime for proper sorting
                            trends_data.index = pd.to_datetime(trends_data.index)
                            trends_data = trends_data.sort_index()
                            # Convert back to string for display
                            trends_data.index = trends_data.index.strftime('%Y-%m-%d')
                        elif granularity == 'W':
                            # For weekly, sort by converting to period and back
                            period_index = pd.to_datetime([pd.Period(p).start_time for p in trends_data.index])
                            trends_data.index = period_index
                            trends_data = trends_data.sort_index()
                            trends_data.index = [f"Week of {d.strftime('%Y-%m-%d')}" for d in trends_data.index]
                        elif granularity == 'M':
                            # For monthly, sort by converting to period and back
                            period_index = pd.to_datetime([pd.Period(p).start_time for p in trends_data.index])
                            trends_data.index = period_index
                            trends_data = trends_data.sort_index()
                            trends_data.index = [d.strftime('%Y-%m') for d in trends_data.index]
                        
                        # Define colors for all escalation categories
                        category_colors = {
                            'current_escalated': '#e74c3c',      # Red - Currently escalated
                            'recently_resolved': '#27ae60',      # Green - Recently resolved escalations
                            'long_duration': '#f39c12',         # Orange - Long duration escalations
                            'other_escalated': '#95a5a6'        # Gray - Other escalated tickets
                        }
                        
                        category_names = {
                            'current_escalated': 'Currently Escalated',
                            'recently_resolved': 'Recently Resolved',
                            'long_duration': 'Long Duration',
                            'other_escalated': 'Other Escalated'
                        }
                        
                        # Add traces for all available categories (not just selected ones for trends)
                        for category in trends_data.columns:
                            if category in category_colors:
                                fig.add_trace(go.Scatter(
                                    name=category_names.get(category, category.replace('_', ' ').title()),
                                    x=trends_data.index,
                                    y=trends_data[category],
                                    mode='lines+markers',
                                    line=dict(color=category_colors.get(category, '#7f8c8d'), width=2),
                                    marker=dict(size=6),
                                    hovertemplate=f'<b>{category_names.get(category, category.replace("_", " ").title())}</b><br>' +
                                                f'Period: %{{x}}<br>' +
                                                f'Escalations: %{{y}}<br>' +
                                                '<extra></extra>',
                                    visible=True if category in selected_categories else 'legendonly'  # Show/hide based on selection
                                ))
                        
                        # Determine granularity label for title
                        granularity_label = {
                            'D': 'Daily',
                            'W': 'Weekly', 
                            'M': 'Monthly'
                        }.get(granularity, 'Weekly')
                        
                        title_text = f"Escalation Trends - {granularity_label} ({title_period}) - {len(filtered_detailed_data):,} total tickets"
                        
                        fig.update_layout(
                            title={'text': title_text, 'x': 0.5, 'xanchor': 'center', 'font': {'size': 14, 'color': '#2c3e50'}},
                            xaxis_title=f"Time Period ({granularity_label})",
                            yaxis_title="Number of Escalations",
                            height=450,
                            margin={'l': 60, 'r': 50, 't': 80, 'b': 60},
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            hovermode='x unified',
                            legend=dict(
                                orientation="h", 
                                yanchor="bottom", 
                                y=1.02, 
                                xanchor="center", 
                                x=0.5, 
                                font=dict(size=10)
                            )
                        )
                        
                        # Adjust x-axis based on granularity
                        if granularity == 'D':
                            fig.update_layout(xaxis=dict(tickangle=45, tickfont={'size': 10}))
                        elif granularity == 'W':
                            fig.update_layout(xaxis=dict(tickangle=45, tickfont={'size': 10}))
                        else:  # Monthly
                            fig.update_layout(xaxis=dict(tickangle=0, tickfont={'size': 10}))
                
            elif view_type == 'assignee':
                # Bar chart showing escalations by assignee
                detailed_data = summary_stats.get('detailed_data', pd.DataFrame())
                if not detailed_data.empty:
                    # Get top 15 assignees by escalation count
                    assignee_counts = detailed_data['AssigneeDisplay'].value_counts()
                    if assignee_count == 'all' or assignee_count is None:
                        top_assignees = assignee_counts
                    else:
                        top_assignees = assignee_counts.head(int(assignee_count))      
                    fig.add_trace(go.Bar(
                        x=top_assignees.index,
                        y=top_assignees.values,
                        marker_color='#3498db',
                        hovertemplate='<b>%{x}</b><br>Escalated Tickets: %{y}<br><extra></extra>'
                    ))                                      
                    
                    title_text = f"Escalated Tickets by Assignee (Top {len(top_assignees)})"
                    
                    fig.update_layout(
                        title={'text': title_text, 'x': 0.5, 'xanchor': 'center', 'font': {'size': 14, 'color': '#2c3e50'}},
                        xaxis_title="Assignee",
                        yaxis_title="Number of Escalated Tickets",
                        height=450,
                        margin={'l': 60, 'r': 50, 't': 80, 'b': 120},
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis=dict(tickangle=45, tickfont={'size': 10})
                    )
                
            elif view_type == 'duration':
                # Distribution chart showing duration buckets
                detailed_data = summary_stats.get('detailed_data', pd.DataFrame())
                if not detailed_data.empty:
                    # Count tickets by duration bucket
                    duration_counts = detailed_data['EscalationDurationBucket'].value_counts()
                    
                    # Ensure proper ordering
                    duration_order = ['<1h', '1-2h', '2-3h', '3-6h', '6-12h', '12-24h', 
                                    '1-2d', '2-3d', '3-5d', '5-10d', '10-30d', '1-2m', 
                                    '2-3m', '3-6m', '6-12m', '>12m', 'No Duration Data']
                    
                    ordered_durations = [d for d in duration_order if d in duration_counts.index]
                    ordered_counts = [duration_counts[d] for d in ordered_durations]
                    
                    # Color code based on severity (longer = more red)
                    colors = ['#27ae60' if i < 6 else '#f39c12' if i < 11 else '#e74c3c' 
                            for i in range(len(ordered_durations))]
                    
                    fig.add_trace(go.Bar(
                        x=ordered_durations,
                        y=ordered_counts,
                        marker_color=colors,
                        hovertemplate='<b>%{x} Duration</b><br>' +
                                    'Tickets: %{y}<br>' +
                                    'Percentage: %{customdata:.1f}%<br>' +
                                    '<extra></extra>',
                        customdata=[(count/sum(ordered_counts)*100) for count in ordered_counts]
                    ))
                    
                    title_text = f"Escalation Duration Distribution ({len(detailed_data):,} tickets)"
                    
                    fig.update_layout(
                        title={'text': title_text, 'x': 0.5, 'xanchor': 'center', 'font': {'size': 14, 'color': '#2c3e50'}},
                        xaxis_title="Duration Bucket",
                        yaxis_title="Number of Tickets",
                        height=450,
                        margin={'l': 60, 'r': 50, 't': 80, 'b': 120},
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        xaxis=dict(tickangle=45, tickfont={'size': 10})
                    )
            
            # If no data available for non-current views
            if view_type != 'current' and fig.data == ():
                fig.add_annotation(
                    text=f"No data available for {view_type} view with current filters",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=16, color="gray")
                )
                fig.update_layout(
                    title={'text': f"Escalated Tickets - {view_type.title()} View", 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16, 'color': '#2c3e50'}},
                    height=450,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
            
            # print(f"📊 Created escalated tickets chart: {view_type} view")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating escalated tickets chart: {e}")
            import traceback
            traceback.print_exc()
            return create_error_figure("Error creating escalated tickets chart")
    
    # @monitor_chart_performance("Enlarged Escalated Tickets Chart")
    # def create_enlarged_escalated_tickets_chart(original_figure):
    #     """
    #     Create an enlarged version of the escalated tickets chart for modal display
    #     """
    #     if not original_figure:
    #         return html.Div("No chart data available", className="text-center p-4")
    #     try:
    #         enlarged_fig = go.Figure(original_figure)
    #         enlarged_fig.update_layout(
    #             height=650,
    #             margin={'l': 80, 'r': 60, 't': 100, 'b': 140},
    #             title={
    #                 **enlarged_fig.layout.title,
    #                 'font': {'size': 20, 'color': '#2c3e50'}
    #             }
    #         )
    #         return dcc.Graph(
    #             figure=enlarged_fig,
    #             config={
    #                 'displayModeBar': True,
    #                 'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
    #                 'displaylogo': False,
    #                 'toImageButtonOptions': {
    #                     'format': 'png',
    #                     'filename': 'workflow_escalated_tickets_chart',
    #                     'height': 650,
    #                     'width': 1200,
    #                     'scale': 1
    #                 }
    #             },
    #             style={'height': '650px'}
    #         )
    #     except Exception as e:
    #         print(f"❌ Error creating enlarged escalated tickets chart: {e}")
    #         return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")

    @monitor_chart_performance("Enlarged Escalated Tickets Chart")
    def create_enlarged_escalated_tickets_chart(original_figure):
        """
        Create an enlarged version of the escalated tickets chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        try:
            # Deep copy the original figure to avoid mutating the dashboard chart
            enlarged_fig = copy.deepcopy(original_figure)
            # Update layout for enlarged modal display
            enlarged_fig['layout'].update({
                'height': 650,
                'margin': {'l': 80, 'r': 60, 't': 100, 'b': 140},
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}
                },
                'xaxis': {
                    **enlarged_fig['layout'].get('xaxis', {}),
                    'tickfont': {'size': 12},
                    'title': {
                        **enlarged_fig['layout'].get('xaxis', {}).get('title', {}),
                        'font': {'size': 14}
                    }
                },
                'yaxis': {
                    **enlarged_fig['layout'].get('yaxis', {}),
                    'tickfont': {'size': 12},
                    'title': {
                        **enlarged_fig['layout'].get('yaxis', {}).get('title', {}),
                        'font': {'size': 14}
                    }
                },
                'legend': {
                    **enlarged_fig['layout'].get('legend', {}),
                    'font': {'size': 12}
                }
            })
            # Optionally, update traces for better visibility
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') == 'bar':
                        trace.update({
                            'marker': {
                                **trace.get('marker', {}),
                                'line': {'width': 1, 'color': 'white'}
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
                        'filename': 'workflow_escalated_tickets_chart',
                        'height': 650,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '650px'}
            )
        except Exception as e:
            print(f"❌ Error creating enlarged escalated tickets chart: {e}")
            return html.Div(f"Error displaying chart: {str(e)}", className="text-center p-4 text-danger")
           
    def create_escalated_tickets_table(detailed_data):
        """
        Create a detailed table for the modal showing all escalated tickets with filtering and pagination
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
            
            # Create filter controls row
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
                ], width=2),
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
                ], width=2),
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
                    html.Label("Page Size:", className="form-label mb-1", style={'fontSize': '12px', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id="escalated-modal-pagesize-filter",
                        options=[
                            {'label': '25 per page', 'value': 25},
                            {'label': '50 per page', 'value': 50},
                            {'label': '100 per page', 'value': 100},
                            {'label': '200 per page', 'value': 200}
                        ],
                        value=50,
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
            
            # Pagination controls row
            pagination_controls = dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.ButtonGroup([
                            dbc.Button("First", id="escalated-modal-first-btn", size="sm", outline=True, color="primary", disabled=True),
                            dbc.Button("Previous", id="escalated-modal-prev-btn", size="sm", outline=True, color="primary", disabled=True),
                        ]),
                        html.Span(id="escalated-modal-page-info", className="mx-3", style={'fontSize': '12px', 'fontWeight': '500'}),
                        dbc.ButtonGroup([
                            dbc.Button("Next", id="escalated-modal-next-btn", size="sm", outline=True, color="primary"),
                            dbc.Button("Last", id="escalated-modal-last-btn", size="sm", outline=True, color="primary"),
                        ])
                    ], className="d-flex align-items-center justify-content-center")
                ], width=12)
            ], className="mb-2")
            
            # Create the initial table with first page
            initial_table = create_paginated_escalated_table(df_sorted, page=1, page_size=50)
            
            return html.Div([
                # Header with summary
                html.P([
                    f"Total: {len(df_sorted):,} escalated tickets"
                ], className="text-muted mb-3"),
                
                # Filter controls
                filter_controls,
                
                # Pagination controls
                pagination_controls,
                
                # Table container with initial data
                html.Div(id="escalated-modal-table-container", children=initial_table),
                
                # Store the data and pagination state
                dcc.Store(id="escalated-modal-data-store", data=df_sorted.to_dict('records')),
                dcc.Store(id="escalated-modal-pagination-store", data={'current_page': 1, 'page_size': 50, 'total_pages': 1})
            ], className="p-3")
            
        except Exception as e:
            print(f"❌ Error creating escalated tickets table: {e}")
            return html.Div([
                html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
            ], className="text-center p-4")

    def create_paginated_escalated_table(filtered_df, page=1, page_size=50):
        """
        Create paginated table from filtered data
        """
        if filtered_df.empty:
            return html.Div("No tickets match the current filter selection.", className="text-center text-muted p-4")
        
        # Calculate pagination
        total_records = len(filtered_df)
        total_pages = max(1, (total_records + page_size - 1) // page_size)  # Ceiling division
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_records)
        
        # Get current page data
        page_df = filtered_df.iloc[start_idx:end_idx]
        
        # Create table rows
        table_rows = []
        for i, row in page_df.iterrows():
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
            title_text = title_text.replace('\n', ' ').replace('\r', ' ').strip()
            if len(title_text) > 200:
                title_text = title_text[:197] + "..."
            
            table_rows.append(
                html.Tr([
                    # Ticket ID with Title hover tooltip
                    html.Td([
                        html.Span(
                            f"#{row['WorkItemId']}", 
                            title=title_text,
                            style={
                                'fontWeight': 'bold', 
                                'fontSize': '12px',
                                'cursor': 'help',
                                'textDecoration': 'underline',
                                'textDecorationStyle': 'dotted'
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
        
        # Pagination info
        pagination_info = html.Div([
            html.Small([
                f"Showing {start_idx + 1:,}-{end_idx:,} of {total_records:,} tickets ",
                f"(Page {page:,} of {total_pages:,})"
            ], className="text-muted", style={'fontSize': '11px'})
        ], className="mt-2 text-center")
        
        return html.Div([
            html.Div(table_component, style={'maxHeight': '450px', 'overflowY': 'auto', 'border': '1px solid #dee2e6', 'borderRadius': '8px'}),
            pagination_info
        ])

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

    @callback(
        Output("workflow-escalated-categories-dropdown", "value"),
        [Input("btn-escalated-active", "n_clicks"),
         Input("btn-escalated-critical", "n_clicks"), 
         Input("btn-escalated-all", "n_clicks"),
         Input("workflow-escalated-view-dropdown", "value")],  # Add view dropdown as input
        prevent_initial_call=True
    )
    def handle_escalated_quick_select(btn_active, btn_critical, btn_all, view_type):
        """Handle quick select buttons for escalated ticket categories - only active for Trends view"""
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Only process quick select buttons when in Trends view
        if view_type != 'trends':
            return ['current_escalated']  # Default selection for non-Trends views
        
        if triggered_id == "btn-escalated-active":
            return ['current_escalated']
        elif triggered_id == "btn-escalated-critical":
            return ['current_escalated', 'long_duration']
        elif triggered_id == "btn-escalated-all":
            return ['current_escalated', 'recently_resolved', 'long_duration']
        elif triggered_id == "workflow-escalated-view-dropdown" and view_type == 'trends':
            return ['current_escalated', 'recently_resolved']  # Default for Trends view
        
        return ['current_escalated']
    
    @callback(
        [Output("workflow-escalated-trends-controls", "style"),
        Output("workflow-escalated-current-controls", "style"),
        Output("workflow-escalated-assignee-controls", "style")],
        Input("workflow-escalated-view-dropdown", "value"),
        prevent_initial_call=False
    )
    def toggle_view_specific_controls(view_type):
        if view_type == 'trends':
            return {'display': 'flex', 'width': '100%'}, {'display': 'none'}, {'display': 'none'}
        elif view_type == 'current':
            return {'display': 'none'}, {'display': 'flex', 'width': '100%'}, {'display': 'none'}
        elif view_type == 'assignee':
            return {'display': 'none'}, {'display': 'none'}, {'display': 'flex', 'width': '100%'}
        else:
            return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
        
    @callback(
        Output("workflow-escalated-priorities-dropdown", "options"),
        [Input("workflow-filtered-query-store", "data"),
         Input("workflow-escalated-view-dropdown", "value")],
        prevent_initial_call=False
    )
    def populate_escalated_priorities_dropdown(stored_selections, view_type):
        """
        Populate the priorities dropdown based on current filter selections
        Only active when Escalated view is selected
        """
        if view_type != 'current':
            return []
        
        try:
            # Get base data
            base_data = get_escalated_tickets_base_data()
            
            # Apply current filters to get available priorities
            filtered_data = apply_escalated_tickets_filters(base_data['work_items'], stored_selections)
            
            if filtered_data.empty:
                return []
            
            # Get unique priorities from filtered data
            available_priorities = sorted([p for p in filtered_data['Priority'].dropna().unique() if str(p).strip()])
            
            # Create dropdown options
            priority_options = [
                {'label': f'🔸 {priority.title()}', 'value': priority}
                for priority in available_priorities
            ]
            
            # print(f"📊 Populated priorities dropdown with {len(priority_options)} options")
            return priority_options
            
        except Exception as e:
            print(f"❌ Error populating priorities dropdown: {e}")
            return []
                
    # Main update callback
    @callback(
        [Output("workflow-escalated-tickets-chart", "figure"),
         Output("workflow-escalated-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
         Input("workflow-escalated-view-dropdown", "value"),
         Input("workflow-escalated-period-dropdown", "value"),
         Input("workflow-escalated-categories-dropdown", "value"),
         Input("workflow-escalated-priorities-dropdown", "value"),
         Input("workflow-escalated-assignee-count-dropdown", "value")],  # Add priorities dropdown
        prevent_initial_call=False
    )
    @monitor_performance("Escalated Tickets Chart Update")
    def update_escalated_tickets_chart(stored_selections, view_type, time_period, selected_categories, selected_priorities, assignee_count):
        """
        Update escalated tickets chart based on filter selections and display options
        """
        try:
            # Handle None or invalid values (controls may be hidden)
            if view_type is None:
                view_type = 'current'
            
            # For non-Trends views, use default values since controls are hidden
            if view_type != 'trends':
                time_period = 30  # Default period for non-Trends views
                selected_categories = ['current_escalated', 'recently_resolved']  # Default categories
            else:
                # For Trends view, handle None values from hidden-then-shown controls
                if time_period is None:
                    time_period = 30
                if selected_categories is None or len(selected_categories) == 0:
                    selected_categories = ['current_escalated', 'recently_resolved']
            
            # Handle priorities selection for Escalated view
            if view_type == 'current':
                # If no priorities selected, treat as "all priorities"
                if selected_priorities is None or len(selected_priorities) == 0:
                    selected_priorities = None  # Will be handled in data preparation
            else:
                selected_priorities = None  # Not relevant for other views
            
            # print(f"🔄 Updating escalated tickets analysis: view = {view_type}, period = {time_period}, categories = {selected_categories}, priorities = {selected_priorities}")
            
            # Get base data
            base_data = get_escalated_tickets_base_data()
            
            # Apply filters
            filtered_data = apply_escalated_tickets_filters(base_data['work_items'], stored_selections)
            
            # Prepare analysis data with case type mapping
            escalation_data, summary_stats = prepare_escalated_tickets_data(
                filtered_data, base_data['case_type_mapping'], view_type, time_period, selected_categories, stored_selections, selected_priorities
            )

            # Create visualization
            fig = create_escalated_tickets_chart(escalation_data, summary_stats, view_type, time_period, selected_categories, assignee_count)
            
            # Generate insights
            insights = generate_escalated_tickets_insights(escalation_data, summary_stats, view_type, selected_categories)

            # print(f"✅ Escalated tickets analysis updated: {len(escalation_data)} records displayed")
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
               
    # Enhanced modal callback to handle pagination
    @callback(
        [Output("escalated-modal-table-container", "children"),
         Output("escalated-modal-results-count", "children"),
         Output("escalated-modal-pagination-store", "data"),
         Output("escalated-modal-page-info", "children"),
         Output("escalated-modal-first-btn", "disabled"),
         Output("escalated-modal-prev-btn", "disabled"),
         Output("escalated-modal-next-btn", "disabled"),
         Output("escalated-modal-last-btn", "disabled")],
        [Input("escalated-modal-priority-filter", "value"),
         Input("escalated-modal-duration-filter", "value"),
         Input("escalated-modal-casetype-filter", "value"),
         Input("escalated-modal-status-filter", "value"),
         Input("escalated-modal-pagesize-filter", "value"),
         Input("escalated-modal-first-btn", "n_clicks"),
         Input("escalated-modal-prev-btn", "n_clicks"),
         Input("escalated-modal-next-btn", "n_clicks"),
         Input("escalated-modal-last-btn", "n_clicks")],
        [State("escalated-modal-data-store", "data"),
         State("escalated-modal-pagination-store", "data")],
        prevent_initial_call=True
    )
    def update_escalated_modal_table_with_pagination(priority_filter, duration_filter, casetype_filter, status_filter, page_size,
                                                   first_clicks, prev_clicks, next_clicks, last_clicks,
                                                   stored_data, pagination_state):
        """
        Update the modal table with filtering and pagination
        """
        if not stored_data:
            return (html.Div("No data available"), "0 tickets", 
                   {'current_page': 1, 'page_size': 50, 'total_pages': 1}, 
                   "Page 1 of 1", True, True, True, True)
        
        try:
            # Convert back to DataFrame
            df = pd.DataFrame(stored_data)
            
            # Apply filters
            if priority_filter and priority_filter != 'all':
                df = df[df['Priority'] == priority_filter]
                
            if duration_filter and duration_filter != 'all':
                df = df[df['EscalationDurationBucket'] == duration_filter]
                
            if casetype_filter and casetype_filter != 'all':
                df = df[df['CaseTypeName'] == casetype_filter]
            
            if status_filter and status_filter != 'all':
                df = df[df['WorkItemStatus'] == status_filter]
            
            # Convert date columns back to datetime
            if 'EscalatedOn' in df.columns:
                df['EscalatedOn'] = pd.to_datetime(df['EscalatedOn'])
            
            # Handle pagination
            triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            current_page = pagination_state.get('current_page', 1) if pagination_state else 1
            current_page_size = page_size or 50
            
            # Calculate total pages
            total_records = len(df)
            total_pages = max(1, (total_records + current_page_size - 1) // current_page_size)
            
            # Handle pagination button clicks
            if triggered_id == "escalated-modal-first-btn":
                current_page = 1
            elif triggered_id == "escalated-modal-prev-btn":
                current_page = max(1, current_page - 1)
            elif triggered_id == "escalated-modal-next-btn":
                current_page = min(total_pages, current_page + 1)
            elif triggered_id == "escalated-modal-last-btn":
                current_page = total_pages
            elif triggered_id in ["escalated-modal-priority-filter", "escalated-modal-duration-filter", 
                                "escalated-modal-casetype-filter", "escalated-modal-status-filter"]:
                # Reset to first page when filters change
                current_page = 1
            elif triggered_id == "escalated-modal-pagesize-filter":
                # Adjust current page when page size changes to maintain roughly same position
                if pagination_state:
                    old_page_size = pagination_state.get('page_size', 50)
                    old_start_record = (current_page - 1) * old_page_size + 1
                    current_page = max(1, (old_start_record + current_page_size - 1) // current_page_size)
            
            # Ensure current page is within bounds
            current_page = max(1, min(current_page, total_pages))
            
            # Create paginated table
            table = create_paginated_escalated_table(df, current_page, current_page_size)
            results_text = f"{len(df):,} tickets"
            
            # Update pagination state
            new_pagination_state = {
                'current_page': current_page,
                'page_size': current_page_size,
                'total_pages': total_pages
            }
            
            # Page info
            page_info = f"Page {current_page:,} of {total_pages:,}"
            
            # Button states
            first_disabled = current_page <= 1
            prev_disabled = current_page <= 1
            next_disabled = current_page >= total_pages
            last_disabled = current_page >= total_pages
            
            return (table, results_text, new_pagination_state, page_info, 
                   first_disabled, prev_disabled, next_disabled, last_disabled)
            
        except Exception as e:
            print(f"❌ Error updating escalated modal table with pagination: {e}")
            return (html.Div(f"Error filtering data: {str(e)}"), "Error", 
                   {'current_page': 1, 'page_size': 50, 'total_pages': 1}, 
                   "Error", True, True, True, True)
       
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
                    # print("🔄 Generating fresh escalated tickets data for details modal...")
                    
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
                    
                    # print("✅ Opening escalated details modal with fresh data")
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
    
    @callback(
        [Output("workflow-chart-modal", "is_open", allow_duplicate=True),
        Output("workflow-modal-chart-content", "children", allow_duplicate=True)],
        [Input("workflow-escalated-tickets-chart-wrapper", "n_clicks")],
        [State("workflow-chart-modal", "is_open"),
        State("workflow-escalated-tickets-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Escalated Tickets Enlarged Modal Toggle")
    def toggle_escalated_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of the shared enlarged chart modal for escalated tickets chart
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None

        if triggered_id == "workflow-escalated-tickets-chart-wrapper" and chart_wrapper_clicks and not is_open:
            if not chart_figure or not chart_figure.get('data'):
                return no_update, no_update
            enlarged_chart = create_enlarged_escalated_tickets_chart(chart_figure)
            return True, enlarged_chart

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