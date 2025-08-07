import { defineStore } from 'pinia'
import { systemApi } from '@/services/api'
import { dashboardWebSocket, systemDetailWebSocket } from '@/services/websocket'
import { 
  setCache, 
  getCache, 
  hasValidCache, 
  getDashboardCacheKey, 
  getHostMetricsCacheKey,
  clearCache
} from '@/utils/cache'

export const useSystemStore = defineStore('system', {
  state: () => ({
    // System overview data
    dashboardData: {
      total_hosts: 0,
      total_records: 0,
      hosts_summary: []
    },
    
    // Current host details
    currentHost: null,
    currentHostMetrics: null,
    
    // Loading states
    isLoadingDashboard: false,
    isLoadingHostDetail: false,
    
    // Error states
    dashboardError: null,
    hostDetailError: null,
    
    // Auto-refresh
    refreshInterval: null,
    lastUpdate: null,
    
    // Cache status
    usingCachedData: false,
    
    // WebSocket connection status
    isWebSocketConnected: false,
    webSocketConnectionAttempts: 0,
    currentHostname: null
  }),

  getters: {
    // Get host by hostname
    getHostByName: (state) => (hostname) => {
      return state.dashboardData.hosts_summary.find(host => host.hostname === hostname)
    },
    
    // Check if data is stale (older than 2 minutes)
    isDataStale: (state) => {
      if (!state.lastUpdate) return true
      return (Date.now() - state.lastUpdate) > 120000 // 2 minutes
    }
  },

  actions: {
    // Fetch system dashboard data with caching
    async fetchDashboardData(forceRefresh = false) {
      const cacheKey = getDashboardCacheKey()
      
      // Try to load from cache first if not forcing refresh
      if (!forceRefresh) {
        const cachedData = getCache(cacheKey)
        if (cachedData) {
          this.dashboardData = cachedData
          this.usingCachedData = true
          this.lastUpdate = Date.now()
          
          // Fetch fresh data in background
          this.fetchDashboardDataFromAPI(cacheKey)
          return
        }
      }
      
      // No cache or force refresh - show loading and fetch fresh data
      this.isLoadingDashboard = true
      this.usingCachedData = false
      await this.fetchDashboardDataFromAPI(cacheKey)
    },

    // Internal method to fetch from API and update cache
    async fetchDashboardDataFromAPI(cacheKey) {
      this.dashboardError = null
      
      try {
        const response = await systemApi.getDashboardData()
        this.dashboardData = response.data
        this.lastUpdate = Date.now()
        this.usingCachedData = false
        
        // Cache the fresh data
        setCache(cacheKey, response.data)
        
      } catch (error) {
        this.dashboardError = error.message || 'Failed to fetch system data'
        console.error('Error fetching dashboard data:', error)
        
        // If we have cached data, keep using it despite the error
        const cachedData = getCache(cacheKey)
        if (cachedData && !this.dashboardData.total_hosts) {
          this.dashboardData = cachedData
          this.usingCachedData = true
        }
      } finally {
        this.isLoadingDashboard = false
      }
    },

    // Fetch metrics for specific host with caching
    async fetchHostMetrics(hostname, hours = 24, forceRefresh = false) {
      const cacheKey = getHostMetricsCacheKey(hostname, hours)
      this.currentHost = hostname
      
      // Try to load from cache first if not forcing refresh
      if (!forceRefresh) {
        const cachedData = getCache(cacheKey)
        if (cachedData) {
          this.currentHostMetrics = cachedData
          this.usingCachedData = true
          
          // Fetch fresh data in background
          this.fetchHostMetricsFromAPI(hostname, hours, cacheKey)
          return
        }
      }
      
      // No cache or force refresh - show loading and fetch fresh data
      this.isLoadingHostDetail = true
      this.usingCachedData = false
      await this.fetchHostMetricsFromAPI(hostname, hours, cacheKey)
    },

    // Internal method to fetch host metrics from API and update cache
    async fetchHostMetricsFromAPI(hostname, hours, cacheKey) {
      this.hostDetailError = null
      
      try {
        const response = await systemApi.getHostMetrics(hostname, hours)
        this.currentHostMetrics = response.data
        this.usingCachedData = false
        
        // Cache the fresh data (shorter TTL for detailed metrics)
        setCache(cacheKey, response.data, 3 * 60 * 1000) // 3 minutes
        
      } catch (error) {
        this.hostDetailError = error.message || 'Failed to fetch host metrics'
        console.error('Error fetching host metrics:', error)
        
        // If we have cached data, keep using it despite the error
        const cachedData = getCache(cacheKey)
        if (cachedData && !this.currentHostMetrics) {
          this.currentHostMetrics = cachedData
          this.usingCachedData = true
        }
      } finally {
        this.isLoadingHostDetail = false
      }
    },

    // Start auto-refresh for dashboard data
    startDashboardAutoRefresh(interval = 60000) { // 1 minute default
      this.stopAutoRefresh() // Clear any existing interval
      
      this.refreshInterval = setInterval(() => {
        this.fetchDashboardData()
      }, interval)
    },

    // Start auto-refresh for host metrics
    startHostAutoRefresh(hostname, hours = 24, interval = 60000) {
      this.stopAutoRefresh() // Clear any existing interval
      
      this.refreshInterval = setInterval(() => {
        if (this.currentHost === hostname) {
          this.fetchHostMetrics(hostname, hours)
        }
      }, interval)
    },

    // Alias for SystemDetail page auto-refresh
    startHostDetailAutoRefresh(hostname, interval = 120000) {
      // Use 24 hours as default time range, 2 minutes polling interval
      this.startHostAutoRefresh(hostname, 24, interval)
    },

    // Stop auto-refresh
    stopAutoRefresh() {
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
    },

    // Clear current host data
    clearHostData() {
      this.currentHost = null
      this.currentHostMetrics = null
      this.hostDetailError = null
    },

    // Force refresh dashboard data (bypass cache)
    async refreshDashboard() {
      await this.fetchDashboardData(true)
    },

    // Force refresh host metrics (bypass cache)
    async refreshHostMetrics(hostname, hours = 24) {
      await this.fetchHostMetrics(hostname, hours, true)
    },

    // Clear cache for specific data
    clearDashboardCache() {
      clearCache(getDashboardCacheKey())
    },

    clearHostCache(hostname, hours = 24) {
      clearCache(getHostMetricsCacheKey(hostname, hours))
    },

    // Check if we have cached data available
    hasCachedDashboard() {
      return hasValidCache(getDashboardCacheKey())
    },

    hasCachedHostMetrics(hostname, hours = 24) {
      return hasValidCache(getHostMetricsCacheKey(hostname, hours))
    },

    // WebSocket methods
    async connectToDashboardWebSocket() {
      try {
        await dashboardWebSocket.connect('/ws/dashboard/')
        this.isWebSocketConnected = true
        this.webSocketConnectionAttempts = 0
        
        // Set up event listeners
        dashboardWebSocket.on('connected', () => {
          console.log('Dashboard WebSocket connected')
          this.isWebSocketConnected = true
        })
        
        dashboardWebSocket.on('disconnected', () => {
          console.log('Dashboard WebSocket disconnected')
          this.isWebSocketConnected = false
        })
        
        dashboardWebSocket.on('metrics_update', (data) => {
          this.handleMetricsUpdate(data)
        })
        
        dashboardWebSocket.on('host_offline', (data) => {
          this.handleHostOffline(data)
        })
        
        dashboardWebSocket.on('cache_invalidation', (data) => {
          this.handleCacheInvalidation(data)
        })
        
        // Start heartbeat
        dashboardWebSocket.startHeartbeat()
        
      } catch (error) {
        console.error('Failed to connect to dashboard WebSocket:', error)
        this.webSocketConnectionAttempts++
        this.isWebSocketConnected = false
      }
    },

    async connectToSystemDetailWebSocket(hostname) {
      try {
        this.currentHostname = hostname
        await systemDetailWebSocket.connect(`/ws/system/${hostname}/`)
        
        // Set up event listeners
        systemDetailWebSocket.on('connected', () => {
          console.log(`System detail WebSocket connected for ${hostname}`)
        })
        
        systemDetailWebSocket.on('disconnected', () => {
          console.log(`System detail WebSocket disconnected for ${hostname}`)
        })
        
        systemDetailWebSocket.on('metrics_update', (data) => {
          if (data.hostname === hostname) {
            this.handleHostMetricsUpdate(data)
          }
        })
        
        // Start heartbeat
        systemDetailWebSocket.startHeartbeat()
        
      } catch (error) {
        console.error('Failed to connect to system detail WebSocket:', error)
      }
    },

    disconnectWebSockets() {
      dashboardWebSocket.disconnect()
      systemDetailWebSocket.disconnect()
      this.isWebSocketConnected = false
      this.currentHostname = null
    },

    // WebSocket event handlers
    handleMetricsUpdate(data) {
      console.log('Received metrics update:', data)
      
      // Update the host in the dashboard data
      const hostIndex = this.dashboardData.hosts_summary.findIndex(
        host => host.hostname === data.hostname
      )
      
      if (hostIndex >= 0) {
        // Update existing host
        this.dashboardData.hosts_summary[hostIndex] = {
          ...this.dashboardData.hosts_summary[hostIndex],
          current_cpu: data.metrics.cpu_percent,
          current_memory: data.metrics.memory_percent,
          last_seen: new Date(data.timestamp * 1000),
          is_online: true
        }
      } else {
        // Add new host
        this.dashboardData.hosts_summary.push({
          hostname: data.hostname,
          current_cpu: data.metrics.cpu_percent,
          current_memory: data.metrics.memory_percent,
          last_seen: new Date(data.timestamp * 1000),
          is_online: true,
          total_records: 1
        })
        this.dashboardData.total_hosts++
      }
      
      this.lastUpdate = Date.now()
      this.usingCachedData = false
    },

    handleHostMetricsUpdate(data) {
      console.log('Received host metrics update:', data)
      
      if (this.currentHostMetrics && data.hostname === this.currentHost) {
        // Update current host metrics
        this.currentHostMetrics = {
          ...this.currentHostMetrics,
          current_cpu: data.metrics.cpu_percent,
          current_memory: data.metrics.memory_percent,
          last_seen: new Date(data.timestamp * 1000),
          is_online: true
        }
        
        // Add to timeline data if it exists
        if (this.currentHostMetrics.timeline_data) {
          this.currentHostMetrics.timeline_data.push({
            timestamp: data.timestamp,
            cpu_percent: data.metrics.cpu_percent,
            memory_percent: data.metrics.memory_percent,
            memory_available_mb: data.metrics.memory_available_mb,
            memory_used_mb: data.metrics.memory_used_mb
          })
          
          // Keep only last 200 points
          if (this.currentHostMetrics.timeline_data.length > 200) {
            this.currentHostMetrics.timeline_data = this.currentHostMetrics.timeline_data.slice(-200)
          }
        }
      }
      
      this.lastUpdate = Date.now()
    },

    handleHostOffline(data) {
      console.log('Host went offline:', data)
      
      // Update host status in dashboard
      const hostIndex = this.dashboardData.hosts_summary.findIndex(
        host => host.hostname === data.hostname
      )
      
      if (hostIndex >= 0) {
        this.dashboardData.hosts_summary[hostIndex].is_online = false
      }
    },

    handleCacheInvalidation(data) {
      console.log('Cache invalidation received:', data)
      
      // Clear affected caches
      data.cache_keys?.forEach(cacheKey => {
        clearCache(cacheKey)
      })
    }
  }
})