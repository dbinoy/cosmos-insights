from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance

@monitor_query_performance("Status Distribution Base Data")
def get_status_distribution_base_data():
    """
    Fetch base data for ticket status distribution analysis
    Uses consumable fact tables with minimal joins
    """
    
    queries = {
        # Get work items data with status information
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
                w.Product
            FROM [consumable].[Fact_WorkFlowItems] w
        """,
        
        # Get status transitions for trend analysis
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
        """,
        
        # Get item status details for better categorization
        "item_status": """
            SELECT DISTINCT
                its.Status,
                its.StatusId,
                its.Item,
                its.ItemShortCode
            FROM [consumable].[Dim_ItemStatus] its
        """
    }

    return run_queries(queries, 'workflow', len(queries))

def apply_status_distribution_filters(work_items, stored_selections):
    """
    Apply filters to base status distribution data using pandas
    Same pattern as workflow ticket volume
    """
    print(f"🔍 Applying status distribution filters: {stored_selections}")
    if not stored_selections:
        stored_selections = {}
    
    # Convert to DataFrames and create explicit copies
    df_work_items = pd.DataFrame(work_items).copy()
    
    print(f"📊 Starting status distribution filtering: {len(df_work_items)} work item records")
    
    if df_work_items.empty:
        return df_work_items
    
    # Parse filter values (same logic as ticket volume)
    selected_aor = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('AOR', '').split(', ') if item.strip("'")]
    selected_case_types = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('CaseTypes', '').split(', ') if item.strip("'")]
    selected_status = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Status', '').split(', ') if item.strip("'")]
    selected_priority = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Priority', '').split(', ') if item.strip("'")]
    selected_origins = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Origins', '').split(', ') if item.strip("'")]
    selected_reasons = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Reasons', '').split(', ') if item.strip("'")]
    selected_products = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Products', '').split(', ') if item.strip("'")]
    selected_features = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Features', '').split(', ') if item.strip("'")]
    selected_modules = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Modules', '').split(', ') if item.strip("'")]
    selected_issues = [item.strip("'") if item != "'-'" else "" for item in stored_selections.get('Issues', '').split(', ') if item.strip("'")]
    start_date = stored_selections.get('StartDate')
    end_date = stored_selections.get('EndDate')
    
    # Parse dates
    if not df_work_items.empty:
        df_work_items['CreatedOn'] = pd.to_datetime(df_work_items['CreatedOn'], errors='coerce')
        df_work_items['ClosedOn'] = pd.to_datetime(df_work_items['ClosedOn'], errors='coerce')
        df_work_items = df_work_items.dropna(subset=['CreatedOn']).copy()

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
    if selected_aor is not None and len(selected_aor) > 0 and "All" not in selected_aor:
        df_work_items = df_work_items.loc[df_work_items['AorShortName'].isin(selected_aor)].copy()
        print(f"🎯 AOR filter applied: {len(df_work_items)} records")

    if selected_case_types is not None and len(selected_case_types) > 0 and "All" not in selected_case_types:
        df_work_items = df_work_items.loc[df_work_items['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
        print(f"📋 Case Type filter applied: {len(df_work_items)} records")

    if selected_products is not None and len(selected_products) > 0 and "All" not in selected_products:
        df_work_items = df_work_items.loc[df_work_items['Product'].isin(selected_products)].copy()
        print(f"🛍️ Product filter applied: {len(df_work_items)} records")

    if selected_modules is not None and len(selected_modules) > 0 and "All" not in selected_modules:
        df_work_items = df_work_items.loc[df_work_items['Module'].isin(selected_modules)].copy()
        print(f"🧩 Module filter applied: {len(df_work_items)} records")
        
    if selected_features is not None and len(selected_features) > 0 and "All" not in selected_features:
        df_work_items = df_work_items.loc[df_work_items['Feature'].isin(selected_features)].copy()
        print(f"⭐ Feature filter applied: {len(df_work_items)} records")

    if selected_issues is not None and len(selected_issues) > 0 and "All" not in selected_issues:
        df_work_items = df_work_items.loc[df_work_items['Issue'].isin(selected_issues)].copy()
        print(f"🐛 Issue filter applied: {len(df_work_items)} records")

    if selected_origins is not None and len(selected_origins) > 0 and "All" not in selected_origins:
        df_work_items = df_work_items.loc[df_work_items['CaseOrigin'].isin(selected_origins)].copy()
        print(f"📍 Origin filter applied: {len(df_work_items)} records")

    if selected_reasons is not None and len(selected_reasons) > 0 and "All" not in selected_reasons:
        df_work_items = df_work_items.loc[df_work_items['CaseReason'].isin(selected_reasons)].copy()
        print(f"📝 Reason filter applied: {len(df_work_items)} records")

    if selected_status is not None and len(selected_status) > 0 and "All" not in selected_status:
        df_work_items = df_work_items.loc[df_work_items['WorkItemStatus'].isin(selected_status)].copy()
        print(f"📊 Status filter applied: {len(df_work_items)} records")

    if selected_priority is not None and len(selected_priority) > 0 and "All" not in selected_priority:
        df_work_items = df_work_items.loc[df_work_items['Priority'].isin(selected_priority)].copy()
        print(f"⚡ Priority filter applied: {len(df_work_items)} records")
    
    return df_work_items

@monitor_performance("Status Distribution Data Preparation")
def prepare_status_distribution_data(filtered_data, status_transitions_data, item_status_data):
    """
    Prepare status distribution data for visualization
    Now uses all three data sources for enhanced insights
    """
    if filtered_data.empty:
        return pd.DataFrame()
    
    try:
        df = filtered_data.copy()
        
        # Fix: Check if data exists and convert properly
        if status_transitions_data is not None and len(status_transitions_data) > 0:
            df_transitions = pd.DataFrame(status_transitions_data).copy()
        else:
            df_transitions = pd.DataFrame()
            
        if item_status_data is not None and len(item_status_data) > 0:
            df_item_status = pd.DataFrame(item_status_data).copy()
        else:
            df_item_status = pd.DataFrame()
        
        # Calculate status distribution
        status_counts = df['WorkItemStatus'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        
        # Calculate percentages
        total_tickets = status_counts['Count'].sum()
        status_counts['Percentage'] = (status_counts['Count'] / total_tickets * 100).round(1)
        
        # Enhanced status categorization using dimension table data
        def categorize_status_enhanced(status):
            if pd.isna(status):
                return 'Unknown'
            
            # First try to match with dimension table
            if not df_item_status.empty:
                matching_status = df_item_status[df_item_status['Status'].str.lower() == str(status).lower()]
                if not matching_status.empty:
                    item_type = matching_status.iloc[0]['Item']
                    if pd.notna(item_type):
                        item_lower = str(item_type).lower()
                        if any(term in item_lower for term in ['open', 'new', 'created']):
                            return 'Open'
                        elif any(term in item_lower for term in ['progress', 'working', 'active']):
                            return 'In Progress'
                        elif any(term in item_lower for term in ['escalated', 'escalation']):
                            return 'Escalated'
                        elif any(term in item_lower for term in ['closed', 'resolved', 'completed']):
                            return 'Closed'
                        elif any(term in item_lower for term in ['hold', 'waiting', 'pending']):
                            return 'On Hold'
            
            # Fallback to original categorization logic
            status_lower = str(status).lower()
            if any(term in status_lower for term in ['open', 'new', 'created', 'not started']):
                return 'Open'
            elif any(term in status_lower for term in ['in progress', 'working', 'assigned', 'active']):
                return 'In Progress'
            elif any(term in status_lower for term in ['escalated', 'escalation']):
                return 'Escalated'
            elif any(term in status_lower for term in ['closed', 'resolved', 'completed', 'done']):
                return 'Closed'
            elif any(term in status_lower for term in ['hold', 'waiting', 'pending']):
                return 'On Hold'
            elif any(term in status_lower for term in ['cancelled', 'canceled']):
                return 'Cancelled'
            else:
                return 'Other'
        
        status_counts['StatusCategory'] = status_counts['Status'].apply(categorize_status_enhanced)
        
        # Add escalation information
        escalated_counts = df[df['IsEscalated'] == '1']['WorkItemStatus'].value_counts()
        status_counts['EscalatedCount'] = status_counts['Status'].map(escalated_counts).fillna(0)
        status_counts['EscalationRate'] = (status_counts['EscalatedCount'] / status_counts['Count'] * 100).round(1)
        
        # Add transition insights using status_transitions data
        if not df_transitions.empty and not df.empty:
            # Get work item IDs for filtered data
            filtered_work_item_ids = set(df['WorkItemId'].tolist())
            
            # Filter transitions to only include relevant work items
            relevant_transitions = df_transitions[
                df_transitions['WorkItemId'].isin(filtered_work_item_ids)
            ].copy()
            
            if not relevant_transitions.empty:
                # Parse transition dates
                relevant_transitions['StatusFromDate'] = pd.to_datetime(relevant_transitions['StatusFromDate'], errors='coerce')
                relevant_transitions['StatusToDate'] = pd.to_datetime(relevant_transitions['StatusToDate'], errors='coerce')
                
                # Calculate average time spent in each status
                status_durations = relevant_transitions.groupby('FromStatusName')['DurationMinutes'].agg(['mean', 'count']).reset_index()
                status_durations.columns = ['Status', 'AvgDurationMinutes', 'TransitionCount']
                
                # Merge with status counts
                status_counts = status_counts.merge(status_durations, on='Status', how='left')
                status_counts['AvgDurationMinutes'] = status_counts['AvgDurationMinutes'].fillna(0)
                status_counts['TransitionCount'] = status_counts['TransitionCount'].fillna(0)
                
                # Calculate status "stickiness" (how long tickets stay in each status)
                status_counts['StatusStickiness'] = status_counts['AvgDurationMinutes'] / 60  # Convert to hours
            else:
                status_counts['AvgDurationMinutes'] = 0
                status_counts['TransitionCount'] = 0
                status_counts['StatusStickiness'] = 0
        else:
            status_counts['AvgDurationMinutes'] = 0
            status_counts['TransitionCount'] = 0
            status_counts['StatusStickiness'] = 0
        
        # Sort by count for better visualization
        status_counts = status_counts.sort_values('Count', ascending=False).reset_index(drop=True)
        
        print(f"📊 Prepared enhanced status distribution data: {len(status_counts)} status types with transition insights")
        return status_counts
        
    except Exception as e:
        print(f"❌ Error preparing status distribution data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def create_status_breakdown_table(status_data):
    """
    Create a detailed breakdown table showing all statuses
    This complements the grouped pie chart and will be displayed in a modal
    """
    if status_data.empty:
        return html.Div("No status data available", className="text-center text-muted p-4")
    
    try:
        # Sort by count descending
        df_sorted = status_data.sort_values('Count', ascending=False).reset_index(drop=True)
        
        # Create table rows
        table_rows = []
        for i, row in df_sorted.iterrows():
            # Color indicator based on status category
            status_colors = {
                'Open': '#E74C3C', 'In Progress': '#3498DB', 'Escalated': '#E67E22',
                'Closed': '#2ECC71', 'On Hold': '#F39C12', 'Cancelled': '#95A5A6', 'Other': '#9B59B6'
            }
            color = status_colors.get(row['StatusCategory'], '#7F8C8D')
            
            # Format duration - simplified to just show hours
            duration_display = ""
            if 'StatusStickiness' in row and pd.notna(row['StatusStickiness']) and row['StatusStickiness'] > 0:
                duration_display = f"{row['StatusStickiness']:.1f}h"
            else:
                duration_display = "—"
            
            table_rows.append(
                html.Tr([
                    html.Td([
                        html.Div(style={
                            'width': '14px', 'height': '14px', 'backgroundColor': color,
                            'borderRadius': '50%', 'display': 'inline-block', 'marginRight': '10px'
                        }),
                        html.Span(row['Status'], style={
                            'fontWeight': 'bold' if i < 3 else '500' if i < 8 else 'normal'
                        })
                    ], style={'verticalAlign': 'middle'}),
                    html.Td(f"{row['Count']:,}", className="text-end fw-bold"),
                    html.Td(f"{row['Percentage']:.1f}%", className="text-end"),
                    html.Td([
                        html.Span(row['StatusCategory'], className="badge rounded-pill", style={
                            'backgroundColor': color, 'color': 'white', 'fontSize': '11px'
                        })
                    ], className="text-center"),
                    html.Td(f"{row['EscalatedCount']:.0f}", className="text-end"),
                    html.Td(f"{row['EscalationRate']:.1f}%", className="text-end"),
                    html.Td(duration_display, className="text-end")  # Changed to match Esc. Rate formatting
                ], style={
                    'fontSize': '14px', 
                    'backgroundColor': '#f8f9fa' if i < 3 else 'white',
                    'borderLeft': f'4px solid {color}'
                })
            )
        
        # Create summary statistics
        total_tickets = df_sorted['Count'].sum()
        total_escalated = df_sorted['EscalatedCount'].sum()
        avg_escalation_rate = (total_escalated / total_tickets * 100) if total_tickets > 0 else 0
        
        return html.Div([
            # Header with summary stats
            dbc.Row([
                dbc.Col([
                    html.H4("Complete Status Breakdown", className="mb-3 text-primary"),
                    html.P([
                        html.Span([
                            html.I(className="fas fa-tickets-alt me-2"),
                            f"Total: {total_tickets:,} tickets across {len(df_sorted)} statuses"
                        ], className="me-4"),
                        html.Span([
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            f"Escalated: {total_escalated:,.0f} ({avg_escalation_rate:.1f}%)"
                        ])
                    ], className="text-muted mb-4")
                ])
            ]),
            
            # Enhanced table with better styling
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("Status", style={'width': '30%', 'borderBottom': '2px solid #dee2e6'}),
                            html.Th("Count", className="text-end", style={'width': '12%', 'borderBottom': '2px solid #dee2e6'}),
                            html.Th("Percentage", className="text-end", style={'width': '10%', 'borderBottom': '2px solid #dee2e6'}),
                            html.Th("Category", className="text-center", style={'width': '15%', 'borderBottom': '2px solid #dee2e6'}),
                            html.Th("Escalated", className="text-end", style={'width': '10%', 'borderBottom': '2px solid #dee2e6'}),
                            html.Th("Esc. Rate", className="text-end", style={'width': '10%', 'borderBottom': '2px solid #dee2e6'}),
                            html.Th("Avg. Duration", className="text-end", style={'width': '13%', 'borderBottom': '2px solid #dee2e6'})  # Changed header and alignment
                        ], style={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'})
                    ]),
                    html.Tbody(table_rows)
                ], className="table table-hover"),
            ], style={'maxHeight': '500px', 'overflowY': 'auto', 'border': '1px solid #dee2e6', 'borderRadius': '8px'}),
        ], className="p-3")
        
    except Exception as e:
        print(f"❌ Error creating status breakdown table: {e}")
        return html.Div([
            html.H4("Error Creating Status Breakdown", className="text-danger mb-3"),
            html.P(f"Unable to generate detailed breakdown: {str(e)}", className="text-muted")
        ], className="text-center p-4")
    
def register_workflow_status_distribution_callbacks(app):
    """
    Register ticket status distribution callbacks
    Matches the component IDs from the layout file
    """
    @monitor_chart_performance("Status Distribution Chart")
    def create_status_distribution_chart(status_data):
        """
        Create interactive status distribution chart using plotly.graph_objects
        Uses intelligent grouping for better readability with many statuses
        """
        if status_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No status distribution data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Ticket Status Distribution",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
        
        try:
            # Intelligent grouping strategy for better readability
            def group_statuses_intelligently(df):
                """
                Group statuses intelligently to show top statuses individually and group smaller ones
                """
                df_sorted = df.sort_values('Count', ascending=False).reset_index(drop=True)
                
                # Strategy: Show top statuses that together make up 90% of tickets
                cumulative_percentage = df_sorted['Percentage'].cumsum()
                
                # Find the cutoff for major statuses (top statuses that make up 85% of data)
                major_cutoff = len(cumulative_percentage[cumulative_percentage <= 85])
                if major_cutoff < 3:  # Always show at least top 3
                    major_cutoff = min(3, len(df_sorted))
                elif major_cutoff > 8:  # Never show more than 8 individual statuses
                    major_cutoff = 8
                
                # Split into major and minor statuses
                major_statuses = df_sorted.iloc[:major_cutoff].copy()
                minor_statuses = df_sorted.iloc[major_cutoff:].copy()
                
                # Create grouped data
                grouped_data = major_statuses.copy()
                
                if not minor_statuses.empty:
                    # Group minor statuses by category for better insights
                    minor_by_category = minor_statuses.groupby('StatusCategory').agg({
                        'Count': 'sum',
                        'Percentage': 'sum',
                        'EscalatedCount': 'sum',
                        'Status': lambda x: ', '.join(x.head(3).tolist()) + (f' (+{len(x)-3} more)' if len(x) > 3 else '')
                    }).reset_index()
                    
                    # Add grouped entries
                    for _, category_group in minor_by_category.iterrows():
                        if category_group['Count'] > 0:  # Only add non-empty groups
                            grouped_entry = {
                                'Status': f"Other {category_group['StatusCategory']} ({category_group['Count']:,} tickets)",
                                'Count': category_group['Count'],
                                'Percentage': category_group['Percentage'],
                                'StatusCategory': category_group['StatusCategory'],
                                'EscalatedCount': category_group['EscalatedCount'],
                                'EscalationRate': (category_group['EscalatedCount'] / category_group['Count'] * 100) if category_group['Count'] > 0 else 0,
                                'DetailedStatuses': category_group['Status']  # Store the detailed breakdown
                            }
                            grouped_data = pd.concat([grouped_data, pd.DataFrame([grouped_entry])], ignore_index=True)
                
                return grouped_data.sort_values('Count', ascending=False).reset_index(drop=True)
            
            # Apply intelligent grouping
            # Apply intelligent grouping
            display_data = group_statuses_intelligently(status_data)
            
            # Create consistent labels for all entries (both individual and grouped)
            enhanced_labels = []
            for _, row in display_data.iterrows():
                if row['Status'].startswith('Other '):
                    # Keep the existing grouped format
                    enhanced_labels.append(row['Status'])
                else:
                    # Add ticket count to individual status entries for consistency
                    enhanced_labels.append(f"{row['Status']} ({row['Count']:,})")
            
            # Define colors for different status categories
            status_colors = {
                'Open': '#E74C3C',          # Red
                'In Progress': '#3498DB',    # Blue
                'Escalated': '#E67E22',      # Orange
                'Closed': '#2ECC71',         # Green
                'On Hold': '#F39C12',        # Yellow/Orange
                'Cancelled': '#95A5A6',      # Gray
                'Other': '#9B59B6'           # Purple
            }
            
            # Map colors to statuses
            colors = [status_colors.get(cat, '#7F8C8D') for cat in display_data['StatusCategory']]
            
            # Create enhanced hover template with detailed information
            hover_texts = []
            for _, row in display_data.iterrows():
                base_hover = f"<b>{row['Status']}</b><br>"
                base_hover += f"Count: {row['Count']:,.0f}<br>"
                base_hover += f"Percentage: {row['Percentage']:.1f}%<br>"
                base_hover += f"Escalated: {row['EscalatedCount']:.0f} ({row['EscalationRate']:.1f}%)<br>"
                
                # Add detailed breakdown for grouped statuses
                if 'DetailedStatuses' in row and pd.notna(row['DetailedStatuses']):
                    base_hover += f"<br><i>Includes: {row['DetailedStatuses']}</i>"
                
                hover_texts.append(base_hover)
            
            # Create pie chart with better sizing and consistent labels
            fig = go.Figure(data=[
                go.Pie(
                    labels=enhanced_labels,  # Use the enhanced labels with consistent formatting
                    values=display_data['Count'],
                    hole=0.5,  # Larger hole for better readability of center text
                    marker=dict(
                        colors=colors,
                        line=dict(color='white', width=3)  # Thicker lines for better separation
                    ),
                    textinfo='label+percent',
                    textposition='outside',
                    textfont=dict(size=11),  # Slightly larger text
                    hovertemplate="%{customdata}<extra></extra>",
                    customdata=hover_texts,
                    sort=False,  # Keep original order (sorted by count)
                    pull=[0.05 if i < 3 else 0 for i in range(len(display_data))]  # Slightly pull out top 3 slices
                )
            ])
                        
            # Add center text showing total tickets and status count
            total_tickets = status_data['Count'].sum()
            total_statuses = len(status_data)
            center_text = f"<b>{total_tickets:,}</b><br>Total Tickets<br><span style='font-size:12px'>{total_statuses} Statuses</span>"
            
            fig.add_annotation(
                text=center_text,
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False
            )
            
            # Update layout with better spacing and legend positioning
            fig.update_layout(
                title={
                    'text': f"Ticket Status Distribution ({len(display_data)} groups shown)",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                showlegend=False,
                legend=dict(
                    orientation="h",  # Horizontal orientation for bottom placement
                    yanchor="top",
                    y=-0.05,  # Position below the chart
                    xanchor="center",
                    x=0.5,  # Center horizontally
                    font=dict(size=10),
                    itemwidth=30,
                    # Control spacing and layout
                    bordercolor="rgba(0,0,0,0)",
                    borderwidth=0,
                    # Make legend items more compact
                    itemclick="toggleothers",  # Better interaction
                    itemdoubleclick="toggle"
                ),
                height=380,  # Increased height to accommodate bottom legend
                margin={'l': 30, 'r': 30, 't': 30, 'b': 30},  # More space at bottom, less on sides
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=11),
                # Ensure pie chart has more space
                autosize=True
            )
            print(f"📊 Created grouped status distribution chart: {len(status_data)} statuses grouped into {len(display_data)} segments")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating status distribution chart: {e}")
            # Return proper error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Ticket Status Distribution - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_performance("Status Distribution Insights Generation")
    def generate_status_distribution_insights(status_data, filtered_data, transitions_data):
        """
        Generate automated insights from status distribution data
        Always returns exactly 3 insights for consistency:
        1. Unresolved tickets count and percentage
        2. Escalation status and rate
        3. Bottleneck status (longest duration)
        """
        if status_data.empty or filtered_data.empty:
            return html.Div([
                html.Div([html.Span("📊 No data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see status insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("📈 Data will appear when tickets match your criteria", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        try:
            # Fix: Check transitions data properly
            if transitions_data is not None and len(transitions_data) > 0:
                df_transitions = pd.DataFrame(transitions_data).copy()
            else:
                df_transitions = pd.DataFrame()
            
            # Calculate key metrics for the 3 focused insights
            total_tickets = status_data['Count'].sum()
            
            # 1. UNRESOLVED TICKETS - Calculate unresolved tickets (everything except closed)
            closed_tickets = status_data[status_data['StatusCategory'] == 'Closed']['Count'].sum()
            unresolved_tickets = total_tickets - closed_tickets
            unresolved_percentage = (unresolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
            
            # 2. ESCALATION STATUS - Fix: Use .sum() to get scalar value
            escalated_mask = filtered_data['IsEscalated'] == '1'
            total_escalated = escalated_mask.sum()  # This returns a scalar, not a Series
            escalation_rate = (total_escalated / total_tickets * 100) if total_tickets > 0 else 0
            
            # 3. BOTTLENECK ANALYSIS - Find status causing longest delays
            bottleneck_info = None
            if not df_transitions.empty and 'StatusStickiness' in status_data.columns:
                # Find the status with highest average duration (bottleneck)
                if status_data['StatusStickiness'].max() > 0:
                    max_stickiness_idx = status_data['StatusStickiness'].idxmax()
                    bottleneck_status = status_data.loc[max_stickiness_idx]
                    if bottleneck_status['StatusStickiness'] > 1:  # More than 1 hour
                        bottleneck_info = {
                            'status': bottleneck_status['Status'],
                            'duration': bottleneck_status['StatusStickiness'],
                            'count': bottleneck_status['Count']
                        }
            
            # Always generate exactly 3 insights
            insights = []
            
            # Insight 1: Unresolved Tickets
            if unresolved_tickets > 0:
                insights.append(f"⚠️ Unresolved Tickets: {unresolved_tickets:,} tickets ({unresolved_percentage:.1f}%) require attention and are not yet closed")
            else:
                insights.append(f"✅ Resolution Status: All {total_tickets:,} tickets in selection are resolved (100% closure rate)")
            
            # Insight 2: Escalation Status
            if total_escalated > 0:
                escalation_severity = "high" if escalation_rate > 10 else "moderate" if escalation_rate > 5 else "low"
                insights.append(f"🚨 Escalation Status: {total_escalated:,} tickets escalated ({escalation_rate:.1f}% rate) - {escalation_severity} escalation activity")
            else:
                insights.append(f"🎯 Escalation Status: No escalated tickets found ({escalation_rate:.1f}% escalation rate) - smooth operations")
            
            # Insight 3: Bottleneck Analysis
            if bottleneck_info:
                duration_desc = f"{bottleneck_info['duration']:.1f} hours" if bottleneck_info['duration'] < 24 else f"{bottleneck_info['duration']/24:.1f} days"
                insights.append(f"⏱️ Bottleneck Status: '{bottleneck_info['status']}' holds {bottleneck_info['count']:,} tickets for avg {duration_desc}")
            else:
                # Fallback when no bottleneck data available
                top_status = status_data.iloc[0] if len(status_data) > 0 else None
                if top_status:
                    insights.append(f"🏆 Status Focus: '{top_status['Status']}' contains most tickets ({top_status['Count']:,} tickets, {top_status['Percentage']:.1f}%)")
                else:
                    insights.append(f"📊 Status Distribution: Tickets spread across {len(status_data)} different statuses")
            
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
            print(f"❌ Error generating status distribution insights: {e}")
            import traceback
            traceback.print_exc()
            # Return 3 error insights for consistency
            return html.Div([
                html.Div([html.Span("❌ **Error: Unable to generate status insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
                               
    @callback(
        [Output("workflow-status-distribution-chart", "figure"),
         Output("workflow-status-insights", "children")],
        [Input("workflow-filtered-query-store", "data")],
        prevent_initial_call=False
    )
    @monitor_performance("Status Distribution Chart Update")
    def update_status_distribution_chart(stored_selections):
        """
        Update status distribution chart based on filter selections
        Now includes View Details button next to the chart
        """
        try:
            print(f"🔄 Updating status distribution chart")
            
            # Get base data (all three queries)
            base_data = get_status_distribution_base_data()
            
            # Apply filters to work items
            filtered_data = apply_status_distribution_filters(base_data['work_items'], stored_selections)
            
            # Prepare status distribution data using all three datasets
            status_data = prepare_status_distribution_data(
                filtered_data, 
                base_data['status_transitions'], 
                base_data['item_status']
            )
            
            # Create visualization
            fig = create_status_distribution_chart(status_data)
            
            # Generate insights using transitions data
            insights = generate_status_distribution_insights(
                status_data, 
                filtered_data, 
                base_data['status_transitions']
            )
            
            # Return just the insights (button will be in the layout next to chart)
            print(f"✅ Status distribution chart updated successfully")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating status distribution chart: {e}")
            
            # Return error chart and message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading status distribution data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Ticket Status Distribution - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig, f"Error generating insights: {str(e)}"
        
    # print("✅ Workflow status distribution callbacks registered")       

def register_workflow_status_distribution_modal_callbacks(app):
    """
    Register callbacks for workflow status distribution chart modal functionality
    Now includes status details modal
    """
    print("Registering Workflow Status Distribution Chart Modal callbacks...")

    @monitor_chart_performance("Enlarged Status Distribution Chart")
    def create_enlarged_status_distribution_chart(original_figure):
        """
        Create an enlarged version of the status distribution chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            # Create a deep copy of the original figure
            enlarged_fig = copy.deepcopy(original_figure)
            
            enlarged_fig['layout'].update({
                'height': 650,  # Increased height for modal
                'margin': {'l': 40, 'r': 200, 't': 100, 'b': 80},  # More space on right for legend
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}  
                },
                # Enable legend for enlarged chart positioned on the right
                'showlegend': True,  # Override to True for modal
                'legend': {
                    'orientation': 'v',  # Vertical orientation for right side
                    'yanchor': 'middle',
                    'y': 0.5,  # Center vertically
                    'xanchor': 'left',
                    'x': 1.02,  # Position to the right of the chart
                    'font': {'size': 12},  # Slightly larger font for modal
                    'bordercolor': "rgba(0,0,0,0)",
                    'borderwidth': 0,
                    'itemclick': "toggleothers",
                    'itemdoubleclick': "toggle",
                    'bgcolor': "rgba(255,255,255,0)",
                    'itemsizing': "constant",
                    # Add some spacing between legend items for vertical layout
                    'tracegroupgap': 5
                }
            })
            
            # Update pie chart for better visibility in larger chart
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') == 'pie':
                        # Make pie chart elements more visible
                        trace.update({
                            'textfont': {'size': 12},
                            'marker': {
                                **trace.get('marker', {}),
                                'line': {'color': 'white', 'width': 3}
                            }
                        })
            
            # Update center annotation if present
            annotations = enlarged_fig['layout'].get('annotations', [])
            for annotation in annotations:
                if annotation.get('x') == 0.5 and annotation.get('y') == 0.5:
                    annotation['font'] = {'size': 20}
            
            # Create the chart component
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True, 
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'workflow_status_distribution_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '600px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged status distribution chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )
           
    @callback(
        [Output("workflow-chart-modal", "is_open", allow_duplicate=True),
        Output("workflow-modal-chart-content", "children", allow_duplicate=True)],
        [Input("workflow-status-chart-wrapper", "n_clicks")],
        [State("workflow-chart-modal", "is_open"),
        State("workflow-status-distribution-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Status Distribution Modal Toggle")
    def toggle_status_distribution_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """Handle opening of status distribution chart modal using SHARED modal"""
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        if triggered_id == "workflow-status-chart-wrapper" and chart_wrapper_clicks and not is_open:
            print("📊 Status distribution chart wrapper clicked! Opening modal...")
            
            if not chart_figure or not chart_figure.get('data'):
                return no_update, no_update
            
            # Use the dedicated enlarged chart function instead of simplified version
            enlarged_chart = create_enlarged_status_distribution_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update

    @callback(
        [Output("workflow-status-details-modal", "is_open"),
         Output("workflow-status-details-content", "children")],
        [Input("workflow-status-details-btn", "n_clicks")],
        [State("workflow-status-details-modal", "is_open"),
         State("workflow-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    @monitor_performance("Status Details Modal Toggle")
    def toggle_status_details_modal(details_btn_clicks, is_open, stored_selections):
        """Handle opening of status details modal with complete breakdown table"""
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        print(f"🔄 Status Details Modal callback triggered by: {triggered_id}")
        
        if triggered_id == "workflow-status-details-btn" and details_btn_clicks:
            print("📊 Status details button clicked! Opening/closing modal...")
            
            if not is_open:
                # Opening modal - generate fresh data
                try:
                    print("🔄 Generating fresh status data for details modal...")
                    
                    # Get base data using the moved functions
                    base_data = get_status_distribution_base_data()
                    
                    # Apply filters
                    filtered_data = apply_status_distribution_filters(base_data['work_items'], stored_selections)
                    
                    # Prepare status data
                    status_data = prepare_status_distribution_data(
                        filtered_data, 
                        base_data['status_transitions'], 
                        base_data['item_status']
                    )
                    
                    # Create detailed table
                    detailed_table = create_status_breakdown_table(status_data)
                    
                    print("✅ Opening status details modal with fresh data")
                    return True, detailed_table
                    
                except Exception as e:
                    print(f"❌ Error generating status details: {e}")
                    import traceback
                    traceback.print_exc()
                    error_content = html.Div([
                        html.H4("Error Loading Status Details", className="text-danger mb-3"),
                        html.P(f"Unable to load detailed breakdown: {str(e)}", className="text-muted")
                    ], className="text-center p-4")
                    return True, error_content
            else:
                # Closing modal
                print("📊 Closing status details modal")
                return False, no_update
        
        return no_update, no_update

    # Close button callback for status details modal
    @callback(
        Output("workflow-status-details-modal", "is_open", allow_duplicate=True),
        [Input("workflow-status-details-close-btn", "n_clicks")],
        [State("workflow-status-details-modal", "is_open")],
        prevent_initial_call=True
    )
    def close_status_details_modal(close_clicks, is_open):
        """Close the status details modal when close button is clicked"""
        if close_clicks and is_open:
            print("📊 Closing status details modal via close button")
            return False
        return no_update
    # print("✅ Workflow Status Distribution Chart Modal callbacks registered successfully")
