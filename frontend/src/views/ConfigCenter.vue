<template>
  <div class="space-y-6" v-loading="loading">

    <section v-if="activeSection === 'ai'" class="config-page">
      <div class="section-header text-center">
        <h1 class="section-title">🤖 AI用例生成模型配置</h1>
        <p class="section-subtitle">配置用于测试用例生成和评审的AI模型</p>
      </div>

      <div class="flex items-center justify-between mt-8 mb-4">
        <h2 class="text-3xl font-semibold text-slate-800">模型配置列表</h2>
        <el-button type="success" @click="openCreateAIDialog">添加配置</el-button>
      </div>

      <div v-if="!aiConfigList.length" class="empty-box">
        暂无模型配置，点击右上角“添加配置”开始配置。
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div v-for="item in aiConfigList" :key="item.id" class="config-card">
          <div class="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 class="text-3xl font-bold text-slate-800">{{ item.name }}</h3>
              <div class="flex items-center gap-2 mt-2 flex-wrap">
                <el-tag size="small" type="info">{{ modelTypeLabel(item.model_type) }}</el-tag>
                <el-tag size="small" type="warning">{{ roleLabel(item.role) }}</el-tag>
                <el-tag size="small" :type="item.enabled ? 'success' : 'danger'">
                  {{ item.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <el-button size="small" type="primary" @click="testConnection(item)">测试连接</el-button>
              <el-button size="small" type="warning" @click="openEditAIDialog(item)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeAIConfig(item)">删除</el-button>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-700">
            <div>
              <p class="meta-label">API Base URL:</p>
              <p class="break-all">{{ item.api_base_url }}</p>
            </div>
            <div>
              <p class="meta-label">模型名称:</p>
              <p>{{ item.model_name }}</p>
            </div>
            <div>
              <p class="meta-label">最大Token数:</p>
              <p>{{ item.max_tokens }}</p>
            </div>
            <div>
              <p class="meta-label">温度参数:</p>
              <p>{{ item.temperature }}</p>
            </div>
            <div>
              <p class="meta-label">Top P参数:</p>
              <p>{{ item.top_p }}</p>
            </div>
            <div>
              <p class="meta-label">创建时间:</p>
              <p>{{ item.created_at || '-' }}</p>
            </div>
          </div>
        </div>
      </div>

      <el-dialog
        v-model="aiDialogVisible"
        :title="editingAIId ? '编辑AI模型配置' : '添加AI模型配置'"
        width="700px"
        destroy-on-close
      >
        <el-form ref="aiDialogFormRef" :model="aiDialogForm" :rules="aiDialogRules" label-position="top">
          <el-form-item label="配置名称" prop="name">
            <el-input v-model="aiDialogForm.name" placeholder="例如：DeepSeek测试用例编写" />
          </el-form-item>

          <el-form-item label="模型类型" prop="model_type">
            <el-select v-model="aiDialogForm.model_type" placeholder="请选择模型类型" class="w-full" @change="onModelTypeChange">
              <el-option label="LM Studio" value="lm_studio" />
              <el-option label="OpenAI 兼容" value="openai_compatible" />
              <el-option label="通义千问" value="qwen" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>

          <el-form-item label="角色" prop="role">
            <el-select v-model="aiDialogForm.role" placeholder="请选择角色" class="w-full">
              <el-option label="需求分析专家" value="analysis" />
              <el-option label="测试用例编写专家" value="generation" />
              <el-option label="测试用例评审专家" value="review" />
            </el-select>
          </el-form-item>

          <el-form-item label="API Key" prop="api_key">
            <el-input v-model="aiDialogForm.api_key" show-password placeholder="输入您的API Key（本地LM Studio可留空）" />
          </el-form-item>

          <el-form-item label="API Base URL" prop="api_base_url">
            <el-input v-model="aiDialogForm.api_base_url" placeholder="例如：http://127.0.0.1:1234/v1" />
          </el-form-item>

          <el-form-item label="模型名称" prop="model_name">
            <el-input v-model="aiDialogForm.model_name" placeholder="例如：qwen/qwen3.5-9b" />
          </el-form-item>

          <div class="grid grid-cols-3 gap-3">
            <el-form-item label="最大Token数" prop="max_tokens">
              <el-input-number v-model="aiDialogForm.max_tokens" :min="128" :max="32768" :step="128" class="!w-full" />
            </el-form-item>
            <el-form-item label="温度参数" prop="temperature">
              <el-input-number v-model="aiDialogForm.temperature" :min="0" :max="2" :step="0.1" class="!w-full" />
            </el-form-item>
            <el-form-item label="Top P参数" prop="top_p">
              <el-input-number v-model="aiDialogForm.top_p" :min="0" :max="1" :step="0.1" class="!w-full" />
            </el-form-item>
          </div>

          <el-form-item>
            <el-checkbox v-model="aiDialogForm.enabled">启用此配置</el-checkbox>
          </el-form-item>
        </el-form>

        <template #footer>
          <div class="flex justify-end gap-3">
            <el-button @click="aiDialogVisible = false">取消</el-button>
            <el-button type="success" :loading="saving" @click="submitAIDialog">保存配置</el-button>
          </div>
        </template>
      </el-dialog>
    </section>

    <section v-if="activeSection === 'prompts'" class="config-page">
      <div class="section-header text-center">
        <h1 class="section-title">📝 提示词配置</h1>
        <p class="section-subtitle">配置用于测试用例编写和评审的AI提示词</p>
      </div>

      <div class="flex items-center justify-between mt-8 mb-4">
        <h2 class="text-3xl font-semibold text-slate-800">提示词配置列表</h2>
        <div class="flex items-center gap-3">
          <el-button color="#8b5cf6" @click="loadDefaultPrompts">📂 加载默认提示词</el-button>
          <el-button type="success" @click="openCreatePromptDialog">+ 添加配置</el-button>
        </div>
      </div>

      <div v-if="!promptConfigList.length" class="empty-box">
        暂无提示词配置，点击右上角“添加配置”开始配置。
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div v-for="item in promptConfigList" :key="item.id" class="config-card">
          <div class="flex items-start justify-between gap-3 mb-3">
            <div>
              <h3 class="text-3xl font-bold text-slate-800">{{ item.name }}</h3>
              <div class="flex items-center gap-2 mt-2 flex-wrap">
                <el-tag size="small" :type="promptTypeTagType(item.prompt_type)">{{ promptTypeLabel(item.prompt_type) }}</el-tag>
                <el-tag size="small" :type="item.enabled ? 'success' : 'danger'">{{ item.enabled ? '启用' : '禁用' }}</el-tag>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <el-button size="small" type="primary" @click="previewPrompt(item)">👁️ 预览</el-button>
              <el-button size="small" type="warning" @click="openEditPromptDialog(item)">✏️ 编辑</el-button>
              <el-button size="small" type="danger" @click="removePromptConfig(item)">🗑 删除</el-button>
            </div>
          </div>

          <p class="meta-label mb-2">提示词内容预览:</p>
          <div class="prompt-preview">
            {{ clippedPrompt(item.content) }}
          </div>

          <div class="grid grid-cols-2 gap-3 mt-4 text-sm text-slate-700">
            <div>
              <p class="meta-label">创建时间:</p>
              <p>{{ item.created_at || '-' }}</p>
            </div>
            <div>
              <p class="meta-label">更新时间:</p>
              <p>{{ item.updated_at || '-' }}</p>
            </div>
            <div>
              <p class="meta-label">创建者:</p>
              <p>{{ item.creator || 'admin' }}</p>
            </div>
          </div>
        </div>
      </div>

      <el-dialog
        v-model="promptDialogVisible"
        :title="editingPromptId ? '编辑配置' : '+ 添加配置'"
        width="760px"
        destroy-on-close
      >
        <el-form ref="promptDialogFormRef" :model="promptDialogForm" :rules="promptDialogRules" label-position="top">
          <el-form-item label="配置名称" prop="name">
            <el-input v-model="promptDialogForm.name" placeholder="例如：测试用例编写提示词 v1.0" />
          </el-form-item>

          <el-form-item label="提示词类型" prop="prompt_type">
            <el-select v-model="promptDialogForm.prompt_type" placeholder="请选择提示词类型" class="w-full">
              <el-option label="需求分析提示词" value="analysis" />
              <el-option label="测试用例编写提示词" value="generation" />
              <el-option label="测试用例评审提示词" value="review" />
            </el-select>
          </el-form-item>

          <el-form-item label="提示词内容" prop="content">
            <el-input
              v-model="promptDialogForm.content"
              type="textarea"
              :rows="12"
              placeholder="请输入提示词内容，支持使用变量占位符..."
            />
            <div class="w-full text-right text-sm text-slate-400 mt-1">字符数：{{ promptDialogForm.content.length }}</div>
          </el-form-item>

          <div class="tips-box">
            <p class="font-semibold mb-2">提示词编写建议:</p>
            <ul class="list-disc pl-5 space-y-1 text-slate-700">
              <li>使用清晰上下文，明确输入和输出</li>
              <li>清晰描述AI的角色和任务</li>
              <li>指定输出格式和结构</li>
              <li>覆盖异常和边界情况要求</li>
            </ul>
          </div>

          <el-form-item class="mt-4">
            <el-checkbox v-model="promptDialogForm.enabled">启用此配置</el-checkbox>
            <p class="text-sm text-slate-500 mt-1">启用后，同类型的其他配置将被禁用</p>
          </el-form-item>
        </el-form>

        <template #footer>
          <div class="flex justify-end gap-3">
            <el-button @click="promptDialogVisible = false">取消</el-button>
            <el-button type="success" :loading="saving" @click="submitPromptDialog">💾 保存配置</el-button>
          </div>
        </template>
      </el-dialog>

      <el-dialog v-model="previewVisible" title="提示词预览" width="760px">
        <div class="preview-dialog-box">{{ previewContent }}</div>
        <template #footer>
          <el-button type="primary" @click="previewVisible = false">关闭</el-button>
        </template>
      </el-dialog>
    </section>

    <section v-if="activeSection === 'behavior'" class="config-page">
      <div class="section-header text-center">
        <h1 class="section-title">⚙️ 生成行为配置</h1>
        <p class="section-subtitle">配置测试用例生成的默认行为和自动化流程</p>
      </div>

      <div class="flex items-center justify-between mt-8 mb-4">
        <h2 class="text-3xl font-semibold text-slate-800">配置列表</h2>
        <el-button type="success" @click="openCreateBehaviorDialog">+ 添加配置</el-button>
      </div>

      <div v-if="!behaviorConfigList.length" class="empty-box">
        暂无生成行为配置，点击右上角“添加配置”开始配置。
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div v-for="item in behaviorConfigList" :key="item.id" class="config-card">
          <div class="flex items-start justify-between gap-3 mb-4">
            <div>
              <h3 class="text-3xl font-bold text-slate-800">{{ item.name }}</h3>
              <div class="flex items-center gap-2 mt-2">
                <el-tag size="small" :type="item.enabled ? 'success' : 'danger'">
                  {{ item.enabled ? '✅ 启用中' : '已禁用' }}
                </el-tag>
                <el-tag size="small" type="info">{{ outputModeLabel(item.output_mode) }}</el-tag>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <el-button size="small" type="warning" @click="openEditBehaviorDialog(item)">✏️ 编辑</el-button>
              <el-button size="small" type="danger" @click="removeBehaviorConfig(item)">🗑 删除</el-button>
            </div>
          </div>

          <div class="space-y-3">
            <div class="prompt-preview">
              <p class="font-semibold mb-2">📤 输出模式</p>
              <div class="flex justify-between text-slate-700">
                <span>默认模式:</span>
                <span class="font-semibold">{{ outputModeLabel(item.output_mode) }}</span>
              </div>
            </div>
            <div class="prompt-preview">
              <p class="font-semibold mb-2">🤖 自动化流程</p>
              <div class="flex justify-between text-slate-700">
                <span>AI评审和改进:</span>
                <span class="font-semibold">{{ item.enable_ai_review ? '✅ 启用中' : '未启用' }}</span>
              </div>
            </div>
            <div class="prompt-preview">
              <p class="font-semibold mb-2">⏱ 超时设置</p>
              <div class="flex justify-between text-slate-700">
                <span>评审和改进超时:</span>
                <span class="font-semibold">{{ item.review_timeout_seconds }} 秒</span>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 mt-4 text-sm text-slate-700">
            <div>
              <p class="meta-label">创建时间:</p>
              <p>{{ item.created_at || '-' }}</p>
            </div>
            <div>
              <p class="meta-label">更新时间:</p>
              <p>{{ item.updated_at || '-' }}</p>
            </div>
          </div>
        </div>
      </div>

      <el-dialog
        v-model="behaviorDialogVisible"
        :title="editingBehaviorId ? '编辑生成行为配置' : '添加生成行为配置'"
        width="760px"
        destroy-on-close
      >
        <el-form ref="behaviorDialogFormRef" :model="behaviorDialogForm" :rules="behaviorDialogRules" label-position="top">
          <div class="tips-box">
            <p class="font-semibold mb-3">📋 基本信息</p>
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="behaviorDialogForm.name" placeholder="默认生成配置" />
            </el-form-item>
            <el-form-item>
              <el-checkbox v-model="behaviorDialogForm.enabled">启用此配置</el-checkbox>
            </el-form-item>
          </div>

          <div class="tips-box mt-4">
            <p class="font-semibold mb-3">📤 输出模式设置</p>
            <el-form-item label="默认输出模式" prop="output_mode">
              <el-select v-model="behaviorDialogForm.output_mode" class="w-full">
                <el-option label="⚡ 实时流式输出" value="stream" />
                <el-option label="📦 完整输出" value="full" />
              </el-select>
            </el-form-item>
          </div>

          <div class="tips-box mt-4">
            <p class="font-semibold mb-3">🤖 自动化流程配置</p>
            <el-checkbox v-model="behaviorDialogForm.enable_ai_review">启用AI评审和改进</el-checkbox>
          </div>

          <div class="tips-box mt-4">
            <p class="font-semibold mb-3">⏱ 超时设置</p>
            <el-form-item label="评审和改进超时时间（秒）">
              <el-input-number
                v-model="behaviorDialogForm.review_timeout_seconds"
                :min="60"
                :max="3600"
                :step="60"
                class="!w-full"
              />
            </el-form-item>
          </div>
        </el-form>

        <template #footer>
          <div class="flex justify-end gap-3">
            <el-button @click="behaviorDialogVisible = false">取消</el-button>
            <el-button type="success" :loading="saving" @click="submitBehaviorDialog">💾 保存配置</el-button>
          </div>
        </template>
      </el-dialog>
    </section>

    <section v-if="activeSection === 'notifications'" class="config-page">
      <div class="notification-header">
        <h1 class="text-4xl font-bold text-white">⚙️ UI自动化通知配置</h1>
        <p class="text-white/80 mt-2">配置飞书、企微、钉钉Webhook机器人地址</p>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <el-tabs v-model="activeNotifyTab" class="px-4">
          <el-tab-pane label="飞书机器人" name="feishu" />
          <el-tab-pane label="企微机器人" name="wecom" />
          <el-tab-pane label="钉钉机器人" name="dingtalk" />
        </el-tabs>

        <div class="p-5 border-t border-slate-200 space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
            <el-form-item label="机器人名称">
              <el-input v-model="currentNotifyConfig.name" :placeholder="`请输入${notifyTabLabel(activeNotifyTab)}名称`" />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="currentNotifyConfig.enabled" />
            </el-form-item>
          </div>

          <el-form-item label="Webhook URL">
            <el-input v-model="currentNotifyConfig.webhook" placeholder="请输入Webhook URL" />
          </el-form-item>

          <el-form-item label="签名 Secret（可选）">
            <el-input v-model="currentNotifyConfig.secret" placeholder="请输入 Secret" />
          </el-form-item>

          <el-form-item label="业务类型">
            <el-checkbox-group v-model="currentNotifyConfig.business_types">
              <el-checkbox label="ui_auto">UI自动化测试</el-checkbox>
              <el-checkbox label="api">接口测试</el-checkbox>
            </el-checkbox-group>
          </el-form-item>

          <div class="pt-4 border-t border-slate-200 flex justify-end">
            <el-button type="primary" :loading="saving" @click="saveNotificationChannel(activeNotifyTab)">
              保存{{ notifyTabLabel(activeNotifyTab) }}配置
            </el-button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import axios from 'axios'

interface AIModelConfig {
  id: string
  name: string
  model_type: string
  role: string
  api_key: string
  api_base_url: string
  model_name: string
  max_tokens: number
  temperature: number
  top_p: number
  enabled: boolean
  created_at: string
}

interface PromptConfigItem {
  id: string
  name: string
  prompt_type: string
  content: string
  enabled: boolean
  created_at: string
  updated_at: string
  creator: string
}

interface GenerationBehaviorConfigItem {
  id: string
  name: string
  output_mode: string
  enable_ai_review: boolean
  review_timeout_seconds: number
  enabled: boolean
  created_at: string
  updated_at: string
}

const route = useRoute()
const loading = ref(false)
const saving = ref(false)

const aiDialogVisible = ref(false)
const editingAIId = ref('')
const aiDialogFormRef = ref<FormInstance>()
const aiConfigList = ref<AIModelConfig[]>([])

const promptDialogVisible = ref(false)
const editingPromptId = ref('')
const promptDialogFormRef = ref<FormInstance>()
const promptConfigList = ref<PromptConfigItem[]>([])
const previewVisible = ref(false)
const previewContent = ref('')
const activeNotifyTab = ref<'feishu' | 'wecom' | 'dingtalk'>('feishu')
const behaviorDialogVisible = ref(false)
const editingBehaviorId = ref('')
const behaviorDialogFormRef = ref<FormInstance>()
const behaviorConfigList = ref<GenerationBehaviorConfigItem[]>([])

const activeSection = computed<'ai' | 'prompts' | 'notifications' | 'behavior'>(() => {
  if (route.path.endsWith('/prompts')) return 'prompts'
  if (route.path.endsWith('/notifications')) return 'notifications'
  if (route.path.endsWith('/behavior')) return 'behavior'
  return 'ai'
})

const currentNotifyConfig = computed(() => {
  return form.notifications[activeNotifyTab.value]
})

const form = reactive({
  ai_models: {
    analysis: '',
    generation: '',
    review: '',
  },
  prompts: {
    analysis: '',
    generation: '',
    review: '',
  },
  notifications: {
    feishu: { name: '', enabled: false, webhook: '', secret: '', business_types: ['ui_auto', 'api'] as string[] },
    dingtalk: { name: '', enabled: false, webhook: '', secret: '', business_types: ['ui_auto', 'api'] as string[] },
    wecom: { name: '', enabled: false, webhook: '', secret: '', business_types: ['ui_auto', 'api'] as string[] },
  },
})

const aiDialogForm = reactive<AIModelConfig>({
  id: '',
  name: '',
  model_type: 'lm_studio',
  role: 'generation',
  api_key: '',
  api_base_url: 'http://127.0.0.1:1234/v1',
  model_name: '',
  max_tokens: 4096,
  temperature: 0.7,
  top_p: 0.9,
  enabled: true,
  created_at: '',
})

const promptDialogForm = reactive<PromptConfigItem>({
  id: '',
  name: '',
  prompt_type: 'generation',
  content: '',
  enabled: true,
  created_at: '',
  updated_at: '',
  creator: 'admin',
})

const behaviorDialogForm = reactive<GenerationBehaviorConfigItem>({
  id: '',
  name: '默认生成配置',
  output_mode: 'stream',
  enable_ai_review: true,
  review_timeout_seconds: 1500,
  enabled: true,
  created_at: '',
  updated_at: '',
})

const aiDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  api_base_url: [{ required: true, message: '请输入 API Base URL', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

const promptDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  prompt_type: [{ required: true, message: '请选择提示词类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入提示词内容', trigger: 'blur' }],
}

const behaviorDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  output_mode: [{ required: true, message: '请选择输出模式', trigger: 'change' }],
}

onMounted(() => {
  fetchConfig()
})

function modelTypeLabel(type: string) {
  const labels: Record<string, string> = {
    lm_studio: 'LM Studio',
    openai_compatible: 'OpenAI兼容',
    qwen: '通义千问',
    other: '其他',
  }
  return labels[type] || type
}

function roleLabel(role: string) {
  const labels: Record<string, string> = {
    analysis: '需求分析专家',
    generation: '测试用例编写专家',
    review: '测试评审专家',
  }
  return labels[role] || role
}

function promptTypeLabel(type: string) {
  const labels: Record<string, string> = {
    analysis: '需求分析提示词',
    generation: '测试用例编写提示词',
    review: '测试用例评审提示词',
  }
  return labels[type] || type
}

function promptTypeTagType(type: string): 'success' | 'warning' | 'danger' {
  if (type === 'analysis') return 'warning'
  if (type === 'generation') return 'success'
  return 'danger'
}

function formatNow() {
  const now = new Date()
  const y = now.getFullYear()
  const m = `${now.getMonth() + 1}`.padStart(2, '0')
  const d = `${now.getDate()}`.padStart(2, '0')
  const hh = `${now.getHours()}`.padStart(2, '0')
  const mm = `${now.getMinutes()}`.padStart(2, '0')
  return `${y}/${m}/${d} ${hh}:${mm}`
}

function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function clippedPrompt(content: string) {
  if (!content) return '-'
  if (content.length <= 220) return content
  return `${content.slice(0, 220)}...`
}

function onModelTypeChange(value: string) {
  if (value === 'lm_studio') {
    aiDialogForm.api_base_url = 'http://127.0.0.1:1234/v1'
    if (!aiDialogForm.model_name) aiDialogForm.model_name = 'qwen/qwen3.5-9b'
    return
  }
  if (value === 'qwen') {
    aiDialogForm.api_base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    if (!aiDialogForm.model_name) aiDialogForm.model_name = 'qwen3-max'
    return
  }
  if (value === 'openai_compatible' && !aiDialogForm.api_base_url) {
    aiDialogForm.api_base_url = 'https://api.openai.com/v1'
  }
}

async function fetchConfig() {
  loading.value = true
  try {
    const resp = await axios.get('/api/config-center')
    applyConfig(resp.data?.data || {})
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
}

function applyConfig(data: any) {
  Object.assign(form.ai_models, data?.ai_models || {})
  Object.assign(form.prompts, data?.prompts || {})
  Object.assign(form.notifications.feishu, data?.notifications?.feishu || {})
  Object.assign(form.notifications.dingtalk, data?.notifications?.dingtalk || {})
  Object.assign(form.notifications.wecom, data?.notifications?.wecom || {})
  aiConfigList.value = Array.isArray(data?.ai_model_configs) ? data.ai_model_configs : []
  promptConfigList.value = Array.isArray(data?.prompt_configs) ? data.prompt_configs : []
  behaviorConfigList.value = Array.isArray(data?.generation_behavior_configs) ? data.generation_behavior_configs : []
}

function resetAIDialogForm() {
  Object.assign(aiDialogForm, {
    id: '',
    name: '',
    model_type: 'lm_studio',
    role: 'generation',
    api_key: '',
    api_base_url: 'http://127.0.0.1:1234/v1',
    model_name: '',
    max_tokens: 4096,
    temperature: 0.7,
    top_p: 0.9,
    enabled: true,
    created_at: '',
  })
}

function openCreateAIDialog() {
  editingAIId.value = ''
  resetAIDialogForm()
  aiDialogVisible.value = true
}

function openEditAIDialog(item: AIModelConfig) {
  editingAIId.value = item.id
  Object.assign(aiDialogForm, item)
  aiDialogVisible.value = true
}

function buildRoleModelMap(list: AIModelConfig[]) {
  const result = {
    analysis: form.ai_models.analysis,
    generation: form.ai_models.generation,
    review: form.ai_models.review,
  }
  for (const role of ['analysis', 'generation', 'review'] as const) {
    const enabled = list.find((x) => x.role === role && x.enabled)
    if (enabled) result[role] = enabled.model_name
  }
  return result
}

async function persistAIConfigList(nextList: AIModelConfig[]) {
  const payload = {
    ai_model_configs: nextList,
    ai_models: buildRoleModelMap(nextList),
  }
  saving.value = true
  try {
    const resp = await axios.put('/api/config-center', payload)
    applyConfig(resp.data?.data || {})
    ElMessage.success('AI 配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function submitAIDialog() {
  if (!aiDialogFormRef.value) return
  const valid = await aiDialogFormRef.value.validate().catch(() => false)
  if (!valid) return

  const record: AIModelConfig = {
    ...aiDialogForm,
    id: editingAIId.value || newId(),
    created_at: aiDialogForm.created_at || formatNow(),
  }

  const nextList = [...aiConfigList.value]
  const idx = nextList.findIndex((x) => x.id === record.id)
  if (idx >= 0) {
    nextList[idx] = record
  } else {
    nextList.unshift(record)
  }

  await persistAIConfigList(nextList)
  aiDialogVisible.value = false
}

async function removeAIConfig(item: AIModelConfig) {
  const confirmed = await ElMessageBox.confirm(`确认删除配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  const nextList = aiConfigList.value.filter((x) => x.id !== item.id)
  await persistAIConfigList(nextList)
}

async function testConnection(item: AIModelConfig) {
  try {
    await axios.post('/api/config-center/test-model', {
      api_key: item.api_key || '',
      api_base_url: item.api_base_url,
      model_name: item.model_name,
    })
    ElMessage.success(`模型「${item.name}」连接成功`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '连接失败')
  }
}

function resetPromptDialogForm() {
  Object.assign(promptDialogForm, {
    id: '',
    name: '',
    prompt_type: 'generation',
    content: '',
    enabled: true,
    created_at: '',
    updated_at: '',
    creator: 'admin',
  })
}

function openCreatePromptDialog() {
  editingPromptId.value = ''
  resetPromptDialogForm()
  promptDialogVisible.value = true
}

function openEditPromptDialog(item: PromptConfigItem) {
  editingPromptId.value = item.id
  Object.assign(promptDialogForm, item)
  promptDialogVisible.value = true
}

function previewPrompt(item: PromptConfigItem) {
  previewContent.value = item.content || '-'
  previewVisible.value = true
}

function mapEnabledPromptByRole(list: PromptConfigItem[]) {
  const result = {
    analysis: form.prompts.analysis,
    generation: form.prompts.generation,
    review: form.prompts.review,
  }
  for (const role of ['analysis', 'generation', 'review'] as const) {
    const enabled = list.find((x) => x.prompt_type === role && x.enabled)
    if (enabled && enabled.content.trim()) {
      result[role] = enabled.content.trim()
    }
  }
  return result
}

async function persistPromptConfigList(nextList: PromptConfigItem[]) {
  const payload = {
    prompt_configs: nextList,
    prompts: mapEnabledPromptByRole(nextList),
  }
  saving.value = true
  try {
    const resp = await axios.put('/api/config-center', payload)
    applyConfig(resp.data?.data || {})
    ElMessage.success('提示词配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function submitPromptDialog() {
  if (!promptDialogFormRef.value) return
  const valid = await promptDialogFormRef.value.validate().catch(() => false)
  if (!valid) return

  const now = formatNow()
  const record: PromptConfigItem = {
    ...promptDialogForm,
    id: editingPromptId.value || newId(),
    created_at: promptDialogForm.created_at || now,
    updated_at: now,
    creator: promptDialogForm.creator || 'admin',
  }

  let nextList = [...promptConfigList.value]
  nextList = nextList.map((x) => {
      if (record.enabled && x.prompt_type === record.prompt_type && x.id !== record.id) {
        return { ...x, enabled: false, updated_at: now }
      }
      return x
    })

  const idx = nextList.findIndex((x) => x.id === record.id)
  if (idx >= 0) {
    nextList[idx] = record
  } else {
    nextList.unshift(record)
  }

  await persistPromptConfigList(nextList)
  promptDialogVisible.value = false
}

async function removePromptConfig(item: PromptConfigItem) {
  const confirmed = await ElMessageBox.confirm(`确认删除提示词配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  const nextList = promptConfigList.value.filter((x) => x.id !== item.id)
  await persistPromptConfigList(nextList)
}

async function loadDefaultPrompts() {
  try {
    const resp = await axios.get('/api/config-center/default-prompts')
    const defaults = Array.isArray(resp.data?.data) ? resp.data.data : []
    if (!defaults.length) {
      ElMessage.warning('未获取到默认提示词')
      return
    }
    await persistPromptConfigList(defaults)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载默认提示词失败')
  }
}

function outputModeLabel(mode: string) {
  return mode === 'stream' ? '⚡ 实时流式输出' : '📦 完整输出'
}

function resetBehaviorDialogForm() {
  Object.assign(behaviorDialogForm, {
    id: '',
    name: '默认生成配置',
    output_mode: 'stream',
    enable_ai_review: true,
    review_timeout_seconds: 1500,
    enabled: true,
    created_at: '',
    updated_at: '',
  })
}

function openCreateBehaviorDialog() {
  editingBehaviorId.value = ''
  resetBehaviorDialogForm()
  behaviorDialogVisible.value = true
}

function openEditBehaviorDialog(item: GenerationBehaviorConfigItem) {
  editingBehaviorId.value = item.id
  Object.assign(behaviorDialogForm, item)
  behaviorDialogVisible.value = true
}

async function persistBehaviorConfigList(nextList: GenerationBehaviorConfigItem[]) {
  const payload = {
    generation_behavior_configs: nextList,
  }
  saving.value = true
  try {
    const resp = await axios.put('/api/config-center', payload)
    applyConfig(resp.data?.data || {})
    ElMessage.success('生成行为配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function submitBehaviorDialog() {
  if (!behaviorDialogFormRef.value) return
  const valid = await behaviorDialogFormRef.value.validate().catch(() => false)
  if (!valid) return

  const now = formatNow()
  const record: GenerationBehaviorConfigItem = {
    ...behaviorDialogForm,
    id: editingBehaviorId.value || newId(),
    review_timeout_seconds: Math.max(60, Math.min(3600, Number(behaviorDialogForm.review_timeout_seconds || 1500))),
    created_at: behaviorDialogForm.created_at || now,
    updated_at: now,
  }

  let nextList = [...behaviorConfigList.value]
  nextList = nextList.map((x) => {
    if (record.enabled && x.id !== record.id) {
      return { ...x, enabled: false, updated_at: now }
    }
    return x
  })

  const idx = nextList.findIndex((x) => x.id === record.id)
  if (idx >= 0) {
    nextList[idx] = record
  } else {
    nextList.unshift(record)
  }

  await persistBehaviorConfigList(nextList)
  behaviorDialogVisible.value = false
}

async function removeBehaviorConfig(item: GenerationBehaviorConfigItem) {
  const confirmed = await ElMessageBox.confirm(`确认删除生成行为配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  const nextList = behaviorConfigList.value.filter((x) => x.id !== item.id)
  await persistBehaviorConfigList(nextList)
}

function notifyTabLabel(tab: 'feishu' | 'wecom' | 'dingtalk') {
  if (tab === 'feishu') return '飞书机器人'
  if (tab === 'wecom') return '企微机器人'
  return '钉钉机器人'
}

async function saveNotificationChannel(tab: 'feishu' | 'wecom' | 'dingtalk') {
  saving.value = true
  try {
    const current = form.notifications[tab]
    const payload = {
      notifications: {
        [tab]: {
          name: current.name,
          enabled: current.enabled,
          webhook: current.webhook,
          secret: current.secret,
          business_types: current.business_types,
        },
      },
    }
    const resp = await axios.put('/api/config-center', payload)
    applyConfig(resp.data?.data || {})
    ElMessage.success(`${notifyTabLabel(tab)}配置已保存`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.config-page {
  max-width: 1280px;
  margin: 0 auto;
}

.section-header {
  margin-top: 4px;
}

.section-title {
  font-size: 54px;
  line-height: 1.1;
  color: #243447;
  font-weight: 800;
}

.section-subtitle {
  margin-top: 10px;
  color: #6b7280;
  font-size: 20px;
}

.config-card {
  background: #fff;
  border: 1px solid #dbe3ee;
  border-radius: 14px;
  padding: 22px;
  box-shadow: 0 2px 12px rgba(2, 6, 23, 0.06);
}

.meta-label {
  color: #64748b;
  font-weight: 600;
  margin-bottom: 2px;
}

.empty-box {
  background: #fff;
  border: 1px solid #dbe3ee;
  border-radius: 14px;
  padding: 48px;
  text-align: center;
  color: #64748b;
}

.prompt-preview {
  background: #f4f6f9;
  border-left: 4px solid #3b82f6;
  border-radius: 8px;
  padding: 12px;
  color: #334155;
  line-height: 1.7;
  min-height: 120px;
  white-space: pre-wrap;
}

.tips-box {
  background: #f4f6f9;
  border-left: 4px solid #3b82f6;
  border-radius: 8px;
  padding: 14px;
}

.preview-dialog-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
  max-height: 420px;
  overflow: auto;
}

.notification-header {
  background: linear-gradient(120deg, #4f7ee8 0%, #6f4bb8 100%);
  border-radius: 14px;
  padding: 26px 24px;
}
</style>
