from dash.dependencies import Input, Output, State
from dash import clientside_callback
import pandas as pd
import textwrap
import time
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    
    @app.callback(
        Output("training-date-range-picker", "start_date_placeholder_text"),
        Output("training-date-range-picker", "end_date_placeholder_text"),
        Input("training-filtered-query-store", "id"),
        prevent_initial_call=False
    )
    def initialize_filter_layout(_):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()
        return str(start_placeholder), str(end_placeholder)
        
    @app.callback(
        Output("training-aors-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_aors_data(_):
        q_aors = 'SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
        result = run_queries({"aors": q_aors}, 1)
        return result["aors"].to_dict("records")            
            
    @app.callback(
        Output("training-offices-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_offices_data(_):
        q_offices = 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]'
        result = run_queries({"offices": q_offices}, 1)
        return result["offices"].to_dict("records")
    
    @app.callback(
        Output("training-topics-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_topics_data(_):
        q_topics = 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]'
        result = run_queries({"topics": q_topics}, 1)
        return result["topics"].to_dict("records")
    
    @app.callback(
        Output("training-instructors-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_instructors_data(_):
        q_instructors = 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]'
        result = run_queries({"instructors": q_instructors}, 1)
        return result["instructors"].to_dict("records")
    
    @app.callback(
        Output("training-locations-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_locations_data(_):
        q_locations = 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]'
        result = run_queries({"locations": q_locations}, 1)
        return result["locations"].to_dict("records")
    
    @app.callback(
        Output("training-classes-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_classes_data(_):
        q_classes = 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]'
        result = run_queries({"classes": q_classes}, 1)
        return result["classes"].to_dict("records")

    @app.callback(
        Output("training-aor-spinner", "spinner_style"),
        Input("training-aors-data-store", "data")
    )
    def toggle_aor_spinner(data):
        if data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}
        return {"display": "none"}
    
    @app.callback(
        Output("training-office-spinner", "spinner_style"),
        Input("training-offices-data-store", "data")
    )
    def toggle_office_spinner(data):
        if data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}
        return {"display": "none"}   

    @app.callback(
        Output("training-topics-spinner", "spinner_style"),
        Input("training-topics-data-store", "data")
    )
    def toggle_topics_spinner(data):
        if data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}
        return {"display": "none"}     

    @app.callback(
        Output("training-instructor-spinner", "spinner_style"),
        Input("training-instructors-data-store", "data")
    )
    def toggle_instructor_spinner(data):
        if data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}
        return {"display": "none"}   
           
    @app.callback(
        Output("training-location-spinner", "spinner_style"),
        Input("training-locations-data-store", "data")
    )
    def toggle_location_spinner(data):
        if data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}
        return {"display": "none"}       

    @app.callback(
        Output("training-class-spinner", "spinner_style"),
        Input("training-classes-data-store", "data")
    )
    def toggle_class_spinner(data):
        if data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}
        return {"display": "none"}              

    @app.callback(
        Output("training-aor-dropdown", "options"),
        Input("training-aors-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_aor_dropdown(aors_data):
        if not aors_data:
            return [{"label": "Loading...", "value": "", "disabled": True}]
        
        return [{"label": "All Aors", "value": "All"}] + [
            {"label": f"{aor['AorShortName']} - {aor['AorName']}", "value": str(aor['AorShortName'])} 
            for aor in aors_data if aor.get('AorShortName')
        ]

    app.clientside_callback(
        """
        function(selected_aors, offices_data) {
            if (!offices_data || offices_data.length === 0) {
                return [{label: "Loading...", value: "", disabled: true}];
            }
            
            let offices = offices_data;
            if (Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) {
                offices = offices.filter(o => selected_aors.indexOf(o.AorShortName) !== -1);
            }
            
            const selectedAorsLabel = (Array.isArray(selected_aors) && selected_aors.length) ? (' ' + selected_aors.join(',') + ' ') : ' ';
            const options = [{label: `All${selectedAorsLabel}Offices`, value: "All"}].concat(
                offices.map(o => ({label: `${o.AorShortName} - ${o.OfficeCode}`, value: o.OfficeCode}))
            );
            return options;
        }
        """,
        Output("training-office-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-offices-data-store", "data"),
        prevent_initial_call=False
    )

    # Topics dropdown
    @app.callback(
        Output("training-topics-dropdown", "options"),
        Input("training-topics-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_topics_dropdown(topics_data):
        if not topics_data:
            return [{"label": "Loading...", "value": "", "disabled": True}]
        
        return [{"label": "All Topics", "value": "All"}] + [
            {"label": topic['TopicName'], "value": str(topic['TopicId'])} 
            for topic in topics_data if topic.get('TopicName')
        ]
    
    # Instructors dropdown
    @app.callback(
        Output("training-instructor-dropdown", "options"),
        Input("training-instructors-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_instructors_dropdown(instructors_data):
        if not instructors_data:
            return [{"label": "Loading...", "value": "", "disabled": True}]
        
        return [{"label": "All Instructors", "value": "All"}] + [
            {"label": instructor['Name'], "value": str(instructor['InstructorID'])} 
            for instructor in instructors_data if instructor.get('Name')
        ]
    
    # Locations dropdown
    @app.callback(
        Output("training-location-dropdown", "options"),
        Input("training-locations-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_locations_dropdown(locations_data):
        if not locations_data:
            return [{"label": "Loading...", "value": "", "disabled": True}]
        
        return [{"label": "All Locations", "value": "All"}] + [
            {"label": location['Name'], "value": str(location['LocationID'])} 
            for location in locations_data if location.get('Name')
        ]    
    
    app.clientside_callback(
        """
        function(selected_aors, selected_instructors, selected_locations, selected_topics, classes_data) {
            if (!classes_data || classes_data.length === 0) {
                return [{label: "Loading...", value: "", disabled: true}];
            }
            
            let classes = classes_data;

            function applyFilter(list, sel, key) {
                if (!Array.isArray(sel) || sel.length === 0 || sel.indexOf("All") !== -1) return list;
                return list.filter(r => sel.indexOf(String(r[key])) !== -1);
            }

            classes = applyFilter(classes, selected_aors, "AorShortName");
            classes = applyFilter(classes, selected_instructors, "InstructorId");
            classes = applyFilter(classes, selected_locations, "LocationId");
            classes = applyFilter(classes, selected_topics, "TopicId");

            if (classes.length === 0) return [{label: "No classes found", value: "", disabled: true}];

            const selectedTopicLabels = Array.isArray(selected_topics) ? selected_topics.join(',') : '';
            let allLabel = `All ${selectedTopicLabels} Classes`.trim();
            const options = [{label: allLabel, value: "All"}].concat(
                classes.map(c => ({label: `${c.ClassName}: ${c.StartTime}`, value: c.ClassId}))
            );
            return options;
        }
        """,
        Output("training-class-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-topics-dropdown", "value"),
        Input("training-classes-data-store", "data"),
        prevent_initial_call=False            
    )
    
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
        prevent_initial_call=True,
        allow_duplicate=True
    )
    def clear_all_filters(n_clicks):
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()  
        return date_start_default, date_end_default, [], [], [], [], [], []