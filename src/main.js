import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

// Import custom styles first (smaller)
import '@/assets/css/app.css'

// Lazy load Bootstrap and Font Awesome to speed up initial load
const loadAssets = async () => {
  // Load Bootstrap CSS and JS asynchronously
  await Promise.all([
    import('bootstrap/dist/css/bootstrap.min.css'),
    import('@/assets/css/fontawesome.css')
  ])
  
  // Load Bootstrap JS after CSS (not critical for initial render)
  import('bootstrap/dist/js/bootstrap.bundle.min.js')
}

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Mount app immediately, load assets in background
app.mount('#app')

// Load heavy assets after app is mounted
loadAssets().catch(console.error)