<template>
  <div id="app" class="loading">
    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container">
        <router-link class="navbar-brand" to="/">
          <i class="fas fa-chart-line"></i> PyPerf Dashboard
        </router-link>
        
        <button 
          class="navbar-toggler" 
          type="button" 
          data-bs-toggle="collapse" 
          data-bs-target="#navbarNav"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav me-auto">
            <li class="nav-item">
              <router-link class="nav-link" to="/" exact-active-class="active">
                <i class="fas fa-home"></i> Dashboard
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/system" active-class="active">
                <i class="fas fa-server"></i> System Metrics
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/records" active-class="active">
                <i class="fas fa-list"></i> Performance Records
              </router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/timeline" active-class="active">
                <i class="fas fa-chart-line"></i> Timeline Viewer
              </router-link>
            </li>
          </ul>
          
          <!-- Cache Debug & Dark Mode Toggle -->
          <div class="navbar-nav d-flex flex-row gap-2">
            <button 
              class="btn btn-outline-light btn-sm" 
              data-bs-toggle="modal"
              data-bs-target="#cacheDebugModal"
              title="View cache status"
            >
              <i class="fas fa-database"></i>
            </button>
            <button 
              class="btn btn-outline-light btn-sm" 
              @click="toggleDarkMode"
              :title="isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
            >
              <i :class="isDarkMode ? 'fas fa-sun' : 'fas fa-moon'"></i>
            </button>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Cache Debugger Modal -->
    <CacheDebugger />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import CacheDebugger from '@/components/CacheDebugger.vue'

export default {
  name: 'App',
  components: {
    CacheDebugger
  },
  setup() {
    const isDarkMode = ref(false)

    const toggleDarkMode = () => {
      isDarkMode.value = !isDarkMode.value
      const theme = isDarkMode.value ? 'dark' : 'light'
      
      // Apply theme to both html and body
      document.documentElement.setAttribute('data-theme', theme)
      document.body.setAttribute('data-theme', theme)
      
      // Save preference
      localStorage.setItem('darkMode', isDarkMode.value.toString())
      
      // Debug logging
      console.log(`Theme switched to: ${theme}`)
    }

    onMounted(() => {
      // Initialize dark mode from localStorage
      const savedDarkMode = localStorage.getItem('darkMode')
      if (savedDarkMode !== null) {
        isDarkMode.value = savedDarkMode === 'true'
      } else {
        // Default to system preference
        isDarkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
      }
      
      const theme = isDarkMode.value ? 'dark' : 'light'
      document.documentElement.setAttribute('data-theme', theme)
      document.body.setAttribute('data-theme', theme)
      
      console.log(`Initial theme set to: ${theme}`)
      
      // Remove loading class and mark Vue as loaded
      setTimeout(() => {
        const appElement = document.getElementById('app')
        appElement.classList.remove('loading')
        appElement.classList.add('vue-loaded')
      }, 100)
    })

    return {
      isDarkMode,
      toggleDarkMode
    }
  }
}
</script>

<style>
/* Smooth transitions for navigation */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Loading state */
.loading {
  opacity: 0.95;
}

/* Main content area */
.main-content {
  min-height: calc(100vh - 76px); /* Account for navbar height */
}
</style>