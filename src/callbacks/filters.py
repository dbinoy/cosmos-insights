from dash.dependencies import Input, Output, State
from dash import clientside_callback
import pandas as pd
import textwrap
import time
from datetime import datetime
from src.utils.db import run_queries

def register_training_filter_callbacks(app):
    
    # Single callback to initialize all data and cache
    @app.callback(
        Output("training-all-data-store", "data"),
        Input("training-filtered-query-store", "id"),
        prevent_initial_call=False
    )
    def load_all_training_data(_):
        """Load all training data in a single callback for efficiency"""
        print("Loading all training data...")
        
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
            print(f"Loaded {len(all_data[key])} {key} records")
        
        return all_data

    # Enhanced modular cache system with all data management
    app.clientside_callback(
        """
        async function(server_data) {
            console.log('🚀 Training Data Cache System Initializing...');
            
            const CACHE_TTL = 60 * 60 * 1000; // 30 minutes
            const DB_NAME = 'TrainingDataCache';
            const DB_VERSION = 1;
            const STORE_NAME = 'training_data';
            
            // ===== INDEXEDDB UTILITIES =====
            const IndexedDBManager = {
                async init() {
                    return new Promise((resolve, reject) => {
                        const request = indexedDB.open(DB_NAME, DB_VERSION);
                        
                        request.onerror = () => {
                            console.error('❌ IndexedDB open failed:', request.error);
                            reject(request.error);
                        };
                        
                        request.onsuccess = () => {
                            console.log('✅ IndexedDB opened successfully');
                            resolve(request.result);
                        };
                        
                        request.onupgradeneeded = (event) => {
                            console.log('🔄 IndexedDB upgrade needed');
                            const db = event.target.result;
                            
                            if (!db.objectStoreNames.contains(STORE_NAME)) {
                                const store = db.createObjectStore(STORE_NAME, { keyPath: 'key' });
                                store.createIndex('timestamp', 'timestamp', { unique: false });
                                store.createIndex('dataType', 'dataType', { unique: false });
                                console.log('📦 IndexedDB store created');
                            }
                        };
                    });
                },
                
                async get(key) {
                    try {
                        const db = await this.init();
                        const transaction = db.transaction([STORE_NAME], 'readonly');
                        const store = transaction.objectStore(STORE_NAME);
                        
                        return new Promise((resolve) => {
                            const request = store.get(key);
                            request.onsuccess = () => {
                                const result = request.result;
                                if (!result) {
                                    console.log(`📭 No cache found for: ${key}`);
                                    resolve(null);
                                    return;
                                }
                                
                                const now = Date.now();
                                const age = now - result.timestamp;
                                
                                if (age > CACHE_TTL) {
                                    console.log(`⏰ Cache expired for: ${key} (${Math.round(age/1000/60)} min old)`);
                                    this.delete(key);
                                    resolve(null);
                                    return;
                                }
                                
                                console.log(`✅ Cache hit for: ${key} (${Math.round(age/1000/60)} min old, ${result.value.length} records)`);
                                resolve(result.value);
                            };
                            request.onerror = () => resolve(null);
                        });
                    } catch (e) {
                        console.warn(`⚠️ IndexedDB read error for ${key}:`, e);
                        return null;
                    }
                },
                
                async set(key, value, dataType = 'training') {
                    try {
                        const db = await this.init();
                        const transaction = db.transaction([STORE_NAME], 'readwrite');
                        const store = transaction.objectStore(STORE_NAME);
                        
                        const data = {
                            key,
                            value,
                            timestamp: Date.now(),
                            dataType,
                            size: JSON.stringify(value).length
                        };
                        
                        return new Promise((resolve) => {
                            const request = store.put(data);
                            request.onsuccess = () => {
                                const sizeMB = Math.round(data.size / 1024 / 1024 * 100) / 100;
                                console.log(`💾 Cached: ${key} (${value.length} records, ${sizeMB}MB)`);
                                resolve(true);
                            };
                            request.onerror = () => {
                                console.error(`❌ Cache write failed for ${key}:`, request.error);
                                resolve(false);
                            };
                        });
                    } catch (e) {
                        console.error(`❌ IndexedDB write error for ${key}:`, e);
                        return false;
                    }
                },
                
                async delete(key) {
                    try {
                        const db = await this.init();
                        const transaction = db.transaction([STORE_NAME], 'readwrite');
                        const store = transaction.objectStore(STORE_NAME);
                        store.delete(key);
                    } catch (e) {
                        console.warn(`Warning: Could not delete ${key}:`, e);
                    }
                },
                
                async clear() {
                    try {
                        const db = await this.init();
                        const transaction = db.transaction([STORE_NAME], 'readwrite');
                        const store = transaction.objectStore(STORE_NAME);
                        store.clear();
                        console.log('🗑️ Cache cleared');
                    } catch (e) {
                        console.warn('Warning: Could not clear cache:', e);
                    }
                }
            };
            
            // ===== DATA MANAGER =====
            const TrainingDataManager = {
                dataKeys: ['aors', 'offices', 'topics', 'instructors', 'locations', 'classes', 'request_stats', 'attendance_stats'],
                cache: {},
                
                async loadAllData() {
                    console.log('📡 Loading all training data...');
                    const results = {};
                    let cacheHits = 0;
                    let serverLoads = 0;
                    
                    // Check cache for all data types
                    for (const key of this.dataKeys) {
                        const cached = await IndexedDBManager.get(key);
                        if (cached && cached.length > 0) {
                            results[key] = cached;
                            this.cache[key] = cached;
                            cacheHits++;
                        }
                    }
                    
                    // If we have server data, cache it and use it
                    if (server_data && typeof server_data === 'object') {
                        for (const key of this.dataKeys) {
                            if (server_data[key] && server_data[key].length > 0) {
                                results[key] = server_data[key];
                                this.cache[key] = server_data[key];
                                
                                // Cache in background
                                IndexedDBManager.set(key, server_data[key]).catch(e => 
                                    console.warn(`Failed to cache ${key}:`, e)
                                );
                                serverLoads++;
                            }
                        }
                    }
                    
                    console.log(`📊 Data loading complete: ${cacheHits} from cache, ${serverLoads} from server`);
                    return results;
                },
                
                getData(key) {
                    return this.cache[key] || [];
                },
                
                isReady() {
                    return this.dataKeys.every(key => this.cache[key] && this.cache[key].length > 0);
                }
            };
            
            // ===== FILTER UTILITIES =====
            const FilterUtils = {
                filterByAors(data, selectedAors) {
                    if (!Array.isArray(selectedAors) || selectedAors.length === 0 || selectedAors.includes("All")) {
                        return data;
                    }
                    return data.filter(item => selectedAors.includes(item.AorShortName));
                },
                
                filterByOffices(data, selectedOffices) {
                    if (!Array.isArray(selectedOffices) || selectedOffices.length === 0 || selectedOffices.includes("All")) {
                        return data;
                    }
                    return data.filter(item => selectedOffices.includes(item.MemberOffice || item.OfficeCode));
                },
                
                getUniqueIds(data, field) {
                    return [...new Set(data.map(item => item[field]).filter(Boolean))];
                },
                
                createOptions(data, labelField, valueField, allLabel = "All") {
                    if (!data || data.length === 0) return [];
                    
                    const options = [{label: allLabel, value: "All"}];
                    return options.concat(
                        data.map(item => ({
                            label: item[labelField],
                            value: String(item[valueField])
                        }))
                    );
                }
            };
            
            // Initialize data
            const allData = await TrainingDataManager.loadAllData();
            
            // Make utilities globally available
            window.trainingDataManager = TrainingDataManager;
            window.trainingFilterUtils = FilterUtils;
            window.trainingIndexedDB = IndexedDBManager;
            
            console.log('🎉 Training Data Cache System Ready!');
            console.log('📋 Available datasets:', Object.keys(allData));
            
            return {
                ready: true,
                data: allData,
                timestamp: Date.now()
            };
        }
        """,
        Output("training-data-ready", "data"),
        Input("training-all-data-store", "data"),
        prevent_initial_call=False
    )

    # Simplified date range initialization
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

    # Unified spinner control
    app.clientside_callback(
        """
        function(data_ready) {
            const isReady = data_ready && data_ready.ready;
            const hideStyle = {"display": "none"};
            const showStyle = {"position": "absolute", "top": "30px", "right": "30px"};
            
            if (isReady) {
                return [
                    hideStyle, "Select AOR(s)...",
                    hideStyle, "Select Office(s)...",
                    hideStyle, "Select Topic(s)...",
                    hideStyle, "Select Instructor(s)...",
                    hideStyle, "Select Location(s)...",
                    hideStyle, "Select Class(es)..."
                ];
            } else {
                return [
                    showStyle, "Loading AORs...",
                    showStyle, "Loading Offices...",
                    showStyle, "Loading Topics...",
                    showStyle, "Loading Instructors...",
                    showStyle, "Loading Locations...",
                    showStyle, "Loading Classes..."
                ];
            }
        }
        """,
        [Output("training-aor-spinner", "spinner_style"), Output("training-aor-dropdown", "placeholder"),
         Output("training-office-spinner", "spinner_style"), Output("training-office-dropdown", "placeholder"),
         Output("training-topics-spinner", "spinner_style"), Output("training-topics-dropdown", "placeholder"),
         Output("training-instructor-spinner", "spinner_style"), Output("training-instructor-dropdown", "placeholder"),
         Output("training-location-spinner", "spinner_style"), Output("training-location-dropdown", "placeholder"),
         Output("training-class-spinner", "spinner_style"), Output("training-class-dropdown", "placeholder")],
        Input("training-data-ready", "data"),
        prevent_initial_call=False
    )

    # AOR dropdown - simplified
    app.clientside_callback(
        """
        function(data_ready) {
            if (!data_ready || !data_ready.ready || !window.trainingDataManager) {
                return [];
            }
            
            const aors = window.trainingDataManager.getData('aors');
            return window.trainingFilterUtils.createOptions(
                aors, 
                'AorShortName', 
                'AorShortName', 
                'All AORs'
            );
        }
        """,
        Output("training-aor-dropdown", "options"),
        Input("training-data-ready", "data"),
        prevent_initial_call=False
    )

    # Office dropdown - filtered by AOR
    app.clientside_callback(
        """
        function(selected_aors, data_ready) {
            if (!data_ready || !data_ready.ready || !window.trainingDataManager) {
                return [];
            }
            
            let offices = window.trainingDataManager.getData('offices');
            
            // Filter by selected AORs
            if (Array.isArray(selected_aors) && selected_aors.length > 0 && !selected_aors.includes("All")) {
                offices = offices.filter(office => selected_aors.includes(office.AorShortName));
            }
            
            const label = Array.isArray(selected_aors) && selected_aors.length > 0 && !selected_aors.includes("All")
                ? `All ${selected_aors.join(',')} Offices`
                : 'All Offices';
                
            return window.trainingFilterUtils.createOptions(
                offices.map(o => ({label: `${o.AorShortName} - ${o.OfficeCode}`, value: o.OfficeCode})),
                'label',
                'value',
                label
            );
        }
        """,
        Output("training-office-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    # Topics dropdown - filtered by AOR and Office
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, data_ready) {
            if (!data_ready || !data_ready.ready || !window.trainingDataManager) {
                return [];
            }
            
            const topics = window.trainingDataManager.getData('topics');
            const requestStats = window.trainingDataManager.getData('request_stats');
            const attendanceStats = window.trainingDataManager.getData('attendance_stats');
            
            // Filter stats by AOR and Office
            let filteredRequestStats = window.trainingFilterUtils.filterByAors(requestStats, selected_aors);
            filteredRequestStats = window.trainingFilterUtils.filterByOffices(filteredRequestStats, selected_offices);
            
            let filteredAttendanceStats = window.trainingFilterUtils.filterByAors(attendanceStats, selected_aors);
            filteredAttendanceStats = window.trainingFilterUtils.filterByOffices(filteredAttendanceStats, selected_offices);
            
            // Get unique topic IDs from filtered stats
            const topicIds = new Set([
                ...window.trainingFilterUtils.getUniqueIds(filteredRequestStats, 'TrainingTopicId'),
                ...window.trainingFilterUtils.getUniqueIds(filteredAttendanceStats, 'TrainingTopicId')
            ]);
            
            // Filter topics by available topic IDs
            const filteredTopics = topics.filter(topic => topicIds.has(topic.TopicId));
            
            return window.trainingFilterUtils.createOptions(
                filteredTopics,
                'TopicName',
                'TopicId',
                'All Topics'
            );
        }
        """,
        Output("training-topics-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), 
         Input("training-office-dropdown", "value"), 
         Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    # Instructors dropdown
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, data_ready) {
            if (!data_ready || !data_ready.ready || !window.trainingDataManager) {
                return [];
            }
            
            const instructors = window.trainingDataManager.getData('instructors');
            const attendanceStats = window.trainingDataManager.getData('attendance_stats');
            
            // Filter attendance stats
            let filteredStats = window.trainingFilterUtils.filterByAors(attendanceStats, selected_aors);
            filteredStats = window.trainingFilterUtils.filterByOffices(filteredStats, selected_offices);
            
            // Get unique instructor IDs
            const instructorIds = new Set(window.trainingFilterUtils.getUniqueIds(filteredStats, 'InstructorId'));
            
            // Filter instructors
            const filteredInstructors = instructors.filter(instructor => 
                instructorIds.size === 0 || instructorIds.has(instructor.InstructorID)
            );
            
            return window.trainingFilterUtils.createOptions(
                filteredInstructors,
                'Name',
                'InstructorID',
                'All Instructors'
            );
        }
        """,
        Output("training-instructor-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), 
         Input("training-office-dropdown", "value"), 
         Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    # Locations dropdown
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, selected_topics, selected_instructors, data_ready) {
            if (!data_ready || !data_ready.ready || !window.trainingDataManager) {
                return [];
            }
            
            const locations = window.trainingDataManager.getData('locations');
            const attendanceStats = window.trainingDataManager.getData('attendance_stats');
            
            // Apply all filters to attendance stats
            let filteredStats = window.trainingFilterUtils.filterByAors(attendanceStats, selected_aors);
            filteredStats = window.trainingFilterUtils.filterByOffices(filteredStats, selected_offices);
            
            // Filter by topics
            if (Array.isArray(selected_topics) && selected_topics.length > 0 && !selected_topics.includes("All")) {
                filteredStats = filteredStats.filter(stat => 
                    selected_topics.includes(String(stat.TrainingTopicId))
                );
            }
            
            // Filter by instructors
            if (Array.isArray(selected_instructors) && selected_instructors.length > 0 && !selected_instructors.includes("All")) {
                filteredStats = filteredStats.filter(stat => 
                    selected_instructors.includes(String(stat.InstructorId))
                );
            }
            
            // Get unique location IDs
            const locationIds = new Set(window.trainingFilterUtils.getUniqueIds(filteredStats, 'LocationId'));
            
            // Filter locations
            const filteredLocations = locations.filter(location => 
                locationIds.size === 0 || locationIds.has(location.LocationID)
            );
            
            return window.trainingFilterUtils.createOptions(
                filteredLocations,
                'Name',
                'LocationID',
                'All Locations'
            );
        }
        """,
        Output("training-location-dropdown", "options"),
        [Input("training-aor-dropdown", "value"), 
         Input("training-office-dropdown", "value"),
         Input("training-topics-dropdown", "value"),
         Input("training-instructor-dropdown", "value"),
         Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    # Classes dropdown
    app.clientside_callback(
        """
        function(selected_aors, selected_offices, selected_instructors, selected_locations, selected_topics, data_ready) {
            if (!data_ready || !data_ready.ready || !window.trainingDataManager) {
                return [];
            }
            
            const classes = window.trainingDataManager.getData('classes');
            const attendanceStats = window.trainingDataManager.getData('attendance_stats');
            const topics = window.trainingDataManager.getData('topics');
            
            let filteredClasses = classes;
            
            // Apply filters to classes directly
            if (Array.isArray(selected_aors) && selected_aors.length > 0 && !selected_aors.includes("All")) {
                filteredClasses = filteredClasses.filter(c => selected_aors.includes(c.AorShortName));
            }
            
            if (Array.isArray(selected_instructors) && selected_instructors.length > 0 && !selected_instructors.includes("All")) {
                filteredClasses = filteredClasses.filter(c => selected_instructors.includes(String(c.InstructorId)));
            }
            
            if (Array.isArray(selected_locations) && selected_locations.length > 0 && !selected_locations.includes("All")) {
                filteredClasses = filteredClasses.filter(c => selected_locations.includes(String(c.LocationId)));
            }
            
            if (Array.isArray(selected_topics) && selected_topics.length > 0 && !selected_topics.includes("All")) {
                filteredClasses = filteredClasses.filter(c => selected_topics.includes(String(c.TopicId)));
            }
            
            // Additional filtering by office through attendance stats
            if (Array.isArray(selected_offices) && selected_offices.length > 0 && !selected_offices.includes("All")) {
                let filteredStats = window.trainingFilterUtils.filterByOffices(attendanceStats, selected_offices);
                const classIds = new Set(window.trainingFilterUtils.getUniqueIds(filteredStats, 'TrainingClassId'));
                filteredClasses = filteredClasses.filter(c => classIds.has(c.ClassId));
            }
            
            if (filteredClasses.length === 0) {
                return [{label: "No classes found", value: "", disabled: true}];
            }
            
            // Create label for "All" option
            let allLabel = "All";
            if (Array.isArray(selected_topics) && selected_topics.length > 0 && !selected_topics.includes("All") && topics) {
                const selectedTopicNames = topics
                    .filter(t => selected_topics.includes(String(t.TopicId)))
                    .map(t => t.TopicName);
                allLabel += ` ${selectedTopicNames.join(',')}`;
            }
            allLabel += " Classes";
            
            const options = [{label: allLabel, value: "All"}];
            return options.concat(
                filteredClasses.map(c => ({
                    label: `${c.ClassName}: ${c.StartTime}`,
                    value: c.ClassId
                }))
            );
        }
        """,
        Output("training-class-dropdown", "options"),
        [Input("training-aor-dropdown", "value"),
         Input("training-office-dropdown", "value"),
         Input("training-instructor-dropdown", "value"),
         Input("training-location-dropdown", "value"),
         Input("training-topics-dropdown", "value"),
         Input("training-data-ready", "data")],
        prevent_initial_call=False
    )

    # Clear filters callback
    @app.callback(
        [Output("training-date-range-picker", "start_date"),
         Output("training-date-range-picker", "end_date"),
         Output("training-aor-dropdown", "value"),
         Output("training-office-dropdown", "value"),
         Output("training-topics-dropdown", "value"),
         Output("training-instructor-dropdown", "value"),
         Output("training-location-dropdown", "value"),
         Output("training-class-dropdown", "value")],
        Input("training-clear-filters-btn", "n_clicks"),
        prevent_initial_call=True,
        allow_duplicate=True
    )
    def clear_all_filters(n_clicks):
        date_start_default = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        date_end_default = datetime.today().date()  
        return date_start_default, date_end_default, [], [], [], [], [], []