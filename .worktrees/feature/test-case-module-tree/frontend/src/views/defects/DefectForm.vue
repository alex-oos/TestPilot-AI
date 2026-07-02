<template>
  <div class="w-full">
    <div class="flex items-center gap-3 mb-6">
      <el-button :icon="ArrowLeft" circle @click="router.back()" />
      <h1 class="text-2xl font-bold text-gray-900">{{ isEdit ? '编辑缺陷' : '创建缺陷' }}</h1>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6" v-loading="pageLoading">
      <!-- 左侧主内容 -->
      <div class="lg:col-span-3 space-y-5">
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
            <el-form-item label="缺陷标题" prop="title">
              <el-input v-model="form.title" placeholder="简要描述缺陷现象" size="large" />
            </el-form-item>

            <el-form-item label="缺陷内容" prop="description">
              <div class="editor-wrapper w-full border border-gray-200 rounded-lg overflow-hidden">
                <Toolbar :editor="editorRef" :defaultConfig="toolbarConfig" :mode="'default'" class="!border-b !border-gray-200" />
                <Editor v-model="form.description" :defaultConfig="editorConfig" :mode="'default'" class="editor-content" @onCreated="handleEditorCreated" />
              </div>
              <p class="text-xs text-gray-400 mt-1.5">支持粘贴/拖拽图片直接上传，可在内容中插入截图</p>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 右侧属性面板 -->
      <div class="space-y-5">
        <!-- 关联信息 -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="text-sm font-semibold text-gray-700 mb-4">关联信息</h3>
          <div class="space-y-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">关联需求</label>
              <el-select
                v-model="form.requirement_id"
                class="w-full"
                placeholder="选择关联需求"
                filterable
                clearable
                @change="onRequirementChange"
              >
                <el-option
                  v-for="req in requirements"
                  :key="req.id"
                  :label="`#${req.id} ${req.title}`"
                  :value="req.id"
                />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">指派人</label>
              <el-select v-model="form.assignee_id" class="w-full" placeholder="选择处理人" filterable clearable>
                <template v-if="reqMembers.length">
                  <el-option-group label="需求相关人员">
                    <el-option v-for="m in reqMembers" :key="m.id" :label="m.name" :value="m.id">
                      <span>{{ m.name }}</span>
                      <span class="text-gray-400 text-xs ml-2">{{ m.role }}</span>
                    </el-option>
                  </el-option-group>
                  <el-option-group label="其他人员">
                    <el-option v-for="emp in otherEmployees" :key="emp.id" :label="emp.name" :value="emp.id">
                      <span>{{ emp.name }}</span>
                      <span class="text-gray-400 text-xs ml-2">{{ emp.position }}</span>
                    </el-option>
                  </el-option-group>
                </template>
                <template v-else>
                  <el-option v-for="emp in employees" :key="emp.id" :label="emp.name" :value="emp.id">
                    <span>{{ emp.name }}</span>
                    <span class="text-gray-400 text-xs ml-2">{{ emp.position }}</span>
                  </el-option>
                </template>
              </el-select>
            </div>
          </div>
        </div>

        <!-- 基本属性 -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="text-sm font-semibold text-gray-700 mb-4">基本属性</h3>
          <div class="space-y-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">严重度</label>
              <el-select v-model="form.severity" class="w-full" placeholder="请选择">
                <el-option label="致命" value="critical" />
                <el-option label="严重" value="major" />
                <el-option label="一般" value="medium" />
                <el-option label="轻微" value="minor" />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">优先级</label>
              <el-select v-model="form.priority" class="w-full" placeholder="请选择">
                <el-option label="紧急" value="urgent" />
                <el-option label="高" value="high" />
                <el-option label="中" value="medium" />
                <el-option label="低" value="low" />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">状态</label>
              <el-select v-model="form.status" class="w-full" placeholder="请选择">
                <el-option label="待处理" value="open" />
                <el-option label="处理中" value="in_progress" />
                <el-option label="已修复" value="resolved" />
                <el-option label="已验证" value="verified" />
                <el-option label="已关闭" value="closed" />
                <el-option label="已拒绝" value="rejected" />
              </el-select>
            </div>
          </div>
        </div>

        <!-- 其他信息 -->
        <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h3 class="text-sm font-semibold text-gray-700 mb-4">其他信息</h3>
          <div class="space-y-4">
            <div>
              <label class="text-xs text-gray-500 mb-1 block">缺陷类型</label>
              <el-select v-model="form.defect_type" class="w-full" placeholder="请选择">
                <el-option label="功能缺陷" value="functional" />
                <el-option label="UI缺陷" value="ui" />
                <el-option label="性能缺陷" value="performance" />
                <el-option label="兼容性" value="compatibility" />
                <el-option label="安全漏洞" value="security" />
                <el-option label="其他" value="other" />
              </el-select>
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">所属模块</label>
              <el-input v-model="form.module" placeholder="输入模块名" />
            </div>
            <div>
              <label class="text-xs text-gray-500 mb-1 block">环境</label>
              <el-input v-model="form.environment" placeholder="如：Chrome 120 / iOS 17" />
            </div>
          </div>
        </div>

        <div class="flex gap-3">
          <el-button type="primary" color="#4f46e5" class="flex-1 !rounded-xl !h-10" :loading="submitting" @click="handleSubmit">
            {{ isEdit ? '保存修改' : '提交缺陷' }}
          </el-button>
          <el-button class="flex-1 !rounded-xl !h-10" @click="router.back()">取消</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, shallowRef, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import type { IDomEditor, IEditorConfig, IToolbarConfig } from '@wangeditor/editor'
import '@wangeditor/editor/dist/css/style.css'
import request from '../../utils/request'

const API_BASE = import.meta.env.VITE_DIRECT_BACKEND_API_BASE?.replace(/\/api$/, '') || 'http://localhost:8001'

interface Employee { id: number; name: string; position: string; department: string; role?: string }
interface ReqMember { id: number; name: string; role: string; node: string }
interface Requirement { id: number; title: string; project_id: number | null; status: string }

const route = useRoute()
const router = useRouter()
const defectId = route.params.id as string
const isEdit = computed(() => !!defectId)

const pageLoading = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const employees = ref<Employee[]>([])
const requirements = ref<Requirement[]>([])
const reqMembers = ref<ReqMember[]>([])

const reqMemberIds = computed(() => new Set(reqMembers.value.map(m => m.id)))
const otherEmployees = computed(() => employees.value.filter(e => !reqMemberIds.value.has(e.id)))

// ---- wangEditor ----
const editorRef = shallowRef<IDomEditor>()

const toolbarConfig: Partial<IToolbarConfig> = {
  toolbarKeys: [
    'undo', 'redo', '|',
    'headerSelect', 'bold', 'italic', 'underline', 'through', '|',
    'color', 'bgColor', '|',
    'bulletedList', 'numberedList', 'todo', '|',
    'justifyLeft', 'justifyCenter', 'justifyRight', '|',
    'insertLink',
    {
      key: 'group-image',
      title: '图片',
      iconSvg: '<svg viewBox="0 0 1024 1024"><path d="M959.877 128l0.123 0.123v767.775l-0.123 0.122H64.102l-0.122-0.122V128.123l0.122-0.123h895.775zM960 64H64C28.795 64 0 92.795 0 128v768c0 35.205 28.795 64 64 64h896c35.205 0 64-28.795 64-64V128c0-35.205-28.795-64-64-64zM832 288.01c0 53.023-42.988 96.01-96.01 96.01s-96.01-42.987-96.01-96.01S682.967 192 735.99 192 832 234.988 832 288.01zM896 832H128V704l224.01-384 256 320h64l224.01-192z"/></svg>',
      menuKeys: ['uploadImage', 'insertImage'],
    },
    '|',
    'insertTable', 'codeBlock', 'blockquote',
  ],
}

const editorConfig: Partial<IEditorConfig> = {
  placeholder: '请输入缺陷详细描述，包含复现步骤、期望结果和实际结果。\n可直接粘贴截图或拖拽图片上传…',
  MENU_CONF: {
    uploadImage: {
      maxFileSize: 20 * 1024 * 1024,
      maxNumberOfFiles: 20,
      allowedFileTypes: ['image/*'],
      compress: false,
      async customUpload(file: File, insertFn: (url: string, alt?: string, href?: string) => void) {
        const fd = new FormData()
        fd.append('file', file)
        try {
          const resp = await request.post('/defects/upload/image', fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
          const payload = resp.data
          const url = payload?.data?.url
          if (url) {
            const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`
            insertFn(fullUrl, file.name || 'image', '')
          } else {
            ElMessage.error('图片上传失败：服务器未返回 URL')
          }
        } catch (e: any) {
          ElMessage.error(`图片上传失败: ${e?.message || '未知错误'}`)
        }
      },
    },
  },
}

function handleEditorCreated(editor: IDomEditor) {
  editorRef.value = editor
}

onBeforeUnmount(() => {
  editorRef.value?.destroy()
})

// ---- form state ----
const form = reactive({
  title: '',
  description: '',
  severity: 'medium',
  priority: 'medium',
  status: 'open',
  defect_type: 'functional',
  module: '',
  environment: '',
  assignee_id: null as number | null,
  requirement_id: null as number | null,
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入缺陷标题', trigger: 'blur' }],
}

const NODE_LABELS: Record<string, string> = {
  requirement_review: '需求评审',
  tech_review: '技术评审',
  case_review: '用例评审',
  testing: '测试执行',
  acceptance: '验收测试',
  released: '发布上线',
  regression: '线上回归',
}

async function onRequirementChange(reqId: number | null) {
  reqMembers.value = []
  if (!reqId) return

  try {
    const { data } = await request.get(`/requirements/${reqId}/node-members`)
    const list = data?.data ?? data ?? []
    const seen = new Set<number>()
    const members: ReqMember[] = []
    for (const m of list) {
      const emp = m.employee
      if (!emp || seen.has(emp.id)) continue
      seen.add(emp.id)
      members.push({
        id: emp.id,
        name: emp.name,
        role: `${NODE_LABELS[m.node] || m.node} · ${m.role}`,
        node: m.node,
      })
    }
    reqMembers.value = members
  } catch { /* ignore */ }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = { ...form }
    if (isEdit.value) {
      await request.put(`/defects/${defectId}`, payload)
      ElMessage.success('缺陷已更新')
    } else {
      await request.post('/defects', payload)
      ElMessage.success('缺陷已创建')
    }
    router.push('/defects')
  } catch (e: any) {
    ElMessage.error(e?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function fetchDefect() {
  if (!defectId) return
  pageLoading.value = true
  try {
    const { data } = await request.get(`/defects/${defectId}`)
    const d = data?.data ?? data
    form.title = d.title || ''
    form.description = d.description || ''
    form.severity = d.severity || 'medium'
    form.priority = d.priority || 'medium'
    form.status = d.status || 'open'
    form.defect_type = d.defect_type || 'functional'
    form.module = d.module || ''
    form.environment = d.environment || ''
    form.assignee_id = d.assignee_id || null
    form.requirement_id = d.requirement_id || null
    if (form.requirement_id) {
      await onRequirementChange(form.requirement_id)
    }
  } catch {
    ElMessage.error('加载缺陷数据失败')
  } finally {
    pageLoading.value = false
  }
}

async function fetchEmployees() {
  try {
    const { data } = await request.get('/hr/employees', { params: { page_size: 200 } })
    employees.value = data?.data?.items ?? data?.items ?? []
  } catch { /* ignore */ }
}

async function fetchRequirements() {
  try {
    const { data } = await request.get('/requirements', { params: { page_size: 200 } })
    requirements.value = data?.data?.items ?? data?.items ?? []
  } catch { /* ignore */ }
}

onMounted(() => {
  fetchEmployees()
  fetchRequirements()
  if (isEdit.value) fetchDefect()
})
</script>

<style scoped>
.editor-wrapper {
  --w-e-toolbar-bg-color: #f9fafb;
  --w-e-toolbar-border-color: #e5e7eb;
}

.editor-content {
  height: 500px !important;
  overflow-y: hidden;
}

:deep(.w-e-toolbar) {
  border-bottom: 1px solid #e5e7eb !important;
}

:deep(.w-e-text-container) {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
  height: 500px !important;
}

:deep(.w-e-scroll) {
  height: 100% !important;
  overflow-y: auto !important;
}

:deep(.w-e-text-placeholder) {
  font-style: normal;
  color: #9ca3af;
  white-space: pre-wrap;
}
</style>
