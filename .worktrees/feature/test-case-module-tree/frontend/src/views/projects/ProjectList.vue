<template>
  <div class="h-full flex flex-col -m-8">
    <!-- 顶栏：标题 + 视图切换 + 操作 -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <h1 class="text-lg font-bold text-gray-900">📁 项目管理</h1>
        <div class="flex bg-gray-100 rounded-lg p-0.5">
          <button
            v-for="v in viewOptions"
            :key="v.key"
            class="px-3 py-1.5 text-xs font-medium rounded-md transition-all"
            :class="currentView === v.key ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="currentView = v.key"
          >{{ v.icon }} {{ v.label }}</button>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <el-input v-model="searchText" placeholder="搜索项目..." clearable size="small" class="!w-48" @input="filterProjects">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterStatus" clearable placeholder="状态" size="small" class="!w-28" @change="filterProjects">
          <el-option label="草稿" value="draft" />
          <el-option label="已立项" value="approved" />
          <el-option label="进行中" value="active" />
          <el-option label="已归档" value="archived" />
        </el-select>
        <el-button type="primary" color="#4f46e5" size="small" @click="goCreateProject">+ 新建项目</el-button>
      </div>
    </div>

    <!-- 表格视图 (飞书多维表格风格) -->
    <div v-if="currentView === 'table'" class="flex-1 overflow-auto bg-gray-50">
      <table class="w-full border-collapse min-w-[900px]">
        <thead class="sticky top-0 z-10">
          <tr class="bg-gray-50 border-b border-gray-200">
            <th class="feishu-th w-10 text-center">
              <input type="checkbox" class="rounded border-gray-300" :checked="allChecked" @change="toggleAll" />
            </th>
            <th class="feishu-th min-w-[240px]" @click="sortBy('name')">
              项目名称 <span class="sort-icon">{{ sortIcon('name') }}</span>
            </th>
            <th class="feishu-th w-[120px]">状态</th>
            <th class="feishu-th w-[120px]">负责人</th>
            <th class="feishu-th w-[100px]" @click="sortBy('req_count')">
              需求数 <span class="sort-icon">{{ sortIcon('req_count') }}</span>
            </th>
            <th class="feishu-th w-[100px]">成员数</th>
            <th class="feishu-th w-[140px]">进度</th>
            <th class="feishu-th w-[170px]" @click="sortBy('created_at')">
              创建时间 <span class="sort-icon">{{ sortIcon('created_at') }}</span>
            </th>
            <th class="feishu-th w-[120px]">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filteredProjects"
            :key="row.id"
            class="feishu-row group"
            :class="{ 'bg-indigo-50/50': selectedIds.has(row.id) }"
          >
            <td class="feishu-td text-center">
              <input type="checkbox" class="rounded border-gray-300" :checked="selectedIds.has(row.id)" @change="toggleSelect(row.id)" />
            </td>
            <!-- 名称 - 行内编辑 -->
            <td class="feishu-td">
              <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
                  :style="{ background: strToColor(row.name) }">
                  {{ (row.name || '?')[0] }}
                </div>
                <div v-if="editingCell?.id === row.id && editingCell?.field === 'name'" class="flex-1">
                  <input
                    v-model="editingCell.value"
                    class="feishu-inline-input"
                    @blur="saveCell(row)"
                    @keyup.enter="saveCell(row)"
                    @keyup.escape="cancelEdit"
                    ref="inlineInput"
                  />
                </div>
                <div v-else class="flex-1 min-w-0">
                  <div class="font-medium text-gray-900 truncate cursor-pointer hover:text-indigo-600" @click="startEdit(row, 'name')">
                    {{ row.name }}
                  </div>
                  <div class="text-xs text-gray-400 truncate">{{ row.description || '暂无描述' }}</div>
                </div>
              </div>
            </td>
            <!-- 状态 - 行内切换 -->
            <td class="feishu-td">
              <el-select
                :model-value="row.status"
                size="small"
                class="!w-full feishu-select"
                @change="(v: string) => quickUpdate(row, 'status', v)"
              >
                <el-option label="进行中" value="active">
                  <span class="inline-block w-2 h-2 rounded-full bg-green-500 mr-2"></span>进行中
                </el-option>
                <el-option label="已归档" value="archived">
                  <span class="inline-block w-2 h-2 rounded-full bg-gray-400 mr-2"></span>已归档
                </el-option>
                <el-option label="已暂停" value="suspended">
                  <span class="inline-block w-2 h-2 rounded-full bg-yellow-500 mr-2"></span>已暂停
                </el-option>
              </el-select>
            </td>
            <!-- 负责人 -->
            <td class="feishu-td">
              <el-select
                :model-value="row.owner_id"
                size="small"
                class="!w-full feishu-select"
                filterable
                clearable
                placeholder="选择负责人"
                @change="(v: number) => updateOwner(row, v)"
              >
                <el-option v-for="emp in employeeOptions" :key="emp.id" :label="emp.name" :value="emp.id">
                  <div class="flex items-center justify-between w-full">
                    <span>{{ emp.name }}</span>
                    <span class="text-xs text-gray-400 ml-2">{{ emp.position || '' }}</span>
                  </div>
                </el-option>
              </el-select>
            </td>
            <!-- 需求数 -->
            <td class="feishu-td text-center">
              <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-blue-50 text-blue-600 text-sm font-medium">{{ row.req_count || 0 }}</span>
            </td>
            <!-- 成员数 -->
            <td class="feishu-td text-center">
              <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-purple-50 text-purple-600 text-sm font-medium">{{ row.member_count || 0 }}</span>
            </td>
            <!-- 进度 -->
            <td class="feishu-td">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all" :style="{ width: (row.progress || 0) + '%', background: progressColor(row.progress || 0) }"></div>
                </div>
                <span class="text-xs text-gray-500 w-8 text-right">{{ row.progress || 0 }}%</span>
              </div>
            </td>
            <!-- 创建时间 -->
            <td class="feishu-td text-sm text-gray-500">{{ formatTime(row.created_at) }}</td>
            <!-- 操作 -->
            <td class="feishu-td">
              <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <el-button link type="primary" size="small" @click="goDetail(row)">打开</el-button>
                <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
              </div>
            </td>
          </tr>
          <!-- 底部添加行 -->
          <tr class="cursor-pointer hover:bg-gray-50 transition-colors" @click="goCreateProject">
            <td colspan="9" class="px-4 py-3 text-sm text-gray-400 border-b border-gray-100">
              <span class="text-indigo-400">+</span> 点击添加新项目
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 看板视图 -->
    <div v-if="currentView === 'kanban'" class="flex-1 overflow-x-auto bg-gray-50 p-6">
      <div class="flex gap-5 h-full min-w-max">
        <div
          v-for="col in kanbanColumns"
          :key="col.value"
          class="w-[320px] shrink-0 flex flex-col"
          :data-status="col.value"
        >
          <div class="flex items-center justify-between mb-3 px-1">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full" :style="{ background: col.color }"></span>
              <span class="font-semibold text-gray-700 text-sm">{{ col.label }}</span>
              <span class="text-xs bg-gray-200 text-gray-600 rounded-full px-2 py-0.5">{{ kanbanData(col.value).length }}</span>
            </div>
            <el-button link size="small" @click="goCreateProject">+</el-button>
          </div>
          <draggable
            :list="kanbanData(col.value)"
            :group="'projects'"
            item-key="id"
            class="flex-1 space-y-3 overflow-y-auto pb-4 min-h-[80px] rounded-lg kanban-drop-zone"
            ghost-class="kanban-ghost"
            drag-class="kanban-drag"
            :data-status="col.value"
            @end="onDragEnd"
          >
            <template #item="{ element }">
              <div
                class="bg-white rounded-xl border border-gray-100 p-4 shadow-sm hover:shadow-md transition-all cursor-pointer group"
                :data-id="element.id"
                @click="openEditDialog(element)"
              >
                <div class="flex items-start justify-between mb-2">
                  <div class="font-medium text-gray-900 text-sm leading-snug">{{ element.name }}</div>
                  <el-dropdown trigger="click" @command="(cmd: string) => handleKanbanAction(cmd, element)" @click.stop>
                    <button class="p-1 rounded hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-opacity" @click.stop>
                      <span class="text-gray-400 text-xs">⋯</span>
                    </button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="open">打开详情</el-dropdown-item>
                        <el-dropdown-item command="edit">编辑</el-dropdown-item>
                        <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
                <p class="text-xs text-gray-400 mb-3 line-clamp-2">{{ element.description || '暂无描述' }}</p>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">{{ element.req_count || 0 }} 需求</span>
                    <span class="text-xs text-purple-500 bg-purple-50 px-2 py-0.5 rounded-full">{{ element.member_count || 0 }} 人</span>
                  </div>
                  <div v-if="element.owner_name" class="w-6 h-6 rounded-full bg-gradient-to-tr from-indigo-400 to-purple-400 text-white text-[10px] flex items-center justify-center font-bold" :title="element.owner_name">
                    {{ element.owner_name[0] }}
                  </div>
                </div>
                <div class="mt-3 flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full" :style="{ width: (element.progress || 0) + '%', background: progressColor(element.progress || 0) }"></div>
                  </div>
                  <span class="text-[10px] text-gray-400">{{ element.progress || 0 }}%</span>
                </div>
              </div>
            </template>
          </draggable>
        </div>
      </div>
    </div>

    <!-- 编辑项目弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑项目" width="500px" :close-on-click-modal="false" destroy-on-close>
      <el-form label-width="80px" :model="editForm">
        <el-form-item label="项目名称">
          <el-input v-model="editForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="请输入项目描述" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" class="!w-full">
            <el-option v-for="col in allStatusOptions" :key="col.value" :label="col.label" :value="col.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="editForm.owner_id" class="!w-full" filterable clearable placeholder="选择负责人">
            <el-option v-for="emp in employeeOptions" :key="emp.id" :label="emp.name" :value="emp.id">
              <div class="flex items-center justify-between w-full">
                <span>{{ emp.name }}</span>
                <span class="text-xs text-gray-400 ml-2">{{ emp.position || '' }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-between">
          <el-button text type="primary" @click="goDetail(editForm)">查看详情</el-button>
          <div class="flex gap-2">
            <el-button @click="editDialogVisible = false">取消</el-button>
            <el-button type="primary" color="#4f46e5" :loading="editSaving" @click="saveEdit">保存</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 画廊视图 -->
    <div v-if="currentView === 'timeline'" class="flex-1 overflow-auto bg-gray-50 p-6">
      <div class="space-y-4">
        <div v-for="item in filteredProjects" :key="item.id"
          class="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-sm transition-shadow flex items-center gap-5 cursor-pointer"
          @click="goDetail(item)"
        >
          <div class="w-12 h-12 rounded-xl flex items-center justify-center text-white text-lg font-bold shrink-0"
            :style="{ background: strToColor(item.name) }">
            {{ (item.name || '?')[0] }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-semibold text-gray-900 mb-1">{{ item.name }}</div>
            <div class="text-xs text-gray-400">{{ item.description || '暂无描述' }}</div>
          </div>
          <div class="flex items-center gap-6 shrink-0">
            <div class="text-center">
              <div class="text-lg font-bold text-blue-600">{{ item.req_count || 0 }}</div>
              <div class="text-[10px] text-gray-400">需求</div>
            </div>
            <div class="text-center">
              <div class="text-lg font-bold text-purple-600">{{ item.member_count || 0 }}</div>
              <div class="text-[10px] text-gray-400">成员</div>
            </div>
            <div class="w-32">
              <div class="flex items-center gap-2 mb-1">
                <div class="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full rounded-full" :style="{ width: (item.progress || 0) + '%', background: progressColor(item.progress || 0) }"></div>
                </div>
                <span class="text-xs text-gray-500">{{ item.progress || 0 }}%</span>
              </div>
            </div>
            <el-tag :type="statusType(item.status)" effect="light" round size="small">{{ statusLabel(item.status) }}</el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref, computed } from 'vue'

import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import request from '../../utils/request'

const router = useRouter()

const viewOptions = [
  { key: 'table', label: '表格', icon: '📊' },
  { key: 'kanban', label: '看板', icon: '📋' },
  { key: 'timeline', label: '画廊', icon: '🖼️' },
]
const currentView = ref('table')

const projects = ref<any[]>([])
const loading = ref(false)
const searchText = ref('')
const filterStatus = ref('')
const sortField = ref('')
const sortOrder = ref<'asc' | 'desc'>('asc')

const selectedIds = ref(new Set<number>())
const allChecked = computed(() => filteredProjects.value.length > 0 && filteredProjects.value.every(p => selectedIds.value.has(p.id)))

const editingCell = ref<{ id: number; field: string; value: string } | null>(null)

const employeeOptions = ref<any[]>([])

async function fetchEmployees() {
  try {
    const resp = await request.get('/hr/employees')
    employeeOptions.value = resp.data?.data || []
  } catch {}
}

const kanbanColumns = [
  { value: 'draft', label: '草稿', color: '#94a3b8' },
  { value: 'approved', label: '已立项', color: '#f59e0b' },
  { value: 'active', label: '进行中', color: '#22c55e' },
  { value: 'archived', label: '已归档', color: '#6b7280' },
]

const filteredProjects = computed(() => {
  let list = [...projects.value]
  if (searchText.value) {
    const kw = searchText.value.toLowerCase()
    list = list.filter(p => p.name?.toLowerCase().includes(kw) || p.description?.toLowerCase().includes(kw))
  }
  if (filterStatus.value) {
    list = list.filter(p => p.status === filterStatus.value)
  }
  if (sortField.value) {
    list.sort((a, b) => {
      const va = a[sortField.value] ?? ''
      const vb = b[sortField.value] ?? ''
      const cmp = va < vb ? -1 : va > vb ? 1 : 0
      return sortOrder.value === 'asc' ? cmp : -cmp
    })
  }
  return list
})

function kanbanData(status: string) {
  return filteredProjects.value.filter(p => p.status === status)
}

function sortBy(field: string) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortOrder.value = 'asc'
  }
}

function sortIcon(field: string) {
  if (sortField.value !== field) return '↕'
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

function filterProjects() {}

async function fetchProjects() {
  loading.value = true
  try {
    const resp = await request.get('/projects', { params: { page: 1, page_size: 100 } })
    projects.value = resp.data?.data?.items || []
  } finally { loading.value = false }
}

function toggleAll() {
  if (allChecked.value) {
    selectedIds.value.clear()
  } else {
    filteredProjects.value.forEach(p => selectedIds.value.add(p.id))
  }
}

function toggleSelect(id: number) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

function startEdit(row: any, field: string) {
  editingCell.value = { id: row.id, field, value: row[field] || '' }
  nextTick(() => {
    const input = document.querySelector('.feishu-inline-input:focus') as HTMLInputElement
    input?.focus()
  })
}

function cancelEdit() { editingCell.value = null }

async function saveCell(row: any) {
  if (!editingCell.value) return
  const { field, value } = editingCell.value
  if (value === (row[field] || '')) { editingCell.value = null; return }
  try {
    await request.put(`/projects/${row.id}`, { ...row, [field]: value })
    row[field] = value
    ElMessage.success('已更新')
  } catch { ElMessage.error('更新失败') }
  editingCell.value = null
}

async function quickUpdate(row: any, field: string, value: any) {
  try {
    await request.put(`/projects/${row.id}`, { ...row, [field]: value })
    row[field] = value
    ElMessage.success('已更新')
  } catch { ElMessage.error('更新失败') }
}

async function updateOwner(row: any, empId: number | null) {
  try {
    await request.put(`/projects/${row.id}`, { owner_id: empId || null })
    row.owner_id = empId
    const emp = employeeOptions.value.find((e: any) => e.id === empId)
    row.owner_name = emp?.name || null
    ElMessage.success('负责人已更新')
  } catch { ElMessage.error('更新失败') }
}

function goCreateProject() {
  router.push('/projects/create')
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await request.delete(`/projects/${row.id}`)
  ElMessage.success('已删除')
  fetchProjects()
}

function handleKanbanAction(cmd: string, item: any) {
  if (cmd === 'open') goDetail(item)
  if (cmd === 'edit') openEditDialog(item)
  if (cmd === 'delete') handleDelete(item)
}

const allStatusOptions = [
  ...kanbanColumns,
  { value: 'suspended', label: '已暂停', color: '#eab308' },
]

const editDialogVisible = ref(false)
const editSaving = ref(false)
const editForm = reactive<{ id: number; name: string; description: string; status: string; owner_id: number | null }>({
  id: 0, name: '', description: '', status: 'active', owner_id: null,
})

function openEditDialog(item: any) {
  editForm.id = item.id
  editForm.name = item.name || ''
  editForm.description = item.description || ''
  editForm.status = item.status || 'active'
  editForm.owner_id = item.owner_id || null
  editDialogVisible.value = true
}

async function saveEdit() {
  if (!editForm.name.trim()) { ElMessage.warning('项目名称不能为空'); return }
  editSaving.value = true
  try {
    await request.put(`/projects/${editForm.id}`, {
      name: editForm.name,
      description: editForm.description,
      status: editForm.status,
      owner_id: editForm.owner_id,
    })
    ElMessage.success('项目已更新')
    editDialogVisible.value = false
    fetchProjects()
  } catch { ElMessage.error('更新失败') }
  finally { editSaving.value = false }
}

async function onDragEnd(evt: any) {
  const toContainer = evt.to as HTMLElement
  const toStatus = toContainer?.dataset?.status
  if (!toStatus) return

  const itemId = evt.item?.dataset?.id ? parseInt(evt.item.dataset.id) : null
  if (!itemId) return

  const project = projects.value.find(p => p.id === itemId)
  if (!project || project.status === toStatus) return

  const oldStatus = project.status
  project.status = toStatus
  try {
    await request.put(`/projects/${project.id}`, { ...project, status: toStatus })
    const label = kanbanColumns.find(c => c.value === toStatus)?.label || toStatus
    ElMessage.success(`已移动到「${label}」`)
  } catch {
    project.status = oldStatus
    ElMessage.error('状态更新失败')
    fetchProjects()
  }
}

function goDetail(row: any) { router.push(`/projects/${row.id}`) }

function strToColor(str: string) {
  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#0ea5e9', '#14b8a6', '#22c55e']
  let hash = 0
  for (let i = 0; i < (str || '').length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function progressColor(p: number) {
  if (p >= 80) return '#22c55e'
  if (p >= 50) return '#3b82f6'
  if (p >= 20) return '#f59e0b'
  return '#ef4444'
}

function statusLabel(s: string) { return { draft: '草稿', approved: '已立项', active: '进行中', archived: '已归档', suspended: '已暂停' }[s] || s }
function statusType(s: string) { return ({ draft: 'info', approved: 'warning', active: 'success', archived: '', suspended: 'danger' } as any)[s] || 'info' }

function formatTime(v: string) {
  if (!v) return '--'
  const d = new Date(v)
  if (isNaN(d.getTime())) return '--'
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

onMounted(() => {
  fetchProjects()
  fetchEmployees()
})
</script>

<style scoped>
.feishu-th {
  padding: 10px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}
.feishu-th .sort-icon {
  font-size: 10px;
  opacity: 0.5;
  margin-left: 2px;
}
.feishu-td {
  padding: 10px 16px;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
  color: #374151;
  vertical-align: middle;
}
.feishu-row {
  transition: background-color 0.15s;
}
.feishu-row:hover {
  background: #f8fafc;
}
.feishu-inline-input {
  width: 100%;
  padding: 4px 8px;
  border: 1.5px solid #818cf8;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  background: white;
}
.feishu-inline-input:focus {
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}
:deep(.feishu-select .el-input__wrapper) {
  box-shadow: none !important;
  background: transparent;
  padding: 0 4px;
}
:deep(.feishu-select .el-input__wrapper:hover) {
  background: #f3f4f6;
  border-radius: 6px;
}
.kanban-ghost {
  opacity: 0.4;
  border: 2px dashed #818cf8 !important;
  background: #eef2ff !important;
  border-radius: 12px;
}
.kanban-drag {
  transform: rotate(2deg);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15) !important;
}
.kanban-drop-zone {
  transition: background-color 0.2s;
}
</style>
