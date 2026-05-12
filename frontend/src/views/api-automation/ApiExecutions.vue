<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">接口执行报告</h1>
        <p class="text-gray-500">查看接口自动化测试的执行历史与结果汇总。</p>
      </div>
      <el-button type="primary" color="#4f46e5" class="!rounded-xl" :loading="triggering" @click="triggerExecution">
        + 发起执行
      </el-button>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <el-table :data="executions" v-loading="loading" empty-text="暂无执行记录" stripe>
        <el-table-column prop="id" label="执行 ID" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="font-mono text-sm text-slate-600">{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusType(row.status)"
              effect="light"
              round
              :class="{ 'status-running': row.status === 'running' }"
            >
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通过率" min-width="200">
          <template #default="{ row }">
            <div class="flex items-center gap-3">
              <el-progress
                :percentage="passRate(row)"
                :color="progressColor(passRate(row))"
                :stroke-width="8"
                class="flex-1"
              />
              <span class="text-sm text-slate-500 w-12 text-right">{{ passRate(row).toFixed(0) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="total" label="总数" width="80" align="center" />
        <el-table-column prop="passed" label="通过" width="80" align="center">
          <template #default="{ row }">
            <span class="text-green-600 font-medium">{{ row.passed ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed" label="失败" width="80" align="center">
          <template #default="{ row }">
            <span class="text-red-500 font-medium">{{ row.failed ?? 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100" align="center">
          <template #default="{ row }">
            {{ row.duration ? `${row.duration}s` : '--' }}
          </template>
        </el-table-column>
        <el-table-column prop="trigger_type" label="触发方式" width="110" align="center">
          <template #default="{ row }">
            <el-tag type="info" effect="plain" round size="small">
              {{ triggerLabel(row.trigger_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50]"
          :total="total"
          @current-change="fetchExecutions"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../utils/request'

interface Execution {
  id: string
  status: string
  total: number
  passed: number
  failed: number
  duration: number | null
  trigger_type: string
  created_at: string
}

const loading = ref(false)
const triggering = ref(false)
const executions = ref<Execution[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

onMounted(() => {
  fetchExecutions()
})

async function fetchExecutions() {
  loading.value = true
  try {
    const resp = await api.get('/api-automation/executions', {
      params: { page: page.value, page_size: pageSize.value },
    })
    const data = resp.data?.data || resp.data || {}
    executions.value = data.items || data || []
    total.value = data.total || executions.value.length
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '加载执行记录失败')
  } finally {
    loading.value = false
  }
}

function handleSizeChange() {
  page.value = 1
  fetchExecutions()
}

async function triggerExecution() {
  const confirmed = await ElMessageBox.confirm(
    '确认发起一次接口自动化执行？将按照当前接口配置执行全量测试。',
    '发起执行',
    { type: 'info', confirmButtonText: '确认执行', cancelButtonText: '取消' }
  ).catch(() => false)
  if (!confirmed) return

  triggering.value = true
  try {
    await api.post('/api-automation/executions')
    ElMessage.success('执行已触发，请稍后刷新查看结果')
    fetchExecutions()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '触发执行失败')
  } finally {
    triggering.value = false
  }
}

function passRate(row: Execution): number {
  if (!row.total || row.total === 0) return 0
  return ((row.passed ?? 0) / row.total) * 100
}

function progressColor(rate: number): string {
  if (rate >= 90) return '#10b981'
  if (rate >= 60) return '#f59e0b'
  return '#ef4444'
}

function statusType(status: string) {
  const map: Record<string, string> = {
    running: '',
    passed: 'success',
    failed: 'danger',
    partial: 'warning',
  }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    running: '执行中',
    passed: '全部通过',
    failed: '执行失败',
    partial: '部分通过',
    pending: '等待中',
  }
  return map[status] || status
}

function triggerLabel(type: string) {
  const map: Record<string, string> = {
    manual: '手动触发',
    schedule: '定时触发',
    ci: 'CI 触发',
    webhook: 'Webhook',
  }
  return map[type] || type || '手动触发'
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
.status-running {
  animation: blink 1.4s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
