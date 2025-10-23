/**
 * Universal IndexedDB Cache Manager for All Dashboards
 * Handles client-side caching for Training, Assist, Comply, and other dashboards
 */

class CacheManager {
    constructor() {
        this.CACHE_TTL = 60 * 60 * 1000; // 60 minutes
        this.DB_NAME = 'CosmosInsightsCache'; // Single DB for all dashboards
        this.DB_VERSION = 1;
        this.STORES = {
            TRAINING: 'training_data',
            ASSIST: 'assist_data',
            COMPLY: 'comply_data',
            SHARED: 'shared_data' // For common data like AORs, Offices
        };
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);
            
            request.onerror = () => {
                console.error('❌ Universal IndexedDB open failed:', request.error);
                reject(request.error);
            };
            
            request.onsuccess = () => {
                console.log('✅ Universal IndexedDB opened successfully');
                resolve(request.result);
            };
            
            request.onupgradeneeded = (event) => {
                console.log('🔄 Universal IndexedDB upgrade needed');
                const db = event.target.result;
                
                // Create stores for each dashboard
                Object.values(this.STORES).forEach(storeName => {
                    if (!db.objectStoreNames.contains(storeName)) {
                        const store = db.createObjectStore(storeName, { keyPath: 'key' });
                        store.createIndex('timestamp', 'timestamp', { unique: false });
                        store.createIndex('dataType', 'dataType', { unique: false });
                        store.createIndex('dashboard', 'dashboard', { unique: false });
                        console.log(`📦 Created store: ${storeName}`);
                    }
                });
            };
        });
    }

    async get(key, dashboard = 'SHARED') {
        try {
            const db = await this.init();
            const storeName = this.STORES[dashboard.toUpperCase()] || this.STORES.SHARED;
            const transaction = db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            
            return new Promise((resolve) => {
                const request = store.get(key);
                request.onsuccess = () => {
                    const result = request.result;
                    if (!result) {
                        console.log(`📭 No cache found for: ${key} in ${dashboard}`);
                        resolve(null);
                        return;
                    }
                    
                    const now = Date.now();
                    const age = now - result.timestamp;
                    
                    if (age > this.CACHE_TTL) {
                        console.log(`⏰ Cache expired for: ${key} in ${dashboard} (${Math.round(age/1000/60)} min old)`);
                        this.delete(key, dashboard);
                        resolve(null);
                        return;
                    }
                    
                    console.log(`✅ Cache hit for: ${key} in ${dashboard} (${Math.round(age/1000/60)} min old, ${result.value.length} records)`);
                    resolve(result.value);
                };
                request.onerror = () => resolve(null);
            });
        } catch (e) {
            console.warn(`⚠️ IndexedDB read error for ${key} in ${dashboard}:`, e);
            return null;
        }
    }

    async set(key, value, dashboard = 'SHARED', dataType = 'data') {
        try {
            const db = await this.init();
            const storeName = this.STORES[dashboard.toUpperCase()] || this.STORES.SHARED;
            const transaction = db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            
            const data = {
                key,
                value,
                timestamp: Date.now(),
                dataType,
                dashboard: dashboard.toLowerCase(),
                size: JSON.stringify(value).length
            };
            
            return new Promise((resolve) => {
                const request = store.put(data);
                request.onsuccess = () => {
                    const sizeMB = Math.round(data.size / 1024 / 1024 * 100) / 100;
                    console.log(`💾 Cached: ${key} in ${dashboard} (${value.length} records, ${sizeMB}MB)`);
                    resolve(true);
                };
                request.onerror = () => {
                    console.error(`❌ Cache write failed for ${key} in ${dashboard}:`, request.error);
                    resolve(false);
                };
            });
        } catch (e) {
            console.error(`❌ IndexedDB write error for ${key} in ${dashboard}:`, e);
            return false;
        }
    }

    async delete(key, dashboard = 'SHARED') {
        try {
            const db = await this.init();
            const storeName = this.STORES[dashboard.toUpperCase()] || this.STORES.SHARED;
            const transaction = db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            store.delete(key);
        } catch (e) {
            console.warn(`Warning: Could not delete ${key} from ${dashboard}:`, e);
        }
    }

    async clearDashboard(dashboard) {
        try {
            const db = await this.init();
            const storeName = this.STORES[dashboard.toUpperCase()] || this.STORES.SHARED;
            const transaction = db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            store.clear();
            console.log(`🗑️ Cleared ${dashboard} cache`);
        } catch (e) {
            console.warn(`Warning: Could not clear ${dashboard} cache:`, e);
        }
    }

    async clearAll() {
        try {
            const db = await this.init();
            const transaction = db.transaction(Object.values(this.STORES), 'readwrite');
            Object.values(this.STORES).forEach(storeName => {
                const store = transaction.objectStore(storeName);
                store.clear();
            });
            console.log('🗑️ Cleared all caches');
        } catch (e) {
            console.warn('Warning: Could not clear all caches:', e);
        }
    }

    // Get cache statistics
    async getStats() {
        try {
            const db = await this.init();
            const stats = {};
            
            for (const [dashboardName, storeName] of Object.entries(this.STORES)) {
                const transaction = db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                
                stats[dashboardName] = await new Promise(resolve => {
                    const request = store.getAll();
                    request.onsuccess = () => {
                        const items = request.result;
                        const totalSize = items.reduce((sum, item) => sum + (item.size || 0), 0);
                        resolve({
                            items: items.length,
                            size: Math.round(totalSize / 1024 / 1024 * 100) / 100 // MB
                        });
                    };
                    request.onerror = () => resolve({ items: 0, size: 0 });
                });
            }
            
            return stats;
        } catch (e) {
            console.warn('Could not get cache stats:', e);
            return {};
        }
    }
}

// Create global singleton instance
window.cacheManager = new CacheManager();