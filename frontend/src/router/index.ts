import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/tasks',
    component: () => import('../layout/AdminLayout.vue'),
    children: [
      {
        path: 'tasks',
        name: 'TaskList',
        component: () => import('../views/TaskList.vue')
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'generate',
        name: 'Generate',
        component: () => import('../views/Generate.vue')
      },
      {
        path: 'task/:id',
        name: 'TaskDetail',
        component: () => import('../views/TaskDetail.vue')
      },
      {
        path: 'config-center',
        redirect: '/config-center/ai'
      },
      {
        path: 'config-center/ai',
        name: 'ConfigCenterAI',
        component: () => import('../views/ConfigCenter.vue')
      },
      {
        path: 'config-center/prompts',
        name: 'ConfigCenterPrompts',
        component: () => import('../views/ConfigCenter.vue')
      },
      {
        path: 'config-center/behavior',
        name: 'ConfigCenterBehavior',
        component: () => import('../views/ConfigCenter.vue')
      },
      {
        path: 'config-center/notifications',
        name: 'ConfigCenterNotifications',
        component: () => import('../views/ConfigCenter.vue')
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
