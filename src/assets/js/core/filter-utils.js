/**
 * Shared Filter Utilities for All Dashboards
 * Common filtering and option creation functions
 */

class FilterUtils {
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
    
    static filterByDateRange(data, startDate, endDate, dateField = 'date') {
        if (!startDate || !endDate) return data;
        
        const start = new Date(startDate);
        const end = new Date(endDate);
        
        return data.filter(item => {
            const itemDate = new Date(item[dateField]);
            return itemDate >= start && itemDate <= end;
        });
    }
    
    static getUniqueIds(data, field) {
        return [...new Set(data.map(item => item[field]).filter(Boolean))];
    }
    
    static createOptions(data, labelField, valueField, allLabel = "All") {
        if (!data || data.length === 0) return [];
        
        const options = [{label: allLabel, value: "All"}];
        return options.concat(
            data.map(item => ({
                label: item[labelField],
                value: String(item[valueField])
            }))
        );
    }

    static createSpinnerStates(isReady, dashboardPrefix = "") {
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

    // Generic AOR options for all dashboards
    static getAorOptions(dataManager, allLabel = "All AORs") {
        if (!dataManager || !dataManager.isReady()) return [];
        
        const aors = dataManager.getData('aors');
        return this.createOptions(aors, 'AorShortName', 'AorShortName', allLabel);
    }

    // Generic Office options for all dashboards
    static getOfficeOptions(selectedAors, dataManager, allLabel = "All Offices") {
        if (!dataManager || !dataManager.isReady()) return [];
        
        let offices = dataManager.getData('offices');
        
        // Filter by selected AORs
        if (Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")) {
            offices = offices.filter(office => selectedAors.includes(office.AorShortName));
        }
        
        const label = Array.isArray(selectedAors) && selectedAors.length > 0 && !selectedAors.includes("All")
            ? `All ${selectedAors.join(',')} Offices`
            : allLabel;
            
        return this.createOptions(
            offices.map(o => ({label: `${o.AorShortName} - ${o.OfficeCode}`, value: o.OfficeCode})),
            'label',
            'value',
            label
        );
    }

    // Cache management utilities
    static async getCacheStats() {
        if (window.cacheManager) {
            return await window.cacheManager.getStats();
        }
        return {};
    }

    static async clearDashboardCache(dashboard) {
        if (window.cacheManager) {
            await window.cacheManager.clearDashboard(dashboard);
        }
    }

    static async clearAllCaches() {
        if (window.cacheManager) {
            await window.cacheManager.clearAll();
        }
    }
}

// Make globally available
window.FilterUtils = FilterUtils;