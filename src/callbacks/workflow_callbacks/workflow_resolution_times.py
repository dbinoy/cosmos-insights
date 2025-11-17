from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import numpy as np
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

@monitor_query_performance("Resolution Times Base Data")
def get_resolution_times_base_data():
    """
    Fetch base data for resolution times analysis
    Uses FACT tables to get comprehensive duration and resolution data
    """
    
    queries = {
        # Get work items with resolution information - using FACT_WorkFlowItems
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
                w.CaseReason,
                w.Feature,
                w.Issue,
                w.Module,
                w.Priority,
                w.Product,
                -- Calculate resolution time in minutes using FACT table data
                CASE 
                    WHEN w.ClosedOn IS NOT NULL AND w.CreatedOn IS NOT NULL
                    THEN DATEDIFF(MINUTE, w.CreatedOn, w.ClosedOn)
                    ELSE NULL
                END as ResolutionTimeMinutes
            FROM [consumable].[Fact_WorkFlowItems] w
            WHERE w.ClosedOn IS NOT NULL  -- Only include resolved tickets
                AND w.CreatedOn IS NOT NULL
                AND DATEDIFF(MINUTE, w.CreatedOn, w.ClosedOn) > 0  -- Valid resolution times only
        """,
        
        # Get detailed duration summary - using FACT_DurationSummary for accurate metrics
        "duration_summary": """
            SELECT 
                ds.WorkItemId,
                ds.OpenToClosed_Min,
                ds.OpenToEscalated_Min,
                ds.OpenToInProgress_Min,
                ds.OpenToResolved_Min,
                ds.OpenToOnHold_Min,
                ds.OpenToFirstCallClosed_Min,
                ds.OpenToScheduled_Min,
                ds.OpenToCanceled_Min,
                ds.OpenToSelfFix_Min
            FROM [consumable].[Fact_DurationSummary] ds
            WHERE ds.OpenToClosed_Min IS NOT NULL 
                AND ds.OpenToClosed_Min > 0
                AND ds.OpenToClosed_Min < 525600  -- Less than 1 year in minutes
        """,
        
        # Get status transitions for workflow analysis - using FACT_StatusTransitions
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
            WHERE st.DurationMinutes IS NOT NULL
                AND st.DurationMinutes >= 0
        """
    }

    return run_queries(queries, 'workflow', len(queries))

def apply_resolution_times_filters(work_items, duration_summary, stored_selections):
    """
    Apply filters to resolution times data using pandas
    Same pattern as other workflow components
    """
    print(f"🔍 Applying resolution times filters: {stored_selections}")
    if not stored_selections:
        stored_selections = {}
    
    # Convert to DataFrames and create explicit copies
    df_work_items = pd.DataFrame(work_items).copy()
    df_duration_summary = pd.DataFrame(duration_summary).copy()
    
    print(f"📊 Starting resolution times filtering: {len(df_work_items)} work item records")
    
    if df_work_items.empty:
        return df_work_items, df_duration_summary
    
    # Parse filter values (same logic as other components)
    selected_aor = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('AOR', '').split(', ') if item.strip("'")]
    selected_case_types = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('CaseTypes', '').split(', ') if item.strip("'")]
    selected_priority = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Priority', '').split(', ') if item.strip("'")]
    selected_origins = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Origins', '').split(', ') if item.strip("'")]
    selected_products = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Products', '').split(', ') if item.strip("'")]
    start_date = stored_selections.get('StartDate')
    end_date = stored_selections.get('EndDate')
    
    # Parse dates
    if not df_work_items.empty:
        df_work_items['CreatedOn'] = pd.to_datetime(df_work_items['CreatedOn'], errors='coerce')
        df_work_items['ClosedOn'] = pd.to_datetime(df_work_items['ClosedOn'], errors='coerce')
        df_work_items = df_work_items.dropna(subset=['CreatedOn', 'ClosedOn']).copy()

        # Apply date range filter if specified
        if start_date and end_date:
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df_work_items = df_work_items.loc[
                    (df_work_items['CreatedOn'] >= start_dt) & 
                    (df_work_items['CreatedOn'] <= end_dt)
                ].copy()
                print(f"📅 Date filter applied: {len(df_work_items)} work item records")
            except Exception as e:
                print(f"❌ Error applying date filter: {e}")
    
    # Apply other filters
    if selected_aor and len(selected_aor) > 0 and "All" not in selected_aor:
        df_work_items = df_work_items.loc[df_work_items['AorShortName'].isin(selected_aor)].copy()
        print(f"🎯 AOR filter applied: {len(df_work_items)} records")

    if selected_case_types and len(selected_case_types) > 0 and "All" not in selected_case_types:
        df_work_items = df_work_items.loc[df_work_items['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
        print(f"📋 Case Type filter applied: {len(df_work_items)} records")

    if selected_products and len(selected_products) > 0 and "All" not in selected_products:
        df_work_items = df_work_items.loc[df_work_items['Product'].isin(selected_products)].copy()
        print(f"🛍️ Product filter applied: {len(df_work_items)} records")

    if selected_priority and len(selected_priority) > 0 and "All" not in selected_priority:
        df_work_items = df_work_items.loc[df_work_items['Priority'].isin(selected_priority)].copy()
        print(f"⚡ Priority filter applied: {len(df_work_items)} records")
    
    # Filter duration summary to match filtered work items
    if not df_duration_summary.empty and not df_work_items.empty:
        filtered_work_item_ids = set(df_work_items['WorkItemId'].tolist())
        df_duration_summary = df_duration_summary[
            df_duration_summary['WorkItemId'].isin(filtered_work_item_ids)
        ].copy()
        print(f"📊 Duration summary filtered: {len(df_duration_summary)} records")
    
    return df_work_items, df_duration_summary

@monitor_performance("Resolution Times Data Preparation")
def prepare_resolution_times_data(filtered_work_items, filtered_duration_summary, status_transitions_data):
    """
    Prepare comprehensive resolution times data for multiple visualization types
    Uses FACT_DurationSummary for accurate metrics
    """
    if filtered_work_items.empty or filtered_duration_summary.empty:
        return pd.DataFrame(), {}, {}
    
    try:
        # Merge work items with duration summary for comprehensive analysis
        merged_df = filtered_work_items.merge(
            filtered_duration_summary, 
            on='WorkItemId', 
            how='inner'
        )
        
        # Use FACT_DurationSummary data as primary source (more accurate)
        merged_df['ResolutionTimeMinutes'] = merged_df['OpenToClosed_Min']
        merged_df['ResolutionTimeHours'] = merged_df['ResolutionTimeMinutes'] / 60
        merged_df['ResolutionTimeDays'] = merged_df['ResolutionTimeHours'] / 24
        
        # Remove outliers and invalid data
        df = merged_df[
            (merged_df['ResolutionTimeMinutes'] > 0) & 
            (merged_df['ResolutionTimeMinutes'] < 525600)  # Less than 1 year
        ].copy()
        
        # Categorize resolution times for distribution analysis
        def categorize_resolution_time(minutes):
            if pd.isna(minutes) or minutes <= 0:
                return 'Invalid'
            elif minutes <= 15:
                return '≤15 min'
            elif minutes <= 60:
                return '15-60 min'
            elif minutes <= 240:  # 4 hours
                return '1-4 hours'
            elif minutes <= 1440:  # 24 hours
                return '4-24 hours'
            elif minutes <= 10080:  # 7 days
                return '1-7 days'
            else:
                return '7+ days'
        
        df['ResolutionCategory'] = df['ResolutionTimeMinutes'].apply(categorize_resolution_time)
        
        # Calculate comprehensive summary statistics
        summary_stats = {
            'total_resolved': len(df),
            'mean_minutes': df['ResolutionTimeMinutes'].mean(),
            'median_minutes': df['ResolutionTimeMinutes'].median(),
            'mean_hours': df['ResolutionTimeHours'].mean(),
            'median_hours': df['ResolutionTimeHours'].median(),
            'p75_hours': df['ResolutionTimeHours'].quantile(0.75),
            'p90_hours': df['ResolutionTimeHours'].quantile(0.90),
            'p95_hours': df['ResolutionTimeHours'].quantile(0.95),
            'std_hours': df['ResolutionTimeHours'].std(),
            'min_hours': df['ResolutionTimeHours'].min(),
            'max_hours': df['ResolutionTimeHours'].max()
        }
        
        # Escalation impact analysis
        escalated_tickets = df[df['IsEscalated'] == '1']
        non_escalated_tickets = df[df['IsEscalated'] == '0']
        
        if not escalated_tickets.empty and not non_escalated_tickets.empty:
            summary_stats['escalated_mean_hours'] = escalated_tickets['ResolutionTimeHours'].mean()
            summary_stats['non_escalated_mean_hours'] = non_escalated_tickets['ResolutionTimeHours'].mean()
            summary_stats['escalation_impact_hours'] = summary_stats['escalated_mean_hours'] - summary_stats['non_escalated_mean_hours']
            summary_stats['escalated_count'] = len(escalated_tickets)
            summary_stats['non_escalated_count'] = len(non_escalated_tickets)
        else:
            summary_stats['escalated_mean_hours'] = 0
            summary_stats['non_escalated_mean_hours'] = summary_stats['mean_hours']
            summary_stats['escalation_impact_hours'] = 0
            summary_stats['escalated_count'] = 0
            summary_stats['non_escalated_count'] = len(df)
        
        # Category analysis for detailed breakdowns
        category_analysis = {}
        
        # Analysis by Work Item Type (most important)
        if 'WorkItemDefinitionShortCode' in df.columns:
            type_stats = df.groupby('WorkItemDefinitionShortCode')['ResolutionTimeHours'].agg([
                'count', 'mean', 'median', 'std'
            ]).round(2)
            type_stats.columns = ['Count', 'Mean_Hours', 'Median_Hours', 'Std_Hours']
            category_analysis['WorkItemType'] = type_stats.sort_values('Mean_Hours', ascending=False)
        
        # Analysis by Priority
        if 'Priority' in df.columns:
            priority_stats = df.groupby('Priority')['ResolutionTimeHours'].agg([
                'count', 'mean', 'median'
            ]).round(2)
            priority_stats.columns = ['Count', 'Mean_Hours', 'Median_Hours']
            category_analysis['Priority'] = priority_stats.sort_values('Mean_Hours', ascending=False)
        
        # Resolution time distribution
        distribution_analysis = df.groupby('ResolutionCategory').size().sort_index()
        distribution_percentages = (distribution_analysis / len(df) * 100).round(1)
        
        category_analysis['Distribution'] = pd.DataFrame({
            'Count': distribution_analysis,
            'Percentage': distribution_percentages
        })
        
        print(f"📊 Prepared comprehensive resolution times data: {len(df)} resolved tickets")
        return df, summary_stats, category_analysis
        
    except Exception as e:
        print(f"❌ Error preparing resolution times data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(), {}, {}

@monitor_performance("Resolution Times Data Preparation with Dimension")
def prepare_resolution_times_data_with_dimension(filtered_work_items, filtered_duration_summary, status_transitions_data, selected_dimension):
    """
    Enhanced version that calculates statistics for any selected dimension
    """
    resolution_data, summary_stats, category_analysis = prepare_resolution_times_data(
        filtered_work_items, filtered_duration_summary, status_transitions_data
    )
    
    # Add dynamic dimension analysis
    if not resolution_data.empty and selected_dimension in resolution_data.columns:
        dimension_key = selected_dimension.replace('WorkItemDefinitionShortCode', 'WorkItemType')
        
        if dimension_key not in category_analysis:
            dimension_stats = resolution_data.groupby(selected_dimension)['ResolutionTimeHours'].agg([
                'count', 'mean', 'median', 'std'
            ]).round(2)
            dimension_stats.columns = ['Count', 'Mean_Hours', 'Median_Hours', 'Std_Hours']
            category_analysis[dimension_key] = dimension_stats.sort_values('Mean_Hours', ascending=False)
    
    return resolution_data, summary_stats, category_analysis

def register_workflow_resolution_times_callbacks(app):
    """
    Register resolution times analysis callbacks with multiple visualization options and dimensions
    """
    
    @monitor_chart_performance("Resolution Times Bar Chart")
    def create_resolution_times_bar_chart(resolution_data, summary_stats, category_analysis, dimension):
        """
        Create horizontal bar chart showing mean vs median resolution times by selected dimension
        """
        if resolution_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No resolution time data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title=f"Mean & Median Resolution Times by {dimension}",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            # Get data for selected dimension
            dimension_key = dimension.replace('WorkItemDefinitionShortCode', 'WorkItemType')
            
            if dimension_key not in category_analysis:
                # Calculate on-the-fly if not pre-calculated
                if dimension in resolution_data.columns:
                    dimension_stats = resolution_data.groupby(dimension)['ResolutionTimeHours'].agg([
                        'count', 'mean', 'median', 'std'
                    ]).round(2)
                    dimension_stats.columns = ['Count', 'Mean_Hours', 'Median_Hours', 'Std_Hours']
                    dimension_data = dimension_stats.sort_values('Mean_Hours', ascending=False).head(15)
                else:
                    return go.Figure()
            else:
                dimension_data = category_analysis[dimension_key].head(15)
            
            # Create horizontal bar chart
            fig = go.Figure()
            
            # Add mean times
            fig.add_trace(go.Bar(
                y=dimension_data.index,
                x=dimension_data['Mean_Hours'],
                name='Mean Time',
                orientation='h',
                marker_color='#3498DB',
                text=[f"{x:.1f}h" for x in dimension_data['Mean_Hours']],
                textposition='outside',
                hovertemplate='%{y}<br>Mean: %{x:.1f}h<br>Count: %{customdata}<extra></extra>',
                customdata=dimension_data['Count']
            ))
            
            # Add median times
            fig.add_trace(go.Bar(
                y=dimension_data.index,
                x=dimension_data['Median_Hours'],
                name='Median Time',
                orientation='h',
                marker_color='#2ECC71',
                text=[f"{x:.1f}h" for x in dimension_data['Median_Hours']],
                textposition='outside',
                hovertemplate='%{y}<br>Median: %{x:.1f}h<extra></extra>'
            ))
            
            dimension_label = dimension.replace('WorkItemDefinitionShortCode', 'Work Item Type')
            
            fig.update_layout(
                title={
                    'text': f"Mean & Median Resolution Times by {dimension_label}",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis_title="Resolution Time (Hours)",
                yaxis_title=dimension_label,
                height=450,
                margin={'l': 120, 'r': 50, 't': 80, 'b': 60},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                ),
                barmode='group'
            )
            
            return fig
            
        except Exception as e:
            print(f"❌ Error creating resolution times bar chart: {e}")
            return go.Figure()
    
    @monitor_chart_performance("Resolution Times Box Plot")
    def create_resolution_times_box_plot(resolution_data, summary_stats, dimension):
        """
        Create box plot showing resolution time distribution by selected dimension
        """
        if resolution_data.empty or dimension not in resolution_data.columns:
            fig = go.Figure()
            fig.add_annotation(
                text="No resolution time data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title=f"Resolution Times Distribution by {dimension}",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            # Filter out extreme outliers for better visualization
            q99 = resolution_data['ResolutionTimeHours'].quantile(0.99)
            display_data = resolution_data[resolution_data['ResolutionTimeHours'] <= q99].copy()
            
            # Get top categories by count for readability
            top_categories = display_data[dimension].value_counts().head(10).index.tolist()
            plot_data = display_data[display_data[dimension].isin(top_categories)]
            
            fig = go.Figure()
            
            # Create box plot for each category
            for category in top_categories:
                category_data = plot_data[plot_data[dimension] == category]['ResolutionTimeHours']
                if len(category_data) > 0:
                    fig.add_trace(go.Box(
                        y=category_data,
                        name=str(category),
                        boxpoints='outliers',
                        marker_color=px.colors.qualitative.Set3[len(fig.data) % len(px.colors.qualitative.Set3)]
                    ))
            
            # Add overall mean line
            mean_hours = summary_stats.get('mean_hours', 0)
            if mean_hours > 0:
                fig.add_hline(
                    y=mean_hours,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Overall Mean: {mean_hours:.1f}h",
                    annotation_position="top left"
                )
            
            dimension_label = dimension.replace('WorkItemDefinitionShortCode', 'Work Item Type')
            
            fig.update_layout(
                title={
                    'text': f"Resolution Times Distribution by {dimension_label}",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                yaxis_title="Resolution Time (Hours)",
                xaxis_title=dimension_label,
                height=450,
                margin={'l': 60, 'r': 50, 't': 80, 'b': 80},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            print(f"❌ Error creating resolution times box plot: {e}")
            return go.Figure()
    
    @monitor_chart_performance("Resolution Times Statistics Figure")
    def create_resolution_times_statistics_figure(resolution_data, summary_stats, category_analysis, dimension, population="all"):
        """
        Create focused statistics view showing distribution with statistical markers
        Population parameter controls which subset of data to analyze:
        - "all": All tickets
        - "escalated": Only escalated tickets  
        - "non_escalated": Only non-escalated tickets
        """
        if resolution_data.empty or not summary_stats:
            fig = go.Figure()
            fig.add_annotation(
                text="No resolution data available for current filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title="Resolution Times Statistics",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

        try:
            # Filter data based on population selection
            if population == "escalated":
                if 'IsEscalated' not in resolution_data.columns:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="Escalation data not available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, xanchor='center', yanchor='middle',
                        showarrow=False,
                        font=dict(size=16, color="gray")
                    )
                    fig.update_layout(title="Escalated Tickets Statistics", height=450)
                    return fig
                    
                filtered_data = resolution_data[resolution_data['IsEscalated'] == '1'].copy()
                if filtered_data.empty:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="🎯 No Escalated Tickets Found!\n\nExcellent performance - all tickets resolved at first contact",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, xanchor='center', yanchor='middle',
                        showarrow=False,
                        font=dict(size=16, color="green")
                    )
                    fig.update_layout(title="Escalated Tickets Statistics", height=450, plot_bgcolor='white', paper_bgcolor='white')
                    return fig
                    
                population_title = "Escalated Tickets"
                population_color = "#E74C3C"
                
            elif population == "non_escalated":
                if 'IsEscalated' not in resolution_data.columns:
                    filtered_data = resolution_data.copy()  # Assume all non-escalated if no escalation data
                else:
                    filtered_data = resolution_data[resolution_data['IsEscalated'] == '0'].copy()
                    
                if filtered_data.empty:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="No non-escalated tickets found",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, xanchor='center', yanchor='middle',
                        showarrow=False,
                        font=dict(size=16, color="gray")
                    )
                    fig.update_layout(title="Non-Escalated Tickets Statistics", height=450)
                    return fig
                    
                population_title = "Non-Escalated Tickets"
                population_color = "#27AE60"
                
            else:  # "all"
                filtered_data = resolution_data.copy()
                population_title = "All Tickets"
                population_color = "#3498DB"
            
            # Calculate statistics for the filtered population
            hours_data = filtered_data['ResolutionTimeHours']
            pop_stats = {
                'count': len(filtered_data),
                'mean_hours': hours_data.mean(),
                'median_hours': hours_data.median(),
                'p75_hours': hours_data.quantile(0.75),
                'p90_hours': hours_data.quantile(0.90),
                'p95_hours': hours_data.quantile(0.95),
                'min_hours': hours_data.min(),
                'max_hours': hours_data.max(),
                'std_hours': hours_data.std()
            }
            
            # Create the visualization
            fig = go.Figure()
            
            # Filter outliers for better visualization (keep 99% of data)
            q99 = hours_data.quantile(0.99)
            display_hours = hours_data[hours_data <= q99]
            
            # Create histogram
            fig.add_trace(
                go.Histogram(
                    x=display_hours,
                    nbinsx=min(30, max(10, len(display_hours) // 10)),  # Adaptive bin count
                    opacity=0.7,
                    marker_color=population_color,
                    name='Ticket Distribution',
                    showlegend=False
                )
            )
            
            # Add vertical lines for key statistics
            stats_lines = [
                {'value': pop_stats['median_hours'], 'name': 'Median', 'color': '#2ECC71', 'dash': 'solid'},
                {'value': pop_stats['mean_hours'], 'name': 'Mean', 'color': '#3498DB', 'dash': 'dash'},
                {'value': pop_stats['p75_hours'], 'name': '75th %ile', 'color': '#F39C12', 'dash': 'dot'},
                {'value': pop_stats['p90_hours'], 'name': '90th %ile', 'color': '#E67E22', 'dash': 'dashdot'},
                {'value': pop_stats['p95_hours'], 'name': '95th %ile', 'color': '#E74C3C', 'dash': 'longdash'}
            ]
            
            # Add the statistical markers as vertical lines
            for stat in stats_lines:
                if not pd.isna(stat['value']) and stat['value'] > 0:
                    fig.add_vline(
                        x=stat['value'],
                        line_dash=stat['dash'],
                        line_color=stat['color'],
                        line_width=2,
                        annotation_text=f"{stat['name']}: {stat['value']:.1f}h",
                        annotation_position="top",
                        annotation_font_size=9
                    )
            
            # Update layout
            fig.update_layout(
                title={
                    'text': f"{population_title} - Resolution Times Distribution ({pop_stats['count']:,} tickets)",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'color': '#2c3e50'}
                },
                xaxis_title="Resolution Time (Hours)",
                yaxis_title="Number of Tickets",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin={'l': 60, 'r': 200, 't': 100, 'b': 80}  # Increased right margin for legend
            )
            
            # Create consolidated legend with all information
            mean_hours = pop_stats['mean_hours']
            median_hours = pop_stats['median_hours']
            
            # Determine distribution characteristics
            if mean_hours > 0 and median_hours > 0:
                skew_ratio = mean_hours / median_hours
                if skew_ratio > 1.3:
                    distribution_note = "Right-skewed"
                    distribution_icon = "📈"
                elif skew_ratio < 0.8:
                    distribution_note = "Left-skewed"
                    distribution_icon = "📉"
                else:
                    distribution_note = "Balanced"
                    distribution_icon = "⚖️"
            else:
                distribution_note = "Insufficient data"
                distribution_icon = "❓"
            
            # Add comparison to overall population if this is a subset
            comparison_text = ""
            if population != "all" and summary_stats.get('mean_hours', 0) > 0:
                overall_mean = summary_stats['mean_hours']
                pop_mean = pop_stats['mean_hours']
                if pop_mean > overall_mean:
                    diff_pct = ((pop_mean - overall_mean) / overall_mean) * 100
                    comparison_text = f"↗️ {diff_pct:.0f}% slower than overall\n"
                elif pop_mean < overall_mean:
                    diff_pct = ((overall_mean - pop_mean) / overall_mean) * 100
                    comparison_text = f"↘️ {diff_pct:.0f}% faster than overall\n"
                else:
                    comparison_text = "➡️ Same as overall average\n"
            
            # Consolidated legend text
            legend_text = f"""<b>📊 Statistics & Interpretation</b><br><br>

<b>Key Metrics:</b><br>
• Median: {median_hours:.1f}h (50% resolve faster)<br>
• Mean: {mean_hours:.1f}h<br>
• 75th percentile: {pop_stats['p75_hours']:.1f}h (75% within)<br>
• 90th percentile: {pop_stats['p90_hours']:.1f}h (90% within)<br>
• 95th percentile: {pop_stats['p95_hours']:.1f}h (only 5% exceed)<br><br>

<b>Distribution:</b><br>
{distribution_icon} {distribution_note}<br>
{comparison_text}<br>

<b>Vertical Lines:</b><br>
<span style='color:#2ECC71'>●</span> Green solid: Median<br>
<span style='color:#3498DB'>●</span> Blue dashed: Mean<br>
<span style='color:#F39C12'>●</span> Orange dotted: 75th percentile<br>
<span style='color:#E67E22'>●</span> Red dash-dot: 90th percentile<br>
<span style='color:#E74C3C'>●</span> Dark red long-dash: 95th percentile"""
            
            # Add single consolidated annotation in top-right corner
            fig.add_annotation(
                text=legend_text,
                xref="paper", yref="paper",
                x=0.99, y=0.98,
                xanchor='right', yanchor='top',
                showarrow=False,
                font=dict(size=10, color="#2c3e50"),
                align="left",
                bgcolor="rgba(248, 249, 250, 0.95)",
                bordercolor="rgba(52, 152, 219, 0.3)",
                borderwidth=1,
                borderpad=12
            )
            
            return fig
            
        except Exception as e:
            print(f"❌ Error creating statistics dashboard: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to simple figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating statistics dashboard: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title="Resolution Times Statistics - Error",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
    
    # @monitor_chart_performance("Resolution Times Statistics Figure")
    # def create_resolution_times_statistics_figure(resolution_data, summary_stats, category_analysis, dimension, population="all"):
    #     """
    #     Create focused statistics view showing distribution with statistical markers
    #     Population parameter controls which subset of data to analyze:
    #     - "all": All tickets
    #     - "escalated": Only escalated tickets  
    #     - "non_escalated": Only non-escalated tickets
    #     """
    #     if resolution_data.empty or not summary_stats:
    #         fig = go.Figure()
    #         fig.add_annotation(
    #             text="No resolution data available for current filters",
    #             xref="paper", yref="paper",
    #             x=0.5, y=0.5, xanchor='center', yanchor='middle',
    #             showarrow=False,
    #             font=dict(size=16, color="gray")
    #         )
    #         fig.update_layout(
    #             title="Resolution Times Statistics",
    #             height=450,
    #             plot_bgcolor='white',
    #             paper_bgcolor='white'
    #         )
    #         return fig

    #     try:
    #         # Filter data based on population selection
    #         if population == "escalated":
    #             if 'IsEscalated' not in resolution_data.columns:
    #                 fig = go.Figure()
    #                 fig.add_annotation(
    #                     text="Escalation data not available",
    #                     xref="paper", yref="paper",
    #                     x=0.5, y=0.5, xanchor='center', yanchor='middle',
    #                     showarrow=False,
    #                     font=dict(size=16, color="gray")
    #                 )
    #                 fig.update_layout(title="Escalated Tickets Statistics", height=450)
    #                 return fig
                    
    #             filtered_data = resolution_data[resolution_data['IsEscalated'] == '1'].copy()
    #             if filtered_data.empty:
    #                 fig = go.Figure()
    #                 fig.add_annotation(
    #                     text="🎯 No Escalated Tickets Found!\n\nExcellent performance - all tickets resolved at first contact",
    #                     xref="paper", yref="paper",
    #                     x=0.5, y=0.5, xanchor='center', yanchor='middle',
    #                     showarrow=False,
    #                     font=dict(size=16, color="green")
    #                 )
    #                 fig.update_layout(title="Escalated Tickets Statistics", height=450, plot_bgcolor='white', paper_bgcolor='white')
    #                 return fig
                    
    #             population_title = "Escalated Tickets"
    #             population_color = "#E74C3C"
                
    #         elif population == "non_escalated":
    #             if 'IsEscalated' not in resolution_data.columns:
    #                 filtered_data = resolution_data.copy()  # Assume all non-escalated if no escalation data
    #             else:
    #                 filtered_data = resolution_data[resolution_data['IsEscalated'] == '0'].copy()
                    
    #             if filtered_data.empty:
    #                 fig = go.Figure()
    #                 fig.add_annotation(
    #                     text="No non-escalated tickets found",
    #                     xref="paper", yref="paper",
    #                     x=0.5, y=0.5, xanchor='center', yanchor='middle',
    #                     showarrow=False,
    #                     font=dict(size=16, color="gray")
    #                 )
    #                 fig.update_layout(title="Non-Escalated Tickets Statistics", height=450)
    #                 return fig
                    
    #             population_title = "Non-Escalated Tickets"
    #             population_color = "#27AE60"
                
    #         else:  # "all"
    #             filtered_data = resolution_data.copy()
    #             population_title = "All Tickets"
    #             population_color = "#3498DB"
            
    #         # Calculate statistics for the filtered population
    #         hours_data = filtered_data['ResolutionTimeHours']
            
    #         # Check if we have valid data
    #         if hours_data.empty or hours_data.isna().all():
    #             fig = go.Figure()
    #             fig.add_annotation(
    #                 text="No valid resolution time data available",
    #                 xref="paper", yref="paper",
    #                 x=0.5, y=0.5, xanchor='center', yanchor='middle',
    #                 showarrow=False,
    #                 font=dict(size=16, color="gray")
    #             )
    #             fig.update_layout(title=f"{population_title} Statistics", height=450)
    #             return fig
            
    #         pop_stats = {
    #             'count': len(filtered_data),
    #             'mean_hours': float(hours_data.mean()),
    #             'median_hours': float(hours_data.median()),
    #             'p75_hours': float(hours_data.quantile(0.75)),
    #             'p90_hours': float(hours_data.quantile(0.90)),
    #             'p95_hours': float(hours_data.quantile(0.95)),
    #             'min_hours': float(hours_data.min()),
    #             'max_hours': float(hours_data.max()),
    #             'std_hours': float(hours_data.std())
    #         }
            
    #         # Create the visualization
    #         fig = go.Figure()
            
    #         # Filter outliers for better visualization (keep 99% of data)
    #         q99 = hours_data.quantile(0.99)
    #         display_hours = hours_data[hours_data <= q99]
            
    #         # Create histogram
    #         fig.add_trace(
    #             go.Histogram(
    #                 x=display_hours,
    #                 nbinsx=min(30, max(10, len(display_hours) // 10)),  # Adaptive bin count
    #                 opacity=0.7,
    #                 marker_color=population_color,
    #                 name='Ticket Distribution',
    #                 showlegend=False
    #             )
    #         )
            
    #         # Add vertical lines for key statistics
    #         stats_lines = [
    #             {'value': pop_stats['median_hours'], 'name': 'Median', 'color': '#2ECC71', 'dash': 'solid'},
    #             {'value': pop_stats['mean_hours'], 'name': 'Mean', 'color': '#3498DB', 'dash': 'dash'},
    #             {'value': pop_stats['p75_hours'], 'name': '75th %ile', 'color': '#F39C12', 'dash': 'dot'},
    #             {'value': pop_stats['p90_hours'], 'name': '90th %ile', 'color': '#E67E22', 'dash': 'dashdot'},
    #             {'value': pop_stats['p95_hours'], 'name': '95th %ile', 'color': '#E74C3C', 'dash': 'longdash'}
    #         ]
            
    #         # Add the statistical markers as vertical lines without individual annotations
    #         for stat in stats_lines:
    #             if not pd.isna(stat['value']) and stat['value'] > 0:
    #                 fig.add_vline(
    #                     x=stat['value'],
    #                     line_dash=stat['dash'],
    #                     line_color=stat['color'],
    #                     line_width=2
    #                 )
            
    #         # Create a compact statistical lines reference for the legend
    #         stats_reference = ""
    #         for stat in stats_lines:
    #             if not pd.isna(stat['value']) and stat['value'] > 0:
    #                 stats_reference += f"<span style='color:{stat['color']}'>●</span> {stat['name']}: {stat['value']:.1f}h<br>"
                    
    #         # Update layout
    #         fig.update_layout(
    #             title={
    #                 'text': f"{population_title} - Resolution Times Distribution ({pop_stats['count']:,} tickets)",
    #                 'x': 0.5,
    #                 'xanchor': 'center',
    #                 'font': {'size': 18, 'color': '#2c3e50'}
    #             },
    #             xaxis_title="Resolution Time (Hours)",
    #             yaxis_title="Number of Tickets",
    #             height=450,
    #             plot_bgcolor='white',
    #             paper_bgcolor='white',
    #             margin={'l': 60, 'r': 250, 't': 100, 'b': 80}  # Increased right margin for legend
    #         )
            
    #         # Create consolidated legend with all information
    #         mean_hours = pop_stats['mean_hours']
    #         median_hours = pop_stats['median_hours']
            
    #         # Determine distribution characteristics
    #         if mean_hours > 0 and median_hours > 0:
    #             skew_ratio = mean_hours / median_hours
    #             if skew_ratio > 1.3:
    #                 distribution_note = "Right-skewed"
    #                 distribution_icon = "📈"
    #             elif skew_ratio < 0.8:
    #                 distribution_note = "Left-skewed"
    #                 distribution_icon = "📉"
    #             else:
    #                 distribution_note = "Balanced"
    #                 distribution_icon = "⚖️"
    #         else:
    #             distribution_note = "Insufficient data"
    #             distribution_icon = "❓"
            
    #         # Add comparison to overall population if this is a subset
    #         comparison_text = ""
    #         if population != "all" and summary_stats.get('mean_hours', 0) > 0:
    #             overall_mean = summary_stats['mean_hours']
    #             pop_mean = pop_stats['mean_hours']
    #             if pop_mean > overall_mean:
    #                 diff_pct = ((pop_mean - overall_mean) / overall_mean) * 100
    #                 comparison_text = f"↗️ {diff_pct:.0f}% slower than overall<br>"
    #             elif pop_mean < overall_mean:
    #                 diff_pct = ((overall_mean - pop_mean) / overall_mean) * 100
    #                 comparison_text = f"↘️ {diff_pct:.0f}% faster than overall<br>"
    #             else:
    #                 comparison_text = "➡️ Same as overall average<br>"
            
    #         # Consolidated legend text with integrated statistical lines
    #         legend_text = f"""<b>📊 Statistics & Interpretation</b><br><br>

    # <b>Key Metrics:</b><br>
    # • Median: {median_hours:.1f}h (50% resolve faster)<br>
    # • Mean: {mean_hours:.1f}h<br>
    # • 75th percentile: {pop_stats['p75_hours']:.1f}h (75% within)<br>
    # • 90th percentile: {pop_stats['p90_hours']:.1f}h (90% within)<br>
    # • 95th percentile: {pop_stats['p95_hours']:.1f}h (only 5% exceed)<br><br>

    # <b>Distribution:</b><br>
    # {distribution_icon} {distribution_note}<br>
    # {comparison_text}<br>

    # <b>Statistical Lines:</b><br>
    # {stats_reference}"""
            
    #         # Add single consolidated annotation in top-right corner
    #         fig.add_annotation(
    #             text=legend_text,
    #             xref="paper", yref="paper",
    #             x=0.99, y=0.98,
    #             xanchor='right', yanchor='top',
    #             showarrow=False,
    #             font=dict(size=10, color="#2c3e50"),
    #             align="left",
    #             bgcolor="rgba(248, 249, 250, 0.95)",
    #             bordercolor="rgba(52, 152, 219, 0.3)",
    #             borderwidth=1,
    #             borderpad=12
    #         )
            
    #         return fig
            
    #     except Exception as e:
    #         print(f"❌ Error creating statistics dashboard: {e}")
    #         import traceback
    #         traceback.print_exc()
            
    #         # Fallback to simple figure
    #         fig = go.Figure()
    #         fig.add_annotation(
    #             text=f"Error creating statistics dashboard: {str(e)}",
    #             xref="paper", yref="paper",
    #             x=0.5, y=0.5, xanchor='center', yanchor='middle',
    #             showarrow=False,
    #             font=dict(size=14, color="red")
    #         )
    #         fig.update_layout(
    #             title="Resolution Times Statistics - Error",
    #             height=450,
    #             plot_bgcolor='white',
    #             paper_bgcolor='white'
    #         )
    #         return fig
                   
    @monitor_chart_performance("Resolution Times Distribution Chart")
    def create_resolution_times_distribution_chart(resolution_data, summary_stats, category_analysis, population="all"):
        """
        Create pie chart showing resolution time distribution by categories
        Population parameter controls which subset of data to analyze:
        - "all": All tickets
        - "escalated": Only escalated tickets  
        - "non_escalated": Only non-escalated tickets
        """
        if resolution_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No resolution time data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title="Resolution Time Distribution Analysis",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            # Filter data based on population selection
            if population == "escalated":
                if 'IsEscalated' not in resolution_data.columns:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="Escalation data not available",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, xanchor='center', yanchor='middle',
                        showarrow=False,
                        font=dict(size=16, color="gray")
                    )
                    fig.update_layout(title="Escalated Tickets Distribution", height=450)
                    return fig
                    
                filtered_data = resolution_data[resolution_data['IsEscalated'] == '1'].copy()
                if filtered_data.empty:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="🎯 No Escalated Tickets Found!\n\nExcellent performance - all tickets resolved at first contact",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, xanchor='center', yanchor='middle',
                        showarrow=False,
                        font=dict(size=16, color="green")
                    )
                    fig.update_layout(title="Escalated Tickets Distribution", height=450, plot_bgcolor='white', paper_bgcolor='white')
                    return fig
                    
                population_title = "Escalated Tickets"
                population_colors = ['#E74C3C', '#C0392B', '#A93226', '#922B21', '#7B241C', '#6B2737', '#5B2C6F']
                
            elif population == "non_escalated":
                if 'IsEscalated' not in resolution_data.columns:
                    filtered_data = resolution_data.copy()  # Assume all non-escalated if no escalation data
                else:
                    filtered_data = resolution_data[resolution_data['IsEscalated'] == '0'].copy()
                    
                if filtered_data.empty:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="No non-escalated tickets found",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, xanchor='center', yanchor='middle',
                        showarrow=False,
                        font=dict(size=16, color="gray")
                    )
                    fig.update_layout(title="Non-Escalated Tickets Distribution", height=450)
                    return fig
                    
                population_title = "Non-Escalated Tickets"
                population_colors = ['#27AE60', '#229954', '#1E8449', '#196F3D', '#145A32', '#0E4B99', '#2E86AB']
                
            else:  # "all"
                filtered_data = resolution_data.copy()
                population_title = "All Tickets"
                population_colors = ['#3498DB', '#2980B9', '#1F618D', '#1A5276', '#154360', '#5DADE2', '#85C1E9']
            
            # Recalculate distribution for the filtered population
            def categorize_resolution_time(minutes):
                if pd.isna(minutes) or minutes <= 0:
                    return 'Invalid'
                elif minutes <= 15:
                    return '≤15 min'
                elif minutes <= 60:
                    return '15-60 min'
                elif minutes <= 240:  # 4 hours
                    return '1-4 hours'
                elif minutes <= 1440:  # 24 hours
                    return '4-24 hours'
                elif minutes <= 10080:  # 7 days
                    return '1-7 days'
                else:
                    return '7+ days'
            
            filtered_data['ResolutionCategory'] = filtered_data['ResolutionTimeMinutes'].apply(categorize_resolution_time)
            
            # Create distribution analysis for this population
            distribution_analysis = filtered_data.groupby('ResolutionCategory').size()
            distribution_percentages = (distribution_analysis / len(filtered_data) * 100).round(1)
            
            population_distribution = pd.DataFrame({
                'Count': distribution_analysis,
                'Percentage': distribution_percentages
            })
            
            # Filter out zero counts and invalid data
            pie_data = population_distribution[population_distribution['Count'] > 0].copy()
            pie_data = pie_data[pie_data.index != 'Invalid']  # Remove invalid entries
            
            if pie_data.empty:
                fig = go.Figure()
                fig.add_annotation(
                    text="No valid distribution data available for this population",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False,
                    font=dict(size=16, color="gray")
                )
                fig.update_layout(
                    title=f"{population_title} - Distribution Analysis",
                    height=450,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                return fig
            
            # Calculate population-specific statistics
            pop_hours_data = filtered_data['ResolutionTimeHours']
            pop_stats = {
                'total_tickets': len(filtered_data),
                'mean_hours': pop_hours_data.mean(),
                'median_hours': pop_hours_data.median(),
                'p90_hours': pop_hours_data.quantile(0.90)
            }
            
            # Create pie chart with population-specific colors
            fig = go.Figure()
            
            fig.add_trace(
                go.Pie(
                    labels=pie_data.index.tolist(),
                    values=pie_data['Count'].tolist(),
                    hole=0.4,  # Donut chart
                    textinfo='label+percent+value',
                    textposition='outside',
                    marker=dict(
                        colors=population_colors[:len(pie_data)],
                        line=dict(color='white', width=2)
                    ),
                    hovertemplate='<b>%{label}</b><br>' +
                                'Count: %{value}<br>' +
                                'Percentage: %{percent}<br>' +
                                '<extra></extra>'
                )
            )
            
            # Add center text with population-specific summary stats
            total_tickets = pop_stats['total_tickets']
            mean_hours = pop_stats['mean_hours']
            median_hours = pop_stats['median_hours']
            
            fig.add_annotation(
                text=f"<b>{total_tickets:,}</b><br>{population_title}<br><br>" +
                    f"Mean: {mean_hours:.1f}h<br>" +
                    f"Median: {median_hours:.1f}h",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False,
                align="center"
            )
            
            # Add comparison insight if this is a subset
            comparison_insight = ""
            if population != "all" and summary_stats.get('mean_hours', 0) > 0:
                overall_mean = summary_stats['mean_hours']
                pop_mean = pop_stats['mean_hours']
                if pop_mean > overall_mean:
                    diff_pct = ((pop_mean - overall_mean) / overall_mean) * 100
                    comparison_insight = f"↗️ {diff_pct:.0f}% slower than overall average"
                elif pop_mean < overall_mean:
                    diff_pct = ((overall_mean - pop_mean) / overall_mean) * 100
                    comparison_insight = f"↘️ {diff_pct:.0f}% faster than overall average"
                else:
                    comparison_insight = "➡️ Same as overall average"
            
            # Update layout with population-specific title
            fig.update_layout(
                title={
                    'text': f"{population_title} - Resolution Time Distribution",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'color': '#2c3e50'}
                },
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin={'l': 50, 'r': 180, 't': 80, 'b': 50},  # Increased right margin for legend
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.05,
                    font=dict(size=11)
                )
            )
            
            # Add comparison insight annotation if available
            if comparison_insight:
                fig.add_annotation(
                    text=comparison_insight,
                    xref="paper", yref="paper",
                    x=0.02, y=0.02,
                    xanchor='left', yanchor='bottom',
                    showarrow=False,
                    font=dict(size=11, color="#2c3e50"),
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor="rgba(0, 0, 0, 0.2)",
                    borderwidth=1,
                    borderpad=3
                )
            
            print(f"📊 Distribution pie chart created successfully for {population} population")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating distribution chart: {e}")
            import traceback
            traceback.print_exc()
            
            # Return error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating distribution chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title=f"{population_title if 'population_title' in locals() else 'Population'} Distribution Analysis - Error",
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
                    
    @monitor_performance("Resolution Times Insights Generation")
    def generate_resolution_times_insights(resolution_data, summary_stats, category_analysis):
        """
        Generate automated insights from resolution times data
        Always returns exactly 3 insights for consistency:
        1. Performance Summary with Mean vs Median analysis
        2. Escalation Impact Analysis
        3. Distribution & Performance Patterns
        """
        if resolution_data.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No resolution data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see resolution insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("⏱️ Data will appear when resolved tickets match your criteria", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        try:
            insights = []
            
            # Insight 1: Performance Summary with Mean vs Median Analysis
            mean_hours = summary_stats.get('mean_hours', 0)
            median_hours = summary_stats.get('median_hours', 0)
            total_resolved = summary_stats.get('total_resolved', 0)
            p90_hours = summary_stats.get('p90_hours', 0)
            
            # Determine if distribution is skewed (mean significantly different from median)
            if mean_hours > 0 and median_hours > 0:
                skew_ratio = mean_hours / median_hours
                if skew_ratio > 1.5:
                    skew_indicator = "right-skewed (few very long resolution times)"
                elif skew_ratio < 0.8:
                    skew_indicator = "left-skewed (consistently fast resolutions)"
                else:
                    skew_indicator = "balanced distribution"
            else:
                skew_indicator = "insufficient data"
            
            # Performance level assessment
            if median_hours < 4:
                performance_level = "excellent"
            elif median_hours < 24:
                performance_level = "good" 
            elif median_hours < 72:
                performance_level = "acceptable"
            else:
                performance_level = "needs improvement"
            
            insights.append(f"⏱️ **Performance Summary**: {total_resolved:,} tickets resolved with {mean_hours:.1f}h mean, {median_hours:.1f}h median ({performance_level}, {skew_indicator})")
            
            # Insight 2: Escalation Impact Analysis
            escalated_count = summary_stats.get('escalated_count', 0)
            escalated_mean = summary_stats.get('escalated_mean_hours', 0)
            non_escalated_mean = summary_stats.get('non_escalated_mean_hours', 0)
            escalation_impact = summary_stats.get('escalation_impact_hours', 0)
            
            if escalated_count > 0 and non_escalated_mean > 0 and escalated_mean > 0:
                impact_multiplier = escalated_mean / non_escalated_mean
                escalation_rate = (escalated_count / total_resolved * 100) if total_resolved > 0 else 0
                
                if escalation_impact > 24:  # More than 1 day difference
                    impact_severity = "significant"
                elif escalation_impact > 8:  # More than 8 hours difference
                    impact_severity = "moderate" 
                elif escalation_impact > 0:
                    impact_severity = "minimal"
                else:
                    impact_severity = "no"
                    
                insights.append(f"🚨 **Escalation Impact**: {escalated_count:,} escalated tickets ({escalation_rate:.1f}%) take {escalated_mean:.1f}h vs {non_escalated_mean:.1f}h ({impact_multiplier:.1f}x longer, {impact_severity} impact)")
            else:
                # Handle cases with no escalated tickets or missing data
                if escalated_count == 0:
                    insights.append(f"🎯 **Escalation Analysis**: No escalated tickets found - excellent first-contact resolution performance")
                else:
                    insights.append(f"🔍 **Escalation Analysis**: {escalated_count:,} escalated tickets detected, impact analysis requires more complete data")
            
            # Insight 3: Distribution & Performance Patterns Analysis
            if 'WorkItemType' in category_analysis and not category_analysis['WorkItemType'].empty:
                # Analysis based on work item types
                work_item_data = category_analysis['WorkItemType']
                slowest_type = work_item_data.index[0]  # Already sorted by Mean_Hours desc
                slowest_time = work_item_data.iloc[0]['Mean_Hours']
                fastest_type = work_item_data.index[-1]
                fastest_time = work_item_data.iloc[-1]['Mean_Hours']
                
                # Calculate performance variance
                if slowest_time > 0 and fastest_time > 0:
                    performance_variance = slowest_time / fastest_time
                    if performance_variance > 5:
                        variance_level = "high variance"
                    elif performance_variance > 2:
                        variance_level = "moderate variance"
                    else:
                        variance_level = "consistent performance"
                else:
                    variance_level = "insufficient data"
                
                insights.append(f"📊 **Type Performance**: '{slowest_type}' takes longest ({slowest_time:.1f}h avg), '{fastest_type}' fastest ({fastest_time:.1f}h), 90% resolve within {p90_hours:.1f}h ({variance_level})")
                
            elif 'Distribution' in category_analysis and not category_analysis['Distribution'].empty:
                # Fallback to distribution analysis when work item type data not available
                dist_data = category_analysis['Distribution']
                
                # Calculate same-day resolution percentage
                same_day_categories = ['≤15 min', '15-60 min', '1-4 hours', '4-24 hours']
                same_day_pct = 0
                for category in same_day_categories:
                    if category in dist_data.index:
                        same_day_pct += dist_data.loc[category, 'Percentage']
                
                # Find most common resolution category
                top_category = dist_data['Count'].idxmax() if not dist_data.empty else "Unknown"
                top_category_pct = dist_data.loc[top_category, 'Percentage'] if top_category in dist_data.index else 0
                
                if same_day_pct > 80:
                    speed_assessment = "excellent speed"
                elif same_day_pct > 60:
                    speed_assessment = "good speed"
                elif same_day_pct > 40:
                    speed_assessment = "moderate speed"
                else:
                    speed_assessment = "improvement needed"
                
                insights.append(f"📈 **Resolution Pattern**: {same_day_pct:.1f}% resolve within 24h, most tickets in '{top_category}' category ({top_category_pct:.1f}%), 90% within {p90_hours:.1f}h ({speed_assessment})")
                
            else:
                # Ultimate fallback using basic statistics
                if p90_hours > 0:
                    if p90_hours < 24:
                        pattern_assessment = "fast resolution pattern"
                    elif p90_hours < 168:  # 1 week
                        pattern_assessment = "standard resolution pattern"
                    else:
                        pattern_assessment = "slow resolution pattern"
                        
                    insights.append(f"📊 **Resolution Pattern**: 90% of tickets resolve within {p90_hours:.1f}h with {mean_hours:.1f}h average ({pattern_assessment})")
                else:
                    insights.append(f"📊 **Resolution Pattern**: Analysis requires more complete resolution time data")
            
            # Create exactly 3 styled insight cards
            insight_components = []
            for insight in insights:
                insight_components.append(
                    html.Div([
                        html.Span(insight, style={'fontSize': '13px'})
                    ], className="mb-2")
                )
            
            return html.Div(insight_components, className="insights-container")
            
        except Exception as e:
            print(f"❌ Error generating resolution times insights: {e}")
            import traceback
            traceback.print_exc()
            # Return 3 error insights for consistency
            return html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate resolution insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")

    @callback(
        Output("workflow-resolution-view-state", "data"),
        [Input("workflow-resolution-bar-btn", "n_clicks"),
         Input("workflow-resolution-box-btn", "n_clicks"),
         Input("workflow-resolution-stats-btn", "n_clicks"),
         Input("workflow-resolution-dist-btn", "n_clicks")],
        [State("workflow-resolution-view-state", "data")],
        prevent_initial_call=False
    )
    def update_view_state(bar_clicks, box_clicks, stats_clicks, dist_clicks, current_state):
        """
        Store the current view state and persist it across dimension changes
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # Initialize with bar chart if no state exists
        if current_state is None:
            current_state = "bar"
        
        # Update state only when a view button is clicked
        if triggered_id == "workflow-resolution-bar-btn":
            return "bar"
        elif triggered_id == "workflow-resolution-box-btn":
            return "box"
        elif triggered_id == "workflow-resolution-stats-btn":
            return "stats"
        elif triggered_id == "workflow-resolution-dist-btn":
            return "dist"
        
        # Return existing state for other triggers (like dimension changes)
        return current_state

    @callback(
        Output("workflow-resolution-population-state", "data"),
        [Input("workflow-resolution-population-selector", "value")],
        prevent_initial_call=False
    )
    def update_population_state(selected_population):
        """Store the selected population for statistics view"""
        return selected_population or "all"
    
    # Main callback 
    @callback(
        [Output("workflow-resolution-times-chart", "figure"),
         Output("workflow-resolution-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
         Input("workflow-resolution-dimension-selector", "value"),
         Input("workflow-resolution-view-state", "data"),
         Input("workflow-resolution-population-state", "data")],
        prevent_initial_call=False
    )
    @monitor_performance("Resolution Times Chart Update")
    def update_resolution_times_chart(stored_selections, selected_dimension, view_state, selected_population):
        """
        Update resolution times chart based on filter selections, dimension, view type, and population
        """
        try:
            print(f"🔄 Updating resolution times chart - Dimension: {selected_dimension}, View: {view_state}, Population: {selected_population}")
            
            # Default to bar chart if no view state
            if view_state is None:
                view_state = "bar"
            
            # Default to all population if none selected
            if selected_population is None:
                selected_population = "all"
            
            # Get base data
            base_data = get_resolution_times_base_data()
            
            # Apply filters
            filtered_work_items, filtered_duration_summary = apply_resolution_times_filters(
                base_data['work_items'], 
                base_data['duration_summary'], 
                stored_selections
            )
            
            # Prepare resolution times data with dynamic dimension analysis
            resolution_data, summary_stats, category_analysis = prepare_resolution_times_data_with_dimension(
                filtered_work_items, 
                filtered_duration_summary, 
                base_data['status_transitions'],
                selected_dimension
            )
            
            # Generate insights (always generated for all views)
            insights = generate_resolution_times_insights(resolution_data, summary_stats, category_analysis)
            
            # Create appropriate visualization based on view state
            if view_state == "stats":
                # For statistics view, pass the population parameter
                fig = create_resolution_times_statistics_figure(
                    resolution_data, summary_stats, category_analysis, 
                    selected_dimension, selected_population
                )
            elif view_state == "box":
                fig = create_resolution_times_box_plot(resolution_data, summary_stats, selected_dimension)
            elif view_state == "dist":
                # For distribution view, also pass the population parameter
                fig = create_resolution_times_distribution_chart(
                    resolution_data, summary_stats, category_analysis, selected_population
                )
            else:  # bar chart (default)
                fig = create_resolution_times_bar_chart(resolution_data, summary_stats, category_analysis, selected_dimension)
            
            print(f"✅ Resolution times chart updated successfully - View: {view_state}, Population: {selected_population}")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating resolution times chart: {e}")
            import traceback
            traceback.print_exc()
            
            # Return error chart
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading resolution times data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(title="Resolution Times Analysis - Error", height=450)
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate resolution insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
               
    @callback(
        [Output("workflow-resolution-bar-btn", "active"),
         Output("workflow-resolution-box-btn", "active"),
         Output("workflow-resolution-stats-btn", "active"),
         Output("workflow-resolution-dist-btn", "active")],
        [Input("workflow-resolution-view-state", "data")],
        prevent_initial_call=False
    )
    def update_button_states(view_state):
        """Update button active states based on stored view state"""
        if view_state == "box":
            return False, True, False, False
        elif view_state == "stats":
            return False, False, True, False
        elif view_state == "dist":
            return False, False, False, True
        else:  # bar chart or default
            return True, False, False, False

    @callback(
        Output("workflow-resolution-dimension-container", "style"),
        [Input("workflow-resolution-view-state", "data")],
        prevent_initial_call=False
    )
    def toggle_dimension_selector_visibility(view_state):
        """Show dimension selector only for Bar Chart and Box Plot views"""
        if view_state in ["bar", "box"]:
            return {'display': 'block', 'marginBottom': '15px'}
        else:
            return {'display': 'none'}

    @callback(
        Output("workflow-resolution-population-container", "style"),
        [Input("workflow-resolution-view-state", "data")],
        prevent_initial_call=False
    )
    def toggle_population_selector_visibility(view_state):
        """Show population selector for Statistics and Distribution views"""
        if view_state in ["stats", "dist"]:
            return {'display': 'block', 'marginBottom': '15px'}
        else:
            return {'display': 'none'}
        
    # Callback to conditionally hide/show chart container for statistics view
    # @callback(
    #     Output("workflow-resolution-times-chart", "style"),
    #     [Input("workflow-resolution-view-state", "data")],
    #     prevent_initial_call=False
    # )
    # def toggle_chart_visibility(view_state):
    #     """Hide chart completely when showing statistics view, show for all others"""
    #     if view_state == "stats":
    #         return {'display': 'none'}
    #     else:
    #         return {'display': 'block', 'height': '450px'}  # Explicitly set height and display   
    
    print("✅ Workflow resolution times callbacks registered")