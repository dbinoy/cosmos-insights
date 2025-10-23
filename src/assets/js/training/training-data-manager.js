/**
 * Training Data Manager
 * Extends DataManager for training-specific functionality
 */

class TrainingDataManager extends DataManager {
    constructor() {
        super('TRAINING');
        this.dataKeys = [
            'aors', 'offices', 'topics', 'instructors', 
            'locations', 'classes', 'request_stats', 'attendance_stats'
        ];
    }

    // Define which data types are shared across dashboards
    isSharedData(key) {
        // No shared data types for training - store everything in TRAINING database
        return false;
    }

    // Static method for callback initialization - keeps Python file clean
    static async initializeTrainingSystem(server_data) {
        // Initialize data manager and cache system
        const dataManager = new TrainingDataManager();
        const result = await dataManager.initializeSystem(server_data);
        
        // Make globally available for other callbacks
        window.trainingDataManager = dataManager;
        
        return result;
    }

    // Training-specific helper methods using TrainingFilterUtils
    getFilteredTopics(selectedAors, selectedOffices) {
        const topics = this.getData('topics');
        const requestStats = this.getData('request_stats');
        const attendanceStats = this.getData('attendance_stats');
        
        // Filter stats by AOR and Office using training-specific filters
        let filteredRequestStats = TrainingFilterUtils.filterByAors(requestStats, selectedAors);
        filteredRequestStats = TrainingFilterUtils.filterByOffices(filteredRequestStats, selectedOffices);
        
        let filteredAttendanceStats = TrainingFilterUtils.filterByAors(attendanceStats, selectedAors);
        filteredAttendanceStats = TrainingFilterUtils.filterByOffices(filteredAttendanceStats, selectedOffices);
        
        // Get unique topic IDs from filtered stats
        const topicIds = new Set([
            ...FilterUtils.getUniqueIds(filteredRequestStats, 'TrainingTopicId'),
            ...FilterUtils.getUniqueIds(filteredAttendanceStats, 'TrainingTopicId')
        ]);
        
        // Filter topics by available topic IDs
        return topics.filter(topic => topicIds.has(topic.TopicId));
    }

    getFilteredInstructors(selectedAors, selectedOffices) {
        const instructors = this.getData('instructors');
        const attendanceStats = this.getData('attendance_stats');
        
        // Filter attendance stats using training-specific filters
        let filteredStats = TrainingFilterUtils.filterByAors(attendanceStats, selectedAors);
        filteredStats = TrainingFilterUtils.filterByOffices(filteredStats, selectedOffices);
        
        // Get unique instructor IDs
        const instructorIds = new Set(FilterUtils.getUniqueIds(filteredStats, 'InstructorId'));
        
        // Filter instructors
        return instructors.filter(instructor => 
            instructorIds.size === 0 || instructorIds.has(instructor.InstructorID)
        );
    }

    getFilteredLocations(selectedAors, selectedOffices, selectedTopics, selectedInstructors) {
        const locations = this.getData('locations');
        const attendanceStats = this.getData('attendance_stats');
        
        // Apply all filters to attendance stats using training-specific filters
        let filteredStats = TrainingFilterUtils.filterByAors(attendanceStats, selectedAors);
        filteredStats = TrainingFilterUtils.filterByOffices(filteredStats, selectedOffices);
        filteredStats = TrainingFilterUtils.filterByTopics(filteredStats, selectedTopics);
        filteredStats = TrainingFilterUtils.filterByInstructors(filteredStats, selectedInstructors);
        
        // Get unique location IDs
        const locationIds = new Set(FilterUtils.getUniqueIds(filteredStats, 'LocationId'));
        
        // Filter locations
        return locations.filter(location => 
            locationIds.size === 0 || locationIds.has(location.LocationID)
        );
    }

    getFilteredClasses(selectedAors, selectedOffices, selectedInstructors, selectedLocations, selectedTopics) {
        const classes = this.getData('classes');
        const attendanceStats = this.getData('attendance_stats');
        const topics = this.getData('topics');
        
        let filteredClasses = classes;
        
        // Apply filters to classes directly using training-specific filters
        filteredClasses = TrainingFilterUtils.filterByAors(filteredClasses, selectedAors);
        filteredClasses = TrainingFilterUtils.filterByInstructors(filteredClasses, selectedInstructors);
        filteredClasses = TrainingFilterUtils.filterByLocations(filteredClasses, selectedLocations);
        filteredClasses = TrainingFilterUtils.filterByTopics(filteredClasses, selectedTopics);
        
        // Additional filtering by office through attendance stats
        if (Array.isArray(selectedOffices) && selectedOffices.length > 0 && !selectedOffices.includes("All")) {
            let filteredStats = TrainingFilterUtils.filterByOffices(attendanceStats, selectedOffices);
            const classIds = new Set(FilterUtils.getUniqueIds(filteredStats, 'TrainingClassId'));
            filteredClasses = filteredClasses.filter(c => classIds.has(c.ClassId));
        }
        
        return {
            classes: filteredClasses,
            topics: topics // Return topics for label generation
        };
    }

    // Get training statistics
    getTrainingStats() {
        const stats = {
            totalClasses: this.getData('classes').length,
            totalInstructors: this.getData('instructors').length,
            totalTopics: this.getData('topics').length,
            totalLocations: this.getData('locations').length,
            totalRequestRecords: this.getData('request_stats').length,
            totalAttendanceRecords: this.getData('attendance_stats').length
        };
        
        return stats;
    }

    // Validate data integrity
    validateData() {
        const issues = [];
        
        // Check for required data
        this.dataKeys.forEach(key => {
            const data = this.getData(key);
            if (!data || data.length === 0) {
                issues.push(`Missing or empty data for: ${key}`);
            }
        });
        
        // Check for data relationships
        const classes = this.getData('classes');
        const topics = this.getData('topics');
        const instructors = this.getData('instructors');
        const locations = this.getData('locations');
        
        if (classes.length > 0 && topics.length > 0) {
            const classTopicIds = new Set(classes.map(c => c.TopicId));
            const availableTopicIds = new Set(topics.map(t => t.TopicId));
            const missingTopics = [...classTopicIds].filter(id => !availableTopicIds.has(id));
            
            if (missingTopics.length > 0) {
                issues.push(`Classes reference missing topics: ${missingTopics.join(', ')}`);
            }
        }
        
        return {
            valid: issues.length === 0,
            issues: issues
        };
    }
}

// Make globally available
window.TrainingDataManager = TrainingDataManager;