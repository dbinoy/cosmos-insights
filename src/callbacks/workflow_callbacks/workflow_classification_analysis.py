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
from inflection import titleize, pluralize

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
        
        # print(f"📊 Starting classification analysis filtering: {len(df_work_items)} work item records")
        
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
                    # print(f"📅 Date filter applied: {len(df_work_items)} work item records")
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")
        
        # Apply other filters
        if selected_aor is not None and len(selected_aor) > 0 and "All" not in selected_aor:
            df_work_items = df_work_items.loc[df_work_items['AorShortName'].isin(selected_aor)].copy()
            # print(f"🎯 AOR filter applied: {len(df_work_items)} records")

        if selected_case_types is not None and len(selected_case_types) > 0 and "All" not in selected_case_types:
            df_work_items = df_work_items.loc[df_work_items['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
            # print(f"📋 Case Type filter applied: {len(df_work_items)} records")

        if selected_products is not None and len(selected_products) > 0 and "All" not in selected_products:
            df_work_items = df_work_items.loc[df_work_items['Product'].isin(selected_products)].copy()
            # print(f"🛍️ Product filter applied: {len(df_work_items)} records")

        if selected_modules is not None and len(selected_modules) > 0 and "All" not in selected_modules:
            df_work_items = df_work_items.loc[df_work_items['Module'].isin(selected_modules)].copy()
            # print(f"🧩 Module filter applied: {len(df_work_items)} records")

        if selected_features is not None and len(selected_features) > 0 and "All" not in selected_features:
            df_work_items = df_work_items.loc[df_work_items['Feature'].isin(selected_features)].copy()
            print(f"⭐ Feature filter applied: {len(df_work_items)} records")

        if selected_issues is not None and len(selected_issues) > 0 and "All" not in selected_issues:
            df_work_items = df_work_items.loc[df_work_items['Issue'].isin(selected_issues)].copy()
            # print(f"🐛 Issue filter applied: {len(df_work_items)} records")

        if selected_origins is not None and len(selected_origins) > 0 and "All" not in selected_origins:
            df_work_items = df_work_items.loc[df_work_items['CaseOrigin'].isin(selected_origins)].copy()
            # print(f"📍 Origin filter applied: {len(df_work_items)} records")

        if selected_reasons is not None and len(selected_reasons) > 0 and "All" not in selected_reasons:
            df_work_items = df_work_items.loc[df_work_items['CaseReason'].isin(selected_reasons)].copy()
            # print(f"📝 Reason filter applied: {len(df_work_items)} records")

        if selected_status is not None and len(selected_status) > 0 and "All" not in selected_status:
            df_work_items = df_work_items.loc[df_work_items['WorkItemStatus'].isin(selected_status)].copy()
            # print(f"📊 Status filter applied: {len(df_work_items)} records")

        if selected_priority is not None and len(selected_priority) > 0 and "All" not in selected_priority:
            df_work_items = df_work_items.loc[df_work_items['Priority'].isin(selected_priority)].copy()
            # print(f"⚡ Priority filter applied: {len(df_work_items)} records")

        return df_work_items

    @monitor_performance("Classification Analysis Data Preparation")
    def prepare_classification_analysis_data(filtered_data, case_types_data, row_dimension="case_type", column_dimension="case_origin"):
        """
        Prepare classification analysis data for visualization
        Creates cross-tabulation of any two dimensions
        UPDATED: Added support for AOR and Case Reason dimensions
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
            
            # Handle missing values for ALL dimensions including AOR and Case Reason
            df['WorkItemDefinitionShortCode'] = df['WorkItemDefinitionShortCode'].fillna('Unspecified')
            df['CaseOrigin'] = df['CaseOrigin'].fillna('Unspecified')
            df['AorShortName'] = df['AorShortName'].fillna('Unspecified')                   # ADDED: AOR handling
            df['CaseReason'] = df['CaseReason'].fillna('Unspecified')                       # ADDED: Case Reason handling
            df['Priority'] = df['Priority'].fillna('Unspecified')
            df['Product'] = df['Product'].fillna('Unspecified')
            df['Module'] = df['Module'].fillna('Unspecified')
            df['Feature'] = df['Feature'].fillna('Unspecified')
            df['Issue'] = df['Issue'].fillna('Unspecified')
            df['WorkItemStatus'] = df['WorkItemStatus'].fillna('Unspecified')
            
            # UPDATED: Simple formatting function using titleize with N/A removal like filter callbacks
            def format_for_display(value):
                if pd.isna(value) or value == '' or value == 'Unspecified':
                    return 'Unspecified'
                formatted = str(value).replace('_', ' ').replace('-', ' ').replace('N/A', '').strip()
                return titleize(formatted) if formatted else 'Unspecified'
            
            # Create display names for case types
            def get_case_type_display_name(code):
                if pd.isna(code) or code == '' or code == 'Unspecified':
                    return 'Unspecified'
                return case_type_mapping.get(code, format_for_display(code))
            
            # UPDATED: Create display columns for ALL dimensions including AOR and Case Reason
            df['CaseTypeDisplay'] = df['WorkItemDefinitionShortCode'].apply(get_case_type_display_name)
            df['CaseOriginDisplay'] = df['CaseOrigin'].apply(format_for_display)
            df['AorDisplay'] = df['AorShortName'].apply(format_for_display)                 # ADDED: AOR display formatting
            df['CaseReasonDisplay'] = df['CaseReason'].apply(format_for_display)            # ADDED: Case Reason display formatting
            df['PriorityDisplay'] = df['Priority'].apply(format_for_display)
            df['ProductDisplay'] = df['Product'].apply(format_for_display)
            df['ModuleDisplay'] = df['Module'].apply(format_for_display)
            df['FeatureDisplay'] = df['Feature'].apply(format_for_display)
            df['IssueDisplay'] = df['Issue'].apply(format_for_display)
            df['StatusDisplay'] = df['WorkItemStatus'].apply(format_for_display)
            
            # UPDATED: Mapping from dimension keys to display column names including new dimensions
            dimension_column_mapping = {
                'case_type': 'CaseTypeDisplay',
                'case_origin': 'CaseOriginDisplay',
                'aor': 'AorDisplay',                                                        
                'case_reason': 'CaseReasonDisplay',                                         
                'priority': 'PriorityDisplay',
                'product': 'ProductDisplay',
                'module': 'ModuleDisplay',
                'feature': 'FeatureDisplay',
                'issue': 'IssueDisplay',
                'status': 'StatusDisplay'
            }
            
            # Get the actual column names for the selected dimensions
            row_column = dimension_column_mapping.get(row_dimension, 'CaseTypeDisplay')
            column_column = dimension_column_mapping.get(column_dimension, 'CaseOriginDisplay')
            
            # Prevent same dimension being used for both rows and columns
            if row_dimension == column_dimension:
                # print(f"⚠️ Same dimension selected for both axes: {row_dimension}. Using default combination.")
                row_column = 'CaseTypeDisplay'
                column_column = 'CaseOriginDisplay'
            
            # Create cross-tabulation for selected dimensions
            crosstab_data = pd.crosstab(
                df[row_column], 
                df[column_column],
                margins=True, 
                margins_name="Total"
            )
            
            # Handle products and AOR specially (limit to avoid overcrowding)
            if column_dimension in ['product', 'aor'] and len(crosstab_data.columns) > 11:  # 10 + Total column
                # Get top 10 by total volume
                column_totals = crosstab_data.loc['Total'].drop('Total', errors='ignore').sort_values(ascending=False).head(10)
                top_items = column_totals.index.tolist() + ['Total']
                crosstab_data = crosstab_data[top_items]
                
            # Calculate summary statistics
            summary_stats = {
                'total_tickets': len(df),
                'row_dimension': row_dimension,
                'column_dimension': column_dimension,
                'unique_rows': df[row_column].nunique(),
                'unique_columns': df[column_column].nunique(),
                'top_row': df[row_column].mode().iloc[0] if not df[row_column].mode().empty else 'N/A',
                'top_column': df[column_column].mode().iloc[0] if not df[column_column].mode().empty else 'N/A'
            }
            
            # print(f"📊 Prepared classification analysis with AOR & Case Reason: {len(df)} tickets, {row_dimension} vs {column_dimension}")
            return crosstab_data, summary_stats
            
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

    @callback(
        [Output("workflow-class-row-dimension", "value"),
        Output("workflow-class-column-dimension", "value"),
        Output("workflow-class-dimension-store", "data")],
        [Input("workflow-class-row-dimension", "value"),
        Input("workflow-class-column-dimension", "value")],
        [State("workflow-class-dimension-store", "data")],
        prevent_initial_call=False
    )
    def prevent_same_dimensions(new_row_dim, new_column_dim, stored_dims):
        """
        Prevent selecting the same dimension for both row and column by flipping the values
        FIXED: Uses stored previous values to enable proper flipping behavior
        """
        triggered = ctx.triggered
        triggered_id = triggered[0]['prop_id'].split('.')[0] if triggered else None
        
        # Initialize stored dimensions if None
        if stored_dims is None:
            stored_dims = {'row': 'case_type', 'column': 'case_origin'}
        
        # Get previous values
        prev_row = stored_dims.get('row', 'case_type')
        prev_column = stored_dims.get('column', 'case_origin')
        
        # print(f"🔄 Dimension callback - Triggered by: {triggered_id}")
        # print(f"📊 New values: row={new_row_dim}, column={new_column_dim}")
        # print(f"📋 Previous values: row={prev_row}, column={prev_column}")
        
        # If same dimension selected, flip the values
        if new_row_dim == new_column_dim:
            if triggered_id == "workflow-class-row-dimension":
                # Row dimension was changed to match column dimension
                # Flip: keep new selection on row, move previous row value to column
                result_row = new_row_dim
                result_column = prev_row
                # print(f"🔄 Row changed to {new_row_dim} (same as column). Flipping: row={result_row}, column={result_column}")
                
            elif triggered_id == "workflow-class-column-dimension":
                # Column dimension was changed to match row dimension  
                # Flip: move previous column value to row, keep new selection on column
                result_row = prev_column
                result_column = new_column_dim
                # print(f"🔄 Column changed to {new_column_dim} (same as row). Flipping: row={result_row}, column={result_column}")

            else:
                # Initial load or other trigger - use default values
                result_row = 'case_type'
                result_column = 'case_origin'
                # print("🏁 Initial load - using defaults")
            
            # Update stored dimensions
            new_stored_dims = {'row': result_row, 'column': result_column}
            return result_row, result_column, new_stored_dims
        
        # Different dimensions selected - update store and return new values
        # print(f"✅ Different dimensions selected - updating store")
        new_stored_dims = {'row': new_row_dim, 'column': new_column_dim}
        return new_row_dim, new_column_dim, new_stored_dims
       
    @monitor_chart_performance("Classification Analysis Stacked Chart")
    def create_classification_stacked_chart(analysis_data, row_dimension="case_type", column_dimension="case_origin", display_limit="top5"):
        """
        Create stacked bar chart for classification analysis
        UPDATED: Generalized to work with any pair of dimensions
        """
        if analysis_data.empty:
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
                    'text': "Tickets Classification Analysis",
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
            crosstab_data = analysis_data.copy()
            if 'Total' in crosstab_data.index:
                crosstab_data = crosstab_data.drop('Total')
            if 'Total' in crosstab_data.columns:
                crosstab_data = crosstab_data.drop('Total', axis=1)
            
            # Sort rows by total tickets (descending)
            row_totals = crosstab_data.sum(axis=1).sort_values(ascending=False)
            crosstab_data = crosstab_data.reindex(row_totals.index)
            
            # Apply display limit based on user selection
            total_rows = len(crosstab_data)
            if display_limit == "top3":
                crosstab_data = crosstab_data.head(3)
                displayed_count = min(3, total_rows)
            elif display_limit == "top5":
                crosstab_data = crosstab_data.head(5)
                displayed_count = min(5, total_rows)
            elif display_limit == "top10":
                crosstab_data = crosstab_data.head(10)
                displayed_count = min(10, total_rows)
            else:  # all
                displayed_count = total_rows
            
            # Create color palette
            colors = px.colors.qualitative.Set3[:len(crosstab_data.columns)]
            
            fig = go.Figure()
            
            # Add traces for each column category
            for i, column in enumerate(crosstab_data.columns):
                fig.add_trace(go.Bar(
                    name=str(column),
                    x=crosstab_data.index,
                    y=crosstab_data[column],
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f"<b>{column}</b><br>%{{x}}<br>Count: %{{y:,.0f}}<extra></extra>"
                ))
            
            # UPDATED: Dynamic labels based on selected dimensions
            dimension_labels = {
                'case_type': 'Case Type',
                'case_origin': 'Case Origin',
                'aor': 'AOR', 
                'case_reason': 'Case Reason', 
                'priority': 'Priority',
                'product': 'Product',
                'module': 'Module',
                'feature': 'Feature',
                'issue': 'Issue',
                'status': 'Status'
            }
            
            row_label = dimension_labels.get(row_dimension, row_dimension.title())
            column_label = dimension_labels.get(column_dimension, column_dimension.title())
            
            # Create title with display information
            display_labels = {
                'top3': 'Top 3',
                'top5': 'Top 5', 
                'top10': 'Top 10',
                'all': 'All'
            }
            display_text = display_labels.get(display_limit, 'Top 5')
            
            if display_limit != "all" and displayed_count < total_rows:
                title_text = f"{row_label} by {column_label} ({display_text} of {total_rows})"
            else:
                title_text = f"{row_label} by {column_label} ({display_text})"
            
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': row_label,
                    'tickangle': -45,
                    'tickfont': {'size': 10 if displayed_count > 10 else 11}
                },
                yaxis={
                    'title': 'Number of Tickets',
                    'showgrid': True,
                    'gridcolor': '#f0f0f0'
                },
                barmode='stack',
                height=450,
                margin={'l': 60, 'r': 120, 't': 80, 'b': 120},
                plot_bgcolor='white',
                paper_bgcolor='white',
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.02,
                    font=dict(size=10),
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="rgba(0,0,0,0.1)",
                    borderwidth=1
                ),
                hovermode='closest'
            )
            
            # print(f"📊 Created generalized stacked chart: {row_dimension} vs {column_dimension} ({displayed_count} of {total_rows})")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating generalized stacked chart: {e}")
            return create_error_figure("Error creating classification chart")

    @monitor_chart_performance("Classification Analysis Heatmap")
    def create_classification_heatmap(analysis_data, row_dimension="case_type", column_dimension="case_origin", display_limit="top5"):
        """
        Create heatmap for classification analysis
        UPDATED: Generalized to work with any pair of dimensions
        """
        if analysis_data.empty:
            return create_error_figure("No classification data available")
        
        try:
            # Get the cross-tabulation data (excluding totals)
            crosstab_data = analysis_data.copy()
            if 'Total' in crosstab_data.index:
                crosstab_data = crosstab_data.drop('Total')
            if 'Total' in crosstab_data.columns:
                crosstab_data = crosstab_data.drop('Total', axis=1)
            
            # Sort rows by total tickets (descending)
            row_totals = crosstab_data.sum(axis=1).sort_values(ascending=False)
            crosstab_data = crosstab_data.reindex(row_totals.index)
            
            # Apply display limit
            total_rows = len(crosstab_data)
            if display_limit == "top3":
                crosstab_data = crosstab_data.head(3)
                displayed_count = min(3, total_rows)
            elif display_limit == "top5":
                crosstab_data = crosstab_data.head(5)
                displayed_count = min(5, total_rows)
            elif display_limit == "top10":
                crosstab_data = crosstab_data.head(10)
                displayed_count = min(10, total_rows)
            else:  # all
                displayed_count = total_rows
            
            # Prepare heatmap values
            heatmap_values = crosstab_data.values
            
            # Smart color scaling for skewed data
            max_value = heatmap_values.max()
            min_value = heatmap_values.min()
            
            if max_value > 0 and min_value >= 0 and (max_value / max(min_value, 1)) > 10:
                import numpy as np
                log_values = np.log1p(heatmap_values)
                heatmap_display_values = log_values
                color_scale = 'Blues'
                colorbar_title = "Log(Ticket Count + 1)"
                is_log_scaled = True
            else:
                heatmap_display_values = heatmap_values
                color_scale = 'Greens'
                colorbar_title = "Ticket Count"
                is_log_scaled = False
            
            # Create hover text
            hover_text = []
            for i in range(len(crosstab_data.index)):
                hover_row = []
                for j in range(len(crosstab_data.columns)):
                    row_item = crosstab_data.index[i]
                    col_item = crosstab_data.columns[j]
                    original_value = int(heatmap_values[i, j])
                    
                    if is_log_scaled:
                        log_value = heatmap_display_values[i, j]
                        hover_text_cell = (
                            f"<b>{row_item}</b><br>"
                            f"<b>{col_item}</b><br>"
                            f"<b>Ticket Count:</b> {original_value:,}<br>"
                            f"<i>Log Value:</i> {log_value:.2f}"
                        )
                    else:
                        hover_text_cell = (
                            f"<b>{row_item}</b><br>"
                            f"<b>{col_item}</b><br>"
                            f"<b>Ticket Count:</b> {original_value:,}"
                        )
                    hover_row.append(hover_text_cell)
                hover_text.append(hover_row)
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_display_values,
                x=crosstab_data.columns,
                y=crosstab_data.index,
                colorscale=color_scale,
                hoverongaps=False,
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_text,
                colorbar=dict(
                    title=colorbar_title,
                    thickness=15,
                    len=0.8,
                    x=1.02
                ),
                zmin=heatmap_display_values.min(),
                zmax=heatmap_display_values.max(),
                connectgaps=False
            ))
            
            # UPDATED: Dynamic labels
            dimension_labels = {
                'case_type': 'Case Type',
                'case_origin': 'Case Origin', 
                'aor': 'AOR',
                'case_reason': 'Case Reason',
                'priority': 'Priority',
                'product': 'Product',
                'module': 'Module',
                'feature': 'Feature',
                'issue': 'Issue',
                'status': 'Status'
            }
            
            row_label = dimension_labels.get(row_dimension, row_dimension.title())
            column_label = dimension_labels.get(column_dimension, column_dimension.title())
            
            display_labels = {
                'top3': 'Top 3',
                'top5': 'Top 5', 
                'top10': 'Top 10',
                'all': 'All'
            }
            display_text = display_labels.get(display_limit, 'Top 5')
            
            if display_limit != "all" and displayed_count < total_rows:
                title_text = f"{row_label} by {column_label} ({display_text} of {total_rows}) - Heatmap"
            else:
                title_text = f"{row_label} by {column_label} ({display_text}) - Heatmap"
            
            fig.update_layout(
                title={
                    'text': title_text,
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': '#2c3e50'}
                },
                xaxis={
                    'title': column_label,
                    'tickangle': -45,
                    'tickfont': {'size': 10},
                    'side': 'bottom'
                },
                yaxis={
                    'title': row_label,
                    'tickfont': {'size': 10 if displayed_count > 10 else 11},
                    'autorange': 'reversed'
                },
                height=450,
                margin={'l': 120, 'r': 120, 't': 80, 'b': 120},
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # print(f"📊 Created generalized heatmap: {row_dimension} vs {column_dimension} ({'Blues' if is_log_scaled else 'Greens'})")
            return fig
            
        except Exception as e:
            print(f"❌ Error creating generalized heatmap: {e}")
            return create_error_figure("Error creating classification heatmap")

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
                'text': "Classification Analysis - Error",
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
        FIXED: Proper DataFrame boolean checking to avoid ambiguous truth value error
        """
        # FIXED: Proper DataFrame checking - use .empty instead of boolean evaluation
        if analysis_data is None or analysis_data.empty or not summary_stats:
            return html.Div([
                html.Div([html.Span("📊 No classification data available for current filter selection", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("🔍 Try adjusting your filters to see classification insights", style={'fontSize': '13px'})], className="mb-2"),
                html.Div([html.Span("📈 Data will appear when tickets match your criteria", style={'fontSize': '13px'})], className="mb-2")
            ], className="insights-container")
        
        try:
            insights = []
            
            # Insight 1: Overall distribution summary with display context
            total_tickets = summary_stats.get('total_tickets', 0)
            unique_rows = summary_stats.get('unique_rows', 0)
            unique_columns = summary_stats.get('unique_columns', 0)
            top_row = summary_stats.get('top_row', 'N/A')
            top_column = summary_stats.get('top_column', 'N/A')
            row_dimension = summary_stats.get('row_dimension', 'case_type')
            column_dimension = summary_stats.get('column_dimension', 'case_origin')
            
            # Add display context
            display_labels = {
                'top3': 'top 3',
                'top5': 'top 5', 
                'top10': 'top 10',
                'all': 'all'
            }
            display_text = display_labels.get(display_preference, 'top 10')
            
            # UPDATED: Dynamic insight based on selected dimensions
            dimension_labels = {
                'case_type': 'case types',
                'case_origin': 'origins',
                'aor': 'AORs',
                'case_reason': 'reasons',
                'priority': 'priorities',
                'product': 'products',
                'module': 'modules',
                'feature': 'features',
                'issue': 'issues',
                'status': 'statuses'
            }
            
            row_label = dimension_labels.get(row_dimension, f'{row_dimension}s')
            column_label = dimension_labels.get(column_dimension, f'{column_dimension}s')
            
            if display_preference != "all":
                insights.append(f"📊 Classification Overview: {total_tickets:,} tickets across {unique_rows} {row_label} and {unique_columns} {column_label} (showing {display_text})")
            else:
                insights.append(f"📊 Classification Overview: {total_tickets:,} tickets across {unique_rows} {row_label} and {unique_columns} {column_label}")
            
            # Insight 2: Top row dimension analysis
            if not analysis_data.empty and 'Total' in analysis_data.columns:
                # Get totals by row (excluding the Total row)
                row_totals = analysis_data['Total'].drop('Total', errors='ignore').sort_values(ascending=False)
                if len(row_totals) > 0:
                    top_row_item = row_totals.index[0]
                    top_row_count = row_totals.iloc[0]
                    
                    # Find the dominant column for this top row
                    if top_row_item in analysis_data.index:
                        row_data = analysis_data.loc[top_row_item].drop('Total', errors='ignore')
                        if len(row_data) > 0:
                            dominant_column = row_data.idxmax()
                            dominant_count = row_data.max()
                            
                            row_dim_label = dimension_labels.get(row_dimension, row_dimension).rstrip('s')
                            column_dim_label = dimension_labels.get(column_dimension, column_dimension).rstrip('s')
                            
                            insights.append(f"🎯 Top {row_dim_label.title()}: '{top_row_item}' leads with {top_row_count:,} tickets, primarily from '{dominant_column}' {column_dim_label} ({dominant_count:,} tickets)")
                        else:
                            insights.append(f"🎯 Volume Distribution: '{top_row_item}' accounts for {top_row_count:,} tickets ({(top_row_count/total_tickets*100):.1f}%)")
                    else:
                        insights.append(f"🎯 Volume Distribution: Data shows varied distribution across {row_label}")
                else:
                    insights.append(f"🎯 Volume Distribution: Data distributed across {unique_rows} {row_label}")
            else:
                insights.append(f"🎯 Volume Distribution: Data distributed across {unique_rows} {row_label}")
            
            # Insight 3: Column dimension distribution analysis
            if not analysis_data.empty and len(analysis_data.columns) > 1:
                # Calculate column totals (excluding Total column)
                columns_to_analyze = [col for col in analysis_data.columns if col != 'Total']
                if len(columns_to_analyze) > 0:
                    column_totals = {}
                    for col in columns_to_analyze:
                        column_totals[col] = analysis_data[col].sum()
                    
                    if column_totals:
                        top_column_item = max(column_totals, key=column_totals.get)
                        top_column_count = column_totals[top_column_item]
                        column_pct = (top_column_count / total_tickets * 100) if total_tickets > 0 else 0
                        
                        column_dim_label = dimension_labels.get(column_dimension, column_dimension).rstrip('s')
                        
                        # Assess distribution evenness
                        if column_pct > 60:
                            distribution_note = "showing concentrated activity"
                        elif column_pct > 40:
                            distribution_note = "showing moderate concentration"
                        else:
                            distribution_note = "showing balanced distribution"
                        
                        insights.append(f"📈 {column_dim_label.title()} Pattern: '{top_column_item}' dominates with {top_column_count:,} tickets ({column_pct:.1f}%) - {distribution_note}")
                    else:
                        insights.append(f"📈 Distribution: Activity spread across {unique_columns} {column_label}")
                else:
                    insights.append(f"📈 Distribution: Activity spread across {unique_columns} {column_label}")
            else:
                insights.append(f"📈 Distribution: Activity spread across {unique_columns} {column_label}")
            
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
        Input("workflow-class-view-state", "data"),
        Input("workflow-class-display-state", "data"),
        Input("workflow-class-row-dimension", "value"),      # ADDED: Row dimension input
        Input("workflow-class-column-dimension", "value")],  # ADDED: Column dimension input
        prevent_initial_call=False
    )
    @monitor_performance("Classification Analysis Chart Update")
    def update_classification_analysis_chart(stored_selections, view_state, display_preference, row_dimension, column_dimension):
        """
        Update classification analysis chart based on filter selections, view type, display preference, and selected dimensions
        UPDATED: Now supports any pair of dimensions
        """
        try:
            # Default states
            if view_state is None:
                view_state = "stacked"
            if display_preference is None:
                display_preference = "top5"
            if row_dimension is None:
                row_dimension = "case_type"
            if column_dimension is None:
                column_dimension = "case_origin"
            
            # print(f"🔄 Updating classification analysis: {row_dimension} vs {column_dimension}, view={view_state}, display={display_preference}")
            
            # Get base data
            base_data = get_classification_analysis_base_data()
            
            # Apply filters
            filtered_data = apply_classification_analysis_filters(base_data['work_items'], stored_selections)
            
            # Prepare analysis data with selected dimensions
            analysis_data, summary_stats = prepare_classification_analysis_data(
                filtered_data, 
                base_data['case_types'], 
                row_dimension,
                column_dimension
            )
            
            # Create visualization based on view state and display preference
            if view_state == "heatmap":
                fig = create_classification_heatmap(analysis_data, row_dimension, column_dimension, display_preference)
            else:  # stacked
                fig = create_classification_stacked_chart(analysis_data, row_dimension, column_dimension, display_preference)
            
            # Generate insights
            insights = generate_classification_analysis_insights(analysis_data, summary_stats, display_preference)
            
            # print(f"✅ Classification analysis updated: {row_dimension} vs {column_dimension} ({view_state}, {display_preference})")
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
                    'text': "Tickets Classification Analysis - Error",
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
                      
    # print("✅ Workflow classification analysis callbacks registered")

def register_workflow_classification_analysis_modal_callbacks(app):
    """
    Register callbacks for workflow classification analysis chart modal functionality
    """
    # print("Registering Workflow Classification Analysis Chart Modal callbacks...")
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
        
        # print(f"🔄 Classification Analysis Modal callback triggered by: {triggered_id}")
        
        # Open modal if chart wrapper clicked and modal is not already open
        if triggered_id == "workflow-classification-chart-wrapper" and chart_wrapper_clicks and not is_open:
            # print("📊 Classification analysis chart wrapper clicked! Opening modal...")
            
            if not chart_figure or not chart_figure.get('data'):
                # print("⚠️ No classification analysis chart figure data available")
                return no_update, no_update
            
            # print("✅ Opening classification analysis modal with chart data")
            enlarged_chart = create_enlarged_classification_analysis_chart(chart_figure)
            return True, enlarged_chart
        
        return no_update, no_update
    
    # print("✅ Workflow Classification Analysis Chart Modal callbacks registered successfully")