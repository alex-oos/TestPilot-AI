<template>
  <div class="space-y-6" v-loading="pageLoading">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <el-button circle @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/test-cases/strategies' }">测试策略</el-breadcrumb-item>
        <el-breadcrumb-item>测试报告</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- Report title -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-gray-900">{{ report.title || '测试报告' }}</h1>
        <span class="text-sm text-gray-400">生成时间: {{ formatTime(report.generated_at) }}</span>
      </div>
    </div>

    <!-- Summary cards -->
    <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
      <div class="bg-indigo-50 rounded-2xl p-5 ring-1 ring-indigo-200">
        <div class="text-sm text-gray-500 mb-1">总用例</div>
        <div class="text-3xl font-bold text-indigo-700">{{ report.total_cases ?? 0 }}</div>
      </div>
      <div class="rounded-2xl p-5 ring-1" :class="passRateClass">
        <div class="text-sm text-gray-500 mb-1">通过率</div>
        <div class="text-3xl font-bold" :class="passRateTextClass">{{ passRateDisplay }}</div>
      </div>
      <div class="bg-green-50 rounded-2xl p-5 ring-1 ring-green-200">
        <div class="text-sm text-gray-500 mb-1">通过</div>
        <div class="text-3xl font-bold text-green-700">{{ report.passed_cases ?? 0 }}</div>
      </div>
      <div class="bg-red-50 rounded-2xl p-5 ring-1 ring-red-200">
        <div class="text-sm text-gray-500 mb-1">失败</div>
        <div class="text-3xl font-bold text-red-700">{{ report.failed_cases ?? 0 }}</div>
      </div>
      <div class="bg-yellow-50 rounded-2xl p-5 ring-1 ring-yellow-200">
        <div class="text-sm text-gray-500 mb-1">阻塞</div>
        <div class="text-3xl font-bold text-yellow-700">{{ report.blocked_cases ?? 0 }}</div>
      </div>
      <div class="bg-gray-50 rounded-2xl p-5 ring-1 ring-gray-200">
        <div class="text-sm text-gray-500 mb-1">跳过</div>
        <div class="text-3xl font-bold text-gray-600">{{ report.skipped_cases ?? 0 }}</div>
      </div>
    </div>

    <!-- Distribution chart -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-4">结果分布</h2>
      <div class="flex items-center gap-8 flex-wrap">
        <!-- CSS Pie chart -->
        <div class="relative w-48 h-48 shrink-0">
          <svg viewBox="0 0 100 100" class="w-full h-full -rotate-90">
            <circle v-for="(seg, i) in pieSegments" :key="i"
              cx="50" cy="50" r="40" fill="none"
              :stroke="seg.color" stroke-width="20"
              :stroke-dasharray="`${seg.length} ${251.2 - seg.length}`"
              :stroke-dashoffset="`-${seg.offset}`"
            />
            <circle v-if="!pieSegments.length" cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" stroke-width="20" />
          </svg>
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="text-center">
              <div class="text-2xl font-bold" :class="passRateTextClass">{{ passRateDisplay }}</div>
              <div class="text-xs text-gray-400">通过率</div>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="space-y-3 flex-1">
          <div v-for="item in distributionItems" :key="item.label" class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full inline-block" :style="{ backgroundColor: item.color }" />
              <span class="text-sm text-gray-700">{{ item.label }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-sm font-medium text-gray-800">{{ item.count }}</span>
              <span class="text-xs text-gray-400 w-12 text-right">{{ item.pct }}%</span>
            </div>
          </div>
          <!-- Progress bars -->
          <div class="mt-4 space-y-2">
            <div v-for="item in distributionItems" :key="item.label + '-bar'" class="flex items-center gap-3">
              <span class="text-xs text-gray-500 w-8">{{ item.label.slice(0, 2) }}</span>
              <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500" :style="{ width: `${item.pct}%`, backgroundColor: item.color }" />
              </div>
              <span class="text-xs text-gray-500 w-10 text-right">{{ item.pct }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Summary text -->
    <div v-if="report.summary" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
      <h2 class="text-lg font-semibold text-gray-800 mb-3">总结</h2>
      <p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded-xl p-4">{{ report.summary }}</p>
    </div>

    <!-- Results table -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800">执行结果明细</h2>
      </div>
      <el-table :data="results" stripe class="w-full" empty-text="暂无结果数据">
        <el-table-column label="ID" prop="id" width="70" align="center" />
        <el-table-column label="用例名称" min-width="200">
          <template #default="{ row }">
            <span class="font-medium">{{ row.test_case_title || `用例 #${row.test_case_id}` }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="resultStatusType(row.status)" effect="dark" size="small" round>
              {{ resultStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="实际结果" min-width="200">
          <template #default="{ row }">
            <span class="text-sm text-gray-600 whitespace-pre-wrap">{{ row.actual_result || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150">
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
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getTestReport, getTestExecution } from '../../api/test-cases'

const route = useRoute()
const router = useRouter()
const reportId = Number(route.params.id)

const pageLoading = ref(true)
const report = reactive<any>({})
const results = ref<any[]>([])

const resultStatusType = (s?: string) => ({ pending: 'info', passed: 'success', failed: 'danger', blocked: 'warning', skipped: 'info' }[s || ''] || '') as any
const resultStatusLabel = (s?: string) => ({ pending: '待执行', passed: '通过', failed: '失败', blocked: '阻塞', skipped: '跳过' }[s || ''] || s || '')

const passRate = computed(() => {
  if (report.pass_rate != null) return report.pass_rate
  const t = report.total_cases || 0
  if (!t) return 0
  return (report.passed_cases || 0) / t
})

const passRateDisplay = computed(() => `${(passRate.value * 100).toFixed(1)}%`)

const passRateClass = computed(() => {
  const r = passRate.value
  if (r >= 0.9) return 'bg-green-50 ring-green-200'
  if (r >= 0.7) return 'bg-yellow-50 ring-yellow-200'
  return 'bg-red-50 ring-red-200'
})

const passRateTextClass = computed(() => {
  const r = passRate.value
  if (r >= 0.9) return 'text-green-700'
  if (r >= 0.7) return 'text-yellow-700'
  return 'text-red-700'
})

const distributionItems = computed(() => {
  const t = report.total_cases || 1
  return [
    { label: '通过', count: report.passed_cases || 0, color: '#22c55e', pct: +((report.passed_cases || 0) / t * 100).toFixed(1) },
    { label: '失败', count: report.failed_cases || 0, color: '#ef4444', pct: +((report.failed_cases || 0) / t * 100).toFixed(1) },
    { label: '阻塞', count: report.blocked_cases || 0, color: '#eab308', pct: +((report.blocked_cases || 0) / t * 100).toFixed(1) },
    { label: '跳过', count: report.skipped_cases || 0, color: '#9ca3af', pct: +((report.skipped_cases || 0) / t * 100).toFixed(1) },
  ]
})

const pieSegments = computed(() => {
  const circumference = 251.2 // 2 * PI * 40
  const total = report.total_cases || 0
  if (!total) return []
  const items = distributionItems.value.filter(i => i.count > 0)
  let offset = 0
  return items.map(item => {
    const length = (item.count / total) * circumference
    const seg = { color: item.color, length, offset }
    offset += length
    return seg
  })
})

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function fetchReport() {
  try {
    const { data } = await getTestReport(reportId)
    const payload = data?.data ?? data
    Object.assign(report, payload)

    if (payload.execution_id) {
      try {
        const { data: execData } = await getTestExecution(payload.execution_id)
        const execPayload = execData?.data ?? execData
        results.value = execPayload.results || []
      } catch { /* execution results optional */ }
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载报告失败')
  }
}

onMounted(async () => {
  await fetchReport()
  pageLoading.value = false
})
</script>
