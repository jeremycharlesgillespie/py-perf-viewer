import { createRouter, createWebHistory } from 'vue-router'

// Import views
import Dashboard from '@/views/Dashboard.vue'
import SystemOverview from '@/views/SystemOverview.vue'
import SystemDetail from '@/views/SystemDetail.vue'
import PerformanceRecords from '@/views/PerformanceRecords.vue'
import RecordDetail from '@/views/RecordDetail.vue'
import FunctionAnalysis from '@/views/FunctionAnalysis.vue'
import TimelineViewer from '@/views/TimelineViewer.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { title: 'PyPerf Dashboard - Home' }
  },
  {
    path: '/system',
    name: 'SystemOverview',
    component: SystemOverview,
    meta: { title: 'System Metrics Overview' }
  },
  {
    path: '/system/:hostname',
    name: 'SystemDetail',
    component: SystemDetail,
    props: true,
    meta: { title: 'System Metrics Detail' }
  },
  {
    path: '/records',
    name: 'PerformanceRecords',
    component: PerformanceRecords,
    meta: { title: 'Performance Records' }
  },
  {
    path: '/records/:recordId',
    name: 'RecordDetail',
    component: RecordDetail,
    props: true,
    meta: { title: 'Record Detail' }
  },
  {
    path: '/functions/:functionName',
    name: 'FunctionAnalysis',
    component: FunctionAnalysis,
    props: true,
    meta: { title: 'Function Analysis' }
  },
  {
    path: '/timeline',
    name: 'TimelineViewer',
    component: TimelineViewer,
    meta: { title: 'Timeline Viewer' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Update page title on route change
router.afterEach((to) => {
  document.title = to.meta.title || 'PyPerf Dashboard'
})

export default router