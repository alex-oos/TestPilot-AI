<template>
  <div class="h-full flex flex-col -m-8">
    <!-- 顶栏 -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-3">
        <el-button text @click="router.push('/requirements')" class="!px-2">
          <span class="text-lg">←</span>
        </el-button>
        <h1 class="text-lg font-bold text-gray-900">📝 {{ requirement?.title || '需求详情' }}</h1>
        <el-tag v-if="requirement" :type="priorityType(requirement.priority)" size="small" effect="light" round>
          {{ priorityLabel(requirement.priority) }}
        </el-tag>
      </div>
      <div class="flex items-center gap-2">
        <el-tag v-if="requirement" size="small" effect="dark" round
          :style="{ background: currentStageColor, borderColor: currentStageColor }">
          {{ currentStageLabel }}
        </el-tag>
      </div>
    </div>

    <!-- 流程节点时间线 -->
    <div v-if="requirement" class="flex-1 overflow-y-auto bg-gray-50">
      <!-- 横向时间线进度条 -->
      <div class="bg-white border-b border-gray-100 px-8 py-5">
        <div class="flex items-center justify-between relative max-w-5xl mx-auto">
          <div class="absolute top-4 left-8 right-8 h-[3px] bg-gray-200 z-0 rounded-full"></div>
          <div class="absolute top-4 left-8 h-[3px] bg-gradient-to-r from-indigo-500 to-purple-500 z-[1] rounded-full transition-all duration-500"
            :style="{ width: progressWidth }"></div>
          <div v-for="(node, idx) in nodes" :key="node.value"
            class="relative z-10 flex flex-col items-center cursor-pointer group"
            style="width: 100px"
            @click="scrollToNode(node.value)">
            <div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all"
              :class="nodeCircleClass(node.value)">
              <span v-if="isNodeDone(node.value)">✓</span>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <span class="text-[10px] mt-1.5 text-center leading-tight font-medium"
              :class="isNodeReached(node.value) ? 'text-gray-800' : 'text-gray-400'">
              {{ node.label }}
            </span>
          </div>
        </div>
      </div>

      <!-- 节点卡片区域 -->
      <div class="max-w-5xl mx-auto px-8 py-6 space-y-5">
        <div v-for="(node, idx) in nodes" :key="node.value"
          :ref="(el: any) => { if (el) nodeRefs[node.value] = el }"
          class="bg-white rounded-2xl border shadow-sm overflow-hidden transition-all"
          :class="requirement.status === node.value
            ? 'border-indigo-300 ring-2 ring-indigo-100'
            : isNodeDone(node.value) ? 'border-green-200' : 'border-gray-100 opacity-75'">

          <!-- 节点头部 -->
          <div class="flex items-center justify-between px-5 py-3 border-b"
            :class="requirement.status === node.value ? 'bg-indigo-50 border-indigo-100' : isNodeDone(node.value) ? 'bg-green-50 border-green-100' : 'bg-gray-50 border-gray-100'">
            <div class="flex items-center gap-3">
              <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                :style="{ background: node.color + '20', color: node.color }">
                {{ idx + 1 }}
              </div>
              <span class="font-semibold text-gray-800">{{ node.label }}</span>
              <span v-if="requirement.status === node.value"
                class="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">当前阶段</span>
              <span v-else-if="isNodeDone(node.value)"
                class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">✓ 已完成</span>
            </div>
            <div class="flex items-center gap-2">
              <el-button size="small" plain @click="jumpToScheduleForNode(node.value)"
                v-if="getNodeMembers(node.value).length > 0">
                📅 排期
              </el-button>
              <el-button size="small" plain @click="openEditDialog(node.value)">
                ✏️ 编辑人员
              </el-button>
              <el-button v-if="requirement.status === node.value && nextNode(node.value)"
                type="primary" color="#4f46e5" size="small"
                @click="advanceToNode(nextNode(node.value)!)">
                推进到 {{ nextNodeLabel(node.value) }} →
              </el-button>
            </div>
          </div>

          <!-- 节点人员内容 -->
          <div class="px-5 py-4">
            <div v-if="getNodeMembers(node.value).length === 0"
              class="text-center py-6 text-gray-400 text-sm">
              <span class="text-2xl block mb-2">👤</span>
              暂未分配人员，点击「编辑人员」添加
            </div>
            <div v-else class="space-y-3">
              <!-- 按角色分组 -->
              <div v-for="role in displayRoles" :key="role.value" class="flex items-start gap-3">
                <div class="w-20 shrink-0 text-right">
                  <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg"
                    :style="{ background: role.bg, color: role.color }">
                    {{ role.icon }} {{ role.label }}
                  </span>
                </div>
                <div class="flex-1 flex flex-wrap gap-2 min-h-[32px] items-center">
                  <template v-for="member in getNodeRoleMembers(node.value, role.value)" :key="member.id">
                    <div class="inline-flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1 text-sm">
                      <div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
                        :style="{ background: role.color }">
                        {{ member.employee?.name?.charAt(0) || '?' }}
                      </div>
                      <span class="text-gray-700">{{ member.employee?.name || '未知' }}</span>
                    </div>
                  </template>
                  <span v-if="getNodeRoleMembers(node.value, role.value).length === 0"
                    class="text-xs text-gray-300">--</span>
                </div>
              </div>

              <!-- 时间 -->
              <div class="flex items-center gap-3 pt-2 border-t border-gray-100">
                <div class="w-20 shrink-0 text-right">
                  <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg bg-slate-100 text-slate-600">
                    🕐 时间
                  </span>
                </div>
                <div class="flex-1 text-sm text-gray-600">
                  {{ getNodeTime(node.value) || '--' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex-1 flex items-center justify-center">
      <el-empty description="加载中..." />
    </div>

    <!-- 编辑人员弹窗 -->
    <el-dialog v-model="editDialogVisible"
      :title="`编辑节点人员 - ${editingNodeLabel}`"
      width="680px" destroy-on-close>
      <div class="space-y-4">
        <!-- 时间设置 -->
        <div class="flex items-center gap-3 pb-3 border-b border-gray-100">
          <span class="text-sm font-medium text-gray-700 w-20">计划时间</span>
          <el-date-picker v-model="editForm.planned_time" type="daterange"
            range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期"
            format="YYYY-MM-DD" value-format="YYYY-MM-DD" class="!w-80"
            @change="checkConflicts" />
          <el-button size="small" text type="primary" @click="jumpToSchedule()" title="查看排期日历">
            📅 查看排期
          </el-button>
        </div>

        <!-- 冲突警告 -->
        <div v-if="conflicts.length > 0" class="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-2">
          <div class="flex items-center gap-2 text-amber-700 font-semibold text-sm">
            <span>⚠️ 资源冲突提醒</span>
            <span class="text-xs font-normal text-amber-600">以下人员在该时间段内已有排期</span>
          </div>
          <div v-for="c in conflicts" :key="c.employee_id" class="flex items-center gap-2 text-sm">
            <span class="font-medium text-gray-800">{{ c.employee_name }}</span>
            <span class="text-amber-600">{{ c.dates.length }}天冲突</span>
            <span class="text-gray-400 text-xs">({{ c.items.map((i: any) => i.title).slice(0, 2).join(', ') }}{{ c.items.length > 2 ? '...' : '' }})</span>
            <el-button size="small" text type="primary" class="!ml-auto !px-1"
              @click="jumpToSchedule(c.employee_id)">
              📅 查看
            </el-button>
          </div>
        </div>

        <!-- 按角色分配人员 -->
        <div v-for="role in displayRoles" :key="role.value" class="flex items-start gap-3">
          <div class="w-20 shrink-0 pt-1 text-right">
            <span class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg"
              :style="{ background: role.bg, color: role.color }">
              {{ role.icon }} {{ role.label }}
            </span>
          </div>
          <div class="flex-1">
            <el-select
              v-model="editForm.roles[role.value]"
              multiple filterable placeholder="选择人员" class="w-full"
              collapse-tags collapse-tags-tooltip
              @change="checkConflicts">
              <el-option v-for="emp in employeesByRole(role.value)" :key="emp.id"
                :label="emp.name" :value="emp.id">
                <div class="flex items-center gap-2">
                  <div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white"
                    :style="{ background: role.color }">
                    {{ emp.name?.charAt(0) }}
                  </div>
                  <span>{{ emp.name }}</span>
                  <span class="text-gray-400 text-xs ml-auto">{{ emp.position || '' }}</span>
                  <span v-if="isEmployeeConflicting(emp.id)" class="text-amber-500 text-xs">⚠️</span>
                </div>
              </el-option>
            </el-select>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="saveNodeMembers" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'
import { getEmployees } from '../../api/hr'

const route = useRoute()
const router = useRouter()
const reqId = computed(() => Number(route.params.id))

const nodes = [
  { value: 'requirement_review', label: '需求评审', color: '#8b5cf6' },
  { value: 'tech_review', label: '技术评审', color: '#6366f1' },
  { value: 'case_review', label: '测试用例评审', color: '#0ea5e9' },
  { value: 'testing', label: '测试执行', color: '#14b8a6' },
  { value: 'acceptance', label: '验收测试', color: '#f59e0b' },
  { value: 'released', label: '发布上线', color: '#22c55e' },
  { value: 'regression', label: '线上回归', color: '#ef4444' },
]
const nodeOrder = nodes.map(n => n.value)

const displayRoles = [
  { value: 'product', label: '产品', icon: '📋', color: '#8b5cf6', bg: '#f3e8ff' },
  { value: 'backend', label: '后端开发', icon: '⚙️', color: '#3b82f6', bg: '#dbeafe' },
  { value: 'frontend', label: '前端开发', icon: '🎨', color: '#06b6d4', bg: '#cffafe' },
  { value: 'tester', label: '测试', icon: '🧪', color: '#10b981', bg: '#d1fae5' },
  { value: 'poc', label: 'POC', icon: '👤', color: '#f59e0b', bg: '#fef3c7' },
]

const requirement = ref<any>(null)
const nodeMembers = ref<any[]>([])
const allEmployees = ref<any[]>([])
const nodeRefs: Record<string, any> = {}

const editDialogVisible = ref(false)
const editingNode = ref('')
const saving = ref(false)
const conflicts = ref<any[]>([])
const editForm = reactive({
  planned_time: null as any,
  roles: {} as Record<string, number[]>,
})

const currentStageColor = computed(() => nodes.find(n => n.value === requirement.value?.status)?.color || '#94a3b8')
const currentStageLabel = computed(() => nodes.find(n => n.value === requirement.value?.status)?.label || requirement.value?.status)
const editingNodeLabel = computed(() => nodes.find(n => n.value === editingNode.value)?.label || '')

const progressWidth = computed(() => {
  if (!requirement.value) return '0%'
  const idx = nodeOrder.indexOf(requirement.value.status)
  if (idx < 0) return '0%'
  return `${(idx / (nodes.length - 1)) * 100}%`
})

function isNodeDone(nodeVal: string) {
  const ni = nodeOrder.indexOf(nodeVal)
  const ci = nodeOrder.indexOf(requirement.value?.status)
  return ni < ci
}

function isNodeReached(nodeVal: string) {
  const ni = nodeOrder.indexOf(nodeVal)
  const ci = nodeOrder.indexOf(requirement.value?.status)
  return ni <= ci
}

function nodeCircleClass(nodeVal: string) {
  const ni = nodeOrder.indexOf(nodeVal)
  const ci = nodeOrder.indexOf(requirement.value?.status)
  if (ni < ci) return 'bg-green-500 border-green-500 text-white'
  if (ni === ci) return 'bg-white border-indigo-500 text-indigo-600 ring-2 ring-indigo-200 shadow-md'
  return 'bg-white border-gray-300 text-gray-400'
}

function nextNode(current: string): string | null {
  const idx = nodeOrder.indexOf(current)
  return idx >= 0 && idx < nodeOrder.length - 1 ? nodeOrder[idx + 1] : null
}
function nextNodeLabel(current: string) {
  const n = nextNode(current)
  return n ? nodes.find(nd => nd.value === n)?.label || '' : ''
}

function getNodeMembers(nodeVal: string) {
  return nodeMembers.value.filter(m => m.node === nodeVal)
}

function getNodeRoleMembers(nodeVal: string, role: string) {
  return nodeMembers.value.filter(m => m.node === nodeVal && m.role === role)
}

function getNodeTime(nodeVal: string) {
  const members = getNodeMembers(nodeVal)
  const t = members.find(m => m.planned_time)?.planned_time
  return t || ''
}

function employeesByRole(displayRole: string): any[] {
  if (displayRole === 'poc') return allEmployees.value
  if (displayRole === 'backend') {
    const matched = allEmployees.value.filter(e =>
      e.role === 'developer' && !e.position?.includes('前端')
    )
    return matched.length ? matched : allEmployees.value.filter(e => e.role === 'developer')
  }
  if (displayRole === 'frontend') {
    const matched = allEmployees.value.filter(e =>
      e.role === 'developer' && e.position?.includes('前端')
    )
    return matched.length ? matched : allEmployees.value.filter(e => e.role === 'developer')
  }
  return allEmployees.value.filter(e => e.role === displayRole || !e.role)
}

function priorityLabel(p: string) {
  return { critical: '紧急', high: '高', medium: '中', low: '低' }[p] || p
}
function priorityType(p: string) {
  return ({ critical: 'danger', high: 'warning', medium: '', low: 'info' } as any)[p] || ''
}

function scrollToNode(nodeVal: string) {
  const el = nodeRefs[nodeVal]
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function openEditDialog(nodeVal: string) {
  editingNode.value = nodeVal
  conflicts.value = []
  const currentMembers = getNodeMembers(nodeVal)

  const rolesData: Record<string, number[]> = {}
  for (const r of displayRoles) {
    rolesData[r.value] = currentMembers
      .filter(m => m.role === r.value)
      .map(m => m.employee_id)
  }
  editForm.roles = rolesData

  const t = currentMembers.find(m => m.planned_time)?.planned_time
  if (t && t.includes(' ~ ')) {
    const [s, e] = t.split(' ~ ')
    editForm.planned_time = [s, e]
  } else {
    editForm.planned_time = null
  }

  editDialogVisible.value = true
  checkConflicts()
}

async function checkConflicts() {
  conflicts.value = []
  if (!editForm.planned_time || editForm.planned_time.length < 2) return
  const allIds = new Set<number>()
  for (const r of displayRoles) {
    for (const id of (editForm.roles[r.value] || [])) allIds.add(id)
  }
  if (allIds.size === 0) return
  try {
    const resp = await request.post('/hr/schedules/conflicts', {
      employee_ids: [...allIds],
      start_date: editForm.planned_time[0],
      end_date: editForm.planned_time[1],
    })
    conflicts.value = resp.data?.data?.conflicts || []
  } catch { /* ignore */ }
}

function isEmployeeConflicting(empId: number): boolean {
  return conflicts.value.some(c => c.employee_id === empId)
}

function jumpToSchedule(employeeId?: number) {
  const query: Record<string, string> = {}
  if (employeeId) query.employee_id = String(employeeId)
  if (editForm.planned_time?.[0]) query.start_date = editForm.planned_time[0]
  router.push({ path: '/hr-calendar', query })
}

function jumpToScheduleForNode(nodeVal: string) {
  const members = getNodeMembers(nodeVal)
  const empIds = [...new Set(members.filter(m => m.employee_id).map(m => m.employee_id))]
  const timeStr = getNodeTime(nodeVal)
  const query: Record<string, string> = {}
  if (empIds.length > 0) query.employee_ids = empIds.join(',')
  if (timeStr) {
    const parts = timeStr.split(' ~ ')
    if (parts.length === 2) query.start_date = parts[0]
  }
  query.requirement_id = String(reqId.value)
  router.push({ path: '/hr-calendar', query })
}

async function saveNodeMembers() {
  saving.value = true
  try {
    const members: { role: string; employee_id: number }[] = []
    for (const r of displayRoles) {
      const ids = editForm.roles[r.value] || []
      for (const empId of ids) {
        members.push({ role: r.value, employee_id: empId })
      }
    }
    const planned_time = editForm.planned_time
      ? `${editForm.planned_time[0]} ~ ${editForm.planned_time[1]}`
      : ''

    await request.put(`/requirements/${reqId.value}/node-members/${editingNode.value}`, {
      members,
      planned_time,
    })

    if (editingNode.value === 'requirement_review' && members.length > 0) {
      const otherNodes = nodeOrder.filter(n => n !== 'requirement_review')
      const emptyNodes = otherNodes.filter(n => getNodeMembers(n).length === 0)
      if (emptyNodes.length > 0) {
        await Promise.all(emptyNodes.map(node =>
          request.put(`/requirements/${reqId.value}/node-members/${node}`, {
            members,
            planned_time,
          })
        ))
        ElMessage.success(`保存成功，已同步人员到其他 ${emptyNodes.length} 个空节点`)
      } else {
        ElMessage.success('保存成功')
      }
    } else {
      ElMessage.success('保存成功')
    }

    editDialogVisible.value = false
    await fetchNodeMembers()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function advanceToNode(newStatus: string) {
  try {
    const resp = await request.put(`/requirements/${reqId.value}`, { status: newStatus })
    requirement.value.status = newStatus
    const label = nodes.find(n => n.value === newStatus)?.label || newStatus
    ElMessage.success(`已推进到「${label}」`)

    const result = resp.data?.data
    if (result?.auto_archived) {
      ElMessage.success({ message: '该项目下所有需求已完成线上回归，项目已自动归档', duration: 5000 })
    }
  } catch {
    ElMessage.error('操作失败')
  }
}

async function fetchRequirement() {
  try {
    const resp = await request.get(`/requirements/${reqId.value}`)
    requirement.value = resp.data?.data || resp.data
  } catch {
    ElMessage.error('加载需求失败')
  }
}

async function fetchNodeMembers() {
  try {
    const resp = await request.get(`/requirements/${reqId.value}/node-members`)
    nodeMembers.value = resp.data?.data || resp.data || []
  } catch {
    nodeMembers.value = []
  }
}

async function fetchEmployees() {
  try {
    const resp = await getEmployees()
    allEmployees.value = resp.data?.data || resp.data || []
  } catch {
    allEmployees.value = []
  }
}

onMounted(() => {
  fetchRequirement()
  fetchNodeMembers()
  fetchEmployees()
})
</script>
