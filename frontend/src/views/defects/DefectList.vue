<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">缺陷管理</h1>
        <p class="text-gray-500">跟踪和管理项目中的所有缺陷，支持多维度筛选。</p>
      </div>
      <el-button type="primary" color="#4f46e5" class="!rounded-xl" @click="openDialog()">
        + 新建缺陷
      </el-button>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
        <el-input v-model="query.keyword" clearable placeholder="搜索标题 / 模块" @keyup.enter="fetchList" />
        <el-select v-model="query.severity" clearable placeholder="严重度">
          <el-option label="致命" value="critical" />
          <el-option label="严重" value="major" />
          <el-option label="一般" value="medium" />
          <el-option label="轻微" value="minor" />
        </el-select>
        <el-select v-model="query.status" clearable placeholder="状态">
          <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-select v-model="query.project" clearable placeholder="项目" filterable>
          <el-option v-for="p in projects" :key="p" :label="p" :value="p" />
        </el-select>
        <div class="flex gap-2">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" color="#4f46e5" @click="fetchList">查询</el-button>
        </div>
      </div>

      <el-table :data="tableData" v-loading="loading" empty-text="暂无缺陷数据" @row-click="goDetail">
        <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip />
        <el-table-column label="严重度" width="100" align="center">
          <template #default="{ row }">
            <el-tag :color="severityColor(row.severity)" effect="dark" size="small" class="!border-0 !text-white" round>
              {{ severityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="90" align="center">
          <template #default="{ row }">
            <span class="text-sm">{{ priorityLabel(row.priority) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="light" round size="small">
              {{ statusLabelMap(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="120" align="center" show-overflow-tooltip />
        <el-table-column prop="assignee" label="指派人" width="100" align="center" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该缺陷？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small" @click.stop>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑缺陷' : '新建缺陷'"
      width="680px"
      destroy-on-close
      class="!rounded-2xl"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" label-position="right">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入缺陷标题" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-x-4">
          <el-form-item label="严重度" prop="severity">
            <el-select v-model="form.severity" placeholder="请选择" class="w-full">
              <el-option label="致命" value="critical" />
              <el-option label="严重" value="major" />
              <el-option label="一般" value="medium" />
              <el-option label="轻微" value="minor" />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级" prop="priority">
            <el-select v-model="form.priority" placeholder="请选择" class="w-full">
              <el-option label="紧急" value="urgent" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-select v-model="form.status" placeholder="请选择" class="w-full">
              <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="项目" prop="project">
            <el-select v-model="form.project" placeholder="请选择项目" filterable allow-create class="w-full">
              <el-option v-for="p in projects" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
          <el-form-item label="模块" prop="module">
            <el-input v-model="form.module" placeholder="所属模块" />
          </el-form-item>
          <el-form-item label="指派人" prop="assignee">
            <el-input v-model="form.assignee" placeholder="指派给" />
          </el-form-item>
        </div>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="缺陷描述" />
        </el-form-item>
        <el-form-item label="重现步骤">
          <el-input v-model="form.steps" type="textarea" :rows="3" placeholder="1. 打开页面&#10;2. 点击按钮&#10;3. ..." />
        </el-form-item>
        <el-form-item label="期望结果">
          <el-input v-model="form.expected" type="textarea" :rows="2" placeholder="预期表现" />
        </el-form-item>
        <el-form-item label="实际结果">
          <el-input v-model="form.actual" type="textarea" :rows="2" placeholder="实际表现" />
        </el-form-item>
        <el-form-item label="环境信息">
          <el-input v-model="form.environment" placeholder="如：Chrome 120 / macOS 14 / 生产环境" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import request from '../../utils/request'

interface Defect {
  id: number
  title: string
  severity: string
  priority: string
  status: string
  project: string
  module: string
  assignee: string
  description: string
  steps: string
  expected: string
  actual: string
  environment: string
  created_at: string
}

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const tableData = ref<Defect[]>([])
const total = ref(0)
const formRef = ref<FormInstance>()

const projects = ref<string[]>(['月亮邮寄员平台', '数据中台', '移动端 App', '管理后台'])

const statusOptions = [
  { label: '待处理', value: 'open' },
  { label: '已指派', value: 'assigned' },
  { label: '修复中', value: 'fixing' },
  { label: '已解决', value: 'resolved' },
  { label: '已验证', value: 'verified' },
  { label: '已关闭', value: 'closed' },
]

const query = reactive({
  keyword: '',
  severity: '',
  status: '',
  project: '',
  page: 1,
  page_size: 10,
})

const defaultForm = (): Partial<Defect> => ({
  title: '',
  severity: 'medium',
  priority: 'medium',
  status: 'open',
  project: '',
  module: '',
  assignee: '',
  description: '',
  steps: '',
  expected: '',
  actual: '',
  environment: '',
})

const form = reactive<Partial<Defect> & { id?: number }>(defaultForm())

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  severity: [{ required: true, message: '请选择严重度', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const severityColor = (s: string) => {
  const map: Record<string, string> = { critical: '#ef4444', major: '#f97316', medium: '#3b82f6', minor: '#9ca3af' }
  return map[s] || '#9ca3af'
}
const severityLabel = (s: string) => {
  const map: Record<string, string> = { critical: '致命', major: '严重', medium: '一般', minor: '轻微' }
  return map[s] || s
}
const priorityLabel = (p: string) => {
  const map: Record<string, string> = { urgent: '🔴 紧急', high: '🟠 高', medium: '🔵 中', low: '⚪ 低' }
  return map[p] || p
}

const statusTagType = (s: string) => {
  const map: Record<string, string> = { open: 'danger', assigned: '', fixing: 'warning', resolved: 'success', verified: 'info', closed: 'info' }
  return (map[s] ?? '') as any
}
const statusLabelMap = (s: string) => {
  const map: Record<string, string> = { open: '待处理', assigned: '已指派', fixing: '修复中', resolved: '已解决', verified: '已验证', closed: '已关闭' }
  return map[s] || s
}

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function fetchList() {
  loading.value = true
  try {
    const { data } = await request.get('/defects', { params: query })
    const payload = data?.data ?? data
    tableData.value = payload?.items ?? payload?.list ?? []
    total.value = payload?.total ?? 0
  } catch (e: any) {
    ElMessage.error(e.message || '加载缺陷列表失败')
  } finally {
    loading.value = false
  }
}

function handleReset() {
  query.keyword = ''
  query.severity = ''
  query.status = ''
  query.project = ''
  query.page = 1
  fetchList()
}

function goDetail(row: Defect) {
  router.push(`/defects/${row.id}`)
}

function openDialog(row?: Defect) {
  isEdit.value = !!row
  Object.assign(form, row ? { ...row } : { ...defaultForm(), id: undefined })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value && form.id) {
      await request.put(`/defects/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/defects', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await request.delete(`/defects/${id}`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(fetchList)
</script>
<style scoped>
:deep(.el-table__row) {
  cursor: pointer;
}
</style>

