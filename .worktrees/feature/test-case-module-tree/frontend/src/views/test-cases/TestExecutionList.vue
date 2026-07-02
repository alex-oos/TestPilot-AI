<template>
  <div class="flex h-full" v-loading="pageLoading">
    <!-- Left Module Sidebar -->
    <div class="w-[220px] flex-shrink-0 border-r border-gray-200 bg-white overflow-y-auto">
      <div class="p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-gray-700">策略模块</h3>
          <span class="text-xs text-gray-400">{{ total }} 条</span>
        </div>
        <div
          class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="selectedModule === null ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'"
          @click="selectModule(null)"
        >
          <span class="text-sm font-medium">📋 全部测试策略</span>
          <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{{ total }}</span>
        </div>
        <div
          class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="selectedModule === 'unplanned' ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-500'"
          @click="selectModule('unplanned')"
        >
          <span class="text-sm">📂 未规划策略</span>
        </div>

        <div class="mt-3 mb-2 px-1">
          <span class="text-[10px] font-semibold uppercase tracking-widest text-gray-400">按项目分类</span>
        </div>
        <div
          v-for="p in projectOptions"
          :key="p.id"
          class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="selectedModule === `project_${p.id}` ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'"
          @click="selectModule(`project_${p.id}`)"
        >
          <span class="text-sm truncate">📁 {{ p.name }}</span>
        </div>
      </div>
    </div>

    <!-- Right Main Area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Action Bar -->
      <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-white">
        <div class="flex items-center gap-2">
          <el-button type="primary" color="#7c3aed" class="!rounded-lg" @click="openCreateDialog">
            <el-icon class="mr-1"><Plus /></el-icon>新建
          </el-button>
        </div>
        <div class="flex items-center gap-3">
          <el-select v-model="filters.status" clearable placeholder="状态" size="small" class="!w-28" @change="fetchList">
            <el-option label="未开始" value="pending" />
            <el-option label="进行中" value="running" />
            <el-option label="已完成" value="completed" />
            <el-option label="已中止" value="aborted" />
          </el-select>
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="搜索策略名称..."
            size="small"
            class="!w-52"
            @keyup.enter="fetchList"
            @clear="fetchList"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button size="small" @click="fetchList" class="!rounded-lg">筛选</el-button>
        </div>
      </div>

      <!-- Table -->
      <div class="flex-1 overflow-auto">
        <el-table :data="executions" stripe class="w-full" empty-text="暂无策略记录" row-class-name="cursor-pointer">
          <el-table-column type="selection" width="40" />
          <el-table-column label="ID" prop="id" width="80" align="center">
            <template #default="{ row }">
              <router-link :to="`/test-cases/strategies/${row.id}`" class="text-indigo-600 hover:text-indigo-800 font-mono">
                {{ row.id }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="测试策略名称" min-width="220">
            <template #default="{ row }">
              <router-link :to="`/test-cases/strategies/${row.id}`" class="text-gray-900 hover:text-indigo-700 font-medium">
                {{ row.title }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag
                :type="execStatusType(row.status)"
                :class="row.status === 'running' ? 'animate-pulse' : ''"
                effect="dark" size="small" round
              >
                {{ execStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建人" width="100" align="center">
            <template #default="{ row }">
              <span class="text-sm text-gray-600">{{ row.executor_name || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="通过率" width="200">
            <template #default="{ row }">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden flex">
                  <div
                    v-if="row.passed_cases > 0"
                    class="h-full bg-green-500"
                    :style="{ width: passRate(row) + '%' }"
                  />
                  <div
                    v-if="row.failed_cases > 0"
                    class="h-full bg-red-500"
                    :style="{ width: failRate(row) + '%' }"
                  />
                </div>
                <span class="text-xs text-gray-500 w-12 text-right">{{ passRate(row).toFixed(1) }}%</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="用例数" width="80" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" class="!font-semibold" @click="router.push(`/test-cases/strategies/${row.id}`)">
                {{ row.total_cases || 0 }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column label="Bug数" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.failed_cases > 0" class="text-red-500 font-semibold">{{ row.failed_cases }}</span>
              <span v-else class="text-gray-400">0</span>
            </template>
          </el-table-column>
          <el-table-column label="所属模块" width="140">
            <template #default="{ row }">
              <span class="text-sm text-gray-500">{{ getProjectName(row.project_id) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              <span class="text-xs text-gray-500">{{ formatTime(row.created_at || row.started_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <div class="flex items-center gap-1">
                <el-button size="small" type="primary" link @click="router.push(`/test-cases/strategies/${row.id}`)">执行</el-button>
                <el-button size="small" type="danger" link @click="handleDeleteExec(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-white">
        <span class="text-sm text-gray-500">共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          small
          @current-change="fetchList"
        />
      </div>
    </div>

    <!-- Create Dialog -->
    <el-dialog v-model="createDialogVisible" title="新建测试策略" width="800px" class="!rounded-2xl" destroy-on-close>
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="策略名称" required>
          <el-input v-model="createForm.title" placeholder="输入策略名称" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-x-4">
          <el-form-item label="策略类型">
            <el-select v-model="createForm.plan_type" class="w-full">
              <el-option label="手动执行" value="manual" />
              <el-option label="回归测试" value="regression" />
              <el-option label="冒烟测试" value="smoke" />
            </el-select>
          </el-form-item>
          <el-form-item label="所属项目">
            <el-select v-model="createForm.project_id" clearable placeholder="选择项目" class="w-full">
              <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="执行人">
            <el-select v-model="createForm.executor_id" clearable filterable placeholder="选择执行人" class="w-full">
              <el-option v-for="u in executorOptions" :key="u.user_id" :label="u.name" :value="u.user_id" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="关联用例">
          <div class="w-full border border-gray-200 rounded-xl overflow-hidden">
            <div class="bg-gray-50 px-4 py-2 flex items-center gap-3 border-b border-gray-200">
              <el-input v-model="caseFilter.keyword" placeholder="搜索用例..." clearable size="small" class="!w-48" @clear="fetchCasesForSelect" @keyup.enter="fetchCasesForSelect" />
              <el-select v-model="caseFilter.priority" clearable placeholder="优先级" size="small" class="!w-28" @change="fetchCasesForSelect">
                <el-option label="P0" value="P0" />
                <el-option label="P1" value="P1" />
                <el-option label="P2" value="P2" />
                <el-option label="P3" value="P3" />
              </el-select>
              <el-input v-model="caseFilter.module" placeholder="模块" clearable size="small" class="!w-32" @clear="fetchCasesForSelect" @keyup.enter="fetchCasesForSelect" />
              <span class="text-sm text-gray-500 ml-auto">已选 <b class="text-indigo-600">{{ createForm.case_ids.length }}</b> 条</span>
            </div>
            <div class="max-h-64 overflow-y-auto">
              <el-table :data="availableCases" size="small" class="w-full"
                @selection-change="onCaseSelectionChange" empty-text="暂无可用用例">
                <el-table-column type="selection" width="45" />
                <el-table-column label="ID" prop="id" width="60" />
                <el-table-column label="用例名称" prop="title" min-width="180" />
                <el-table-column label="模块" prop="module" width="100" />
                <el-table-column label="优先级" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag :color="priorityColor(row.priority)" effect="dark" size="small" class="!border-0 !text-white !rounded-md">
                      {{ row.priority || '-' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#7c3aed" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTestExecutions, createTestExecution, deleteTestExecution,
  getTestCases,
} from '../../api/test-cases'
import { getProjects } from '../../api/projects'
import { getEmployees } from '../../api/hr'

const router = useRouter()

const pageLoading = ref(true)
const creating = ref(false)
const createDialogVisible = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const selectedModule = ref<string | null>(null)

const executions = ref<any[]>([])
const projectOptions = ref<any[]>([])
const executorOptions = ref<any[]>([])
const availableCases = ref<any[]>([])

const filters = reactive({ project_id: null as number | null, status: '', keyword: '' })
const createForm = reactive({
  title: '',
  plan_type: 'manual',
  project_id: null as number | null,
  executor_id: null as number | null,
  case_ids: [] as number[],
})
const caseFilter = reactive({ keyword: '', priority: '', module: '' })
const execStatusType = (s: string) => ({ pending: 'info', running: '', completed: 'success', aborted: 'danger' }[s] || '') as any
const execStatusLabel = (s: string) => ({ pending: '未开始', running: '进行中', completed: '已完成', aborted: '已中止' }[s] || s)
const priorityColor = (p: string) => ({ P0: '#ef4444', P1: '#f97316', P2: '#3b82f6', P3: '#9ca3af', critical: '#ef4444', high: '#f97316', medium: '#3b82f6', low: '#9ca3af' }[p] || '#9ca3af')

function passRate(row: any) {
  const t = row.total_cases || 0
  if (t === 0) return 0
  return ((row.passed_cases || 0) / t) * 100
}

function failRate(row: any) {
  const t = row.total_cases || 0
  if (t === 0) return 0
  return ((row.failed_cases || 0) / t) * 100
}

function getProjectName(projectId?: number) {
  if (!projectId) return '-'
  const p = projectOptions.value.find((x: any) => x.id === projectId)
  return p?.name || '-'
}

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function selectModule(mod: string | null) {
  selectedModule.value = mod
  if (mod === null || mod === 'unplanned') {
    filters.project_id = null
  } else if (mod.startsWith('project_')) {
    filters.project_id = Number(mod.replace('project_', ''))
  }
  page.value = 1
  fetchList()
}

async function fetchList() {
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (filters.project_id) params.project_id = filters.project_id
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    const { data } = await getTestExecutions(params)
    const payload = data?.data ?? data
    executions.value = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
    total.value = payload?.total ?? executions.value.length
  } catch (e: any) {
    ElMessage.error(e.message || '加载策略列表失败')
  }
}

async function fetchProjects() {
  try {
    const { data } = await getProjects({ page_size: 200 })
    const payload = data?.data ?? data
    projectOptions.value = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
  } catch { /* ignore */ }
}

async function fetchExecutors() {
  try {
    const { data } = await getEmployees()
    const payload = data?.data ?? data
    const employees = Array.isArray(payload) ? payload : []
    const currentUserId = Number(localStorage.getItem('user_id') || 0)
    const currentUsername = localStorage.getItem('username') || '当前用户'
    const options = employees
      .filter((e: any) => e.user_id)
      .map((e: any) => ({
        user_id: e.user_id,
        name: e.name || e.email || `用户 #${e.user_id}`,
      }))
    if (currentUserId && !options.some((u: any) => u.user_id === currentUserId)) {
      options.unshift({ user_id: currentUserId, name: currentUsername })
    }
    executorOptions.value = options
  } catch {
    const currentUserId = Number(localStorage.getItem('user_id') || 0)
    executorOptions.value = currentUserId
      ? [{ user_id: currentUserId, name: localStorage.getItem('username') || '当前用户' }]
      : []
  }
}

async function fetchCasesForSelect() {
  try {
    const params: any = { page_size: 200, status: 'active' }
    if (caseFilter.keyword) params.keyword = caseFilter.keyword
    if (caseFilter.priority) params.priority = caseFilter.priority
    if (caseFilter.module) params.module = caseFilter.module
    const { data } = await getTestCases(params)
    const payload = data?.data ?? data
    availableCases.value = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
  } catch { availableCases.value = [] }
}

function onCaseSelectionChange(selection: any[]) {
  createForm.case_ids = selection.map((c: any) => c.id)
}

function openCreateDialog() {
  createForm.title = ''
  createForm.plan_type = 'manual'
  createForm.project_id = null
  createForm.executor_id = Number(localStorage.getItem('user_id') || 0) || null
  createForm.case_ids = []
  caseFilter.keyword = ''
  caseFilter.priority = ''
  caseFilter.module = ''
  createDialogVisible.value = true
  fetchCasesForSelect()
}

async function handleCreate() {
  if (!createForm.title.trim()) { ElMessage.warning('请输入策略名称'); return }
  if (createForm.case_ids.length === 0) { ElMessage.warning('请选择至少一条用例'); return }
  creating.value = true
  try {
    await createTestExecution(createForm)
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    fetchList()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleDeleteExec(row: any) {
  try {
    await ElMessageBox.confirm('确认删除该策略？', '删除确认', { type: 'warning' })
    await deleteTestExecution(row.id)
    ElMessage.success('已删除')
    fetchList()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

onMounted(async () => {
  await Promise.all([fetchList(), fetchProjects(), fetchExecutors()])
  pageLoading.value = false
})
</script>

<style scoped>
:deep(.el-table .cell) {
  padding: 8px 12px;
}
</style>
