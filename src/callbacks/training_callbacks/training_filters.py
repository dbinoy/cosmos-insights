from dash import callback, Input, Output
import pandas as pd
from datetime import datetime
from src.utils.db import run_queries
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

def register_training_filter_callbacks(app):
    """
    Register optimized training filter callbacks
    Fetch queries individually as needed - no large data store
    """

    # ✅ Individual query functions for optimal caching
    def get_aors_data():
        """Fetch AORs data - cached independently"""
        query = 'SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
        result = run_queries({"aors": query}, 1)
        return result["aors"]

    def get_offices_data():
        """Fetch offices data - cached independently"""
        query = 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]'
        result = run_queries({"offices": query}, 1)
        return result["offices"]

    def get_topics_data():
        """Fetch topics data - cached independently"""
        query = 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]'
        result = run_queries({"topics": query}, 1)
        return result["topics"]

    def get_instructors_data():
        """Fetch instructors data - cached independently"""
        query = 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]'
        result = run_queries({"instructors": query}, 1)
        return result["instructors"]

    def get_locations_data():
        """Fetch locations data - cached independently"""
        query = 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]'
        result = run_queries({"locations": query}, 1)
        return result["locations"]

    def get_classes_data():
        """Fetch classes data - cached independently"""
        query = 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]'
        result = run_queries({"classes": query}, 1)
        return result["classes"]

    def get_request_stats_data():
        """Fetch request stats for filtering - cached independently"""
        query = 'SELECT [TrainingTopicId],[TrainingTopicName],[AorShortName],[AorName],[MemberOffice],[MembersRequested],[TotalRequests] FROM [consumable].[Fact_RequestStats]'
        result = run_queries({"request_stats": query}, 1)
        return result["request_stats"]

    def get_attendance_stats_data():
        """Fetch attendance stats for filtering - cached independently"""
        query = 'SELECT [TrainingClassId],[ClassName],[TrainingTopicId],[TrainingTopicName],[LocationId],[LocationName],[InstructorId],[InstructorName],[AorShortName],[MemberOffice],[MembersAttended],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]'
        result = run_queries({"attendance_stats": query}, 1)
        return result["attendance_stats"]

    # ✅ Initial filters - fetch only AORs data
    @callback(
        [Output("training-date-range-picker", "start_date_placeholder_text"),
         Output("training-date-range-picker", "end_date_placeholder_text"),
         Output("training-aor-dropdown", "options"),
         Output("training-aor-dropdown", "placeholder"),
         Output("training-aor-spinner", "style")],     
        Input("training-filtered-query-store", "id"),  # Simple trigger
        prevent_initial_call=False
    )
    # @monitor_performance("Training AOR Dropdown Population")
    def populate_initial_filters(_):
        """
        Populate initial filters - only fetches AOR data
        """
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        
        try:
            # ✅ Fetch only AORs data - small, cached query
            df_aors = get_aors_data()
            aor_options = [{"label": "All Aors", "value": "All"}] + [
                {"label": f"{row['AorShortName']} - {row['AorName']}", "value": str(row['AorShortName'])}
                for _, row in df_aors.iterrows() if pd.notnull(row['AorShortName'])
            ]
            
            # print(f"📊 AOR options loaded: {len(aor_options)} options")
            return (
                str(start_placeholder), 
                str(end_placeholder), 
                aor_options,
                "Select AORs...",  # ✅ Updated placeholder
                {'display': 'none'}  # ✅ Hide spinner (empty content)
            )
            
        except Exception as e:
            print(f"❌ Error loading AOR options: {e}")
            return (
                str(start_placeholder), 
                str(end_placeholder), 
                [],
                "Error loading AORs",
                {"visibility": "hidden"}  # ✅ Hide spinner even on error
            )

    # Show office spinner when AOR changes
    @callback(
        [Output("training-office-spinner", "style", allow_duplicate=True),
         Output("training-office-dropdown", "placeholder", allow_duplicate=True)],
        Input("training-aor-dropdown", "value"),
        prevent_initial_call=True
    )
    def show_office_spinner(selected_aors):
        """Show office spinner when AOR selection changes"""
        return (
            {"visibility": "block", "position": "relative", "top": "-30px", "right": "-30px"},  # ✅ Show spinner
            "Re-Loading offices..."        # ✅ Loading placeholder
        )

    # ✅ Office dropdown - fetch offices + apply AOR filter
    @callback(
        [Output("training-office-dropdown", "options"),
         Output("training-office-dropdown", "placeholder"),
         Output("training-office-spinner", "style")], 
        Input("training-aor-dropdown", "value"),
        prevent_initial_call=False
    )
    # @monitor_performance("Training Office Dropdown Population")
    def populate_office_filter(selected_aors):
        """
        Populate office dropdown based on selected AORs
        Fetches only offices data when needed
        """
        try:
            # ✅ Fetch only offices data - small, cached query
            df_offices = get_offices_data()
            
            if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
                df_offices = df_offices[df_offices["AorShortName"].isin(selected_aors)]
                selected_aors_label = ' ' + ','.join(selected_aors) + ' '
            else:
                selected_aors_label = ' '

            office_options = [{"label": f"All{selected_aors_label}Offices", "value": "All"}] + [
                {"label": f"{row['AorShortName']} - {row['OfficeCode']}", "value": row['OfficeCode']}
                for _, row in df_offices.iterrows() if pd.notnull(row['OfficeCode'])
            ]
            
            return (
                office_options,
                "Select Offices...",
                {"visibility": "hidden"}  
            )
            
        except Exception as e:
            print(f"❌ Error loading office options: {e}")
            return (
                [],
                "Error loading Offices",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )
    # Show topics/instructors spinners when AOR or Office changes
    @callback(
        [Output("training-topics-spinner", "style", allow_duplicate=True),
         Output("training-topics-dropdown", "placeholder", allow_duplicate=True),
         Output("training-instructor-spinner", "style", allow_duplicate=True),
         Output("training-instructor-dropdown", "placeholder", allow_duplicate=True)],
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value")],
        prevent_initial_call=True
    )
    def show_topics_instructors_spinners(selected_aors, selected_offices):
        """Show topics and instructors spinners when AOR/Office selection changes"""
        return (
            {"visibility": "block", "position": "relative", "top": "-30px", "right": "-30px"},   # ✅ Show topics spinner
            "Re-Loading topics...",         # ✅ Loading placeholder
            {"visibility": "block", "position": "relative", "top": "-30px", "right": "-30px"},   # ✅ Show instructors spinner
            "Re-Loading instructors..."     # ✅ Loading placeholder
        )        

    # ✅ Topics dropdown - fetch topics + request/attendance stats for filtering
    @callback(
        [Output("training-topics-dropdown", "options"),
         Output("training-topics-dropdown", "placeholder"),
         Output("training-topics-spinner", "style")],
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value")],
        prevent_initial_call=False
    )
    # @monitor_performance("Training Topics Dropdown Population")
    def populate_topics_filter(selected_aors, selected_offices):
        """
        Populate topics dropdown based on AOR/Office selections
        Fetches topics + stats data when needed
        """
        try:
            # ✅ Fetch only required data - cached queries
            df_topics = get_topics_data()
            
            # Only fetch stats if filtering is needed
            filtered = False
            if (selected_aors and len(selected_aors) != 0 and "All" not in selected_aors) or \
               (selected_offices and len(selected_offices) != 0 and "All" not in selected_offices):
                filtered = True
                
                # Fetch stats for filtering
                df_request_stats = get_request_stats_data()
                df_attendance_stats = get_attendance_stats_data()
                
                if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
                    df_request_stats = df_request_stats[df_request_stats["AorShortName"].isin(selected_aors)]
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin(selected_aors)]

                if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
                    df_request_stats = df_request_stats[df_request_stats["MemberOffice"].isin(selected_offices)]
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin(selected_offices)]

                # Get available topic IDs from filtered stats
                topic_ids_from_requests = df_request_stats["TrainingTopicId"].unique().tolist()
                topic_ids_from_attendance = df_attendance_stats["TrainingTopicId"].unique().tolist()
                topic_ids = list(set(topic_ids_from_requests).union(set(topic_ids_from_attendance)))
                df_topics = df_topics[df_topics["TopicId"].isin(topic_ids)]

            topic_options = [{"label": "All Topics", "value": "All"}] + [
                {"label": row['TopicName'], "value": str(row['TopicId'])}
                for _, row in df_topics.iterrows() if pd.notnull(row['TopicName'])
            ]
            
            # print(f"📊 Topic options loaded: {len(topic_options)} options (filtered: {filtered})")
            return (
                topic_options,
                "Select Topics...",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )
            
        except Exception as e:
            print(f"❌ Error loading topic options: {e}")
            return (
                [],
                "Error loading Topics",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )

    # ✅ Instructors dropdown - fetch instructors + attendance stats for filtering
    @callback(
        [Output("training-instructor-dropdown", "options"),
         Output("training-instructor-dropdown", "placeholder"),
         Output("training-instructor-spinner", "style")],
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value")],
        prevent_initial_call=False
    )
    # @monitor_performance("Training Instructors Dropdown Population")
    def populate_instructor_filter(selected_aors, selected_offices):
        """
        Populate instructors dropdown based on AOR/Office selections
        """
        try:
            # ✅ Fetch only required data
            df_instructors = get_instructors_data()
            
            filtered = False
            if (selected_aors and len(selected_aors) != 0 and "All" not in selected_aors) or \
               (selected_offices and len(selected_offices) != 0 and "All" not in selected_offices):
                filtered = True
                
                # Fetch attendance stats for filtering
                df_attendance_stats = get_attendance_stats_data()
                
                if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin(selected_aors)]

                if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin(selected_offices)]

                # Filter instructors by available instructor IDs
                instructor_ids = df_attendance_stats["InstructorId"].unique().tolist()
                df_instructors = df_instructors[df_instructors["InstructorID"].isin(instructor_ids)]

            instructor_options = [{"label": "All Instructors", "value": "All"}] + [
                {"label": row['Name'], "value": str(row['InstructorID'])}
                for _, row in df_instructors.iterrows() if pd.notnull(row['Name'])
            ]
            
            # print(f"📊 Instructor options loaded: {len(instructor_options)} options (filtered: {filtered})")
            return (
                instructor_options,
                "Select Instructors...",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )
            
        except Exception as e:
            print(f"❌ Error loading instructor options: {e}")
            return (
                [],
                "Error loading Instructors",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )

    # Show locations spinner when filters change
    @callback(
        [Output("training-location-spinner", "style", allow_duplicate=True),
         Output("training-location-dropdown", "placeholder", allow_duplicate=True)],
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value"),
         Input("training-topics-dropdown", "value"),
         Input("training-instructor-dropdown", "value")],
        prevent_initial_call=True
    )
    def show_location_spinner(selected_aors, selected_offices, selected_topics, selected_instructors):
        """Show location spinner when dependent filters change"""
        return (
            {"visibility": "block", "position": "relative", "top": "-30px", "right": "-30px"},   # ✅ Show spinner
            "Re-Loading locations..."       # ✅ Loading placeholder
        )
    
    # ✅ Locations dropdown - fetch locations + attendance stats for filtering
    @callback(
        [Output("training-location-dropdown", "options"),
         Output("training-location-dropdown", "placeholder"),
         Output("training-location-spinner", "style")],
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value"),
         Input("training-topics-dropdown", "value"),
         Input("training-instructor-dropdown", "value")],
        prevent_initial_call=False
    )
    # @monitor_performance("Training Locations Dropdown Population")
    def populate_location_filter(selected_aors, selected_offices, selected_topics, selected_instructors):
        """
        Populate locations dropdown based on filter selections
        """
        try:
            # ✅ Fetch only required data
            df_locations = get_locations_data()
            
            filtered = False
            if any([
                selected_aors and len(selected_aors) != 0 and "All" not in selected_aors,
                selected_offices and len(selected_offices) != 0 and "All" not in selected_offices,
                selected_topics and len(selected_topics) != 0 and "All" not in selected_topics,
                selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors
            ]):
                filtered = True
                
                # Fetch attendance stats for filtering
                df_attendance_stats = get_attendance_stats_data()
                
                if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin(selected_aors)]

                if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin(selected_offices)]

                if selected_topics and len(selected_topics) != 0 and "All" not in selected_topics:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["TrainingTopicId"].isin(selected_topics)]

                if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["InstructorId"].isin(selected_instructors)]

                # Filter locations by available location IDs
                location_ids = df_attendance_stats["LocationId"].unique().tolist()
                df_locations = df_locations[df_locations["LocationID"].isin(location_ids)]

            location_options = [{"label": "All Locations", "value": "All"}] + [
                {"label": row['Name'], "value": str(row['LocationID'])}
                for _, row in df_locations.iterrows() if pd.notnull(row['Name'])
            ]
            
            # print(f"📊 Location options loaded: {len(location_options)} options (filtered: {filtered})")
            return (
                location_options,
                "Select Locations...",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )
            
        except Exception as e:
            print(f"❌ Error loading location options: {e}")
            return (
                [],
                "Error loading Locations",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )

    # Show classes spinner when filters change
    @callback(
        [Output("training-class-spinner", "style", allow_duplicate=True),
         Output("training-class-dropdown", "placeholder", allow_duplicate=True)],
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value"),
         Input("training-instructor-dropdown", "value"),
         Input("training-location-dropdown", "value"),
         Input("training-topics-dropdown", "value")],
        prevent_initial_call=True
    )
    def show_class_spinner(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics):
        """Show class spinner when dependent filters change"""
        return (
            {"visibility": "block", "position": "relative", "top": "-30px", "right": "-30px"},   # ✅ Show spinner
            "Re-Loading classes..."         # ✅ Loading placeholder
        )
    
    # ✅ Classes dropdown - fetch classes + topics + attendance stats for filtering
    @callback(
        [Output("training-class-dropdown", "options"),
         Output("training-class-dropdown", "placeholder"),
         Output("training-class-spinner", "style")], 
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value"),
         Input("training-instructor-dropdown", "value"),
         Input("training-location-dropdown", "value"),
         Input("training-topics-dropdown", "value")],
        prevent_initial_call=False
    )
    # @monitor_performance("Training Classes Dropdown Population")
    def populate_class_filter(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics):
        """
        Populate classes dropdown based on all filter selections
        """
        try:
            # ✅ Fetch required data
            df_topics = get_topics_data()
            df_classes = get_classes_data()
            
            filtered = False
            
            # Apply filtering from attendance stats
            if any([
                selected_aors and len(selected_aors) != 0 and "All" not in selected_aors,
                selected_offices and len(selected_offices) != 0 and "All" not in selected_offices,
                selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors,
                selected_locations and len(selected_locations) != 0 and "All" not in selected_locations
            ]):
                filtered = True
                df_attendance_stats = get_attendance_stats_data()
                
                if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["AorShortName"].isin(selected_aors)]
                    df_classes = df_classes[df_classes["AorShortName"].isin(selected_aors)]

                if selected_offices and len(selected_offices) != 0 and "All" not in selected_offices:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["MemberOffice"].isin(selected_offices)]

                if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["InstructorId"].isin(selected_instructors)]
                    df_classes = df_classes[df_classes["InstructorId"].isin(selected_instructors)]

                if selected_locations and len(selected_locations) != 0 and "All" not in selected_locations:
                    df_attendance_stats = df_attendance_stats[df_attendance_stats["LocationId"].isin(selected_locations)]
                    df_classes = df_classes[df_classes["LocationId"].isin(selected_locations)]

                # Filter classes by available class IDs
                class_ids = df_attendance_stats["TrainingClassId"].unique().tolist()
                df_classes = df_classes[df_classes["ClassId"].isin(class_ids)]

            # Apply topic filter directly to classes
            if selected_topics and len(selected_topics) != 0 and "All" not in selected_topics:
                df_classes = df_classes[df_classes["TopicId"].isin(selected_topics)]
                selected_topic_labels = df_topics[df_topics["TopicId"].isin(selected_topics)]['TopicName'].values.tolist()
                selected_topics_label = ' ' + ','.join([str(topic) for topic in selected_topic_labels]) + ' '
            else:
                selected_topics_label = ' '

            # Build dynamic "All Classes" label
            all_classes_label = f"All{selected_topics_label}Classes"
            if selected_aors and len(selected_aors) != 0 and "All" not in selected_aors:
                all_classes_label = f"{all_classes_label} For {','.join(selected_aors)}"
            if selected_instructors and len(selected_instructors) != 0 and "All" not in selected_instructors:
                instructor_names = df_classes[df_classes['InstructorId'].isin(selected_instructors)]['InstructorName'].unique().tolist()
                all_classes_label = f"{all_classes_label} By {','.join(instructor_names)}"
            if selected_locations and len(selected_locations) != 0 and "All" not in selected_locations:
                location_names = df_classes[df_classes['LocationId'].isin(selected_locations)]['LocationName'].unique().tolist()
                all_classes_label = f"{all_classes_label} At {','.join(location_names)}"

            if len(df_classes) > 0:
                class_options = [{"label": all_classes_label, "value": "All"}] + [
                    {"label": f"{row['ClassName']}: {row['StartTime']}", "value": row['ClassId']}
                    for _, row in df_classes.iterrows() if pd.notnull(row['ClassName'])
                ]
            else:
                class_options = []

            # print(f"📊 Class options loaded: {len(class_options)} options (filtered: {filtered})")
            return (
                class_options,
                "Select Classes..." if class_options else "No classes available",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )
            
        except Exception as e:
            print(f"❌ Error loading class options: {e}")
            return (
                [],
                "Error loading Classes",
                {"visibility": "hidden"}  # ✅ Hide spinner
            )

    # ✅ Clear filters callback
    @callback(
        [Output("training-date-range-picker", "start_date", allow_duplicate=True),
         Output("training-date-range-picker", "end_date", allow_duplicate=True),
         Output("training-aor-dropdown", "value", allow_duplicate=True),
         Output("training-office-dropdown", "value", allow_duplicate=True),
         Output("training-topics-dropdown", "value", allow_duplicate=True),
         Output("training-instructor-dropdown", "value", allow_duplicate=True),
         Output("training-location-dropdown", "value", allow_duplicate=True),
         Output("training-class-dropdown", "value", allow_duplicate=True)],
        Input("training-clear-filters-btn", "n_clicks"),
        prevent_initial_call=True
    )
    # @monitor_performance("Training Clear All Filters")
    def clear_all_filters(n_clicks):
        """
        Clear all filter selections
        """
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()
        
        return (
            date_start_default, date_end_default,
            [], [], [], [], [], []  # Clear all dropdown selections
        )

    # print("✅ Training filter callbacks registered (optimized - individual queries)")

    @app.callback(
        Output("training-filtered-query-store", "data"),     
        Input("training-date-range-picker", "start_date"),
        Input("training-date-range-picker", "end_date"),  
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-topics-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-class-dropdown", "value"),
        prevent_initial_call=False
    )
    def filter_data_query(start_date, end_date, 
                          selected_aors, selected_offices, 
                          selected_topics, selected_instructors, 
                          selected_locations, selected_classes):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        selections = {
            "Day_From": start_date if start_date is not None else start_placeholder,
            "Day_To": end_date if end_date is not None else end_placeholder,
            "AORs": ", ".join(["'"+aor+"'" for aor in selected_aors]) if selected_aors and len(selected_aors) > 0 and "All" not in selected_aors else "",
            "Offices": ", ".join(["'"+office+"'" for office in selected_offices]) if selected_offices and len(selected_offices) > 0 and "All" not in selected_offices else "",
            "Topics": ", ".join(["'"+topic+"'" for topic in selected_topics]) if selected_topics and len(selected_topics) > 0 and "All" not in selected_topics else "",
            "Instructors": ", ".join(["'"+instructor+"'" for instructor in selected_instructors]) if selected_instructors and len(selected_instructors) > 0 and "All" not in selected_instructors else "",
            "Locations": ", ".join(["'"+location+"'" for location in selected_locations]) if selected_locations and len(selected_locations) > 0 and "All" not in selected_locations else "",
            "Classes": ", ".join(["'"+cls+"'" for cls in selected_classes]) if selected_classes and len(selected_classes) > 0 and "All" not in selected_classes else ""
        }
        # print("🔍 Training filter selections updated:", selections)
        return selections