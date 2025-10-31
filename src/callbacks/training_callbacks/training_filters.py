from dash.dependencies import Input, Output, State
from dash import clientside_callback
import pandas as pd
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    """
    Clean, modular training filter callbacks using external JavaScript modules
    All JavaScript logic is now completely externalized to utility files
    """
    # print("Registering Filter callbacks...")

    # Step 1: Initial cache check - now externalized to TrainingDataManager
    app.clientside_callback(
        "function(_) { return TrainingDataManager.checkTrainingDataCache(_); }",
        Output("training-cache-check-store", "data"),
        Input("training-filtered-query-store", "id"),
        prevent_initial_call=False
    )   
    
    # Step 2: Conditional server data loading - only if cache check indicates need
    @app.callback(
        Output("training-filtered-data-store", "data"),
        Input("training-cache-check-store", "data"),
        prevent_initial_call=False
    )
    def load_all_training_data(cache_check_result):
        """Load training data from server only if cache check indicates it's needed"""
        
        # If cache check hasn't completed yet, return no_update
        if not cache_check_result:
            return {}
        
        # If cache has all data, don't load from server
        if not cache_check_result.get('needsServerData', True):
            # print("✅ Cache check indicates all data available - skipping server queries")
            return cache_check_result.get('cacheData', {})
        
        # Cache is incomplete - load from server
        # print("📡 Loading training data from server...")
        
        queries = {
            "aors": 'SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]',
            "offices": 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]',
            "topics": 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]',
            "instructors": 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]',
            "locations": 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]',
            "classes": 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]',
            "request_stats": 'SELECT [TrainingTopicId],[AorShortName],[MemberOffice],[TotalRequests] FROM [consumable].[Fact_RequestStats]',
            "attendance_stats": 'SELECT [TrainingClassId],[TrainingTopicId],[LocationId],[InstructorId],[AorShortName],[MemberOffice],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]',
            "active_members": "SELECT [MemberID], [OfficeCode] FROM [consumable].[Fact_MemberEngagement] WHERE ([TotalSessionsRegistered] > 0 OR [TotalSessionsAttended] > 0) AND [MemberStatus] = 'Active'"            
        }
        
        # Execute all queries at once
        results = run_queries(queries, 1)
        
        # Convert to dictionaries
        all_data = {}
        for key, df in results.items():
            all_data[key] = df.to_dict("records")
            # print(f"📊 Loaded {len(all_data[key])} {key} records from server")
        
        return all_data

    # Step 3: Initialize system with either cached or server data
    app.clientside_callback(
        "function(server_data) { return TrainingDataManager.initializeTrainingSystem(server_data); }",
        Output("training-data-ready", "data"),
        Input("training-filtered-data-store", "data"),
        prevent_initial_call=False
    )

    # Initialize date range placeholders
    @app.callback(
        Output("training-date-range-picker", "start_date_placeholder_text"),
        Output("training-date-range-picker", "end_date_placeholder_text"),
        Input("training-data-ready", "data"),
        prevent_initial_call=False
    )
    def initialize_date_range(data_ready):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        return str(start_placeholder), str(end_placeholder)

    # Unified spinner control using training-specific utility function
    app.clientside_callback(
        "function(data_ready) { const isReady = data_ready && data_ready.ready; return TrainingFilterUtils.createTrainingSpinnerStates(isReady); }",
        [Output("training-aor-spinner", "spinner_style"), Output("training-aor-dropdown", "placeholder"),
         Output("training-office-spinner", "spinner_style"), Output("training-office-dropdown", "placeholder"),
         Output("training-topics-spinner", "spinner_style"), Output("training-topics-dropdown", "placeholder"),
         Output("training-instructor-spinner", "spinner_style"), Output("training-instructor-dropdown", "placeholder"),
         Output("training-location-spinner", "spinner_style"), Output("training-location-dropdown", "placeholder"),
         Output("training-class-spinner", "spinner_style"), Output("training-class-dropdown", "placeholder")],
        Input("training-data-ready", "data"),
        prevent_initial_call=False
    )

    # Clean dropdown callbacks using external handlers
    app.clientside_callback(
        "function(data_ready) { return TrainingDropdownHandlers.getAorOptions(window.trainingDataManager); }",
        Output("training-aor-dropdown", "options"),
        Input("training-data-ready", "data"),
        prevent_initial_call=False
    )

    app.clientside_callback(
        "function(selected_aors, data_ready) { return TrainingDropdownHandlers.getOfficeOptions(selected_aors, window.trainingDataManager); }",
        Output("training-office-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    app.clientside_callback(
        "function(selected_aors, selected_offices, data_ready) { return TrainingDropdownHandlers.getTopicOptions(selected_aors, selected_offices, window.trainingDataManager); }",
        Output("training-topics-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), Input("training-office-dropdown", "value"), Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    app.clientside_callback(
        "function(selected_aors, selected_offices, data_ready) { return TrainingDropdownHandlers.getInstructorOptions(selected_aors, selected_offices, window.trainingDataManager); }",
        Output("training-instructor-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), Input("training-office-dropdown", "value"), Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    app.clientside_callback(
        "function(selected_aors, selected_offices, selected_topics, selected_instructors, data_ready) { return TrainingDropdownHandlers.getLocationOptions(selected_aors, selected_offices, selected_topics, selected_instructors, window.trainingDataManager); }",
        Output("training-location-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), Input("training-office-dropdown", "value"), Input("training-topics-dropdown", "value"), Input("training-instructor-dropdown", "value"), Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    app.clientside_callback(
        "function(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics, data_ready) { return TrainingDropdownHandlers.getClassOptions(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics, window.trainingDataManager); }",
        Output("training-class-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), Input("training-office-dropdown", "value"), Input("training-instructor-dropdown", "value"), Input("training-location-dropdown", "value"), Input("training-topics-dropdown", "value"), Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    # Clear filters callback - using external utility function
    app.clientside_callback(
        "function(n_clicks) { return TrainingFilterUtils.clearAllTrainingFilters(n_clicks); }",
        [Output("training-date-range-picker", "start_date"),
         Output("training-date-range-picker", "end_date"),
         Output("training-aor-dropdown", "value"),
         Output("training-office-dropdown", "value"),
         Output("training-topics-dropdown", "value"),
         Output("training-instructor-dropdown", "value"),
         Output("training-location-dropdown", "value"),
         Output("training-class-dropdown", "value")],
        Input("training-clear-filters-btn", "n_clicks"),
        prevent_initial_call=True
    )

    @app.callback(
        Output("training-filtered-query-store", "data"),     
        Input("training-filtered-data-store", "data"),
        Input("training-date-range-picker", "start_date"),
        Input("training-date-range-picker", "end_date"),  
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-topics-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-class-dropdown", "value"),
        prevent_initial_call=True
    )
    def filter_data_query(filter_data, start_date, end_date, 
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