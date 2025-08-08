<template>
  <div class="container mt-4">
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item">
          <router-link to="/system">System Metrics</router-link>
        </li>
        <li class="breadcrumb-item active">{{ hostname }}</li>
      </ol>
    </nav>

    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="mb-0">System Metrics: {{ hostname }}</h1>
      
      <!-- Refresh Button -->
      <div>
        <button 
          class="btn btn-outline-secondary btn-sm" 
          @click="refreshData"
          :disabled="isLoadingHostDetail"
          title="Refresh data from server"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoadingHostDetail }"></i>
        </button>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="isLoadingHostDetail" class="text-center py-4">
      <div class="loading-spinner"></div>
      <p class="mt-2">Loading host metrics...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="hostDetailError" class="alert alert-danger">
      <i class="fas fa-exclamation-triangle"></i>
      {{ hostDetailError }}
    </div>

    <!-- Host Metrics -->
    <div v-else-if="hostMetrics">
      <!-- Current Metrics Cards -->
      <div class="row mb-4">
        <div class="col-md-6">
          <div class="card">
            <div class="card-body text-center">
              <h6 class="card-title text-muted">Current CPU</h6>
              <h3 :class="getCpuClass(hostMetrics.current_cpu)">
                {{ hostMetrics.current_cpu?.toFixed(1) }}%
              </h3>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card">
            <div class="card-body text-center">
              <h6 class="card-title text-muted">Current Memory</h6>
              <h3 :class="getMemoryClass(hostMetrics.current_memory)">
                {{ hostMetrics.current_memory?.toFixed(1) }}%
              </h3>
            </div>
          </div>
        </div>
      </div>

      <!-- Combined CPU & Memory Usage Chart - Full Width -->
      <div class="row mb-4">
        <div class="col-12">
          <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
              <div class="d-flex align-items-center">
                <h5 class="mb-0 me-3">System Usage</h5>
                <small class="text-muted" v-if="hostMetrics.first_seen">
                  <i class="fas fa-calendar-plus"></i>
                  First Seen: 
                  <span class="fw-bold">{{ formatTimestamp(hostMetrics.first_seen) }}</span>
                </small>
              </div>
              <div class="chart-controls d-flex align-items-center">
                <small class="text-muted me-3">
                  <i class="fas fa-clock"></i>
                  Last Update: 
                  <span class="fw-bold">{{ formatTimestamp(hostMetrics.last_seen || hostMetrics.time_range?.end) }}</span>
                </small>
                <div class="btn-group" role="group">
                  <button 
                    v-for="level in zoomLevels" 
                    :key="level.label"
                    class="btn btn-sm"
                    :class="currentZoomLevel === level.label ? 'btn-primary' : 'btn-outline-secondary'"
                    @click="setZoomLevel(level)"
                    :title="`Show last ${level.label}`"
                  >
                    {{ level.label }}
                  </button>
                  <button class="btn btn-sm btn-outline-secondary" @click="resetZoom('combined')" title="Show last 7 days">
                    7 days
                  </button>
                </div>
              </div>
            </div>
            <div class="card-body" style="position: relative;">
              <canvas ref="combinedChart" style="height: 400px; display: block;"></canvas>
              <div v-if="!hostMetrics || !hasChartData" class="text-center py-4 text-muted" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10;">
                <i class="fas fa-chart-line fa-3x mb-3"></i>
                <p>No system data available yet</p>
                <small>Data will appear once system metrics are collected</small>
                <div class="mt-2">
                  <small class="text-info">Debug: hasChartData = {{ hasChartData }}, hostMetrics = {{ !!hostMetrics }}</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Navigation -->
    <div class="mt-4 text-center">
      <router-link to="/system" class="btn btn-secondary">Back to Overview</router-link>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'
import { formatTimestamp } from '@/services/api'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import zoomPlugin from 'chartjs-plugin-zoom'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  Filler,
  zoomPlugin
)

export default {
  name: 'SystemDetail',
  props: {
    hostname: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const route = useRoute()
    const systemStore = useSystemStore()
    const hours = 24 // Fixed at 24 hours since we're using zoom controls
    
    // Chart references
    const combinedChart = ref(null)
    let combinedChartInstance = null
    
    // Zoom levels configuration
    const zoomLevels = [
      { label: '10m', minutes: 10, ticks: 'minute', unit: 'minute', stepSize: 2 },
      { label: '30m', minutes: 30, ticks: 'minute', unit: 'minute', stepSize: 5 },
      { label: '1h', minutes: 60, ticks: 'minute', unit: 'minute', stepSize: 10 },
      { label: '4h', minutes: 240, ticks: 'hour', unit: 'hour', stepSize: 1 },
      { label: '24h', minutes: 1440, ticks: 'hour', unit: 'hour', stepSize: 4 }
    ]
    
    const currentZoomLevel = ref(null)

    // Computed properties
    const hostMetrics = computed(() => systemStore.currentHostMetrics)
    const isLoadingHostDetail = computed(() => systemStore.isLoadingHostDetail)
    const hostDetailError = computed(() => systemStore.hostDetailError)
    
    const hasChartData = computed(() => {
      if (!hostMetrics.value) return false
      
      let metrics = []
      if (hostMetrics.value.timeline_data) {
        metrics = hostMetrics.value.timeline_data
      } else if (hostMetrics.value.metrics) {
        metrics = hostMetrics.value.metrics
      } else if (hostMetrics.value.data) {
        metrics = hostMetrics.value.data
      } else if (Array.isArray(hostMetrics.value)) {
        metrics = hostMetrics.value
      }
      
      return metrics.length > 0
    })

    // Methods
    const getCpuClass = (cpu) => {
      if (cpu <= 60) return 'text-success'
      if (cpu <= 80) return 'text-warning'
      return 'text-danger'
    }

    const getMemoryClass = (memory) => {
      if (memory <= 60) return 'text-success'
      if (memory <= 80) return 'text-warning'
      return 'text-danger'
    }

    const formatDateTime = (timestamp) => {
      if (!timestamp) return 'N/A'
      
      // Unix timestamps from DynamoDB are in UTC
      const date = new Date(timestamp * 1000)
      
      // Force Central Time (Chicago timezone)  
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZone: 'America/Chicago',
        timeZoneName: 'short'
      }).format(date)
    }


    const fetchHostData = async () => {
      await systemStore.fetchHostMetrics(props.hostname, hours)
    }

    const refreshData = async () => {
      await systemStore.refreshHostMetrics(props.hostname, hours)
      // Update charts after data refresh
      await nextTick()
      updateCharts()
    }

    // Combined chart configuration
    const getCombinedChartConfig = () => {
      // Calculate minimum zoom range based on data density
      const minDataPoints = 10
      const dataInterval = 60 * 1000 // 1 minute intervals in milliseconds
      const minRange = minDataPoints * dataInterval // 10 minutes minimum view
      
      // Function to clear zoom level when user manually zooms
      const handleZoom = ({ chart }) => {
        currentZoomLevel.value = null
      }
      
      return {
        type: 'line',
        data: {
          datasets: [
            {
              label: 'CPU Usage',
              data: [],
              borderColor: '#0d6efd',
              backgroundColor: '#0d6efd20',
              fill: false,
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 0,
              pointBorderWidth: 0,
              pointBackgroundColor: 'transparent',
              pointHoverBackgroundColor: 'transparent',
              pointHoverBorderColor: 'transparent',
              pointHoverBorderWidth: 0,
              yAxisID: 'y'
            },
            {
              label: 'Memory Usage',
              data: [],
              borderColor: '#28a745',
              backgroundColor: '#28a74520',
              fill: false,
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 0,
              pointBorderWidth: 0,
              pointBackgroundColor: 'transparent',
              pointHoverBackgroundColor: 'transparent',
              pointHoverBorderColor: 'transparent',
              pointHoverBorderWidth: 0,
              yAxisID: 'y'
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'minute',
                stepSize: 5,
                displayFormats: {
                  second: 'HH:mm:ss',
                  minute: 'HH:mm',
                  hour: 'HH:mm',
                  day: 'MMM dd'
                },
                tooltipFormat: 'HH:mm:ss'
              },
              title: {
                display: true,
                text: 'Time (CDT)'
              },
              ticks: {
                source: 'auto',
                autoSkip: true,
                maxRotation: 45,
                minRotation: 45,
                callback: function(value, index, ticks) {
                  const date = new Date(value)
                  
                  // Standard HH:mm:ss CDT format for all zoom levels
                  return date.toLocaleTimeString('en-US', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    timeZone: 'America/Chicago'
                  }) + ' CDT'
                }
              }
            },
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              beginAtZero: true,
              max: 100,
              title: {
                display: true,
                text: 'Usage (%)'
              },
              grid: {
                drawOnChartArea: true,
              }
            }
          },
          plugins: {
            zoom: {
              pan: {
                enabled: true,
                mode: 'x'
              },
              zoom: {
                wheel: {
                  enabled: true,
                  speed: 0.1,
                  modifierKey: null  // No modifier key needed
                },
                pinch: {
                  enabled: true
                },
                mode: 'x',
                onZoom: handleZoom
              },
              limits: {
                x: {
                  minRange: 30 * 1000,  // Minimum 30 seconds view (maximum zoom in)
                  maxRange: 48 * 60 * 60 * 1000  // Maximum 48 hours view (maximum zoom out)
                }
              }
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                title: function(context) {
                  // Format timestamp to match "Last Update" format
                  const timestamp = context[0].parsed.x
                  return formatTimestamp(timestamp / 1000) // Convert milliseconds to seconds
                },
                label: function(context) {
                  return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
                }
              }
            }
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
          }
        }
      }
    }

    // Create combined chart
    const createCharts = async () => {
      await nextTick()
      
      if (combinedChart.value && !combinedChartInstance) {
        combinedChartInstance = new ChartJS(combinedChart.value, getCombinedChartConfig())
      }
      
      updateCharts()
    }

    // Update chart data
    const updateCharts = () => {
      if (!hostMetrics.value) {
        console.log('No hostMetrics.value available')
        return
      }

      console.log('Host metrics data structure:', hostMetrics.value)

      // Try different possible data structures
      let metrics = []
      if (hostMetrics.value.timeline_data) {
        metrics = hostMetrics.value.timeline_data
      } else if (hostMetrics.value.metrics) {
        metrics = hostMetrics.value.metrics
      } else if (hostMetrics.value.data) {
        metrics = hostMetrics.value.data
      } else if (Array.isArray(hostMetrics.value)) {
        metrics = hostMetrics.value
      }

      console.log('Metrics array:', metrics)
      console.log('Metrics length:', metrics.length)

      if (metrics.length === 0) {
        console.warn('No metrics data available for charts')
        return
      }

      // Log first few items to understand structure
      console.log('Sample metric:', metrics.slice(0, 2))
      
      // Prepare data for charts - try different field names
      const cpuData = metrics.map(metric => {
        const timestamp = metric.timestamp || metric.time || metric.date
        const cpu = metric.cpu_percent || metric.cpu || metric.cpu_usage
        
        return {
          x: new Date(timestamp * 1000),
          y: cpu
        }
      }).filter(item => item.x && item.y !== undefined)
      
      const memoryData = metrics.map(metric => {
        const timestamp = metric.timestamp || metric.time || metric.date
        const memory = metric.memory_percent || metric.memory || metric.memory_usage
        
        return {
          x: new Date(timestamp * 1000),
          y: memory
        }
      }).filter(item => item.x && item.y !== undefined)

      console.log('CPU data for chart:', cpuData.slice(0, 3))
      console.log('Memory data for chart:', memoryData.slice(0, 3))

      // Update combined chart
      if (combinedChartInstance) {
        console.log('Updating chart with CPU points:', cpuData.length, 'Memory points:', memoryData.length)
        combinedChartInstance.data.datasets[0].data = cpuData // CPU dataset
        combinedChartInstance.data.datasets[1].data = memoryData // Memory dataset
        
        // Auto-scroll to show newest data if no specific zoom level is set
        if (!currentZoomLevel.value && cpuData.length > 0) {
          // Set default zoom level to 1h
          const oneHourLevel = zoomLevels.find(level => level.label === '1h')
          if (oneHourLevel) {
            setZoomLevel(oneHourLevel)
          }
        }
        
        combinedChartInstance.update('active')
        
        // If no data, make sure chart is still visible
        if (cpuData.length === 0 && memoryData.length === 0) {
          console.warn('No data points for chart - chart may appear empty')
        }
      } else {
        console.warn('Chart instance not available for update')
      }
    }

    // Set zoom level to show specific time range
    const setZoomLevel = (level) => {
      if (!combinedChartInstance || !hostMetrics.value?.timeline_data) return
      
      currentZoomLevel.value = level.label
      
      // Get the latest data point time
      const timelineData = hostMetrics.value.timeline_data
      const latestTime = Math.max(...timelineData.map(d => d.timestamp * 1000))
      const earliestTime = latestTime - (level.minutes * 60 * 1000)
      
      // Update chart time axis configuration
      combinedChartInstance.options.scales.x.time.unit = level.unit
      
      // Configure zoom level-specific settings
      if (level.label === '1m') {
        // For 1-minute view, use Chart.js default spacing with second precision
        console.log('1m zoom: Using default Chart.js time marker spacing')
        
        // Configure time scale for seconds with default spacing
        combinedChartInstance.options.scales.x.time = {
          ...combinedChartInstance.options.scales.x.time,
          unit: 'second',
          minUnit: 'second'
        }
        
        // Let Chart.js handle tick generation automatically
        combinedChartInstance.options.scales.x.ticks = {
          ...combinedChartInstance.options.scales.x.ticks,
          autoSkip: true,         // Let Chart.js decide spacing
          source: 'auto',         // Optimal tick generation
          maxRotation: 45,        // Angle time markers at 45 degrees
          minRotation: 45,        // Force 45 degrees (don't auto-adjust)
          callback: function(value, index, ticks) {
            const date = new Date(value)
            return date.toLocaleTimeString('en-US', {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              timeZone: 'America/Chicago'
            }) + ' CDT'
          }
        }
        
        console.log(`1m zoom: Time range ${new Date(earliestTime).toISOString()} to ${new Date(latestTime).toISOString()}`)
      } else {
        // Configure for other zoom levels with standard format
        combinedChartInstance.options.scales.x.time = {
          ...combinedChartInstance.options.scales.x.time,
          unit: level.unit,
          minUnit: 'minute'
        }
        
        combinedChartInstance.options.scales.x.ticks = {
          ...combinedChartInstance.options.scales.x.ticks,
          autoSkip: true,
          source: 'auto',
          maxRotation: 45,        // 45-degree angle for all zoom levels
          minRotation: 45,        // Force 45 degrees
          callback: function(value, index, ticks) {
            const date = new Date(value)
            
            // Standard HH:mm:ss CDT format for all zoom levels
            return date.toLocaleTimeString('en-US', {
              hour12: false,
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              timeZone: 'America/Chicago'
            }) + ' CDT'
          }
        }
        
        // Clean up any 1-minute zoom specific properties
        delete combinedChartInstance.options.scales.x.ticks.stepSize
        delete combinedChartInstance.options.scales.x.ticks.maxTicksLimit
      }
      
      // Set the visible range
      combinedChartInstance.options.scales.x.min = earliestTime
      combinedChartInstance.options.scales.x.max = latestTime
      
      // Update the chart
      combinedChartInstance.update('none')
    }
    
    // Reset zoom
    const resetZoom = (chartType) => {
      if (chartType === 'combined' && combinedChartInstance) {
        currentZoomLevel.value = null
        
        // Instead of resetZoom(), use the same logic as 24h button to be consistent
        if (hostMetrics.value?.timeline_data && hostMetrics.value.timeline_data.length > 0) {
          // Get the time range of available data (same as 24h button)
          const timelineData = hostMetrics.value.timeline_data
          const latestTime = Math.max(...timelineData.map(d => d.timestamp * 1000))
          const earliestTime = Math.min(...timelineData.map(d => d.timestamp * 1000))
          
          // Use the full data range, but with same axis configuration as 24h
          combinedChartInstance.options.scales.x.time = {
            ...combinedChartInstance.options.scales.x.time,
            unit: 'hour',      // Same as 24h button
            minUnit: 'minute'
          }
          
          combinedChartInstance.options.scales.x.ticks = {
            ...combinedChartInstance.options.scales.x.ticks,
            autoSkip: true,
            source: 'auto',
            maxRotation: 45,
            minRotation: 45,
            callback: function(value, index, ticks) {
              const date = new Date(value)
              
              // Standard HH:mm:ss CDT format for all zoom levels
              return date.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                timeZone: 'America/Chicago'
              }) + ' CDT'
            }
          }
          
          // Set the visible range to show all available data
          combinedChartInstance.options.scales.x.min = earliestTime
          combinedChartInstance.options.scales.x.max = latestTime
        } else {
          // Fallback to standard reset if no data
          combinedChartInstance.resetZoom()
        }
        
        // Clean up zoom-specific properties
        delete combinedChartInstance.options.scales.x.ticks.stepSize
        delete combinedChartInstance.options.scales.x.ticks.maxTicksLimit
        combinedChartInstance.update('none')
      }
    }

    // Destroy charts
    const destroyCharts = () => {
      if (combinedChartInstance) {
        combinedChartInstance.destroy()
        combinedChartInstance = null
      }
    }

    // Watch for hostname changes
    watch(() => props.hostname, (newHostname) => {
      if (newHostname) {
        fetchHostData()
      }
    })

    // Watch for data changes to update charts
    watch(hostMetrics, () => {
      console.log('hostMetrics watcher triggered')
      updateCharts()
    }, { deep: true })


    // Lifecycle
    onMounted(async () => {
      await fetchHostData()
      await createCharts()
      // Start auto-refresh polling for this host (2 minutes like dashboard)
      systemStore.startHostDetailAutoRefresh(props.hostname, 120000)
    })

    onUnmounted(() => {
      systemStore.stopAutoRefresh()
      systemStore.clearHostData()
      destroyCharts()
    })

    return {
      // Store
      systemStore,
      
      // Data
      zoomLevels,
      currentZoomLevel,
      
      // Refs
      combinedChart,
      
      // Computed
      hostMetrics,
      isLoadingHostDetail,
      hostDetailError,
      hasChartData,
      
      // Methods
      getCpuClass,
      getMemoryClass,
      formatDateTime,
      formatTimestamp,
      refreshData,
      setZoomLevel,
      resetZoom
    }
  }
}
</script>

<style scoped>
.breadcrumb-item a {
  text-decoration: none;
}

.card-body h3 {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 0;
}

.card-title {
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

/* Chart specific styles */
.chart-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-controls .btn {
  font-size: 0.875rem;
}

/* Canvas container */
.card-body canvas {
  max-height: 300px;
  cursor: crosshair;
}

/* Responsive chart height */
@media (max-width: 768px) {
  .card-body canvas {
    max-height: 250px;
  }
}
</style>