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
            print(f"🎯 Using cached processed compliance data (age: {(current_time - _cache_timestamp).seconds}s)")
            return _compliance_data_cache['merged_df']
        
        print("📊 Processing fresh compliance case data...")
        
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
        
        print(f"✅ Processed and cached {len(merged_df)} compliance cases")
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
    print("🗑️ Compliance data cache invalidated")

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