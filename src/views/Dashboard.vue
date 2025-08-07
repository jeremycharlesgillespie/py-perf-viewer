<template>
  <div class="container mt-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="mb-0">
        <i class="fas fa-tachometer-alt"></i> Performance Dashboard
      </h1>
      
      <!-- Refresh Button -->
      <div>
        <button 
          class="btn btn-outline-secondary btn-sm" 
          @click="refreshData"
          :disabled="systemStore.isLoadingDashboard"
          title="Refresh data from server"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': systemStore.isLoadingDashboard }"></i>
        </button>
      </div>
    </div>

    <!-- Navigation Buttons -->
    <div class="mb-4">
      <router-link to="/system" class="btn btn-primary me-2">
        <i class="fas fa-server"></i> System Metrics
      </router-link>
      <router-link to="/records" class="btn btn-secondary me-2">
        <i class="fas fa-list"></i> Performance Records
      </router-link>
      <router-link to="/timeline" class="btn btn-secondary">
        <i class="fas fa-chart-line"></i> Timeline Viewer
      </router-link>
    </div>

    <!-- Quick System Summary -->
    <div v-if="systemData.total_hosts > 0" class="row mt-4">
      <div class="col-12">
        <div class="card">
          <div class="card-header bg-primary text-white">
            <h5 class="mb-0">
              <i class="fas fa-server"></i> System Metrics Summary
            </h5>
          </div>
          <div class="card-body">
            <div class="row mb-3">
              <div class="col-md-6">
                <p><strong>Active System Hosts:</strong> {{ systemData.total_hosts }}</p>
                <p><strong>System Records:</strong> {{ systemData.total_records }}</p>
              </div>
              <div class="col-md-6 text-end">
                <router-link to="/system" class="btn btn-primary">
                  View All System Metrics <i class="fas fa-arrow-right"></i>
                </router-link>
              </div>
            </div>
            
            <div v-if="systemData.hosts_summary?.length" class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Hostname</th>
                    <th>Current CPU</th>
                    <th>Current Memory</th>
                    <th>Last Update</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="host in systemData.hosts_summary.slice(0, 3)" :key="host.hostname">
                    <td>
                      <router-link :to="{ name: 'SystemDetail', params: { hostname: host.hostname } }">
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
                      <small class="timestamp">
                        {{ formatTimestamp(host.last_seen) }}
                      </small>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Getting Started -->
    <div v-else class="row mt-4">
      <div class="col-12">
        <div class="text-center py-5">
          <i class="fas fa-chart-line fa-4x text-muted mb-4"></i>
          <h3 class="text-muted">Welcome to PyPerf Dashboard</h3>
          <p class="text-muted mb-4">
            Start monitoring your system performance by ensuring the py-perf-daemon is running.
          </p>
          <router-link to="/system" class="btn btn-primary btn-lg">
            <i class="fas fa-server"></i> Check System Status
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { formatTimestamp } from '@/services/api'

export default {
  name: 'Dashboard',
  setup() {
    const systemStore = useSystemStore()

    // Computed properties
    const systemData = computed(() => systemStore.dashboardData)

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

    const refreshData = async () => {
      await systemStore.refreshDashboard()
    }

    // Lifecycle - defer API call to improve initial load
    onMounted(() => {
      // Load system data after a short delay to prioritize UI rendering
      setTimeout(() => {
        systemStore.fetchDashboardData()
      }, 100)
      
      // Start auto-refresh for dashboard (2 minutes to match data availability)
      systemStore.startDashboardAutoRefresh(120000)
    })

    onUnmounted(() => {
      // Stop auto-refresh when leaving dashboard
      systemStore.stopAutoRefresh()
    })

    return {
      // Store
      systemStore,
      
      // Computed
      systemData,
      
      // Methods
      getCpuBadgeClass,
      getMemoryBadgeClass,
      refreshData,
      formatTimestamp
    }
  }
}
</script>

<style scoped>
.timestamp {
  font-family: 'Courier New', monospace;
}

.btn {
  transition: all 0.2s ease;
}

.btn:hover {
  transform: translateY(-1px);
}

.card {
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  transition: box-shadow 0.3s ease;
}

.card:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}
</style>