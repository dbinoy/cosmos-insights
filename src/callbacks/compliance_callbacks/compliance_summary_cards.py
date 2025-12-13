from dash import callback, Input, Output
import pandas as pd
import json
from datetime import datetime, timedelta
from src.utils.db import run_queries
from functools import reduce, lru_cache
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

# Global cache for processed compliance data
_compliance_data_cache = {}
_cache_timestamp = None
_cache_duration_minutes = 60  # Cache for 60 minutes

def register_compliance_summary_cards_callbacks(app):
    """Register compliance summary cards callbacks"""
    
    @lru_cache(maxsize=1)
    def get_compliance_case_data():
        """
        Fetch and merge compliance case data with caching of processed result
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
            print(f"❌ Error fetching compliance case data: {e}")
            return pd.DataFrame()
    
    def invalidate_compliance_cache():
        """Manually invalidate the cache if needed"""
        global _compliance_data_cache, _cache_timestamp
        _compliance_data_cache = {}
        _cache_timestamp = None
        get_compliance_case_data.cache_clear()
        # print("🗑️ Compliance data cache invalidated")

    def apply_date_filters(df, date_from, date_to):
        """Apply date range filters to the dataframe"""
        if df.empty:
            return df
            
        # Filter by CreatedOn date within the specified range
        if 'CreatedOn' in df.columns:
            df = df[
                (df['CreatedOn'] >= pd.to_datetime(date_from)) &
                (df['CreatedOn'] <= pd.to_datetime(date_to))
            ]
        
        return df
    
    def apply_compliance_filters(df, filter_selections):
        """Apply compliance-specific filters"""
        if df.empty:
            return df
        
        filtered_df = df.copy()
        
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
    
    def calculate_summary_metrics(df):
        """Calculate all summary metrics"""
        if df.empty:
            return {
                'total_cases': 0,
                'open_cases': 0,
                'avg_resolution_days': 0,
                'total_citations': 0,
                'high_risk_members': 0,
                'top_agent': 'N/A'
            }
        
        # Total Cases
        total_cases = len(df)
        
        # Open Cases (Status != 'Closed')
        open_cases = len(df[df['Status'] != 'Closed']) if 'Status' in df.columns else 0
        
        # Average Resolution Time (for closed cases)
        avg_resolution_days = 0
        if 'CreatedOn' in df.columns and 'ClosedOn' in df.columns:
            closed_cases = df[
                (df['Status'] == 'Closed') & 
                df['ClosedOn'].notna() & 
                df['CreatedOn'].notna()
            ].copy()
            
            if not closed_cases.empty:
                closed_cases['resolution_days'] = (closed_cases['ClosedOn'] - closed_cases['CreatedOn']).dt.days
                avg_resolution_days = closed_cases['resolution_days'].mean()
        
        # Total Citations (cases containing "Citation" in ViolationName)
        total_citations = 0
        if 'ViolationName' in df.columns:
            citation_cases = df[df['ViolationName'].apply(
                lambda x: any("Citation" in str(item) for item in x) 
                if isinstance(x, list) and x else False
            )]
            total_citations = len(citation_cases)
        
        # High-Risk Members (members with 10+ cases)
        high_risk_members = 0
        if 'MemberName' in df.columns:
            member_case_counts = df.groupby('MemberName').size()
            high_risk_members = len(member_case_counts[member_case_counts > 10])
        
        # Top Agent (agent with highest case load)
        top_agent = 'N/A'
        if 'AssignedUser' in df.columns:
            agent_case_counts = df.groupby('AssignedUser').size()
            if not agent_case_counts.empty:
                top_agent_name = agent_case_counts.idxmax()
                top_agent_count = agent_case_counts.max()
                # Format as "Name (count)"
                top_agent = f"{top_agent_name} ({top_agent_count})"
        
        return {
            'total_cases': total_cases,
            'open_cases': open_cases,
            'avg_resolution_days': avg_resolution_days,
            'total_citations': total_citations,
            'high_risk_members': high_risk_members,
            'top_agent': top_agent
        }
       
    # Show spinners when filters change
    @app.callback(
        [Output("compliance-total-cases-spinner", "style", allow_duplicate=True),
         Output("compliance-open-cases-spinner", "style", allow_duplicate=True),
         Output("compliance-avg-resolution-spinner", "style", allow_duplicate=True),
         Output("compliance-total-citations-spinner", "style", allow_duplicate=True),
         Output("compliance-high-risk-members-spinner", "style", allow_duplicate=True),
         Output("compliance-top-agent-spinner", "style", allow_duplicate=True)],
        [Input("compliance-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    def show_compliance_summary_card_spinners(stored_selections):
        """Show summary cards spinner when filter selections change"""
        spinner_style = {"position": "absolute", "top": "10px", "right": "10px", "visibility": "visible"}
        return tuple([spinner_style] * 6)

    @callback(
        [Output("compliance-total-cases-value", "children"),
         Output("compliance-open-cases-value", "children"),
         Output("compliance-avg-resolution-value", "children"),
         Output("compliance-total-citations-value", "children"),
         Output("compliance-high-risk-members-value", "children"),
         Output("compliance-top-agent-value", "children"),
         Output("compliance-total-cases-spinner", "style"),
         Output("compliance-open-cases-spinner", "style"),
         Output("compliance-avg-resolution-spinner", "style"),
         Output("compliance-total-citations-spinner", "style"),
         Output("compliance-high-risk-members-spinner", "style"),
         Output("compliance-top-agent-spinner", "style")],
        Input("compliance-filtered-query-store", "data"),
        prevent_initial_call=False
    )
    @monitor_performance("Compliance Summary Cards Update")
    def update_summary_cards(filter_selections):
        """Update all compliance summary cards based on current filter selections"""
        
        # Default values and hidden spinner style
        hidden_spinner = {"position": "absolute", "top": "10px", "right": "10px", "visibility": "hidden"}
        
        try:
            # Get filter selections or use defaults
            if not filter_selections:
                filter_selections = {}
                
            date_from = filter_selections.get('Day_From', (datetime.now() - timedelta(days=365)).date())
            date_to = filter_selections.get('Day_To', datetime.now().date())
            
            # Fetch compliance case data
            df = get_compliance_case_data()
            
            if df.empty:
                return ("0", "0", "0d", "0", "0", "N/A") + tuple([hidden_spinner] * 6)
            
            # Apply compliance filters to current period
            current_df = apply_date_filters(df, date_from, date_to)
            current_df = apply_compliance_filters(current_df, filter_selections)
            
            # Calculate current metrics
            current_metrics = calculate_summary_metrics(current_df)
            
            return (
                # Total Cases
                f"{current_metrics['total_cases']:,}",
                
                # Open Cases  
                f"{current_metrics['open_cases']:,}",
                
                # Average Resolution Time
                f"{current_metrics['avg_resolution_days']:.1f}d" if current_metrics['avg_resolution_days'] > 0 else "N/A",
                
                # Total Citations
                f"{current_metrics['total_citations']:,}",
                
                # High-Risk Members
                f"{current_metrics['high_risk_members']:,}",
                
                # Top Agent
                current_metrics['top_agent'],

                # Hide all spinners after successful update
            ) + tuple([hidden_spinner] * 6)
            
        except Exception as e:
            print(f"❌ Error updating compliance summary cards: {e}")
            import traceback
            traceback.print_exc()
            return (["Error"] * 6) + [hidden_spinner] * 6
    
    # Expose cache invalidation function for manual cache clearing if needed
    app.compliance_cache_invalidate = invalidate_compliance_cache    
    # print("✅ Compliance summary cards callbacks registered")