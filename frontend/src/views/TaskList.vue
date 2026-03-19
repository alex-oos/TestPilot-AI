<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">任务列表</h1>
        <p class="text-gray-500">查看最近提交的测试用例生成任务，点击可进入详情页。</p>
      </div>
      <el-button type="primary" color="#4f46e5" class="!rounded-xl" @click="router.push('/generate')">
        + 新建生成任务
      </el-button>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-3 mb-4">
        <el-input v-model="query.taskName" clearable placeholder="任务名称" @keyup.enter="handleSearch" />
        <el-input v-model="query.taskId" clearable placeholder="任务ID" @keyup.enter="handleSearch" />
        <el-select v-model="query.sourceType" clearable placeholder="来源">
          <el-option label="本地文件" value="local" />
          <el-option label="飞书文档" value="feishu" />
          <el-option label="钉钉文档" value="dingtalk" />
          <el-option label="手动输入" value="manual" />
        </el-select>
        <el-select v-model="query.status" clearable placeholder="状态">
          <el-option label="已上传" value="uploaded" />
          <el-option label="排队中" value="queued" />
          <el-option label="待开始" value="pending" />
          <el-option label="执行中" value="running" />
          <el-option label="待采纳确认" value="waiting_decision" />
          <el-option label="已完成" value="completed" />
          <el-option label="需求分析异常" value="analysis_failed" />
          <el-option label="用例编写异常" value="generation_failed" />
          <el-option label="用例评审异常" value="review_failed" />
          <el-option label="执行异常" value="failed" />
        </el-select>
        <el-input v-model="query.submitter" clearable placeholder="提交人" @keyup.enter="handleSearch" />
      </div>
      <div class="flex items-center justify-between mb-4">
        <el-button
          type="danger"
          plain
          :disabled="selectedTaskIds.length === 0"
          @click="batchDeleteTasks"
        >
          批量删除
        </el-button>
        <div class="flex gap-2">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" color="#4f46e5" @click="handleSearch">查询</el-button>
        </div>
      </div>

      <el-table
        :data="tasks"
        :loading="loading"
        empty-text="暂无任务，先创建一个吧"
        row-class-name="task-row"
        row-key="id"
        @row-click="goDetail"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="52" align="center" />
        <el-table-column prop="task_name" label="任务名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="id" label="任务 ID" min-width="240" show-overflow-tooltip />
        <el-table-column label="来源" width="140" align="center">
          <template #default="scope">{{ sourceLabel(scope.row.source_type) }}</template>
        </el-table-column>
        <el-table-column prop="submitter" label="提交人" width="140" align="center" />
        <el-table-column label="状态" width="140" align="center">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="light" round>
              {{ statusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="190">
          <template #default="scope">{{ formatTime(scope.row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最后更新" min-width="190">
          <template #default="scope">{{ formatTime(scope.row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center">
          <template #default="scope">
            <el-button link type="primary" @click.stop="goDetail(scope.row)">查看详情</el-button>
            <el-button
              link
              type="warning"
              :disabled="scope.row.status === 'running'"
              @click.stop="retryTask(scope.row)"
            >
              重试
            </el-button>
            <el-button
              link
              type="danger"
              @click.stop="deleteTask(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[10, 20, 50]"
          :total="total"
          @current-change="fetchTasks"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const tasks = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const selectedTaskIds = ref<string[]>([])
const query = reactive({
  taskName: '',
  taskId: '',
  sourceType: '',
  status: '',
  submitter: '',
})

onMounted(() => {
  fetchTasks()
})

async function fetchTasks() {
  loading.value = true
  try {
    const resp = await axios.get('/api/use_cases/tasks', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        task_name: query.taskName || undefined,
        task_id: query.taskId || undefined,
        source_type: query.sourceType || undefined,
        status: query.status || undefined,
        submitter: query.submitter || undefined,
      }
    })
    const data = resp.data?.data || {}
    tasks.value = data.items || []
    total.value = data.total || 0
    selectedTaskIds.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchTasks()
}

function handleReset() {
  query.taskId = ''
  query.taskName = ''
  query.sourceType = ''
  query.status = ''
  query.submitter = ''
  page.value = 1
  fetchTasks()
}

function handleSizeChange() {
  page.value = 1
  fetchTasks()
}

function handleSelectionChange(rows: any[]) {
  selectedTaskIds.value = rows.map((item) => item.id).filter(Boolean)
}

function goDetail(row: any, column?: any) {
  if (column?.type === 'selection' || column?.label === '操作') return
  router.push(`/task/${row.id}`)
}

async function retryTask(row: any) {
  const confirmed = await ElMessageBox.confirm(
    `确认重试任务 ${row.id} 吗？将使用同一任务ID重新执行。`,
    '提示',
    {
      type: 'warning',
      confirmButtonText: '确认重试',
      cancelButtonText: '取消',
    }
  ).catch(() => false)
  if (!confirmed) return

  try {
    const resp = await axios.post(`/api/use_cases/task/${row.id}/retry`)
    const sameTaskId = resp.data?.data?.task_id || row.id
    ElMessage.success('任务已重试')
    if (sameTaskId) {
      router.push(`/task/${sameTaskId}`)
      return
    }
    fetchTasks()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.response?.data?.detail || '重试失败，请稍后再试')
  }
}

async function deleteTask(row: any) {
  const confirmed = await ElMessageBox.confirm(
    `确认删除任务 ${row.id} 吗？删除后不可恢复。`,
    '提示',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    }
  ).catch(() => false)
  if (!confirmed) return

  try {
    await axios.delete(`/api/use_cases/task/${row.id}`)
    ElMessage.success('任务已删除')
    if (tasks.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await fetchTasks()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.response?.data?.detail || '删除失败，请稍后再试')
  }
}

async function batchDeleteTasks() {
  if (selectedTaskIds.value.length === 0) return
  const ids = [...selectedTaskIds.value]
  const confirmed = await ElMessageBox.confirm(
    `确认批量删除已选中的 ${ids.length} 个任务吗？删除后不可恢复。`,
    '提示',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    }
  ).catch(() => false)
  if (!confirmed) return

  try {
    await axios.delete('/api/use_cases/tasks', { data: { task_ids: ids } })
    ElMessage.success(`已删除 ${ids.length} 个任务`)
    if (tasks.value.length === ids.length && page.value > 1) {
      page.value -= 1
    }
    await fetchTasks()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.response?.data?.detail || '批量删除失败，请稍后再试')
  }
}

function sourceLabel(sourceType: string) {
  if (sourceType === 'feishu') return '飞书文档'
  if (sourceType === 'dingtalk') return '钉钉文档'
  if (sourceType === 'manual') return '手动输入'
  return '本地文件'
}

function statusLabel(status: string) {
  switch (status) {
    case 'uploaded': return '已上传'
    case 'queued': return '排队中'
    case 'pending': return '待开始'
    case 'running': return '执行中'
    case 'waiting_decision': return '待采纳确认'
    case 'completed': return '已完成'
    case 'analysis_failed': return '需求分析异常'
    case 'generation_failed': return '用例编写异常'
    case 'review_failed': return '用例评审异常'
    case 'failed': return '执行异常'
    default: return '未知'
  }
}

function statusTagType(status: string) {
  switch (status) {
    case 'completed': return 'success'
    case 'analysis_failed': return 'danger'
    case 'generation_failed': return 'danger'
    case 'review_failed': return 'danger'
    case 'failed': return 'danger'
    case 'waiting_decision': return 'warning'
    case 'running': return 'warning'
    default: return 'info'
  }
}

function formatTime(value: string) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
}
</script>

<style scoped>
:deep(.task-row) {
  cursor: pointer;
}
</style>
