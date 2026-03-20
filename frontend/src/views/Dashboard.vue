<template>
  <div class="space-y-6">
    <!-- Welcome Section -->
    <div class="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-8 text-white shadow-lg relative overflow-hidden">
      <div class="relative z-10">
        <h1 class="text-3xl font-bold mb-2">欢迎回来，管理员！ 👋</h1>
        <p class="text-indigo-100 max-w-xl text-lg">
          这是您测试环境今天的重点数据。您的团队本周共生成 {{ overview.summary.this_week_new_count }} 个新任务。
        </p>
      </div>
      <!-- Decorative rings -->
      <div class="absolute right-0 top-0 w-64 h-64 bg-white opacity-10 rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2"></div>
      <div class="absolute right-40 bottom-0 w-48 h-48 bg-white opacity-10 rounded-full blur-2xl transform translate-y-1/2"></div>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" v-loading="loading">
      
      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-blue-50 text-blue-600 rounded-xl">
            <span class="text-xl">📄</span>
          </div>
          <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.documents_week_change_pct)">
            {{ trendText(overview.trends.documents_week_change_pct) }}
          </span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">已解析文档总量</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ numberText(overview.summary.total_documents) }}</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
            <span class="text-xl">⚡</span>
          </div>
          <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.generated_week_change_pct)">
            {{ trendText(overview.trends.generated_week_change_pct) }}
          </span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">已生成用例总数</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ numberText(overview.summary.generated_cases_total) }}</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-green-50 text-green-600 rounded-xl">
            <span class="text-xl">✔️</span>
          </div>
          <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.coverage_week_change_pct, true)">
            {{ trendText(overview.trends.coverage_week_change_pct) }}
          </span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">测试用例覆盖率</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ percentText(overview.summary.coverage_rate) }}</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-orange-50 text-orange-600 rounded-xl">
            <span class="text-xl">⏱️</span>
          </div>
          <span class="text-sm font-medium px-2 py-1 rounded-md" :class="trendClass(overview.trends.average_duration_week_change_pct)">
            {{ trendText(overview.trends.average_duration_week_change_pct) }}
          </span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">平均生成耗时</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">{{ durationText(overview.summary.average_duration_seconds) }}</p>
        </div>
      </div>

    </div>

    <!-- Charts / Activity Mock -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <div class="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-6">用例生成动态</h3>
        <div class="h-64 flex items-end justify-between gap-2 px-4 pb-4 border-b border-slate-100">
          <div
            v-for="(item, idx) in overview.weekly_activity"
            :key="item.label"
            class="w-full rounded-t-sm transition-colors relative group"
            :class="idx === currentWeekday ? 'bg-indigo-500 hover:bg-indigo-600 shadow-[0_0_15px_rgba(99,102,241,0.5)]' : 'bg-slate-100 hover:bg-indigo-100'"
            :style="{ height: barHeight(item.value) }"
          >
            <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
              {{ item.value }}
            </div>
          </div>
        </div>
        <div class="flex justify-between text-xs text-slate-400 mt-2 px-4">
          <span
            v-for="(item, idx) in overview.weekly_activity"
            :key="`label-${item.label}`"
            :class="idx === currentWeekday ? 'text-indigo-600 font-medium' : ''"
          >
            {{ item.label }}
          </span>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-6">最近需求来源文档</h3>
        <div class="space-y-4">
          <div v-for="item in overview.source_distribution" :key="item.source_type" class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center text-lg">{{ item.icon }}</div>
              <div>
                <p class="text-sm font-medium text-slate-700">{{ item.label }}</p>
                <p class="text-xs text-slate-400">{{ item.count }} 个任务</p>
              </div>
            </div>
            <span class="text-sm font-semibold text-slate-600">{{ percentText(item.percent) }}</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getDashboardOverview } from '../api/dashboard'

interface DashboardOverview {
  summary: {
    total_documents: number
    generated_cases_total: number
    coverage_rate: number
    average_duration_seconds: number
    this_week_new_count: number
  }
  trends: {
    documents_week_change_pct: number | null
    generated_week_change_pct: number | null
    coverage_week_change_pct: number | null
    average_duration_week_change_pct: number | null
  }
  weekly_activity: Array<{ label: string; value: number }>
  source_distribution: Array<{ source_type: string; label: string; icon: string; count: number; percent: number }>
}

const loading = ref(false)
const overview = ref<DashboardOverview>({
  summary: {
    total_documents: 0,
    generated_cases_total: 0,
    coverage_rate: 0,
    average_duration_seconds: 0,
    this_week_new_count: 0,
  },
  trends: {
    documents_week_change_pct: null,
    generated_week_change_pct: null,
    coverage_week_change_pct: null,
    average_duration_week_change_pct: null,
  },
  weekly_activity: [
    { label: '周一', value: 0 },
    { label: '周二', value: 0 },
    { label: '周三', value: 0 },
    { label: '周四', value: 0 },
    { label: '周五', value: 0 },
    { label: '周六', value: 0 },
    { label: '周日', value: 0 },
  ],
  source_distribution: [],
})

const currentWeekday = computed(() => {
  const day = new Date().getDay()
  return day === 0 ? 6 : day - 1
})

const weeklyMax = computed(() => {
  const max = Math.max(...overview.value.weekly_activity.map((x) => x.value), 1)
  return max
})

onMounted(() => {
  fetchOverview()
})

async function fetchOverview() {
  loading.value = true
  try {
    const resp = await getDashboardOverview()
    if (resp.data?.code === 0 && resp.data?.data) {
      overview.value = {
        ...overview.value,
        ...resp.data.data,
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载首页统计失败')
  } finally {
    loading.value = false
  }
}

function numberText(value: number) {
  return Number(value || 0).toLocaleString('zh-CN')
}

function percentText(value: number) {
  return `${Number(value || 0).toFixed(1)}%`
}

function durationText(value: number) {
  return `${Number(value || 0).toFixed(1)}s`
}

function trendText(value: number | null) {
  if (value === null || Number.isNaN(value)) return '--'
  const v = Number(value)
  if (v > 0) return `+${v.toFixed(1)}%`
  return `${v.toFixed(1)}%`
}

function trendClass(value: number | null, neutralWhenZero = false) {
  if (value === null || Number.isNaN(value) || (neutralWhenZero && value === 0)) {
    return 'text-slate-400 bg-slate-50'
  }
  return value >= 0 ? 'text-green-500 bg-green-50' : 'text-red-500 bg-red-50'
}

function barHeight(value: number) {
  const normalized = Math.max(0, Number(value || 0))
  const minPercent = 18
  const dynamic = Math.round((normalized / weeklyMax.value) * 82)
  return `${minPercent + dynamic}%`
}
</script>
