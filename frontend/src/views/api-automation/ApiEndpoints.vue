<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">接口管理</h1>
        <p class="text-gray-500">管理项目中的 API 接口定义，支持增删改查操作。</p>
      </div>
      <el-button type="primary" color="#4f46e5" class="!rounded-xl" @click="openDialog()">
        + 新增接口
      </el-button>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div class="flex items-center gap-3 mb-4">
        <el-select v-model="filterMethod" clearable placeholder="HTTP 方法筛选" class="w-48" @change="fetchEndpoints">
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
          <el-option label="DELETE" value="DELETE" />
        </el-select>
        <el-input v-model="searchKeyword" clearable placeholder="搜索接口名称或路径" class="w-72" @keyup.enter="fetchEndpoints" />
        <el-button type="primary" color="#4f46e5" @click="fetchEndpoints">查询</el-button>
      </div>

      <el-table :data="filteredEndpoints" v-loading="loading" empty-text="暂无接口数据" stripe>
        <el-table-column prop="name" label="接口名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="请求方法" width="120" align="center">
          <template #default="{ row }">
            <el-tag :color="methodColor(row.method)" effect="dark" class="!border-0 !text-white font-semibold" round>
              {{ row.method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="text-sm text-slate-600 bg-slate-50 px-2 py-0.5 rounded">{{ row.path }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :page-sizes="[10, 20, 50]"
          :total="total"
          @current-change="fetchEndpoints"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑接口' : '新增接口'"
      width="600px"
      destroy-on-close
      class="!rounded-2xl"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="top">
        <el-form-item label="接口名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：获取用户列表" />
        </el-form-item>
        <el-form-item label="请求方法" prop="method">
          <el-select v-model="form.method" placeholder="选择 HTTP 方法" class="w-full">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
            <el-option label="PATCH" value="PATCH" />
          </el-select>
        </el-form-item>
        <el-form-item label="请求路径" prop="path">
          <el-input v-model="form.path" placeholder="例如：/api/users" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="接口功能描述" />
        </el-form-item>
        <el-form-item label="请求头">
          <el-input
            v-model="form.headers"
            type="textarea"
            :rows="3"
            placeholder='JSON 格式，例如：{"Content-Type": "application/json"}'
          />
        </el-form-item>
        <el-form-item label="请求体">
          <el-input
            v-model="form.body"
            type="textarea"
            :rows="4"
            placeholder='JSON 格式，例如：{"name": "test"}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '确认新增' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '../../utils/request'

interface Endpoint {
  id: string
  name: string
  method: string
  path: string
  description: string
  headers: string
  body: string
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')

const endpoints = ref<Endpoint[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const filterMethod = ref('')
const searchKeyword = ref('')

const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  method: 'GET',
  path: '',
  description: '',
  headers: '',
  body: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入接口名称', trigger: 'blur' }],
  method: [{ required: true, message: '请选择请求方法', trigger: 'change' }],
  path: [{ required: true, message: '请输入请求路径', trigger: 'blur' }],
}

const filteredEndpoints = computed(() => {
  let list = endpoints.value
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    list = list.filter(
      (e) => e.name.toLowerCase().includes(kw) || e.path.toLowerCase().includes(kw)
    )
  }
  return list
})

onMounted(() => {
  fetchEndpoints()
})

async function fetchEndpoints() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filterMethod.value) params.method = filterMethod.value
    const resp = await api.get('/api-automation/endpoints', { params })
    const data = resp.data?.data || resp.data || {}
    endpoints.value = data.items || data || []
    total.value = data.total || endpoints.value.length
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '加载接口列表失败')
  } finally {
    loading.value = false
  }
}

function handleSizeChange() {
  page.value = 1
  fetchEndpoints()
}

function methodColor(method: string): string {
  const colors: Record<string, string> = {
    GET: '#10b981',
    POST: '#3b82f6',
    PUT: '#f59e0b',
    DELETE: '#ef4444',
    PATCH: '#8b5cf6',
  }
  return colors[method] || '#6b7280'
}

function openDialog(row?: Endpoint) {
  if (row) {
    isEdit.value = true
    editingId.value = row.id
    form.name = row.name
    form.method = row.method
    form.path = row.path
    form.description = row.description || ''
    form.headers = row.headers || ''
    form.body = row.body || ''
  } else {
    isEdit.value = false
    editingId.value = ''
    form.name = ''
    form.method = 'GET'
    form.path = ''
    form.description = ''
    form.headers = ''
    form.body = ''
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
      await api.put(`/api-automation/endpoints/${editingId.value}`, payload)
      ElMessage.success('接口已更新')
    } else {
      await api.post('/api-automation/endpoints', payload)
      ElMessage.success('接口已创建')
    }
    dialogVisible.value = false
    fetchEndpoints()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Endpoint) {
  const confirmed = await ElMessageBox.confirm(
    `确认删除接口「${row.name}」吗？删除后不可恢复。`,
    '提示',
    { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  ).catch(() => false)
  if (!confirmed) return

  try {
    await api.delete(`/api-automation/endpoints/${row.id}`)
    ElMessage.success('接口已删除')
    if (endpoints.value.length === 1 && page.value > 1) page.value -= 1
    fetchEndpoints()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || e?.message || '删除失败')
  }
}
</script>
