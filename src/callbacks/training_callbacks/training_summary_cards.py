from dash.dependencies import Input, Output
import pandas as pd
from src.utils.db import run_queries
from datetime import datetime, timedelta
import re


def register_training_summary_cards_callbacks(app):

    def fetch_base_data():
        queries = {
            "offices": 'SELECT DISTINCT [AorShortName], [OfficeCode] FROM [consumable].[Dim_Aors] ORDER BY [AorShortName], [OfficeCode]',
            "classes": 'SELECT [TopicId],[TopicName],[ClassId],[ClassName],[AorShortName],[StartTime],[InstructorId],[InstructorName],[LocationId],[LocationName] FROM [consumable].[Dim_ClassTopics] ORDER BY [TopicName], [ClassName], [StartTime]',
            "request_stats": 'SELECT [TrainingTopicId],[AorShortName],[MemberOffice],[TotalRequests] FROM [consumable].[Fact_RequestStats]',
            "attendance_stats": 'SELECT [TrainingClassId],[StartTime],[TrainingTopicId],[LocationId],[InstructorId],[AorShortName],[MemberOffice],[TotalAttendances] FROM [consumable].[Fact_AttendanceStats]',
            "active_members": "SELECT [MemberID],[MemberName],[MemberType],[MemberStatus],[OfficeCode],[TotalSessionsRegistered],[TotalSessionsAttended] FROM [consumable].[Fact_MemberEngagement] WHERE ([TotalSessionsRegistered] > 0 OR [TotalSessionsAttended] > 0) AND [MemberStatus] = 'Active'"            
        }
        result = run_queries(queries, 'training', len(queries))
        # print(f"✅ Fetched base data for training summary cards: {len(result['offices'])} offices, {len(result['classes'])} classes, {len(result['request_stats'])} request stats, {len(result['attendance_stats'])} attendance stats, {len(result['active_members'])} active members")
        return result

    def calculate_active_members_count(df_members, query_selections, df_offices):
        """
        Filter active members DataFrame based on query selections using pandas
        Enhanced to handle AOR-based filtering using existing office data 
        """
        if df_members.empty:
            return 0
        
        try:
            df_filtered = df_members.copy()
            
            if query_selections and isinstance(query_selections, dict):
                # Get filter values
                aors_filter = query_selections.get('AORs', '')
                offices_filter = query_selections.get('Offices', '')
                
                aor_list = []
                if aors_filter:
                    aor_list = [aor.strip("'") for aor in aors_filter.split(', ') if aor.strip("'")]
                
                office_list = []
                if offices_filter:
                    office_list = [office.strip("'") for office in offices_filter.split(', ') if office.strip("'")]
                
                # Determine which offices to filter by
                offices_to_filter = []
                
                if office_list:
                    # If specific offices are selected, use those
                    offices_to_filter = office_list
                    # print(f"🏢 Using explicitly selected offices: {office_list}")
                    
                elif aor_list:
                    # If AORs are selected but no specific offices, get all offices under those AORs
                    # Use existing office data 
                    
                    if df_offices is not None and not df_offices.empty:
                       
                        # Filter offices to selected AORs and get their office codes
                        if 'AorShortName' in df_offices.columns and 'OfficeCode' in df_offices.columns:
                            aor_offices = df_offices[df_offices['AorShortName'].isin(aor_list)]
                            offices_to_filter = aor_offices['OfficeCode'].unique().tolist()
                            # print(f"🎯 AOR-based filtering: Found {len(offices_to_filter)} offices for AORs {aor_list}")
                            # print(f"📋 Offices under selected AORs: {offices_to_filter}")
                        else:
                            print("⚠️ Office data missing required columns (AorShortName, OfficeCode)")
                    else:
                        print("⚠️ No office data available for AOR filtering")
                
                # Apply office filtering if we have offices to filter by
                if offices_to_filter:
                    df_filtered = df_filtered[df_filtered['OfficeCode'].isin(offices_to_filter)]
                    # print(f"🏢 Office filtering applied to ACTIVE MEMBERS: {len(df_filtered)} members for offices: {offices_to_filter}")
            
            # Count unique MemberIDs
            active_count = df_filtered['MemberID'].nunique()
            # print(f"👤 Filtered Active Members Count: {active_count}")
            
            return active_count
            
        except Exception as e:
            print(f"❌ Error filtering active members: {e}")
            return 0
    
    """
    Register callbacks for training summary cards
    """
    # print("Registering Training Summary Cards callbacks...")
    
    def parse_custom_datetime(date_str):
        """
        Parse custom datetime format: 'Feb-04-25@6 PM' -> datetime object
        """
        if not date_str or pd.isna(date_str):
            return None
            
        try:
            # Handle the custom format: "Feb-04-25@6 PM"
            if '@' in str(date_str):
                # Split date and time parts
                date_part, time_part = str(date_str).split('@')
                
                # Parse date part: "Feb-04-25" -> "Feb 04 2025"
                date_components = date_part.split('-')
                if len(date_components) == 3:
                    month_str, day_str, year_str = date_components
                    
                    # Convert 2-digit year to 4-digit year
                    year = int('20' + year_str) if len(year_str) == 2 else int(year_str)
                    
                    # Create a proper date string
                    formatted_date = f"{month_str} {day_str} {year}"
                    
                    # Parse time part: "6 PM" -> "18:00"
                    time_str = time_part.strip()
                    
                    # Combine and parse
                    full_datetime_str = f"{formatted_date} {time_str}"
                    return pd.to_datetime(full_datetime_str, format='%b %d %Y %I %p')
            
            # Fallback: try standard datetime parsing
            return pd.to_datetime(date_str, errors='coerce')
            
        except Exception as e:
            print(f"⚠️ Error parsing date '{date_str}': {e}")
            return None
    
    # Show locations spinner when filters change
    @app.callback(
         [Output("total-classes-spinner", "style", allow_duplicate=True),
         Output("total-attendances-spinner", "style", allow_duplicate=True),
         Output("total-requests-spinner", "style", allow_duplicate=True),
         Output("active-members-spinner", "style", allow_duplicate=True)],
        [Input("training-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    def show_summary_card_spinners(query_selectionss):
        """Show summary cards spinner when filter selections change"""
        return (
                {"visibility": "block", "position": "absolute", "top": "10px", "right": "10px"},
                {"visibility": "block", "position": "absolute", "top": "10px", "right": "10px"},
                {"visibility": "block", "position": "absolute", "top": "10px", "right": "10px"},
                {"visibility": "block", "position": "absolute", "top": "10px", "right": "10px"}
        )
        
    @app.callback(
        [Output("total-classes-card", "children"),
         Output("total-attendances-card", "children"),
         Output("total-requests-card", "children"),
         Output("active-members-card", "children"),
         Output("total-classes-spinner", "style"),
         Output("total-attendances-spinner", "style"),
         Output("total-requests-spinner", "style"),
         Output("active-members-spinner", "style")],
        [Input("training-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    def update_training_summary_cards(query_selections):
        """
        Update summary cards with filtered training data
        """
        # Default values
        default_values = ["0", "0", "0%", "0"]
        
        base_data = fetch_base_data()
        
        try:
            df_classes = base_data.get('classes', pd.DataFrame()).copy()
            # print(f"📊 Total classes before filtering: {len(df_classes)}")
            df_attendance = base_data.get('attendance_stats', pd.DataFrame()).copy()
            df_requests = base_data.get('request_stats', pd.DataFrame()).copy()
            
            # Apply filters based on query_selections
            if query_selections and isinstance(query_selections, dict):
                # Parse AOR filter once for reuse
                aors_filter = query_selections.get('AORs', '')
                aor_list = []
                if aors_filter:
                    aor_list = [aor.strip("'") for aor in aors_filter.split(', ') if aor.strip("'")]
                # Filter classes by AOR 
                if aor_list and not df_classes.empty and 'AorShortName' in df_classes.columns:
                    df_classes = df_classes[df_classes['AorShortName'].isin(aor_list)]
                    # print(f"🎯 AOR filtering applied to CLASSES: {len(df_classes)} classes for AORs: {aor_list}")
                
                # Filter classes by date range with custom parsing
                if not df_classes.empty and 'StartTime' in df_classes.columns:
                    # print("🔍 Parsing custom datetime format for classes...")
                    
                    # Parse custom datetime format
                    df_classes['ParsedStartTime'] = df_classes['StartTime'].apply(parse_custom_datetime)
                    
                    # Filter out rows where parsing failed
                    df_classes = df_classes.dropna(subset=['ParsedStartTime'])
                    start_date = query_selections.get('Day_From')
                    end_date = query_selections.get('Day_To')
                    
                    if start_date and end_date:
                        try:
                            start_date = pd.to_datetime(start_date)
                            end_date = pd.to_datetime(end_date)
                            
                            # Apply date filter using parsed datetime
                            df_classes = df_classes[
                                (df_classes['ParsedStartTime'] >= start_date) & 
                                (df_classes['ParsedStartTime'] <= end_date)
                            ]
                            # print(f"📅 Date filtering applied to CLASSES: {len(df_classes)} classes between {start_date.date()} and {end_date.date()}")

                            # print(f"Number of classes after date filtering: {len(df_classes)}")
                            
                        except Exception as e:
                            print(f"❌ Error applying date filter to classes: {e}")
                
                # Filter classes by Topics (if classes have TopicId)
                topics_filter = query_selections.get('Topics', '')
                if topics_filter and not df_classes.empty:
                    topic_list = [topic.strip("'") for topic in topics_filter.split(', ') if topic.strip("'")]
                    if topic_list:
                        try:
                            topic_ids = [str(topic) for topic in topic_list]
                            if 'TopicId' in df_classes.columns:
                                df_classes = df_classes[df_classes['TopicId'].isin(topic_ids)]
                                # print(f"📚 Topic filtering applied to CLASSES: {len(df_classes)} classes for topics: {topic_ids}")
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Error filtering classes by topics: {e}")
                
                # Filter classes by Instructors (if classes have InstructorId)
                instructors_filter = query_selections.get('Instructors', '')
                if instructors_filter and not df_classes.empty:
                    instructor_list = [inst.strip("'") for inst in instructors_filter.split(', ') if inst.strip("'")]
                    if instructor_list:
                        try:
                            instructor_ids = [str(inst) for inst in instructor_list]
                            if 'InstructorId' in df_classes.columns:
                                df_classes = df_classes[df_classes['InstructorId'].isin(instructor_ids)]
                                # print(f"👨‍🏫 Instructor filtering applied to CLASSES: {len(df_classes)} classes for instructors: {instructor_ids}")
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Error filtering classes by instructors: {e}")
                
                # Filter classes by Locations (if classes have LocationId)
                locations_filter = query_selections.get('Locations', '')
                if locations_filter and not df_classes.empty:
                    location_list = [loc.strip("'") for loc in locations_filter.split(', ') if loc.strip("'")]
                    if location_list:
                        try:
                            location_ids = [str(loc) for loc in location_list]
                            if 'LocationId' in df_classes.columns:
                                df_classes = df_classes[df_classes['LocationId'].isin(location_ids)]
                                # print(f"📍 Location filtering applied to CLASSES: {len(df_classes)} classes for locations: {location_ids}")
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Error filtering classes by locations: {e}")
                
                # Filter classes by Classes (if classes have ClassId)
                classes_filter = query_selections.get('Classes', '')
                if classes_filter and not df_classes.empty:
                    class_list = [cls.strip("'") for cls in classes_filter.split(', ') if cls.strip("'")]
                    if class_list:
                        try:
                            class_ids = [str(cls) for cls in class_list]
                            if 'ClassId' in df_classes.columns:
                                df_classes = df_classes[df_classes['ClassId'].isin(class_ids)]
                                # print(f"🏫 Class filtering applied to CLASSES: {len(df_classes)} classes for classes: {class_ids}")
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Error filtering classes by classes: {e}")    

                # Filter attendance by AOR (existing logic)
                if aor_list and not df_attendance.empty:
                    df_attendance = df_attendance[df_attendance['AorShortName'].isin(aor_list)]
                    # print(f"🎯 AOR filtering applied to ATTENDANCE: {len(df_attendance)} attendance records for AORs: {aor_list}")
                
                # Filter attendance by Office
                offices_filter = query_selections.get('Offices', '')
                if offices_filter and not df_attendance.empty:
                    office_list = [office.strip("'") for office in offices_filter.split(', ') if office.strip("'")]
                    if office_list:
                        df_attendance = df_attendance[df_attendance['MemberOffice'].isin(office_list)]
                        # print(f"🏢 Office filtering applied to ATTENDANCE: {len(df_attendance)} attendance records for offices: {office_list}")
                
                # Filter attendance by Topics
                if topics_filter and not df_attendance.empty:
                    topic_list = [topic.strip("'") for topic in topics_filter.split(', ') if topic.strip("'")]
                    if topic_list:
                        try:
                            topic_ids = [str(topic) for topic in topic_list]
                            df_attendance = df_attendance[df_attendance['TrainingTopicId'].isin(topic_ids)]
                            # print(f"📚 Topic filtering applied to ATTENDANCE: {len(df_attendance)} attendance records for topics: {topic_ids}")
                        except (ValueError, TypeError):
                            df_attendance = df_attendance[df_attendance['TrainingTopicId'].astype(str).isin(topic_list)]
                            # print(f"📚 Topic filtering applied to ATTENDANCE (as strings): {len(df_attendance)} attendance records")
                
                # Filter attendance by Instructors
                if instructors_filter and not df_attendance.empty:
                    instructor_list = [inst.strip("'") for inst in instructors_filter.split(', ') if inst.strip("'")]
                    if instructor_list:
                        try:
                            instructor_ids = [str(inst) for inst in instructor_list]
                            df_attendance = df_attendance[df_attendance['InstructorId'].isin(instructor_ids)]
                            # print(f"👨‍🏫 Instructor filtering applied to ATTENDANCE: {len(df_attendance)} attendance records for instructors: {instructor_ids}")
                        except (ValueError, TypeError):
                            df_attendance = df_attendance[df_attendance['InstructorId'].astype(str).isin(instructor_list)]
                            # print(f"👨‍🏫 Instructor filtering applied to ATTENDANCE (as strings): {len(df_attendance)} attendance records")
                
                # Filter attendance by Locations
                if locations_filter and not df_attendance.empty:
                    location_list = [loc.strip("'") for loc in locations_filter.split(', ') if loc.strip("'")]
                    if location_list:
                        try:
                            location_ids = [str(loc) for loc in location_list]
                            df_attendance = df_attendance[df_attendance['LocationId'].isin(location_ids)]
                            # print(f"📍 Location filtering applied to ATTENDANCE: {len(df_attendance)} attendance records for locations: {location_ids}")
                        except (ValueError, TypeError):
                            df_attendance = df_attendance[df_attendance['LocationId'].astype(str).isin(location_list)]
                            # print(f"📍 Location filtering applied to ATTENDANCE (as strings): {len(df_attendance)} attendance records")
                
                # Apply filters to requests data
                if not df_requests.empty:
                    df_requests_filtered = df_requests.copy()
                    
                    if aor_list:
                        df_requests_filtered = df_requests_filtered[df_requests_filtered['AorShortName'].isin(aor_list)]
                        # print(f"🎯 AOR filtering applied to REQUESTS: {len(df_requests_filtered)} request records")
                    
                    offices_filter = query_selections.get('Offices', '')
                    if offices_filter:
                        office_list = [office.strip("'") for office in offices_filter.split(', ') if office.strip("'")]
                        if office_list:
                            df_requests_filtered = df_requests_filtered[df_requests_filtered['MemberOffice'].isin(office_list)]
                            # print(f"🏢 Office filtering applied to REQUESTS: {len(df_requests_filtered)} request records")
                else:
                    df_requests_filtered = df_requests
            
            # Calculate summary metrics
            
            # 1. Total Classes 
            total_classes = len(df_classes) if not df_classes.empty else 0
            
            # 2. Total Attendances (sum from attendance stats)
            if not df_attendance.empty and 'TotalAttendances' in df_attendance.columns:
                total_attendances = df_attendance['TotalAttendances'].sum()
            else:
                # Fallback: count attendance records
                total_attendances = len(df_attendance)

            # 3. 2. Total Requests (sum from request stats)
            if not df_requests_filtered.empty and 'TotalRequests' in df_requests_filtered.columns:
                total_requests = df_requests_filtered['TotalRequests'].sum()
            else:
                # Fallback: count request records
                total_requests = len(df_requests_filtered)
        
            # 4. Active Members (unique members with attendance)
            active_members = calculate_active_members_count(base_data.get('active_members', pd.DataFrame()), query_selections, base_data.get('offices', pd.DataFrame()))            
            
            # Format the values for display
            total_classes_formatted = f"{total_classes:,}"
            total_attendances_formatted = f"{int(total_attendances):,}"
            total_requests_formatted = f"{int(total_requests):,}"
            active_members_formatted = f"{active_members:,}"
            
            # print(f"📊 Summary Cards Updated: Classes={total_classes}, Attendances={int(total_attendances)}, Requests={total_requests}, Members={active_members}")
            
            return [
                total_classes_formatted,
                total_attendances_formatted, 
                total_requests_formatted,
                active_members_formatted,
                {"visibility": "hidden"},
                {"visibility": "hidden"},
                {"visibility": "hidden"},
                {"visibility": "hidden"}
            ]
            
        except Exception as e:
            print(f"❌ Error updating summary cards: {e}")
            return default_values