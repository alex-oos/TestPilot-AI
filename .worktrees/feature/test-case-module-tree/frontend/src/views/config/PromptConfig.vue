<template>
  <section class="config-page" v-loading="loading">
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
      暂无提示词配置，点击右上角"添加配置"开始配置。
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
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createPrompt,
  editPrompt,
  deletePrompt,
  getPrompts,
  getPromptDefaults,
} from '../../api/config-center'
import { formatNow, newId } from './utils'

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

const loading = ref(false)
const saving = ref(false)
const promptDialogVisible = ref(false)
const editingPromptId = ref('')
const promptDialogFormRef = ref<FormInstance>()
const promptConfigList = ref<PromptConfigItem[]>([])
const previewVisible = ref(false)
const previewContent = ref('')

const prompts = reactive({
  analysis: '',
  generation: '',
  review: '',
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

const promptDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  content: [{ required: true, message: '请输入提示词内容', trigger: 'blur' }],
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

function clippedPrompt(content: string) {
  if (!content) return '-'
  if (content.length <= 220) return content
  return `${content.slice(0, 220)}...`
}

function applyPromptConfig(data: any) {
  Object.assign(prompts, data?.prompts || {})
  promptConfigList.value = Array.isArray(data?.prompt_configs)
    ? data.prompt_configs.map((item: any) => ({
      ...item,
      role: item?.role || item?.prompt_type || 'generation',
      prompt_type: item?.prompt_type || item?.role || 'generation',
    }))
    : []
}

async function fetchConfig() {
  loading.value = true
  try {
    const resp = await getPrompts()
    applyPromptConfig(resp.data?.data || {})
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
}

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
    analysis: prompts.analysis,
    generation: prompts.generation,
    review: prompts.review,
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
</style>
