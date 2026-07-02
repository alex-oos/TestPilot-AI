<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">👥 人力管理</h1>
        <p class="text-gray-500">管理团队人员，包含层级（组长/成员）和职能角色（产品/开发/测试）。</p>
      </div>
      <div class="flex gap-2">
        <el-button color="#0ea5e9" class="!rounded-xl" @click="openSyncDialog">🔄 从平台同步</el-button>
        <el-button type="primary" color="#4f46e5" class="!rounded-xl" @click="openDialog()">+ 新增员工</el-button>
      </div>
    </div>

    <!-- 角色概览卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
      <div class="bg-white rounded-xl border border-gray-100 shadow-sm p-4 text-center">
        <div class="text-2xl font-bold text-gray-800">{{ tableData.length }}</div>
        <div class="text-xs text-gray-400 mt-1">全部人员</div>
      </div>
      <div class="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl border border-amber-100 p-4 text-center">
        <div class="text-2xl font-bold text-amber-600">{{ countByLevel('leader') }}</div>
        <div class="text-xs text-amber-500 mt-1">👑 组长</div>
      </div>
      <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100 p-4 text-center">
        <div class="text-2xl font-bold text-blue-600">{{ countByRole('product') }}</div>
        <div class="text-xs text-blue-500 mt-1">📋 产品</div>
      </div>
      <div class="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl border border-green-100 p-4 text-center">
        <div class="text-2xl font-bold text-green-600">{{ countByRole('developer') }}</div>
        <div class="text-xs text-green-500 mt-1">💻 开发</div>
      </div>
      <div class="bg-gradient-to-br from-purple-50 to-violet-50 rounded-xl border border-purple-100 p-4 text-center">
        <div class="text-2xl font-bold text-purple-600">{{ countByRole('tester') }}</div>
        <div class="text-xs text-purple-500 mt-1">🧪 测试</div>
      </div>
      <div class="bg-gradient-to-br from-cyan-50 to-sky-50 rounded-xl border border-cyan-100 p-4 text-center">
        <div class="text-2xl font-bold text-cyan-600">{{ countCanLogin }}</div>
        <div class="text-xs text-cyan-500 mt-1">🔑 可登录</div>
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
      <div class="grid grid-cols-1 md:grid-cols-6 gap-3 mb-4">
        <el-input v-model="query.keyword" clearable placeholder="搜索姓名 / 邮箱" @keyup.enter="fetchList" />
        <el-select v-model="query.role" clearable placeholder="职能角色" @change="fetchList">
          <el-option label="产品" value="product" />
          <el-option label="开发" value="developer" />
          <el-option label="测试" value="tester" />
        </el-select>
        <el-select v-model="query.level" clearable placeholder="层级" @change="fetchList">
          <el-option label="组长" value="leader" />
          <el-option label="成员" value="member" />
        </el-select>
        <el-select v-model="query.status" clearable placeholder="状态" @change="fetchList">
          <el-option label="在职" value="active" />
          <el-option label="离职" value="inactive" />
          <el-option label="试用期" value="probation" />
        </el-select>
        <el-select v-model="query.loginFilter" clearable placeholder="登录状态" @change="fetchList">
          <el-option label="可登录" value="yes" />
          <el-option label="未开通" value="no" />
        </el-select>
        <div class="flex gap-2">
          <el-button @click="handleReset">重置</el-button>
          <el-button type="primary" color="#4f46e5" @click="fetchList">查询</el-button>
        </div>
      </div>

      <el-table :data="filteredData" v-loading="loading" empty-text="暂无员工数据">
        <el-table-column prop="name" label="姓名" min-width="130">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-full text-white text-[11px] flex items-center justify-center font-bold shrink-0"
                :style="{ background: strToColor(row.name) }">{{ (row.name || '?')[0] }}</div>
              <div>
                <div class="font-medium text-gray-800">{{ row.name }}</div>
                <div v-if="row.level === 'leader'" class="text-[10px] text-amber-500">👑 组长</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="职能角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="roleTagType(row.role)" size="small" effect="light" round>{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="层级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.level === 'leader' ? 'warning' : 'info'" size="small" effect="plain" round>
              {{ row.level === 'leader' ? '组长' : '成员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="170" show-overflow-tooltip />
        <el-table-column prop="position" label="职位" min-width="120" show-overflow-tooltip />
        <el-table-column label="来源" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.sync_source" size="small" effect="plain" round :type="syncSourceType(row.sync_source)">
              {{ syncSourceLabel(row.sync_source) }}
            </el-tag>
            <span v-else class="text-gray-300 text-xs">手动</span>
          </template>
        </el-table-column>
        <el-table-column label="登录状态" width="130" align="center">
          <template #default="{ row }">
            <div v-if="row.can_login" class="flex items-center justify-center gap-1">
              <span class="w-2 h-2 rounded-full bg-green-400 inline-block"></span>
              <span class="text-green-600 text-xs font-medium">可登录</span>
              <el-popconfirm title="确认禁用该员工的平台登录？" @confirm="handleDisableLogin(row)">
                <template #reference>
                  <el-button link type="danger" size="small" class="!ml-1" @click.stop>禁用</el-button>
                </template>
              </el-popconfirm>
            </div>
            <div v-else>
              <el-button link type="primary" size="small" @click.stop="handleEnableLogin(row)">
                🔑 开通登录
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light" round size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除该员工？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button link type="danger" size="small" @click.stop>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-4">
        <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" :total="total"
          :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" background @size-change="fetchList" @current-change="fetchList" />
      </div>
    </div>

    <!-- 新增/编辑员工 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑员工' : '新增员工'" width="580px" destroy-on-close class="!rounded-2xl">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" label-position="right">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="职能角色" prop="role">
            <el-select v-model="form.role" class="w-full" placeholder="选择职能角色">
              <el-option label="产品" value="product" />
              <el-option label="开发" value="developer" />
              <el-option label="测试" value="tester" />
            </el-select>
          </el-form-item>
          <el-form-item label="层级" prop="level">
            <el-select v-model="form.level" class="w-full" placeholder="选择层级">
              <el-option label="组长" value="leader" />
              <el-option label="成员" value="member" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="职位">
          <el-input v-model="form.position" placeholder="如：高级开发工程师" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="部门">
            <el-select v-model="form.department" placeholder="选择部门" class="w-full">
              <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
            </el-select>
          </el-form-item>
          <el-form-item label="团队">
            <el-select v-model="form.team_id" placeholder="选择团队" clearable class="w-full">
              <el-option v-for="t in teamList" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </el-form-item>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="入职日期">
            <el-date-picker v-model="form.hire_date" type="date" value-format="YYYY-MM-DD" class="!w-full" />
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-select v-model="form.status" class="w-full">
              <el-option label="在职" value="active" />
              <el-option label="离职" value="inactive" />
              <el-option label="试用期" value="probation" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 同步对话框 -->
    <el-dialog v-model="syncDialogVisible" title="🔄 从平台同步人员" width="720px" destroy-on-close class="!rounded-2xl">
      <!-- Step 1: 选择平台 -->
      <div v-if="syncStep === 1" class="space-y-4">
        <p class="text-gray-500 text-sm">选择要同步的平台，一键导入人员数据到本系统。</p>
        <div class="grid grid-cols-3 gap-4">
          <div v-for="p in syncPlatforms" :key="p.key"
            class="border-2 rounded-xl p-5 text-center cursor-pointer transition-all hover:shadow-md"
            :class="syncSelectedPlatform === p.key ? 'border-sky-400 bg-sky-50 shadow-md' : 'border-gray-200 hover:border-sky-200'"
            @click="syncSelectedPlatform = p.key">
            <div class="text-3xl mb-2">{{ platformIcon(p.key) }}</div>
            <div class="font-bold text-gray-800">{{ p.name }}</div>
            <div class="text-xs text-gray-400 mt-1">{{ p.user_count }} 人</div>
            <div v-if="syncSelectedPlatform === p.key"
              class="mt-2 text-xs text-sky-500 font-medium">✓ 已选择</div>
          </div>
        </div>
      </div>

      <!-- Step 2: 预览并选择导入人员 -->
      <div v-if="syncStep === 2" class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-gray-500 text-sm">从 </span>
            <el-tag effect="dark" round size="small" color="#0ea5e9">{{ platformIcon(syncSelectedPlatform) }} {{ syncPlatformName }}</el-tag>
            <span class="text-gray-500 text-sm"> 获取到 {{ syncUsers.length }} 人</span>
          </div>
          <el-checkbox v-model="syncSelectAll" :indeterminate="syncIndeterminate" @change="handleSyncSelectAll">全选</el-checkbox>
        </div>
        <div class="max-h-[400px] overflow-y-auto space-y-2 pr-1">
          <div v-for="u in syncUsers" :key="u.email"
            class="flex items-center gap-3 p-3 rounded-xl border transition-all"
            :class="u.already_exists ? 'border-gray-100 bg-gray-50 opacity-60' : (u._selected ? 'border-sky-200 bg-sky-50/50' : 'border-gray-200 hover:border-sky-100')">
            <el-checkbox v-model="u._selected" :disabled="u.already_exists" />
            <div class="w-8 h-8 rounded-full text-white text-xs flex items-center justify-center font-bold shrink-0"
              :style="{ background: strToColor(u.name) }">{{ (u.name || '?')[0] }}</div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-medium text-gray-800">{{ u.name }}</span>
                <el-tag size="small" :type="roleTagType(u.role)" effect="light" round>{{ roleLabel(u.role) }}</el-tag>
              </div>
              <div class="text-xs text-gray-400 truncate">{{ u.email }} · {{ u.position }} · {{ u.department }}</div>
            </div>
            <div>
              <el-tag v-if="u.already_exists" type="info" size="small" effect="plain" round>已存在</el-tag>
            </div>
          </div>
        </div>
        <div v-if="syncUsers.length === 0" class="text-center py-8 text-gray-400">暂无人员数据</div>
      </div>

      <!-- Step 3: 导入结果 -->
      <div v-if="syncStep === 3" class="text-center py-6 space-y-4">
        <div class="text-5xl">🎉</div>
        <div class="text-xl font-bold text-gray-800">同步完成!</div>
        <div class="flex justify-center gap-6 mt-4">
          <div class="bg-green-50 rounded-xl px-6 py-3 border border-green-100">
            <div class="text-2xl font-bold text-green-600">{{ syncResult.imported }}</div>
            <div class="text-xs text-green-500">成功导入</div>
          </div>
          <div class="bg-gray-50 rounded-xl px-6 py-3 border border-gray-200">
            <div class="text-2xl font-bold text-gray-500">{{ syncResult.skipped }}</div>
            <div class="text-xs text-gray-400">已跳过</div>
          </div>
        </div>
        <div v-if="syncResult.imported_names?.length" class="mt-3">
          <div class="text-xs text-gray-400 mb-1">已导入人员:</div>
          <div class="flex flex-wrap gap-1 justify-center">
            <el-tag v-for="n in syncResult.imported_names" :key="n" size="small" effect="light" round type="success">{{ n }}</el-tag>
          </div>
        </div>
        <p class="text-sm text-gray-400 mt-4">
          导入的员工默认登录密码为 <code class="bg-gray-100 px-2 py-0.5 rounded text-gray-600 font-mono">123456</code>
          ，可在列表中单独「开通登录」。
        </p>
      </div>

      <template #footer>
        <div class="flex justify-between w-full">
          <div>
            <el-button v-if="syncStep > 1 && syncStep < 3" @click="syncStep--">← 上一步</el-button>
          </div>
          <div class="flex gap-2">
            <el-button @click="syncDialogVisible = false">{{ syncStep === 3 ? '关闭' : '取消' }}</el-button>
            <el-button v-if="syncStep === 1" type="primary" color="#0ea5e9" :disabled="!syncSelectedPlatform" :loading="syncLoading"
              @click="handleSyncFetch">下一步 →</el-button>
            <el-button v-if="syncStep === 2" type="primary" color="#0ea5e9" :disabled="syncSelectedCount === 0" :loading="syncLoading"
              @click="handleSyncImport">导入 {{ syncSelectedCount }} 人</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 开通登录结果 -->
    <el-dialog v-model="loginResultVisible" title="🔑 账号开通成功" width="420px" class="!rounded-2xl">
      <div class="text-center py-4 space-y-3">
        <div class="text-4xl">✅</div>
        <div class="text-lg font-bold text-gray-800">{{ loginResultData.username }} 的平台账号已开通</div>
        <div class="bg-blue-50 rounded-xl p-4 border border-blue-100 space-y-2 text-left">
          <div class="flex justify-between">
            <span class="text-gray-500 text-sm">登录账号:</span>
            <code class="bg-white px-2 py-0.5 rounded text-blue-600 font-mono text-sm border">{{ loginResultData.username }}</code>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500 text-sm">初始密码:</span>
            <code class="bg-white px-2 py-0.5 rounded text-blue-600 font-mono text-sm border">{{ loginResultData.default_password }}</code>
          </div>
        </div>
        <p class="text-xs text-gray-400">请通知该员工使用以上账号密码登录平台</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="loginResultVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import request from '../../utils/request'

interface Employee {
  id: number; name: string; email: string; phone: string; position: string
  department: string; team_id?: number; role: string; level: string
  hire_date: string; status: string; user_id?: number; can_login?: boolean
  sync_source?: string; sync_id?: string
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const tableData = ref<Employee[]>([])
const total = ref(0)
const formRef = ref<FormInstance>()
const teamList = ref<any[]>([])

const departments = ['工程部', '测试部', '产品部', '设计部', '运维部', '市场部']

const query = reactive({ keyword: '', role: '', level: '', status: '', loginFilter: '', page: 1, page_size: 20 })

const defaultForm = (): Partial<Employee> & { id?: number } => ({
  name: '', email: '', phone: '', position: '', department: '', team_id: undefined,
  role: 'developer', level: 'member', hire_date: '', status: 'active',
})
const form = reactive<Partial<Employee> & { id?: number }>(defaultForm())

const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  role: [{ required: true, message: '请选择职能角色', trigger: 'change' }],
  level: [{ required: true, message: '请选择层级', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const filteredData = computed(() => {
  let data = [...tableData.value]
  if (query.keyword) {
    const kw = query.keyword.toLowerCase()
    data = data.filter(e => e.name?.toLowerCase().includes(kw) || e.email?.toLowerCase().includes(kw))
  }
  if (query.role) data = data.filter(e => e.role === query.role)
  if (query.level) data = data.filter(e => e.level === query.level)
  if (query.status) data = data.filter(e => e.status === query.status)
  if (query.loginFilter === 'yes') data = data.filter(e => e.can_login)
  if (query.loginFilter === 'no') data = data.filter(e => !e.can_login)
  return data
})

const countCanLogin = computed(() => tableData.value.filter(e => e.can_login).length)

function countByRole(role: string) { return tableData.value.filter(e => e.role === role).length }
function countByLevel(level: string) { return tableData.value.filter(e => e.level === level).length }

function roleLabel(r: string) { return { product: '产品', developer: '开发', tester: '测试' }[r] || r }
function roleTagType(r: string) { return ({ product: '', developer: 'success', tester: 'warning' } as any)[r] || 'info' }
function statusType(s: string) { return ({ active: 'success', inactive: 'info', probation: 'warning' } as any)[s] || 'info' }
function statusLabel(s: string) { return { active: '在职', inactive: '离职', probation: '试用期' }[s] || s }

function syncSourceLabel(s: string) { return { feishu: '飞书', dingtalk: '钉钉', wecom: '企微' }[s] || s }
function syncSourceType(s: string) { return ({ feishu: 'primary', dingtalk: 'success', wecom: 'warning' } as any)[s] || 'info' }
function platformIcon(key: string) { return { feishu: '🐦', dingtalk: '💬', wecom: '💼' }[key] || '🔗' }

function strToColor(str: string) {
  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#0ea5e9', '#14b8a6', '#22c55e']
  let hash = 0; for (let i = 0; i < (str || '').length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

async function fetchList() {
  loading.value = true
  try {
    const { data } = await request.get('/hr/employees', { params: { page: query.page, page_size: query.page_size } })
    const payload = data?.data ?? data
    tableData.value = payload?.items ?? payload?.list ?? (Array.isArray(payload) ? payload : [])
    total.value = payload?.total ?? tableData.value.length
  } catch { ElMessage.error('加载员工列表失败') }
  finally { loading.value = false }
}

async function fetchTeams() {
  try { const resp = await request.get('/hr/teams'); teamList.value = resp.data?.data || resp.data || [] } catch {}
}

function handleReset() {
  query.keyword = ''; query.role = ''; query.level = ''; query.status = ''; query.loginFilter = ''; query.page = 1
  fetchList()
}

function openDialog(row?: Employee) {
  isEdit.value = !!row
  Object.assign(form, row ? { ...row } : { ...defaultForm(), id: undefined })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true
  try {
    if (isEdit.value && form.id) {
      await request.put(`/hr/employees/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/hr/employees', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } catch { ElMessage.error('操作失败') }
  finally { submitting.value = false }
}

async function handleDelete(id: number) {
  try { await request.delete(`/hr/employees/${id}`); ElMessage.success('删除成功'); fetchList() }
  catch { ElMessage.error('删除失败') }
}

// ---- 登录管理 ----
const loginResultVisible = ref(false)
const loginResultData = ref<any>({})

async function handleEnableLogin(row: Employee) {
  try {
    await ElMessageBox.confirm(
      `确认为「${row.name}」开通平台登录账号？\n账号将使用邮箱作为用户名，初始密码为 123456。`,
      '开通登录', { confirmButtonText: '确认开通', type: 'info' }
    )
    const { data } = await request.post(`/hr/sync/enable-login/${row.id}`)
    const result = data?.data ?? data
    loginResultData.value = result
    loginResultVisible.value = true
    fetchList()
  } catch {}
}

async function handleDisableLogin(row: Employee) {
  try {
    await request.post(`/hr/sync/disable-login/${row.id}`)
    ElMessage.success(`已禁用 ${row.name} 的登录权限`)
    fetchList()
  } catch { ElMessage.error('操作失败') }
}

// ---- 平台同步 ----
const syncDialogVisible = ref(false)
const syncStep = ref(1)
const syncLoading = ref(false)
const syncPlatforms = ref<any[]>([])
const syncSelectedPlatform = ref('')
const syncPlatformName = ref('')
const syncUsers = ref<any[]>([])
const syncResult = ref<any>({})

const syncSelectAll = ref(false)
const syncIndeterminate = computed(() => {
  const selectable = syncUsers.value.filter(u => !u.already_exists)
  const selected = selectable.filter(u => u._selected)
  return selected.length > 0 && selected.length < selectable.length
})
const syncSelectedCount = computed(() => syncUsers.value.filter(u => u._selected && !u.already_exists).length)

function handleSyncSelectAll(val: any) {
  syncUsers.value.forEach(u => { if (!u.already_exists) u._selected = val })
}

async function openSyncDialog() {
  syncStep.value = 1
  syncSelectedPlatform.value = ''
  syncUsers.value = []
  syncResult.value = {}
  syncDialogVisible.value = true

  try {
    const { data } = await request.get('/hr/sync/platforms')
    syncPlatforms.value = data?.data ?? data ?? []
  } catch { ElMessage.error('加载平台列表失败') }
}

async function handleSyncFetch() {
  if (!syncSelectedPlatform.value) return
  syncLoading.value = true
  try {
    const { data } = await request.post('/hr/sync/fetch', { platform: syncSelectedPlatform.value })
    const result = data?.data ?? data
    syncPlatformName.value = result.platform_name
    syncUsers.value = (result.users || []).map((u: any) => ({ ...u, _selected: !u.already_exists }))
    syncSelectAll.value = syncUsers.value.filter(u => !u.already_exists).every(u => u._selected)
    syncStep.value = 2
  } catch { ElMessage.error('获取平台人员数据失败') }
  finally { syncLoading.value = false }
}

async function handleSyncImport() {
  const selected = syncUsers.value.filter(u => u._selected && !u.already_exists)
  if (!selected.length) return
  syncLoading.value = true
  try {
    const { data } = await request.post('/hr/sync/import', {
      platform: syncSelectedPlatform.value,
      users: selected,
    })
    syncResult.value = data?.data ?? data
    syncStep.value = 3
    fetchList()
  } catch { ElMessage.error('导入失败') }
  finally { syncLoading.value = false }
}

onMounted(() => { fetchList(); fetchTeams() })
</script>
