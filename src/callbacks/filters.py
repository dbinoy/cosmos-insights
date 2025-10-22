from dash.dependencies import Input, Output, State
from dash import clientside_callback
import pandas as pd
import textwrap
import time
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    
    @app.callback(
        Output("training-filter-data-store", "data"),
        Input("training-filtered-query-store", "id"), 
        prevent_initial_call=False
    )
    def load_filter_data(_):
        start = time.time()
        q_aors ='SELECT DISTINCT [AorID], [AorName], [AorShortName] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName]'
        q_offices = 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]'
        q_topics = 'SELECT DISTINCT [TopicId], [TopicName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName]'
        q_instructors = 'SELECT [InstructorID], [Name] FROM [consumable].[Dim_Instructors] ORDER BY [Name]'
        q_locations = 'SELECT [LocationID], [Name] FROM [consumable].[Dim_Locations] ORDER BY [Name]'
        q_classes = 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]'
        # q_request_stats = 'SELECT [TrainingTopicId],[TrainingTopicName],[AorShortName],[AorName],[MemberOffice],[MembersRequested],[TotalRequests] FROM [consumable].[Fact_RequestStats]'
        # q_attendance_stats = 'SELECT [TrainingClassId],[ClassName],[TrainingTopicId],[TrainingTopicName],[LocationId],[LocationName],[InstructorId],[InstructorName],[AorShortName],[MemberOffice],[MembersAttended],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]'


        queries = {
            "aors": q_aors,
            "offices": q_offices,
            "topics": q_topics,
            "instructors": q_instructors,
            "locations": q_locations,
            "classes": q_classes,
            # "request_stats": q_request_stats,
            # "attendance_stats": q_attendance_stats
        }           

        results = run_queries(queries, len(queries.keys()))
        filter_data = {
            "aors": results["aors"].to_dict("records"),
            "offices": results["offices"].to_dict("records"),
            "topics": results["topics"].to_dict("records"),
            "instructors": results["instructors"].to_dict("records"),
            "locations": results["locations"].to_dict("records"),
            "classes": results["classes"].to_dict("records"),
            # "request_stats": results["request_stats"].to_dict("records"),
            # "attendance_stats": results["attendance_stats"].to_dict("records")
        }    
        print("Data Load done in", time.time()-start, "s")
        return filter_data   
    
    @app.callback(
        Output("training-date-range-picker", "start_date_placeholder_text"),
        Output("training-date-range-picker", "end_date_placeholder_text"),
        Output("training-aor-dropdown", "options"),
        # Output("training-office-dropdown", "options"),
        # Output("training-topics-dropdown", "options"),
        # Output("training-instructor-dropdown", "options"),
        # Output("training-location-dropdown", "options"),
        # Output("training-class-dropdown", "options"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=False
    )
    def populate_filters(filter_data):
        start_placeholder = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        end_placeholder = datetime.today().date()        

        if not filter_data:
            # return str(start_placeholder), str(end_placeholder), [], [], [], [], [], []
            return str(start_placeholder), str(end_placeholder), []
        
        df_aors = pd.DataFrame(filter_data["aors"])
        aor_options = [{"label": "All Aors", "value": "All"}]+[{"label": v[1]['AorShortName']+' - '+v[1]['AorName'], "value": str(v[1]['AorShortName'])} for v in df_aors.iterrows() if pd.notnull(v)]

        # df_offices = pd.DataFrame(filter_data["offices"])
        # office_options = [{"label": "All Offices", "value": "All"}]+[{"label": v[1]['AorShortName']+' - '+v[1]['OfficeCode'], "value": v[1]['OfficeCode']} for v in df_offices.iterrows() if pd.notnull(v)]

        # df_topics = pd.DataFrame(filter_data["topics"])
        # topic_options = [{"label": "All Topics", "value": "All"}]+[{"label": v[1]['TopicName'], "value": str(v[1]['TopicId'])} for v in df_topics.iterrows() if pd.notnull(v)]

        # df_instructors = pd.DataFrame(filter_data["instructors"])
        # instructor_options = [{"label": "All Instructors", "value": "All"}]+[{"label": v[1]['Name'], "value": str(v[1]['InstructorID'])} for v in df_instructors.iterrows() if pd.notnull(v)]

        # df_locations = pd.DataFrame(filter_data["locations"])        
        # location_options = [{"label": "All Locations", "value": "All"}]+[{"label": v[1]['Name'], "value": str(v[1]['LocationID'])} for v in df_locations.iterrows() if pd.notnull(v)]

        # df_classes = pd.DataFrame(filter_data["classes"])
        # class_options = [{"label": "All Classes", "value": "All"}]+[{"label": v[1]['ClassName']+': '+v[1]['StartTime'], "value": v[1]['ClassId']} for v in df_classes.iterrows() if pd.notnull(v)]

        # return str(start_placeholder), str(end_placeholder), aor_options, office_options, topic_options, instructor_options, location_options, class_options      
        return str(start_placeholder), str(end_placeholder), aor_options   
    
  
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
        aor_default = []
        office_default = []
        topics_default = []
        instructor_default = []
        location_default = []
        class_default = []
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()  
        return date_start_default, date_end_default, aor_default, office_default, topics_default, instructor_default, location_default, class_default

    
    app.clientside_callback(
        """
        function(selected_aors, filterData) {
            if (!filterData || !filterData.offices) { return []; }
            let offices = filterData.offices;
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
        Output("training-office-dropdown", "options", allow_duplicate=True),
        Input("training-aor-dropdown", "value"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=True
    )

    # topics options (client-side). can be extended to depend on aor/office if desired
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, filterData) {
            if (!filterData || !filterData.topics) { return []; }
            let topics = filterData.topics;
            // optional: filter topics based on other selections using precomputed stats in filterData if available
            const options = [{label: "All Topics", value: "All"}].concat(
                topics.map(t => ({label: t.TopicName, value: String(t.TopicId)}))
            );
            return options;
        }
        """,
        Output("training-topics-dropdown", "options", allow_duplicate=True),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=True    
    )

    # instructor options (client-side)
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, filterData) {
            if (!filterData || !filterData.instructors) { return []; }
            let instructors = filterData.instructors;
            // client-side filtering logic can be added here if needed
            const options = [{label: "All Instructors", value: "All"}].concat(
                instructors.map(i => ({label: i.Name, value: String(i.InstructorID)}))
            );
            return options;
        }
        """,
        Output("training-instructor-dropdown", "options", allow_duplicate=True ),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=True
    )

    # location options (client-side)
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, filterData) {
            if (!filterData || !filterData.locations) { return []; }
            let locations = filterData.locations;
            const options = [{label: "All Locations", value: "All"}].concat(
                locations.map(l => ({label: l.Name, value: String(l.LocationID)}))
            );
            return options;
        }
        """,
        Output("training-location-dropdown", "options", allow_duplicate=True ),
        Input("training-aor-dropdown", "value"),
        Input("training-office-dropdown", "value"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=True
    )

    # class options depend on selected aors, instructors, locations, topics and filter store
    app.clientside_callback(
        """
        function(selected_aors, selected_instructors, selected_locations, selected_topics, filterData) {
            if (!filterData || !filterData.classes) { return []; }
            let classes = filterData.classes;

            function applyFilter(list, sel, key) {
                if (!Array.isArray(sel) || sel.length === 0 || sel.indexOf("All") !== -1) return list;
                return list.filter(r => sel.indexOf(String(r[key])) !== -1);
            }

            classes = applyFilter(classes, selected_aors, "AorShortName");
            classes = applyFilter(classes, selected_instructors, "InstructorId");
            classes = applyFilter(classes, selected_locations, "LocationId");
            classes = applyFilter(classes, selected_topics, "TopicId");

            if (classes.length === 0) return [];

            // build options - label with ClassName and StartTime, value ClassId
            const selectedTopicLabels = Array.isArray(selected_topics) ? selected_topics.join(',') : '';
            let allLabel = `All ${selectedTopicLabels} Classes`.trim();
            const options = [{label: allLabel, value: "All"}].concat(
                classes.map(c => ({label: `${c.ClassName}: ${c.StartTime}`, value: c.ClassId}))
            );
            return options;
        }
        """,
        Output("training-class-dropdown", "options", allow_duplicate=True ),
        Input("training-aor-dropdown", "value"),
        Input("training-instructor-dropdown", "value"),
        Input("training-location-dropdown", "value"),
        Input("training-topics-dropdown", "value"),
        Input("training-filter-data-store", "data"),
        prevent_initial_call=True            
    )