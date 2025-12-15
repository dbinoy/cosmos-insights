import pandas as pd
import json
from datetime import datetime, timedelta
from src.utils.db import run_queries
from functools import reduce, lru_cache
from src.utils.performance import monitor_performance

# Global cache for processed compliance data
_compliance_data_cache = {}
_cache_timestamp = None
_cache_duration_minutes = 60  # Cache for 60 minutes

@lru_cache(maxsize=1)
def get_compliance_base_data():
    """
    Fetch and merge compliance case data with global caching
    This is shared across all compliance callbacks for consistency
    """
    global _compliance_data_cache, _cache_timestamp

    try:
        # Check if we have valid cached data
        current_time = datetime.now()
        if (_cache_timestamp and 
            _compliance_data_cache and 
            (current_time - _cache_timestamp).seconds < _cache_duration_minutes * 60):
            # print(f"🎯 Using cached processed compliance data (age: {(current_time - _cache_timestamp).seconds}s)")
            return _compliance_data_cache['merged_df']
        
        # print("📊 Processing fresh compliance case data...")
        
        # Fetch all required tables (these queries are still cached by run_queries)
        queries = {
            "case_details": "SELECT * FROM [consumable].[Fact_CaseDetails]",
            "case_events": "SELECT * FROM [consumable].[Fact_CaseEvents]", 
            "case_notes": "SELECT * FROM [consumable].[Fact_CaseNotes]",
            "case_notices": "SELECT * FROM [consumable].[Fact_CaseNotices]"
        }
        
        result = run_queries(queries, 'compliance', 5)
        
        # Parse JSON columns in Fact_CaseDetails
        case_details_df = result["case_details"].copy()
        
        if 'ViolationName' in case_details_df.columns:
            case_details_df['ViolationName'] = case_details_df['ViolationName'].apply(json.loads)
        if 'ViolationDescription' in case_details_df.columns:
            case_details_df['ViolationDescription'] = case_details_df['ViolationDescription'].apply(json.loads)
        if 'RuleNumber' in case_details_df.columns:
            case_details_df['RuleNumber'] = case_details_df['RuleNumber'].apply(json.loads)
        if 'RuleTitle' in case_details_df.columns:
            case_details_df['RuleTitle'] = case_details_df['RuleTitle'].apply(json.loads)
        if 'CitationFee' in case_details_df.columns:
            case_details_df['CitationFee'] = case_details_df['CitationFee'].apply(json.loads)
        if 'FineType' in case_details_df.columns:
            case_details_df['FineType'] = case_details_df['FineType'].apply(json.loads)
        if 'ReportIds' in case_details_df.columns:
            case_details_df['ReportIds'] = case_details_df['ReportIds'].apply(lambda x: json.loads(x) if pd.notna(x) else [])
            case_details_df.insert(case_details_df.columns.get_loc('ReportIds') + 1, 'NumReportIds', case_details_df['ReportIds'].apply(len))
        
        # Parse JSON columns in other tables
        case_notes_df = result["case_notes"].copy()
        if 'Notes' in case_notes_df.columns:
            case_notes_df['Notes'] = case_notes_df['Notes'].apply(json.loads)
            case_notes_df['NumNotes'] = case_notes_df['Notes'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        case_notices_df = result["case_notices"].copy()
        if 'CaseNotices' in case_notices_df.columns:
            case_notices_df['CaseNotices'] = case_notices_df['CaseNotices'].apply(json.loads)
            case_notices_df['NumCaseNotices'] = case_notices_df['CaseNotices'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        # Group case events by ID
        case_events_df = result["case_events"].copy()
        if not case_events_df.empty:
            grouped_case_events_df = (
                case_events_df
                .drop(columns=['ID'])
                .groupby(case_events_df['ID'])
                .apply(lambda g: g.to_dict(orient='records'))
                .reset_index(name='CaseEvents')
            )
            grouped_case_events_df['NumCaseEvents'] = grouped_case_events_df['CaseEvents'].apply(len)
        else:
            grouped_case_events_df = pd.DataFrame(columns=['ID', 'CaseEvents', 'NumCaseEvents'])
        
        # Merge all dataframes
        dfs = [case_details_df, grouped_case_events_df, case_notices_df, case_notes_df]
        merged_df = reduce(lambda left, right: pd.merge(left, right, on='ID', how='left'), dfs)
        
        # Fill missing values
        list_columns = ['Notes', 'CaseNotices', 'CaseEvents']
        for col in list_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].apply(lambda x: x if isinstance(x, list) else [])
        
        numeric_columns = ['NumNotes', 'NumCaseNotices', 'NumCaseEvents']
        for col in numeric_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].fillna(0).astype(int)
        
        # Convert date columns
        date_columns = ['CreatedOn', 'ClosedOn']
        for col in date_columns:
            if col in merged_df.columns:
                merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce')
        
        # Cache the processed result
        _compliance_data_cache['merged_df'] = merged_df
        _cache_timestamp = current_time
        
        # print(f"✅ Processed and cached {len(merged_df)} compliance cases")
        return merged_df
        
    except Exception as e:
        print(f"❌ Error fetching compliance base data: {e}")
        return pd.DataFrame()

def invalidate_compliance_cache():
    """Manually invalidate the cache if needed"""
    global _compliance_data_cache, _cache_timestamp
    _compliance_data_cache = {}
    _cache_timestamp = None
    get_compliance_base_data.cache_clear()
    # print("🗑️ Compliance data cache invalidated")

@monitor_performance("Compliance Filter Application")
def apply_compliance_filters(df, filter_selections):
    """Apply compliance-specific filters - standardized across all callbacks"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply date filter
    if filter_selections.get('Day_From') and filter_selections.get('Day_To'):
        date_from = pd.to_datetime(filter_selections['Day_From'])
        date_to = pd.to_datetime(filter_selections['Day_To'])
        if 'CreatedOn' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['CreatedOn'] >= date_from) &
                (filtered_df['CreatedOn'] <= date_to)
            ]
    
    # Apply Disposition filter
    if filter_selections.get('Disposition'):
        disposition_list = [d.strip().strip("'") for d in filter_selections['Disposition'].split(',')]
        filtered_df = filtered_df[filtered_df['Disposition'].isin(disposition_list)]
    
    # Apply AssignedUser filter
    if filter_selections.get('AssignedUser'):
        user_list = [u.strip().strip("'") for u in filter_selections['AssignedUser'].split(',')]
        filtered_df = filtered_df[filtered_df['AssignedUser'].isin(user_list)]
    
    # Apply ViolationName filter (list column)
    if filter_selections.get('ViolationName'):
        violation_list = [v.strip().strip("'") for v in filter_selections['ViolationName'].split(',')]
        filtered_df = filtered_df[filtered_df['ViolationName'].apply(
            lambda x: any(item in violation_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply RuleNumber filter (list column)
    if filter_selections.get('RuleNumber'):
        rule_list = [r.strip().strip("'") for r in filter_selections['RuleNumber'].split(',')]
        filtered_df = filtered_df[filtered_df['RuleNumber'].apply(
            lambda x: any(item in rule_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply RuleTitle filter (list column)
    if filter_selections.get('RuleTitle'):
        title_list = [t.strip().strip("'") for t in filter_selections['RuleTitle'].split(',')]
        filtered_df = filtered_df[filtered_df['RuleTitle'].apply(
            lambda x: any(item in title_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply CitationFee filter (list column)
    if filter_selections.get('CitationFee'):
        fee_list = [f.strip().strip("'") for f in filter_selections['CitationFee'].split(',')]
        filtered_df = filtered_df[filtered_df['CitationFee'].apply(
            lambda x: any(item in fee_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply FineType filter (list column)
    if filter_selections.get('FineType'):
        type_list = [t.strip().strip("'") for t in filter_selections['FineType'].split(',')]
        filtered_df = filtered_df[filtered_df['FineType'].apply(
            lambda x: any(item in type_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply NumReports filter
    if filter_selections.get('NumReports'):
        num_list = [int(n.strip()) for n in filter_selections['NumReports'].split(',')]
        filtered_df = filtered_df[filtered_df['NumReportIds'].isin(num_list)]
    
    return filtered_df

@monitor_performance("Outstanding Issues Classification")
def classify_case_severity(df):
    """
    Classify compliance cases by severity level based on violation types and additional factors
    
    Returns DataFrame with additional columns:
    - BaseSeverity: Base severity from violation type
    - FinalSeverity: Final severity after applying multipliers
    - SeverityReason: Reason for severity classification
    - IsOutstanding: Boolean indicating if case is outstanding (unresolved)
    """
    if df.empty:
        return df
    
    df_classified = df.copy()
    
    def get_base_severity_from_violations(violation_list):
        """Classify base severity from violation types"""
        if not isinstance(violation_list, list) or len(violation_list) == 0:
            return "RESOLVED", "No violations"
        
        # Get first non-null violation
        violation = None
        for v in violation_list:
            if v is not None and str(v).strip():
                violation = v
                break
        
        if not violation:
            return "DATA_ISSUE", "Null violation data"
        
        # CRITICAL - Immediate Action Required
        if violation in ['Citation', 'Citation: Unresolved', 'Combined Citation', 
                        'Disciplinary Complaint', 'Disciplinary Complaint Upheld']:
            return "CRITICAL", f"Active enforcement: {violation}"
        
        # HIGH - Urgent (Within 7 Days)
        elif violation in ['Investigation Created', 'Escalated', 'Warning', 'Violation Override']:
            return "HIGH", f"Investigation/escalation: {violation}"
        
        # MEDIUM - Standard Priority (Within 30 Days) 
        elif violation in ['AOR/MLS Referral', 'Transferred to OM/DB', 'Modification']:
            return "MEDIUM", f"Administrative action: {violation}"
        
        # LOW - Routine (Standard Timeline)
        elif violation in ['Call', 'Chat', 'Left Voicemail']:
            return "LOW", f"Communication activity: {violation}"
        
        # RESOLVED/CLOSED - No Action Required
        elif violation in ['Corrected', 'Corrected Prior to Review', 'Citation - Dismissed by review panel',
                          'Disciplinary Complaint Dismissed', 'No Violation', 'Duplicate', 
                          'Aged Report', 'Unable to Verify', 'Withdrawn']:
            return "RESOLVED", f"Case resolved: {violation}"
        
        # DATA ISSUES
        elif violation in ['Null', None, ''] or str(violation).strip() == '':
            return "DATA_ISSUE", "Missing violation data"
        
        else:
            return "MEDIUM", f"Other violation: {violation}"
    
    def apply_severity_multipliers(base_severity, row):
        """Apply multipliers based on case characteristics"""
        severity_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        level_names = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
        
        if base_severity in ["RESOLVED", "DATA_ISSUE"]:
            return base_severity, []
        
        current_level = severity_levels.get(base_severity, 2)
        multipliers_applied = []
        
        # Unassigned cases: +1 severity level
        if pd.isna(row.get('AssignedUser')) or str(row.get('AssignedUser', '')).strip() == '':
            current_level = min(current_level + 1, 4)
            multipliers_applied.append("Unassigned (+1)")
        
        # Age factor: Cases open > 10 days get +1 severity level
        if 'CreatedOn' in row and pd.notna(row['CreatedOn']):
            try:
                created_date = pd.to_datetime(row['CreatedOn'])
                days_open = (pd.Timestamp.now() - created_date).days
                if days_open > 10:
                    current_level = min(current_level + 1, 4)
                    multipliers_applied.append(f"Aging {days_open} days (+1)")
            except:
                pass
        
        final_severity = level_names.get(current_level, base_severity)
        return final_severity, multipliers_applied
    
    def is_case_outstanding(row):
        """Determine if case is outstanding (unresolved)"""
        # Check disposition first
        disposition = row.get('Disposition', '')
        if disposition and str(disposition).lower() in ['closed', 'resolved', 'complete']:
            return False
        
        # Check status
        status = row.get('Status', '')
        if status and str(status).lower() in ['closed', 'resolved', 'complete']:
            return False
        
        # Check violation types for resolved cases
        violation_list = row.get('ViolationName', [])
        if isinstance(violation_list, list) and len(violation_list) > 0:
            first_violation = violation_list[0] if violation_list[0] is not None else None
            if first_violation in ['Corrected', 'Corrected Prior to Review', 'Citation - Dismissed by review panel',
                                 'Disciplinary Complaint Dismissed', 'No Violation', 'Duplicate', 
                                 'Aged Report', 'Unable to Verify', 'Withdrawn']:
                return False
        
        # If none of the above, consider it outstanding
        return True
    
    # Apply classifications
    severity_data = df_classified.apply(
        lambda row: get_base_severity_from_violations(row.get('ViolationName', [])), axis=1
    )
    
    df_classified['BaseSeverity'] = [s[0] for s in severity_data]
    df_classified['BaseSeverityReason'] = [s[1] for s in severity_data]
    
    # Apply multipliers
    final_severity_data = df_classified.apply(
        lambda row: apply_severity_multipliers(row['BaseSeverity'], row), axis=1
    )
    
    df_classified['FinalSeverity'] = [s[0] for s in final_severity_data]
    df_classified['SeverityMultipliers'] = [s[1] for s in final_severity_data]
    
    # Create comprehensive severity reason
    df_classified['SeverityReason'] = df_classified.apply(
        lambda row: f"{row['BaseSeverityReason']}" + 
                   (f" | Multipliers: {', '.join(row['SeverityMultipliers'])}" if row['SeverityMultipliers'] else ""), 
        axis=1
    )
    
    # Determine outstanding status
    df_classified['IsOutstanding'] = df_classified.apply(is_case_outstanding, axis=1)
    
    # Calculate days open
    df_classified['DaysOpen'] = df_classified.apply(
        lambda row: (pd.Timestamp.now() - pd.to_datetime(row['CreatedOn'])).days 
        if pd.notna(row.get('CreatedOn')) else 0, axis=1
    )
    
    return df_classified

@monitor_performance("Outstanding Issues Data Preparation")
def prepare_outstanding_issues_data(df, view_state="severity"):
    """
    Prepare outstanding issues data based on view state
    Only includes cases that are truly outstanding (unresolved)
    """
    if df.empty:
        return pd.DataFrame(), {}
    
    # First classify all cases
    classified_df = classify_case_severity(df)
    
    # Filter to only outstanding cases
    outstanding_df = classified_df[classified_df['IsOutstanding'] == True].copy()
    
    if outstanding_df.empty:
        return pd.DataFrame(), {'total_cases': 0, 'outstanding_cases': 0}
    
    # Prepare data based on view state
    if view_state == "severity":
        # Group by final severity level
        status_counts = outstanding_df['FinalSeverity'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Ensure proper ordering (CRITICAL -> HIGH -> MEDIUM -> LOW -> DATA_ISSUE)
        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'DATA_ISSUE']
        status_counts['SortOrder'] = status_counts['Category'].map(
            {sev: i for i, sev in enumerate(severity_order)}
        ).fillna(99)
        status_counts = status_counts.sort_values('SortOrder').drop('SortOrder', axis=1).reset_index(drop=True)
        
    elif view_state == "age":
        # Group by age buckets
        def categorize_age(days):
            if days <= 7:
                return "≤7 days (Fresh)"
            elif days <= 30:
                return "8-30 days (Recent)"
            elif days <= 90:
                return "31-90 days (Aging)"
            else:
                return ">90 days (Stale)"
        
        outstanding_df['AgeCategory'] = outstanding_df['DaysOpen'].apply(categorize_age)
        status_counts = outstanding_df['AgeCategory'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Sort by age order
        age_order = ["≤7 days (Fresh)", "8-30 days (Recent)", "31-90 days (Aging)", ">90 days (Stale)"]
        status_counts['SortOrder'] = status_counts['Category'].map(
            {age: i for i, age in enumerate(age_order)}
        ).fillna(99)
        status_counts = status_counts.sort_values('SortOrder').drop('SortOrder', axis=1).reset_index(drop=True)
        
    elif view_state == "assignment":
        # Group by assignment status
        def categorize_assignment(assigned_user):
            if pd.isna(assigned_user) or str(assigned_user).strip() == '':
                return "🚨 Unassigned"
            else:
                return f"👤 {str(assigned_user).strip()}"
        
        outstanding_df['AssignmentCategory'] = outstanding_df['AssignedUser'].apply(categorize_assignment)
        status_counts = outstanding_df['AssignmentCategory'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Sort with unassigned first (highest priority)
        status_counts['IsUnassigned'] = status_counts['Category'].str.contains('🚨 Unassigned')
        status_counts = status_counts.sort_values(['IsUnassigned', 'Count'], ascending=[False, False]).drop('IsUnassigned', axis=1).reset_index(drop=True)
        
    elif view_state == "violation":
        # Group by violation type (first violation)
        def get_first_violation(violation_list):
            if isinstance(violation_list, list) and len(violation_list) > 0:
                return violation_list[0] if violation_list[0] is not None else "No Violation"
            return "No Violation"
        
        outstanding_df['FirstViolation'] = outstanding_df['ViolationName'].apply(get_first_violation)
        status_counts = outstanding_df['FirstViolation'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Sort by count descending
        status_counts = status_counts.sort_values('Count', ascending=False).reset_index(drop=True)
    
    # Calculate summary stats
    total_cases = len(df)
    outstanding_cases = len(outstanding_df)
    
    # Severity breakdown
    severity_breakdown = outstanding_df['FinalSeverity'].value_counts().to_dict()
    
    # Assignment stats
    unassigned_count = len(outstanding_df[
        outstanding_df['AssignedUser'].isna() | 
        (outstanding_df['AssignedUser'].astype(str).str.strip() == '')
    ])
    
    # Age stats
    aging_count = len(outstanding_df[outstanding_df['DaysOpen'] > 30])
    stale_count = len(outstanding_df[outstanding_df['DaysOpen'] > 90])
    
    summary_stats = {
        'total_cases': total_cases,
        'outstanding_cases': outstanding_cases,
        'outstanding_percentage': (outstanding_cases / total_cases * 100) if total_cases > 0 else 0,
        'critical_cases': severity_breakdown.get('CRITICAL', 0),
        'high_cases': severity_breakdown.get('HIGH', 0),
        'unassigned_cases': unassigned_count,
        'aging_cases': aging_count,
        'stale_cases': stale_count,
        'avg_days_open': outstanding_df['DaysOpen'].mean() if not outstanding_df.empty else 0
    }
    
    return status_counts, summary_stats
