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
        <el-input v-model="query.taskName" clearable placeholder="按任务名称查询" @keyup.enter="handleSearch" />
        <el-input v-model="query.taskId" clearable placeholder="按任务ID查询" @keyup.enter="handleSearch" />
        <el-select v-model="query.sourceType" clearable placeholder="按来源查询">
          <el-option label="本地文件" value="local" />
          <el-option label="飞书文档" value="feishu" />
          <el-option label="钉钉文档" value="dingtalk" />
        </el-select>
        <el-select v-model="query.status" clearable placeholder="按状态查询">
          <el-option label="待开始" value="pending" />
          <el-option label="执行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="执行异常" value="failed" />
        </el-select>
        <el-input v-model="query.submitter" clearable placeholder="按提交人查询" @keyup.enter="handleSearch" />
      </div>
      <div class="flex gap-2 justify-end mb-4">
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" color="#4f46e5" @click="handleSearch">查询</el-button>
      </div>

      <el-table :data="tasks" :loading="loading" empty-text="暂无任务，先创建一个吧" row-class-name="task-row" @row-click="goDetail">
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
        <el-table-column label="操作" width="170" align="center">
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

function goDetail(row: any) {
  router.push(`/task/${row.id}`)
}

async function retryTask(row: any) {
  const confirmed = await ElMessageBox.confirm(
    `确认重试任务 ${row.id} 吗？系统将创建一个新任务重新执行。`,
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
    const newTaskId = resp.data?.data?.task_id
    ElMessage.success('重试任务已创建')
    if (newTaskId) {
      router.push(`/task/${newTaskId}`)
      return
    }
    fetchTasks()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.response?.data?.detail || '重试失败，请稍后再试')
  }
}

function sourceLabel(sourceType: string) {
  if (sourceType === 'feishu') return '飞书文档'
  if (sourceType === 'dingtalk') return '钉钉文档'
  return '本地文件'
}

function statusLabel(status: string) {
  switch (status) {
    case 'pending': return '待开始'
    case 'running': return '执行中'
    case 'completed': return '已完成'
    case 'failed': return '执行异常'
    default: return '未知'
  }
}

function statusTagType(status: string) {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'danger'
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
