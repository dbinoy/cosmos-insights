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
        Output("training-request-stats-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_request_stats_data(_):
        q_request_stats = 'SELECT [TrainingTopicId],[AorShortName],[MemberOffice] FROM [consumable].[Fact_RequestStats]'
        result = run_queries({"request_stats": q_request_stats}, 1)
        return result["request_stats"].to_dict("records")

    @app.callback(
        Output("training-attendance-stats-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_attendance_stats_data(_):
        q_attendance_stats = 'SELECT [TrainingClassId],[TrainingTopicId],[LocationId],[InstructorId],[AorShortName],[MemberOffice] FROM [consumable].[Fact_AttendanceStats]'
        result = run_queries({"attendance_stats": q_attendance_stats}, 1)
        return result["attendance_stats"].to_dict("records")
    
    @app.callback(
        Output("training-aor-spinner", "spinner_style"),
        Output("training-aor-dropdown", "placeholder"),
        Input("training-aors-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data")
    )
    def toggle_aor_spinner(data, req_data, att_data):
        if data is None and req_data is None and att_data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}, "Loading AORs..."
        return {"display": "none"}, "Select AOR(s)"
        
    @app.callback(
        Output("training-office-spinner", "spinner_style"),
        Output("training-office-dropdown", "placeholder"),
        Input("training-offices-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data")
    )
    def toggle_office_spinner(data, req_data, att_data):
        if data is None and req_data is None and att_data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}, "Loading Offices..."
        return {"display": "none"}, "Select Office(s)"

    @app.callback(
        Output("training-topics-spinner", "spinner_style"),
        Output("training-topics-dropdown", "placeholder"),
        Input("training-topics-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data")
    )
    def toggle_topics_spinner(data, req_data, att_data):
        if data is None and req_data is None and att_data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}, "Loading Topics..."
        return {"display": "none"}, "Select Topic(s)"

    @app.callback(
        Output("training-instructor-spinner", "spinner_style"),
        Output("training-instructor-dropdown", "placeholder"),
        Input("training-instructors-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data")
    )
    def toggle_instructor_spinner(data, req_data, att_data):
        if data is None and req_data is None and att_data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}, "Loading Instructors..."
        return {"display": "none"}, "Select Instructor(s)"

    @app.callback(
        Output("training-location-spinner", "spinner_style"),
        Output("training-location-dropdown", "placeholder"),
        Input("training-locations-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data")
    )
    def toggle_location_spinner(data, req_data, att_data):
        if data is None and req_data is None and att_data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}, "Loading Locations..."
        return {"display": "none"}, "Select Location(s)"   

    @app.callback(
        Output("training-class-spinner", "spinner_style"),
        Output("training-class-dropdown", "placeholder"),
        Input("training-classes-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data")
    )
    def toggle_class_spinner(data, req_data, att_data):
        if data is None and req_data is None and att_data is None:
            return {"position": "absolute", "top": "30px", "right": "30px"}, "Loading Classes..."
        return {"display": "none"}, "Select Class(es)"

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
    
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, topics_data, request_stats, attendance_stats) {
            if (!topics_data || topics_data.length === 0) {
                return [{label: "Loading...", value: "", disabled: true}];
            }
            
            let filtered_topics = topics_data;
            
            // If we have stats data and filters are applied, filter topics based on stats
            if (request_stats && attendance_stats && request_stats.length > 0 && attendance_stats.length > 0) {
                let filtered_request_stats = request_stats;
                let filtered_attendance_stats = attendance_stats;
                let should_filter = false;
                
                // Filter stats by AOR
                if (Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_request_stats = filtered_request_stats.filter(r => selected_aors.indexOf(r.AorShortName) !== -1);
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_aors.indexOf(r.AorShortName) !== -1);
                }
                
                // Filter stats by Office
                if (Array.isArray(selected_offices) && selected_offices.length > 0 && selected_offices.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_request_stats = filtered_request_stats.filter(r => selected_offices.indexOf(r.MemberOffice) !== -1);
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_offices.indexOf(r.MemberOffice) !== -1);
                }
                
                // If filters were applied, get unique topic IDs from filtered stats
                if (should_filter) {
                    const topic_ids_from_requests = [...new Set(filtered_request_stats.map(r => r.TrainingTopicId))];
                    const topic_ids_from_attendance = [...new Set(filtered_attendance_stats.map(r => r.TrainingTopicId))];
                    const all_topic_ids = [...new Set([...topic_ids_from_requests, ...topic_ids_from_attendance])];
                    
                    filtered_topics = topics_data.filter(t => all_topic_ids.indexOf(t.TopicId) !== -1);
                }
            }
            
            const options = [{label: "All Topics", value: "All"}].concat(
                filtered_topics.map(t => ({label: t.TopicName, value: String(t.TopicId)}))
            );
            return options;
        }
        """,
        Output("training-topics-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-topics-data-store", "data"),
        Input("training-request-stats-data-store", "data"),
        Input("training-attendance-stats-data-store", "data"),
        prevent_initial_call=False
    )
    
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, instructors_data, attendance_stats) {
            if (!instructors_data || instructors_data.length === 0) {
                return [{label: "Loading...", value: "", disabled: true}];
            }
            
            let filtered_instructors = instructors_data;
            
            // If we have attendance stats and filters are applied
            if (attendance_stats && attendance_stats.length > 0) {
                let filtered_attendance_stats = attendance_stats;
                let should_filter = false;
                
                // Filter stats by AOR
                if (Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_aors.indexOf(r.AorShortName) !== -1);
                }
                
                // Filter stats by Office
                if (Array.isArray(selected_offices) && selected_offices.length > 0 && selected_offices.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_offices.indexOf(r.MemberOffice) !== -1);
                }
                
                // If filters were applied, get unique instructor IDs from filtered stats
                if (should_filter) {
                    const instructor_ids = [...new Set(filtered_attendance_stats.map(r => r.InstructorId))];
                    filtered_instructors = instructors_data.filter(i => instructor_ids.indexOf(i.InstructorID) !== -1);
                }
            }
            
            const options = [{label: "All Instructors", value: "All"}].concat(
                filtered_instructors.map(i => ({label: i.Name, value: String(i.InstructorID)}))
            );
            return options;
        }
        """,
        Output("training-instructor-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-instructors-data-store", "data"),
        Input("training-attendance-stats-data-store", "data"),
        prevent_initial_call=False
    ) 
    
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, selected_topics, selected_instructors, locations_data, attendance_stats) {
            if (!locations_data || locations_data.length === 0) {
                return [{label: "Loading...", value: "", disabled: true}];
            }
            
            let filtered_locations = locations_data;
            
            // If we have attendance stats and filters are applied
            if (attendance_stats && attendance_stats.length > 0) {
                let filtered_attendance_stats = attendance_stats;
                let should_filter = false;
                
                // Filter stats by AOR
                if (Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_aors.indexOf(r.AorShortName) !== -1);
                }
                
                // Filter stats by Office
                if (Array.isArray(selected_offices) && selected_offices.length > 0 && selected_offices.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_offices.indexOf(r.MemberOffice) !== -1);
                }
                
                // Filter stats by Topics
                if (Array.isArray(selected_topics) && selected_topics.length > 0 && selected_topics.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_topics.indexOf(String(r.TrainingTopicId)) !== -1);
                }
                
                // Filter stats by Instructors
                if (Array.isArray(selected_instructors) && selected_instructors.length > 0 && selected_instructors.indexOf("All") === -1) {
                    should_filter = true;
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_instructors.indexOf(String(r.InstructorId)) !== -1);
                }
                
                // If filters were applied, get unique location IDs from filtered stats
                if (should_filter) {
                    const location_ids = [...new Set(filtered_attendance_stats.map(r => r.LocationId))];
                    filtered_locations = locations_data.filter(l => location_ids.indexOf(l.LocationID) !== -1);
                }
            }
            
            const options = [{label: "All Locations", value: "All"}].concat(
                filtered_locations.map(l => ({label: l.Name, value: String(l.LocationID)}))
            );
            return options;
        }
        """,
        Output("training-location-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-topics-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-locations-data-store", "data"),
        Input("training-attendance-stats-data-store", "data"),
        prevent_initial_call=False
    )
    
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics, 
                 classes_data, attendance_stats, topics_data) {
            if (!classes_data || classes_data.length === 0) {
                return [{label: "Loading...", value: "", disabled: true}];
            }
            
            let filtered_classes = classes_data;
            
            // First filter classes directly by selected filters
            if (Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) {
                filtered_classes = filtered_classes.filter(c => selected_aors.indexOf(c.AorShortName) !== -1);
            }
            
            if (Array.isArray(selected_instructors) && selected_instructors.length > 0 && selected_instructors.indexOf("All") === -1) {
                filtered_classes = filtered_classes.filter(c => selected_instructors.indexOf(String(c.InstructorId)) !== -1);
            }
            
            if (Array.isArray(selected_locations) && selected_locations.length > 0 && selected_locations.indexOf("All") === -1) {
                filtered_classes = filtered_classes.filter(c => selected_locations.indexOf(String(c.LocationId)) !== -1);
            }
            
            if (Array.isArray(selected_topics) && selected_topics.length > 0 && selected_topics.indexOf("All") === -1) {
                filtered_classes = filtered_classes.filter(c => selected_topics.indexOf(String(c.TopicId)) !== -1);
            }
            
            // Additionally filter by attendance stats if available and other filters are applied
            if (attendance_stats && attendance_stats.length > 0 && 
                ((Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) ||
                 (Array.isArray(selected_offices) && selected_offices.length > 0 && selected_offices.indexOf("All") === -1))) {
                
                let filtered_attendance_stats = attendance_stats;
                
                // Filter attendance stats by AOR and Office
                if (Array.isArray(selected_aors) && selected_aors.length > 0 && selected_aors.indexOf("All") === -1) {
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_aors.indexOf(r.AorShortName) !== -1);
                }
                
                if (Array.isArray(selected_offices) && selected_offices.length > 0 && selected_offices.indexOf("All") === -1) {
                    filtered_attendance_stats = filtered_attendance_stats.filter(r => selected_offices.indexOf(r.MemberOffice) !== -1);
                }
                
                // Get class IDs from filtered attendance stats
                const class_ids_from_stats = [...new Set(filtered_attendance_stats.map(r => r.TrainingClassId))];
                filtered_classes = filtered_classes.filter(c => class_ids_from_stats.indexOf(c.ClassId) !== -1);
            }
            
            if (filtered_classes.length === 0) {
                return [{label: "No classes found", value: "", disabled: true}];
            }
            
            // Build label for "All" option
            let all_label = "All";
            if (Array.isArray(selected_topics) && selected_topics.length > 0 && selected_topics.indexOf("All") === -1 && topics_data) {
                const selected_topic_names = topics_data
                    .filter(t => selected_topics.indexOf(String(t.TopicId)) !== -1)
                    .map(t => t.TopicName);
                all_label += ` ${selected_topic_names.join(',')}`;
            }
            all_label += " Classes";
            
            const options = [{label: all_label, value: "All"}].concat(
                filtered_classes.map(c => ({label: `${c.ClassName}: ${c.StartTime}`, value: c.ClassId}))
            );
            return options;
        }
        """,
        Output("training-class-dropdown", "options"),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-topics-dropdown", "value"),
        Input("training-classes-data-store", "data"),
        Input("training-attendance-stats-data-store", "data"),
        Input("training-topics-data-store", "data"),
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