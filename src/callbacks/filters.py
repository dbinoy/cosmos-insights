from dash.dependencies import Input, Output, State
import pandas as pd
import textwrap
import time
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    print("Registering training filter callbacks")
    start = time.time()
    @app.callback(
        Output("training-filter-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_filter_data(_):
        q_aors ='SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
        q_offices = 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]'
        # q_classes = 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]'
        q_topics = 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]'
        q_instructors = 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]'
        q_locations = 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]'
        # q_request_stats = 'SELECT [TrainingTopicId],[TrainingTopicName],[AorShortName],[AorName],[MemberOffice],[MembersRequested],[TotalRequests] FROM [consumable].[Fact_RequestStats]'
        # q_attendance_stats = 'SELECT [TrainingClassId],[ClassName],[TrainingTopicId],[TrainingTopicName],[LocationId],[LocationName],[InstructorId],[InstructorName],[AorShortName],[MemberOffice],[MembersAttended],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]'


        queries = {
            "aors": q_aors,
            "offices": q_offices,
            # "classes": q_classes,
            "topics": q_topics,
            "instructors": q_instructors,
            "locations": q_locations,
            # "request_stats": q_request_stats,
            # "attendance_stats": q_attendance_stats
        }           

        results = run_queries(queries, len(queries.keys()))
        filter_data = {
            "aors": results["aors"].to_dict("records"),
            "offices": results["offices"].to_dict("records"),
            # "classes": results["classes"].to_dict("records"),
            "topics": results["topics"].to_dict("records"),
            "instructors": results["instructors"].to_dict("records"),
            "locations": results["locations"].to_dict("records"),
            # "request_stats": results["request_stats"].to_dict("records"),
            # "attendance_stats": results["attendance_stats"].to_dict("records")
        }    
        print("Data Load done in", time.time()-start, "s")
        return filter_data   
    
    @app.callback(
        Output("training-date-range-picker", "start_date_placeholder_text"),
        Output("training-date-range-picker", "end_date_placeholder_text"),
        Output("training-aor-dropdown", "options"),
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

        return str(start_placeholder), str(end_placeholder), aor_options
    print("Training filter callback registration complete")

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
        Output("training-topics-dropdown", "options"),
        # Input("training-aor-dropdown", "value"),
        # Input("training-office-dropdown", "value"),  
        Input("training-filter-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_topics_filter(filter_data):
        if not filter_data:
            return []
        
        df_topics = pd.DataFrame(filter_data["topics"])
        # df_request_stats = pd.DataFrame(filter_data["request_stats"])
        # df_attendance_stats = pd.DataFrame(filter_data["attendance_stats"])

        # filtered = False
        
        # if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
        #     filtered = True
        #     df_request_stats = df_request_stats[df_request_stats["AorShortName"].isin([aor for aor in selected_aors])] 
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin([aor for aor in selected_aors])] 

        # if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
        #     filtered = True
        #     df_request_stats = df_request_stats[df_request_stats["MemberOffice"].isin([office for office in selected_offices])]      
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin([office for office in selected_offices])]                          

        # if filtered == True:
        #     topic_ids_from_request_stats = df_request_stats["TrainingTopicId"].unique().tolist()
        #     topic_ids_from_attendance_stats = df_attendance_stats["TrainingTopicId"].unique().tolist()
        #     topic_ids = list(set(topic_ids_from_request_stats).union(set(topic_ids_from_attendance_stats)))
        #     df_topics = df_topics[df_topics["TopicId"].isin(topic_ids)]

        topic_options = [{"label": "All Topics", "value": "All"}]+[{"label": v[1]['TopicName'], "value": str(v[1]['TopicId'])} for v in df_topics.iterrows() if pd.notnull(v)]

        return topic_options

    @app.callback(
        Output("training-instructor-dropdown", "options"),
        # Input("training-aor-dropdown", "value"),
        # Input("training-office-dropdown", "value"),  
        Input("training-filter-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_instructor_filter(filter_data):
        if not filter_data:
            return []
        
        df_instructors = pd.DataFrame(filter_data["instructors"])
        # df_attendance_stats = pd.DataFrame(filter_data["attendance_stats"])

        # filtered = False
        
        # if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
        #     filtered = True
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin([aor for aor in selected_aors])] 

        # if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
        #     filtered = True
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin([office for office in selected_offices])]                

        # if filtered == True:
        #     instructor_ids = df_attendance_stats["InstructorId"].unique().tolist()
        #     df_instructors = df_instructors[df_instructors["InstructorID"].isin(instructor_ids)]

        instructor_options = [{"label": "All Instructors", "value": "All"}]+[{"label": v[1]['Name'], "value": str(v[1]['InstructorID'])} for v in df_instructors.iterrows() if pd.notnull(v)]
        return instructor_options
          
    @app.callback(
        Output("training-location-dropdown", "options"),
        # Input("training-aor-dropdown", "value"),
        # Input("training-office-dropdown", "value"),  
        # Input("training-topics-dropdown", "value"), 
        # Input("training-instructor-dropdown", "value"), 
        Input("training-filter-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_location_filter(filter_data):
        if not filter_data:
            return []
        
        df_locations = pd.DataFrame(filter_data["locations"])        
        # df_attendance_stats = pd.DataFrame(filter_data["attendance_stats"])

        # filtered = False
        
        # if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
        #     filtered = True
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin([aor for aor in selected_aors])] 

        # if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
        #     filtered = True
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin([office for office in selected_offices])]     

        # if selected_topics and len(selected_topics) != 0 and "All" not in selected_topics:
        #     filtered = True
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["TrainingTopicId"].isin([topic for topic in selected_topics])]

        # if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
        #     filtered = True
        #     df_attendance_stats = df_attendance_stats[df_attendance_stats["InstructorId"].isin([instr for instr in selected_instructors])]           

        # if filtered == True:
        #     location_ids = df_attendance_stats["LocationId"].unique().tolist()
        #     df_locations = df_locations[df_locations["LocationID"].isin(location_ids)]

        location_options = [{"label": "All Locations", "value": "All"}]+[{"label": v[1]['Name'], "value": str(v[1]['LocationID'])} for v in df_locations.iterrows() if pd.notnull(v)]
        return location_options
    
    '''      
    @app.callback(
        Output("training-class-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-topics-dropdown", "value"),        
        Input("training-filter-data-store", "data"),    
        prevent_initial_call=True
    )
    def populate_class_filter(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics, filter_data):
        if not filter_data:
            return []
        
        df_topics = pd.DataFrame(filter_data["topics"])
        df_classes = pd.DataFrame(filter_data["classes"])
        df_attendance_stats = pd.DataFrame(filter_data["attendance_stats"])
        filtered = False

        if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
            filtered = True
            df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin([aor for aor in selected_aors])] 
            df_classes = df_classes[df_classes["AorShortName"].isin([aor for aor in selected_aors])] 

        if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
            filtered = True
            df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin([office for office in selected_offices])]     
               
        if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
            filtered = True
            df_attendance_stats = df_attendance_stats[df_attendance_stats["InstructorId"].isin([instr for instr in selected_instructors])]                       
            df_classes = df_classes[df_classes["InstructorId"].isin([instr for instr in selected_instructors])]

        if selected_locations and len(selected_locations) != 0 and "All" not in selected_locations:
            filtered = True
            df_attendance_stats = df_attendance_stats[df_attendance_stats["LocationId"].isin([loc for loc in selected_locations])]
            df_classes = df_classes[df_classes["LocationId"].isin([loc for loc in selected_locations])]

        if filtered == True:
            class_ids = df_attendance_stats["TrainingClassId"].unique().tolist()
            df_classes = df_classes[df_classes["ClassId"].isin(class_ids)]

        if selected_topics and len(selected_topics) != 0 and "All" not in selected_topics:
            df_classes = df_classes[df_classes["TopicId"].isin([topic for topic in selected_topics])]
            selected_topic_labels = df_topics[df_topics["TopicId"].isin([topic for topic in selected_topics])]['TopicName'].values.tolist()
            selected_topics = ' ' + ','.join([str(topic) for topic in selected_topic_labels]) + ' '
        else:
            selected_topics = ' '

        all_classes_label = f"All{selected_topics}Classes"
        if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
            all_classes_label = f"{all_classes_label} For {','.join(selected_aors)}"
        if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
            all_classes_label = f"{all_classes_label} By {','.join(df_classes[df_classes['InstructorId'].isin([instr for instr in selected_instructors])]['InstructorName'].unique().tolist())}"
        if selected_locations and len(selected_locations) != 0 and "All" not in selected_locations:
            all_classes_label = f"{all_classes_label} At {','.join(df_classes[df_classes['LocationId'].isin([loc for loc in selected_locations])]['LocationName'].unique().tolist())}"
        if len(df_classes) > 0:
            class_options = [{"label": f"{all_classes_label}", "value": "All"}]+[{"label": v[1]['ClassName']+': '+v[1]['StartTime'], "value": v[1]['ClassId']} for v in df_classes.iterrows() if pd.notnull(v)]
        else:
            class_options = []

        return class_options           
    
    @app.callback(
        Output("training-date-range-picker", "start_date"),
        Output("training-date-range-picker", "end_date"),
        Output("training-aor-dropdown", "value"),
        Output("training-office-dropdown", "value"),
        Output("training-topics-dropdown", "value"),
        Output("training-instructor-dropdown", "value"),
        Output("training-location-dropdown", "value"),
        Output("training-class-dropdown", "value"),
        Input("training-clear-filters-btn", "n_clicks"),
        Input("training-filter-data-store", "data"),    
        prevent_initial_call=True,
        allow_duplicate=True
    )
    def clear_all_filters(n_clicks, filter_data):
        aor__default = []
        office_default = []
        topics_default = []
        instructor_default = []
        location_default = []
        class_default = []
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()  
        return date_start_default, date_end_default, aor__default, office_default, topics_default, instructor_default, location_default, class_default
    '''    
    
