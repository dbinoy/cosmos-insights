from dash import callback, Input, Output
import pandas as pd
from datetime import datetime, timedelta
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters
from src.utils.performance import monitor_performance


def register_compliance_summary_cards_callbacks(app):
    """Register compliance summary cards callbacks"""
    
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
            df = get_compliance_base_data()
            
            if df.empty:
                return ("0", "0", "0d", "0", "0", "N/A") + tuple([hidden_spinner] * 6)
            
            # Apply compliance filters 
            filtered_df = apply_compliance_filters(df, filter_selections)

            # Calculate current metrics
            summary_metrics = calculate_summary_metrics(filtered_df)

            return (
                # Total Cases
                f"{summary_metrics['total_cases']:,}",
                
                # Open Cases  
                f"{summary_metrics['open_cases']:,}",
                
                # Average Resolution Time
                f"{summary_metrics['avg_resolution_days']:.1f}d" if summary_metrics['avg_resolution_days'] > 0 else "N/A",
                
                # Total Citations
                f"{summary_metrics['total_citations']:,}",
                
                # High-Risk Members
                f"{summary_metrics['high_risk_members']:,}",
                
                # Top Agent
                summary_metrics['top_agent'],

                # Hide all spinners after successful update
            ) + tuple([hidden_spinner] * 6)
            
        except Exception as e:
            print(f"❌ Error updating compliance summary cards: {e}")
            import traceback
            traceback.print_exc()
            return (["Error"] * 6) + [hidden_spinner] * 6

    # print("✅ Compliance summary cards callbacks registered")