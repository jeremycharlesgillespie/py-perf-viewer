import axios from 'axios'

// Create axios instance with default config
const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // Increase timeout to 30 seconds for DynamoDB operations
  headers: {
    'Content-Type': 'application/json',
  }
})

// Request interceptor for error handling
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// System Metrics API
export const systemApi = {
  // Get system dashboard data (overview)
  getDashboardData() {
    return api.get('/system/')
  },

  // Get system metrics for specific hostname
  getHostMetrics(hostname, hours = 24) {
    return api.get('/system/', {
      params: { hostname, hours }
    })
  },

  // Get list of system hostnames
  getSystemHostnames() {
    return api.get('/system/hostnames/')
  }
}

// Performance Metrics API
export const performanceApi = {
  // Get performance metrics overview
  getMetrics() {
    return api.get('/metrics/')
  },

  // Get hostnames for performance data
  getHostnames() {
    return api.get('/hostnames/')
  },

  // Get function names
  getFunctions() {
    return api.get('/functions/')
  },

  // Get timeline data
  getTimelineData(params = {}) {
    return api.get('/timeline/', { params })
  }
}

// Records API (placeholder - will need to be implemented based on existing endpoints)
export const recordsApi = {
  // Get performance records with filtering/pagination
  getRecords(params = {}) {
    // This would need to be implemented in Django views
    return api.get('/records/', { params })
  },

  // Get specific record detail
  getRecordDetail(recordId) {
    return api.get(`/records/${recordId}/`)
  },

  // Get function analysis
  getFunctionAnalysis(functionName, params = {}) {
    return api.get(`/functions/${functionName}/`, { params })
  }
}

// Utility functions
export const formatTimestamp = (timestamp) => {
  let date
  
  if (!timestamp) {
    return 'N/A'
  }
  
  // Handle different timestamp formats
  if (typeof timestamp === 'string') {
    // ISO datetime string from Django
    date = new Date(timestamp)
  } else if (typeof timestamp === 'number') {
    // Unix timestamp
    date = new Date(timestamp * 1000)
  } else {
    return 'Invalid Date'
  }
  
  // Check if date is valid
  if (isNaN(date.getTime())) {
    return 'Invalid Date'
  }
  
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'America/Chicago',
    timeZoneName: 'short'
  }).format(date)
}

export const formatDate = (timestamp) => {
  let date
  
  if (!timestamp) {
    return 'N/A'
  }
  
  // Handle different timestamp formats
  if (typeof timestamp === 'string') {
    // ISO datetime string from Django
    date = new Date(timestamp)
  } else if (typeof timestamp === 'number') {
    // Unix timestamp
    date = new Date(timestamp * 1000)
  } else {
    return 'Invalid Date'
  }
  
  // Check if date is valid
  if (isNaN(date.getTime())) {
    return 'Invalid Date'
  }
  
  return date.toLocaleDateString([], {
    month: 'short',
    day: 'numeric'
  })
}

export default api