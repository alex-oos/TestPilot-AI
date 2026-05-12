<template>
  <div class="space-y-0" v-loading="pageLoading">
    <!-- Breadcrumb -->
    <div class="px-6 py-3 bg-white border-b border-gray-100">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/test-cases/strategies' }">测试策略</el-breadcrumb-item>
        <el-breadcrumb-item>策略详情</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- Title + Stats + Actions -->
    <div class="px-6 py-4 bg-white border-b border-gray-100">
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-lg font-bold text-gray-900 mb-2">
            <span class="text-gray-400 font-mono mr-2">[{{ execution.id }}]</span>
            {{ execution.title || '策略详情' }}
          </h1>
          <div class="flex items-center gap-5 text-sm text-gray-500">
            <span class="flex items-center gap-2">
              <span class="text-gray-400">执行人</span>
              <el-select
                v-model="execution.executor_id"
                size="small"
                filterable
                clearable
                placeholder="选择执行人"
                class="!w-32"
                :loading="savingExecutor"
                @change="handleExecutorChange"
              >
                <el-option v-for="u in executorOptions" :key="u.user_id" :label="u.name" :value="u.user_id" />
              </el-select>
            </span>
            <span class="flex items-center gap-1.5">
              <span class="text-gray-400">用例数</span>
              <b class="text-indigo-600 cursor-pointer hover:underline" @click="activeTab = 'plan'">{{ execution.total_cases ?? 0 }} 个</b>
            </span>
            <span class="flex items-center gap-1.5">
              <span class="text-gray-400">通过率</span>
              <b class="text-green-600">{{ passRateStr }}%</b>
            </span>
            <span class="flex items-center gap-1.5">
              <span class="text-gray-400">Bug数</span>
              <b :class="bugCount > 0 ? 'text-red-500' : 'text-gray-400'">{{ bugCount }}</b>
            </span>
            <el-tag
              :type="execStatusType(execution.status)"
              :class="execution.status === 'running' ? 'animate-pulse' : ''"
              effect="dark" size="small" round
            >
              {{ execStatusLabel(execution.status) }}
            </el-tag>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <el-button v-if="execution.status === 'pending'" type="success" size="small" class="!rounded-lg" @click="handleStart">
            <el-icon class="mr-1"><VideoPlay /></el-icon>开始执行
          </el-button>
          <el-button v-if="execution.status === 'running'" type="warning" size="small" class="!rounded-lg" @click="handleAbort">
            <el-icon class="mr-1"><VideoPause /></el-icon>中止
          </el-button>
          <el-button size="small" class="!rounded-lg" @click="handleGenReport" :disabled="!allExecuted">
            <el-icon class="mr-1"><Document /></el-icon>生成报告
          </el-button>
          <el-button size="small" class="!rounded-lg" @click="openAssociateCaseDialog">
            <el-icon class="mr-1"><Plus /></el-icon>关联用例
          </el-button>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="px-6 bg-white border-b border-gray-200">
      <div class="flex gap-0">
        <button
          v-for="tab in tabs" :key="tab.key"
          class="px-5 py-3 text-sm font-medium border-b-2 transition-colors"
          :class="activeTab === tab.key
            ? 'border-indigo-600 text-indigo-700'
            : 'border-transparent text-gray-500 hover:text-gray-700'"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- Tab: 测试规划 -->
    <div v-if="activeTab === 'plan'" class="flex-1 bg-gray-50">
      <!-- View Toggle -->
      <div class="px-6 py-3 flex items-center justify-between bg-white border-b border-gray-100">
        <span class="text-sm text-gray-500">共 {{ results.length }} 条用例</span>
        <div class="flex items-center gap-2">
          <el-button-group size="small">
            <el-button
              :type="viewMode === 'mindmap' ? 'primary' : 'default'"
              @click="viewMode = 'mindmap'"
              class="!rounded-l-lg"
            >
              🧠 脑图
            </el-button>
            <el-button
              :type="viewMode === 'table' ? 'primary' : 'default'"
              @click="viewMode = 'table'"
              class="!rounded-r-lg"
            >
              📋 表格
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- MindMap View -->
      <div v-if="viewMode === 'mindmap'" class="relative h-[calc(100vh-320px)] bg-white m-4 rounded-xl border border-gray-100 overflow-hidden">
        <MindMapComponent v-if="mindMapData" :data="mindMapData" @node-click="handleMindMapNodeClick" />
        <div v-else class="h-full flex items-center justify-center text-gray-400">暂无关联用例</div>
        <div
          v-if="selectedMindMapResult"
          class="absolute right-4 bottom-4 w-[360px] bg-white border border-gray-200 rounded-lg shadow-lg p-4"
        >
          <div class="flex items-start justify-between gap-3 mb-3">
            <div class="min-w-0">
              <p class="text-sm font-semibold text-gray-900 truncate">{{ selectedMindMapResult.test_case_title || `用例 #${selectedMindMapResult.test_case_id}` }}</p>
              <p class="text-xs text-gray-500 mt-1">{{ selectedMindMapResult.test_case_module || '默认模块' }}</p>
            </div>
            <el-tag :type="resultStatusType(selectedMindMapResult.status)" size="small" effect="dark" round>
              {{ resultStatusLabel(selectedMindMapResult.status) }}
            </el-tag>
          </div>
          <div class="grid grid-cols-4 gap-2">
            <el-button size="small" type="success" @click="openResultDialog(selectedMindMapResult, 'passed')">通过</el-button>
            <el-button size="small" type="danger" @click="openResultDialog(selectedMindMapResult, 'failed')">失败</el-button>
            <el-button size="small" color="#eab308" class="!text-white" @click="openResultDialog(selectedMindMapResult, 'blocked')">阻塞</el-button>
            <el-button size="small" @click="openResultDialog(selectedMindMapResult, 'skipped')">跳过</el-button>
          </div>
          <el-button size="small" type="warning" plain class="!mt-3 !w-full" @click="openBugDialog(selectedMindMapResult)">
            <el-icon class="mr-1"><Warning /></el-icon>提Bug
          </el-button>
        </div>
      </div>

      <!-- Table View -->
      <div v-if="viewMode === 'table'" class="m-4 bg-white rounded-xl border border-gray-100 overflow-hidden">
        <el-table :data="results" stripe class="w-full" empty-text="暂无关联用例">
          <el-table-column label="ID" prop="id" width="70" align="center" />
          <el-table-column label="用例名称" min-width="200">
            <template #default="{ row }">
              <span class="font-medium text-gray-900">{{ row.test_case_title || `用例 #${row.test_case_id}` }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="resultStatusType(row.status)" effect="dark" size="small" round>
                {{ resultStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="实际结果" prop="actual_result" min-width="180">
            <template #default="{ row }">
              <span class="text-sm text-gray-600 whitespace-pre-wrap">{{ row.actual_result || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行时间" width="160">
            <template #default="{ row }">{{ formatTime(row.executed_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="340" fixed="right">
            <template #default="{ row }">
              <div class="flex items-center gap-1">
                <el-button size="small" type="success" @click="openResultDialog(row, 'passed')">通过</el-button>
                <el-button size="small" type="danger" @click="openResultDialog(row, 'failed')">失败</el-button>
                <el-button size="small" color="#eab308" class="!text-white" @click="openResultDialog(row, 'blocked')">阻塞</el-button>
                <el-button size="small" @click="openResultDialog(row, 'skipped')">跳过</el-button>
                <el-button size="small" type="warning" plain @click="openBugDialog(row)">
                  <el-icon class="mr-0.5"><Warning /></el-icon>提Bug
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Tab: 执行历史 -->
    <div v-if="activeTab === 'history'" class="p-6 bg-gray-50 min-h-[400px]">
      <div class="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <el-table :data="executionHistory" stripe class="w-full" empty-text="暂无执行记录">
          <el-table-column label="用例" min-width="200">
            <template #default="{ row }">
              <span class="font-medium">{{ row.test_case_title || `用例 #${row.test_case_id}` }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行结果" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="resultStatusType(row.status)" effect="dark" size="small" round>
                {{ resultStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="实际结果" prop="actual_result" min-width="200">
            <template #default="{ row }">
              <span class="text-sm text-gray-600">{{ row.actual_result || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="备注" prop="notes" min-width="120">
            <template #default="{ row }">
              <span class="text-sm text-gray-500">{{ row.notes || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行时间" width="160">
            <template #default="{ row }">{{ formatTime(row.executed_at) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Tab: 变更历史 -->
    <div v-if="activeTab === 'changelog'" class="p-6 bg-gray-50 min-h-[400px]">
      <div class="bg-white rounded-xl border border-gray-100 p-6">
        <el-timeline>
          <el-timeline-item
            v-for="(log, idx) in changeLog" :key="idx"
            :timestamp="log.time" placement="top"
            :type="log.type"
          >
            <p class="text-sm text-gray-700">{{ log.content }}</p>
          </el-timeline-item>
          <el-timeline-item v-if="execution.created_at" timestamp="" placement="top" type="primary">
            <p class="text-sm text-gray-700">创建策略 "{{ execution.title }}"</p>
            <p class="text-xs text-gray-400 mt-1">{{ formatTime(execution.created_at) }}</p>
          </el-timeline-item>
        </el-timeline>
        <div v-if="changeLog.length === 0 && !execution.created_at" class="text-center text-gray-400 py-10">暂无变更记录</div>
      </div>
    </div>

    <!-- Result update dialog -->
    <el-dialog v-model="resultDialogVisible" :title="resultDialogTitle" width="500px" class="!rounded-2xl">
      <el-form :model="resultForm" label-width="90px">
        <el-form-item label="执行状态">
          <el-tag :type="resultStatusType(resultForm.status)" effect="dark" round>
            {{ resultStatusLabel(resultForm.status) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="实际结果">
          <el-input v-model="resultForm.actual_result" type="textarea" :rows="4" placeholder="输入实际结果..." />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="resultForm.notes" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resultDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#7c3aed" :loading="updatingResult" @click="submitResult">确认</el-button>
      </template>
    </el-dialog>

    <!-- Bug submit dialog -->
    <el-dialog v-model="bugDialogVisible" title="提交缺陷" width="700px" class="!rounded-2xl" destroy-on-close>
      <el-form :model="bugForm" label-width="90px">
        <el-form-item label="缺陷标题" required>
          <el-input v-model="bugForm.title" placeholder="输入缺陷标题" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-x-4">
          <el-form-item label="严重程度">
            <el-select v-model="bugForm.severity" class="w-full">
              <el-option label="致命" value="critical" />
              <el-option label="严重" value="major" />
              <el-option label="一般" value="normal" />
              <el-option label="轻微" value="minor" />
              <el-option label="建议" value="suggestion" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="bugForm.priority" class="w-full">
              <el-option label="P0 - 紧急" value="P0" />
              <el-option label="P1 - 高" value="P1" />
              <el-option label="P2 - 中" value="P2" />
              <el-option label="P3 - 低" value="P3" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="关联用例">
          <el-input :model-value="bugForm.case_title" disabled />
        </el-form-item>
        <el-form-item label="复现步骤" required>
          <el-input v-model="bugForm.description" type="textarea" :rows="5" placeholder="详细描述缺陷复现步骤..." />
        </el-form-item>
        <el-form-item label="预期结果">
          <el-input v-model="bugForm.expected_result" type="textarea" :rows="2" placeholder="期望的正确行为" />
        </el-form-item>
        <el-form-item label="实际结果">
          <el-input v-model="bugForm.actual_result" type="textarea" :rows="2" placeholder="实际发生的行为" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bugDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submittingBug" @click="submitBug">
          <el-icon class="mr-1"><Warning /></el-icon>提交缺陷
        </el-button>
      </template>
    </el-dialog>

    <!-- Associate Case Dialog -->
    <el-dialog v-model="associateDialogVisible" title="关联测试用例" width="800px" class="!rounded-2xl" destroy-on-close>
      <div class="border border-gray-200 rounded-xl overflow-hidden">
        <div class="bg-gray-50 px-4 py-2 flex items-center gap-3 border-b border-gray-200">
          <el-input v-model="assocCaseFilter.keyword" placeholder="搜索用例..." clearable size="small" class="!w-48" @clear="fetchAssocCases" @keyup.enter="fetchAssocCases" />
          <el-select v-model="assocCaseFilter.priority" clearable placeholder="优先级" size="small" class="!w-28" @change="fetchAssocCases">
            <el-option label="P0" value="P0" />
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
          </el-select>
          <span class="text-sm text-gray-500 ml-auto">已选 <b class="text-indigo-600">{{ assocCaseIds.length }}</b> 条</span>
        </div>
        <div class="max-h-80 overflow-y-auto">
          <el-table :data="assocAvailCases" size="small" class="w-full"
            @selection-change="onAssocSelectionChange" empty-text="暂无可用用例">
            <el-table-column type="selection" width="45" />
            <el-table-column label="ID" prop="id" width="60" />
            <el-table-column label="用例名称" prop="title" min-width="180" />
            <el-table-column label="模块" prop="module" width="100" />
            <el-table-column label="优先级" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small">{{ row.priority || '-' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="associateDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#7c3aed" :loading="associating" @click="submitAssociate">关联</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VideoPlay, VideoPause, Document, Warning, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getTestExecution, startTestExecution, abortTestExecution,
  updateExecutionResult, generateTestReport, getTestCases,
  updateTestExecution, updateExecutionCases,
} from '../../api/test-cases'
import { createDefect } from '../../api/defects'
import { getEmployees } from '../../api/hr'
import MindMapComponent from '../../components/MindMap.vue'
import type { MindMapNode } from '../../components/MindMap.vue'

const route = useRoute()
const router = useRouter()
const execId = Number(route.params.id)

const pageLoading = ref(true)
const updatingResult = ref(false)
const submittingBug = ref(false)
const associating = ref(false)
const savingExecutor = ref(false)
const resultDialogVisible = ref(false)
const bugDialogVisible = ref(false)
const associateDialogVisible = ref(false)
const viewMode = ref<'table' | 'mindmap'>('mindmap')
const activeTab = ref<'plan' | 'history' | 'changelog'>('plan')

const tabs = [
  { key: 'plan' as const, label: '测试规划' },
  { key: 'history' as const, label: '执行历史' },
  { key: 'changelog' as const, label: '变更历史' },
]

const execution = reactive<any>({})
const results = ref<any[]>([])
const executorOptions = ref<any[]>([])
const selectedMindMapResult = ref<any | null>(null)
const resultForm = reactive({ resultId: 0, status: '', actual_result: '', notes: '' })
const bugForm = reactive({
  title: '',
  severity: 'normal',
  priority: 'P2',
  description: '',
  expected_result: '',
  actual_result: '',
  case_title: '',
  test_case_id: 0,
  project_id: null as number | null,
})

const assocCaseFilter = reactive({ keyword: '', priority: '' })
const assocAvailCases = ref<any[]>([])
const assocCaseIds = ref<number[]>([])

const allExecuted = computed(() => {
  if (!results.value.length) return false
  return results.value.every((r: any) => r.status !== 'pending')
})

const passRateStr = computed(() => {
  const t = execution.total_cases || 0
  if (t === 0) return '0.00'
  return (((execution.passed_cases || 0) / t) * 100).toFixed(2)
})

const bugCount = computed(() => execution.failed_cases || 0)

const executionHistory = computed(() =>
  results.value.filter((r: any) => r.status !== 'pending')
)

const changeLog = computed(() => {
  const logs: { time: string; content: string; type: string }[] = []
  results.value.forEach((r: any) => {
    if (r.status !== 'pending' && r.executed_at) {
      logs.push({
        time: formatTime(r.executed_at),
        content: `用例 "${r.test_case_title || r.test_case_id}" 执行结果: ${resultStatusLabel(r.status)}`,
        type: r.status === 'passed' ? 'success' : r.status === 'failed' ? 'danger' : 'warning',
      })
    }
  })
  logs.sort((a, b) => (a.time > b.time ? -1 : 1))
  return logs
})

const resultDialogTitle = computed(() => {
  const labels: Record<string, string> = { passed: '标记为通过', failed: '标记为失败', blocked: '标记为阻塞', skipped: '标记为跳过' }
  return labels[resultForm.status] || '更新结果'
})

const mindMapData = computed<MindMapNode | null>(() => {
  if (!results.value.length) return null

  const statusColorMap: Record<string, string> = {
    passed: '#22c55e',
    failed: '#ef4444',
    blocked: '#eab308',
    skipped: '#9ca3af',
    pending: '#d1d5db',
  }

  const statusTagMap: Record<string, string> = {
    pending: '未执行',
    passed: '已通过',
    failed: '未通过',
    blocked: '阻塞',
    skipped: '跳过',
  }

  const moduleMap = new Map<string, any[]>()
  results.value.forEach((r: any) => {
    const mod = r.test_case_module || '默认模块'
    if (!moduleMap.has(mod)) moduleMap.set(mod, [])
    moduleMap.get(mod)!.push(r)
  })

  const moduleChildren: MindMapNode[] = Array.from(moduleMap.entries()).map(([modName, cases]) => ({
    content: `📂 ${modName}`,
    children: cases.map((c: any) => ({
      content: c.test_case_title || `用例 #${c.test_case_id}`,
      children: [
        {
          content: `${statusTagMap[c.status] || c.status}`,
          payload: { color: statusColorMap[c.status] || '#d1d5db' },
        },
        ...(c.actual_result ? [{ content: `实际结果: ${c.actual_result}` }] : []),
      ],
      payload: {
        id: String(c.id),
        type: 'execution-result',
        status: c.status,
        color: statusColorMap[c.status] || '#d1d5db',
      },
    })),
    payload: { color: '#7c3aed' },
  }))

  return { content: `📋 ${execution.title || '测试策略'}`, children: moduleChildren }
})

const execStatusType = (s?: string) => ({ pending: 'info', running: '', completed: 'success', aborted: 'danger' }[s || ''] || '') as any
const execStatusLabel = (s?: string) => ({ pending: '未开始', running: '进行中', completed: '已完成', aborted: '已中止' }[s || ''] || s || '')
const resultStatusType = (s?: string) => ({ pending: 'info', passed: 'success', failed: 'danger', blocked: 'warning', skipped: 'info' }[s || ''] || '') as any
const resultStatusLabel = (s?: string) => ({ pending: '未执行', passed: '通过', failed: '失败', blocked: '阻塞', skipped: '跳过' }[s || ''] || s || '')

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function openResultDialog(row: any, status: string) {
  resultForm.resultId = row.id
  resultForm.status = status
  resultForm.actual_result = row.actual_result || ''
  resultForm.notes = row.notes || ''
  resultDialogVisible.value = true
}

function handleMindMapNodeClick(node: MindMapNode) {
  if (node.payload?.type !== 'execution-result' || !node.payload.id) return
  selectedMindMapResult.value = results.value.find((r: any) => String(r.id) === node.payload?.id) || null
}

function openBugDialog(row: any) {
  const caseTitle = row.test_case_title || `用例 #${row.test_case_id}`
  bugForm.title = `[${caseTitle}] `
  bugForm.severity = 'normal'
  bugForm.priority = 'P2'
  bugForm.description = ''
  bugForm.expected_result = ''
  bugForm.actual_result = row.actual_result || ''
  bugForm.case_title = caseTitle
  bugForm.test_case_id = row.test_case_id
  bugForm.project_id = execution.project_id || null
  bugDialogVisible.value = true
}

async function openAssociateCaseDialog() {
  assocCaseFilter.keyword = ''
  assocCaseFilter.priority = ''
  assocCaseIds.value = []
  associateDialogVisible.value = true
  await fetchAssocCases()
}

async function fetchAssocCases() {
  try {
    const params: any = { page_size: 200, status: 'active' }
    if (assocCaseFilter.keyword) params.keyword = assocCaseFilter.keyword
    if (assocCaseFilter.priority) params.priority = assocCaseFilter.priority
    const { data } = await getTestCases(params)
    const payload = data?.data ?? data
    const allCases = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
    const existIds = new Set(results.value.map((r: any) => r.test_case_id))
    assocAvailCases.value = allCases.filter((c: any) => !existIds.has(c.id))
  } catch { assocAvailCases.value = [] }
}

function onAssocSelectionChange(selection: any[]) {
  assocCaseIds.value = selection.map((c: any) => c.id)
}

async function submitAssociate() {
  if (assocCaseIds.value.length === 0) { ElMessage.warning('请选择要关联的用例'); return }
  associating.value = true
  try {
    await updateExecutionCases(execId, { case_ids: assocCaseIds.value })
    ElMessage.success('关联成功')
    associateDialogVisible.value = false
    await fetchDetail()
  } catch (e: any) {
    ElMessage.error(e.message || '关联失败')
  } finally {
    associating.value = false
  }
}

async function submitResult() {
  updatingResult.value = true
  try {
    await updateExecutionResult(execId, resultForm.resultId, {
      status: resultForm.status,
      actual_result: resultForm.actual_result,
      notes: resultForm.notes,
      executor_id: execution.executor_id,
    })
    ElMessage.success('结果已更新')
    resultDialogVisible.value = false
    await fetchDetail()
    selectedMindMapResult.value = results.value.find((r: any) => r.id === resultForm.resultId) || null
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    updatingResult.value = false
  }
}

async function submitBug() {
  if (!bugForm.title.trim()) { ElMessage.warning('请输入缺陷标题'); return }
  if (!bugForm.description.trim()) { ElMessage.warning('请输入复现步骤'); return }
  submittingBug.value = true
  try {
    await createDefect({
      title: bugForm.title,
      severity: bugForm.severity,
      priority: bugForm.priority,
      description: bugForm.description,
      expected_result: bugForm.expected_result,
      actual_result: bugForm.actual_result,
      project_id: bugForm.project_id,
      test_case_id: bugForm.test_case_id,
      status: 'open',
      defect_type: 'functional',
    })
    ElMessage.success('缺陷已提交')
    bugDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e.message || '提交缺陷失败')
  } finally {
    submittingBug.value = false
  }
}

async function handleStart() {
  try {
    await startTestExecution(execId)
    ElMessage.success('策略已开始执行')
    await fetchDetail()
  } catch (e: any) {
    ElMessage.error(e.message || '启动失败')
  }
}

async function handleAbort() {
  try {
    await ElMessageBox.confirm('确认中止当前执行？', '中止确认', { type: 'warning' })
    await abortTestExecution(execId)
    ElMessage.success('已中止')
    await fetchDetail()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '中止失败')
  }
}

async function handleGenReport() {
  try {
    const { data } = await generateTestReport(execId)
    const report = data?.data ?? data
    ElMessage.success('报告已生成')
    router.push(`/test-cases/reports/${report.id}`)
  } catch (e: any) {
    ElMessage.error(e.message || '生成报告失败')
  }
}

async function handleExecutorChange() {
  savingExecutor.value = true
  try {
    const { data } = await updateTestExecution(execId, { executor_id: execution.executor_id || null })
    Object.assign(execution, data?.data ?? data)
    ElMessage.success('执行人已更新')
  } catch (e: any) {
    ElMessage.error(e.message || '执行人更新失败')
    await fetchDetail()
  } finally {
    savingExecutor.value = false
  }
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

async function fetchDetail() {
  try {
    const { data } = await getTestExecution(execId)
    const payload = data?.data ?? data
    Object.assign(execution, payload)
    results.value = payload.results || []
    if (selectedMindMapResult.value) {
      selectedMindMapResult.value = results.value.find((r: any) => r.id === selectedMindMapResult.value?.id) || null
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载策略详情失败')
  }
}

onMounted(async () => {
  await Promise.all([fetchDetail(), fetchExecutors()])
  pageLoading.value = false
})
</script>
