<template>
  <div class="h-full flex flex-col -m-8">
    <!-- 顶栏 -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <h1 class="text-lg font-bold text-gray-900">📝 需求管理</h1>
        <div class="flex bg-gray-100 rounded-lg p-0.5">
          <button v-for="v in viewModes" :key="v.key"
            class="px-3 py-1.5 text-xs font-medium rounded-md transition-all"
            :class="viewMode === v.key ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="viewMode = v.key">{{ v.icon }} {{ v.label }}</button>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <el-select v-model="filterProject" clearable placeholder="所属项目" size="small" class="!w-40" @change="fetchRequirements">
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-select v-model="filterPriority" clearable placeholder="优先级" size="small" class="!w-28" @change="fetchRequirements">
          <el-option label="紧急" value="critical" />
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索需求..." clearable size="small" class="!w-44" />
        <el-button type="primary" color="#4f46e5" size="small" @click="openCreateDialog">+ 新建需求</el-button>
      </div>
    </div>

    <!-- 流程阶段概览条 -->
    <div class="bg-white border-b border-gray-100 px-6 py-3 shrink-0">
      <div class="flex items-center gap-1">
        <div v-for="(stage, idx) in stages" :key="stage.value"
          class="flex items-center">
          <div
            class="flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer transition-all text-sm"
            :class="activeStageFilter === stage.value
              ? 'bg-indigo-50 text-indigo-700 font-semibold ring-1 ring-indigo-200'
              : 'hover:bg-gray-50 text-gray-600'"
            @click="toggleStageFilter(stage.value)"
          >
            <span class="w-2 h-2 rounded-full" :style="{ background: stage.color }"></span>
            <span>{{ stage.label }}</span>
            <span class="text-xs bg-gray-100 text-gray-500 rounded-full px-1.5 py-0.5 min-w-[20px] text-center"
              :class="activeStageFilter === stage.value && '!bg-indigo-100 !text-indigo-600'">
              {{ stageCount(stage.value) }}
            </span>
          </div>
          <span v-if="idx < stages.length - 1" class="text-gray-300 mx-0.5">→</span>
        </div>
      </div>
    </div>

    <!-- 流程看板视图 (默认) -->
    <div v-if="viewMode === 'pipeline'" class="flex-1 overflow-x-auto bg-gray-50 p-4">
      <div class="flex gap-3 h-full min-w-max">
        <div v-for="stage in visibleStages" :key="stage.value" class="w-[280px] shrink-0 flex flex-col">
          <!-- 列头 -->
          <div class="flex items-center justify-between mb-3 px-2">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full" :style="{ background: stage.color }"></span>
              <span class="font-semibold text-gray-700 text-sm">{{ stage.label }}</span>
              <span class="text-xs bg-gray-200 text-gray-600 rounded-full px-2 py-0.5">{{ stageRequirements(stage.value).length }}</span>
            </div>
          </div>
          <!-- 可拖拽卡片列表 -->
          <draggable
            :list="stageRequirements(stage.value)"
            :group="{ name: 'requirements', pull: true, put: true }"
            item-key="id"
            class="flex-1 space-y-2.5 overflow-y-auto pb-4 pr-1 min-h-[80px] rounded-lg transition-colors"
            :class="dragOverStage === stage.value ? 'bg-indigo-50 ring-2 ring-indigo-200 ring-dashed' : ''"
            ghost-class="drag-ghost"
            chosen-class="drag-chosen"
            drag-class="drag-active"
            :animation="200"
            @start="onDragStart"
            @end="onDragEnd($event, stage.value)"
            @change="(evt: any) => onDragChange(evt, stage.value)"
            @dragover.native="dragOverStage = stage.value"
            @dragleave.native="dragOverStage = ''"
          >
            <template #item="{ element: req }">
              <div
                class="bg-white rounded-xl border border-gray-100 p-3.5 shadow-sm hover:shadow-md transition-all cursor-grab active:cursor-grabbing group"
                @click="openDetail(req)">
                <div class="flex items-start justify-between mb-2">
                  <span class="font-medium text-gray-900 text-sm leading-snug flex-1">{{ req.title }}</span>
                  <el-tag :type="priorityType(req.priority)" size="small" effect="light" round class="!ml-2 shrink-0">
                    {{ priorityLabel(req.priority) }}
                  </el-tag>
                </div>
                <p v-if="req.description" class="text-xs text-gray-400 mb-3 line-clamp-2">{{ req.description }}</p>
                <div class="flex items-center justify-between">
                  <span class="text-[10px] text-gray-400">{{ projectName(req.project_id) }}</span>
                  <div class="flex items-center gap-1">
                    <el-button v-if="nextStage(stage.value)" link size="small" type="primary"
                      class="!text-[10px] opacity-0 group-hover:opacity-100 transition-opacity"
                      @click.stop="advanceStage(req, nextStage(stage.value)!)">
                      → {{ nextStageLabel(stage.value) }}
                    </el-button>
                  </div>
                </div>
              </div>
            </template>
            <template #footer>
              <div v-if="stageRequirements(stage.value).length === 0 && !isDragging"
                class="text-center text-xs text-gray-300 py-8">暂无需求</div>
            </template>
          </draggable>
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-if="viewMode === 'list'" class="flex-1 overflow-auto bg-gray-50 p-4">
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <el-table :data="filteredRequirements" v-loading="loading" stripe
          :header-cell-style="{ background: '#f9fafb', color: '#475569', fontWeight: '600', fontSize: '12px' }">
          <el-table-column prop="title" label="需求标题" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="cursor-pointer hover:text-indigo-600 font-medium" @click="openDetail(row)">{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column label="当前阶段" width="130" align="center">
            <template #default="{ row }">
              <div class="flex items-center justify-center gap-1.5">
                <span class="w-2 h-2 rounded-full" :style="{ background: stageColor(row.status) }"></span>
                <span class="text-xs font-medium">{{ stageLabel(row.status) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="优先级" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="priorityType(row.priority)" size="small" effect="light" round>{{ priorityLabel(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="所属项目" width="140">
            <template #default="{ row }">
              <el-button v-if="row.project_id" link type="primary" size="small" @click="goProject(row.project_id)">{{ projectName(row.project_id) }}</el-button>
              <span v-else class="text-gray-400 text-xs">--</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
              <el-button v-if="nextStage(row.status)" link type="success" size="small" @click="advanceStage(row, nextStage(row.status)!)">
                推进 →
              </el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 新建需求弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建需求" width="580px" destroy-on-close>
      <el-form :model="createForm" label-width="80px" label-position="top">
        <el-form-item label="需求标题" required>
          <el-input v-model="createForm.title" placeholder="请输入需求标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="需求描述">
          <el-input v-model="createForm.description" type="textarea" :rows="4" placeholder="需求描述" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="所属项目" required>
            <el-select v-model="createForm.project_id" placeholder="选择已立项/进行中的项目" class="w-full" filterable>
              <el-option v-for="p in creatableProjectOptions" :key="p.value" :label="p.label" :value="p.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级">
            <el-select v-model="createForm.priority" class="w-full">
              <el-option label="紧急" value="critical" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="需求类型">
            <el-select v-model="createForm.type" class="w-full">
              <el-option label="功能需求" value="functional" />
              <el-option label="非功能需求" value="non-functional" />
              <el-option label="UI/UX" value="ui_ux" />
              <el-option label="接口需求" value="api" />
            </el-select>
          </el-form-item>
          <el-form-item label="需求来源">
            <el-input v-model="createForm.source" placeholder="如：产品经理、客户反馈" />
          </el-form-item>
        </div>
        <div class="mt-1 mb-2 text-xs text-gray-400 font-medium">📋 相关人员（非必填）</div>
        <div class="grid grid-cols-3 gap-4">
          <el-form-item label="产品负责人">
            <el-select v-model="createForm.product_owner_id" clearable placeholder="选择产品" class="w-full" filterable>
              <el-option v-for="e in productEmployees" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="开发负责人">
            <el-select v-model="createForm.dev_owner_id" clearable placeholder="选择开发" class="w-full" filterable>
              <el-option v-for="e in devEmployees" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="测试负责人">
            <el-select v-model="createForm.test_owner_id" clearable placeholder="选择测试" class="w-full" filterable>
              <el-option v-for="e in testEmployees" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import draggable from 'vuedraggable'
import request from '../../utils/request'
import { getEmployees } from '../../api/hr'

const router = useRouter()

const viewModes = [
  { key: 'pipeline', label: '流程看板', icon: '🔄' },
  { key: 'list', label: '列表', icon: '📋' },
]
const viewMode = ref('pipeline')

const stages = [
  { value: 'requirement_review', label: '需求评审', shortLabel: '需求评审', color: '#8b5cf6' },
  { value: 'tech_review', label: '技术评审', shortLabel: '技术评审', color: '#6366f1' },
  { value: 'case_review', label: '用例评审', shortLabel: '用例评审', color: '#0ea5e9' },
  { value: 'testing', label: '测试执行', shortLabel: '测试执行', color: '#14b8a6' },
  { value: 'acceptance', label: '验收测试', shortLabel: '验收测试', color: '#f59e0b' },
  { value: 'released', label: '发布上线', shortLabel: '发布上线', color: '#22c55e' },
  { value: 'regression', label: '线上回归', shortLabel: '线上回归', color: '#ef4444' },
]
const stageOrder = stages.map(s => s.value)

const loading = ref(false)
const requirements = ref<any[]>([])
const projectOptions = ref<{ label: string; value: any }[]>([])
const creatableProjectOptions = computed(() =>
  allProjects.value
    .filter((p: any) => p.status === 'approved' || p.status === 'active')
    .map((p: any) => ({ label: p.name, value: p.id }))
)
const allProjects = ref<any[]>([])
const filterProject = ref('')
const filterPriority = ref('')
const searchText = ref('')
const activeStageFilter = ref('')

const createDialogVisible = ref(false)
const createForm = reactive({ title: '', description: '', project_id: null as any, priority: 'medium', type: 'functional', source: '', product_owner_id: null as any, dev_owner_id: null as any, test_owner_id: null as any })
const allEmployees = ref<any[]>([])
const productEmployees = computed(() => allEmployees.value.filter(e => e.role === 'product' || !e.role))
const devEmployees = computed(() => allEmployees.value.filter(e => e.role === 'developer' || !e.role))
const testEmployees = computed(() => allEmployees.value.filter(e => e.role === 'tester' || !e.role))


const filteredRequirements = computed(() => {
  let list = [...requirements.value]
  if (searchText.value) {
    const kw = searchText.value.toLowerCase()
    list = list.filter(r => r.title?.toLowerCase().includes(kw))
  }
  if (activeStageFilter.value) {
    list = list.filter(r => r.status === activeStageFilter.value)
  }
  return list
})

const visibleStages = computed(() => {
  if (activeStageFilter.value) return stages.filter(s => s.value === activeStageFilter.value)
  return stages
})

const isDragging = ref(false)
const dragOverStage = ref('')

function stageCount(status: string) { return requirements.value.filter(r => r.status === status).length }
function stageRequirements(status: string) { return filteredRequirements.value.filter(r => r.status === status) }
function stageColor(status: string) { return stages.find(s => s.value === status)?.color || '#94a3b8' }
function stageLabel(status: string) { return stages.find(s => s.value === status)?.label || status }

function onDragStart() {
  isDragging.value = true
}

function onDragEnd(_evt: any, _stageValue: string) {
  isDragging.value = false
  dragOverStage.value = ''
}

async function onDragChange(evt: any, targetStage: string) {
  if (!evt.added) return
  const req = evt.added.element
  if (req.status === targetStage) return

  const oldStatus = req.status
  req.status = targetStage
  try {
    const resp = await request.put(`/requirements/${req.id}`, { ...req, status: targetStage })
    ElMessage.success(`已将「${req.title}」移至「${stageLabel(targetStage)}」`)
    const result = resp.data?.data
    if (result?.auto_archived) {
      ElMessage.success({ message: '该项目下所有需求已完成线上回归，项目已自动归档', duration: 5000 })
      fetchProjects()
    }
  } catch {
    req.status = oldStatus
    ElMessage.error('状态更新失败，已恢复')
    fetchRequirements()
  }
}

function toggleStageFilter(v: string) {
  activeStageFilter.value = activeStageFilter.value === v ? '' : v
}

function nextStage(current: string): string | null {
  const idx = stageOrder.indexOf(current)
  return idx >= 0 && idx < stageOrder.length - 1 ? stageOrder[idx + 1] : null
}
function nextStageLabel(current: string) { const n = nextStage(current); return n ? stageLabel(n) : '' }

async function advanceStage(req: any, newStatus: string) {
  try {
    const resp = await request.put(`/requirements/${req.id}`, { ...req, status: newStatus })
    req.status = newStatus
    ElMessage.success(`已推进到「${stageLabel(newStatus)}」`)
    const result = resp.data?.data
    if (result?.auto_archived) {
      ElMessage.success({ message: '该项目下所有需求已完成线上回归，项目已自动归档', duration: 5000 })
      fetchProjects()
    }
    fetchRequirements()
  } catch { ElMessage.error('操作失败') }
}

function priorityLabel(p: string) { return { critical: '紧急', high: '高', medium: '中', low: '低' }[p] || p }
function priorityType(p: string) { return ({ critical: 'danger', high: 'warning', medium: '', low: 'info' } as any)[p] || '' }
function projectName(id: any) { return projectOptions.value.find(p => p.value === id)?.label || '' }
function goProject(id: any) { router.push(`/projects/${id}`) }
function formatTime(v: string) { if (!v) return '--'; const d = new Date(v); return isNaN(d.getTime()) ? '--' : d.toLocaleString('zh-CN') }

function openDetail(req: any) { router.push(`/requirements/${req.id}`) }

function openCreateDialog() {
  createForm.title = ''; createForm.description = ''; createForm.project_id = null
  createForm.priority = 'medium'; createForm.type = 'functional'; createForm.source = ''
  createForm.product_owner_id = null; createForm.dev_owner_id = null; createForm.test_owner_id = null
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.title?.trim()) { ElMessage.warning('请输入需求标题'); return }
  if (!createForm.project_id) { ElMessage.warning('请选择所属项目'); return }
  try {
    const resp = await request.post('/requirements', { ...createForm, status: 'requirement_review' })
    const result = resp.data?.data
    if (resp.data?.code !== 0 && resp.data?.msg) {
      ElMessage.error(resp.data.msg)
      return
    }
    if (result?.project_activated) {
      ElMessage.success('需求已创建，项目已自动进入「进行中」状态')
    } else {
      ElMessage.success('需求已创建，进入需求评审阶段')
    }
    createDialogVisible.value = false
    fetchRequirements()
    fetchProjects()
  } catch (e: any) {
    const msg = e?.response?.data?.message || '创建失败'
    ElMessage.error(msg)
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除需求「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(`/requirements/${row.id}`)
  ElMessage.success('已删除')
  fetchRequirements()
}

async function fetchRequirements() {
  loading.value = true
  try {
    const params: any = {}
    if (filterProject.value) params.project_id = filterProject.value
    if (filterPriority.value) params.priority = filterPriority.value
    const resp = await request.get('/requirements', { params })
    const payload = resp.data?.data
    requirements.value = payload?.items || payload || resp.data?.items || (Array.isArray(resp.data) ? resp.data : [])
  } finally { loading.value = false }
}

async function fetchProjects() {
  try {
    const resp = await request.get('/projects', { params: { page_size: 100 } })
    const list = resp.data?.data?.items || resp.data?.data || resp.data || []
    const arr = Array.isArray(list) ? list : []
    allProjects.value = arr
    projectOptions.value = arr.map((p: any) => ({ label: p.name, value: p.id }))
  } catch {}
}

async function fetchAllEmployees() {
  try {
    const resp = await getEmployees()
    allEmployees.value = resp.data?.data || resp.data || []
  } catch { allEmployees.value = [] }
}

onMounted(() => { fetchProjects(); fetchRequirements(); fetchAllEmployees() })
</script>

<style scoped>
.drag-ghost {
  opacity: 0.4;
  background: #e0e7ff;
  border: 2px dashed #6366f1;
  border-radius: 0.75rem;
}
.drag-chosen {
  box-shadow: 0 8px 25px -5px rgb(99 102 241 / 0.3);
  transform: rotate(2deg);
}
.drag-active {
  opacity: 0.9;
}
</style>
