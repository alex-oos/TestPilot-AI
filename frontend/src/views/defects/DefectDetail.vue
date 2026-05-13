<template>
  <div class="space-y-6" v-loading="pageLoading">
    <div class="flex items-center gap-3">
      <el-button circle @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <div class="flex-1 min-w-0">
        <h1 class="text-2xl font-bold text-gray-900 truncate">{{ defect.title || '缺陷详情' }}</h1>
        <p class="text-gray-400 text-sm mt-0.5">ID: {{ defect.id }}</p>
      </div>
      <el-button type="primary" color="#4f46e5" class="!rounded-xl" @click="router.push(`/defects/${defect.id}/edit`)">
        编辑
      </el-button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 左侧：缺陷详情 -->
      <div class="lg:col-span-2 space-y-4">
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">缺陷信息</h2>

          <template v-if="!editMode">
            <div class="space-y-5">
              <DetailSection title="描述" :content="defect.description" />
              <DetailSection title="重现步骤" :content="defect.steps" />
              <DetailSection title="期望结果" :content="defect.expected" />
              <DetailSection title="实际结果" :content="defect.actual" />
              <DetailSection title="环境信息" :content="defect.environment" />
            </div>
          </template>

          <template v-else>
            <el-form label-width="90px" label-position="right">
              <el-form-item label="标题">
                <el-input v-model="defect.title" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="defect.description" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="重现步骤">
                <el-input v-model="defect.steps" type="textarea" :rows="3" />
              </el-form-item>
              <el-form-item label="期望结果">
                <el-input v-model="defect.expected" type="textarea" :rows="2" />
              </el-form-item>
              <el-form-item label="实际结果">
                <el-input v-model="defect.actual" type="textarea" :rows="2" />
              </el-form-item>
              <el-form-item label="环境信息">
                <el-input v-model="defect.environment" />
              </el-form-item>
              <div class="flex justify-end">
                <el-button type="primary" color="#4f46e5" :loading="saving" @click="saveDefect">保存</el-button>
              </div>
            </el-form>
          </template>
        </div>

        <!-- 评论区 -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h2 class="text-lg font-semibold text-gray-800 mb-4">评论 ({{ comments.length }})</h2>

          <div class="space-y-4 mb-5">
            <div v-if="comments.length === 0" class="text-gray-400 text-sm text-center py-6">暂无评论</div>
            <div
              v-for="c in comments"
              :key="c.id"
              class="rounded-xl border border-gray-100 p-4 hover:shadow-sm transition-shadow"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <div class="w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold">
                    {{ (c.author || '?')[0] }}
                  </div>
                  <span class="text-sm font-medium text-gray-800">{{ c.author }}</span>
                </div>
                <span class="text-xs text-gray-400">{{ formatTime(c.created_at) }}</span>
              </div>
              <p class="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{{ c.content }}</p>
            </div>
          </div>

          <div class="border-t border-gray-100 pt-4">
            <el-input
              v-model="newComment"
              type="textarea"
              :rows="3"
              placeholder="输入评论内容…"
              resize="none"
            />
            <div class="flex justify-end mt-3">
              <el-button type="primary" color="#4f46e5" :loading="commentSubmitting" :disabled="!newComment.trim()" @click="submitComment">
                发表评论
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：元信息 + 历史 -->
      <div class="space-y-4">
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="text-base font-semibold text-gray-800 mb-4">元信息</h3>
          <div class="space-y-3">
            <MetaRow label="状态">
              <el-tag :type="statusTagType(defect.status)" effect="light" round size="small">
                {{ statusLabel(defect.status) }}
              </el-tag>
            </MetaRow>
            <MetaRow label="严重度">
              <el-tag :color="severityColor(defect.severity)" effect="dark" size="small" class="!border-0 !text-white" round>
                {{ severityLabel(defect.severity) }}
              </el-tag>
            </MetaRow>
            <MetaRow label="优先级">{{ priorityLabel(defect.priority) }}</MetaRow>
            <MetaRow label="项目">{{ defect.project || '-' }}</MetaRow>
            <MetaRow label="模块">{{ defect.module || '-' }}</MetaRow>
            <MetaRow label="指派人">{{ defect.assignee || '-' }}</MetaRow>
            <MetaRow label="创建人">{{ defect.creator || '-' }}</MetaRow>
            <MetaRow label="创建时间">{{ formatTime(defect.created_at) }}</MetaRow>
            <MetaRow label="更新时间">{{ formatTime(defect.updated_at) }}</MetaRow>
          </div>

          <div v-if="editMode" class="border-t border-gray-100 mt-4 pt-4 space-y-3">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">状态</label>
              <el-select v-model="defect.status" class="w-full" size="small">
                <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">严重度</label>
              <el-select v-model="defect.severity" class="w-full" size="small">
                <el-option label="致命" value="critical" />
                <el-option label="严重" value="major" />
                <el-option label="一般" value="medium" />
                <el-option label="轻微" value="minor" />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">优先级</label>
              <el-select v-model="defect.priority" class="w-full" size="small">
                <el-option label="紧急" value="urgent" />
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">指派人</label>
              <el-input v-model="defect.assignee" size="small" />
            </div>
          </div>
        </div>

        <!-- 变更历史 -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="text-base font-semibold text-gray-800 mb-4">变更历史</h3>
          <div v-if="history.length === 0" class="text-gray-400 text-sm text-center py-4">暂无变更记录</div>
          <div v-else class="relative pl-5">
            <div class="absolute left-[7px] top-2 bottom-2 w-px bg-gray-200" />
            <div v-for="h in history" :key="h.id" class="relative pb-5 last:pb-0">
              <div class="absolute -left-5 top-1 w-3.5 h-3.5 rounded-full border-2 border-indigo-400 bg-white" />
              <div class="text-sm text-gray-700">{{ h.description }}</div>
              <div class="text-xs text-gray-400 mt-0.5">{{ h.operator }} · {{ formatTime(h.created_at) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

const DetailSection = defineComponent({
  props: { title: String, content: String },
  setup(props) {
    return () => h('div', [
      h('h4', { class: 'text-sm font-medium text-gray-500 mb-1' }, props.title),
      h('p', {
        class: 'text-sm text-gray-800 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded-lg p-3',
      }, props.content || '暂无内容'),
    ])
  },
})

const MetaRow = defineComponent({
  props: { label: String },
  setup(props, { slots }) {
    return () => h('div', { class: 'flex items-center justify-between' }, [
      h('span', { class: 'text-sm text-gray-500' }, props.label),
      h('span', { class: 'text-sm text-gray-800' }, slots.default?.()),
    ])
  },
})

interface DefectData {
  id: number
  title: string
  severity: string
  priority: string
  status: string
  project: string
  module: string
  assignee: string
  creator: string
  description: string
  steps: string
  expected: string
  actual: string
  environment: string
  created_at: string
  updated_at: string
}

interface Comment {
  id: number
  author: string
  content: string
  created_at: string
}

interface HistoryItem {
  id: number
  description: string
  operator: string
  created_at: string
}

const route = useRoute()
const router = useRouter()
const defectId = route.params.id as string

const pageLoading = ref(true)
const saving = ref(false)
const commentSubmitting = ref(false)
const editMode = ref(false)
const newComment = ref('')

const defect = reactive<Partial<DefectData>>({})
const comments = ref<Comment[]>([])
const history = ref<HistoryItem[]>([])

const statusOptions = [
  { label: '待处理', value: 'open' },
  { label: '已指派', value: 'assigned' },
  { label: '修复中', value: 'fixing' },
  { label: '已解决', value: 'resolved' },
  { label: '已验证', value: 'verified' },
  { label: '已关闭', value: 'closed' },
]

const severityColor = (s?: string) => {
  const map: Record<string, string> = { critical: '#ef4444', major: '#f97316', medium: '#3b82f6', minor: '#9ca3af' }
  return map[s || ''] || '#9ca3af'
}
const severityLabel = (s?: string) => {
  const map: Record<string, string> = { critical: '致命', major: '严重', medium: '一般', minor: '轻微' }
  return map[s || ''] || s || ''
}
const priorityLabel = (p?: string) => {
  const map: Record<string, string> = { urgent: '🔴 紧急', high: '🟠 高', medium: '🔵 中', low: '⚪ 低' }
  return map[p || ''] || p || ''
}
const statusTagType = (s?: string) => {
  const map: Record<string, string> = { open: 'danger', assigned: '', fixing: 'warning', resolved: 'success', verified: 'info', closed: 'info' }
  return (map[s || ''] ?? '') as any
}
const statusLabel = (s?: string) => {
  const map: Record<string, string> = { open: '待处理', assigned: '已指派', fixing: '修复中', resolved: '已解决', verified: '已验证', closed: '已关闭' }
  return map[s || ''] || s || ''
}

function formatTime(t?: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function fetchDefect() {
  try {
    const { data } = await request.get(`/defects/${defectId}`)
    const payload = data?.data ?? data
    Object.assign(defect, payload)
  } catch (e: any) {
    ElMessage.error(e.message || '加载缺陷详情失败')
  }
}

async function fetchComments() {
  try {
    const { data } = await request.get(`/defects/${defectId}/comments`)
    const payload = data?.data ?? data
    comments.value = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
  } catch {
    comments.value = []
  }
}

async function fetchHistory() {
  try {
    const { data } = await request.get(`/defects/${defectId}/history`)
    const payload = data?.data ?? data
    history.value = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
  } catch {
    history.value = []
  }
}

async function saveDefect() {
  saving.value = true
  try {
    await request.put(`/defects/${defectId}`, defect)
    ElMessage.success('保存成功')
    editMode.value = false
    fetchHistory()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function submitComment() {
  if (!newComment.value.trim()) return
  commentSubmitting.value = true
  try {
    await request.post(`/defects/${defectId}/comments`, { content: newComment.value })
    ElMessage.success('评论已发表')
    newComment.value = ''
    fetchComments()
  } catch (e: any) {
    ElMessage.error(e.message || '评论提交失败')
  } finally {
    commentSubmitting.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchDefect(), fetchComments(), fetchHistory()])
  pageLoading.value = false
})
</script>
