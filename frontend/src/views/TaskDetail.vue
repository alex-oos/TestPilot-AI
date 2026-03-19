<template>
  <div class="space-y-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-1">任务详情</h1>
        <p class="text-gray-400 text-sm font-mono">{{ taskId }}</p>
      </div>
      <div class="flex items-center gap-3">
        <el-button @click="router.push('/tasks')" plain class="!rounded-xl">返回任务列表</el-button>
        <el-button @click="router.push('/generate')" plain class="!rounded-xl">新建任务</el-button>
      </div>
    </div>

    <div class="rounded-2xl p-5 flex items-center gap-4 transition-all duration-500" :class="bannerClass">
      <div class="text-3xl">{{ bannerIcon }}</div>
      <div>
        <p class="font-bold text-lg">{{ bannerTitle }}</p>
        <p class="text-sm opacity-80">{{ bannerSubtitle }}</p>
      </div>
      <div v-if="task.status === 'running'" class="ml-auto">
        <div class="w-6 h-6 border-3 border-white border-t-transparent rounded-full animate-spin"></div>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
      <div class="flex items-center justify-between mb-5">
        <h2 class="text-lg font-semibold text-gray-800">AI 正在生成测试用例...</h2>
        <span class="text-sm text-gray-400">按阶段线性执行</span>
      </div>

      <div class="space-y-4">
        <div
          v-for="stage in orderedStages"
          :key="stage.key"
          class="rounded-2xl border overflow-hidden transition-all"
          :class="stageContainerClass(stage)"
        >
          <button
            class="w-full text-left px-5 py-4 md:px-7 md:py-5 flex items-center justify-between gap-4"
            :class="stageHeaderClass(stage)"
            @click="toggleStage(stage.key)"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="text-2xl shrink-0">{{ stage.icon }}</div>
              <div class="min-w-0">
                <div class="text-xl font-bold text-white truncate">{{ stage.title }}</div>
                <div class="text-white/90 text-sm mt-1 flex items-center gap-2">
                  <span class="px-2 py-0.5 rounded-full bg-white/20">Stage {{ stage.index }}</span>
                  <span>{{ phaseStatusLabel(stage.phase.status) }}</span>
                </div>
              </div>
            </div>
            <span class="text-2xl text-white/90 shrink-0">{{ isExpanded(stage.key) ? '⌃' : '⌄' }}</span>
          </button>

          <div v-if="isExpanded(stage.key)" class="bg-white px-5 py-5 md:px-7 md:py-6 border-t" :class="stageBodyBorderClass(stage)">
            <div class="mb-4">
              <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="stageProgressColorClass(stage)"
                  :style="{ width: `${stageProgress(stage.phase.status)}%` }"
                ></div>
              </div>
              <p class="text-sm text-gray-500 mt-2">{{ stageHint(stage) }}</p>
            </div>

            <div v-if="stage.key === 'analysis'" class="space-y-4">
              <div class="rounded-xl border border-blue-100 bg-blue-50/40 p-4">
                <p class="text-sm font-semibold text-blue-700 mb-2">需求分析</p>
                <pre class="whitespace-pre-wrap text-sm text-slate-700 leading-6 font-sans">{{ analysisText || '等待分析结果...' }}</pre>
              </div>
              <div class="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
                <p class="text-sm font-semibold text-indigo-700 mb-2">测试策略</p>
                <pre class="whitespace-pre-wrap text-sm text-slate-700 leading-6 font-sans">{{ designText || '等待策略输出...' }}</pre>
              </div>
            </div>

            <div v-if="stage.key === 'generation'" class="space-y-4">
              <div class="flex items-center justify-between bg-slate-50 rounded-xl border border-slate-200 px-4 py-3">
                <span class="text-sm text-slate-600">已生成测试用例</span>
                <span class="text-xl font-bold text-slate-800">{{ cases.length }}</span>
              </div>
              <div class="rounded-xl border border-purple-100 bg-purple-50/40 p-4">
                <p class="text-sm font-semibold text-purple-700 mb-2">用例预览（前 5 条）</p>
                <ul v-if="cases.length" class="space-y-2">
                  <li v-for="item in cases.slice(0, 5)" :key="item.id" class="text-sm text-slate-700">
                    {{ item.id }}. {{ item.title }}
                  </li>
                </ul>
                <p v-else class="text-sm text-slate-500">等待用例生成中...</p>
              </div>
            </div>

            <div v-if="stage.key === 'review'" class="space-y-4">
              <div class="flex items-center gap-4 rounded-xl border border-emerald-100 bg-emerald-50/40 p-4">
                <div class="text-center min-w-[80px]">
                  <div class="text-3xl font-black" :class="scoreColor">{{ review.quality_score ?? '--' }}</div>
                  <div class="text-xs text-gray-500">质量评分</div>
                </div>
                <div class="flex-1">
                  <el-progress :percentage="review.quality_score ?? 0" :color="scoreProgressColor" :stroke-width="8" />
                  <p class="text-sm text-slate-600 mt-2">{{ review.summary || '等待评审结果...' }}</p>
                </div>
              </div>

              <div v-if="review.issues?.length" class="rounded-xl border border-red-100 bg-red-50/40 p-4">
                <p class="text-sm font-semibold text-red-700 mb-2">发现问题（{{ review.issues.length }}）</p>
                <ul class="space-y-2">
                  <li v-for="(issue, i) in review.issues" :key="i" class="text-sm text-slate-700">• {{ issue }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="task.status === 'completed'" class="animate-fade-in-up">
      <el-tabs v-model="activeTab" class="results-tabs">
        <el-tab-pane label="📋 测试用例" name="cases">
          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mt-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-800">
                测试用例
                <span class="ml-2 text-sm font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">共 {{ cases.length }} 条</span>
              </h3>
              <div class="flex gap-2">
                <el-button size="small" @click="exportExcel" :loading="exporting.excel" class="!rounded-lg">📊 导出 Excel</el-button>
                <el-button size="small" @click="exportXmind" :loading="exporting.xmind" class="!rounded-lg">🗺️ 导出 XMind</el-button>
                <el-button size="small" type="primary" @click="syncMs" :loading="exporting.ms" class="!rounded-lg">🔗 同步 MS</el-button>
              </div>
            </div>

            <el-table :data="cases" border style="width: 100%;" :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600' }">
              <el-table-column prop="id" label="编号" width="70" align="center" />
              <el-table-column prop="module" label="模块" width="120" />
              <el-table-column prop="title" label="用例标题" width="200" />
              <el-table-column prop="precondition" label="前置条件" width="130" />
              <el-table-column prop="steps" label="测试步骤">
                <template #default="scope">
                  <pre class="font-sans whitespace-pre-wrap text-sm text-gray-600 m-0">{{ scope.row.steps }}</pre>
                </template>
              </el-table-column>
              <el-table-column prop="expected_result" label="预期结果" />
              <el-table-column prop="priority" label="优先级" width="85" align="center">
                <template #default="scope">
                  <el-tag :type="scope.row.priority === '高' ? 'danger' : scope.row.priority === '低' ? 'success' : 'warning'" effect="light" round size="small">
                    {{ scope.row.priority }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="🗺️ 思维导图" name="mindmap">
          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mt-4">
            <div class="bg-slate-900 rounded-xl p-6 overflow-auto max-h-[600px]">
              <pre class="text-green-400 text-sm font-mono whitespace-pre-wrap">{{ task.mindmap }}</pre>
            </div>
            <p class="text-xs text-gray-400 mt-3 text-center">
              复制上方内容，粘贴到
              <a href="https://markmap.js.org/repl" target="_blank" class="text-indigo-500 underline">Markmap REPL</a>
              可查看交互式思维导图
            </p>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-if="task.status === 'failed'" class="bg-white rounded-2xl border border-red-200 shadow-sm p-8 text-center">
      <div class="text-5xl mb-4">😞</div>
      <h3 class="text-xl font-bold text-red-600 mb-2">任务执行失败</h3>
      <p class="text-gray-500 text-sm mb-6">{{ task.error || '发生未知错误，请重试' }}</p>
      <el-button type="primary" color="#4f46e5" @click="router.push('/generate')" class="!rounded-xl">重新生成</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { updateTaskStatusInHistory } from '../utils/taskHistory'

type PhaseKey = 'analysis' | 'generation' | 'review'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const activeTab = ref('cases')
const exporting = ref({ excel: false, xmind: false, ms: false })
const expandedStages = ref<PhaseKey[]>(['analysis'])

const task = ref<any>({
  id: taskId,
  status: 'pending',
  phases: {
    analysis: { status: 'pending', label: '需求分析', data: null },
    generation: { status: 'pending', label: '用例编写', data: null },
    review: { status: 'pending', label: '用例评审', data: null },
  },
  mindmap: null,
  error: null,
})

const stageMeta: Record<PhaseKey, { index: number; title: string; icon: string }> = {
  analysis: { index: 1, title: '需求分析阶段', icon: '⚙️' },
  generation: { index: 2, title: '测试用例生成阶段', icon: '🧪' },
  review: { index: 3, title: '测试用例评审阶段', icon: '📝' },
}

let eventSource: EventSource | null = null

onMounted(async () => {
  await fetchTaskSnapshot()
  startSSE()
})

onUnmounted(() => {
  eventSource?.close()
})

async function fetchTaskSnapshot() {
  try {
    const resp = await axios.get(`/api/use_cases/task/${taskId}`)
    if (resp.data?.data) {
      task.value = { ...task.value, ...resp.data.data }
      syncExpandedStage()
      updateTaskStatusInHistory(taskId, task.value.status)
    }
  } catch {
    // snapshot only for initial hydration; ignore if not available yet
  }
}

function startSSE() {
  eventSource = new EventSource(`/api/use_cases/task/${taskId}/stream`)

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      task.value = { ...task.value, ...data }
      syncExpandedStage()
      updateTaskStatusInHistory(taskId, task.value.status)

      if (data.status === 'completed' || data.status === 'failed') {
        eventSource?.close()
      }
    } catch (err) {
      console.error('SSE parse error', err)
    }
  }

  eventSource.onerror = () => {
    eventSource?.close()
  }
}

const orderedStages = computed(() => {
  const phases = task.value.phases ?? {}
  const keys: PhaseKey[] = ['analysis', 'generation', 'review']

  return keys.map((key) => ({
    key,
    index: stageMeta[key].index,
    title: stageMeta[key].title,
    icon: stageMeta[key].icon,
    phase: phases[key] ?? { status: 'pending', label: stageMeta[key].title, data: null }
  }))
})

const cases = computed<any[]>(() => task.value.phases?.generation?.data?.cases ?? [])
const analysisText = computed(() => task.value.phases?.analysis?.data?.analysis ?? '')
const designText = computed(() => task.value.phases?.analysis?.data?.design ?? '')
const review = computed(() => task.value.phases?.review?.data?.review ?? {})

const bannerClass = computed(() => {
  switch (task.value.status) {
    case 'running': return 'bg-gradient-to-r from-blue-600 to-blue-500 text-white'
    case 'completed': return 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white'
    case 'failed': return 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
    default: return 'bg-gray-100 text-gray-600'
  }
})

const bannerIcon = computed(() => {
  switch (task.value.status) {
    case 'running': return '🤖'
    case 'completed': return '🎉'
    case 'failed': return '❌'
    default: return '⏳'
  }
})

const bannerTitle = computed(() => {
  switch (task.value.status) {
    case 'pending': return '任务已创建，等待执行...'
    case 'running': return 'AI 正在生成测试用例...'
    case 'completed': return '全部完成！测试用例已生成'
    case 'failed': return '任务执行失败'
    default: return ''
  }
})

const bannerSubtitle = computed(() => {
  const running = Object.values(task.value.phases ?? {}).find((p: any) => p.status === 'running') as any
  if (running) return `当前正在执行：${running.label}`
  if (task.value.status === 'completed') return `共生成 ${cases.value.length} 条测试用例，质量评分 ${review.value.quality_score ?? '--'} 分`
  return '请稍候...'
})

const scoreColor = computed(() => {
  const s = review.value.quality_score ?? 0
  return s >= 80 ? 'text-emerald-600' : s >= 60 ? 'text-amber-500' : 'text-red-500'
})

const scoreProgressColor = computed(() => {
  const s = review.value.quality_score ?? 0
  return s >= 80 ? '#10b981' : s >= 60 ? '#f59e0b' : '#ef4444'
})

function syncExpandedStage() {
  const current = orderedStages.value.find((s) => s.phase.status === 'running')
  if (current && !expandedStages.value.includes(current.key)) {
    expandedStages.value = [current.key]
    return
  }

  if (task.value.status === 'completed') {
    expandedStages.value = ['review']
  }
}

function toggleStage(key: PhaseKey) {
  if (isExpanded(key)) {
    expandedStages.value = expandedStages.value.filter((k) => k !== key)
  } else {
    expandedStages.value = [key]
  }
}

function isExpanded(key: PhaseKey) {
  return expandedStages.value.includes(key)
}

function stageProgress(status: string) {
  switch (status) {
    case 'pending': return 5
    case 'running': return 55
    case 'completed': return 100
    case 'failed': return 100
    default: return 0
  }
}

function phaseStatusLabel(status: string) {
  switch (status) {
    case 'pending': return '等待中'
    case 'running': return '执行中...'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return '--'
  }
}

function stageHint(stage: any) {
  switch (stage.phase.status) {
    case 'running': return `${stage.title}正在执行，请稍候...`
    case 'completed': return `${stage.title}已完成`
    case 'failed': return `${stage.title}执行失败`
    default: return `${stage.title}等待执行`
  }
}

function stageHeaderClass(stage: any) {
  if (stage.index === 1) return 'bg-gradient-to-r from-blue-600 to-blue-500'
  if (stage.index === 2) return 'bg-gradient-to-r from-violet-600 to-purple-500'
  return 'bg-gradient-to-r from-emerald-600 to-green-500'
}

function stageContainerClass(stage: any) {
  return stage.phase.status === 'failed'
    ? 'border-red-200'
    : stage.phase.status === 'completed'
      ? 'border-emerald-200'
      : 'border-slate-200'
}

function stageBodyBorderClass(stage: any) {
  if (stage.index === 1) return 'border-blue-100'
  if (stage.index === 2) return 'border-purple-100'
  return 'border-emerald-100'
}

function stageProgressColorClass(stage: any) {
  if (stage.phase.status === 'failed') return 'bg-red-500'
  if (stage.index === 1) return 'bg-blue-500'
  if (stage.index === 2) return 'bg-purple-500'
  return 'bg-emerald-500'
}

async function exportExcel() {
  if (!cases.value.length) return
  exporting.value.excel = true
  try {
    const resp = await axios.post('/api/use_cases/export/excel', { cases: cases.value }, { responseType: 'blob' })
    downloadBlob(resp.data, 'test_cases.xlsx')
    ElMessage.success('Excel 导出成功')
  } catch {
    ElMessage.error('Excel 导出失败')
  } finally {
    exporting.value.excel = false
  }
}

async function exportXmind() {
  if (!cases.value.length) return
  exporting.value.xmind = true
  try {
    const resp = await axios.post(
      '/api/use_cases/export/xmind',
      { cases: cases.value, title: 'AI自动生成测试用例' },
      { responseType: 'blob' }
    )
    downloadBlob(resp.data, 'test_cases.xmind')
    ElMessage.success('XMind 文件导出成功')
  } catch {
    ElMessage.error('XMind 导出失败')
  } finally {
    exporting.value.xmind = false
  }
}

async function syncMs() {
  if (!cases.value.length) return
  exporting.value.ms = true
  try {
    const resp = await axios.post('/api/use_cases/sync/ms', { cases: cases.value })
    ElMessage.success(resp.data.data.message || '同步成功')
  } catch {
    ElMessage.error('同步失败')
  } finally {
    exporting.value.ms = false
  }
}

function downloadBlob(data: Blob, filename: string) {
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 0.5s ease-out forwards;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

:deep(.results-tabs .el-tabs__header) {
  margin-bottom: 0;
}

:deep(.results-tabs .el-tabs__item) {
  font-size: 14px;
  padding: 10px 20px;
}

:deep(.results-tabs .el-tabs__item.is-active) {
  color: #4f46e5;
  font-weight: 600;
}

:deep(.results-tabs .el-tabs__active-bar) {
  background-color: #4f46e5;
}
</style>
