<template>
  <div class="space-y-6" v-loading="pageLoading">
    <!-- Breadcrumb + Back -->
    <div class="flex items-center gap-3">
      <el-button circle @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/test-cases' }">测试用例</el-breadcrumb-item>
        <el-breadcrumb-item>用例详情</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- Header -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <div class="flex items-center justify-between mb-3">
        <h1 class="text-2xl font-bold text-gray-900 truncate flex-1 min-w-0">{{ testCase.title || '用例详情' }}</h1>
        <div class="flex items-center gap-2 shrink-0">
          <el-button v-if="!editing" type="primary" color="#4f46e5" class="!rounded-xl" @click="editing = true">
            <el-icon class="mr-1"><Edit /></el-icon>编辑
          </el-button>
          <el-button type="success" class="!rounded-xl" @click="openExecuteDialog">
            <el-icon class="mr-1"><VideoPlay /></el-icon>执行
          </el-button>
          <el-button type="danger" class="!rounded-xl" @click="handleDelete">
            <el-icon class="mr-1"><Delete /></el-icon>删除
          </el-button>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <el-tag :color="priorityColor(testCase.priority)" effect="dark" size="small" class="!border-0 !text-white !rounded-md">
          {{ priorityLabel(testCase.priority) }}
        </el-tag>
        <el-tag :type="statusType(testCase.status)" effect="light" round size="small">
          {{ statusLabel(testCase.status) }}
        </el-tag>
        <el-tag effect="plain" round size="small">
          {{ sourceLabel(testCase.source) }}
        </el-tag>
        <el-tag type="info" effect="plain" round size="small">
          {{ caseTypeLabel(testCase.case_type) }}
        </el-tag>
        <span class="text-xs text-gray-400 ml-2">#{{ testCase.id }}</span>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <!-- 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <div class="p-6">
          <template v-if="!editing">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <InfoItem label="模块" :value="testCase.module" />
              <InfoItem label="优先级" :value="priorityLabel(testCase.priority)" />
              <InfoItem label="用例类型" :value="caseTypeLabel(testCase.case_type)" />
              <InfoItem label="来源" :value="sourceLabel(testCase.source)" />
              <div class="md:col-span-2">
                <InfoItem label="前置条件" :value="testCase.precondition" />
              </div>
              <div class="md:col-span-2">
                <InfoItem label="描述" :value="testCase.description" />
              </div>
              <InfoItem label="创建时间" :value="formatTime(testCase.created_at)" />
              <InfoItem label="更新时间" :value="formatTime(testCase.updated_at)" />
            </div>
          </template>
          <template v-else>
            <el-form :model="editForm" label-width="90px" class="max-w-3xl">
              <el-form-item label="标题">
                <el-input v-model="editForm.title" />
              </el-form-item>
              <el-form-item label="模块">
                <el-input v-model="editForm.module" />
              </el-form-item>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6">
                <el-form-item label="优先级">
                  <el-select v-model="editForm.priority" class="w-full">
                    <el-option label="P0 - 致命" value="critical" />
                    <el-option label="P1 - 高" value="high" />
                    <el-option label="P2 - 中" value="medium" />
                    <el-option label="P3 - 低" value="low" />
                  </el-select>
                </el-form-item>
                <el-form-item label="用例类型">
                  <el-select v-model="editForm.case_type" class="w-full">
                    <el-option label="功能测试" value="functional" />
                    <el-option label="性能测试" value="performance" />
                    <el-option label="安全测试" value="security" />
                    <el-option label="兼容性测试" value="compatibility" />
                    <el-option label="UI测试" value="ui" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="前置条件">
                <el-input v-model="editForm.precondition" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="editForm.description" type="textarea" :rows="4" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" color="#4f46e5" :loading="saving" @click="handleSave">保存</el-button>
                <el-button @click="cancelEdit">取消</el-button>
              </el-form-item>
            </el-form>
          </template>
        </div>
      </el-tab-pane>

      <!-- 测试步骤 -->
      <el-tab-pane label="测试步骤" name="steps">
        <div class="p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-gray-800">测试步骤 ({{ steps.length }})</h3>
            <el-button v-if="!editingSteps" type="primary" color="#4f46e5" size="small" @click="startEditSteps">
              <el-icon class="mr-1"><Edit /></el-icon>编辑步骤
            </el-button>
            <div v-else class="flex gap-2">
              <el-button type="primary" color="#4f46e5" size="small" :loading="saving" @click="saveSteps">保存</el-button>
              <el-button size="small" @click="cancelEditSteps">取消</el-button>
            </div>
          </div>

          <template v-if="!editingSteps">
            <el-table :data="steps" border stripe class="w-full" empty-text="暂无测试步骤">
              <el-table-column label="序号" width="70" align="center">
                <template #default="{ row }">{{ row.order }}</template>
              </el-table-column>
              <el-table-column label="操作步骤" prop="action" min-width="200">
                <template #default="{ row }">
                  <span class="whitespace-pre-wrap text-sm">{{ row.action }}</span>
                </template>
              </el-table-column>
              <el-table-column label="预期结果" prop="expected_result" min-width="200">
                <template #default="{ row }">
                  <span class="whitespace-pre-wrap text-sm">{{ row.expected_result || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="测试数据" prop="test_data" min-width="150">
                <template #default="{ row }">
                  <span class="whitespace-pre-wrap text-sm text-gray-500">{{ row.test_data || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </template>
          <template v-else>
            <div class="space-y-3">
              <div v-for="(step, idx) in editSteps" :key="idx"
                class="border border-gray-200 rounded-xl p-4 bg-gray-50 relative group">
                <div class="flex items-center gap-3 mb-3">
                  <span class="text-sm font-bold text-gray-500 w-8">{{ idx + 1 }}</span>
                  <div class="flex gap-1 ml-auto">
                    <el-button size="small" circle :disabled="idx === 0" @click="moveStep(idx, -1)">
                      <el-icon><Top /></el-icon>
                    </el-button>
                    <el-button size="small" circle :disabled="idx === editSteps.length - 1" @click="moveStep(idx, 1)">
                      <el-icon><Bottom /></el-icon>
                    </el-button>
                    <el-button size="small" circle type="danger" @click="editSteps.splice(idx, 1)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <el-input v-model="step.action" type="textarea" :rows="2" placeholder="操作步骤" />
                  <el-input v-model="step.expected_result" type="textarea" :rows="2" placeholder="预期结果" />
                  <el-input v-model="step.test_data" type="textarea" :rows="2" placeholder="测试数据（可选）" />
                </div>
              </div>
              <el-button type="primary" plain class="w-full !rounded-xl" @click="addStep">
                <el-icon class="mr-1"><Plus /></el-icon>添加步骤
              </el-button>
            </div>
          </template>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Execute Dialog -->
    <el-dialog v-model="executeDialogVisible" title="创建测试执行" width="500px" class="!rounded-2xl">
      <el-form :model="executeForm" label-width="90px">
        <el-form-item label="执行名称">
          <el-input v-model="executeForm.title" placeholder="输入执行名称" />
        </el-form-item>
        <el-form-item label="执行类型">
          <el-select v-model="executeForm.plan_type" class="w-full">
            <el-option label="手动执行" value="manual" />
            <el-option label="回归测试" value="regression" />
            <el-option label="冒烟测试" value="smoke" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="executeDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" :loading="executing" @click="handleExecute">创建执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Edit, Delete, VideoPlay, Plus, Top, Bottom } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTestCase, updateTestCase, deleteTestCase, createTestExecution } from '../../api/test-cases'

interface TestStep {
  id?: number
  order: number
  action: string
  expected_result: string
  test_data: string
}

interface TestCaseData {
  id: number
  title: string
  module: string
  priority: string
  case_type: string
  description: string
  precondition: string
  status: string
  source: string
  created_at: string
  updated_at: string
  steps: TestStep[]
}

const InfoItem = defineComponent({
  props: { label: String, value: String },
  setup(props) {
    return () => h('div', [
      h('span', { class: 'text-sm font-medium text-gray-500 block mb-1' }, props.label),
      h('p', { class: 'text-sm text-gray-800 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap min-h-[40px]' },
        props.value || '暂无'),
    ])
  },
})

const route = useRoute()
const router = useRouter()
const caseId = Number(route.params.id)

const pageLoading = ref(true)
const saving = ref(false)
const executing = ref(false)
const editing = ref(false)
const editingSteps = ref(false)
const activeTab = ref('info')
const executeDialogVisible = ref(false)

const testCase = reactive<Partial<TestCaseData>>({})
const steps = ref<TestStep[]>([])
const editForm = reactive({ title: '', module: '', priority: 'medium', case_type: 'functional', precondition: '', description: '' })
const editSteps = ref<TestStep[]>([])
const executeForm = reactive({ title: '', plan_type: 'manual' })

const priorityColor = (p?: string) => {
  const map: Record<string, string> = { critical: '#ef4444', high: '#f97316', medium: '#3b82f6', low: '#9ca3af' }
  return map[p || ''] || '#9ca3af'
}
const priorityLabel = (p?: string) => {
  const map: Record<string, string> = { critical: 'P0 致命', high: 'P1 高', medium: 'P2 中', low: 'P3 低' }
  return map[p || ''] || p || '-'
}
const statusType = (s?: string) => {
  const map: Record<string, string> = { active: 'success', draft: 'info', deprecated: 'warning', archived: 'danger' }
  return (map[s || ''] || '') as any
}
const statusLabel = (s?: string) => {
  const map: Record<string, string> = { active: '生效', draft: '草稿', deprecated: '已废弃', archived: '已归档' }
  return map[s || ''] || s || '-'
}
const sourceLabel = (s?: string) => {
  const map: Record<string, string> = { manual: '手动创建', ai: 'AI 生成', import: '导入' }
  return map[s || ''] || s || '-'
}
const caseTypeLabel = (t?: string) => {
  const map: Record<string, string> = { functional: '功能测试', performance: '性能测试', security: '安全测试', compatibility: '兼容性测试', ui: 'UI测试' }
  return map[t || ''] || t || '-'
}

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function fillEditForm() {
  editForm.title = testCase.title || ''
  editForm.module = testCase.module || ''
  editForm.priority = testCase.priority || 'medium'
  editForm.case_type = testCase.case_type || 'functional'
  editForm.precondition = testCase.precondition || ''
  editForm.description = testCase.description || ''
}

function cancelEdit() {
  editing.value = false
  fillEditForm()
}

async function handleSave() {
  saving.value = true
  try {
    await updateTestCase(caseId, editForm)
    Object.assign(testCase, editForm)
    editing.value = false
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确认删除该测试用例？删除后无法恢复。', '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await deleteTestCase(caseId)
    ElMessage.success('已删除')
    router.push('/test-cases')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

function startEditSteps() {
  editSteps.value = steps.value.map(s => ({ ...s }))
  editingSteps.value = true
}

function cancelEditSteps() {
  editingSteps.value = false
}

function addStep() {
  editSteps.value.push({ order: editSteps.value.length + 1, action: '', expected_result: '', test_data: '' })
}

function moveStep(idx: number, dir: number) {
  const target = idx + dir
  if (target < 0 || target >= editSteps.value.length) return
  const arr = editSteps.value
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
  arr.forEach((s, i) => (s.order = i + 1))
}

async function saveSteps() {
  saving.value = true
  try {
    editSteps.value.forEach((s, i) => (s.order = i + 1))
    await updateTestCase(caseId, { steps: editSteps.value })
    steps.value = editSteps.value.map(s => ({ ...s }))
    editingSteps.value = false
    ElMessage.success('步骤已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function openExecuteDialog() {
  executeForm.title = `执行 - ${testCase.title || ''}`
  executeForm.plan_type = 'manual'
  executeDialogVisible.value = true
}

async function handleExecute() {
  if (!executeForm.title.trim()) { ElMessage.warning('请输入执行名称'); return }
  executing.value = true
  try {
    const { data } = await createTestExecution({
      title: executeForm.title,
      plan_type: executeForm.plan_type,
      project_id: (testCase as any).project_id,
      case_ids: [caseId],
    })
    const exec = data?.data ?? data
    ElMessage.success('创建成功')
    executeDialogVisible.value = false
    router.push(`/test-cases/strategies/${exec.id}`)
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    executing.value = false
  }
}

async function fetchDetail() {
  try {
    const { data } = await getTestCase(caseId)
    const payload = data?.data ?? data
    Object.assign(testCase, payload)
    steps.value = (payload.steps || []).sort((a: TestStep, b: TestStep) => a.order - b.order)
    fillEditForm()
  } catch (e: any) {
    ElMessage.error(e.message || '加载用例详情失败')
  }
}

onMounted(async () => {
  await fetchDetail()
  pageLoading.value = false
})
</script>
