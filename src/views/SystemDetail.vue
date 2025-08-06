<template>
  <div class="container mt-4">
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item">
          <router-link to="/">Dashboard</router-link>
        </li>
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
              <h5 class="mb-0">System Usage</h5>
              <div class="chart-controls">
                <button class="btn btn-sm btn-outline-secondary me-2" @click="resetZoom('combined')">
                  <i class="fas fa-search-minus"></i> Reset Zoom
                </button>
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

      <!-- Time Range Info -->
      <div class="card mt-4">
        <div class="card-body">
          <div class="row">
            <div class="col-md-6">
              <p><strong>Time Range:</strong> Last {{ hours }} hours</p>
            </div>
            <div class="col-md-6">
              <p v-if="hostMetrics.first_seen">
                <strong>First Seen:</strong> {{ formatDateTime(hostMetrics.first_seen) }}
              </p>
              <p v-if="hostMetrics.time_range">
                <strong>Last Update:</strong> {{ formatDateTime(hostMetrics.time_range.end) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Time Range Filter -->
    <div class="mt-4">
      <form @submit.prevent="updateTimeRange" class="d-flex align-items-center gap-2">
        <label for="hours" class="form-label mb-0">Time Range:</label>
        <select v-model="hours" id="hours" class="form-select" style="max-width: 200px;">
          <option value="1">Last 1 hour</option>
          <option value="6">Last 6 hours</option>
          <option value="24">Last 24 hours</option>
          <option value="48">Last 48 hours</option>
          <option value="168">Last 7 days</option>
        </select>
        <button type="submit" class="btn btn-primary">Update</button>
        <router-link to="/system" class="btn btn-secondary ms-2">Back to Overview</router-link>
      </form>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '@/stores/system'
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
    const hours = ref(parseInt(route.query.hours) || 24)
    
    // Chart references
    const combinedChart = ref(null)
    let combinedChartInstance = null

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

    const updateTimeRange = async () => {
      console.log('Time range changed to:', hours.value, 'hours')
      
      // Destroy existing chart to ensure clean state
      destroyCharts()
      
      // Fetch new data
      await fetchHostData()
      
      // Recreate chart with new data
      await nextTick()
      await createCharts()
    }

    const fetchHostData = async () => {
      await systemStore.fetchHostMetrics(props.hostname, hours.value)
    }

    const refreshData = async () => {
      await systemStore.refreshHostMetrics(props.hostname, hours.value)
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
                displayFormats: {
                  hour: 'HH:mm',
                  day: 'MMM dd'
                }
              },
              title: {
                display: true,
                text: 'Time'
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
                  enabled: true
                },
                pinch: {
                  enabled: true
                },
                mode: 'x'
              },
              limits: {
                x: {
                  minRange: minRange // Dynamic minimum range based on data density
                }
              }
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
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
        combinedChartInstance.update('active')
        
        // If no data, make sure chart is still visible
        if (cpuData.length === 0 && memoryData.length === 0) {
          console.warn('No data points for chart - chart may appear empty')
        }
      } else {
        console.warn('Chart instance not available for update')
      }
    }

    // Reset zoom
    const resetZoom = (chartType) => {
      if (chartType === 'combined' && combinedChartInstance) {
        combinedChartInstance.resetZoom()
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

    // Watch for hours change to trigger data refresh
    watch(hours, async (newHours, oldHours) => {
      if (oldHours !== undefined) { // Avoid initial trigger
        console.log('Hours changed from', oldHours, 'to', newHours)
        await updateTimeRange()
      }
    })

    // Lifecycle
    onMounted(async () => {
      await fetchHostData()
      await createCharts()
      // Connect to WebSocket for real-time updates instead of polling
      await systemStore.connectToSystemDetailWebSocket(props.hostname)
    })

    onUnmounted(() => {
      systemStore.stopAutoRefresh()
      systemStore.clearHostData()
      systemStore.disconnectWebSockets()
      destroyCharts()
    })

    return {
      // Store
      systemStore,
      
      // Data
      hours,
      
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
      updateTimeRange,
      refreshData,
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