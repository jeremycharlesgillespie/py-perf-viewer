<template>
  <div class="modal fade" id="cacheDebugModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="fas fa-database"></i> Cache Status
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        
        <div class="modal-body">
          <!-- Cache Statistics -->
          <div class="row mb-4">
            <div class="col-md-4">
              <div class="card text-center">
                <div class="card-body">
                  <h6 class="card-title">Total Cache Entries</h6>
                  <h4 class="text-info">{{ cacheStats.pyperfEntries }}</h4>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card text-center">
                <div class="card-body">
                  <h6 class="card-title">Cache Size</h6>
                  <h4 class="text-success">{{ formatBytes(cacheStats.totalSize) }}</h4>
                </div>
              </div>
            </div>
            <div class="col-md-4">
              <div class="card text-center">
                <div class="card-body">
                  <h6 class="card-title">Expired Entries</h6>
                  <h4 class="text-warning">{{ expiredCount }}</h4>
                </div>
              </div>
            </div>
          </div>

          <!-- Cache Entries Table -->
          <div v-if="cacheStats.entries?.length" class="table-responsive">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>Cache Key</th>
                  <th>Age</th>
                  <th>TTL</th>
                  <th>Size</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in cacheStats.entries" :key="entry.key">
                  <td>
                    <small class="font-monospace">{{ formatCacheKey(entry.key) }}</small>
                  </td>
                  <td>{{ entry.age }}s</td>
                  <td>{{ entry.ttl }}s</td>
                  <td>{{ formatBytes(entry.size) }}</td>
                  <td>
                    <span 
                      class="badge" 
                      :class="entry.expired ? 'bg-warning' : 'bg-success'"
                    >
                      {{ entry.expired ? 'Expired' : 'Valid' }}
                    </span>
                  </td>
                  <td>
                    <button 
                      class="btn btn-outline-danger btn-sm"
                      @click="clearSpecificCache(entry.key)"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            No cache entries found.
          </div>
        </div>
        
        <div class="modal-footer">
          <button 
            type="button" 
            class="btn btn-warning" 
            @click="cleanupExpired"
          >
            <i class="fas fa-broom"></i> Cleanup Expired
          </button>
          <button 
            type="button" 
            class="btn btn-danger" 
            @click="clearAllCache"
          >
            <i class="fas fa-trash-alt"></i> Clear All Cache
          </button>
          <button 
            type="button" 
            class="btn btn-secondary" 
            @click="refreshStats"
          >
            <i class="fas fa-sync-alt"></i> Refresh
          </button>
          <button 
            type="button" 
            class="btn btn-primary" 
            data-bs-dismiss="modal"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { 
  getCacheStats, 
  clearAllCaches, 
  cleanupExpiredCache, 
  clearCache 
} from '@/utils/cache'

export default {
  name: 'CacheDebugger',
  setup() {
    const cacheStats = ref({
      totalEntries: 0,
      pyperfEntries: 0,
      totalSize: 0,
      entries: []
    })

    // Computed properties
    const expiredCount = computed(() => {
      return cacheStats.value.entries?.filter(entry => entry.expired).length || 0
    })

    // Methods
    const refreshStats = () => {
      cacheStats.value = getCacheStats()
    }

    const clearAllCache = () => {
      clearAllCaches()
      refreshStats()
    }

    const cleanupExpired = () => {
      cleanupExpiredCache()
      refreshStats()
    }

    const clearSpecificCache = (key) => {
      clearCache(key)
      refreshStats()
    }

    const formatBytes = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
    }

    const formatCacheKey = (key) => {
      // Make cache keys more readable
      return key
        .replace('pyperf_', '')
        .replace('_', ' ')
        .replace(/([A-Z])/g, ' $1')
        .trim()
    }

    // Initialize on mount
    onMounted(() => {
      refreshStats()
    })

    return {
      cacheStats,
      expiredCount,
      refreshStats,
      clearAllCache,
      cleanupExpired,
      clearSpecificCache,
      formatBytes,
      formatCacheKey
    }
  }
}
</script>

<style scoped>
.font-monospace {
  font-family: 'Courier New', monospace;
}

.table th {
  border-top: none;
  font-weight: 600;
}

.modal-body {
  max-height: 70vh;
  overflow-y: auto;
}
</style>