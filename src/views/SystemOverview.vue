<template>
  <div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="mb-0">System Metrics Overview</h1>
      
      <!-- Refresh Button -->
      <div>
        <button 
          class="btn btn-outline-secondary btn-sm" 
          @click="refreshData"
          :disabled="isLoading"
          title="Refresh data from server"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': isLoading }"></i>
        </button>
      </div>
    </div>
    
    <!-- Summary Cards -->
    <div class="row mb-4">
      <div class="col-md-6">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title">Total Hosts</h5>
            <h2 class="text-primary">{{ dashboardData.total_hosts }}</h2>
          </div>
        </div>
      </div>
      <div class="col-md-6">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title">Status</h5>
            <h2 class="text-success">
              <i class="fas fa-check-circle"></i> Active
            </h2>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="text-center py-4">
      <div class="loading-spinner"></div>
      <p class="mt-2">Loading system data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="dashboardError" class="alert alert-danger">
      <i class="fas fa-exclamation-triangle"></i>
      {{ dashboardError }}
    </div>

    <!-- Hosts Summary -->
    <div v-else class="card">
      <div class="card-header">
        <h3 class="mb-0">System Hosts</h3>
      </div>
      <div class="card-body">
        <div v-if="dashboardData.hosts_summary?.length" class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Hostname</th>
                <th>Current CPU %</th>
                <th>Current Memory %</th>
                <th>Status</th>
                <th>Last Update</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="host in dashboardData.hosts_summary" :key="host.hostname">
                <td>
                  <router-link 
                    :to="{ name: 'SystemDetail', params: { hostname: host.hostname } }"
                    class="text-decoration-none"
                  >
                    <strong>{{ host.hostname }}</strong>
                  </router-link>
                </td>
                <td>
                  <span 
                    class="badge"
                    :class="getCpuBadgeClass(host.current_cpu)"
                  >
                    {{ host.current_cpu?.toFixed(1) }}%
                  </span>
                </td>
                <td>
                  <span 
                    class="badge"
                    :class="getMemoryBadgeClass(host.current_memory)"
                  >
                    {{ host.current_memory?.toFixed(1) }}%
                  </span>
                </td>
                <td>
                  <span 
                    class="badge"
                    :class="host.is_online ? 'bg-success' : 'bg-secondary'"
                  >
                    <i class="fas fa-circle"></i>
                    {{ host.is_online ? 'Online' : 'Offline' }}
                  </span>
                </td>
                <td>
                  <small class="timestamp" :data-timestamp="getTimestamp(host.last_seen)">
                    {{ formatTimestamp(host.last_seen) }}
                  </small>
                  <br>
                  <small class="text-muted">
                    {{ formatDate(host.last_seen) }}
                  </small>
                </td>
                <td>
                  <div class="btn-group btn-group-sm" role="group">
                    <router-link 
                      :to="{ name: 'SystemDetail', params: { hostname: host.hostname } }" 
                      class="btn btn-outline-primary"
                      title="View details"
                    >
                      <i class="fas fa-chart-line"></i>
                    </router-link>
                    <button
                      @click="removeSystem(host.hostname)"
                      class="btn btn-outline-danger"
                      :disabled="isRemoving"
                      title="Remove from dashboard"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div v-else class="alert alert-info">
          <i class="fas fa-info-circle"></i>
          No system data available yet. Make sure the py-perf-daemon is running and uploading data to DynamoDB.
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { formatTimestamp, formatDate } from '@/services/api'

export default {
  name: 'SystemOverview',
  setup() {
    const systemStore = useSystemStore()
    const isRemoving = ref(false)

    // Computed properties
    const dashboardData = computed(() => systemStore.dashboardData)
    const isLoadingDashboard = computed(() => systemStore.isLoadingDashboard)
    const dashboardError = computed(() => systemStore.dashboardError)

    // Methods
    const getCpuBadgeClass = (cpu) => {
      if (cpu <= 60) return 'bg-success'
      if (cpu <= 80) return 'bg-warning text-dark'
      return 'bg-danger'
    }

    const getMemoryBadgeClass = (memory) => {
      if (memory <= 60) return 'bg-success'
      if (memory <= 80) return 'bg-warning text-dark'
      return 'bg-danger'
    }

    const getTimestamp = (lastSeen) => {
      if (!lastSeen) return 0
      // lastSeen is already a timestamp, no need to convert
      return typeof lastSeen === 'number' ? lastSeen : 0
    }


    const refreshData = async () => {
      await systemStore.refreshDashboard()
    }

    const fetchData = async () => {
      await systemStore.fetchDashboardData()
    }

    const removeSystem = async (hostname) => {
      if (!confirm(`Are you sure you want to remove ${hostname} from the dashboard?`)) {
        return
      }
      
      isRemoving.value = true
      try {
        const response = await fetch('/api/system/remove/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ hostname })
        })
        
        const data = await response.json()
        
        if (response.ok) {
          // Refresh the dashboard data
          await systemStore.fetchDashboardData()
          alert(`System ${hostname} has been removed from the dashboard`)
        } else {
          alert(`Failed to remove system: ${data.error || 'Unknown error'}`)
        }
      } catch (error) {
        console.error('Error removing system:', error)
        alert(`Error removing system: ${error.message}`)
      } finally {
        isRemoving.value = false
      }
    }

    // Lifecycle
    onMounted(async () => {
      await fetchData()
      // Start auto-refresh polling for system monitoring updates (2 minutes)
      systemStore.startDashboardAutoRefresh(120000)
    })

    onUnmounted(() => {
      systemStore.stopAutoRefresh()
      systemStore.disconnectWebSockets()
    })

    return {
      // Store
      systemStore,
      
      // Data
      isRemoving,
      
      // Computed
      dashboardData,
      isLoading: isLoadingDashboard,
      dashboardError,
      
      // Methods
      getCpuBadgeClass,
      getMemoryBadgeClass,
      getTimestamp,
      refreshData,
      removeSystem,
      formatTimestamp,
      formatDate
    }
  }
}
</script>

<style scoped>
.timestamp {
  font-family: 'Courier New', monospace;
}

.card-body h2 {
  font-size: 2rem;
  font-weight: bold;
}

.table th {
  border-top: none;
}

.btn-primary {
  transition: all 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-1px);
}
</style>