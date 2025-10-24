/**
 * Training Dropdown Handlers
 * Complete implementation using FilterUtils and TrainingDataManager
 */

class TrainingDropdownHandlers {
    static getAorOptions(dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const aors = dataManager.getData('aors');
        return FilterUtils.createOptions(aors, ['AorShortName', 'AorName'], 'AorShortName', 'All AORs',  ' - ');
    }

    static getOfficeOptions(selectedAors, dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        let offices = dataManager.getData('offices');
        
        // Filter by selected AORs
        if (Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")) {
            offices = offices.filter(office => selectedAors.includes(office.AorShortName));
        }
        
        const label = Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")
            ? `All ${selectedAors.join(',')} Offices`
            : 'All Offices';
            
        return FilterUtils.createOptions(
            offices.map(o => ({label: `${o.AorShortName} - ${o.OfficeCode}`, value: o.OfficeCode})),
            'label',
            'value',
            label
        );
    }

    static getTopicOptions(selectedAors, selectedOffices, dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const filteredTopics = dataManager.getFilteredTopics(selectedAors, selectedOffices);
        return FilterUtils.createOptions(filteredTopics, 'TopicName', 'TopicId', 'All Topics');
    }

    static getInstructorOptions(selectedAors, selectedOffices, dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const filteredInstructors = dataManager.getFilteredInstructors(selectedAors, selectedOffices);
        return FilterUtils.createOptions(filteredInstructors, 'Name', 'InstructorID', 'All Instructors');
    }

    static getLocationOptions(selectedAors, selectedOffices, selectedTopics, selectedInstructors, dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const filteredLocations = dataManager.getFilteredLocations(
            selectedAors, selectedOffices, selectedTopics, selectedInstructors
        );
        
        return FilterUtils.createOptions(filteredLocations, 'Name', 'LocationID', 'All Locations');
    }

    static getClassOptions(selectedAors, selectedOffices, selectedInstructors, selectedLocations, selectedTopics, dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const result = dataManager.getFilteredClasses(
            selectedAors, selectedOffices, selectedInstructors, selectedLocations, selectedTopics
        );
        
        const { classes: filteredClasses, topics } = result;
        
        if (filteredClasses.length === 0) {
            return [{label: "No classes found", value: "", disabled: true}];
        }
        
        // Create label for "All" option
        let allLabel = "All";
        if (Array.isArray(selectedTopics) && selectedTopics.length > 0 && !selectedTopics.includes("All") && topics) {
            const selectedTopicNames = topics
                .filter(t => selectedTopics.includes(String(t.TopicId)))
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

    // Helper method to create enhanced class options with more details
    static getEnhancedClassOptions(selectedAors, selectedOffices, selectedInstructors, selectedLocations, selectedTopics, dataManager) {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const result = dataManager.getFilteredClasses(
            selectedAors, selectedOffices, selectedInstructors, selectedLocations, selectedTopics
        );
        
        const { classes: filteredClasses, topics } = result;
        const instructors = dataManager.getData('instructors');
        const locations = dataManager.getData('locations');
        
        if (filteredClasses.length === 0) {
            return [{label: "No classes found", value: "", disabled: true}];
        }
        
        // Create enhanced options with instructor and location details
        const options = [{label: "All Classes", value: "All"}];
        return options.concat(
            filteredClasses.map(c => {
                const instructor = instructors.find(i => i.InstructorID === c.InstructorId);
                const location = locations.find(l => l.LocationID === c.LocationId);
                
                const instructorName = instructor ? instructor.Name : 'Unknown Instructor';
                const locationName = location ? location.Name : 'Unknown Location';
                
                return {
                    label: `${c.ClassName} | ${c.StartTime} | ${instructorName} | ${locationName}`,
                    value: c.ClassId
                };
            })
        );
    }

    // Method to get dropdown options with counts
    static getOptionsWithCounts(selectedAors, selectedOffices, dataManager) {
        if (!dataManager || !dataManager.isReady()) return {};
        
        const topics = dataManager.getFilteredTopics(selectedAors, selectedOffices);
        const instructors = dataManager.getFilteredInstructors(selectedAors, selectedOffices);
        const locations = dataManager.getFilteredLocations(selectedAors, selectedOffices, [], []);
        const classResult = dataManager.getFilteredClasses(selectedAors, selectedOffices, [], [], []);
        
        return {
            topicCount: topics.length,
            instructorCount: instructors.length,
            locationCount: locations.length,
            classCount: classResult.classes.length
        };
    }

    // Method to validate current filter selections
    static validateFilterSelections(selectedAors, selectedOffices, selectedTopics, selectedInstructors, selectedLocations, selectedClasses, dataManager) {
        if (!dataManager || !dataManager.isReady()) {
            return { valid: false, message: "Data not ready" };
        }
        
        const validation = {
            valid: true,
            warnings: [],
            errors: []
        };
        
        // Check if selections result in any data
        const result = dataManager.getFilteredClasses(
            selectedAors, selectedOffices, selectedInstructors, selectedLocations, selectedTopics
        );
        
        if (result.classes.length === 0) {
            validation.warnings.push("Current filter combination returns no classes");
        }
        
        // Check for conflicting selections
        if (Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")) {
            const availableOffices = dataManager.getData('offices')
                .filter(office => selectedAors.includes(office.AorShortName))
                .map(office => office.OfficeCode);
            
            if (Array.isArray(selectedOffices) && selectedOffices.length > 0 && !selectedOffices.includes("All")) {
                const invalidOffices = selectedOffices.filter(office => !availableOffices.includes(office));
                if (invalidOffices.length > 0) {
                    validation.warnings.push(`Selected offices not available for selected AORs: ${invalidOffices.join(', ')}`);
                }
            }
        }
        
        return validation;
    }

    // Method to get filter summary
    static getFilterSummary(selectedAors, selectedOffices, selectedTopics, selectedInstructors, selectedLocations, selectedClasses, dataManager) {
        if (!dataManager || !dataManager.isReady()) return "Data not ready";
        
        const summary = [];
        
        if (Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")) {
            summary.push(`AORs: ${selectedAors.join(', ')}`);
        }
        
        if (Array.isArray(selectedOffices) && selectedOffices.length > 0 && !selectedOffices.includes("All")) {
            summary.push(`Offices: ${selectedOffices.join(', ')}`);
        }
        
        if (Array.isArray(selectedTopics) && selectedTopics.length > 0 && !selectedTopics.includes("All")) {
            const topics = dataManager.getData('topics');
            const topicNames = topics
                .filter(t => selectedTopics.includes(String(t.TopicId)))
                .map(t => t.TopicName);
            summary.push(`Topics: ${topicNames.join(', ')}`);
        }
        
        if (Array.isArray(selectedInstructors) && selectedInstructors.length > 0 && !selectedInstructors.includes("All")) {
            const instructors = dataManager.getData('instructors');
            const instructorNames = instructors
                .filter(i => selectedInstructors.includes(String(i.InstructorID)))
                .map(i => i.Name);
            summary.push(`Instructors: ${instructorNames.join(', ')}`);
        }
        
        if (Array.isArray(selectedLocations) && selectedLocations.length > 0 && !selectedLocations.includes("All")) {
            const locations = dataManager.getData('locations');
            const locationNames = locations
                .filter(l => selectedLocations.includes(String(l.LocationID)))
                .map(l => l.Name);
            summary.push(`Locations: ${locationNames.join(', ')}`);
        }
        
        if (Array.isArray(selectedClasses) && selectedClasses.length > 0 && !selectedClasses.includes("All")) {
            summary.push(`Classes: ${selectedClasses.length} selected`);
        }
        
        return summary.length > 0 ? summary.join(' | ') : 'No filters applied';
    }

    // Method to reset all dropdowns to default state
    static getDefaultFilterValues() {
        return {
            aors: [],
            offices: [],
            topics: [],
            instructors: [],
            locations: [],
            classes: []
        };
    }

    // Method to get spinner states for all dropdowns
    static getSpinnerStates(dataReady) {
        return FilterUtils.createSpinnerStates(dataReady && dataReady.ready, "training");
    }
}

// Make globally available
window.TrainingDropdownHandlers = TrainingDropdownHandlers;