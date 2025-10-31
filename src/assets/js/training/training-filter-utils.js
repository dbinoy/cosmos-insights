/**
 * Training-Specific Filter Utilities
 * Handles training data structure and field names
 */

class TrainingFilterUtils {
    static filterByAors(data, selectedAors) {
        if (!Array.isArray(selectedAors) || selectedAors.length === 0 || selectedAors.includes("All")) {
            return data;
        }
        return data.filter(item => selectedAors.includes(item.AorShortName));
    }
    
    static filterByOffices(data, selectedOffices) {
        if (!Array.isArray(selectedOffices) || selectedOffices.length === 0 || selectedOffices.includes("All")) {
            return data;
        }
        return data.filter(item => selectedOffices.includes(item.MemberOffice || item.OfficeCode));
    }

    static filterByTopics(data, selectedTopics) {
        if (!Array.isArray(selectedTopics) || selectedTopics.length === 0 || selectedTopics.includes("All")) {
            return data;
        }
        return data.filter(item => selectedTopics.includes(String(item.TrainingTopicId || item.TopicId)));
    }

    static filterByInstructors(data, selectedInstructors) {
        if (!Array.isArray(selectedInstructors) || selectedInstructors.length === 0 || selectedInstructors.includes("All")) {
            return data;
        }
        return data.filter(item => selectedInstructors.includes(String(item.InstructorId || item.InstructorID)));
    }

    static filterByLocations(data, selectedLocations) {
        if (!Array.isArray(selectedLocations) || selectedLocations.length === 0 || selectedLocations.includes("All")) {
            return data;
        }
        return data.filter(item => selectedLocations.includes(String(item.LocationId || item.LocationID)));
    }

    static filterByClasses(data, selectedClasses) {
        if (!Array.isArray(selectedClasses) || selectedClasses.length === 0 || selectedClasses.includes("All")) {
            return data;
        }
        return data.filter(item => selectedClasses.includes(String(item.TrainingClassId || item.ClassId)));
    }

    // Training-specific spinner states with training dropdown placeholders
    static createTrainingSpinnerStates(isReady) {
        const loadingPlaceholders = [
            "Loading AORs...",
            "Loading Offices...", 
            "Loading Topics...",
            "Loading Instructors...",
            "Loading Locations...",
            "Loading Classes..."
        ];
        
        const readyPlaceholders = [
            "Select AOR(s)...",
            "Select Office(s)...",
            "Select Topic(s)...",
            "Select Instructor(s)...",
            "Select Location(s)...",
            "Select Class(es)..."
        ];
        
        return FilterUtils.createGenericSpinnerStates(isReady, loadingPlaceholders, readyPlaceholders);
    }

    // Clear all training filters - returns array of default values
    static clearAllTrainingFilters(n_clicks) {
        // Only execute if button was actually clicked
        if (!n_clicks) {
            // Return current values on initial load (prevent clearing on page load)
            return window.dash_clientside.no_update;
        }
        
        // Default date values
        const dateStartDefault = '2020-01-01';
        const dateEndDefault = new Date().toISOString().split('T')[0]; // Today's date in YYYY-MM-DD format
        
        // Clear all dropdown values
        const emptyArray = [];
        
        // console.log('🧹 Clearing all training filters via TrainingFilterUtils...');
        
        return [
            dateStartDefault,    // training-date-range-picker start_date
            dateEndDefault,      // training-date-range-picker end_date
            emptyArray,          // training-aor-dropdown value
            emptyArray,          // training-office-dropdown value
            emptyArray,          // training-topics-dropdown value
            emptyArray,          // training-instructor-dropdown value
            emptyArray,          // training-location-dropdown value
            emptyArray           // training-class-dropdown value
        ];
    }

    // Alternative method that returns an object for more flexibility
    static getDefaultFilterValues() {
        const dateStartDefault = '2020-01-01';
        const dateEndDefault = new Date().toISOString().split('T')[0];
        
        return {
            startDate: dateStartDefault,
            endDate: dateEndDefault,
            aors: [],
            offices: [],
            topics: [],
            instructors: [],
            locations: [],
            classes: []
        };
    }

    // Utility to apply all training filters at once
    static applyAllFilters(data, filters) {
        let filteredData = data;
        
        if (filters.aors) {
            filteredData = this.filterByAors(filteredData, filters.aors);
        }
        
        if (filters.offices) {
            filteredData = this.filterByOffices(filteredData, filters.offices);
        }
        
        if (filters.topics) {
            filteredData = this.filterByTopics(filteredData, filters.topics);
        }
        
        if (filters.instructors) {
            filteredData = this.filterByInstructors(filteredData, filters.instructors);
        }
        
        if (filters.locations) {
            filteredData = this.filterByLocations(filteredData, filters.locations);
        }
        
        if (filters.classes) {
            filteredData = this.filterByClasses(filteredData, filters.classes);
        }
        
        if (filters.dateRange && filters.dateRange.start && filters.dateRange.end) {
            filteredData = FilterUtils.filterByDateRange(
                filteredData, 
                filters.dateRange.start, 
                filters.dateRange.end, 
                filters.dateRange.field || 'StartTime'
            );
        }
        
        return filteredData;
    }

    // Training-specific validation for filter combinations
    static validateTrainingFilters(filters, dataManager) {
        const validation = {
            valid: true,
            warnings: [],
            errors: []
        };

        if (!dataManager || !dataManager.isReady()) {
            validation.valid = false;
            validation.errors.push("Training data not ready");
            return validation;
        }

        // Check AOR-Office compatibility
        if (filters.aors && filters.offices && 
            !filters.aors.includes("All") && !filters.offices.includes("All")) {
            
            const offices = dataManager.getData('offices');
            const validOffices = offices
                .filter(office => filters.aors.includes(office.AorShortName))
                .map(office => office.OfficeCode);
            
            const invalidOffices = filters.offices.filter(office => !validOffices.includes(office));
            
            if (invalidOffices.length > 0) {
                validation.warnings.push(
                    `Selected offices not available for selected AORs: ${invalidOffices.join(', ')}`
                );
            }
        }

        // Check if any classes would result from current filters
        if (dataManager.getFilteredClasses) {
            const result = dataManager.getFilteredClasses(
                filters.aors, filters.offices, filters.instructors, 
                filters.locations, filters.topics
            );
            
            if (result.classes && result.classes.length === 0) {
                validation.warnings.push("Current filter combination returns no classes");
            }
        }

        return validation;
    }
}

// Make globally available
window.TrainingFilterUtils = TrainingFilterUtils;