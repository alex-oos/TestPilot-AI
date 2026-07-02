<template>
  <section class="config-page" v-loading="loading">
    <div class="section-header text-center">
      <h1 class="section-title">🤖 AI 模型配置</h1>
      <p class="section-subtitle">配置用于测试用例生成和评审的 AI 模型</p>
    </div>

    <div class="flex items-center justify-between mt-8 mb-4">
      <h2 class="text-3xl font-semibold text-slate-800">模型配置列表</h2>
      <el-button type="success" @click="openCreateAIDialog">添加配置</el-button>
    </div>

    <div v-if="!aiConfigList.length" class="empty-box">
      暂无模型配置，点击右上角"添加配置"开始配置。
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
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createAIModel,
  editAIModel,
  deleteAIModel,
  getAIModels,
  testModelConnection,
} from '../../api/config-center'
import { formatNow, newId } from './utils'

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

const aiDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
  api_base_url: [{ required: true, message: '请输入 API Base URL', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

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

function onModelTypeChange(value: string) {
  const defaultBaseUrl = modelTypeDefaultBaseUrl[value]
  if (defaultBaseUrl) {
    aiDialogForm.api_base_url = defaultBaseUrl
  }
}

function applyAIConfig(data: any) {
  aiConfigList.value = Array.isArray(data?.ai_model_configs) ? data.ai_model_configs : []
}

async function fetchConfig() {
  loading.value = true
  try {
    const resp = await getAIModels()
    applyAIConfig(resp.data?.data || {})
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
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

onMounted(() => {
  fetchConfig()
})
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
</style>
