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
      <div class="flex items-center justify-between mb-8">
        <h2 class="text-lg font-semibold text-gray-800">AI 正在生成测试用例...</h2>
        <span class="text-sm text-gray-400">横向时间线</span>
      </div>

      <div class="relative pb-3">
        <div class="absolute top-5 left-0 right-0 h-1 bg-slate-200 rounded-full"></div>
        <div
          class="absolute top-5 left-0 h-1 bg-indigo-500 rounded-full transition-all duration-500"
          :style="{ width: timelineProgressWidth }"
        ></div>

        <div class="relative grid grid-cols-3 gap-4">
          <button
            v-for="stage in orderedStages"
            :key="stage.key"
            class="flex flex-col items-center text-center gap-2 py-1"
            :class="{ 'cursor-not-allowed opacity-45': !canSelectStage(stage) }"
            :disabled="!canSelectStage(stage)"
            @click="selectStage(stage)"
          >
            <div
              class="w-10 h-10 rounded-full border-2 flex items-center justify-center text-sm font-bold transition-all"
              :class="stageDotClass(stage)"
            >
              <span v-if="stage.phase.status === 'running'" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin inline-block"></span>
              <span v-else-if="stage.phase.status === 'completed'">✓</span>
              <span v-else-if="stage.phase.status === 'failed'">✕</span>
              <span v-else>{{ stage.index }}</span>
            </div>
            <div class="text-sm font-semibold text-slate-800">{{ stage.title }}</div>
            <div class="text-xs" :class="stageTextClass(stage.phase.status)">{{ phaseStatusLabel(stage.phase.status) }}</div>
          </button>
        </div>
      </div>

      <div class="mt-6 rounded-2xl border p-5 md:p-6" :class="stageContainerClass(selectedStageData)">
        <div class="mb-4">
          <div class="flex items-center gap-3">
            <span class="text-2xl">{{ selectedStageData.icon }}</span>
            <div>
              <h3 class="text-xl font-bold text-slate-800">{{ selectedStageData.title }}</h3>
              <p class="text-sm text-slate-500">Stage {{ selectedStageData.index }} · {{ phaseStatusLabel(selectedStageData.phase.status) }}</p>
            </div>
          </div>
          <div class="h-2 bg-slate-100 rounded-full overflow-hidden mt-4">
            <div
              class="h-full rounded-full transition-all duration-500"
              :class="stageProgressColorClass(selectedStageData)"
              :style="{ width: `${stageProgress(selectedStageData.phase.status)}%` }"
            ></div>
          </div>
          <p class="text-sm text-gray-500 mt-2">{{ stageHint(selectedStageData) }}</p>
        </div>

        <div v-if="selectedStage === 'analysis'" class="space-y-4">
          <div class="rounded-xl border border-amber-100 bg-amber-50/40 p-4">
            <p class="text-sm font-semibold text-amber-700 mb-3">需求分析子节点（实时）</p>
            <div v-if="analysisSubSteps.length" class="space-y-2">
              <div
                v-for="item in analysisSubSteps"
                :key="item.key"
                class="flex items-center justify-between rounded-lg border border-amber-100 bg-white px-3 py-2"
              >
                <span class="text-sm text-slate-700">{{ item.label }}</span>
                <div class="flex items-center gap-2">
                  <span
                    v-if="item.status === 'running'"
                    class="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin inline-block"
                  ></span>
                  <el-tag :type="subStepTagType(item.status)" effect="light" size="small" round>
                    {{ phaseStatusLabel(item.status) }}
                  </el-tag>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-slate-500">等待子节点状态...</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
            <p class="text-sm font-semibold text-slate-700 mb-2">需求内容</p>
            <pre class="whitespace-pre-wrap text-sm text-slate-700 leading-6 font-sans">{{ sourceRequirementText || '等待需求解析内容...' }}</pre>
          </div>
          <div class="rounded-xl border border-blue-100 bg-blue-50/40 p-4">
            <p class="text-sm font-semibold text-blue-700 mb-2">需求分析</p>
            <pre class="whitespace-pre-wrap text-sm text-slate-700 leading-6 font-sans">{{ analysisText || '等待分析结果...' }}</pre>
          </div>
          <div class="rounded-xl border border-indigo-100 bg-indigo-50/40 p-4">
            <p class="text-sm font-semibold text-indigo-700 mb-2">测试策略</p>
            <pre class="whitespace-pre-wrap text-sm text-slate-700 leading-6 font-sans">{{ designText || '等待策略输出...' }}</pre>
          </div>
        </div>

        <div v-if="selectedStage === 'generation'" class="space-y-4">
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

        <div v-if="selectedStage === 'review'" class="space-y-4">
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

          <div class="rounded-xl border border-slate-200 bg-slate-50/40 p-4">
            <div class="flex items-center justify-between mb-3">
              <p class="text-sm font-semibold text-slate-700">评审修改（可直接编辑）</p>
              <el-button
                size="small"
                type="primary"
                color="#4f46e5"
                :loading="savingReviewCases"
                @click="saveReviewCases"
                class="!rounded-lg"
              >
                保存评审结果
              </el-button>
            </div>

            <el-table :data="reviewEditableCases" border style="width: 100%">
              <el-table-column prop="id" label="编号" width="70" align="center" />
              <el-table-column label="模块" min-width="120">
                <template #default="scope">
                  <el-input v-model="scope.row.module" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="用例标题" min-width="220">
                <template #default="scope">
                  <el-input v-model="scope.row.title" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="步骤" min-width="240">
                <template #default="scope">
                  <el-input v-model="scope.row.steps" size="small" type="textarea" :rows="2" />
                </template>
              </el-table-column>
              <el-table-column label="预期结果" min-width="200">
                <template #default="scope">
                  <el-input v-model="scope.row.expected_result" size="small" type="textarea" :rows="2" />
                </template>
              </el-table-column>
              <el-table-column label="优先级" width="110" align="center">
                <template #default="scope">
                  <el-select v-model="scope.row.priority" size="small">
                    <el-option label="高" value="高" />
                    <el-option label="中" value="中" />
                    <el-option label="低" value="低" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="120" align="center">
                <template #default="scope">
                  <el-select v-model="scope.row.adoption_status" size="small">
                    <el-option label="采纳" value="accepted" />
                    <el-option label="不采纳" value="rejected" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" align="center">
                <template #default="scope">
                  <el-button link type="danger" @click="removeReviewCase(scope.$index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showFinalArtifacts" class="animate-fade-in-up">
      <el-tabs v-model="activeTab" class="results-tabs">
        <el-tab-pane label="📋 测试用例" name="cases">
          <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mt-4">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-800">
                测试用例
                <span class="ml-2 text-sm font-normal text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">共 {{ cases.length }} 条</span>
              </h3>
              <div class="flex gap-2">
                <el-button 
                  size="small" 
                  :type="viewMode === 'table' ? 'primary' : ''" 
                  @click="viewMode = 'table'" 
                  class="!rounded-lg"
                >
                  📊 表格视图
                </el-button>
                <el-button 
                  size="small" 
                  :type="viewMode === 'mindmap' ? 'primary' : ''" 
                  @click="viewMode = 'mindmap'" 
                  class="!rounded-lg"
                >
                  🗺️ 思维导图
                </el-button>
                <el-divider direction="vertical" />
                <el-button size="small" @click="exportExcel" :loading="exporting.excel" class="!rounded-lg">📊 导出 Excel</el-button>
                <el-button size="small" @click="exportXmind" :loading="exporting.xmind" class="!rounded-lg">🗺️ 导出 XMind</el-button>
                <el-button size="small" type="primary" @click="syncMs" :loading="exporting.ms" class="!rounded-lg">🔗 同步 MS</el-button>
              </div>
            </div>

            <!-- 表格视图 -->
            <div v-if="viewMode === 'table'">
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
                <el-table-column label="状态" width="100" align="center">
                  <template #default="scope">
                    <el-tag :type="scope.row.adoption_status === 'rejected' ? 'danger' : 'success'" effect="light" round size="small">
                      {{ scope.row.adoption_status === 'rejected' ? '不采纳' : '采纳' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 思维导图视图 -->
            <div v-else-if="viewMode === 'mindmap'" style="min-height: 600px;">
              <MindMap :data="mindMapData" />
            </div>
          </div>
        </el-tab-pane>


      </el-tabs>
    </div>

    <div v-if="isTaskFailed(task.status)" class="bg-white rounded-2xl border border-red-200 shadow-sm p-8 text-center">
      <div class="text-5xl mb-4">😞</div>
      <h3 class="text-xl font-bold text-red-600 mb-2">任务执行失败</h3>
      <p class="text-gray-500 text-sm mb-6">{{ task.error || '发生未知错误，请重试' }}</p>
      <el-button type="primary" color="#4f46e5" @click="router.push('/generate')" class="!rounded-xl">重新生成</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { updateTaskStatusInHistory } from '../utils/taskHistory'
import MindMap from '../components/MindMap.vue'

type PhaseKey = 'analysis' | 'generation' | 'review'

const route = useRoute()
const router = useRouter()
const taskId = route.params.id as string

const activeTab = ref('cases')
const viewMode = ref<'table' | 'mindmap'>('table')
const exporting = ref({ excel: false, xmind: false, ms: false })
const selectedStage = ref<PhaseKey>('analysis')
const reviewEditableCases = ref<any[]>([])
const savingReviewCases = ref(false)

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

function isTaskFailed(status?: string) {
  return ['analysis_failed', 'generation_failed', 'review_failed', 'failed'].includes(status || '')
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
    const resp = await axios.get(`/api/tasks/${taskId}`)
    if (resp.data?.data) {
      task.value = { ...task.value, ...resp.data.data }
      hydrateReviewEditableCases(true)
      syncExpandedStage()
      updateTaskStatusInHistory(taskId, task.value.status)
    }
  } catch {
    // snapshot only for initial hydration; ignore if not available yet
  }
}

function startSSE() {
  eventSource = new EventSource(`/api/tasks/${taskId}/events`)

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      task.value = { ...task.value, ...data }
      hydrateReviewEditableCases()
      syncExpandedStage()
      updateTaskStatusInHistory(taskId, task.value.status)

      if (data.status === 'completed' || isTaskFailed(data.status) || data.status === 'waiting_decision') {
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
const selectedStageData = computed(() => {
  return orderedStages.value.find((item) => item.key === selectedStage.value) ?? orderedStages.value[0]
})

const reachableStageIndex = computed(() => {
  if (task.value.status === 'completed' || task.value.status === 'waiting_decision') return 3

  const phases = task.value.phases ?? {}
  if (phases.review?.status && phases.review.status !== 'pending') return 3
  if (phases.generation?.status && phases.generation.status !== 'pending') return 2
  return 1
})
const timelineProgressWidth = computed(() => {
  const done = orderedStages.value.filter((s) => s.phase.status === 'completed').length
  const running = orderedStages.value.some((s) => s.phase.status === 'running') ? 0.5 : 0
  return `${Math.round(((done + running) / orderedStages.value.length) * 100)}%`
})

const showFinalArtifacts = computed(() => {
  const phases = task.value.phases ?? {}
  return phases.generation?.status === 'completed' && phases.review?.status === 'completed'
})

const cases = computed<any[]>(() => {
  const data = task.value.phases?.generation?.data
  let result: any[] = []
  if (data && typeof data === 'object') {
    result = data.cases ?? []
  }
  return result.map((item: any) => ({
    ...item,
    adoption_status: item?.adoption_status === 'rejected' ? 'rejected' : 'accepted',
  }))
})

const sourceRequirementText = computed(() => {
  const data = task.value.phases?.analysis?.data
  if (typeof data === 'string') return data
  if (data && typeof data === 'object') return data.source_text ?? ''
  return ''
})

const analysisText = computed(() => {
  const data = task.value.phases?.analysis?.data
  if (typeof data === 'string') return data
  if (data && typeof data === 'object') return data.analysis ?? ''
  return ''
})

const designText = computed(() => {
  const data = task.value.phases?.analysis?.data
  if (data && typeof data === 'object') return data.design ?? ''
  return ''
})

const analysisSubSteps = computed<any[]>(() => {
  const data = task.value.phases?.analysis?.data
  if (!data || typeof data !== 'object' || !Array.isArray(data.sub_steps)) return []
  return data.sub_steps
})

const review = computed(() => {
  const data = task.value.phases?.review?.data
  if (data && typeof data === 'object') return data.review ?? {}
  return {}
})

function normalizeReviewCase(item: any, fallbackId: number) {
  return {
    id: item?.id ?? fallbackId,
    module: item?.module ?? '',
    title: item?.title ?? '',
    precondition: item?.precondition ?? '',
    steps: item?.steps ?? '',
    expected_result: item?.expected_result ?? '',
    priority: item?.priority ?? '中',
    adoption_status: item?.adoption_status === 'rejected' ? 'rejected' : 'accepted',
  }
}

function hydrateReviewEditableCases(force = false) {
  if (!force && reviewEditableCases.value.length) return
  const reviewed = review.value?.reviewed_cases
  if (Array.isArray(reviewed) && reviewed.length) {
    reviewEditableCases.value = reviewed.map((item: any, idx: number) => normalizeReviewCase(item, idx + 1))
    return
  }
  reviewEditableCases.value = cases.value.map((item: any, idx: number) => normalizeReviewCase(item, idx + 1))
}

const bannerClass = computed(() => {
  switch (task.value.status) {
    case 'queued': return 'bg-gradient-to-r from-slate-500 to-slate-600 text-white'
    case 'running': return 'bg-gradient-to-r from-blue-600 to-blue-500 text-white'
    case 'waiting_decision': return 'bg-gradient-to-r from-amber-500 to-orange-500 text-white'
    case 'completed': return 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white'
    case 'analysis_failed': return 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
    case 'generation_failed': return 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
    case 'review_failed': return 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
    case 'failed': return 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
    default: return 'bg-gray-100 text-gray-600'
  }
})

const bannerIcon = computed(() => {
  switch (task.value.status) {
    case 'queued': return '🕒'
    case 'running': return '🤖'
    case 'waiting_decision': return '📩'
    case 'completed': return '🎉'
    case 'analysis_failed': return '❌'
    case 'generation_failed': return '❌'
    case 'review_failed': return '❌'
    case 'failed': return '❌'
    default: return '⏳'
  }
})

const bannerTitle = computed(() => {
  switch (task.value.status) {
    case 'uploaded': return '文件已上传，待启动分析'
    case 'queued': return '任务排队中，准备执行...'
    case 'pending': return '任务已创建，等待执行...'
    case 'running': return 'AI 正在生成测试用例...'
    case 'waiting_decision': return '已发送钉钉通知，等待采纳确认'
    case 'completed': return '全部完成！测试用例已生成'
    case 'analysis_failed': return '需求分析异常'
    case 'generation_failed': return '用例编写异常'
    case 'review_failed': return '用例评审异常'
    case 'failed': return '任务执行失败'
    default: return ''
  }
})

const bannerSubtitle = computed(() => {
  const running = Object.values(task.value.phases ?? {}).find((p: any) => p.status === 'running') as any
  if (running) return `当前正在执行：${running.label}`
  if (task.value.status === 'waiting_decision') return '请在钉钉中确认是否采纳'
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
  if (current) {
    selectedStage.value = current.key
    return
  }

  const failed = orderedStages.value.find((s) => s.phase.status === 'failed')
  if (failed) {
    selectedStage.value = failed.key
    return
  }

  if (task.value.status === 'completed' || task.value.status === 'waiting_decision') {
    selectedStage.value = 'review'
    return
  }
  selectedStage.value = 'analysis'
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

function stageContainerClass(stage: any) {
  return stage.phase.status === 'failed'
    ? 'border-red-200'
    : stage.phase.status === 'completed'
      ? 'border-emerald-200'
      : 'border-slate-200'
}

function stageProgressColorClass(stage: any) {
  if (stage.phase.status === 'failed') return 'bg-red-500'
  if (stage.index === 1) return 'bg-blue-500'
  if (stage.index === 2) return 'bg-purple-500'
  return 'bg-emerald-500'
}

function stageDotClass(stage: any) {
  if (stage.phase.status === 'failed') return 'bg-red-500 border-red-500 text-white'
  if (stage.phase.status === 'completed') return 'bg-emerald-500 border-emerald-500 text-white'
  if (stage.phase.status === 'running') return 'bg-indigo-500 border-indigo-500 text-white'
  return selectedStage.value === stage.key
    ? 'bg-indigo-50 border-indigo-500 text-indigo-600'
    : 'bg-white border-slate-300 text-slate-500'
}

function stageTextClass(status: string) {
  if (status === 'failed') return 'text-red-500'
  if (status === 'completed') return 'text-emerald-600'
  if (status === 'running') return 'text-indigo-600'
  return 'text-slate-400'
}

function subStepTagType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'running') return 'primary'
  if (status === 'failed') return 'danger'
  return 'info'
}

function canSelectStage(stage: any) {
  return stage.index <= reachableStageIndex.value
}

function selectStage(stage: any) {
  if (!canSelectStage(stage)) return
  selectedStage.value = stage.key
}

function removeReviewCase(index: number) {
  reviewEditableCases.value.splice(index, 1)
}

async function saveReviewCases() {
  if (!reviewEditableCases.value.length) {
    ElMessage.warning('请至少保留一条评审用例')
    return
  }
  savingReviewCases.value = true
  try {
    const payload = {
      cases: reviewEditableCases.value.map((item, idx) => ({
        ...normalizeReviewCase(item, idx + 1),
      })),
    }
    const resp = await axios.put(`/api/tasks/${taskId}/review-cases`, payload)
    const data = resp.data?.data || {}
    if (data.task) {
      task.value = { ...task.value, ...data.task }
    } else {
      await fetchTaskSnapshot()
    }
    hydrateReviewEditableCases(true)
    ElMessage.success(`评审已保存：采纳 ${data.adopted_count ?? 0} 条，不采纳 ${data.rejected_count ?? 0} 条`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.response?.data?.detail || '保存评审失败')
  } finally {
    savingReviewCases.value = false
  }
}

async function exportExcel() {
  if (!cases.value.length) return
  exporting.value.excel = true
  try {
    const resp = await axios.post('/api/tasks/exports/excel', { cases: cases.value }, { responseType: 'blob' })
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
      '/api/tasks/exports/xmind',
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
    const resp = await axios.post('/api/tasks/sync/ms', { cases: cases.value })
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

// 从后端接口获取思维导图数据
const mindMapData = ref<any>(null)

async function fetchMindMapData() {
  try {
    const resp = await axios.get(`/api/tasks/${taskId}/mindmap-data`)
    if (resp.data?.data?.root) {
      mindMapData.value = resp.data.data.root
      console.log('[思维导图] 数据加载成功')
    }
  } catch (error) {
    console.error('[思维导图] 获取数据失败:', error)
  }
}

// 在任务完成后加载思维导图数据
watch(
  () => task.value.status,
  (newStatus) => {
    if (['completed', 'waiting_decision'].includes(newStatus)) {
      setTimeout(() => fetchMindMapData(), 500)
    }
  },
  { immediate: false }
)

// 监听 viewMode 变化，当切换到思维导图时加载数据
watch(
  () => viewMode.value,
  (newMode) => {
    if (newMode === 'mindmap' && !mindMapData.value) {
      fetchMindMapData()
    }
  }
)
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
