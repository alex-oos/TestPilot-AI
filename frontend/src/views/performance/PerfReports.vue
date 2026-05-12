<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900 mb-2">性能执行报告</h1>
      <p class="text-gray-500">查看性能测试执行记录和关键指标数据。</p>
    </div>

    <!-- Summary cards -->
    <div v-if="selectedExecution" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
            <span class="text-lg">⏱️</span>
          </div>
          <span class="text-sm text-slate-400">平均响应时间</span>
        </div>
        <p class="text-3xl font-bold text-slate-800">
          {{ selectedExecution.avg_response_time != null ? `${selectedExecution.avg_response_time}ms` : '--' }}
        </p>
      </div>
      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl">
            <span class="text-lg">📊</span>
          </div>
          <span class="text-sm text-slate-400">P95 响应时间</span>
        </div>
        <p class="text-3xl font-bold text-slate-800">
          {{ selectedExecution.p95_response_time != null ? `${selectedExecution.p95_response_time}ms` : '--' }}
        </p>
      </div>
      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2.5 bg-green-50 text-green-600 rounded-xl">
            <span class="text-lg">⚡</span>
          </div>
          <span class="text-sm text-slate-400">TPS (每秒事务数)</span>
        </div>
        <p class="text-3xl font-bold text-slate-800">
          {{ selectedExecution.tps != null ? selectedExecution.tps.toLocaleString() : '--' }}
        </p>
      </div>
      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2.5 bg-red-50 text-red-600 rounded-xl">
            <span class="text-lg">❌</span>
          </div>
          <span class="text-sm text-slate-400">错误率</span>
        </div>
        <p class="text-3xl font-bold" :class="errorRateClass(selectedExecution.error_rate)">
          {{ selectedExecution.error_rate != null ? `${selectedExecution.error_rate}%` : '--' }}
        </p>
      </div>
    </div>

    <!-- Execution list -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-slate-800">执行记录</h3>
        <el-button :loading="loadingBaseline" @click="fetchBaselines">刷新基线</el-button>
      </div>

      <el-table
        :data="executions"
        v-loading="loading"
        empty-text="暂无执行记录"
        stripe
        highlight-current-row
        @row-click="selectExecution"
      >
        <el-table-column prop="scenario_name" label="场景名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light" round>
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column label="结束时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="平均响应" width="110" align="center">
          <template #default="{ row }">
            <span v-if="row.avg_response_time != null">{{ row.avg_response_time }}ms</span>
            <span v-else class="text-slate-400">--</span>
          </template>
        </el-table-column>
        <el-table-column label="P95" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.p95_response_time != null">{{ row.p95_response_time }}ms</span>
            <span v-else class="text-slate-400">--</span>
          </template>
        </el-table-column>
        <el-table-column label="TPS" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.tps != null">{{ row.tps }}</span>
            <span v-else class="text-slate-400">--</span>
          </template>
        </el-table-column>
        <el-table-column label="错误率" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.error_rate != null" :class="errorRateClass(row.error_rate)">
              {{ row.error_rate }}%
            </span>
            <span v-else class="text-slate-400">--</span>
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

    <!-- Baseline comparison -->
    <div v-if="baselines.length > 0" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <h3 class="text-lg font-semibold text-slate-800 mb-4">性能基线</h3>
      <el-table :data="baselines" stripe>
        <el-table-column prop="scenario_name" label="场景名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="基线平均响应" width="140" align="center">
          <template #default="{ row }">
            {{ row.avg_response_time != null ? `${row.avg_response_time}ms` : '--' }}
          </template>
        </el-table-column>
        <el-table-column label="基线 P95" width="120" align="center">
          <template #default="{ row }">
            {{ row.p95_response_time != null ? `${row.p95_response_time}ms` : '--' }}
          </template>
        </el-table-column>
        <el-table-column label="基线 TPS" width="100" align="center">
          <template #default="{ row }">
            {{ row.tps != null ? row.tps : '--' }}
          </template>
        </el-table-column>
        <el-table-column label="基线错误率" width="120" align="center">
          <template #default="{ row }">
            {{ row.error_rate != null ? `${row.error_rate}%` : '--' }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../utils/request'

interface PerfExecution {
  id: string
  scenario_name: string
  status: string
  started_at: string
  finished_at: string
  avg_response_time: number | null
  p95_response_time: number | null
  tps: number | null
  error_rate: number | null
}

interface Baseline {
  id: string
  scenario_name: string
  avg_response_time: number | null
  p95_response_time: number | null
  tps: number | null
  error_rate: number | null
  updated_at: string
}

const loading = ref(false)
const loadingBaseline = ref(false)
const executions = ref<PerfExecution[]>([])
const baselines = ref<Baseline[]>([])
const selectedExecution = ref<PerfExecution | null>(null)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

onMounted(() => {
  fetchExecutions()
  fetchBaselines()
})

async function fetchExecutions() {
  loading.value = true
  try {
    const resp = await api.get('/performance/executions', {
      params: { page: page.value, page_size: pageSize.value },
    })
    const data = resp.data?.data || resp.data || {}
    executions.value = data.items || data || []
    total.value = data.total || executions.value.length
    if (executions.value.length > 0 && !selectedExecution.value) {
      selectedExecution.value = executions.value[0]
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '加载执行记录失败')
  } finally {
    loading.value = false
  }
}

async function fetchBaselines() {
  loadingBaseline.value = true
  try {
    const resp = await api.get('/performance/baselines')
    const data = resp.data?.data || resp.data || {}
    baselines.value = data.items || data || []
  } catch {
    // baselines are optional
  } finally {
    loadingBaseline.value = false
  }
}

function handleSizeChange() {
  page.value = 1
  fetchExecutions()
}

function selectExecution(row: PerfExecution) {
  selectedExecution.value = row
}

function statusType(status: string) {
  const map: Record<string, string> = {
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    pending: 'info',
  }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    pending: '等待中',
  }
  return map[status] || status
}

function errorRateClass(rate: number | null) {
  if (rate == null) return 'text-slate-800'
  if (rate > 5) return 'text-red-500'
  if (rate > 1) return 'text-orange-500'
  return 'text-green-600'
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
:deep(.el-table__row) {
  cursor: pointer;
}
</style>
