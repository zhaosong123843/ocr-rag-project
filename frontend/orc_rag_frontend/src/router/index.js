import { createRouter, createWebHistory } from 'vue-router'

// Import your route components here
import AboutView from '../views/AboutView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'about',
      component: AboutView
    },
    {
      path: '/about',
      name: 'about-alt',
      component: AboutView
    }
  ]
})

export default router