<template>
  <div class="space-y-6" v-loading="loading">

    <section v-if="activeSection === 'ai'" class="config-page">
      <div class="section-header text-center">
        <h1 class="section-title">🤖 AI 模型配置</h1>
        <p class="section-subtitle">配置用于测试用例生成和评审的 AI 模型</p>
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
                <el-tag size="small" :type="item.enabled ? 'success' : 'danger'">
                  {{ item.enabled ? '已启用' : '已禁用' }}
                </el-tag>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <el-switch
                :model-value="item.enabled"
                inline-prompt
                active-text="开"
                inactive-text="关"
                :disabled="saving || togglingAIId === item.id"
                @change="toggleAIConfigEnabled(item, $event as boolean)"
              />
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
            <div>
              <p class="meta-label">修改时间:</p>
              <p>{{ item.updated_at || '-' }}</p>
            </div>
            <div>
              <p class="meta-label">创建者:</p>
              <p>{{ item.creator || 'admin' }}</p>
            </div>
            <div>
              <p class="meta-label">修改者:</p>
              <p>{{ item.modifier || 'admin' }}</p>
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
              <el-option
                v-for="item in modelTypeOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="API Key" prop="api_key">
            <el-input v-model="aiDialogForm.api_key" show-password placeholder="输入您的API Key（本地LM Studio可留空）" />
          </el-form-item>

          <el-form-item label="API Base URL" prop="api_base_url">
            <el-input v-model="aiDialogForm.api_base_url" placeholder="例如：http://127.0.0.1:1234/v1" />
          </el-form-item>

          <el-form-item label="模型名称" prop="model_name">
            <el-input
              v-model="aiDialogForm.model_name"
              placeholder="请输入模型名称，例如：qwen3:8b / deepseek-chat / gpt-4.1"
            />
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

          <el-form-item label="启用状态">
            <el-switch
              v-model="aiDialogForm.enabled"
              inline-prompt
              active-text="开"
              inactive-text="关"
            />
          </el-form-item>

          <div class="mb-2">
            <el-tag :type="aiTestPassed ? 'success' : 'warning'">
              {{ aiTestPassed ? '已通过连接测试，可保存' : '请先测试配置，测试通过后才可保存' }}
            </el-tag>
          </div>
        </el-form>

        <template #footer>
          <div class="flex justify-end gap-3">
            <el-button @click="aiDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="aiTesting" @click="testCurrentAIDialogConnection">测试配置</el-button>
            <el-button type="success" :loading="saving" :disabled="!aiTestPassed" @click="submitAIDialog">保存配置</el-button>
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
                <el-tag size="small" :type="promptTypeTagType(item.role || item.prompt_type || '')">{{ promptTypeLabel(item.role || item.prompt_type || '') }}</el-tag>
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

          <el-form-item label="角色" prop="role">
            <el-select v-model="promptDialogForm.role" placeholder="请选择角色" class="w-full">
              <el-option label="需求分析专家" value="analysis" />
              <el-option label="测试用例编写专家" value="generation" />
              <el-option label="测试用例评审专家" value="review" />
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

    <section v-if="activeSection === 'notifications'" class="config-page config-page-full">
      <div class="notification-header">
        <h1 class="text-4xl font-bold text-white">⚙️ 消息通知配置</h1>
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

          <el-form-item label="自定义关键词（可选）">
            <el-input v-model="currentNotifyConfig.custom_keyword" placeholder="请输入自定义关键词（如：@all）" />
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import {
  createAIModel,
  createBehavior,
  createPrompt,
  deleteAIModel,
  deleteBehavior,
  deletePrompt,
  editAIModel,
  editBehavior,
  editNotification,
  editPrompt,
  getAIModels,
  getBehaviors,
  getNotifications,
  getPromptDefaults,
  getPrompts,
  testModelConnection,
} from '../api/config-center'

interface AIModelConfig {
  id: string
  name: string
  model_type: string
  api_key: string
  api_base_url: string
  model_name: string
  max_tokens: number
  temperature: number
  top_p: number
  enabled: boolean
  created_at: string
  updated_at: string
  creator: string
  modifier: string
}

interface PromptConfigItem {
  id: string
  name: string
  role: string
  prompt_type?: string
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
const aiTestPassed = ref(false)
const aiTesting = ref(false)
const aiLastTestSignature = ref('')
const togglingAIId = ref('')

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
  role_configs: {
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
    feishu: { name: '', enabled: false, webhook: '', secret: '', custom_keyword: '' },
    dingtalk: { name: '', enabled: false, webhook: '', secret: '', custom_keyword: '' },
    wecom: { name: '', enabled: false, webhook: '', secret: '', custom_keyword: '' },
  },
})

const aiDialogForm = reactive<AIModelConfig>({
  id: '',
  name: '',
  model_type: 'lm_studio',
  api_key: '',
  api_base_url: 'http://127.0.0.1:1234/v1',
  model_name: '',
  max_tokens: 4096,
  temperature: 0.7,
  top_p: 0.9,
  enabled: true,
  created_at: '',
  updated_at: '',
  creator: 'admin',
  modifier: 'admin',
})

const promptDialogForm = reactive<PromptConfigItem>({
  id: '',
  name: '',
  role: 'generation',
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
  api_base_url: [{ required: true, message: '请输入 API Base URL', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

const promptDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  content: [{ required: true, message: '请输入提示词内容', trigger: 'blur' }],
}

const behaviorDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  output_mode: [{ required: true, message: '请选择输出模式', trigger: 'change' }],
}

onMounted(() => {
  fetchConfig()
})

watch(
  () => activeSection.value,
  () => {
    fetchConfig()
  }
)

const modelTypeOptions = [
  { label: 'LM Studio', value: 'lm_studio' },
  { label: 'Ollama', value: 'ollama' },
  { label: 'OpenAI 兼容', value: 'openai_compatible' },
  { label: '通义千问', value: 'qwen' },
  { label: '火山云', value: 'volcengine' },
  { label: '智谱清言', value: 'zhipu' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '腾讯元宝', value: 'yuanbao' },
  { label: '其他', value: 'other' },
]

const modelTypeDefaultBaseUrl: Record<string, string> = {
  lm_studio: 'http://127.0.0.1:1234/v1',
  ollama: 'http://127.0.0.1:11434/v1',
  openai_compatible: 'https://api.openai.com/v1',
  qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  volcengine: 'https://ark.cn-beijing.volces.com/api/v3',
  zhipu: 'https://open.bigmodel.cn/api/paas/v4',
  deepseek: 'https://api.deepseek.com/v1',
  yuanbao: 'https://api.hunyuan.cloud.tencent.com/v1',
}

function modelTypeLabel(type: string) {
  const labels: Record<string, string> = {
    lm_studio: 'LM Studio',
    ollama: 'Ollama',
    openai_compatible: 'OpenAI兼容',
    qwen: '通义千问',
    volcengine: '火山云',
    zhipu: '智谱清言',
    deepseek: 'DeepSeek',
    yuanbao: '腾讯元宝',
    other: '其他',
  }
  return labels[type] || type
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
  const defaultBaseUrl = modelTypeDefaultBaseUrl[value]
  if (defaultBaseUrl) {
    aiDialogForm.api_base_url = defaultBaseUrl
  }
}

async function fetchConfig() {
  loading.value = true
  try {
    if (activeSection.value === 'ai') {
      const resp = await getAIModels()
      applyAIConfig(resp.data?.data || {})
    } else if (activeSection.value === 'prompts') {
      const resp = await getPrompts()
      applyPromptConfig(resp.data?.data || {})
    } else if (activeSection.value === 'behavior') {
      const resp = await getBehaviors()
      applyBehaviorConfig(resp.data?.data || {})
    } else if (activeSection.value === 'notifications') {
      const resp = await getNotifications()
      applyNotificationConfig(resp.data?.data || {})
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
}

function applyAIConfig(data: any) {
  aiConfigList.value = Array.isArray(data?.ai_model_configs) ? data.ai_model_configs : []
}

function applyPromptConfig(data: any) {
  Object.assign(form.prompts, data?.prompts || {})
  promptConfigList.value = Array.isArray(data?.prompt_configs)
    ? data.prompt_configs.map((item: any) => ({
      ...item,
      role: item?.role || item?.prompt_type || 'generation',
      prompt_type: item?.prompt_type || item?.role || 'generation',
    }))
    : []
}

function applyBehaviorConfig(data: any) {
  behaviorConfigList.value = Array.isArray(data?.generation_behavior_configs) ? data.generation_behavior_configs : []
}

function applyNotificationConfig(data: any) {
  Object.assign(form.notifications.feishu, data?.notifications?.feishu || {})
  Object.assign(form.notifications.dingtalk, data?.notifications?.dingtalk || {})
  Object.assign(form.notifications.wecom, data?.notifications?.wecom || {})
}

function resetAIDialogForm() {
  Object.assign(aiDialogForm, {
    id: '',
    name: '',
    model_type: 'lm_studio',
    api_key: '',
    api_base_url: 'http://127.0.0.1:1234/v1',
    model_name: 'qwen/qwen3.5-9b',
    max_tokens: 4096,
    temperature: 0.7,
    top_p: 0.9,
    enabled: true,
    created_at: '',
    updated_at: '',
    creator: 'admin',
    modifier: 'admin',
  })
}

function buildAITestSignature() {
  return JSON.stringify({
    model_type: aiDialogForm.model_type,
    api_key: (aiDialogForm.api_key || '').trim(),
    api_base_url: (aiDialogForm.api_base_url || '').trim(),
    model_name: (aiDialogForm.model_name || '').trim(),
  })
}

function resetAITestState() {
  aiTestPassed.value = false
  aiLastTestSignature.value = ''
}

function openCreateAIDialog() {
  editingAIId.value = ''
  resetAIDialogForm()
  resetAITestState()
  aiDialogVisible.value = true
}

function openEditAIDialog(item: AIModelConfig) {
  editingAIId.value = item.id
  Object.assign(aiDialogForm, {
    id: item.id,
    name: item.name,
    model_type: item.model_type,
    api_key: item.api_key,
    api_base_url: item.api_base_url,
    model_name: item.model_name,
    max_tokens: item.max_tokens,
    temperature: item.temperature,
    top_p: item.top_p,
    enabled: item.enabled,
    created_at: item.created_at,
    updated_at: item.updated_at,
    creator: item.creator || 'admin',
    modifier: item.modifier || 'admin',
  })
  resetAITestState()
  aiDialogVisible.value = true
}

async function createAIConfigItem(record: AIModelConfig) {
  saving.value = true
  try {
    const resp = await createAIModel(record)
    applyAIConfig(resp.data?.data || {})
    ElMessage.success('AI 模型配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function updateAIConfigItem(record: AIModelConfig) {
  saving.value = true
  try {
    const resp = await editAIModel(record)
    applyAIConfig(resp.data?.data || {})
    ElMessage.success('AI 模型配置已保存')
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
  if (!aiTestPassed.value || aiLastTestSignature.value !== buildAITestSignature()) {
    ElMessage.warning('请先测试当前配置并通过，再保存')
    return
  }

  const record: AIModelConfig = {
    id: editingAIId.value || newId(),
    name: aiDialogForm.name,
    model_type: aiDialogForm.model_type,
    api_key: aiDialogForm.api_key,
    api_base_url: aiDialogForm.api_base_url,
    model_name: aiDialogForm.model_name,
    max_tokens: aiDialogForm.max_tokens,
    temperature: aiDialogForm.temperature,
    top_p: aiDialogForm.top_p,
    enabled: aiDialogForm.enabled,
    created_at: aiDialogForm.created_at || formatNow(),
    updated_at: formatNow(),
    creator: aiDialogForm.creator || 'admin',
    modifier: 'admin',
  }

  if (editingAIId.value) {
    await updateAIConfigItem(record)
  } else {
    await createAIConfigItem(record)
  }
  aiDialogVisible.value = false
}

async function testCurrentAIDialogConnection() {
  if (!aiDialogFormRef.value) return
  const valid = await aiDialogFormRef.value.validate().catch(() => false)
  if (!valid) return

  aiTesting.value = true
  try {
    await testModelConnection({
      api_key: aiDialogForm.api_key || '',
      api_base_url: aiDialogForm.api_base_url,
      model_name: aiDialogForm.model_name,
    })
    aiLastTestSignature.value = buildAITestSignature()
    aiTestPassed.value = true
    ElMessage.success('模型连接测试成功，可以保存')
  } catch (e: any) {
    aiTestPassed.value = false
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '连接测试失败')
  } finally {
    aiTesting.value = false
  }
}

async function removeAIConfig(item: AIModelConfig) {
  const confirmed = await ElMessageBox.confirm(`确认删除配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  saving.value = true
  try {
    const resp = await deleteAIModel(item.id)
    applyAIConfig(resp.data?.data || {})
    ElMessage.success('AI 模型配置已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '删除失败')
  } finally {
    saving.value = false
  }
}

async function testConnection(item: AIModelConfig) {
  try {
    await testModelConnection({
      api_key: item.api_key || '',
      api_base_url: item.api_base_url,
      model_name: item.model_name,
    })
    ElMessage.success(`模型「${item.name}」连接成功`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '连接失败')
  }
}

async function toggleAIConfigEnabled(item: AIModelConfig, enabled: boolean) {
  if (item.enabled === enabled) return
  togglingAIId.value = item.id
  try {
    await updateAIConfigItem({ ...item, enabled })
  } finally {
    togglingAIId.value = ''
  }
}

watch(
  () => [aiDialogForm.model_type, aiDialogForm.api_key, aiDialogForm.api_base_url, aiDialogForm.model_name],
  () => {
    if (!aiDialogVisible.value) return
    if (aiTestPassed.value && aiLastTestSignature.value !== buildAITestSignature()) {
      aiTestPassed.value = false
    }
  }
)

function resetPromptDialogForm() {
  Object.assign(promptDialogForm, {
    id: '',
    name: '',
    role: 'generation',
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
  Object.assign(promptDialogForm, {
    ...item,
    role: item.role || item.prompt_type || 'generation',
    prompt_type: item.prompt_type || item.role || 'generation',
  })
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
    const enabled = list.find((x) => (x.role || x.prompt_type) === role && x.enabled)
    if (enabled && enabled.content.trim()) {
      result[role] = enabled.content.trim()
    }
  }
  return result
}

async function createPromptConfigItem(record: PromptConfigItem) {
  saving.value = true
  try {
    const resp = await createPrompt(record)
    applyPromptConfig(resp.data?.data || {})
    ElMessage.success('提示词配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function updatePromptConfigItem(record: PromptConfigItem) {
  saving.value = true
  try {
    const resp = await editPrompt(record)
    applyPromptConfig(resp.data?.data || {})
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
    role: promptDialogForm.role || promptDialogForm.prompt_type || 'generation',
    prompt_type: promptDialogForm.role || promptDialogForm.prompt_type || 'generation',
    id: editingPromptId.value || newId(),
    created_at: promptDialogForm.created_at || now,
    updated_at: now,
    creator: promptDialogForm.creator || 'admin',
  }

  if (editingPromptId.value) {
    await updatePromptConfigItem(record)
  } else {
    await createPromptConfigItem(record)
  }
  promptDialogVisible.value = false
}

async function removePromptConfig(item: PromptConfigItem) {
  const confirmed = await ElMessageBox.confirm(`确认删除提示词配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  saving.value = true
  try {
    const resp = await deletePrompt(item.id)
    applyPromptConfig(resp.data?.data || {})
    ElMessage.success('提示词配置已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '删除失败')
  } finally {
    saving.value = false
  }
}

async function loadDefaultPrompts() {
  try {
    const resp = await getPromptDefaults()
    const defaults = Array.isArray(resp.data?.data) ? resp.data.data : []
    if (!defaults.length) {
      ElMessage.warning('未获取到默认提示词')
      return
    }
    const payload = {
      prompt_configs: defaults,
      prompts: mapEnabledPromptByRole(defaults),
    }
    const promptConfigs = Array.isArray(payload.prompt_configs) ? payload.prompt_configs : []
    for (const item of promptConfigs) {
      await editPrompt(item)
    }
    const result = await getPrompts()
    applyPromptConfig(result.data?.data || {})
    ElMessage.success('默认提示词已加载')
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

async function createBehaviorConfigItem(record: GenerationBehaviorConfigItem) {
  saving.value = true
  try {
    const resp = await createBehavior(record)
    applyBehaviorConfig(resp.data?.data || {})
    ElMessage.success('生成行为配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function updateBehaviorConfigItem(record: GenerationBehaviorConfigItem) {
  saving.value = true
  try {
    const resp = await editBehavior(record)
    applyBehaviorConfig(resp.data?.data || {})
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

  if (editingBehaviorId.value) {
    await updateBehaviorConfigItem(record)
  } else {
    await createBehaviorConfigItem(record)
  }
  behaviorDialogVisible.value = false
}

async function removeBehaviorConfig(item: GenerationBehaviorConfigItem) {
  const confirmed = await ElMessageBox.confirm(`确认删除生成行为配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  saving.value = true
  try {
    const resp = await deleteBehavior(item.id)
    applyBehaviorConfig(resp.data?.data || {})
    ElMessage.success('生成行为配置已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '删除失败')
  } finally {
    saving.value = false
  }
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
      name: current.name,
      enabled: current.enabled,
      webhook: current.webhook,
      secret: current.secret,
      custom_keyword: current.custom_keyword,
    }
    const resp = await editNotification(tab, payload)
    applyNotificationConfig(resp.data?.data || {})
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

.config-page-full {
  max-width: none;
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
