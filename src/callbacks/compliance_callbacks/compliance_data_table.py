from dash import callback, ctx, dcc, html, Input, Output, State, no_update, dash_table
import pandas as pd
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
import base64
from datetime import datetime, timedelta
from src.utils.compliance_data import (
    get_compliance_base_data, 
    apply_compliance_filters,
    classify_case_severity,
    get_event_history,
    get_case_flow_with_lifecycle_stages,
    prepare_html_content
)
from src.utils.performance import monitor_performance, monitor_query_performance
import json
import re

def register_compliance_data_table_callbacks(app):
    """
    Register compliance data table callbacks with export functionality
    Matches the component IDs from the layout file
    """
    
    @monitor_query_performance("Compliance Data Table Base Data")
    def get_compliance_data_table_base_data():
        """
        Get comprehensive base data for all compliance report types
        Uses cached compliance base data optimized for reporting
        """
        try:
            # Get merged compliance case details (already cached)
            base_df = get_compliance_base_data()
            
            if base_df.empty:
                print("⚠️ No compliance base data available")
                return {}
            
            # Get additional enriched data
            event_history_df = get_event_history()
            case_flow_df = get_case_flow_with_lifecycle_stages()
            classified_df = classify_case_severity(base_df)
            
            return {
                "case_details": base_df,
                "event_history": event_history_df, 
                "case_flow": case_flow_df,
                "classified_cases": classified_df
            }
            
        except Exception as e:
            print(f"❌ Error getting compliance data table base data: {e}")
            return {}

    def parse_list_field(field_value, default="N/A"):
        """Parse list fields safely for display - handles numpy arrays and pandas Series"""
        try:
            # Handle None/NaN cases first
            if field_value is None:
                return default
            
            # Handle numpy arrays
            if isinstance(field_value, np.ndarray):
                if field_value.size == 0:
                    return default
                # Convert to list and process
                field_list = field_value.tolist()
                for item in field_list:
                    if item is not None and str(item).strip():
                        return str(item)
                return default
            
            # Handle pandas Series (shouldn't happen but just in case)
            if hasattr(field_value, 'iloc'):
                if len(field_value) == 0:
                    return default
                for item in field_value:
                    if item is not None and str(item).strip():
                        return str(item)
                return default
            
            # Use pandas isna for scalar values
            if hasattr(pd, 'isna'):
                try:
                    if pd.isna(field_value):
                        return default
                except (ValueError, TypeError):
                    # If pd.isna fails, continue with other checks
                    pass
            
            # Handle regular lists
            if isinstance(field_value, list):
                if len(field_value) == 0:
                    return default
                # Get first non-null item
                for item in field_value:
                    if item is not None and str(item).strip():
                        return str(item)
                return default
            
            # Handle string values
            if isinstance(field_value, str):
                return field_value.strip() if field_value.strip() else default
            
            # Handle other types
            if field_value:
                return str(field_value)
            else:
                return default
                
        except Exception as e:
            print(f"⚠️ Warning in parse_list_field: {e}, returning default")
            return default

    def format_currency_list(fee_list):
        """Format citation fee list for display - handles numpy arrays"""
        try:
            # Handle None/NaN cases first
            if fee_list is None:
                return "$0.00"
            
            # Handle numpy arrays
            if isinstance(fee_list, np.ndarray):
                if fee_list.size == 0:
                    return "$0.00"
                fee_list = fee_list.tolist()
            
            # Handle pandas Series
            if hasattr(fee_list, 'iloc'):
                if len(fee_list) == 0:
                    return "$0.00"
                fee_list = fee_list.tolist()
            
            # Handle scalar values
            if not isinstance(fee_list, list):
                fee_list = [fee_list] if fee_list else []
            
            if len(fee_list) == 0:
                return "$0.00"
            
            total = 0
            for fee in fee_list:
                if fee and str(fee).replace('$', '').replace(',', '').replace('.', '').replace('-', '').isdigit():
                    try:
                        clean_fee = float(str(fee).replace('$', '').replace(',', ''))
                        total += clean_fee
                    except (ValueError, TypeError):
                        continue
            
            return f"${total:,.2f}" if total > 0 else "$0.00"
            
        except Exception as e:
            print(f"⚠️ Warning in format_currency_list: {e}, returning $0.00")
            return "$0.00"

    def safe_list_aggregation(series_of_lists):
        """Safely aggregate lists in a pandas series - handles numpy arrays"""
        try:
            total_count = 0
            for item in series_of_lists:
                if item is None:
                    continue
                    
                # Handle numpy arrays
                if isinstance(item, np.ndarray):
                    total_count += item.size
                # Handle regular lists
                elif isinstance(item, list):
                    total_count += len(item)
                # Handle scalar values
                else:
                    total_count += 1
                    
            return total_count
            
        except Exception as e:
            print(f"⚠️ Warning in safe_list_aggregation: {e}, returning 0")
            return 0

    def safe_fee_aggregation(series_of_fee_lists):
        """Safely aggregate fee lists - handles numpy arrays"""
        try:
            total = 0
            for fee_list in series_of_fee_lists:
                if fee_list is None:
                    continue
                
                # Handle numpy arrays
                if isinstance(fee_list, np.ndarray):
                    if fee_list.size == 0:
                        continue
                    fee_list = fee_list.tolist()
                
                # Handle scalar values
                if not isinstance(fee_list, list):
                    fee_list = [fee_list] if fee_list else []
                
                for fee in fee_list:
                    if fee and str(fee).replace('$', '').replace(',', '').replace('.', '').replace('-', '').isdigit():
                        try:
                            clean_fee = float(str(fee).replace('$', '').replace(',', ''))
                            total += clean_fee
                        except (ValueError, TypeError):
                            continue
                            
            return total
            
        except Exception as e:
            print(f"⚠️ Warning in safe_fee_aggregation: {e}, returning 0")
            return 0

    @monitor_performance("Compliance Data Table Filter Application")
    def apply_compliance_data_table_filters(base_data, query_selections):
        """
        Apply filters to base compliance data using pandas
        """
        if not query_selections:
            query_selections = {}
        
        # Filter the main case details dataframe
        filtered_data = {}
        
        for key, data in base_data.items():
            if isinstance(data, pd.DataFrame) and not data.empty:
                if key == "case_details" or key == "classified_cases":
                    # Apply compliance filters to case data
                    filtered_data[key] = apply_compliance_filters(data.copy(), query_selections)
                else:
                    # For event history and case flow, filter by matching case IDs
                    if "case_details" in filtered_data and not filtered_data["case_details"].empty:
                        case_ids = set(filtered_data["case_details"]['ID'].tolist())
                        if 'CaseID' in data.columns:
                            filtered_data[key] = data[data['CaseID'].isin(case_ids)].copy()
                        else:
                            filtered_data[key] = data.copy()
                    else:
                        filtered_data[key] = data.copy()
            else:
                filtered_data[key] = data
        
        return filtered_data

    @monitor_performance("Compliance Data Table Report Preparation")
    def prepare_compliance_data_table_report(filtered_data, report_type):
        """
        Prepare compliance data table based on selected report type
        """
        try:
            if report_type == "case_summary":
                df = filtered_data.get('case_details', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                # Select and format columns for case summary
                report_df = df.copy()
                
                # Parse list columns for display with improved error handling
                print(f"🔄 Processing {len(report_df)} rows for case_summary report")
                
                try:
                    report_df['FirstRuleNumber'] = report_df['RuleNumber'].apply(parse_list_field)
                    print("✅ Processed RuleNumber column")
                except Exception as e:
                    print(f"❌ Error processing RuleNumber: {e}")
                    report_df['FirstRuleNumber'] = "N/A"
                
                try:
                    report_df['FirstRuleTitle'] = report_df['RuleTitle'].apply(parse_list_field)
                    print("✅ Processed RuleTitle column")
                except Exception as e:
                    print(f"❌ Error processing RuleTitle: {e}")
                    report_df['FirstRuleTitle'] = "N/A"
                
                try:
                    report_df['FirstViolation'] = report_df['ViolationName'].apply(parse_list_field)
                    print("✅ Processed ViolationName column")
                except Exception as e:
                    print(f"❌ Error processing ViolationName: {e}")
                    report_df['FirstViolation'] = "N/A"
                
                try:
                    report_df['TotalCitationFee'] = report_df['CitationFee'].apply(format_currency_list)
                    print("✅ Processed CitationFee column")
                except Exception as e:
                    print(f"❌ Error processing CitationFee: {e}")
                    report_df['TotalCitationFee'] = "$0.00"
                
                # Format dates
                try:
                    report_df['CreatedDate'] = pd.to_datetime(report_df['CreatedOn'], errors='coerce').dt.strftime('%Y-%m-%d')
                    report_df['ClosedDate'] = pd.to_datetime(report_df['ClosedOn'], errors='coerce').dt.strftime('%Y-%m-%d')
                    print("✅ Processed date columns")
                except Exception as e:
                    print(f"❌ Error processing dates: {e}")
                    report_df['CreatedDate'] = "N/A"
                    report_df['ClosedDate'] = "N/A"
                
                # Select final columns with meaningful names
                final_columns = {
                    'CaseNumber': 'Case Number',
                    'MemberName': 'Member Name', 
                    'AssignedUser': 'Assigned User',
                    'Status': 'Status',
                    'Disposition': 'Disposition',
                    'FirstViolation': 'Primary Violation',
                    'FirstRuleNumber': 'Rule Number',
                    'ViolationCategory': 'Violation Category',
                    'TotalCitationFee': 'Citation Fee',
                    'CreatedDate': 'Created Date',
                    'ClosedDate': 'Closed Date'
                }
                
                # Select only existing columns
                available_columns = [col for col in final_columns.keys() if col in report_df.columns]
                report_df = report_df[available_columns].rename(columns={k: v for k, v in final_columns.items() if k in available_columns})
                
                print(f"✅ Generated case_summary report with {len(report_df)} rows and {len(report_df.columns)} columns")
                return report_df
                
            elif report_type == "violation_details":
                df = filtered_data.get('case_details', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                # Expand violation details - one row per violation
                expanded_rows = []
                
                print(f"🔄 Expanding violations for {len(df)} cases")
                
                for idx, row in df.iterrows():
                    try:
                        violations = row.get('ViolationName', [])
                        rule_numbers = row.get('RuleNumber', [])
                        rule_titles = row.get('RuleTitle', [])
                        citation_fees = row.get('CitationFee', [])
                        
                        # Handle numpy arrays and convert to lists
                        if isinstance(violations, np.ndarray):
                            violations = violations.tolist() if violations.size > 0 else []
                        elif not isinstance(violations, list):
                            violations = [violations] if violations else []
                            
                        if isinstance(rule_numbers, np.ndarray):
                            rule_numbers = rule_numbers.tolist() if rule_numbers.size > 0 else []
                        elif not isinstance(rule_numbers, list):
                            rule_numbers = [rule_numbers] if rule_numbers else []
                            
                        if isinstance(rule_titles, np.ndarray):
                            rule_titles = rule_titles.tolist() if rule_titles.size > 0 else []
                        elif not isinstance(rule_titles, list):
                            rule_titles = [rule_titles] if rule_titles else []
                            
                        if isinstance(citation_fees, np.ndarray):
                            citation_fees = citation_fees.tolist() if citation_fees.size > 0 else []
                        elif not isinstance(citation_fees, list):
                            citation_fees = [citation_fees] if citation_fees else []
                        
                        max_len = max(len(violations), len(rule_numbers), len(rule_titles), len(citation_fees), 1)
                        
                        for i in range(max_len):
                            violation = violations[i] if i < len(violations) and violations[i] else "N/A"
                            rule_num = rule_numbers[i] if i < len(rule_numbers) and rule_numbers[i] else "N/A"
                            rule_title = rule_titles[i] if i < len(rule_titles) and rule_titles[i] else "N/A"
                            citation_fee = citation_fees[i] if i < len(citation_fees) and citation_fees[i] else "$0.00"
                            
                            expanded_rows.append({
                                'Case Number': row.get('CaseNumber', 'N/A'),
                                'Member Name': row.get('MemberName', 'N/A'),
                                'Violation Name': violation,
                                'Rule Number': rule_num,
                                'Rule Title': rule_title,
                                'Citation Fee': citation_fee,
                                'Violation Category': row.get('ViolationCategory', 'N/A'),
                                'Detailed Rule Category': row.get('DetailedRuleCategory', 'N/A'),
                                'Status': row.get('Status', 'N/A'),
                                'Created Date': pd.to_datetime(row.get('CreatedOn'), errors='coerce').strftime('%Y-%m-%d') if pd.notna(row.get('CreatedOn')) else 'N/A'
                            })
                            
                    except Exception as e:
                        print(f"❌ Error processing row {idx}: {e}")
                        # Add minimal row to prevent complete failure
                        expanded_rows.append({
                            'Case Number': row.get('CaseNumber', 'N/A'),
                            'Member Name': row.get('MemberName', 'N/A'),
                            'Violation Name': 'Error processing',
                            'Rule Number': 'N/A',
                            'Rule Title': 'N/A',
                            'Citation Fee': '$0.00',
                            'Violation Category': 'N/A',
                            'Detailed Rule Category': 'N/A',
                            'Status': row.get('Status', 'N/A'),
                            'Created Date': 'N/A'
                        })
                
                result_df = pd.DataFrame(expanded_rows)
                print(f"✅ Generated violation_details report with {len(result_df)} rows")
                return result_df
                
            elif report_type == "member_violations":
                df = filtered_data.get('case_details', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                print(f"🔄 Aggregating member violations for {len(df)} cases")
                
                # Aggregate by member with improved error handling
                try:
                    member_summary = df.groupby('MemberName').agg({
                        'ID': 'count',  # Total cases
                        'ViolationName': lambda x: safe_list_aggregation(x),  # Total violations
                        'CitationFee': lambda x: safe_fee_aggregation(x),  # Total fees
                        'Status': lambda x: (x == 'Closed').sum(),  # Closed cases
                        'CreatedOn': lambda x: pd.to_datetime(x, errors='coerce').min(),  # First case
                        'ClosedOn': lambda x: pd.to_datetime(x, errors='coerce').max(),  # Last closed
                    }).reset_index()
                    
                    # Rename columns
                    member_summary.columns = ['Member Name', 'Total Cases', 'Total Violations', 'Total Citation Fees', 'Closed Cases', 'First Case Date', 'Last Closed Date']
                    
                    # Calculate resolution rate
                    member_summary['Resolution Rate %'] = (member_summary['Closed Cases'] / member_summary['Total Cases'] * 100).round(1)
                    
                    # Format currency
                    member_summary['Total Citation Fees'] = member_summary['Total Citation Fees'].apply(lambda x: f"${x:,.2f}")
                    
                    # Format dates
                    member_summary['First Case Date'] = member_summary['First Case Date'].dt.strftime('%Y-%m-%d')
                    member_summary['Last Closed Date'] = member_summary['Last Closed Date'].dt.strftime('%Y-%m-%d')
                    
                    # Sort by total violations descending
                    member_summary = member_summary.sort_values('Total Violations', ascending=False)
                    
                    print(f"✅ Generated member_violations report with {len(member_summary)} rows")
                    return member_summary
                    
                except Exception as e:
                    print(f"❌ Error in member aggregation: {e}")
                    return pd.DataFrame()
                
            # Continue with other report types using the same pattern...
            elif report_type == "office_violations":
                df = filtered_data.get('case_details', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                try:
                    office_summary = df.groupby('AssignedUser').agg({
                        'ID': 'count',
                        'MemberName': 'nunique',  # Unique members
                        'ViolationName': lambda x: safe_list_aggregation(x),
                        'Status': lambda x: (x == 'Closed').sum(),
                        'CitationFee': lambda x: safe_fee_aggregation(x)
                    }).reset_index()
                    
                    office_summary.columns = ['Office/Agent', 'Total Cases', 'Unique Members', 'Total Violations', 'Closed Cases', 'Total Citation Fees']
                    office_summary['Resolution Rate %'] = (office_summary['Closed Cases'] / office_summary['Total Cases'] * 100).round(1)
                    office_summary['Total Citation Fees'] = office_summary['Total Citation Fees'].apply(lambda x: f"${x:,.2f}")
                    
                    return office_summary.sort_values('Total Cases', ascending=False)
                    
                except Exception as e:
                    print(f"❌ Error in office aggregation: {e}")
                    return pd.DataFrame()
                
            elif report_type == "rule_violations":
                df = filtered_data.get('case_details', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                # Expand rule violations with improved error handling
                rule_rows = []
                
                for idx, row in df.iterrows():
                    try:
                        rule_numbers = row.get('RuleNumber', [])
                        rule_titles = row.get('RuleTitle', [])
                        
                        # Handle numpy arrays
                        if isinstance(rule_numbers, np.ndarray):
                            rule_numbers = rule_numbers.tolist() if rule_numbers.size > 0 else []
                        elif not isinstance(rule_numbers, list):
                            rule_numbers = [rule_numbers] if rule_numbers else []
                            
                        if isinstance(rule_titles, np.ndarray):
                            rule_titles = rule_titles.tolist() if rule_titles.size > 0 else []
                        elif not isinstance(rule_titles, list):
                            rule_titles = [rule_titles] if rule_titles else []
                        
                        for i, rule_num in enumerate(rule_numbers):
                            if rule_num:
                                rule_title = rule_titles[i] if i < len(rule_titles) else "N/A"
                                rule_rows.append({
                                    'Rule Number': rule_num,
                                    'Rule Title': rule_title,
                                    'Case Number': row.get('CaseNumber', 'N/A'),
                                    'Member Name': row.get('MemberName', 'N/A'),
                                    'Detailed Rule Category': row.get('DetailedRuleCategory', 'N/A'),
                                    'Status': row.get('Status', 'N/A'),
                                    'Created Date': pd.to_datetime(row.get('CreatedOn'), errors='coerce').strftime('%Y-%m-%d') if pd.notna(row.get('CreatedOn')) else 'N/A'
                                })
                                
                    except Exception as e:
                        print(f"❌ Error processing rule row {idx}: {e}")
                        continue
                
                rule_df = pd.DataFrame(rule_rows)
                
                if rule_df.empty:
                    return rule_df
                
                # Sort by rule number
                rule_df = rule_df.sort_values(['Rule Number', 'Created Date'])
                
                return rule_df
                
            elif report_type == "financial_summary":
                df = filtered_data.get('case_details', pd.DataFrame())
                if df.empty:
                    return pd.DataFrame()
                
                # Calculate financial metrics with improved error handling
                financial_rows = []
                
                for idx, row in df.iterrows():
                    try:
                        citation_fees = row.get('CitationFee', [])
                        fine_types = row.get('FineType', [])
                        
                        # Handle numpy arrays
                        if isinstance(citation_fees, np.ndarray):
                            citation_fees = citation_fees.tolist() if citation_fees.size > 0 else []
                        elif not isinstance(citation_fees, list):
                            citation_fees = [citation_fees] if citation_fees else []
                            
                        if isinstance(fine_types, np.ndarray):
                            fine_types = fine_types.tolist() if fine_types.size > 0 else []
                        elif not isinstance(fine_types, list):
                            fine_types = [fine_types] if fine_types else []
                        
                        total_fee = 0
                        for fee in citation_fees:
                            if fee and str(fee).replace('$', '').replace(',', '').replace('.', '').replace('-', '').isdigit():
                                try:
                                    total_fee += float(str(fee).replace('$', '').replace(',', ''))
                                except:
                                    continue
                        
                        fine_type = fine_types[0] if fine_types and fine_types[0] else "Standard"
                        
                        financial_rows.append({
                            'Case Number': row.get('CaseNumber', 'N/A'),
                            'Member Name': row.get('MemberName', 'N/A'),
                            'Citation Fee': f"${total_fee:.2f}",
                            'Fine Type': fine_type,
                            'Status': row.get('Status', 'N/A'),
                            'Disposition': row.get('Disposition', 'N/A'),
                            'Created Date': pd.to_datetime(row.get('CreatedOn'), errors='coerce').strftime('%Y-%m-%d') if pd.notna(row.get('CreatedOn')) else 'N/A'
                        })
                        
                    except Exception as e:
                        print(f"❌ Error processing financial row {idx}: {e}")
                        continue
                
                return pd.DataFrame(financial_rows).sort_values('Citation Fee', ascending=False)
                
            elif report_type == "activity_log":
                event_df = filtered_data.get('case_flow', pd.DataFrame())
                if event_df.empty:
                    return pd.DataFrame()
                
                try:
                    # Format activity log
                    activity_df = event_df.copy()
                    
                    # Select relevant columns
                    activity_columns = {
                        'CaseNumber': 'Case Number',
                        'ActionDate': 'Activity Date',
                        'EventSummary': 'Activity Summary', 
                        'LifecycleStage': 'Activity Type',
                        'MemberName': 'Member Name',
                        'AssignedUser': 'Assigned User',
                        'Status': 'Case Status'
                    }
                    
                    available_cols = [col for col in activity_columns.keys() if col in activity_df.columns]
                    activity_df = activity_df[available_cols].rename(columns={k: v for k, v in activity_columns.items() if k in available_cols})
                    
                    # Format date
                    if 'Activity Date' in activity_df.columns:
                        activity_df['Activity Date'] = pd.to_datetime(activity_df['Activity Date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
                    
                    # Sort by date descending
                    activity_df = activity_df.sort_values('Activity Date', ascending=False) if 'Activity Date' in activity_df.columns else activity_df
                    
                    return activity_df
                    
                except Exception as e:
                    print(f"❌ Error processing activity log: {e}")
                    return pd.DataFrame()
                
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Error preparing compliance data table report: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @callback(
        Output("compliance-data-table-container", "children"),
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-data-table-report-type-dropdown", "value"),
         Input("compliance-table-page-size-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Compliance Data Table Update")
    def update_compliance_data_table(query_selections, report_type, page_size):
        """
        Update compliance data table based on selections
        """
        try:
            print(f"🔄 Updating compliance data table: report={report_type}, page_size={page_size}")
            
            # Get base data
            base_data = get_compliance_data_table_base_data()
            
            if not base_data:
                return html.Div([
                    html.P("No compliance data available for the selected filters and report type.", 
                           className="text-muted text-center p-4")
                ])
            
            # Apply filters
            filtered_data = apply_compliance_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_compliance_data_table_report(filtered_data, report_type)
            
            if report_df.empty:
                return html.Div([
                    html.P("No data available for the selected filters and report type.", 
                           className="text-muted text-center p-4")
                ])
            
            # Create data table columns
            columns = []
            for col in report_df.columns:
                col_config = {
                    "name": col,
                    "id": col,
                    "deletable": False,
                    "selectable": False
                }
                
                # Format specific column types
                if col in ['Resolution Rate %']:
                    col_config.update({
                        "type": "numeric",
                        "format": {"specifier": ".1f"}
                    })
                elif col in ['Total Cases', 'Total Violations', 'Closed Cases', 'Unique Members']:
                    col_config.update({
                        "type": "numeric",
                        "format": {"specifier": ","}
                    })
                elif 'Date' in col:
                    col_config.update({
                        "type": "datetime"
                    })
                
                columns.append(col_config)
            
            # Create conditional styling
            style_data_conditional = [
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa'
                }
            ]
            
            # Add status-based styling for certain reports
            if report_type in ['case_summary', 'violation_details', 'financial_summary']:
                style_data_conditional.extend([
                    {
                        'if': {
                            'filter_query': '{Status} = Closed',
                            'column_id': 'Status'
                        },
                        'backgroundColor': '#d4edda',
                        'color': '#155724'
                    },
                    {
                        'if': {
                            'filter_query': '{Status} != Closed',
                            'column_id': 'Status'
                        },
                        'backgroundColor': '#f8d7da',
                        'color': '#721c24'
                    }
                ])
            
            # Create the data table
            data_table = dash_table.DataTable(
                id="compliance-data-table",
                columns=columns,
                data=report_df.to_dict('records'),
                page_size=page_size,
                sort_action="native",
                sort_mode="multi",
                filter_action="native",
                style_table={
                    'overflowX': 'auto',
                    'minWidth': '100%'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '12px',
                    'border': '1px solid #dee2e6'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'color': '#495057',
                    'border': '1px solid #dee2e6'
                },
                style_data_conditional=style_data_conditional,
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'background-color: grey; font-family: monospace; color: white'
                }],
                tooltip_data=[
                    {
                        column: {'value': str(value), 'type': 'markdown'}
                        for column, value in row.items()
                    } for row in report_df.to_dict('records')
                ],
                tooltip_duration=None
            )
            
            # Add summary information
            summary_info = html.Div([
                html.P([
                    html.Strong(f"Showing {len(report_df):,} records"),
                    f" • Report: {report_type.replace('_', ' ').title()}",
                    f" • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ], className="text-muted small mb-3")
            ])
            
            return html.Div([summary_info, data_table])
            
        except Exception as e:
            print(f"❌ Error updating compliance data table: {e}")
            import traceback
            traceback.print_exc()
            return html.Div([
                html.P(f"Error loading data table: {str(e)}", 
                       className="text-danger text-center p-4")
            ])

    @callback(
        Output("compliance-download-csv", "data"),
        Input("compliance-export-csv-btn", "n_clicks"),
        [State("compliance-filtered-query-store", "data"),
         State("compliance-data-table-report-type-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Compliance CSV Export")
    def export_compliance_csv(n_clicks, query_selections, report_type):
        """
        Export current compliance data table view as CSV
        """
        if not n_clicks:
            return no_update
        
        try:
            print(f"📥 Exporting Compliance CSV: report={report_type}")
            
            # Get base data
            base_data = get_compliance_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_compliance_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_compliance_data_table_report(filtered_data, report_type)
            
            if report_df.empty:
                return no_update
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"compliance_{report_type}_{timestamp}.csv"
            
            return dcc.send_data_frame(report_df.to_csv, filename, index=False)
            
        except Exception as e:
            print(f"❌ Error exporting compliance CSV: {e}")
            return no_update

    @callback(
        Output("compliance-download-excel", "data"),
        Input("compliance-export-excel-btn", "n_clicks"),
        [State("compliance-filtered-query-store", "data"),
         State("compliance-data-table-report-type-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Compliance Excel Export")
    def export_compliance_excel(n_clicks, query_selections, report_type):
        """
        Export current compliance data table view as Excel
        """
        if not n_clicks:
            return no_update
        
        try:
            print(f"📥 Exporting Compliance Excel: report={report_type}")
            
            # Get base data
            base_data = get_compliance_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_compliance_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_compliance_data_table_report(filtered_data, report_type)
            
            if report_df.empty:
                print("❌ No data to export")
                return no_update
            
            print(f"✅ Preparing Excel export with {len(report_df)} records")
            
            # Create Excel file using BytesIO buffer
            import io
            try:
                # Try using openpyxl engine first
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    sheet_name = report_type.replace('_', ' ').title()[:31]  # Excel sheet name limit
                    report_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                buffer.seek(0)
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"compliance_{report_type}_{timestamp}.xlsx"
                
                print(f"✅ Excel file created successfully: {filename}")
                
                return dcc.send_bytes(
                    buffer.getvalue(),
                    filename=filename
                )
                
            except ImportError:
                print("⚠️ openpyxl not available, trying xlsxwriter")
                # Fallback to xlsxwriter
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    sheet_name = report_type.replace('_', ' ').title()[:31]
                    report_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                buffer.seek(0)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"compliance_{report_type}_{timestamp}.xlsx"
                
                return dcc.send_bytes(
                    buffer.getvalue(),
                    filename=filename
                )
                
        except Exception as e:
            print(f"❌ Error exporting compliance Excel: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: If Excel fails, export as CSV with .xlsx extension
            try:
                print("⚠️ Falling back to CSV export with Excel extension")
                base_data = get_compliance_data_table_base_data()
                filtered_data = apply_compliance_data_table_filters(base_data, query_selections)
                report_df = prepare_compliance_data_table_report(filtered_data, report_type)
                
                if not report_df.empty:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"compliance_{report_type}_{timestamp}_fallback.csv"
                    return dcc.send_data_frame(report_df.to_csv, filename, index=False)
                    
            except Exception as fallback_error:
                print(f"❌ Fallback export also failed: {fallback_error}")
            
            return no_update

    @callback(
        Output("compliance-download-pdf", "data"),
        Input("compliance-export-pdf-btn", "n_clicks"),
        [State("compliance-filtered-query-store", "data"),
         State("compliance-data-table-report-type-dropdown", "value")],
        prevent_initial_call=True
    )
    @monitor_performance("Compliance PDF Export")
    def export_compliance_pdf(n_clicks, query_selections, report_type):
        """
        Export current compliance data table view as a nicely formatted PDF
        """
        if not n_clicks:
            return no_update
        
        try:
            print(f"📄 Exporting Compliance PDF: report={report_type}")
            
            # Get base data
            base_data = get_compliance_data_table_base_data()
            
            # Apply filters
            filtered_data = apply_compliance_data_table_filters(base_data, query_selections)
            
            # Prepare report data
            report_df = prepare_compliance_data_table_report(filtered_data, report_type)
            
            if report_df.empty:
                print("❌ No data to export")
                return no_update
            
            print(f"✅ Preparing PDF export with {len(report_df)} records")
            
            # Create PDF buffer
            buffer = io.BytesIO()
            
            # Determine page orientation based on number of columns
            if len(report_df.columns) > 6:
                page_size = landscape(A4)
                page_width = landscape(A4)[0]
            else:
                page_size = A4
                page_width = A4[0]
            
            # Create PDF document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=page_size,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=1*inch,
                bottomMargin=0.5*inch
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.black,
                alignment=TA_CENTER,
                spaceAfter=0.3*inch
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=0.2*inch
            )
            
            # Create text styles for table cells with proper wrapping
            cell_text_style = ParagraphStyle(
                'CellText',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.black,
                alignment=TA_LEFT,
                leading=10,
                leftIndent=2,
                rightIndent=2,
                spaceAfter=2,
                wordWrap='LTR'
            )
            
            cell_numeric_style = ParagraphStyle(
                'CellNumeric',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.black,
                alignment=TA_RIGHT,
                leading=10,
                leftIndent=2,
                rightIndent=2,
                spaceAfter=2
            )
            
            cell_center_style = ParagraphStyle(
                'CellCenter',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.black,
                alignment=TA_CENTER,
                leading=10,
                leftIndent=2,
                rightIndent=2,
                spaceAfter=2
            )
            
            header_style = ParagraphStyle(
                'HeaderText',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.whitesmoke,
                alignment=TA_CENTER,
                leading=11,
                fontName='Helvetica-Bold',
                leftIndent=2,
                rightIndent=2
            )
            
            # Create content elements
            elements = []
            
            # Title
            report_title = report_type.replace('_', ' ').title()
            title = Paragraph(f"Compliance Report: {report_title}", title_style)
            elements.append(title)
            
            # Subtitle with metadata
            current_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            subtitle = Paragraph(f"Generated on {current_time} • {len(report_df):,} records", subtitle_style)
            elements.append(subtitle)
            
            # Add some space
            elements.append(Spacer(1, 0.2*inch))
            
            # Calculate column widths
            headers = list(report_df.columns)
            num_cols = len(headers)
            available_width = page_width - 1*inch
            
            def calculate_column_widths(df, headers, available_width):
                """Calculate column widths based on content length and type"""
                min_width = 1.0*inch
                max_width = 3.0*inch
                
                column_weights = {}
                
                for col in headers:
                    # Get sample of data for analysis (first 20 rows)
                    sample_data = df[col].head(20).astype(str)
                    
                    # Calculate average character length
                    avg_length = sample_data.str.len().mean()
                    max_length = sample_data.str.len().max()
                    header_length = len(col)
                    
                    # Determine column type and appropriate width
                    if any(keyword in col.lower() for keyword in ['number', 'id', 'fee', 'rate', 'count']):
                        # Numeric columns need less space
                        weight = min(1.5*inch, max(min_width, header_length * 0.12*inch))
                    elif any(keyword in col.lower() for keyword in ['name', 'title', 'description', 'summary']):
                        # Text columns need more space
                        weight = min(max_width, max(1.8*inch, avg_length * 0.05*inch))
                    elif any(keyword in col.lower() for keyword in ['date', 'time']):
                        # Date columns need medium space
                        weight = min(1.8*inch, max(1.3*inch, header_length * 0.1*inch))
                    elif col.lower() in ['status', 'type', 'category']:
                        # Short categorical columns
                        weight = min(1.5*inch, max(min_width, max(avg_length * 0.08*inch, header_length * 0.1*inch)))
                    else:
                        # Default sizing
                        weight = min(max_width, max(min_width, avg_length * 0.05*inch))
                    
                    column_weights[col] = weight
                
                # Normalize weights to fit available width
                total_weight = sum(column_weights.values())
                if total_weight > available_width:
                    # Scale down proportionally
                    scale_factor = available_width / total_weight
                    column_weights = {col: weight * scale_factor for col, weight in column_weights.items()}
                elif total_weight < available_width:
                    # Distribute extra space proportionally
                    extra_space = available_width - total_weight
                    for col in column_weights:
                        column_weights[col] += extra_space / num_cols
                
                return [column_weights[col] for col in headers]
            
            # Calculate intelligent column widths
            col_widths = calculate_column_widths(report_df, headers, available_width)
            
            # Prepare table data with Paragraph objects for text wrapping
            table_data = []
            
            # Add headers with Paragraph objects
            header_row = []
            for header in headers:
                header_paragraph = Paragraph(str(header), header_style)
                header_row.append(header_paragraph)
            table_data.append(header_row)
            
            # Add data rows with Paragraph objects for automatic wrapping
            max_rows = 100
            for i, row in report_df.head(max_rows).iterrows():
                row_data = []
                for col_idx, val in enumerate(row):
                    col_name = headers[col_idx]
                    
                    if pd.isna(val):
                        cell_content = ""
                        cell_paragraph = Paragraph(cell_content, cell_text_style)
                    elif isinstance(val, (int, float)):
                        if isinstance(val, float) and val == int(val):
                            cell_content = str(int(val))
                        else:
                            cell_content = str(val)
                        # Use numeric style for numbers
                        cell_paragraph = Paragraph(cell_content, cell_numeric_style)
                    else:
                        # Clean the text for PDF
                        text = str(val).strip()
                        
                        # Clean up text for PDF (escape special characters)
                        text = text.replace('&', '&amp;')
                        text = text.replace('<', '&lt;')
                        text = text.replace('>', '&gt;')
                        text = text.replace('"', '&quot;')
                        text = text.replace("'", '&#39;')
                        
                        # Determine appropriate style based on column type
                        if any(keyword in col_name.lower() for keyword in ['rate', 'count', 'fee', '%']):
                            cell_paragraph = Paragraph(text, cell_numeric_style)
                        elif any(keyword in col_name.lower() for keyword in ['date', 'time']):
                            cell_paragraph = Paragraph(text, cell_center_style)
                        else:
                            cell_paragraph = Paragraph(text, cell_text_style)
                    
                    row_data.append(cell_paragraph)
                
                table_data.append(row_data)
            
            # Create table with calculated widths and automatic row heights
            table = Table(
                table_data,
                colWidths=col_widths,
                repeatRows=1,
                splitByRow=True
            )
            
            # Apply table styling
            table_style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                
                # Data rows styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                
                # Generous padding for text wrapping
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                
                # Vertical alignment for wrapped text
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                
                # Grid lines for better readability
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
                ('LINEBEFORE', (0, 0), (0, -1), 2, colors.black),
                ('LINEAFTER', (-1, 0), (-1, -1), 2, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ])
            
            table.setStyle(table_style)
            elements.append(table)
            
            # Add footer note if data was truncated
            if len(report_df) > max_rows:
                footer_style = ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=TA_CENTER
                )
                elements.append(Spacer(1, 0.2*inch))
                footer_text = f"Note: Showing first {max_rows} records of {len(report_df):,} total records. Use Excel export for complete data."
                footer = Paragraph(footer_text, footer_style)
                elements.append(footer)
            
            # Add note about text wrapping
            wrap_note_style = ParagraphStyle(
                'WrapNote',
                parent=styles['Normal'],
                fontSize=7,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=0.1*inch
            )
            elements.append(Spacer(1, 0.1*inch))
            wrap_note = Paragraph("All text content is preserved with automatic wrapping for readability.", wrap_note_style)
            elements.append(wrap_note)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"compliance_{report_type}_{timestamp}.pdf"
            
            print(f"✅ PDF file created successfully: {filename}")
            
            return dcc.send_bytes(
                buffer.getvalue(),
                filename=filename
            )
            
        except Exception as e:
            print(f"❌ Error exporting compliance PDF: {e}")
            import traceback
            traceback.print_exc()
            return no_update

print("✅ Compliance data table callbacks registered")