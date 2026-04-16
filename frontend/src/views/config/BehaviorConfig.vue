<template>
  <section class="config-page" v-loading="loading">
    <div class="section-header text-center">
      <h1 class="section-title">⚙️ 生成行为配置</h1>
      <p class="section-subtitle">配置测试用例生成的默认行为和自动化流程</p>
    </div>

    <div class="flex items-center justify-between mt-8 mb-4">
      <h2 class="text-3xl font-semibold text-slate-800">配置列表</h2>
      <el-button type="success" @click="openCreateBehaviorDialog">+ 添加配置</el-button>
    </div>

    <div v-if="!behaviorConfigList.length" class="empty-box">
      暂无生成行为配置，点击右上角"添加配置"开始配置。
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
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createBehavior,
  editBehavior,
  deleteBehavior,
  getBehaviors,
} from '../../api/config-center'
import { formatNow, newId } from './utils'

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

const loading = ref(false)
const saving = ref(false)
const behaviorDialogVisible = ref(false)
const editingBehaviorId = ref('')
const behaviorDialogFormRef = ref<FormInstance>()
const behaviorConfigList = ref<GenerationBehaviorConfigItem[]>([])

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

const behaviorDialogRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  output_mode: [{ required: true, message: '请选择输出模式', trigger: 'change' }],
}

function outputModeLabel(mode: string) {
  return mode === 'stream' ? '⚡ 实时流式输出' : '📦 完整输出'
}

function applyBehaviorConfig(data: any) {
  behaviorConfigList.value = Array.isArray(data?.generation_behavior_configs) ? data.generation_behavior_configs : []
}

async function fetchConfig() {
  loading.value = true
  try {
    const resp = await getBehaviors()
    applyBehaviorConfig(resp.data?.data || {})
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
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
</style>
