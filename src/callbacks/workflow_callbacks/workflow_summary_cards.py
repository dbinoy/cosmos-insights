from dash.dependencies import Input, Output
import pandas as pd
from src.utils.db import run_queries
from datetime import datetime, timedelta
import time
from functools import wraps

def monitor_performance(func_name="Unknown"):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                print(f"⏱️ {func_name} completed in {duration:.2f} seconds")
                return result
            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ {func_name} failed after {duration:.2f} seconds: {str(e)}")
                raise
        return wrapper
    return decorator

def register_workflow_summary_cards_callbacks(app):
    """
    Register callbacks for workflow summary cards
    """
    
    def fetch_base_data():
        """Fetch all workflow base data for summary calculations"""
        queries = {
            "work_items": '''
                SELECT 
                    w.WorkItemId,
                    w.Title,
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
            ''',
            "duration_summary": '''
                SELECT 
                    WorkItemId,
                    OpenToClosed_Min,
                    OpenToResolved_Min
                FROM [consumable].[Fact_DurationSummary]
                WHERE (OpenToClosed_Min IS NOT NULL OR OpenToResolved_Min IS NOT NULL)
            '''
        }
        result = run_queries(queries, 'workflow', len(queries))
        # print(f"✅ Fetched workflow base data: {len(result['work_items'])} work items, {len(result['duration_summary'])} duration records")
        return result

    def apply_filters_to_dataset(df, selected_aor=None, selected_case_types=None, selected_status=None, 
                                selected_priority=None, selected_origins=None, selected_reasons=None,
                                selected_products=None, selected_features=None, selected_modules=None, 
                                selected_issues=None, start_date=None, end_date=None):
        """Apply all filters to the work items dataset"""
        if df.empty:
            return df
            
        filtered_df = df.copy()
        
        # Date range filter
        if start_date and end_date:
            try:
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                filtered_df['CreatedOn'] = pd.to_datetime(filtered_df['CreatedOn'])
                filtered_df = filtered_df[
                    (filtered_df['CreatedOn'] >= start_date) & 
                    (filtered_df['CreatedOn'] <= end_date)
                ]
            except Exception as e:
                print(f"⚠️ Error applying date filter: {e}")
        
        # AOR filter
        if selected_aor is not None and len(selected_aor) > 0 and "All" not in selected_aor:
            # print(f"Applying AOR filter: {selected_aor}")
            filtered_df = filtered_df[filtered_df["AorShortName"].isin(selected_aor)]
            
        # Case Type filter - using CaseTypeCode logic from filters
        if selected_case_types is not None and len(selected_case_types) > 0 and "All" not in selected_case_types:
            print(f"Applying Case Type filter: {selected_case_types}")
            filtered_df = filtered_df[filtered_df["WorkItemDefinitionShortCode"].isin(selected_case_types)]
            
        # Product filter
        if selected_products is not None and len(selected_products) > 0 and "All" not in selected_products:
            # print(f"Applying Product filter: {selected_products}")
            filtered_df = filtered_df[filtered_df["Product"].isin(selected_products)]

        # Module filter
        if selected_modules is not None and len(selected_modules) > 0 and "All" not in selected_modules:
            # print(f"Applying Module filter: {selected_modules}")
            filtered_df = filtered_df[filtered_df["Module"].isin(selected_modules)]

        # Feature filter
        if selected_features is not None and len(selected_features) > 0 and "All" not in selected_features:
            # print(f"Applying Feature filter: {selected_features}")
            filtered_df = filtered_df[filtered_df["Feature"].isin(selected_features)]
            
        # Issue filter
        if selected_issues is not None and len(selected_issues) > 0 and "All" not in selected_issues:
            # print(f"Applying Issue filter: {selected_issues}")
            filtered_df = filtered_df[filtered_df["Issue"].isin(selected_issues)]

        # Case Origin filter
        if selected_origins is not None and len(selected_origins) > 0 and "All" not in selected_origins:
            # print(f"Applying Case Origin filter: {selected_origins}")
            filtered_df = filtered_df[filtered_df["CaseOrigin"].isin(selected_origins)]
            
        # Case Reason filter
        if selected_reasons is not None and len(selected_reasons) > 0 and "All" not in selected_reasons:
            # print(f"Applying Case Reason filter: {selected_reasons}")
            filtered_df = filtered_df[filtered_df["CaseReason"].isin(selected_reasons)]

        # Status filter
        if selected_status is not None and len(selected_status) > 0 and "All" not in selected_status:
            # print(f"Applying Status filter: {selected_status}")
            filtered_df = filtered_df[filtered_df["WorkItemStatus"].isin(selected_status)]
            
        # Priority filter
        if selected_priority is not None and len(selected_priority) > 0 and "All" not in selected_priority:
            # print(f"Applying Priority filter: {selected_priority}")
            filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priority)]
            
        return filtered_df

    def parse_filter_selections(stored_selections):
        """Parse stored filter selections into individual components"""
        # print(f"Parsing stored selections: {stored_selections}")
        if not stored_selections:
            return {}
            
        try:
            # Extract filter values from stored selections
            # This should match the structure used in workflow_filters.py
            return {
                'selected_aor': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('AOR', '').split(', ') if item.strip("'")],
                'selected_case_types': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('CaseTypes', '').split(', ') if item.strip("'")],  
                'selected_status': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Status', '').split(', ') if item.strip("'")],
                'selected_priority': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Priority', '').split(', ') if item.strip("'")],
                'selected_origins': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Origins', '').split(', ') if item.strip("'")],
                'selected_reasons': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Reasons', '').split(', ') if item.strip("'")],
                'selected_products': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Products', '').split(', ') if item.strip("'")],
                'selected_features': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Features', '').split(', ') if item.strip("'")],
                'selected_modules': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Modules', '').split(', ') if item.strip("'")],
                'selected_issues': [item.strip("'") if item!= "'-'" else "" for item in stored_selections.get('Issues', '').split(', ') if item.strip("'")],
                'start_date': stored_selections.get('Day_From'),
                'end_date': stored_selections.get('Day_To')
            }
        except Exception as e:
            print(f"⚠️ Error parsing filter selections: {e}")
            return {}

    def format_duration(minutes):
        """Format duration from minutes to human readable format"""
        if pd.isna(minutes) or minutes == 0:
            return "0h"
        
        hours = int(minutes / 60)
        remaining_minutes = int(minutes % 60)
        
        if hours == 0:
            return f"{remaining_minutes}m"
        elif remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}m"

    # Show spinners when filters change
    @app.callback(
        [Output("workflow-total-tickets-spinner", "style", allow_duplicate=True),
         Output("workflow-open-tickets-spinner", "style", allow_duplicate=True),
         Output("workflow-escalated-tickets-spinner", "style", allow_duplicate=True),
         Output("workflow-avg-resolution-spinner", "style", allow_duplicate=True),
         Output("workflow-closed-tickets-spinner", "style", allow_duplicate=True),
         Output("workflow-active-assignees-spinner", "style", allow_duplicate=True)],
        [Input("workflow-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    def show_summary_card_spinners(stored_selections):
        """Show summary cards spinner when filter selections change"""
        spinner_style = {"position": "absolute", "top": "10px", "right": "10px", "visibility": "visible"}
        return tuple([spinner_style] * 6)

    @app.callback(
        [Output("workflow-total-tickets-value", "children"),
         Output("workflow-open-tickets-value", "children"),
         Output("workflow-escalated-tickets-value", "children"),
         Output("workflow-avg-resolution-value", "children"),
         Output("workflow-closed-tickets-value", "children"),
         Output("workflow-active-assignees-value", "children"),
         Output("workflow-total-tickets-spinner", "style"),
         Output("workflow-open-tickets-spinner", "style"),
         Output("workflow-escalated-tickets-spinner", "style"),
         Output("workflow-avg-resolution-spinner", "style"),
         Output("workflow-closed-tickets-spinner", "style"),
         Output("workflow-active-assignees-spinner", "style")],
        [Input("workflow-filtered-query-store", "data")],
        prevent_initial_call=False
    )
    @monitor_performance("Workflow Summary Cards Update")
    def update_workflow_summary_cards(stored_selections):
        """
        Update summary cards with filtered workflow data
        """
        # Default values - only card values, no trend components
        default_values = ["0", "0", "0", "0h", "0", "0"]
        hidden_spinner = {"position": "absolute", "top": "10px", "right": "10px", "visibility": "hidden"}
        
        try:
            # Fetch base data
            base_data = fetch_base_data()
            df_work_items = base_data.get('work_items', pd.DataFrame())
            df_durations = base_data.get('duration_summary', pd.DataFrame())
            
            if df_work_items.empty:
                print("⚠️ No work items data available")
                return default_values + [hidden_spinner] * 6
            
            # Parse filter selections
            filters = parse_filter_selections(stored_selections)
            # print(f"Applying filters: {filters}")
            # Apply filters to work items
            filtered_df = apply_filters_to_dataset(df_work_items, **filters)
            
            if filtered_df.empty:
                print("⚠️ No data after filtering")
                return default_values + [hidden_spinner] * 6
            
            # Calculate summary metrics
            
            # 1. Total Tickets
            total_tickets = len(filtered_df)
            
            # 2. Open Tickets (non-closed statuses)
            open_statuses = ['Open', 'In Progress', 'On Hold', 'Pending Verification', 'Scheduled', 'Not Started', 'Pending']
            open_tickets = len(filtered_df[
                filtered_df['WorkItemStatus'].isin(open_statuses) | 
                filtered_df['ClosedOn'].isna()
            ])
            
            # 3. Escalated Tickets
            escalated_tickets = len(filtered_df[filtered_df['IsEscalated'] == '1'])

            # 4. Average Resolution Time
            work_item_ids = filtered_df['WorkItemId'].tolist()
            if not df_durations.empty and work_item_ids:
                duration_filtered = df_durations[df_durations['WorkItemId'].isin(work_item_ids)]
                
                # Use OpenToClosed_Min or OpenToResolved_Min
                resolution_times = []
                for _, row in duration_filtered.iterrows():
                    if pd.notna(row['OpenToClosed_Min']):
                        resolution_times.append(row['OpenToClosed_Min'])
                    elif pd.notna(row['OpenToResolved_Min']):
                        resolution_times.append(row['OpenToResolved_Min'])
                
                avg_resolution_minutes = sum(resolution_times) / len(resolution_times) if resolution_times else 0
                avg_resolution_formatted = format_duration(avg_resolution_minutes)
            else:
                avg_resolution_formatted = "0h"
            
            # 5. Closed This Month
            current_month = datetime.now().replace(day=1)
            filtered_df['ClosedOn'] = pd.to_datetime(filtered_df['ClosedOn'], errors='coerce')
            closed_this_month = len(filtered_df[
                (filtered_df['ClosedOn'] >= current_month) & 
                (filtered_df['ClosedOn'].notna())
            ])
            
            # 6. Active Assignees (unique assigned users in current dataset)
            active_assignees = filtered_df['AssignedTo'].nunique() if 'AssignedTo' in filtered_df.columns else 0
            
            # Format values for display
            total_tickets_formatted = f"{total_tickets:,}"
            open_tickets_formatted = f"{open_tickets:,}"
            escalated_tickets_formatted = f"{escalated_tickets:,}"
            closed_tickets_formatted = f"{closed_this_month:,}"
            active_assignees_formatted = f"{active_assignees:,}"
            
            # print(f"📊 Workflow Summary Updated: Total={total_tickets}, Open={open_tickets}, Escalated={escalated_tickets}, Avg Res={avg_resolution_formatted}, Closed={closed_this_month}, Assignees={active_assignees}")
            
            return [
                total_tickets_formatted,
                open_tickets_formatted,
                escalated_tickets_formatted,
                avg_resolution_formatted,
                closed_tickets_formatted,
                active_assignees_formatted
            ] + [hidden_spinner] * 6
            
        except Exception as e:
            print(f"❌ Error updating workflow summary cards: {e}")
            import traceback
            traceback.print_exc()
            return default_values + [hidden_spinner] * 6