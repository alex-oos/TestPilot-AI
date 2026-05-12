<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">性能场景</h1>
        <p class="text-gray-500">配置和管理性能测试场景，包括负载、压力、尖峰和耐久性测试。</p>
      </div>
      <el-button type="primary" color="#4f46e5" class="!rounded-xl" @click="openDialog()">
        + 新建场景
      </el-button>
    </div>

    <div v-loading="loading">
      <div v-if="scenarios.length === 0 && !loading" class="bg-white rounded-2xl border border-gray-100 shadow-sm p-16 text-center">
        <div class="text-5xl mb-4">🚀</div>
        <p class="text-lg text-slate-500 mb-4">暂无性能测试场景</p>
        <el-button type="primary" color="#4f46e5" @click="openDialog()">创建第一个场景</el-button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="item in scenarios"
          :key="item.id"
          class="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-6 flex flex-col"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1 min-w-0 mr-3">
              <h3 class="text-lg font-semibold text-slate-800 truncate">{{ item.name }}</h3>
              <p class="text-sm text-slate-400 mt-1 truncate" :title="item.description">
                {{ item.description || '暂无描述' }}
              </p>
            </div>
            <el-tag :type="typeTagType(item.type)" effect="light" round size="small" class="shrink-0">
              {{ typeLabel(item.type) }}
            </el-tag>
          </div>

          <div class="space-y-3 flex-1">
            <div class="flex items-center gap-2 text-sm">
              <span class="text-slate-400 w-16">目标 URL</span>
              <code class="text-slate-600 bg-slate-50 px-2 py-0.5 rounded truncate flex-1" :title="item.target_url">
                {{ item.target_url }}
              </code>
            </div>
            <div class="flex gap-4">
              <div class="flex items-center gap-2 text-sm">
                <span class="text-slate-400">并发数</span>
                <span class="font-semibold text-slate-700">{{ item.concurrency }}</span>
              </div>
              <div class="flex items-center gap-2 text-sm">
                <span class="text-slate-400">持续</span>
                <span class="font-semibold text-slate-700">{{ item.duration }}s</span>
              </div>
              <div v-if="item.ramp_up" class="flex items-center gap-2 text-sm">
                <span class="text-slate-400">预热</span>
                <span class="font-semibold text-slate-700">{{ item.ramp_up }}s</span>
              </div>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <span class="text-slate-400 w-16">状态</span>
              <el-tag :type="scenarioStatusType(item.status)" size="small" effect="plain" round>
                {{ scenarioStatusLabel(item.status) }}
              </el-tag>
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-5 pt-4 border-t border-slate-100">
            <el-button size="small" @click="openDialog(item)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(item)">删除</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑场景' : '新建场景'"
      width="600px"
      destroy-on-close
      class="!rounded-2xl"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="场景名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：首页负载测试" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="场景说明" />
        </el-form-item>
        <el-form-item label="测试类型" prop="type">
          <el-select v-model="form.type" placeholder="选择测试类型" class="w-full">
            <el-option label="负载测试 (Load)" value="load" />
            <el-option label="压力测试 (Stress)" value="stress" />
            <el-option label="尖峰测试 (Spike)" value="spike" />
            <el-option label="耐久测试 (Endurance)" value="endurance" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标 URL" prop="target_url">
          <el-input v-model="form.target_url" placeholder="https://example.com/api/endpoint" />
        </el-form-item>
        <div class="grid grid-cols-3 gap-4">
          <el-form-item label="并发数" prop="concurrency">
            <el-input-number v-model="form.concurrency" :min="1" :max="10000" class="!w-full" />
          </el-form-item>
          <el-form-item label="持续时间 (秒)" prop="duration">
            <el-input-number v-model="form.duration" :min="1" :max="86400" class="!w-full" />
          </el-form-item>
          <el-form-item label="预热时间 (秒)">
            <el-input-number v-model="form.ramp_up" :min="0" :max="3600" class="!w-full" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '确认创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../utils/request'

interface Scenario {
  id: string
  name: string
  description: string
  type: string
  target_url: string
  concurrency: number
  duration: number
  ramp_up: number
  status: string
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')

const scenarios = ref<Scenario[]>([])

const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  description: '',
  type: 'load',
  target_url: '',
  concurrency: 10,
  duration: 60,
  ramp_up: 5,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入场景名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择测试类型', trigger: 'change' }],
  target_url: [{ required: true, message: '请输入目标 URL', trigger: 'blur' }],
  concurrency: [{ required: true, message: '请输入并发数', trigger: 'blur' }],
  duration: [{ required: true, message: '请输入持续时间', trigger: 'blur' }],
}

onMounted(() => {
  fetchScenarios()
})

async function fetchScenarios() {
  loading.value = true
  try {
    const resp = await api.get('/performance/scenarios')
    const data = resp.data?.data || resp.data || {}
    scenarios.value = data.items || data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '加载场景列表失败')
  } finally {
    loading.value = false
  }
}

function typeLabel(type: string) {
  const map: Record<string, string> = { load: '负载', stress: '压力', spike: '尖峰', endurance: '耐久' }
  return map[type] || type
}

function typeTagType(type: string) {
  const map: Record<string, string> = { load: 'success', stress: 'danger', spike: 'warning', endurance: '' }
  return map[type] || 'info'
}

function scenarioStatusLabel(status: string) {
  const map: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status || '空闲'
}

function scenarioStatusType(status: string) {
  const map: Record<string, string> = {
    idle: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

function openDialog(row?: Scenario) {
  if (row) {
    isEdit.value = true
    editingId.value = row.id
    form.name = row.name
    form.description = row.description || ''
    form.type = row.type
    form.target_url = row.target_url
    form.concurrency = row.concurrency
    form.duration = row.duration
    form.ramp_up = row.ramp_up || 0
  } else {
    isEdit.value = false
    editingId.value = ''
    form.name = ''
    form.description = ''
    form.type = 'load'
    form.target_url = ''
    form.concurrency = 10
    form.duration = 60
    form.ramp_up = 5
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = { ...form }
    if (isEdit.value) {
      await api.put(`/performance/scenarios/${editingId.value}`, payload)
      ElMessage.success('场景已更新')
    } else {
      await api.post('/performance/scenarios', payload)
      ElMessage.success('场景已创建')
    }
    dialogVisible.value = false
    fetchScenarios()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Scenario) {
  const confirmed = await ElMessageBox.confirm(
    `确认删除场景「${row.name}」吗？删除后不可恢复。`,
    '提示',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  ).catch(() => false)
  if (!confirmed) return

  try {
    await api.delete(`/performance/scenarios/${row.id}`)
    ElMessage.success('场景已删除')
    fetchScenarios()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '删除失败')
  }
}
</script>
