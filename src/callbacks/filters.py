from dash.dependencies import Input, Output, State
import pandas as pd
import textwrap
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    @app.callback(
        Output("training-filter-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_filter_data(_):
        q_aors ='SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
        q_offices = 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]'
        q_classes = 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]'
        q_topics = 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]'
        q_instructors = 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]'
        q_locations = 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]'

        queries = {
            "aors": q_aors,
            "offices": q_offices,
            "classes": q_classes,
            "topics": q_topics,
            "instructors": q_instructors,
            "locations": q_locations
        }           

        results = run_queries(queries, len(queries.keys()))
        filter_data = {
            "aors": results["aors"].to_dict("records"),
            "offices": results["offices"].to_dict("records"),
            "classes": results["classes"].to_dict("records"),
            "topics": results["topics"].to_dict("records"),
            "instructors": results["instructors"].to_dict("records"),
            "locations": results["locations"].to_dict("records")
        }     
        return filter_data   
    
    @app.callback(
        Output("training-date-range-picker", "start_date_placeholder_text"),
        Output("training-date-range-picker", "end_date_placeholder_text"),
        Output("training-aor-dropdown", "options"),
        Output("training-topics-dropdown", "options"),
        Output("training-instructor-dropdown", "options"),
        Output("training-location-dropdown", "options"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_filters(filter_data):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()        

        if not filter_data:
            return str(start_placeholder), str(end_placeholder), []
        
        df_aors = pd.DataFrame(filter_data["aors"])
        aor_options = [{"label": "All Aors", "value": "All"}]+[{"label": v[1]['AorShortName']+' - '+v[1]['AorName'], "value": str(v[1]['AorShortName'])} for v in df_aors.iterrows() if pd.notnull(v)]

        df_topics = pd.DataFrame(filter_data["topics"])
        topic_options = [{"label": "All Topics", "value": "All"}]+[{"label": v[1]['TopicName'], "value": str(v[1]['TopicId'])} for v in df_topics.iterrows() if pd.notnull(v)]

        df_instructors = pd.DataFrame(filter_data["instructors"])
        instructor_options = [{"label": "All Instructors", "value": "All"}]+[{"label": v[1]['Name'], "value": str(v[1]['InstructorID'])} for v in df_instructors.iterrows() if pd.notnull(v)]

        df_locations = pd.DataFrame(filter_data["locations"])
        location_options = [{"label": "All Locations", "value": "All"}]+[{"label": v[1]['Name'], "value": str(v[1]['LocationID'])} for v in df_locations.iterrows() if pd.notnull(v)]

        return str(start_placeholder), str(end_placeholder), aor_options, topic_options, instructor_options, location_options
        
    @app.callback(
        Output("training-office-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-filter-data-store", "data"),    
        prevent_initial_call=True
    )
    def populate_office_filter(selected_aors, filter_data):
        if not filter_data:
            return []
        
        df_offices = pd.DataFrame(filter_data["offices"])
        if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
            df_offices = df_offices[df_offices["AorShortName"].isin([aor for aor in selected_aors])]
            selected_aors = ' ' + ','.join(selected_aors) + ' '
        else:
            selected_aors = ' '

        office_options = [{"label": f"All{selected_aors}Offices", "value": "All"}]+[{"label": v[1]['AorShortName']+' - '+v[1]['OfficeCode'], "value": v[1]['OfficeCode']} for v in df_offices.iterrows() if pd.notnull(v)]
        return office_options      

    @app.callback(
        Output("training-class-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-topics-dropdown", "value"),        
        Input("training-filter-data-store", "data"),    
        prevent_initial_call=True
    )
    def populate_class_filter(selected_aors, selected_instructors, selected_locations, selected_topics, filter_data):
        if not filter_data:
            return []
        
        df_topics = pd.DataFrame(filter_data["topics"])
        df_classes = pd.DataFrame(filter_data["classes"])

        if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
            df_classes = df_classes[df_classes["AorShortName"].isin([aor for aor in selected_aors])]    

        if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
            df_classes = df_classes[df_classes["InstructorId"].isin([instr for instr in selected_instructors])]

        if selected_locations and len(selected_locations) != 0 and "All" not in selected_locations:
            df_classes = df_classes[df_classes["LocationId"].isin([loc for loc in selected_locations])]

        if selected_topics and len(selected_topics) != 0 and "All" not in selected_topics:
            df_classes = df_classes[df_classes["TopicId"].isin([topic for topic in selected_topics])]
            selected_topic_labels = df_topics[df_topics["TopicId"].isin([topic for topic in selected_topics])]['TopicName'].values.tolist()
            selected_topics = ' ' + ','.join([str(topic) for topic in selected_topic_labels]) + ' '
        else:
            selected_topics = ' '

        if len(df_classes) > 0:
            class_options = [{"label": f"All{selected_topics}Classes", "value": "All"}]+[{"label": textwrap.shorten(v[1]['ClassName'], width=72, placeholder='')+': '+v[1]['StartTime'], "value": v[1]['ClassId']} for v in df_classes.iterrows() if pd.notnull(v)]
        else:
            class_options = []

        return class_options           