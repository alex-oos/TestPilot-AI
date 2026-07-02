<template>
  <div class="space-y-6">
    <!-- Welcome Section -->
    <div class="rounded-2xl p-8 text-white shadow-lg relative overflow-hidden"
      :class="isAdmin ? 'bg-gradient-to-r from-slate-800 to-slate-900' : 'bg-gradient-to-r from-indigo-500 to-purple-600'">
      <div class="relative z-10">
        <div class="flex items-center gap-3 mb-2">
          <h1 class="text-3xl font-bold">{{ welcomeText }} 👋</h1>
          <span v-if="isAdmin" class="px-3 py-1 bg-amber-500 text-white text-xs font-bold rounded-full shadow">超级管理员</span>
        </div>
        <p class="text-indigo-100 max-w-xl text-lg" :class="isAdmin ? '!text-slate-300' : ''">
          {{ roleDesc }}
        </p>
      </div>
      <div class="absolute right-0 top-0 w-64 h-64 bg-white opacity-10 rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2"></div>
      <div class="absolute right-40 bottom-0 w-48 h-48 bg-white opacity-10 rounded-full blur-2xl transform translate-y-1/2"></div>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6" :class="isAdmin ? 'lg:grid-cols-6' : 'lg:grid-cols-4'" v-loading="loading">
      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-blue-50 text-blue-600 rounded-xl"><span class="text-xl">📁</span></div>
        </div>
        <h3 class="text-slate-500 text-sm font-medium">{{ isAdmin ? '全部项目' : '参与项目' }}</h3>
        <p class="text-3xl font-bold text-slate-800 mt-1">{{ roleData.summary.total_projects }}</p>
      </div>
      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-green-50 text-green-600 rounded-xl"><span class="text-xl">🚀</span></div>
        </div>
        <h3 class="text-slate-500 text-sm font-medium">进行中项目</h3>
        <p class="text-3xl font-bold text-slate-800 mt-1">{{ roleData.summary.active_projects }}</p>
      </div>
      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-indigo-50 text-indigo-600 rounded-xl"><span class="text-xl">📝</span></div>
        </div>
        <h3 class="text-slate-500 text-sm font-medium">{{ isAdmin ? '全部需求' : '相关需求' }}</h3>
        <p class="text-3xl font-bold text-slate-800 mt-1">{{ roleData.summary.total_requirements }}</p>
      </div>
      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 rounded-xl" :class="roleData.summary.open_bugs > 0 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'">
            <span class="text-xl">🐛</span>
          </div>
        </div>
        <h3 class="text-slate-500 text-sm font-medium">待处理缺陷</h3>
        <p class="text-3xl font-bold mt-1" :class="roleData.summary.open_bugs > 0 ? 'text-red-600' : 'text-slate-800'">{{ roleData.summary.open_bugs }}</p>
      </div>
      <!-- Admin extra cards -->
      <div v-if="isAdmin" class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-purple-50 text-purple-600 rounded-xl"><span class="text-xl">🐞</span></div>
        </div>
        <h3 class="text-slate-500 text-sm font-medium">全部缺陷</h3>
        <p class="text-3xl font-bold text-slate-800 mt-1">{{ roleData.summary.total_defects || 0 }}</p>
      </div>
      <div v-if="isAdmin" class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-cyan-50 text-cyan-600 rounded-xl"><span class="text-xl">👥</span></div>
        </div>
        <h3 class="text-slate-500 text-sm font-medium">在职人员</h3>
        <p class="text-3xl font-bold text-slate-800 mt-1">{{ roleData.summary.total_employees || 0 }}</p>
      </div>
    </div>

    <!-- Admin: Team Overview -->
    <div v-if="isAdmin && roleData.team_overview" class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
      <h3 class="text-lg font-semibold text-slate-800 mb-4">团队角色分布</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-blue-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-blue-700">{{ roleData.team_overview.product || 0 }}</div>
          <div class="text-xs text-blue-500 mt-1 font-medium">产品人员</div>
        </div>
        <div class="bg-indigo-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-indigo-700">{{ roleData.team_overview.developer || 0 }}</div>
          <div class="text-xs text-indigo-500 mt-1 font-medium">开发人员</div>
        </div>
        <div class="bg-green-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-green-700">{{ roleData.team_overview.tester || 0 }}</div>
          <div class="text-xs text-green-500 mt-1 font-medium">测试工程师</div>
        </div>
        <div class="bg-slate-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-slate-700">{{ roleData.team_overview.other || 0 }}</div>
          <div class="text-xs text-slate-500 mt-1 font-medium">其他</div>
        </div>
      </div>
    </div>

    <!-- Module Quick Access -->
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
      <router-link to="/projects" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">📁</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">项目管理</div>
      </router-link>
      <router-link to="/requirements" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">📝</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">需求管理</div>
      </router-link>
      <router-link to="/hr-calendar" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">📅</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">资源日历</div>
      </router-link>
      <router-link to="/hr/employees" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">👥</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">人力管理</div>
      </router-link>
      <router-link to="/ai-testcase/generate" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">🤖</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">AI 用例</div>
      </router-link>
      <router-link to="/api-automation/endpoints" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">🔌</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">接口自动化</div>
      </router-link>
      <router-link to="/performance/scenarios" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">⚡</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">性能管理</div>
      </router-link>
      <router-link to="/defects" class="bg-white rounded-xl p-4 border border-slate-100 shadow-sm hover:shadow-md transition-all text-center group">
        <div class="text-2xl mb-2">🐛</div>
        <div class="text-xs font-medium text-slate-600 group-hover:text-indigo-600">缺陷管理</div>
      </router-link>
    </div>

    <!-- Project Cards -->
    <div v-if="roleData.projects.length > 0" class="space-y-4">
      <h2 class="text-xl font-bold text-slate-800">{{ isAdmin ? '全部项目概览' : '我的项目' }}</h2>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div
          v-for="proj in roleData.projects"
          :key="proj.project_id"
          class="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden hover:shadow-md transition-shadow"
        >
          <!-- Project Header -->
          <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div class="flex items-center gap-3 min-w-0">
              <router-link :to="`/projects/${proj.project_id}`" class="text-lg font-bold text-slate-800 hover:text-indigo-600 truncate transition-colors">
                {{ proj.project_name }}
              </router-link>
              <span class="shrink-0 text-xs font-medium px-2.5 py-1 rounded-full" :class="statusBadge(proj.project_status)">
                {{ proj.project_status_label }}
              </span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <div v-if="proj.open_bugs > 0" class="flex items-center gap-1 text-red-500 bg-red-50 px-2.5 py-1 rounded-full text-xs font-semibold">
                🐛 {{ proj.open_bugs }} 个缺陷
              </div>
              <div v-else class="flex items-center gap-1 text-green-500 bg-green-50 px-2.5 py-1 rounded-full text-xs font-semibold">
                ✅ 无缺陷
              </div>
            </div>
          </div>

          <!-- Admin view: requirement status distribution -->
          <div v-if="isAdmin && proj.requirement_status_dist" class="px-6 py-3 border-b border-slate-50 bg-slate-50/50">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs text-slate-500 font-medium">需求 {{ proj.requirement_count || 0 }}:</span>
              <span v-for="(cnt, label) in proj.requirement_status_dist" :key="String(label)" class="text-[11px] px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-600">
                {{ label }} <span class="font-bold text-slate-800">{{ cnt }}</span>
              </span>
            </div>
          </div>

          <!-- Role view: requirements list -->
          <div v-if="!isAdmin && proj.requirements?.length" class="p-4 space-y-3 max-h-[320px] overflow-y-auto">
            <div
              v-for="req in proj.requirements"
              :key="req.id"
              class="bg-slate-50 rounded-xl p-4 hover:bg-slate-100 transition-colors"
            >
              <div class="flex items-center justify-between mb-2">
                <router-link :to="`/requirements/${req.id}`" class="text-sm font-semibold text-slate-700 hover:text-indigo-600 truncate transition-colors">
                  {{ req.title }}
                </router-link>
                <span class="text-[11px] font-medium px-2 py-0.5 rounded-md shrink-0 ml-2" :class="reqStatusBadge(req.status)">
                  {{ req.status_label }}
                </span>
              </div>
              <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                <span class="flex items-center gap-1">
                  <span class="font-medium text-slate-600">优先级:</span>
                  <span :class="priorityClass(req.priority)">{{ priorityLabel(req.priority) }}</span>
                </span>
                <span v-if="(roleData.role === 'developer' || roleData.role === 'tester') && req.testing_time" class="flex items-center gap-1">
                  <span class="font-medium text-slate-600">提测时间:</span>
                  <span class="text-indigo-600 font-medium">{{ req.testing_time }}</span>
                </span>
                <span v-if="req.my_nodes?.length" class="flex items-center gap-1">
                  <span class="font-medium text-slate-600">我的节点:</span>
                  <span v-for="(nd, idx) in req.my_nodes" :key="idx" class="inline-flex items-center gap-0.5">
                    <span class="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded text-[10px] font-medium">{{ nd.node_label }}</span>
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && (hasEmployee || isAdmin)" class="bg-white rounded-2xl p-12 border border-slate-100 shadow-sm text-center">
      <div class="text-5xl mb-4">📭</div>
      <h3 class="text-lg font-semibold text-slate-700 mb-2">暂无项目数据</h3>
      <p class="text-sm text-slate-400">{{ isAdmin ? '系统中暂无项目，请先在项目管理中创建' : '当您被分配到需求节点后，关联的项目将在这里显示' }}</p>
    </div>

    <!-- Fallback for non-admin, non-employee users -->
    <div v-if="!hasEmployee && !isAdmin" class="space-y-6">
      <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
        <span class="text-2xl">💡</span>
        <div>
          <p class="text-sm font-medium text-amber-800">当前账号未关联员工身份</p>
          <p class="text-xs text-amber-600">请在人力管理中为该账号绑定员工记录，即可看到角色专属看板</p>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div class="flex justify-between items-start mb-4">
            <div class="p-3 bg-blue-50 text-blue-600 rounded-xl"><span class="text-xl">📄</span></div>
            <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.documents_week_change_pct)">
              {{ trendText(overview.trends.documents_week_change_pct) }}
            </span>
          </div>
          <h3 class="text-slate-500 text-sm font-medium">已解析文档总量</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ numberText(overview.summary.total_documents) }}</p>
        </div>
        <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div class="flex justify-between items-start mb-4">
            <div class="p-3 bg-indigo-50 text-indigo-600 rounded-xl"><span class="text-xl">⚡</span></div>
            <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.generated_week_change_pct)">
              {{ trendText(overview.trends.generated_week_change_pct) }}
            </span>
          </div>
          <h3 class="text-slate-500 text-sm font-medium">已生成用例总数</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ numberText(overview.summary.generated_cases_total) }}</p>
        </div>
        <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div class="flex justify-between items-start mb-4">
            <div class="p-3 bg-green-50 text-green-600 rounded-xl"><span class="text-xl">✔️</span></div>
            <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.coverage_week_change_pct, true)">
              {{ trendText(overview.trends.coverage_week_change_pct) }}
            </span>
          </div>
          <h3 class="text-slate-500 text-sm font-medium">测试用例覆盖率</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ percentText(overview.summary.coverage_rate) }}</p>
        </div>
        <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
          <div class="flex justify-between items-start mb-4">
            <div class="p-3 bg-orange-50 text-orange-600 rounded-xl"><span class="text-xl">⏱️</span></div>
            <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.average_duration_week_change_pct)">
              {{ trendText(overview.trends.average_duration_week_change_pct) }}
            </span>
          </div>
          <h3 class="text-slate-500 text-sm font-medium">平均生成耗时</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ durationText(overview.summary.average_duration_seconds) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { getDashboardOverview } from '../api/dashboard'
import request from '../utils/request'

const userStore = useUserStore()
const loading = ref(false)
const isAdmin = computed(() => userStore.username === 'admin')
const hasEmployee = computed(() => !!userStore.employeeId)

const roleData = ref<{
  role: string
  role_label: string
  employee_name: string
  position: string
  projects: any[]
  summary: Record<string, number>
  team_overview?: Record<string, number>
}>({
  role: '',
  role_label: '',
  employee_name: '',
  position: '',
  projects: [],
  summary: { total_projects: 0, active_projects: 0, total_requirements: 0, open_bugs: 0 },
})

const welcomeText = computed(() => {
  if (isAdmin.value) return '欢迎回来，管理员！'
  if (roleData.value.employee_name) return `欢迎回来，${roleData.value.employee_name}！`
  return `欢迎回来，${userStore.username || '用户'}！`
})

const roleDesc = computed(() => {
  const r = roleData.value
  if (isAdmin.value) {
    const s = r.summary
    return `超级管理员全局视图 | ${s.total_projects || 0} 个项目、${s.total_requirements || 0} 个需求、${s.open_bugs || 0} 个待处理缺陷、${s.total_employees || 0} 名在职人员`
  }
  if (!r.role) return '这是您的工作台，请查看今日待办事项。'
  const roleName = r.position || r.role_label || r.role
  const active = r.summary.active_projects
  const bugs = r.summary.open_bugs
  if (r.role === 'product') return `${roleName} | 您当前有 ${active} 个进行中项目，${r.summary.total_requirements} 个相关需求。`
  if (r.role === 'developer') return `${roleName} | 您当前有 ${active} 个进行中项目，${bugs} 个待处理缺陷。`
  if (r.role === 'tester') return `${roleName} | 您当前有 ${active} 个进行中项目，${bugs} 个未解决缺陷需要跟踪。`
  return `${roleName} | 您当前有 ${active} 个进行中项目。`
})

interface DashboardOverview {
  summary: { total_documents: number; generated_cases_total: number; coverage_rate: number; average_duration_seconds: number; this_week_new_count: number }
  trends: { documents_week_change_pct: number | null; generated_week_change_pct: number | null; coverage_week_change_pct: number | null; average_duration_week_change_pct: number | null }
  weekly_activity: Array<{ label: string; value: number }>
  source_distribution: any[]
}
const overview = ref<DashboardOverview>({
  summary: { total_documents: 0, generated_cases_total: 0, coverage_rate: 0, average_duration_seconds: 0, this_week_new_count: 0 },
  trends: { documents_week_change_pct: null, generated_week_change_pct: null, coverage_week_change_pct: null, average_duration_week_change_pct: null },
  weekly_activity: [],
  source_distribution: [],
})

onMounted(async () => {
  loading.value = true
  try {
    if (isAdmin.value) {
      const resp = await request.get('/dashboard/admin-view')
      if (resp.data?.data) roleData.value = resp.data.data
    } else {
      const empId = userStore.employeeId
      if (empId) {
        const resp = await request.get('/dashboard/role-view', { params: { employee_id: empId } })
        if (resp.data?.data) roleData.value = resp.data.data
      } else if (userStore.userId) {
        try {
          const infoResp = await request.get('/dashboard/my-info', { params: { user_id: userStore.userId } })
          const empData = infoResp.data?.data
          if (empData) {
            userStore.setEmployee(empData)
            const resp = await request.get('/dashboard/role-view', { params: { employee_id: empData.id } })
            if (resp.data?.data) roleData.value = resp.data.data
          }
        } catch {}
      }

      if (!hasEmployee.value && !isAdmin.value) {
        try {
          const resp = await getDashboardOverview()
          if (resp.data?.code === 0 && resp.data?.data) overview.value = { ...overview.value, ...resp.data.data }
        } catch {}
      }
    }
  } catch (e: any) {
    ElMessage.error('加载看板数据失败')
  } finally {
    loading.value = false
  }
})

function statusBadge(status: string) {
  const map: Record<string, string> = {
    active: 'bg-green-100 text-green-700', approved: 'bg-blue-100 text-blue-700',
    draft: 'bg-slate-100 text-slate-600', archived: 'bg-gray-100 text-gray-500',
    suspended: 'bg-orange-100 text-orange-700',
  }
  return map[status] || 'bg-slate-100 text-slate-600'
}

function reqStatusBadge(status: string) {
  const map: Record<string, string> = {
    requirement_review: 'bg-slate-100 text-slate-600', tech_review: 'bg-blue-100 text-blue-700',
    case_review: 'bg-indigo-100 text-indigo-700', testing: 'bg-amber-100 text-amber-700',
    acceptance: 'bg-purple-100 text-purple-700', released: 'bg-green-100 text-green-700',
    regression: 'bg-teal-100 text-teal-700',
  }
  return map[status] || 'bg-slate-100 text-slate-600'
}

function priorityLabel(p: string) { return { critical: '紧急', high: '高', medium: '中', low: '低' }[p] || p }
function priorityClass(p: string) {
  const map: Record<string, string> = { critical: 'text-red-600 font-semibold', high: 'text-orange-600 font-semibold', medium: 'text-slate-600', low: 'text-slate-400' }
  return map[p] || 'text-slate-600'
}

function numberText(v: number) { return Number(v || 0).toLocaleString('zh-CN') }
function percentText(v: number) { return `${Number(v || 0).toFixed(1)}%` }
function durationText(v: number) { return `${Number(v || 0).toFixed(1)}s` }
function trendText(v: number | null) { if (v === null || Number.isNaN(v)) return '--'; const n = Number(v); return n > 0 ? `+${n.toFixed(1)}%` : `${n.toFixed(1)}%` }
function trendClass(v: number | null, neutralWhenZero = false) { if (v === null || Number.isNaN(v) || (neutralWhenZero && v === 0)) return 'text-slate-400 bg-slate-50'; return v! >= 0 ? 'text-green-500 bg-green-50' : 'text-red-500 bg-red-50' }
</script>
