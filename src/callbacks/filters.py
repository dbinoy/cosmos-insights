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
    
    # Step 1: Initial cache check - now externalized to TrainingDataManager
    app.clientside_callback(
        "function(_) { return TrainingDataManager.checkTrainingDataCache(_); }",
        Output("training-cache-check-store", "data"),
        Input("training-filtered-query-store", "id"),
        prevent_initial_call=False
    )
    
    # Step 2: Conditional server data loading - only if cache check indicates need
    @app.callback(
        Output("training-all-data-store", "data"),
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
            print("✅ Cache check indicates all data available - skipping server queries")
            return cache_check_result.get('cacheData', {})
        
        # Cache is incomplete - load from server
        print("📡 Loading training data from server...")
        
        queries = {
            "aors": 'SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]',
            "offices": 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]',
            "topics": 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]',
            "instructors": 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]',
            "locations": 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]',
            "classes": 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]',
            "request_stats": 'SELECT [TrainingTopicId],[AorShortName],[MemberOffice] FROM [consumable].[Fact_RequestStats]',
            "attendance_stats": 'SELECT [TrainingClassId],[TrainingTopicId],[LocationId],[InstructorId],[AorShortName],[MemberOffice] FROM [consumable].[Fact_AttendanceStats]'
        }
        
        # Execute all queries at once
        results = run_queries(queries, 1)
        
        # Convert to dictionaries
        all_data = {}
        for key, df in results.items():
            all_data[key] = df.to_dict("records")
            print(f"📊 Loaded {len(all_data[key])} {key} records from server")
        
        return all_data

    # Step 3: Initialize system with either cached or server data
    app.clientside_callback(
        "function(server_data) { return TrainingDataManager.initializeTrainingSystem(server_data); }",
        Output("training-data-ready", "data"),
        Input("training-all-data-store", "data"),
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