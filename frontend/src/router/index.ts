import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/dashboard',
    component: () => import('../layout/AdminLayout.vue'),
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },

      // 项目管理
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('../views/projects/ProjectList.vue')
      },
      {
        path: 'projects/create',
        name: 'ProjectCreate',
        component: () => import('../views/projects/ProjectForm.vue')
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('../views/projects/ProjectDetail.vue')
      },

      // 需求管理（独立入口，也可从项目详情进入）
      {
        path: 'requirements',
        name: 'RequirementList',
        component: () => import('../views/requirements/RequirementList.vue')
      },
      {
        path: 'requirements/:id',
        name: 'RequirementDetail',
        component: () => import('../views/requirements/RequirementDetail.vue')
      },

      // 人力资源日历（独立入口，也可从项目详情进入）
      {
        path: 'hr-calendar',
        name: 'HRCalendar',
        component: () => import('../views/hr/HRCalendar.vue')
      },

      // 人力管理
      {
        path: 'hr/employees',
        name: 'EmployeeList',
        component: () => import('../views/hr/EmployeeList.vue')
      },

      // ---- 质量中心 ----
      // 测试用例管理
      {
        path: 'test-cases',
        name: 'TestCaseList',
        component: () => import('../views/test-cases/TestCaseList.vue')
      },

      // AI 测试用例
      {
        path: 'ai-testcase/generate',
        name: 'Generate',
        component: () => import('../views/Generate.vue')
      },
      {
        path: 'ai-testcase/tasks',
        name: 'TaskList',
        component: () => import('../views/TaskList.vue')
      },
      {
        path: 'ai-testcase/task/:id',
        name: 'TaskDetail',
        component: () => import('../views/TaskDetail.vue')
      },
      // 测试用例管理
      {
        path: 'test-cases',
        name: 'TestCaseList',
        component: () => import('../views/test-cases/TestCaseList.vue')
      },
      {
        path: 'test-cases/strategies',
        name: 'TestStrategyList',
        component: () => import('../views/test-cases/TestExecutionList.vue')
      },
      {
        path: 'test-cases/strategies/:id',
        name: 'TestStrategyDetail',
        component: () => import('../views/test-cases/TestExecutionDetail.vue')
      },
      {
        path: 'test-cases/reports/:id',
        name: 'TestReportDetail',
        component: () => import('../views/test-cases/TestReportDetail.vue')
      },
      {
        path: 'test-cases/:id',
        name: 'TestCaseDetail',
        component: () => import('../views/test-cases/TestCaseDetail.vue')
      },

      // 效率提升
      {
        path: 'efficiency/database',
        name: 'DatabaseTool',
        component: () => import('../views/efficiency/DatabaseTool.vue')
      },
      {
        path: 'efficiency/server',
        name: 'ServerTool',
        component: () => import('../views/efficiency/ServerTool.vue')
      },

      // 接口自动化
      {
        path: 'api-automation/endpoints',
        name: 'ApiEndpoints',
        component: () => import('../views/api-automation/ApiEndpoints.vue')
      },
      {
        path: 'api-automation/executions',
        name: 'ApiExecutions',
        component: () => import('../views/api-automation/ApiExecutions.vue')
      },
      // 性能管理
      {
        path: 'performance/scenarios',
        name: 'PerfScenarios',
        component: () => import('../views/performance/PerfScenarios.vue')
      },
      {
        path: 'performance/reports',
        name: 'PerfReports',
        component: () => import('../views/performance/PerfReports.vue')
      },

      // 缺陷管理
      {
        path: 'defects',
        name: 'DefectList',
        component: () => import('../views/defects/DefectList.vue')
      },
      {
        path: 'defects/:id',
        name: 'DefectDetail',
        component: () => import('../views/defects/DefectDetail.vue')
      },

      // 配置中心
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
        path: 'config-center/role-configs',
        name: 'ConfigCenterRoleConfigs',
        component: () => import('../views/RoleModelMapping.vue')
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
      },
      {
        path: 'config-center/skills',
        name: 'ConfigCenterSkills',
        component: () => import('../views/SkillsCenter.vue')
      },

      // 兼容旧路由
      {
        path: 'tasks',
        redirect: '/ai-testcase/tasks'
      },
      {
        path: 'generate',
        redirect: '/ai-testcase/generate'
      },
      {
        path: 'task/:id',
        redirect: to => `/ai-testcase/task/${to.params.id}`
      },
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

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/dashboard'
  }
  return true
})

export default router
