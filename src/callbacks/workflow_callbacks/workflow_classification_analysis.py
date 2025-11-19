from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from src.utils.db import run_queries
import time
import copy
from functools import wraps
from src.utils.performance import monitor_performance, monitor_query_performance, monitor_chart_performance
from inflection import titleize

def register_workflow_classification_analysis_callbacks(app):
    """
    Register ticket classification analysis callbacks
    Matches the component IDs from the layout file
    """
    
    @monitor_query_performance("Classification Analysis Base Data")
    def get_classification_analysis_base_data():
        """
        Fetch base data for ticket classification analysis
        Uses consumable fact tables with minimal joins
        """
        
        queries = {
            # Get work items data with classification information
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
            
            # Get case type mapping for proper display names
            "case_types": """
                SELECT DISTINCT 
                    CaseTypeCode,
                    CaseTypeName,
                    CaseOrigin,
                    CaseReason
                FROM [consumable].[Dim_WorkItemAttributes]
                WHERE CaseTypeCode IS NOT NULL
            """,
            
            # Get additional classification dimensions
            "classification_dims": """
                SELECT DISTINCT
                    Product,
                    Module,
                    Feature,
                    Issue,
                    Priority
                FROM [consumable].[Dim_WorkItemAttributes]
                WHERE Product IS NOT NULL OR Module IS NOT NULL
            """
        }

        return run_queries(queries, 'workflow', len(queries))

    def apply_classification_analysis_filters(work_items, stored_selections):
        """
        Apply filters to base classification analysis data using pandas
        Same pattern as other workflow callbacks
        """
        if not stored_selections:
            stored_selections = {}
        
        # Convert to DataFrames and create explicit copies
        df_work_items = pd.DataFrame(work_items).copy()
        
        print(f"📊 Starting classification analysis filtering: {len(df_work_items)} work item records")
        
        if df_work_items.empty:
            return df_work_items
        
        # Parse filter values (same logic as other callbacks)
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

    @monitor_performance("Classification Analysis Data Preparation")
    def prepare_classification_analysis_data(filtered_data, case_types_data, view_type="stacked"):
        """
        Prepare classification analysis data for visualization
        Creates cross-tabulation of case types vs classification dimensions
        UPDATED: Added simple formatting using titleize for case origins and other dimensions
        """
        if filtered_data.empty:
            return pd.DataFrame(), {}
        
        try:
            df = filtered_data.copy()
            
            # Get case type mapping for proper display names
            case_type_mapping = {}
            if case_types_data is not None and len(case_types_data) > 0:
                df_case_types = pd.DataFrame(case_types_data).copy()
                case_type_mapping = dict(zip(df_case_types['CaseTypeCode'], df_case_types['CaseTypeName']))
            
            # Handle missing values and create proper labels
            df['WorkItemDefinitionShortCode'] = df['WorkItemDefinitionShortCode'].fillna('Unspecified')
            df['CaseOrigin'] = df['CaseOrigin'].fillna('Unspecified')
            df['Priority'] = df['Priority'].fillna('Unspecified')
            df['Product'] = df['Product'].fillna('Unspecified')
            
            # UPDATED: Simple formatting function using titleize
            def format_for_display(value):
                if pd.isna(value) or value == '' or value == 'Unspecified':
                    return 'Unspecified'
                # Simple formatting: replace underscores, hyphens, handle N/A, then titleize
                formatted = str(value).replace('_', ' ').replace('-', ' ').replace('N/A', '').strip()
                return titleize(formatted) if formatted else 'Unspecified'
            
            # Create display names for case types
            def get_case_type_display_name(code):
                if pd.isna(code) or code == '' or code == 'Unspecified':
                    return 'Unspecified'
                return case_type_mapping.get(code, format_for_display(code))
            
            # Apply formatting to create display columns
            df['CaseTypeDisplay'] = df['WorkItemDefinitionShortCode'].apply(get_case_type_display_name)
            df['CaseOriginDisplay'] = df['CaseOrigin'].apply(format_for_display)  # ADDED: Formatted case origin
            df['PriorityDisplay'] = df['Priority'].apply(format_for_display)  # ADDED: Formatted priority
            df['ProductDisplay'] = df['Product'].apply(format_for_display)  # ADDED: Formatted product
            
            # Create cross-tabulation matrices for different classification dimensions
            analysis_data = {}
            
            # UPDATED: Case Type vs Case Origin (using formatted display names)
            case_origin_crosstab = pd.crosstab(
                df['CaseTypeDisplay'], 
                df['CaseOriginDisplay'],  # Use formatted display names
                margins=True, margins_name="Total"
            )
            analysis_data['case_origin'] = case_origin_crosstab
            
            # UPDATED: Case Type vs Priority (using formatted display names)
            priority_crosstab = pd.crosstab(
                df['CaseTypeDisplay'], 
                df['PriorityDisplay'],  # Use formatted display names
                margins=True, margins_name="Total"
            )
            analysis_data['priority'] = priority_crosstab
            
            # UPDATED: Case Type vs Product (using formatted display names, top 10 products to avoid overcrowding)
            product_counts = df['ProductDisplay'].value_counts().head(10)  # Use formatted names for counting
            top_products = product_counts.index.tolist()
            df_top_products = df[df['ProductDisplay'].isin(top_products)].copy()
            
            if not df_top_products.empty:
                product_crosstab = pd.crosstab(
                    df_top_products['CaseTypeDisplay'], 
                    df_top_products['ProductDisplay'],  # Use formatted display names
                    margins=True, margins_name="Total"
                )
                analysis_data['product'] = product_crosstab
            else:
                analysis_data['product'] = pd.DataFrame()
            
            # UPDATED: Overall summary statistics (using formatted names for top items)
            summary_stats = {
                'total_tickets': len(df),
                'unique_case_types': df['CaseTypeDisplay'].nunique(),
                'unique_origins': df['CaseOriginDisplay'].nunique(),  # Use formatted names
                'unique_priorities': df['PriorityDisplay'].nunique(),  # Use formatted names
                'unique_products': df['ProductDisplay'].nunique(),  # Use formatted names
                'top_case_type': df['CaseTypeDisplay'].mode().iloc[0] if not df['CaseTypeDisplay'].mode().empty else 'N/A',
                'top_origin': df['CaseOriginDisplay'].mode().iloc[0] if not df['CaseOriginDisplay'].mode().empty else 'N/A',  # Use formatted names
                'top_priority': df['PriorityDisplay'].mode().iloc[0] if not df['PriorityDisplay'].mode().empty else 'N/A'  # Use formatted names
            }
            
            print(f"📊 Prepared classification analysis data with titleized labels: {len(df)} tickets across {summary_stats['unique_case_types']} case types")
            return analysis_data, summary_stats
            
        except Exception as e:
            print(f"❌ Error preparing classification analysis data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), {}
        
    @callback(
        Output("workflow-class-display-state", "data"),
        [Input("workflow-class-display-selector", "value")],
        prevent_initial_call=False
    )
    def update_class_display_state(display_value):
        """Store the current display preference"""
        return display_value if display_value else "top5"

    @monitor_chart_performance("Classification Analysis Stacked Chart")
    def create_classification_stacked_chart(analysis_data, dimension="case_origin", display_limit="top10"):
        """
        Create stacked bar chart for classification analysis
        UPDATED: Moved legend to vertical position on the right side to eliminate all overlap issues
        """
        if not analysis_data or dimension not in analysis_data or analysis_data[dimension].empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No classification data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Tickets by Classification & Type",
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
            # Get the cross-tabulation data (excluding totals)
            crosstab_data = analysis_data[dimension].copy()
            if 'Total' in crosstab_data.index:
                crosstab_data = crosstab_data.drop('Total')
            if 'Total' in crosstab_data.columns:
                crosstab_data = crosstab_data.drop('Total', axis=1)
            
            # Sort case types by total tickets (descending)
            row_totals = crosstab_data.sum(axis=1).sort_values(ascending=False)
            crosstab_data = crosstab_data.reindex(row_totals.index)
            
            # Apply display limit based on user selection
            total_case_types = len(crosstab_data)
            if display_limit == "top3":
                crosstab_data = crosstab_data.head(3)
                displayed_count = min(3, total_case_types)
            elif display_limit == "top5":
                crosstab_data = crosstab_data.head(5)
                displayed_count = min(5, total_case_types)
            elif display_limit == "top10":
                crosstab_data = crosstab_data.head(10)
                displayed_count = min(10, total_case_types)
            else:  # all
                displayed_count = total_case_types
            
            # Create color palette
            colors = px.colors.qualitative.Set3[:len(crosstab_data.columns)]
            
            fig = go.Figure()
            
            # Add traces for each classification category
            for i, column in enumerate(crosstab_data.columns):
                fig.add_trace(go.Bar(
                    name=str(column),
                    x=crosstab_data.index,
                    y=crosstab_data[column],
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f"<b>{column}</b><br>Case Type: %{{x}}<br>Count: %{{y:,.0f}}<extra></extra>"
                ))
            
            # Update layout
            dimension_labels = {
                'case_origin': 'Case Origin',
                'priority': 'Priority',
                'product': 'Product'
            }
            dimension_label = dimension_labels.get(dimension, dimension.title())
            
            # Create title with display information
            display_labels = {
                'top3': 'Top 3',
                'top5': 'Top 5', 
                'top10': 'Top 10',
                'all': 'All'
            }
            display_text = display_labels.get(display_limit, 'Top 10')
            
            if display_limit != "all" and displayed_count < total_case_types:
                title_text = f"Tickets by Case Type & {dimension_label} ({display_text} of {total_case_types})"
            else:
                title_text = f"Tickets by Case Type & {dimension_label} ({display_text} Case Types)"
            
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': 'Case Type',
                    'tickangle': -45,
                    'tickfont': {'size': 10 if displayed_count > 10 else 11}
                },
                yaxis={
                    'title': 'Number of Tickets',
                    'showgrid': True,
                    'gridcolor': '#f0f0f0'
                },
                barmode='stack',
                height=400,
                # UPDATED: Adjusted margins - increased right margin for vertical legend, restored normal bottom margin
                margin={'l': 60, 'r': 120, 't': 80, 'b': 120},  # More right space for legend, normal bottom
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    # UPDATED: Vertical legend on the right side - completely avoids all overlap issues
                    orientation="v",  # Vertical orientation
                    yanchor="middle",  # Center vertically
                    y=0.5,  # Middle of chart area
                    xanchor="left",  # Align to left of legend position
                    x=1.02,  # Position just outside the chart area on the right
                    font=dict(size=10),
                    bgcolor="rgba(255,255,255,0.8)",  # Semi-transparent background
                    bordercolor="rgba(0,0,0,0.1)",  # Light border
                    borderwidth=1
                ),
                hovermode='closest'
            )
            
            print(f"📊 Created classification stacked chart: {displayed_count} of {total_case_types} case types ({display_limit}) with vertical legend")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating classification stacked chart: {e}")
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
                    'text': "Tickets by Classification & Type - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig

    @monitor_chart_performance("Classification Analysis Heatmap")
    def create_classification_heatmap(analysis_data, dimension="case_origin", display_limit="top10"):
        """
        Create heatmap for classification analysis
        UPDATED: Using lighter, more eye-soothing color palettes
        """
        if not analysis_data or dimension not in analysis_data or analysis_data[dimension].empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No classification data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                title={
                    'text': "Tickets by Classification & Type (Heatmap)",
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
            # Get the cross-tabulation data (excluding totals)
            crosstab_data = analysis_data[dimension].copy()
            if 'Total' in crosstab_data.index:
                crosstab_data = crosstab_data.drop('Total')
            if 'Total' in crosstab_data.columns:
                crosstab_data = crosstab_data.drop('Total', axis=1)
            
            # Sort case types by total tickets (descending)
            row_totals = crosstab_data.sum(axis=1).sort_values(ascending=False)
            crosstab_data = crosstab_data.reindex(row_totals.index)
            
            # Apply display limit based on user selection
            total_case_types = len(crosstab_data)
            if display_limit == "top3":
                crosstab_data = crosstab_data.head(3)
                displayed_count = min(3, total_case_types)
            elif display_limit == "top5":
                crosstab_data = crosstab_data.head(5)
                displayed_count = min(5, total_case_types)
            elif display_limit == "top10":
                crosstab_data = crosstab_data.head(10)
                displayed_count = min(10, total_case_types)
            else:  # all
                displayed_count = total_case_types
            
            # Improve visibility for heavily skewed data
            heatmap_values = crosstab_data.values
            
            # Check if data is heavily skewed (ratio > 10:1)
            max_value = heatmap_values.max()
            min_value = heatmap_values.min()
            
            if max_value > 0 and min_value >= 0 and (max_value / max(min_value, 1)) > 10:
                # Apply log transformation to reduce skewness
                import numpy as np
                # Add 1 to handle zeros, then apply log
                log_values = np.log1p(heatmap_values)  # log(1 + x) to handle zeros
                heatmap_display_values = log_values
                # UPDATED: Lighter, more soothing color palette for log-scaled data
                color_scale = 'Blues'  # Softer than Plasma, easier on the eyes
                colorbar_title = "Log(Ticket Count + 1)"
                is_log_scaled = True
                print(f"📊 Applied log transformation for heavily skewed heatmap data (max: {max_value}, min: {min_value})")
            else:
                # Use original values with better color scale
                heatmap_display_values = heatmap_values
                # UPDATED: Lighter, more soothing color palette for linear data
                color_scale = 'Greens'  # Softer than Viridis, more natural
                colorbar_title = "Ticket Count"
                is_log_scaled = False
                print(f"📊 Using linear scale for heatmap data (max: {max_value}, min: {min_value})")
            
            # Create custom hover template that ALWAYS shows original values
            hover_text = []
            for i in range(len(crosstab_data.index)):
                hover_row = []
                for j in range(len(crosstab_data.columns)):
                    case_type = crosstab_data.index[i]
                    classification = crosstab_data.columns[j]
                    original_value = int(heatmap_values[i, j])  # Always use original values
                    log_value = heatmap_display_values[i, j] if is_log_scaled else None
                    
                    # Build hover text showing original values prominently
                    if is_log_scaled:
                        hover_text_cell = (
                            f"<b>Case Type:</b> {case_type}<br>"
                            f"<b>Classification:</b> {classification}<br>"
                            f"<b>Ticket Count:</b> {original_value:,}<br>"
                            f"<i>Log Value:</i> {log_value:.2f}"
                        )
                    else:
                        hover_text_cell = (
                            f"<b>Case Type:</b> {case_type}<br>"
                            f"<b>Classification:</b> {classification}<br>"
                            f"<b>Ticket Count:</b> {original_value:,}"
                        )
                    
                    hover_row.append(hover_text_cell)
                hover_text.append(hover_row)
            
            # Create heatmap with improved visibility and soothing colors
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_display_values,  # Use transformed values for coloring
                x=crosstab_data.columns,
                y=crosstab_data.index,
                colorscale=color_scale,  # UPDATED: Using lighter, more soothing color palettes
                hoverongaps=False,
                # Use custom hover template that shows original values
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_text,  # Custom hover text with original values
                # Colorbar settings
                colorbar=dict(
                    title=colorbar_title,
                    thickness=15,
                    len=0.8,
                    x=1.02
                ),
                # Color scaling options for better contrast
                zmin=heatmap_display_values.min(),
                zmax=heatmap_display_values.max(),
                connectgaps=False
            ))
            
            # Update layout
            dimension_labels = {
                'case_origin': 'Case Origin',
                'priority': 'Priority', 
                'product': 'Product'
            }
            dimension_label = dimension_labels.get(dimension, dimension.title())
            
            # Create title with display information
            display_labels = {
                'top3': 'Top 3',
                'top5': 'Top 5', 
                'top10': 'Top 10',
                'all': 'All'
            }
            display_text = display_labels.get(display_limit, 'Top 10')
            
            if display_limit != "all" and displayed_count < total_case_types:
                title_text = f"Tickets by Case Type & {dimension_label} ({display_text} of {total_case_types}) - Heatmap"
            else:
                title_text = f"Tickets by Case Type & {dimension_label} ({display_text}) - Heatmap"
            
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': dimension_label,
                    'tickangle': -45,
                    'tickfont': {'size': 10},
                    'side': 'bottom'
                },
                yaxis={
                    'title': 'Case Type',
                    'tickfont': {'size': 10 if displayed_count > 10 else 11},
                    'autorange': 'reversed'  # Reverse y-axis to show highest volume at top
                },
                height=450,  # Match stacked chart height
                # Adjusted margins for better colorbar positioning
                margin={'l': 120, 'r': 120, 't': 80, 'b': 120},  # More right space for colorbar
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            print(f"📊 Created classification heatmap with soothing colors ({'Blues' if is_log_scaled else 'Greens'}): {displayed_count} of {total_case_types} case types ({display_limit})")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating classification heatmap: {e}")
            import traceback
            traceback.print_exc()
            
            # Return proper error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating heatmap: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Tickets by Classification & Type - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=450,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            return fig
                      
    @monitor_performance("Classification Analysis Insights Generation")
    def generate_classification_analysis_insights(analysis_data, summary_stats, display_preference="top10"):
        """
        Generate automated insights from classification analysis data
        UPDATED: Added display_preference parameter to provide context about displayed vs total data
        """
        if not analysis_data or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No classification data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see classification insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("📈 Data will appear when tickets match your criteria", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        try:
            insights = []
            
            # Insight 1: Overall distribution summary with display context
            total_tickets = summary_stats.get('total_tickets', 0)
            unique_case_types = summary_stats.get('unique_case_types', 0)
            top_case_type = summary_stats.get('top_case_type', 'N/A')
            
            # Add display context
            display_labels = {
                'top3': 'top 3',
                'top5': 'top 5', 
                'top10': 'top 10',
                'all': 'all'
            }
            display_text = display_labels.get(display_preference, 'top 10')
            
            if display_preference != "all":
                insights.append(f"📊 Classification Overview: {total_tickets:,} tickets across {unique_case_types} case types (showing {display_text}), with '{top_case_type}' being most common")
            else:
                insights.append(f"📊 Classification Overview: {total_tickets:,} tickets across {unique_case_types} case types, with '{top_case_type}' being most common")
            
            # Insight 2: Case origin analysis (same as before)
            if 'case_origin' in analysis_data and not analysis_data['case_origin'].empty:
                origin_data = analysis_data['case_origin']
                if 'Total' in origin_data.columns:
                    origin_totals = origin_data['Total'].drop('Total', errors='ignore').sort_values(ascending=False)
                    if len(origin_totals) > 0:
                        top_origin_case_type = origin_totals.index[0]
                        top_origin_count = origin_totals.iloc[0]
                        
                        # Find the dominant origin for this case type
                        case_type_row = origin_data.loc[top_origin_case_type]
                        case_type_row_clean = case_type_row.drop('Total', errors='ignore')
                        dominant_origin = case_type_row_clean.idxmax()
                        
                        insights.append(f"🎯 Case Origin Pattern: '{top_origin_case_type}' has highest volume ({top_origin_count:,} tickets), primarily from '{dominant_origin}' channel")
                    else:
                        insights.append(f"📍 Case Origin Analysis: Data distributed across {summary_stats.get('unique_origins', 0)} different origins")
                else:
                    insights.append(f"📍 Case Origin Analysis: Data distributed across {summary_stats.get('unique_origins', 0)} different origins")
            else:
                insights.append(f"📍 Case Origin Analysis: Data distributed across {summary_stats.get('unique_origins', 0)} different origins")
            
            # Insight 3: Priority distribution analysis (same as before)  
            if 'priority' in analysis_data and not analysis_data['priority'].empty:
                priority_data = analysis_data['priority']
                if 'Total' in priority_data.columns:
                    # Calculate priority distribution
                    priority_totals = priority_data.loc['Total'].drop('Total', errors='ignore')
                    if len(priority_totals) > 0:
                        top_priority = priority_totals.idxmax()
                        top_priority_count = priority_totals.max()
                        priority_pct = (top_priority_count / total_tickets * 100) if total_tickets > 0 else 0
                        
                        # Assess priority distribution
                        high_priority_terms = ['High', 'Critical', 'Urgent', 'Emergency']
                        has_high_priority = any(term in str(top_priority) for term in high_priority_terms)
                        priority_assessment = "requires immediate attention" if has_high_priority else "manageable priority levels"
                        
                        insights.append(f"⚡ Priority Distribution: '{top_priority}' priority dominates with {top_priority_count:,} tickets ({priority_pct:.1f}%) - {priority_assessment}")
                    else:
                        insights.append(f"⚡ Priority Analysis: Tickets distributed across {summary_stats.get('unique_priorities', 0)} priority levels")
                else:
                    insights.append(f"⚡ Priority Analysis: Tickets distributed across {summary_stats.get('unique_priorities', 0)} priority levels")
            else:
                insights.append(f"⚡ Priority Analysis: Tickets distributed across {summary_stats.get('unique_priorities', 0)} priority levels")
            
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
            print(f"❌ Error generating classification analysis insights: {e}")
            import traceback
            traceback.print_exc()
            # Return 3 error insights for consistency
            return html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate classification insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
           

    @callback(
        Output("workflow-class-view-state", "data"),
        [Input("workflow-class-stacked-btn", "n_clicks"),
        Input("workflow-class-heatmap-btn", "n_clicks")],
        [State("workflow-class-view-state", "data")],
        prevent_initial_call=False
    )
    def update_classification_view_state(stacked_clicks, heatmap_clicks, current_state):
        """
        Store the current view state and persist it across display preference changes
        Following the same pattern as Resolution Times Analysis
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # Initialize with stacked chart if no state exists
        if current_state is None:
            current_state = "stacked"
        
        # Update state only when a view button is clicked
        if triggered_id == "workflow-class-heatmap-btn":
            return "heatmap"
        elif triggered_id == "workflow-class-stacked-btn":
            return "stacked"
        
        # Return existing state for other triggers (like display dropdown changes)
        return current_state

    @callback(
        [Output("workflow-class-stacked-btn", "active"),
        Output("workflow-class-heatmap-btn", "active")],
        [Input("workflow-class-view-state", "data")],  # UPDATED: Use stored state instead of clicks
        prevent_initial_call=False
    )
    def update_classification_view_buttons(view_state):
        """
        Update button active states based on stored view state
        UPDATED: Now uses stored state like Resolution Times
        """
        if view_state == "heatmap":
            return False, True
        else:  # stacked or default
            return True, False

    @callback(
        [Output("workflow-classification-chart", "figure"),
        Output("workflow-classification-insights", "children")],
        [Input("workflow-filtered-query-store", "data"),
        Input("workflow-class-view-state", "data"),  # UPDATED: Use stored view state
        Input("workflow-class-display-state", "data")], 
        prevent_initial_call=False
    )
    @monitor_performance("Classification Analysis Chart Update")
    def update_classification_analysis_chart(stored_selections, view_state, display_preference):
        """
        Update classification analysis chart based on filter selections, view type, and display preference
        UPDATED: Now uses stored view state instead of button clicks
        """
        try:
            # Default states - same as Resolution Times pattern
            if view_state is None:
                view_state = "stacked"  # Default view
            if display_preference is None:
                display_preference = "top5"  # Default display
            
            print(f"🔄 Updating classification analysis chart: view_type={view_state}, display={display_preference}")
            
            # Get base data
            base_data = get_classification_analysis_base_data()
            
            # Apply filters
            filtered_data = apply_classification_analysis_filters(base_data['work_items'], stored_selections)
            
            # Prepare analysis data
            analysis_data, summary_stats = prepare_classification_analysis_data(
                filtered_data, 
                base_data['case_types'], 
                view_state
            )
            
            # Create visualization based on stored view state and display preference
            if view_state == "heatmap":
                fig = create_classification_heatmap(analysis_data, "case_origin", display_preference)
            else:  # stacked
                fig = create_classification_stacked_chart(analysis_data, "case_origin", display_preference)
            
            # Generate insights
            insights = generate_classification_analysis_insights(analysis_data, summary_stats, display_preference)
            
            print(f"✅ Classification analysis chart updated successfully ({view_state}, {display_preference})")
            return fig, insights
            
        except Exception as e:
            print(f"❌ Error updating classification analysis chart: {e}")
            
            # Return error chart and message
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error loading classification analysis data: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="red")
            )
            fig.update_layout(
                title={
                    'text': "Tickets by Classification & Type - Error",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            error_insights = html.Div([
                html.Div([html.Span("❌ **Error**: Unable to generate classification insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔧 **Issue**: Data processing error occurred", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔄 **Action**: Try refreshing or adjusting filters", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
            
            return fig, error_insights
               
    print("✅ Workflow classification analysis callbacks registered")

def register_workflow_classification_analysis_modal_callbacks(app):
    """
    Register callbacks for workflow classification analysis chart modal functionality
    """
    print("Registering Workflow Classification Analysis Chart Modal callbacks...")
    @monitor_chart_performance("Enlarged Classification Analysis Chart")
    def create_enlarged_classification_analysis_chart(original_figure):
        """
        Create an enlarged version of the classification analysis chart for modal display
        """
        if not original_figure:
            return html.Div("No chart data available", className="text-center p-4")
        
        try:
            # Create a deep copy of the original figure
            enlarged_fig = copy.deepcopy(original_figure)
            
            # Update layout for larger modal display
            enlarged_fig['layout'].update({
                'height': 650,  # Increased height for modal
                'margin': {'l': 120, 'r': 150, 't': 100, 'b': 140},  # UPDATED: More right margin for vertical legend in modal
                'title': {
                    **enlarged_fig['layout'].get('title', {}),
                    'font': {'size': 20, 'color': '#2c3e50'}  
                },
                'xaxis': {
                    **enlarged_fig['layout'].get('xaxis', {}),
                    'title': {
                        **enlarged_fig['layout'].get('xaxis', {}).get('title', {}),
                        'font': {'size': 14}
                    },
                    'tickfont': {'size': 12}  
                },
                'yaxis': {
                    **enlarged_fig['layout'].get('yaxis', {}),
                    'title': {
                        **enlarged_fig['layout'].get('yaxis', {}).get('title', {}),
                        'font': {'size': 14}
                    },
                    'tickfont': {'size': 12} 
                },
                'legend': {
                    **enlarged_fig['layout'].get('legend', {}),
                    'font': {'size': 12},
                    # UPDATED: Keep vertical legend for modal - larger font and positioning
                    'orientation': 'v',
                    'yanchor': 'middle',
                    'y': 0.5,
                    'xanchor': 'left',
                    'x': 1.02,  # Position outside chart area
                    'bgcolor': "rgba(255,255,255,0.9)",
                    'bordercolor': "rgba(0,0,0,0.1)",
                    'borderwidth': 1
                }
            })
            
            # Update traces for better visibility in larger chart
            if 'data' in enlarged_fig and enlarged_fig['data']:
                for trace in enlarged_fig['data']:
                    if trace.get('type') == 'bar':
                        # Make bar chart elements more visible
                        trace.update({
                            'marker': {
                                **trace.get('marker', {}),
                                'line': {'width': 1, 'color': 'white'}  # Better borders
                            }
                        })
                    elif trace.get('type') == 'heatmap':
                        # Keep heatmap as-is, it scales well
                        pass
            
            # Create the chart component
            return dcc.Graph(
                figure=enlarged_fig,
                config={
                    'displayModeBar': True, 
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d'],
                    'displaylogo': False,
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'workflow_classification_analysis_chart',
                        'height': 650,
                        'width': 1200,
                        'scale': 1
                    }
                },
                style={'height': '650px'}
            )
            
        except Exception as e:
            print(f"❌ Error creating enlarged classification analysis chart: {str(e)}")
            return html.Div(
                f"Error displaying chart: {str(e)}", 
                className="text-center p-4 text-danger"
            )    
           
    @callback(
        [Output("workflow-chart-modal", "is_open", allow_duplicate=True),
        Output("workflow-modal-chart-content", "children", allow_duplicate=True)],
        [Input("workflow-classification-chart-wrapper", "n_clicks")],
        [State("workflow-chart-modal", "is_open"),
        State("workflow-classification-chart", "figure")],
        prevent_initial_call=True
    )
    @monitor_performance("Classification Analysis Modal Toggle")
    def toggle_classification_analysis_chart_modal(chart_wrapper_clicks, is_open, chart_figure):
        """
        Handle opening of classification analysis chart modal using SHARED modal
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        print(f"🔄 Classification Analysis Modal callback triggered by: {triggered_id}")
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "workflow-classification-chart-wrapper" and chart_wrapper_clicks and not is_open:
            print("📊 Classification analysis chart wrapper clicked! Opening modal...")
            
            if not chart_figure or not chart_figure.get('data'):
                print("⚠️ No classification analysis chart figure data available")
                return no_update, no_update
            
            print("✅ Opening classification analysis modal with chart data")
            enlarged_chart = create_enlarged_classification_analysis_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
    
    print("✅ Workflow Classification Analysis Chart Modal callbacks registered successfully")