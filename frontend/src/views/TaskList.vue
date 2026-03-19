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

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <el-table :data="tasks" empty-text="暂无任务，先创建一个吧" row-class-name="task-row" @row-click="goDetail">
        <el-table-column prop="id" label="任务 ID" min-width="240" show-overflow-tooltip />
        <el-table-column prop="sourceLabel" label="来源" width="140" align="center" />
        <el-table-column label="状态" width="140" align="center">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="light" round>
              {{ statusLabel(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="190">
          <template #default="scope">{{ formatTime(scope.row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="最后更新" min-width="190">
          <template #default="scope">{{ formatTime(scope.row.updatedAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="scope">
            <el-button link type="primary" @click.stop="goDetail(scope.row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { getTaskHistory, type TaskHistoryItem } from '../utils/taskHistory'

const router = useRouter()
const tasks = computed(() => getTaskHistory())

function goDetail(row: TaskHistoryItem) {
  router.push(`/task/${row.id}`)
}

function statusLabel(status: string) {
  switch (status) {
    case 'pending': return '等待中'
    case 'running': return '执行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
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
