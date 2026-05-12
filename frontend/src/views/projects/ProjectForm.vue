<template>
  <div class="h-full flex flex-col -m-8">
    <!-- 顶栏 -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3">
        <el-button text @click="goBack">
          <el-icon class="mr-1"><ArrowLeft /></el-icon>返回
        </el-button>
        <h1 class="text-lg font-bold text-gray-900">📝 新建项目</h1>
      </div>
    </div>

    <!-- 表单内容 -->
    <div class="flex-1 overflow-auto bg-gray-50 p-6">
      <div class="max-w-2xl mx-auto">
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="100px"
            label-position="top"
            size="large"
          >
            <el-form-item label="项目名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入项目名称" maxlength="100" show-word-limit />
            </el-form-item>

            <el-form-item label="项目描述" prop="description">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="4"
                placeholder="请输入项目描述（可选）"
                maxlength="500"
                show-word-limit
              />
            </el-form-item>

            <div class="grid grid-cols-2 gap-6">
              <el-form-item label="状态" prop="status">
                <el-select v-model="form.status" class="!w-full">
                  <el-option v-for="opt in statusOptions" :key="opt.value" :label="opt.label" :value="opt.value">
                    <div class="flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full" :style="{ background: opt.color }"></span>
                      <span>{{ opt.label }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="负责人" prop="owner_id">
                <el-select
                  v-model="form.owner_id"
                  class="!w-full"
                  filterable
                  clearable
                  placeholder="选择负责人"
                >
                  <el-option v-for="emp in employeeOptions" :key="emp.id" :label="emp.name" :value="emp.id">
                    <div class="flex items-center justify-between w-full">
                      <span>{{ emp.name }}</span>
                      <span class="text-xs text-gray-400 ml-2">{{ emp.position || '' }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
            </div>

            <div class="flex justify-end gap-3 mt-8 pt-6 border-t border-gray-100">
              <el-button size="large" @click="goBack">取消</el-button>
              <el-button type="primary" size="large" color="#4f46e5" :loading="submitting" @click="handleSubmit">
                创建项目
              </el-button>
            </div>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { useUserStore } from '../../stores/user'
import request from '../../utils/request'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const employeeOptions = ref<any[]>([])

const statusOptions = [
  { value: 'draft', label: '草稿', color: '#94a3b8' },
  { value: 'approved', label: '已立项', color: '#f59e0b' },
  { value: 'active', label: '进行中', color: '#22c55e' },
  { value: 'archived', label: '已归档', color: '#6b7280' },
]

const form = reactive({
  name: '',
  description: '',
  status: 'draft',
  owner_id: null as number | null,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

async function fetchEmployees() {
  try {
    const resp = await request.get('/hr/employees')
    employeeOptions.value = resp.data?.data || []
  } catch {}
}

function setDefaultOwner() {
  const empId = userStore.employeeId
  if (empId) {
    form.owner_id = empId
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await request.post('/projects', {
      name: form.name,
      description: form.description,
      status: form.status,
      owner_id: form.owner_id,
    })
    ElMessage.success('项目创建成功')
    router.push('/projects')
  } catch {
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}

function goBack() {
  router.push('/projects')
}

onMounted(async () => {
  await fetchEmployees()
  setDefaultOwner()
})
</script>
