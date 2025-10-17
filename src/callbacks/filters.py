from dash.dependencies import Input, Output, State
import pandas as pd
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    @app.callback(
        Output("training-filter-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_filter_data(_):
        q_aors ='SELECT [AorID], [Name], [ShortName] FROM [consumable].[Dim_Aors] ORDER BY [ShortName]'
        q_members ='SELECT [MemberID], [MemberName], [OfficeCode] FROM [consumable].[Dim_Members]'

        queries = {
            "aors": q_aors,
            "members": q_members
        }           

        results = run_queries(queries, len(queries.keys()))
        filter_data = {
            "aors": results["aors"].to_dict("records"),
            "members": results["members"].to_dict("records")
        }     
        return filter_data   
    
    @app.callback(
        Output("training-date-range-picker", "start_date_placeholder_text"),
        Output("training-date-range-picker", "end_date_placeholder_text"),
        Output("training-aor-dropdown", "options"),
        Output("training-office-dropdown", "options"),
        # Output("training-member-dropdown", "options"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_filters(filter_data):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()        
        if not filter_data:
            return str(start_placeholder), str(end_placeholder), [], [], []
        df_aors = pd.DataFrame(filter_data["aors"])
        aor_options = [{"label": "All Aors", "value": "All"}]+[{"label": v[1]['ShortName']+' - '+v[1]['Name'], "value": str(v[1]['AorID'])} for v in df_aors.iterrows() if pd.notnull(v)]
        print(df_aors.shape)
        df_members = pd.DataFrame(filter_data["members"])
        print(sorted(list(df_members['OfficeCode'].dropna().unique())))
        office_options = [{"label": "All Offices", "value": "All"}]+[{"label": v, "value": v} for v in sorted(list(df_members['OfficeCode'].dropna().unique()))]
        print("Building member options")
        member_options = [{"label": "All Members", "value": "All"}]+[{"label": v[1]['MemberName'], "value": str(v[1]['MemberID'])} for v in df_members.iterrows() if pd.notnull(v)]
        print(len(member_options))
        return str(start_placeholder), str(end_placeholder), aor_options, office_options    