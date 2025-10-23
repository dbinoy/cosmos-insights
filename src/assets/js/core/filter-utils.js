/**
 * Shared Filter Utilities for All Dashboards
 * Common filtering and option creation functions
 */

class FilterUtils {
    static filterByDateRange(data, startDate, endDate, dateField = 'date') {
        if (!startDate || !endDate) return data;
        
        const start = new Date(startDate);
        const end = new Date(endDate);
        
        return data.filter(item => {
            const itemDate = new Date(item[dateField]);
            return itemDate >= start && itemDate <= end;
        });
    }
    
    static filterByValues(data, selectedValues, fieldName) {
        if (!Array.isArray(selectedValues) || selectedValues.length === 0 || selectedValues.includes("All")) {
            return data;
        }
        return data.filter(item => selectedValues.includes(item[fieldName]));
    }
    
    static filterByMultipleFields(data, selectedValues, fieldNames) {
        if (!Array.isArray(selectedValues) || selectedValues.length === 0 || selectedValues.includes("All")) {
            return data;
        }
        return data.filter(item => {
            return fieldNames.some(fieldName => 
                item[fieldName] && selectedValues.includes(item[fieldName])
            );
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

    // Generic spinner state creator - takes arrays of loading and ready placeholders
    static createGenericSpinnerStates(isReady, loadingPlaceholders, readyPlaceholders) {
        const hideStyle = {"display": "none"};
        const showStyle = {"position": "absolute", "top": "30px", "right": "30px"};
        
        const placeholders = isReady ? readyPlaceholders : loadingPlaceholders;
        const style = isReady ? hideStyle : showStyle;
        
        const result = [];
        for (let i = 0; i < placeholders.length; i++) {
            result.push(style, placeholders[i]);
        }
        
        return result;
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