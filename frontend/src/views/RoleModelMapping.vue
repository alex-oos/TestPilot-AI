<template>
  <div class="space-y-6" v-loading="loading">
    <section class="config-page">
      <div class="section-header text-center">
        <h1 class="section-title">📝 角色配置</h1>
        <p class="section-subtitle">配置用于测试用例编写和评审的AI角色</p>
      </div>

      <div class="flex items-center justify-between mt-8 mb-4">
        <h2 class="text-3xl font-semibold text-slate-800">角色配置列表</h2>
        <el-button type="success" @click="openCreateDialog">+ 添加配置</el-button>
      </div>

      <div v-if="!roleConfigList.length" class="empty-box">
        暂无角色配置，点击右上角“添加配置”开始配置。
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div v-for="item in roleConfigList" :key="item.id" class="config-card">
          <div class="flex items-start justify-between gap-3 mb-3">
            <div>
              <h3 class="text-3xl font-bold text-slate-800">{{ item.name }}</h3>
              <div class="flex items-center gap-2 mt-2 flex-wrap">
                <el-tag size="small" :type="roleTagType(item.role_type)">{{ roleLabel(item.role_type) }}</el-tag>
                <el-tag size="small" :type="item.enabled ? 'success' : 'danger'">{{ item.enabled ? '启用' : '禁用' }}</el-tag>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <el-button size="small" type="warning" @click="openEditDialog(item)">✏️ 编辑</el-button>
              <el-button size="small" type="danger" @click="removeRoleConfig(item)">🗑 删除</el-button>
            </div>
          </div>

          <p class="meta-label mb-2">配置模型:</p>
          <div class="prompt-preview">{{ item.mapped_model_name || '-' }}</div>

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
            <div>
              <p class="meta-label">修改者:</p>
              <p>{{ item.modifier || 'admin' }}</p>
            </div>
          </div>
        </div>
      </div>

      <el-dialog
        v-model="dialogVisible"
        :title="editingId ? '编辑配置' : '+ 添加配置'"
        width="760px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="dialogForm" :rules="formRules" label-position="top">
          <el-form-item label="配置名称" prop="name">
            <el-input v-model="dialogForm.name" placeholder="例如：需求分析专家配置 v1.0" />
          </el-form-item>

          <el-form-item label="角色" prop="role_type">
            <el-select v-model="dialogForm.role_type" placeholder="请选择角色" class="w-full">
              <el-option label="需求分析专家" value="analysis" />
              <el-option label="测试用例编写专家" value="generation" />
              <el-option label="测试用例评审专家" value="review" />
            </el-select>
          </el-form-item>

          <el-form-item label="模型名称" prop="mapped_model_name">
            <el-select
              v-model="dialogForm.mapped_model_name"
              placeholder="请选择模型名称"
              class="w-full"
              filterable
              allow-create
              default-first-option
            >
              <el-option v-for="name in modelNameOptions" :key="name" :label="name" :value="name" />
            </el-select>
          </el-form-item>

          <el-form-item class="mt-4">
            <el-checkbox v-model="dialogForm.enabled">启用此配置</el-checkbox>
            <p class="text-sm text-slate-500 mt-1">启用后，同角色的其他配置将被禁用</p>
          </el-form-item>
        </el-form>

        <template #footer>
          <div class="flex justify-end gap-3">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="success" :loading="saving" @click="submitDialog">💾 保存配置</el-button>
          </div>
        </template>
      </el-dialog>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

interface AIModelConfig {
  id: string
  model_name: string
  enabled: boolean
}

interface RoleConfigItem {
  id: string
  name: string
  role_type: string
  mapped_model_name: string
  enabled: boolean
  created_at: string
  updated_at: string
  creator: string
  modifier: string
}

const loading = ref(false)
const saving = ref(false)
const modelConfigs = ref<AIModelConfig[]>([])
const roleConfigList = ref<RoleConfigItem[]>([])

const dialogVisible = ref(false)
const editingId = ref('')
const formRef = ref<FormInstance>()

const dialogForm = reactive<RoleConfigItem>({
  id: '',
  name: '',
  role_type: 'generation',
  mapped_model_name: '',
  enabled: true,
  created_at: '',
  updated_at: '',
  creator: 'admin',
  modifier: 'admin',
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  role_type: [{ required: true, message: '请选择角色', trigger: 'change' }],
  mapped_model_name: [{ required: true, message: '请选择模型名称', trigger: 'change' }],
}

const modelNameOptions = computed(() => {
  const names = modelConfigs.value
    .filter((x) => x.enabled && (x.model_name || '').trim())
    .map((x) => x.model_name.trim())
  return Array.from(new Set(names))
})

function roleLabel(role: string) {
  if (role === 'analysis') return '需求分析专家'
  if (role === 'generation') return '测试用例编写专家'
  return '测试用例评审专家'
}

function roleTagType(role: string): 'warning' | 'success' | 'danger' {
  if (role === 'analysis') return 'warning'
  if (role === 'generation') return 'success'
  return 'danger'
}

function formatNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')
}

function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function normalizeRoleItem(item: any): RoleConfigItem {
  return {
    id: String(item?.id || ''),
    name: String(item?.name || ''),
    role_type: String(item?.role_type || 'generation'),
    mapped_model_name: String(item?.mapped_model_name || ''),
    enabled: Boolean(item?.enabled ?? true),
    created_at: String(item?.created_at || ''),
    updated_at: String(item?.updated_at || ''),
    creator: String(item?.creator || 'admin'),
    modifier: String(item?.modifier || 'admin'),
  }
}

function resetDialogForm() {
  Object.assign(dialogForm, {
    id: '',
    name: '',
    role_type: 'generation',
    mapped_model_name: modelNameOptions.value[0] || '',
    enabled: true,
    created_at: '',
    updated_at: '',
    creator: 'admin',
    modifier: 'admin',
  })
}

async function loadData() {
  loading.value = true
  try {
    const resp = await axios.get('/api/config-center/role-configs')
    const data = resp.data?.data || {}
    modelConfigs.value = Array.isArray(data?.ai_model_configs) ? data.ai_model_configs : []
    roleConfigList.value = Array.isArray(data?.role_config_items)
      ? data.role_config_items.map((x: any) => normalizeRoleItem(x))
      : []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '加载角色配置失败')
  } finally {
    loading.value = false
  }
}

async function persistRoleConfigList(nextList: RoleConfigItem[]) {
  const payload = {
    role_config_items: nextList,
  }
  saving.value = true
  try {
    const resp = await axios.put('/api/config-center/role-configs', payload)
    const data = resp.data?.data || {}
    roleConfigList.value = Array.isArray(data?.role_config_items)
      ? data.role_config_items.map((x: any) => normalizeRoleItem(x))
      : []
    ElMessage.success('角色配置已保存')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function openCreateDialog() {
  editingId.value = ''
  resetDialogForm()
  dialogVisible.value = true
}

function openEditDialog(item: RoleConfigItem) {
  editingId.value = item.id
  Object.assign(dialogForm, item)
  dialogVisible.value = true
}

async function submitDialog() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const now = formatNow()
  const record: RoleConfigItem = {
    ...dialogForm,
    id: editingId.value || newId(),
    created_at: dialogForm.created_at || now,
    updated_at: now,
    creator: dialogForm.creator || 'admin',
    modifier: 'admin',
  }

  let nextList = [...roleConfigList.value]
  nextList = nextList.map((x) => {
    if (record.enabled && x.role_type === record.role_type && x.id !== record.id) {
      return { ...x, enabled: false, updated_at: now, modifier: 'admin' }
    }
    return x
  })

  const idx = nextList.findIndex((x) => x.id === record.id)
  if (idx >= 0) {
    nextList[idx] = record
  } else {
    nextList.unshift(record)
  }

  await persistRoleConfigList(nextList)
  dialogVisible.value = false
}

async function removeRoleConfig(item: RoleConfigItem) {
  const confirmed = await ElMessageBox.confirm(`确认删除角色配置「${item.name}」吗？`, '提示', {
    type: 'warning',
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
  }).catch(() => false)
  if (!confirmed) return

  const nextList = roleConfigList.value.filter((x) => x.id !== item.id)
  await persistRoleConfigList(nextList)
}

onMounted(() => {
  loadData()
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
  min-height: 72px;
  white-space: pre-wrap;
}
</style>
