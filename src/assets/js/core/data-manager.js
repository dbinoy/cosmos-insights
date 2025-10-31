/**
 * Base Data Manager Class for All Dashboards
 * Provides common functionality for data loading and caching
 */

class DataManager {
    constructor(dashboardName) {
        this.dashboardName = dashboardName.toUpperCase();
        this.cache = {};
        this.cacheManager = window.cacheManager;
        this.dataKeys = []; // To be defined by subclasses
    }

    async loadAllData(serverData, useSharedCache = true) {
        // console.log(`📡 Loading all ${this.dashboardName} data...`);
        const results = {};
        let cacheHits = 0;
        let serverLoads = 0;
        
        // Check cache for all data types
        for (const key of this.dataKeys) {
            // Try dashboard-specific cache first, then shared cache if applicable
            let cached = await this.cacheManager.get(key, this.dashboardName);
            
            if (!cached && useSharedCache && this.isSharedData(key)) {
                cached = await this.cacheManager.get(key, 'SHARED');
            }
            
            if (cached && cached.length > 0) {
                results[key] = cached;
                this.cache[key] = cached;
                cacheHits++;
            }
        }
        
        // If we have server data, cache it and use it
        if (serverData && typeof serverData === 'object') {
            for (const key of this.dataKeys) {
                if (serverData[key] && serverData[key].length > 0) {
                    results[key] = serverData[key];
                    this.cache[key] = serverData[key];
                    
                    // Cache in appropriate store - dashboard-specific by default
                    const cacheLocation = this.isSharedData(key) ? 'SHARED' : this.dashboardName;
                    this.cacheManager.set(key, serverData[key], cacheLocation).catch(e => 
                        console.warn(`Failed to cache ${key}:`, e)
                    );
                    serverLoads++;
                }
            }
        }
        
        // console.log(`📊 ${this.dashboardName} data loading complete: ${cacheHits} from cache, ${serverLoads} from server`);
        return results;
    }

    getData(key) {
        return this.cache[key] || [];
    }

    isReady() {
        return this.dataKeys.every(key => this.cache[key] && this.cache[key].length > 0);
    }

    // Override in subclasses to define which data is shared across dashboards
    isSharedData(key) {
        // By default, no data is shared - each dashboard manages its own data
        return false;
    }

    async initializeSystem(serverData) {
        // console.log(`🚀 ${this.dashboardName} Data Cache System Initializing...`);
        
        // Initialize data
        const allData = await this.loadAllData(serverData);
        
        // console.log(`🎉 ${this.dashboardName} Data Cache System Ready!`);
        // console.log(`📋 Available datasets:`, Object.keys(allData));
        
        return {
            ready: true,
            data: allData,
            timestamp: Date.now(),
            dashboard: this.dashboardName
        };
    }
}

// Make globally available
window.DataManager = DataManager;