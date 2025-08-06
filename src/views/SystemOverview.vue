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
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title">Total Hosts</h5>
            <h2 class="text-primary">{{ dashboardData.total_hosts }}</h2>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title">Total Records</h5>
            <h2 class="text-success">{{ dashboardData.total_records }}</h2>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title">Time Range</h5>
            <p class="mb-0">{{ hours }} hours</p>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h5 class="card-title">Status</h5>
            <p class="mb-0 text-success">
              <i class="fas fa-check-circle"></i> Active
            </p>
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
                  <router-link 
                    :to="{ name: 'SystemDetail', params: { hostname: host.hostname } }" 
                    class="btn btn-sm btn-primary"
                  >
                    <i class="fas fa-chart-line"></i> Investigate
                  </router-link>
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
      </form>
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
    const hours = ref(24)

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

    const updateTimeRange = () => {
      fetchData()
    }

    const refreshData = async () => {
      await systemStore.refreshDashboard()
    }

    const fetchData = async () => {
      await systemStore.fetchDashboardData()
    }

    // Lifecycle
    onMounted(async () => {
      await fetchData()
      // Connect to WebSocket for real-time updates instead of polling
      await systemStore.connectToDashboardWebSocket()
    })

    onUnmounted(() => {
      systemStore.stopAutoRefresh()
      systemStore.disconnectWebSockets()
    })

    return {
      // Store
      systemStore,
      
      // Data
      hours,
      
      // Computed
      dashboardData,
      isLoading: isLoadingDashboard,
      dashboardError,
      
      // Methods
      getCpuBadgeClass,
      getMemoryBadgeClass,
      getTimestamp,
      updateTimeRange,
      refreshData,
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