from dash import callback, Input, Output, State
import pandas as pd
import json
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

def register_compliance_filter_callbacks(app):
    """
    Register compliance filter callbacks with no precedence - each filter affects all others equally
    """

    # ✅ Single query function to load all compliance attributes
    def get_compliance_attributes_data():
        """Fetch all compliance attributes data - cached independently"""
        query = '''SELECT DISTINCT 
                      [AssignedUser],
                      [Disposition], 
                      [ViolationName],
                      [RuleNumber],
                      [RuleTitle],
                      [CitationFee],
                      [FineType],
                      [ReportIds]
                   FROM [consumable].[Fact_CaseDetails]
                   ORDER BY 
                      [AssignedUser],
                      [Disposition]'''
        
        result = run_queries({"compliance_attributes": query}, 'compliance', 1)
        compliance_df = result["compliance_attributes"]

        # Parse JSON columns
        compliance_df['ViolationName'] = compliance_df['ViolationName'].apply(json.loads)
        compliance_df['RuleNumber'] = compliance_df['RuleNumber'].apply(json.loads)
        compliance_df['RuleTitle'] = compliance_df['RuleTitle'].apply(json.loads)
        compliance_df['CitationFee'] = compliance_df['CitationFee'].apply(json.loads)
        compliance_df['FineType'] = compliance_df['FineType'].apply(json.loads)
        compliance_df['ReportIds'] = compliance_df['ReportIds'].apply(lambda x: json.loads(x) if pd.notna(x) else [])
        
        # Create NumReportIds column
        compliance_df.insert(compliance_df.columns.get_loc('ReportIds') + 1, 'NumReportIds', compliance_df['ReportIds'].apply(len))
        
        # Drop ReportIds as we only need the count
        compliance_df.drop('ReportIds', axis=1, inplace=True)

        return compliance_df

    def apply_filters_to_dataset(df, selected_disposition=None, selected_assigned_user=None, 
                                selected_violation_name=None, selected_rule_number=None,
                                selected_rule_title=None, selected_citation_fee=None, 
                                selected_fine_type=None, selected_num_reports=None):
        """Apply all non-empty filter selections to the dataset"""
        filtered_df = df.copy()
        
        if selected_disposition is not None and len(selected_disposition) > 0 and "All" not in selected_disposition:
            filtered_df = filtered_df[filtered_df["Disposition"].isin(selected_disposition)]
            # print(f"Filtered by Disposition: {selected_disposition}, Remaining Rows: {len(filtered_df)}")
        if selected_assigned_user is not None and len(selected_assigned_user) > 0 and "All" not in selected_assigned_user:
            filtered_df = filtered_df[filtered_df["AssignedUser"].isin(selected_assigned_user)]
            # print(f"Filtered by AssignedUser: {selected_assigned_user}, Remaining Rows: {len(filtered_df)}")
        if selected_violation_name is not None and len(selected_violation_name) > 0 and "All" not in selected_violation_name:
            # Handle list column - check if any values in the list match selected values
            filtered_df = filtered_df[filtered_df["ViolationName"].apply(lambda x: any(item in selected_violation_name for item in x))]
            # print(f"Filtered by ViolationName: {selected_violation_name}, Remaining Rows: {len(filtered_df)}")
        if selected_rule_number is not None and len(selected_rule_number) > 0 and "All" not in selected_rule_number:
            # Handle list column - check if any values in the list match selected values
            filtered_df = filtered_df[filtered_df["RuleNumber"].apply(lambda x: any(item in selected_rule_number for item in x))]
            # print(f"Filtered by RuleNumber: {selected_rule_number}, Remaining Rows: {len(filtered_df)}")
        if selected_rule_title is not None and len(selected_rule_title) > 0 and "All" not in selected_rule_title:
            # Handle list column - check if any values in the list match selected values
            filtered_df = filtered_df[filtered_df["RuleTitle"].apply(lambda x: any(item in selected_rule_title for item in x))]
            # print(f"Filtered by RuleTitle: {selected_rule_title}, Remaining Rows: {len(filtered_df)}")
        if selected_citation_fee is not None and len(selected_citation_fee) > 0 and "All" not in selected_citation_fee:
            # Handle list column - check if any values in the list match selected values
            filtered_df = filtered_df[filtered_df["CitationFee"].apply(lambda x: any(item in selected_citation_fee for item in x))]
            # print(f"Filtered by CitationFee: {selected_citation_fee}, Remaining Rows: {len(filtered_df)}")
        if selected_fine_type is not None and len(selected_fine_type) > 0 and "All" not in selected_fine_type:
            # Handle list column - check if any values in the list match selected values
            filtered_df = filtered_df[filtered_df["FineType"].apply(lambda x: any(item in selected_fine_type for item in x))]
            # print(f"Filtered by FineType: {selected_fine_type}, Remaining Rows: {len(filtered_df)}")
        if selected_num_reports is not None and len(selected_num_reports) > 0 and "All" not in selected_num_reports:
            # Convert selected values to integers for comparison
            selected_num_reports_int = [int(x) for x in selected_num_reports]
            filtered_df = filtered_df[filtered_df["NumReportIds"].isin(selected_num_reports_int)]
            # print(f"Filtered by NumReportIds: {selected_num_reports}, Remaining Rows: {len(filtered_df)}")

        return filtered_df

    def generate_dropdown_options(filtered_df, column_name, is_list_column=False):
        """Generate dropdown options from filtered dataframe"""
        column_map = {
            "Disposition": "Disposition",
            "AssignedUser": "AssignedUser", 
            "ViolationName": "ViolationName",
            "RuleNumber": "RuleNumber",
            "RuleTitle": "RuleTitle",
            "CitationFee": "CitationFee",
            "FineType": "FineType",
            "NumReportIds": "NumReportIds"
        }
        
        actual_column = column_map.get(column_name, column_name)
        label_prefix = pluralize(titleize(column_name.replace("NumReport", "Report count").replace("Assigned", "").replace("User", "Agent").replace("Ids", "").replace("Type", "")))
        # label_prefix = column_name.replace("Num", "Number of ").replace("Ids", "").replace("Type", "")
        
        options = [{"label": f"All {label_prefix}", "value": "All"}]
        
        if is_list_column:
            # Handle list columns - extract all unique values from lists
            unique_values = set()
            for item_list in filtered_df[actual_column]:
                if isinstance(item_list, list):
                    unique_values.update(item_list)
            
            for value in sorted(unique_values):
                if pd.notnull(value) and str(value).strip() != "":
                    str_value = str(value)
                    if column_name == "CitationFee":
                        # Format citation fees as currency
                        try:
                            fee_value = float(str_value)
                            if fee_value == 0:
                                label = "No Fee"
                            else:
                                label = f"${fee_value:,.2f}"
                        except:
                            label = str_value
                    elif column_name == "RuleNumber":
                        label = f"Rule - {str_value}" if str_value[0].isdigit() else str_value
                    elif column_name == "RuleTitle":
                        label = str_value if len(str_value) <= 100 else str_value[:97] + "..."
                    elif column_name == "FineType":
                        label = titleize(str_value)
                    else:
                        label = str_value
                    
                    options.append({"label": label, "value": str_value})
        else:
            # Handle regular columns
            for value in sorted(filtered_df[actual_column].dropna().unique()):
                if pd.notnull(value):
                    str_value = str(value)
                    if str_value.strip() == "":
                        continue
                    
                    if column_name == "NumReportIds":
                        # Format number of reports
                        label = f"{str_value} Report{'s' if int(str_value) != 1 else ''}"
                    else:
                        label = titleize(str_value)
                        label = label.replace("N/A", "").strip()
                    
                    options.append({"label": label, "value": str_value})
        
        return options

    # ✅ Initial filters - load all dropdowns with full dataset
    @callback(
        [Output("compliance-date-range-picker", "start_date_placeholder_text"),
         Output("compliance-date-range-picker", "end_date_placeholder_text"),
         Output("compliance-disposition-dropdown", "options"),
         Output("compliance-disposition-dropdown", "placeholder"),
         Output("compliance-disposition-spinner", "style"),
         Output("compliance-assigned-agent-dropdown", "options"),
         Output("compliance-assigned-agent-dropdown", "placeholder"),
         Output("compliance-assigned-agent-spinner", "style"),
         Output("compliance-violation-name-dropdown", "options"),
         Output("compliance-violation-name-dropdown", "placeholder"),
         Output("compliance-violation-name-spinner", "style"),
         Output("compliance-rule-number-dropdown", "options"),
         Output("compliance-rule-number-dropdown", "placeholder"),
         Output("compliance-rule-number-spinner", "style"),
         Output("compliance-rule-title-dropdown", "options"),
         Output("compliance-rule-title-dropdown", "placeholder"),
         Output("compliance-rule-title-spinner", "style"),
         Output("compliance-citation-fee-dropdown", "options"),
         Output("compliance-citation-fee-dropdown", "placeholder"),
         Output("compliance-citation-fee-spinner", "style"),
         Output("compliance-fine-type-dropdown", "options"),
         Output("compliance-fine-type-dropdown", "placeholder"),
         Output("compliance-fine-type-spinner", "style"),
         Output("compliance-num-reports-dropdown", "options"),
         Output("compliance-num-reports-dropdown", "placeholder"),
         Output("compliance-num-reports-spinner", "style")],     
        Input("compliance-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    @monitor_performance("Compliance Initial Filters Population")
    def populate_initial_filters(_):
        """
        Populate all filters initially from full Fact_CaseDetails dataset
        """
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        
        try:
            # ✅ Fetch all compliance attributes data
            df_attributes = get_compliance_attributes_data()
            
            # Generate options for all dropdowns using full dataset
            disposition_options = generate_dropdown_options(df_attributes, "Disposition")
            assigned_user_options = generate_dropdown_options(df_attributes, "AssignedUser")
            violation_name_options = generate_dropdown_options(df_attributes, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(df_attributes, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(df_attributes, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(df_attributes, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(df_attributes, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(df_attributes, "NumReportIds")
            
            return (
                str(start_placeholder), str(end_placeholder), 
                disposition_options, "Select Disposition...", {'display': 'none'},
                assigned_user_options, "Select Agent...", {'display': 'none'},
                violation_name_options, "Select Violation Names...", {'display': 'none'},
                rule_number_options, "Select Rule Numbers...", {'display': 'none'},
                rule_title_options, "Search Rule Title...", {'display': 'none'},
                citation_fee_options, "Select Citation Fee...", {'display': 'none'},
                fine_type_options, "Select Fine Type...", {'display': 'none'},
                num_reports_options, "Select Number of Reports...", {'display': 'none'}
            )
            
        except Exception as e:
            print(f"❌ Error loading initial compliance filters: {e}")
            import traceback
            traceback.print_exc()
            return (
                str(start_placeholder), str(end_placeholder),
                [], "Error loading Disposition", {"visibility": "hidden"},
                [], "Error loading Assigned Agents", {"visibility": "hidden"},
                [], "Error loading Violation Names", {"visibility": "hidden"},
                [], "Error loading Rule Numbers", {"visibility": "hidden"},
                [], "Error loading Rule Titles", {"visibility": "hidden"},
                [], "Error loading Citation Fees", {"visibility": "hidden"},
                [], "Error loading Fine Types", {"visibility": "hidden"},
                [], "Error loading Number of Reports", {"visibility": "hidden"}
            )

    # ✅ Disposition dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-disposition-dropdown", "value"),
        [State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Disposition Filter Change - Update All Others")
    def update_filters_on_disposition_change(selected_disposition, selected_assigned_user, selected_violation_name,
                                            selected_rule_number, selected_rule_title, selected_citation_fee,
                                            selected_fine_type, selected_num_reports):
        """When Disposition selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                assigned_user_options, violation_name_options, rule_number_options,
                rule_title_options, citation_fee_options, fine_type_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Disposition change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Assigned Agent dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-assigned-agent-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Assigned Agent Filter Change - Update All Others")
    def update_filters_on_assigned_user_change(selected_assigned_user, selected_disposition, selected_violation_name,
                                              selected_rule_number, selected_rule_title, selected_citation_fee,
                                              selected_fine_type, selected_num_reports):
        """When Assigned Agent selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                disposition_options, violation_name_options, rule_number_options,
                rule_title_options, citation_fee_options, fine_type_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Assigned Agent change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Violation Name dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-violation-name-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Violation Name Filter Change - Update All Others")
    def update_filters_on_violation_name_change(selected_violation_name, selected_disposition, selected_assigned_user,
                                               selected_rule_number, selected_rule_title, selected_citation_fee,
                                               selected_fine_type, selected_num_reports):
        """When Violation Name selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                disposition_options, assigned_user_options, rule_number_options,
                rule_title_options, citation_fee_options, fine_type_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Violation Name change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Rule Number dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-rule-number-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Rule Number Filter Change - Update All Others")
    def update_filters_on_rule_number_change(selected_rule_number, selected_disposition, selected_assigned_user,
                                            selected_violation_name, selected_rule_title, selected_citation_fee,
                                            selected_fine_type, selected_num_reports):
        """When Rule Number selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                disposition_options, assigned_user_options, violation_name_options,
                rule_title_options, citation_fee_options, fine_type_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Rule Number change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Rule Title dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-rule-title-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Rule Title Filter Change - Update All Others")
    def update_filters_on_rule_title_change(selected_rule_title, selected_disposition, selected_assigned_user,
                                           selected_violation_name, selected_rule_number, selected_citation_fee,
                                           selected_fine_type, selected_num_reports):
        """When Rule Title selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                disposition_options, assigned_user_options, violation_name_options,
                rule_number_options, citation_fee_options, fine_type_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Rule Title change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Citation Fee dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-citation-fee-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Citation Fee Filter Change - Update All Others")
    def update_filters_on_citation_fee_change(selected_citation_fee, selected_disposition, selected_assigned_user,
                                             selected_violation_name, selected_rule_number, selected_rule_title,
                                             selected_fine_type, selected_num_reports):
        """When Citation Fee selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                disposition_options, assigned_user_options, violation_name_options,
                rule_number_options, rule_title_options, fine_type_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Citation Fee change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Fine Type dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "options", allow_duplicate=True)],
        Input("compliance-fine-type-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Fine Type Filter Change - Update All Others")
    def update_filters_on_fine_type_change(selected_fine_type, selected_disposition, selected_assigned_user,
                                          selected_violation_name, selected_rule_number, selected_rule_title,
                                          selected_citation_fee, selected_num_reports):
        """When Fine Type selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            num_reports_options = generate_dropdown_options(filtered_df, "NumReportIds")
            
            return (
                disposition_options, assigned_user_options, violation_name_options,
                rule_number_options, rule_title_options, citation_fee_options, num_reports_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Fine Type change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Number of Reports dropdown change - updates all other dropdowns
    @callback(
        [Output("compliance-disposition-dropdown", "options", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "options", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "options", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "options", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "options", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "options", allow_duplicate=True)],
        Input("compliance-num-reports-dropdown", "value"),
        [State("compliance-disposition-dropdown", "value"),
         State("compliance-assigned-agent-dropdown", "value"),
         State("compliance-violation-name-dropdown", "value"),
         State("compliance-rule-number-dropdown", "value"),
         State("compliance-rule-title-dropdown", "value"),
         State("compliance-citation-fee-dropdown", "value"),
         State("compliance-fine-type-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Number of Reports Filter Change - Update All Others")
    def update_filters_on_num_reports_change(selected_num_reports, selected_disposition, selected_assigned_user,
                                            selected_violation_name, selected_rule_number, selected_rule_title,
                                            selected_citation_fee, selected_fine_type):
        """When Number of Reports selection changes, update all other dropdown options"""
        try:
            df_attributes = get_compliance_attributes_data()
            
            # Apply all current filter selections
            filtered_df = apply_filters_to_dataset(
                df_attributes,
                selected_disposition=selected_disposition,
                selected_assigned_user=selected_assigned_user,
                selected_violation_name=selected_violation_name,
                selected_rule_number=selected_rule_number,
                selected_rule_title=selected_rule_title,
                selected_citation_fee=selected_citation_fee,
                selected_fine_type=selected_fine_type,
                selected_num_reports=selected_num_reports
            )
            
            # Generate updated options for all other dropdowns
            disposition_options = generate_dropdown_options(filtered_df, "Disposition")
            assigned_user_options = generate_dropdown_options(filtered_df, "AssignedUser")
            violation_name_options = generate_dropdown_options(filtered_df, "ViolationName", is_list_column=True)
            rule_number_options = generate_dropdown_options(filtered_df, "RuleNumber", is_list_column=True)
            rule_title_options = generate_dropdown_options(filtered_df, "RuleTitle", is_list_column=True)
            citation_fee_options = generate_dropdown_options(filtered_df, "CitationFee", is_list_column=True)
            fine_type_options = generate_dropdown_options(filtered_df, "FineType", is_list_column=True)
            
            return (
                disposition_options, assigned_user_options, violation_name_options,
                rule_number_options, rule_title_options, citation_fee_options, fine_type_options
            )
            
        except Exception as e:
            print(f"❌ Error updating filters on Number of Reports change: {e}")
            return ([], [], [], [], [], [], [])

    # ✅ Clear filters callback
    @callback(
        [Output("compliance-date-range-picker", "start_date", allow_duplicate=True),
         Output("compliance-date-range-picker", "end_date", allow_duplicate=True),
         Output("compliance-disposition-dropdown", "value", allow_duplicate=True),
         Output("compliance-assigned-agent-dropdown", "value", allow_duplicate=True),
         Output("compliance-violation-name-dropdown", "value", allow_duplicate=True),
         Output("compliance-rule-number-dropdown", "value", allow_duplicate=True),
         Output("compliance-rule-title-dropdown", "value", allow_duplicate=True),
         Output("compliance-citation-fee-dropdown", "value", allow_duplicate=True),
         Output("compliance-fine-type-dropdown", "value", allow_duplicate=True),
         Output("compliance-num-reports-dropdown", "value", allow_duplicate=True)],
        Input("compliance-clear-filters-btn", "n_clicks"),
        prevent_initial_call=True
    )
    @monitor_performance("Compliance Clear All Filters")
    def clear_all_filters(n_clicks):
        """Clear all filter selections"""
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()
        
        return (
            date_start_default, date_end_default,
            [], [], [], [], [], [], [], []  # Clear all dropdown selections
        )

    # ✅ Store filter selections
    @app.callback(
        Output("compliance-filtered-query-store", "data"),     
        [Input("compliance-date-range-picker", "start_date"),
         Input("compliance-date-range-picker", "end_date"),  
         Input("compliance-disposition-dropdown", "value"),
         Input("compliance-assigned-agent-dropdown", "value"),
         Input("compliance-violation-name-dropdown", "value"),
         Input("compliance-rule-number-dropdown", "value"),
         Input("compliance-rule-title-dropdown", "value"),
         Input("compliance-citation-fee-dropdown", "value"),
         Input("compliance-fine-type-dropdown", "value"),
         Input("compliance-num-reports-dropdown", "value")],
        prevent_initial_call=False
    )
    def filter_data_query(start_date, end_date, selected_disposition, selected_assigned_user,
                          selected_violation_name, selected_rule_number, selected_rule_title,
                          selected_citation_fee, selected_fine_type, selected_num_reports):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        
        selections = {
            "Day_From": start_date if start_date is not None else start_placeholder,
            "Day_To": end_date if end_date is not None else end_placeholder,
            "Disposition": ", ".join([f"'{disposition}'" for disposition in selected_disposition]) if selected_disposition and len(selected_disposition) > 0 and "All" not in selected_disposition else "",
            "AssignedUser": ", ".join([f"'{user}'" for user in selected_assigned_user]) if selected_assigned_user and len(selected_assigned_user) > 0 and "All" not in selected_assigned_user else "",
            "ViolationName": ", ".join([f"'{violation}'" for violation in selected_violation_name]) if selected_violation_name and len(selected_violation_name) > 0 and "All" not in selected_violation_name else "",
            "RuleNumber": ", ".join([f"'{rule}'" for rule in selected_rule_number]) if selected_rule_number and len(selected_rule_number) > 0 and "All" not in selected_rule_number else "",
            "RuleTitle": ", ".join([f"'{title}'" for title in selected_rule_title]) if selected_rule_title and len(selected_rule_title) > 0 and "All" not in selected_rule_title else "",
            "CitationFee": ", ".join([f"'{fee}'" for fee in selected_citation_fee]) if selected_citation_fee and len(selected_citation_fee) > 0 and "All" not in selected_citation_fee else "",
            "FineType": ", ".join([f"'{fine_type}'" for fine_type in selected_fine_type]) if selected_fine_type and len(selected_fine_type) > 0 and "All" not in selected_fine_type else "",
            "NumReports": ", ".join([f"{num}" for num in selected_num_reports]) if selected_num_reports and len(selected_num_reports) > 0 and "All" not in selected_num_reports else ""
        }
        
        return selections

    # print("✅ Compliance filter callbacks registered (no precedence - all filters equal)")