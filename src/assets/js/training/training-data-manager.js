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
        const sharedDataTypes = ['aors', 'offices']; // These are common across all dashboards
        return sharedDataTypes.includes(key);
    }

    // Training-specific helper methods
    getFilteredTopics(selectedAors, selectedOffices) {
        const topics = this.getData('topics');
        const requestStats = this.getData('request_stats');
        const attendanceStats = this.getData('attendance_stats');
        
        // Filter stats by AOR and Office
        let filteredRequestStats = FilterUtils.filterByAors(requestStats, selectedAors);
        filteredRequestStats = FilterUtils.filterByOffices(filteredRequestStats, selectedOffices);
        
        let filteredAttendanceStats = FilterUtils.filterByAors(attendanceStats, selectedAors);
        filteredAttendanceStats = FilterUtils.filterByOffices(filteredAttendanceStats, selectedOffices);
        
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
        
        // Filter attendance stats
        let filteredStats = FilterUtils.filterByAors(attendanceStats, selectedAors);
        filteredStats = FilterUtils.filterByOffices(filteredStats, selectedOffices);
        
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
        
        // Apply all filters to attendance stats
        let filteredStats = FilterUtils.filterByAors(attendanceStats, selectedAors);
        filteredStats = FilterUtils.filterByOffices(filteredStats, selectedOffices);
        
        // Filter by topics
        if (Array.isArray(selectedTopics) && selectedTopics.length > 0 && !selectedTopics.includes("All")) {
            filteredStats = filteredStats.filter(stat => 
                selectedTopics.includes(String(stat.TrainingTopicId))
            );
        }
        
        // Filter by instructors
        if (Array.isArray(selectedInstructors) && selectedInstructors.length > 0 && !selectedInstructors.includes("All")) {
            filteredStats = filteredStats.filter(stat => 
                selectedInstructors.includes(String(stat.InstructorId))
            );
        }
        
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
        
        // Apply filters to classes directly
        if (Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")) {
            filteredClasses = filteredClasses.filter(c => selectedAors.includes(c.AorShortName));
        }
        
        if (Array.isArray(selectedInstructors) && selectedInstructors.length > 0 && !selectedInstructors.includes("All")) {
            filteredClasses = filteredClasses.filter(c => selectedInstructors.includes(String(c.InstructorId)));
        }
        
        if (Array.isArray(selectedLocations) && selectedLocations.length > 0 && !selectedLocations.includes("All")) {
            filteredClasses = filteredClasses.filter(c => selectedLocations.includes(String(c.LocationId)));
        }
        
        if (Array.isArray(selectedTopics) && selectedTopics.length > 0 && !selectedTopics.includes("All")) {
            filteredClasses = filteredClasses.filter(c => selectedTopics.includes(String(c.TopicId)));
        }
        
        // Additional filtering by office through attendance stats
        if (Array.isArray(selectedOffices) && selectedOffices.length > 0 && !selectedOffices.includes("All")) {
            let filteredStats = FilterUtils.filterByOffices(attendanceStats, selectedOffices);
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