from dash import callback, Input, Output, State
import pandas as pd
from datetime import datetime
from src.utils.db import run_queries
import time
from inflection import titleize, pluralize
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

def register_workflow_filter_callbacks(app):
    """
    Register workflow filter callbacks with no precedence - each filter affects all others equally
    """

    # ✅ Single query function to load all attributes
    def get_work_item_attributes_data():
        """Fetch all work item attributes data - cached independently"""
        query = '''SELECT DISTINCT [Aor], [CaseTypeCode], [CaseTypeName], [CaseOrigin], 
                          [CaseReason], [Feature], [Issue], [Product], [Module], [Priority], [Status]
                   FROM [consumable].[Dim_WorkItemAttributes]
                   ORDER BY [Aor], [CaseTypeCode], [CaseOrigin], [CaseReason], [Feature], 
                           [Issue], [Product], [Module], [Priority], [Status]'''
        result = run_queries({"work_item_attributes": query}, 'workflow', 1)
        work_item_df = result["work_item_attributes"]

        aor_query = 'SELECT DISTINCT [AorShortName] , [AorName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
        aor_result = run_queries({"aor_details": aor_query}, 'training', 1)
        aor_df = aor_result["aor_details"]

        aor_df['AorName'] = (aor_df['AorName']
                            .str.replace(r' Association of Realtors', '', case=False, regex=True)
                            .str.replace(r' Board of Realtors', '', case=False, regex=True)
                            .str.replace(r' Realtors', '', case=False, regex=True)
                            .str.replace(r' BOR', '', case=False, regex=True)
                            .str.replace(r' Board', '', case=False, regex=True)
                            .str.strip())

        aor_mapping = dict(zip(aor_df['AorShortName'], aor_df['AorName']))
        aor_mapping[''] = 'Unspecified'  # Empty string
        aor_mapping[None] = 'Unspecified' 
        work_item_df['AorName'] = work_item_df['Aor'].map(aor_mapping).fillna('Unspecified')
        columns = work_item_df.columns.tolist()
        aor_index = columns.index('Aor')
        columns.insert(aor_index + 1, columns.pop(columns.index('AorName')))
        work_item_df = work_item_df[columns]    

        return work_item_df

    def apply_filters_to_dataset(df, selected_aor=None, selected_case_types=None, selected_status=None, 
                                selected_priority=None, selected_origins=None, selected_reasons=None,
                                selected_products=None, selected_features=None, selected_modules=None, 
                                selected_issues=None):
        """Apply all non-empty filter selections to the dataset"""
        filtered_df = df.copy()
        
        if selected_aor is not None and len(selected_aor) > 0 and "All" not in selected_aor:
            filtered_df = filtered_df[filtered_df["Aor"].isin(selected_aor)]
        if selected_case_types is not None and len(selected_case_types) > 0 and "All" not in selected_case_types:
            filtered_df = filtered_df[filtered_df["CaseTypeCode"].isin(selected_case_types)]
        if selected_status is not None and len(selected_status) > 0 and "All" not in selected_status:
            filtered_df = filtered_df[filtered_df["Status"].isin(selected_status)]
        if selected_priority is not None and len(selected_priority) > 0 and "All" not in selected_priority:
            filtered_df = filtered_df[filtered_df["Priority"].isin(selected_priority)]
        if selected_origins is not None and len(selected_origins) > 0 and "All" not in selected_origins:
            filtered_df = filtered_df[filtered_df["CaseOrigin"].isin(selected_origins)]
        if selected_reasons is not None and len(selected_reasons) > 0 and "All" not in selected_reasons:
            filtered_df = filtered_df[filtered_df["CaseReason"].isin(selected_reasons)]
        if selected_products is not None and len(selected_products) > 0 and "All" not in selected_products:
            filtered_df = filtered_df[filtered_df["Product"].isin(selected_products)]
        if selected_features is not None and len(selected_features) > 0 and "All" not in selected_features:
            filtered_df = filtered_df[filtered_df["Feature"].isin(selected_features)]
        if selected_modules is not None and len(selected_modules) > 0 and "All" not in selected_modules:
            filtered_df = filtered_df[filtered_df["Module"].isin(selected_modules)]
        if selected_issues is not None and len(selected_issues) > 0 and "All" not in selected_issues:
            filtered_df = filtered_df[filtered_df["Issue"].isin(selected_issues)]
            
        return filtered_df

    def generate_dropdown_options(filtered_df, column_name, special_case_type=False, special_aor=False):
        """Generate dropdown options from filtered dataframe"""
        if special_case_type and column_name == "CaseType":
            # Special handling for Case Type - value=CaseTypeCode, label=CaseTypeName
            case_type_df = filtered_df[['CaseTypeCode', 'CaseTypeName']].dropna().drop_duplicates()
            return [{"label": "All Case Types", "value": "All"}] + [
                {"label": row['CaseTypeName'], "value": str(row['CaseTypeCode'])}
                for _, row in case_type_df.iterrows() if pd.notnull(row['CaseTypeCode'])
            ]
        elif special_aor and column_name == "Aor":
            # Special handling for AOR - value=Aor, label=Aor-AorName
            aor_df = filtered_df[['Aor', 'AorName']].dropna().drop_duplicates()
            options = [{"label": "All AORs", "value": "All"}]
            
            for _, row in aor_df.iterrows():
                if pd.notnull(row['Aor']) and pd.notnull(row['AorName']):
                    aor_value = str(row['Aor'])
                    aor_name = row['AorName']
                    
                    # ✅ Special case: if AOR is empty string and AorName is "Unspecified"
                    if aor_value == "" and aor_name == "Unspecified":
                        label = "Unspecified"
                        aor_value = "-"  # Use placeholder value for empty string
                    else:
                        label = f"{aor_value} - {aor_name}"
                    
                    options.append({"label": label, "value": aor_value})
            
            return options
        else:
            # Regular handling for other columns
            column_map = {
                "Aor": "Aor",
                "Status": "Status", 
                "Priority": "Priority",
                "CaseOrigin": "CaseOrigin",
                "CaseReason": "CaseReason",
                "Product": "Product",
                "Feature": "Feature",
                "Module": "Module",
                "Issue": "Issue"
            }
            
            actual_column = column_map.get(column_name, column_name)
            label_prefix = pluralize(titleize(column_name)) 
            
            options = [{"label": f"All {label_prefix}", "value": "All"}]
            
            # ✅ Handle empty strings by showing "Unspecified" as label
            for value in sorted(filtered_df[actual_column].dropna().unique()):
                if pd.notnull(value):
                    str_value = str(value)
                    # ✅ Special case: if value is empty string, show "Unspecified" as label
                    if str_value == "":
                        label = "Unspecified"
                        str_value = "-"  # Use placeholder value for empty string
                    else:
                        label = titleize(str_value)
                        label = label.replace("N/A", "").strip()                    
                    
                    options.append({"label": label, "value": str_value})
            
            return options

    # ✅ Initial filters - load all dropdowns with full dataset
    @callback(
        [Output("workflow-date-range-picker", "start_date_placeholder_text"),
         Output("workflow-date-range-picker", "end_date_placeholder_text"),
         Output("workflow-aor-dropdown", "options"),
         Output("workflow-aor-dropdown", "placeholder"),
         Output("workflow-aor-spinner", "style"),
         Output("workflow-case-type-dropdown", "options"),
         Output("workflow-case-type-dropdown", "placeholder"),
         Output("workflow-case-type-spinner", "style"),
         Output("workflow-status-dropdown", "options"),
         Output("workflow-status-dropdown", "placeholder"),
         Output("workflow-status-spinner", "style"),
         Output("workflow-priority-dropdown", "options"),
         Output("workflow-priority-dropdown", "placeholder"),
         Output("workflow-priority-spinner", "style"),
         Output("workflow-origin-dropdown", "options"),
         Output("workflow-origin-dropdown", "placeholder"),
         Output("workflow-origin-spinner", "style"),
         Output("workflow-case-reason-dropdown", "options"),
         Output("workflow-case-reason-dropdown", "placeholder"),
         Output("workflow-case-reason-spinner", "style"),
         Output("workflow-product-dropdown", "options"),
         Output("workflow-product-dropdown", "placeholder"),
         Output("workflow-product-spinner", "style"),
         Output("workflow-feature-dropdown", "options"),
         Output("workflow-feature-dropdown", "placeholder"),
         Output("workflow-feature-spinner", "style"),
         Output("workflow-module-dropdown", "options"),
         Output("workflow-module-dropdown", "placeholder"),
         Output("workflow-module-spinner", "style"),
         Output("workflow-issue-dropdown", "options"),
         Output("workflow-issue-dropdown", "placeholder"),
         Output("workflow-issue-spinner", "style")],     
        Input("workflow-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    @monitor_performance("Workflow Initial Filters Population")
    def populate_initial_filters(_):
        """
        Populate all filters initially from full Dim_WorkItemAttributes dataset
        """
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        
        try:
            # ✅ Fetch all attributes data
            df_attributes = get_work_item_attributes_data()
            
            # Generate options for all dropdowns using full dataset
            aor_options = generate_dropdown_options(df_attributes, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(df_attributes, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(df_attributes, "Status")
            priority_options = generate_dropdown_options(df_attributes, "Priority")
            origin_options = generate_dropdown_options(df_attributes, "CaseOrigin")
            reason_options = generate_dropdown_options(df_attributes, "CaseReason")
            product_options = generate_dropdown_options(df_attributes, "Product")
            feature_options = generate_dropdown_options(df_attributes, "Feature")
            module_options = generate_dropdown_options(df_attributes, "Module")
            issue_options = generate_dropdown_options(df_attributes, "Issue")
            
            return (
                str(start_placeholder), str(end_placeholder), 
                aor_options, "Select AORs...", {'display': 'none'},
                case_type_options, "Select Case Types...", {'display': 'none'},
                status_options, "Select Statuses...", {'display': 'none'},
                priority_options, "Select Priorities...", {'display': 'none'},
                origin_options, "Select Case Origins...", {'display': 'none'},
                reason_options, "Select Case Reasons...", {'display': 'none'},
                product_options, "Select Products...", {'display': 'none'},
                feature_options, "Select Features...", {'display': 'none'},
                module_options, "Select Modules...", {'display': 'none'},
                issue_options, "Select Issues...", {'display': 'none'}
            )
            
        except Exception as e:
            print(f"❌ Error loading initial filters: {e}")
            import traceback
            traceback.print_exc()
            return (
                str(start_placeholder), str(end_placeholder),
                [], "Error loading AORs", {"visibility": "hidden"},
                [], "Error loading Case Types", {"visibility": "hidden"},
                [], "Error loading Statuses", {"visibility": "hidden"},
                [], "Error loading Priorities", {"visibility": "hidden"},
                [], "Error loading Case Origins", {"visibility": "hidden"},
                [], "Error loading Case Reasons", {"visibility": "hidden"},
                [], "Error loading Products", {"visibility": "hidden"},
                [], "Error loading Features", {"visibility": "hidden"},
                [], "Error loading Modules", {"visibility": "hidden"},
                [], "Error loading Issues", {"visibility": "hidden"}
            )

    # ✅ AOR dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-aor-dropdown", "value"),
        [State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("AOR Filter Change - Update All Others")
    def update_filters_on_aor_change(selected_aor, selected_case_types, selected_status, selected_priority,
                                     selected_origins, selected_reasons, selected_products, selected_features,
                                     selected_modules, selected_issues):
        """When AOR selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                case_type_options, status_options, priority_options,
                origin_options, reason_options, product_options,
                feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on AOR change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Case Type dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-case-type-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Case Type Filter Change - Update All Others")
    def update_filters_on_case_type_change(selected_case_types, selected_aor, selected_status, selected_priority,
                                           selected_origins, selected_reasons, selected_products, selected_features,
                                           selected_modules, selected_issues):
        """When Case Type selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, status_options, priority_options,
                origin_options, reason_options, product_options,
                feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Case Type change: {e}")
            return ([], [], [], [], [], [], [], [], [])
        
    # ✅ Status dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-status-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Status Filter Change - Update All Others")
    def update_filters_on_status_change(selected_status, selected_aor, selected_case_types, selected_priority,
                                        selected_origins, selected_reasons, selected_products, selected_features,
                                        selected_modules, selected_issues):
        """When Status selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, priority_options,
                origin_options, reason_options, product_options,
                feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Status change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Priority dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-priority-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Priority Filter Change - Update All Others")
    def update_filters_on_priority_change(selected_priority, selected_aor, selected_case_types, selected_status,
                                          selected_origins, selected_reasons, selected_products, selected_features,
                                          selected_modules, selected_issues):
        """When Priority selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, status_options,
                origin_options, reason_options, product_options,
                feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Priority change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Case Origin dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-origin-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Origin Filter Change - Update All Others")
    def update_filters_on_origin_change(selected_origins, selected_aor, selected_case_types, selected_status,
                                        selected_priority, selected_reasons, selected_products, selected_features,
                                        selected_modules, selected_issues):
        """When Origin selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, status_options, priority_options,
                reason_options, product_options, feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Origin change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Case Reason dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-case-reason-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Case Reason Filter Change - Update All Others")
    def update_filters_on_case_reason_change(selected_reasons, selected_aor, selected_case_types, selected_status,
                                             selected_priority, selected_origins, selected_products, selected_features,
                                             selected_modules, selected_issues):
        """When Case Reason selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, status_options, priority_options,
                origin_options, product_options, feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Case Reason change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Product dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-product-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Product Filter Change - Update All Others")
    def update_filters_on_product_change(selected_products, selected_aor, selected_case_types, selected_status,
                                         selected_priority, selected_origins, selected_reasons, selected_features,
                                         selected_modules, selected_issues):
        """When Product selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, status_options, priority_options,
                origin_options, reason_options, feature_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Product change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Feature dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-feature-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-module-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Feature Filter Change - Update All Others")
    def update_filters_on_feature_change(selected_features, selected_aor, selected_case_types, selected_status,
                                         selected_priority, selected_origins, selected_reasons, selected_products,
                                         selected_modules, selected_issues):
        """When Feature selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            module_options = generate_dropdown_options(filtered_df, "Module")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, status_options, priority_options,
                origin_options, reason_options, product_options, module_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Feature change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Module dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-issue-dropdown", "options", allow_duplicate=True)],
        Input("workflow-module-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-issue-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Module Filter Change - Update All Others")
    def update_filters_on_module_change(selected_modules, selected_aor, selected_case_types, selected_status,
                                        selected_priority, selected_origins, selected_reasons, selected_products,
                                        selected_features, selected_issues):
        """When Module selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            issue_options = generate_dropdown_options(filtered_df, "Issue")
            
            return (
                aor_options, case_type_options, status_options, priority_options,
                origin_options, reason_options, product_options, feature_options, issue_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Module change: {e}")
            return ([], [], [], [], [], [], [], [], [])

    # ✅ Issue dropdown change - updates all other dropdowns
    @callback(
        [Output("workflow-aor-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "options", allow_duplicate=True),
         Output("workflow-status-dropdown", "options", allow_duplicate=True),
         Output("workflow-priority-dropdown", "options", allow_duplicate=True),
         Output("workflow-origin-dropdown", "options", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "options", allow_duplicate=True),
         Output("workflow-product-dropdown", "options", allow_duplicate=True),
         Output("workflow-feature-dropdown", "options", allow_duplicate=True),
         Output("workflow-module-dropdown", "options", allow_duplicate=True)],
        Input("workflow-issue-dropdown", "value"),
        [State("workflow-aor-dropdown", "value"),
         State("workflow-case-type-dropdown", "value"),
         State("workflow-status-dropdown", "value"),
         State("workflow-priority-dropdown", "value"),
         State("workflow-origin-dropdown", "value"),
         State("workflow-case-reason-dropdown", "value"),
         State("workflow-product-dropdown", "value"),
         State("workflow-feature-dropdown", "value"),
         State("workflow-module-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Issue Filter Change - Update All Others")
    def update_filters_on_issue_change(selected_issues, selected_aor, selected_case_types, selected_status,
                                       selected_priority, selected_origins, selected_reasons, selected_products,
                                       selected_features, selected_modules):
        """When Issue selection changes, update all other dropdown options"""
        try:
            df_attributes = get_work_item_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_aor=selected_aor,
                selected_case_types=selected_case_types,
                selected_status=selected_status,
                selected_priority=selected_priority,
                selected_origins=selected_origins,
                selected_reasons=selected_reasons,
                selected_products=selected_products,
                selected_features=selected_features,
                selected_modules=selected_modules,
                selected_issues=selected_issues
            )
            
            # Generate updated options for all other dropdowns
            aor_options = generate_dropdown_options(filtered_df, "Aor", special_aor=True)
            case_type_options = generate_dropdown_options(filtered_df, "CaseType", special_case_type=True)
            status_options = generate_dropdown_options(filtered_df, "Status")
            priority_options = generate_dropdown_options(filtered_df, "Priority")
            origin_options = generate_dropdown_options(filtered_df, "CaseOrigin")
            reason_options = generate_dropdown_options(filtered_df, "CaseReason")
            product_options = generate_dropdown_options(filtered_df, "Product")
            feature_options = generate_dropdown_options(filtered_df, "Feature")
            module_options = generate_dropdown_options(filtered_df, "Module")
            
            return (
                aor_options, case_type_options, status_options, priority_options,
                origin_options, reason_options, product_options, feature_options, module_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Issue change: {e}")
            return ([], [], [], [], [], [], [], [], [])


    # ✅ Clear filters callback
    @callback(
        [Output("workflow-date-range-picker", "start_date", allow_duplicate=True),
         Output("workflow-date-range-picker", "end_date", allow_duplicate=True),
         Output("workflow-aor-dropdown", "value", allow_duplicate=True),
         Output("workflow-case-type-dropdown", "value", allow_duplicate=True),
         Output("workflow-status-dropdown", "value", allow_duplicate=True),
         Output("workflow-priority-dropdown", "value", allow_duplicate=True),
         Output("workflow-origin-dropdown", "value", allow_duplicate=True),
         Output("workflow-case-reason-dropdown", "value", allow_duplicate=True),
         Output("workflow-product-dropdown", "value", allow_duplicate=True),
         Output("workflow-feature-dropdown", "value", allow_duplicate=True),
         Output("workflow-module-dropdown", "value", allow_duplicate=True),
         Output("workflow-issue-dropdown", "value", allow_duplicate=True)],
        Input("workflow-clear-filters-btn", "n_clicks"),
        prevent_initial_call=True
    )
    @monitor_performance("Workflow Clear All Filters")
    def clear_all_filters(n_clicks):
        """Clear all filter selections"""
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()
        
        return (
            date_start_default, date_end_default,
            [], [], [], [], [], [], [], [], [], []  # Clear all dropdown selections
        )

    # ✅ Store filter selections
    @app.callback(
        Output("workflow-filtered-query-store", "data"),     
        [Input("workflow-date-range-picker", "start_date"),
         Input("workflow-date-range-picker", "end_date"),  
         Input("workflow-aor-dropdown", "value"),
         Input("workflow-case-type-dropdown", "value"),
         Input("workflow-status-dropdown", "value"),
         Input("workflow-priority-dropdown", "value"),
         Input("workflow-origin-dropdown", "value"),
         Input("workflow-case-reason-dropdown", "value"),
         Input("workflow-product-dropdown", "value"),
         Input("workflow-feature-dropdown", "value"),
         Input("workflow-module-dropdown", "value"),
         Input("workflow-issue-dropdown", "value")],
        prevent_initial_call=False
    )
    def filter_data_query(start_date, end_date, 
                          selected_aor, selected_case_types, selected_status, selected_priority, 
                          selected_origins, selected_reasons, selected_products, selected_features,
                          selected_modules, selected_issues):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        
        selections = {
            "Day_From": start_date if start_date is not None else start_placeholder,
            "Day_To": end_date if end_date is not None else end_placeholder,
            "AOR": ", ".join([f"'{aor}'" for aor in selected_aor]) if selected_aor and len(selected_aor) > 0 and "All" not in selected_aor else "",
            "CaseTypes": ", ".join([f"'{case_type}'" for case_type in selected_case_types]) if selected_case_types and len(selected_case_types) > 0 and "All" not in selected_case_types else "",
            "Status": ", ".join([f"'{status}'" for status in selected_status]) if selected_status and len(selected_status) > 0 and "All" not in selected_status else "",
            "Priority": ", ".join([f"'{priority}'" for priority in selected_priority]) if selected_priority and len(selected_priority) > 0 and "All" not in selected_priority else "",
            "Origins": ", ".join([f"'{origin}'" for origin in selected_origins]) if selected_origins and len(selected_origins) > 0 and "All" not in selected_origins else "",
            "Reasons": ", ".join([f"'{reason}'" for reason in selected_reasons]) if selected_reasons and len(selected_reasons) > 0 and "All" not in selected_reasons else "",
            "Products": ", ".join([f"'{product}'" for product in selected_products]) if selected_products and len(selected_products) > 0 and "All" not in selected_products else "",
            "Features": ", ".join([f"'{feature}'" for feature in selected_features]) if selected_features and len(selected_features) > 0 and "All" not in selected_features else "",
            "Modules": ", ".join([f"'{module}'" for module in selected_modules]) if selected_modules and len(selected_modules) > 0 and "All" not in selected_modules else "",
            "Issues": ", ".join([f"'{issue}'" for issue in selected_issues]) if selected_issues and len(selected_issues) > 0 and "All" not in selected_issues else ""
        }
        
        return selections

    # print("✅ Workflow filter callbacks registered (no precedence - all filters equal)")