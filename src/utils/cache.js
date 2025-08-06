/**
 * Local caching utilities for DynamoDB data
 * Uses localStorage with TTL (Time To Live) support
 */

// Default cache TTL: 5 minutes
const DEFAULT_CACHE_TTL = 5 * 60 * 1000

// Cache key prefixes to avoid conflicts
const CACHE_KEYS = {
  DASHBOARD: 'pyperf_dashboard',
  HOST_METRICS: 'pyperf_host_metrics',
  SYSTEM_DATA: 'pyperf_system_data'
}

/**
 * Set data in cache with TTL
 * @param {string} key - Cache key
 * @param {any} data - Data to cache
 * @param {number} ttl - Time to live in milliseconds
 */
export const setCache = (key, data, ttl = DEFAULT_CACHE_TTL) => {
  try {
    const cacheItem = {
      data,
      timestamp: Date.now(),
      ttl
    }
    localStorage.setItem(key, JSON.stringify(cacheItem))
  } catch (error) {
    console.warn('Failed to set cache:', error)
  }
}

/**
 * Get data from cache if not expired
 * @param {string} key - Cache key
 * @returns {any|null} - Cached data or null if expired/not found
 */
export const getCache = (key) => {
  try {
    const cached = localStorage.getItem(key)
    if (!cached) return null
    
    const cacheItem = JSON.parse(cached)
    const now = Date.now()
    
    // Check if cache has expired
    if (now - cacheItem.timestamp > cacheItem.ttl) {
      localStorage.removeItem(key)
      return null
    }
    
    return cacheItem.data
  } catch (error) {
    console.warn('Failed to get cache:', error)
    return null
  }
}

/**
 * Check if cache exists and is valid
 * @param {string} key - Cache key
 * @returns {boolean} - True if cache is valid
 */
export const hasValidCache = (key) => {
  return getCache(key) !== null
}

/**
 * Clear specific cache entry
 * @param {string} key - Cache key to clear
 */
export const clearCache = (key) => {
  try {
    localStorage.removeItem(key)
  } catch (error) {
    console.warn('Failed to clear cache:', error)
  }
}

/**
 * Clear all PyPerf caches
 */
export const clearAllCaches = () => {
  Object.values(CACHE_KEYS).forEach(key => {
    clearCache(key)
  })
  
  // Also clear any host-specific caches
  try {
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
      if (key.startsWith('pyperf_')) {
        localStorage.removeItem(key)
      }
    })
  } catch (error) {
    console.warn('Failed to clear all caches:', error)
  }
}

/**
 * Generate cache key for dashboard data
 * @returns {string} - Cache key
 */
export const getDashboardCacheKey = () => {
  return CACHE_KEYS.DASHBOARD
}

/**
 * Generate cache key for host metrics
 * @param {string} hostname - Host name
 * @param {number} hours - Hours of data
 * @returns {string} - Cache key
 */
export const getHostMetricsCacheKey = (hostname, hours = 24) => {
  return `${CACHE_KEYS.HOST_METRICS}_${hostname}_${hours}h`
}

/**
 * Get cache statistics for debugging
 * @returns {object} - Cache statistics
 */
export const getCacheStats = () => {
  const stats = {
    totalEntries: 0,
    pyperfEntries: 0,
    totalSize: 0,
    entries: []
  }
  
  try {
    const keys = Object.keys(localStorage)
    stats.totalEntries = keys.length
    
    keys.forEach(key => {
      if (key.startsWith('pyperf_')) {
        stats.pyperfEntries++
        const data = localStorage.getItem(key)
        stats.totalSize += data.length
        
        try {
          const cacheItem = JSON.parse(data)
          const age = Date.now() - cacheItem.timestamp
          const isExpired = age > cacheItem.ttl
          
          stats.entries.push({
            key,
            age: Math.round(age / 1000), // seconds
            ttl: Math.round(cacheItem.ttl / 1000), // seconds
            size: data.length,
            expired: isExpired
          })
        } catch (e) {
          // Invalid cache entry
        }
      }
    })
  } catch (error) {
    console.warn('Failed to get cache stats:', error)
  }
  
  return stats
}

/**
 * Cleanup expired cache entries
 */
export const cleanupExpiredCache = () => {
  try {
    const keys = Object.keys(localStorage)
    let cleaned = 0
    
    keys.forEach(key => {
      if (key.startsWith('pyperf_')) {
        if (!hasValidCache(key)) {
          cleaned++
        }
      }
    })
    
    console.log(`Cleaned up ${cleaned} expired cache entries`)
    return cleaned
  } catch (error) {
    console.warn('Failed to cleanup cache:', error)
    return 0
  }
}

// Auto-cleanup expired cache entries on page load
if (typeof window !== 'undefined') {
  // Run cleanup after a short delay to not block page load
  setTimeout(() => {
    cleanupExpiredCache()
  }, 5000)
}