<template>
  <div class="h-full flex flex-col -m-8">
    <!-- 顶栏 -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <h1 class="text-lg font-bold text-gray-900">📅 人力排期</h1>
        <div class="flex bg-gray-100 rounded-lg p-0.5">
          <button
            v-for="v in viewModes"
            :key="v.key"
            class="px-3 py-1.5 text-xs font-medium rounded-md transition-all"
            :class="viewMode === v.key ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
            @click="viewMode = v.key"
          >{{ v.icon }} {{ v.label }}</button>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <!-- 三种维度切换 -->
        <div class="flex bg-amber-50 rounded-lg p-0.5 border border-amber-200">
          <button v-for="dim in dimensions" :key="dim.key"
            class="px-2.5 py-1 text-[11px] font-medium rounded-md transition-all"
            :class="groupDimension === dim.key ? 'bg-amber-400 text-white shadow-sm' : 'text-amber-700 hover:bg-amber-100'"
            @click="groupDimension = dim.key; buildGantt()">{{ dim.icon }} {{ dim.label }}</button>
        </div>
        <el-select v-model="filterTeam" clearable placeholder="按团队筛选" size="small" class="!w-36" @change="buildGantt">
          <el-option v-for="t in teams" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-select
          v-model="filterProjects"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          clearable
          placeholder="按项目筛选"
          size="small"
          class="!w-48"
          @change="buildGantt"
        >
          <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="p.value" />
        </el-select>
        <el-select
          v-model="filterRequirements"
          multiple
          filterable
          collapse-tags
          collapse-tags-tooltip
          clearable
          placeholder="按需求筛选"
          size="small"
          class="!w-48"
          @change="buildGantt"
        >
          <el-option v-for="r in requirementOptions" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
        <div class="flex items-center gap-1 bg-gray-100 rounded-lg px-2 py-1">
          <el-button link size="small" @click="shiftRange(-7)">‹‹</el-button>
          <el-button link size="small" @click="shiftRange(-1)">‹</el-button>
          <span class="text-xs font-medium text-gray-600 px-2 min-w-[140px] text-center">{{ rangeLabel }}</span>
          <el-button link size="small" @click="shiftRange(1)">›</el-button>
          <el-button link size="small" @click="shiftRange(7)">››</el-button>
        </div>
        <el-button type="primary" color="#4f46e5" size="small" @click="openScheduleDialog">+ 新建排期</el-button>
      </div>
    </div>

    <!-- 甘特图视图 -->
    <div v-if="viewMode === 'gantt'" class="flex-1 overflow-auto bg-gray-50">
      <div class="flex min-w-max">
        <!-- 左侧人员列表 -->
        <div class="w-[220px] shrink-0 bg-white border-r border-gray-200 sticky left-0 z-20">
          <div class="gantt-header-row bg-gray-50 border-b border-gray-200 font-semibold text-gray-600">
            {{ groupDimension === 'team' ? '团队 / 成员' : groupDimension === 'project' ? '项目 / 成员' : '时间段 / 成员' }}
          </div>
          <template v-for="group in ganttGroups" :key="group.team">
            <div class="gantt-team-row border-b border-gray-100 bg-gray-50/80 cursor-pointer" @click="toggleTeamExpand(group.team)">
              <span class="text-xs mr-1">{{ expandedTeams.has(group.team) ? '▼' : '▶' }}</span>
              <span class="font-semibold text-gray-700 text-sm">{{ group.team }}</span>
              <span class="text-xs text-gray-400 ml-2">({{ group.members.length }}人)</span>
            </div>
            <template v-if="expandedTeams.has(group.team)">
              <div
                v-for="member in group.members"
                :key="member.id"
                class="gantt-member-row border-b border-gray-50 cursor-pointer hover:bg-indigo-50/40 transition-colors"
                :class="{ 'bg-indigo-50 ring-1 ring-indigo-200': highlightEmployeeIds.has(member.id) }"
                @click="showMemberDetail(member)"
              >
                <div class="flex items-center gap-2">
                  <div class="w-6 h-6 rounded-full text-white text-[10px] flex items-center justify-center font-bold shrink-0"
                    :style="{ background: strToColor(member.name) }">
                    {{ (member.name || '?')[0] }}
                  </div>
                  <div class="min-w-0">
                    <div class="text-sm font-medium text-gray-800 truncate">{{ member.name }}</div>
                    <div class="text-[10px] truncate" :class="highlightEmployeeIds.has(member.id) ? 'text-indigo-500 font-medium' : 'text-gray-400'">
                      {{ highlightEmployeeIds.has(member.id) ? getMemberReleaseLabel(member) : (member.position || member.role || '') }}
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </div>

        <!-- 右侧甘特时间轴 -->
        <div class="flex-1">
          <!-- 日期头部 -->
          <div class="gantt-header-row bg-gray-50 border-b border-gray-200 flex sticky top-0 z-10">
            <div
              v-for="day in dateRange"
              :key="day.str"
              class="gantt-day-header"
              :class="{
                'bg-indigo-50/80 text-indigo-600': day.isToday,
                'bg-red-50/50 text-red-400': day.isWeekend && !day.isToday,
              }"
            >
              <div class="text-[10px] leading-none">{{ day.weekday }}</div>
              <div class="text-xs font-semibold leading-none mt-0.5">{{ day.label }}</div>
            </div>
          </div>

          <!-- 甘特条 -->
          <template v-for="group in ganttGroups" :key="'g-' + group.team">
            <!-- Team 空行 -->
            <div class="gantt-team-row border-b border-gray-100 bg-gray-50/80 flex">
              <div v-for="day in dateRange" :key="day.str" class="gantt-day-cell"
                :class="{ 'bg-indigo-50/30': day.isToday, 'bg-gray-50/60': day.isWeekend && !day.isToday }">
              </div>
            </div>
            <template v-if="expandedTeams.has(group.team)">
              <div
                v-for="member in group.members"
                :key="'m-' + member.id"
                class="gantt-member-row border-b border-gray-50 flex relative"
              >
                <div
                  v-for="day in dateRange"
                  :key="day.str"
                  class="gantt-day-cell relative"
                  :class="{
                    'bg-indigo-50/30': day.isToday,
                    'bg-gray-50/60': day.isWeekend && !day.isToday,
                  }"
                >
                  <!-- 排期条 -->
                  <div
                    v-for="bar in getBarsForCell(member.id, day.str)"
                    :key="bar.id"
                    class="gantt-bar"
                    :class="ganttBarClass(bar)"
                    :title="`${bar.title} (${typeLabel(bar.schedule_type)})`"
                    @click="showBarDetail(bar)"
                  >
                    <span class="truncate text-[10px] font-medium">{{ bar.title }}</span>
                  </div>
                </div>
              </div>
            </template>
          </template>
        </div>
      </div>
    </div>

    <!-- 资源总览视图 -->
    <div v-if="viewMode === 'overview'" class="flex-1 overflow-auto bg-gray-50 p-6">
      <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
        <div
          v-for="group in ganttGroups"
          :key="group.team"
          class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden"
        >
          <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 class="font-semibold text-gray-800">{{ group.team }}</h3>
              <p class="text-xs text-gray-400">{{ group.members.length }} 名成员</p>
            </div>
            <div class="text-right">
              <div class="text-2xl font-bold" :style="{ color: utilizationColor(group.utilization) }">{{ group.utilization }}%</div>
              <div class="text-[10px] text-gray-400">资源利用率</div>
            </div>
          </div>
          <div class="p-4 space-y-3">
            <div v-for="m in group.members" :key="m.id" class="flex items-center gap-3 cursor-pointer hover:bg-gray-50 rounded-lg px-1 py-0.5"
              @click="showMemberDetail(m)">
              <div class="w-7 h-7 rounded-full text-white text-[10px] flex items-center justify-center font-bold shrink-0"
                :style="{ background: strToColor(m.name) }">{{ (m.name || '?')[0] }}</div>
              <div class="flex-1 min-w-0">
                <div class="text-sm text-gray-700 truncate">{{ m.name }}</div>
                <div class="text-[10px] text-gray-400 truncate">{{ getMemberReleaseLabel(m) }}</div>
              </div>
              <div class="w-20 shrink-0">
                <div class="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all" :style="{ width: m.utilization + '%', background: utilizationColor(m.utilization) }"></div>
                </div>
              </div>
              <span class="text-xs font-medium w-8 text-right" :style="{ color: utilizationColor(m.utilization) }">{{ m.utilization }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 人员任务详情侧边面板 -->
    <el-drawer v-model="memberDetailVisible" :title="memberDetailData?.name + ' - 任务排期'" size="420px">
      <template v-if="memberDetailData">
        <div class="space-y-4">
          <!-- 人员基本信息 -->
          <div class="flex items-center gap-3 pb-3 border-b border-gray-100">
            <div class="w-10 h-10 rounded-full text-white text-sm flex items-center justify-center font-bold"
              :style="{ background: strToColor(memberDetailData.name) }">
              {{ (memberDetailData.name || '?')[0] }}
            </div>
            <div>
              <div class="font-semibold text-gray-800">{{ memberDetailData.name }}</div>
              <div class="text-xs text-gray-400">{{ memberDetailData.position || memberDetailData.role || '' }}</div>
            </div>
            <div class="ml-auto text-right">
              <div class="text-lg font-bold" :style="{ color: utilizationColor(memberDetailData.utilization) }">
                {{ memberDetailData.utilization }}%
              </div>
              <div class="text-[10px] text-gray-400">利用率</div>
            </div>
          </div>

          <!-- 释放时间 -->
          <div class="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
            <div class="text-xs text-blue-600 font-semibold mb-1">📅 预计释放时间</div>
            <div class="text-sm text-blue-800 font-medium">{{ getMemberReleaseLabel(memberDetailData) }}</div>
          </div>

          <!-- 任务列表 -->
          <div>
            <h4 class="text-sm font-semibold text-gray-700 mb-2">📋 当前任务</h4>
            <div v-if="memberTaskSummary.length === 0" class="text-center text-gray-400 text-sm py-4">暂无排期任务</div>
            <div v-else class="space-y-2">
              <div v-for="task in memberTaskSummary" :key="task.key"
                class="bg-gray-50 border border-gray-100 rounded-xl px-4 py-3">
                <div class="flex items-center justify-between">
                  <span class="font-medium text-gray-800 text-sm">{{ task.title }}</span>
                  <el-tag size="small" :type="task.type === 'leave' ? 'warning' : ''" effect="light" round>
                    {{ ({ work: '项目排期', schedule: '项目排期', leave: '请假', training: '培训', meeting: '会议' } as Record<string, string>)[task.type] || task.type }}
                  </el-tag>
                </div>
                <div class="text-xs text-gray-500 mt-1">{{ task.startDate }} ~ {{ task.endDate }}  ({{ task.days }}天)</div>
                <div v-if="task.project" class="text-xs text-indigo-500 mt-0.5">📂 {{ task.project }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 新建排期弹窗 -->
    <el-dialog v-model="scheduleDialogVisible" title="新建排期" width="520px" destroy-on-close>
      <el-form :model="scheduleForm" label-width="80px">
        <el-form-item label="员工" required>
          <el-select v-model="scheduleForm.employee_id" filterable placeholder="选择员工" class="w-full">
            <el-option v-for="e in allEmployees" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="scheduleForm.project" placeholder="关联项目" clearable class="w-full">
            <el-option v-for="p in projectOptions" :key="p.value" :label="p.label" :value="p.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围" required>
          <el-date-picker
            v-model="scheduleForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="!w-full"
          />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="scheduleForm.type" class="w-full">
            <el-option label="项目排期" value="work" />
            <el-option label="请假" value="leave" />
            <el-option label="培训" value="training" />
            <el-option label="会议" value="meeting" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="scheduleForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="createSchedule">确定</el-button>
      </template>
    </el-dialog>

    <!-- 排期详情弹窗 -->
    <el-dialog v-model="detailVisible" title="排期详情" width="400px">
      <el-descriptions :column="1" border v-if="detailBar">
        <el-descriptions-item label="事项">{{ detailBar.title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeLabel(detailBar.schedule_type) }}</el-descriptions-item>
        <el-descriptions-item label="员工">{{ getEmployeeName(detailBar.employee_id) }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ detailBar.schedule_date }}</el-descriptions-item>
        <el-descriptions-item label="项目">{{ getProjectName(detailBar.project_id) || '--' }}</el-descriptions-item>
        <el-descriptions-item label="描述" v-if="detailBar.description">{{ detailBar.description }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../../utils/request'

const route = useRoute()
const highlightEmployeeIds = ref<Set<number>>(new Set())
const fromRequirementId = ref<number | null>(null)

const viewModes: Array<{ key: 'gantt' | 'overview'; label: string; icon: string }> = [
  { key: 'gantt', label: '甘特图', icon: '📊' },
  { key: 'overview', label: '资源总览', icon: '📈' },
]
const viewMode = ref<'gantt' | 'overview'>('gantt')

const dimensions: Array<{ key: 'team' | 'project' | 'time'; label: string; icon: string }> = [
  { key: 'team', label: '分组维度', icon: '👥' },
  { key: 'project', label: '项目维度', icon: '📂' },
  { key: 'time', label: '时间维度', icon: '🕐' },
]
const groupDimension = ref<'team' | 'project' | 'time'>('team')

const filterTeam = ref<number | ''>('')
const filterProjects = ref<number[]>([])
const filterRequirements = ref<number[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const requirementOptions = ref<{ label: string; value: number }[]>([])
const teams = ref<any[]>([])
const allEmployees = ref<any[]>([])
const allSchedules = ref<any[]>([])
const expandedTeams = ref(new Set<string>())

interface GanttGroup {
  team: string
  teamId: number | null
  utilization: number
  members: { id: number; name: string; position?: string; role?: string; utilization: number; schedules: any[] }[]
}
const ganttGroups = ref<GanttGroup[]>([])

// 日期范围
const startDate = ref(getMonday(new Date()))
const dayCount = 21

function getMonday(d: Date) {
  const dt = new Date(d)
  const day = dt.getDay()
  const diff = dt.getDate() - day + (day === 0 ? -6 : 1)
  dt.setDate(diff)
  dt.setHours(0, 0, 0, 0)
  return dt
}

function shiftRange(days: number) {
  const d = new Date(startDate.value)
  d.setDate(d.getDate() + days)
  startDate.value = d
}

const dateRange = computed(() => {
  const days: { str: string; label: string; weekday: string; isToday: boolean; isWeekend: boolean }[] = []
  const todayStr = fmtDate(new Date())
  const wdays = ['日', '一', '二', '三', '四', '五', '六']
  for (let i = 0; i < dayCount; i++) {
    const d = new Date(startDate.value)
    d.setDate(d.getDate() + i)
    const s = fmtDate(d)
    days.push({
      str: s,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
      weekday: wdays[d.getDay()],
      isToday: s === todayStr,
      isWeekend: d.getDay() === 0 || d.getDay() === 6,
    })
  }
  return days
})

const rangeLabel = computed(() => {
  const end = new Date(startDate.value)
  end.setDate(end.getDate() + dayCount - 1)
  return `${fmtDate(startDate.value)} ~ ${fmtDate(end)}`
})

function fmtDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 排期弹窗
const scheduleDialogVisible = ref(false)
const scheduleForm = reactive({ employee_id: null as number | null, project: '', dateRange: [] as string[], type: 'work', remark: '' })
const detailVisible = ref(false)
const detailBar = ref<any>(null)

function openScheduleDialog() {
  scheduleForm.employee_id = null; scheduleForm.project = ''; scheduleForm.dateRange = []; scheduleForm.type = 'work'; scheduleForm.remark = ''
  scheduleDialogVisible.value = true
}

async function createSchedule() {
  if (!scheduleForm.employee_id || !scheduleForm.dateRange?.length) { ElMessage.warning('请填写必要信息'); return }
  const [start, end] = scheduleForm.dateRange
  const dates: string[] = []
  const d = new Date(start)
  const endD = new Date(end)
  while (d <= endD) { dates.push(fmtDate(d)); d.setDate(d.getDate() + 1) }

  try {
    const title = scheduleForm.project ? `${scheduleForm.project} - 排期` : '排期'
    for (const dt of dates) {
      await request.post('/hr/schedules', {
        employee_id: scheduleForm.employee_id,
        project_id: projectOptions.value.find(p => p.label === scheduleForm.project)?.value || null,
        schedule_date: dt,
        title,
        schedule_type: scheduleForm.type,
        description: scheduleForm.remark,
      })
    }
    ElMessage.success('排期已创建')
    scheduleDialogVisible.value = false
    fetchData()
  } catch { ElMessage.error('创建失败') }
}

function showBarDetail(bar: any) {
  detailBar.value = bar
  detailVisible.value = true
}

function getBarsForCell(memberId: number, dateStr: string) {
  return allSchedules.value.filter(s => {
    return s.employee_id === memberId && s.schedule_date === dateStr
  })
}

function ganttBarClass(bar: any) {
  const map: Record<string, string> = {
    work: 'gantt-bar-schedule',
    schedule: 'gantt-bar-schedule',
    leave: 'gantt-bar-leave',
    training: 'gantt-bar-training',
    meeting: 'gantt-bar-meeting',
  }
  return map[bar.schedule_type] || 'gantt-bar-schedule'
}

function typeLabel(t: string) {
  return ({ work: '项目排期', schedule: '项目排期', leave: '请假', training: '培训', meeting: '会议' } as Record<string, string>)[t] || t
}

function getEmployeeName(empId: number): string {
  return allEmployees.value.find(e => e.id === empId)?.name || '--'
}

function getProjectName(projId: number | null): string {
  if (!projId) return ''
  return projectOptions.value.find(p => p.value === projId)?.label || ''
}

function toggleTeamExpand(team: string) {
  if (expandedTeams.value.has(team)) expandedTeams.value.delete(team)
  else expandedTeams.value.add(team)
}

function buildGantt() {
  let employees = [...allEmployees.value]
  if (filterTeam.value) employees = employees.filter(e => e.team_id === filterTeam.value)

  const totalWorkDays = dayCount - dateRange.value.filter(d => d.isWeekend).length

  function enrichEmployee(emp: any) {
    let schedules = allSchedules.value.filter(s => s.employee_id === emp.id)
    if (filterProjects.value.length > 0) {
      const projLabels = new Set(filterProjects.value.map(id => projectOptions.value.find(p => p.value === id)?.label).filter(Boolean))
      schedules = schedules.filter(s => filterProjects.value.includes(s.project_id) || projLabels.has(s.project))
    }
    if (filterRequirements.value.length > 0) {
      schedules = schedules.filter(s => filterRequirements.value.includes(s.requirement_id))
    }
    const workDays = new Set(schedules.filter(s => s.schedule_type !== 'leave').map(s => s.schedule_date)).size
    return {
      ...emp,
      schedules,
      utilization: totalWorkDays > 0 ? Math.min(100, Math.round((workDays / totalWorkDays) * 100)) : 0,
    }
  }

  const groupMap = new Map<string, any[]>()

  if (groupDimension.value === 'team') {
    for (const emp of employees) {
      const teamName = teams.value.find(t => t.id === emp.team_id)?.name || '未分组'
      if (!groupMap.has(teamName)) groupMap.set(teamName, [])
      groupMap.get(teamName)!.push(enrichEmployee(emp))
    }
  } else if (groupDimension.value === 'project') {
    const projNameMap = new Map<string, any[]>()
    for (const emp of employees) {
      const empData = enrichEmployee(emp)
      const projects = new Set(empData.schedules.map((s: any) => s.project || '未分配项目'))
      if (projects.size === 0) projects.add('未分配项目')
      for (const pName of projects) {
        const key = String(pName)
        if (!projNameMap.has(key)) projNameMap.set(key, [])
        const existing = projNameMap.get(key)!
        if (!existing.find((e: any) => e.id === empData.id)) existing.push(empData)
      }
    }
    for (const [k, v] of projNameMap) groupMap.set(k, v)
  } else {
    const weekMap = new Map<string, any[]>()
    for (const day of dateRange.value) {
      const d = new Date(day.str)
      const weekStart = new Date(d)
      weekStart.setDate(d.getDate() - ((d.getDay() + 6) % 7))
      const weekLabel = `${weekStart.getMonth() + 1}/${weekStart.getDate()} 周`
      if (!weekMap.has(weekLabel)) weekMap.set(weekLabel, [])
    }
    for (const emp of employees) {
      const empData = enrichEmployee(emp)
      for (const [weekLabel] of weekMap) {
        const existing = weekMap.get(weekLabel)!
        if (!existing.find((e: any) => e.id === empData.id)) existing.push(empData)
      }
    }
    for (const [k, v] of weekMap) groupMap.set(k, v)
  }

  const groups: GanttGroup[] = []
  for (const [groupName, members] of groupMap) {
    const sorted = [...members].sort((a, b) => {
      const aH = highlightEmployeeIds.value.has(a.id) ? 0 : 1
      const bH = highlightEmployeeIds.value.has(b.id) ? 0 : 1
      return aH - bH
    })
    const avgUtil = sorted.length ? Math.round(sorted.reduce((s: number, m: any) => s + m.utilization, 0) / sorted.length) : 0
    groups.push({
      team: groupName,
      teamId: null,
      utilization: avgUtil,
      members: sorted,
    })
    if (sorted.some(m => highlightEmployeeIds.value.has(m.id))) {
      expandedTeams.value.add(groupName)
    }
  }
  if (highlightEmployeeIds.value.size === 0) {
    for (const g of groups) expandedTeams.value.add(g.team)
  }
  ganttGroups.value = groups
}

function strToColor(str: string) {
  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f97316', '#0ea5e9', '#14b8a6', '#22c55e']
  let hash = 0
  for (let i = 0; i < (str || '').length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function utilizationColor(u: number) {
  if (u >= 90) return '#ef4444'
  if (u >= 70) return '#f59e0b'
  if (u >= 40) return '#3b82f6'
  return '#22c55e'
}

// ---- 人员任务详情面板 ----
const memberDetailVisible = ref(false)
const memberDetailData = ref<any>(null)
const memberTaskSummary = ref<any[]>([])

function showMemberDetail(member: any) {
  memberDetailData.value = member
  memberTaskSummary.value = buildTaskSummary(member)
  memberDetailVisible.value = true
}

function buildTaskSummary(member: any): any[] {
  const schedules = allSchedules.value.filter(s => s.employee_id === member.id)
  const taskMap = new Map<string, { title: string; type: string; project: string; dates: string[] }>()
  for (const s of schedules) {
    const key = s.title || s.description || `${s.schedule_type}-${s.project_id || 'none'}`
    if (!taskMap.has(key)) {
      taskMap.set(key, {
        title: s.title || '未命名任务',
        type: s.schedule_type || 'work',
        project: projectOptions.value.find(p => p.value === s.project_id)?.label || '',
        dates: [],
      })
    }
    taskMap.get(key)!.dates.push(s.schedule_date)
  }
  const tasks: any[] = []
  for (const [key, t] of taskMap) {
    const sorted = t.dates.filter(Boolean).sort()
    if (sorted.length > 0) {
      tasks.push({
        key,
        title: t.title,
        type: t.type,
        project: t.project,
        startDate: sorted[0],
        endDate: sorted[sorted.length - 1],
        days: sorted.length,
      })
    }
  }
  return tasks.sort((a, b) => a.startDate.localeCompare(b.startDate))
}

function getMemberReleaseLabel(member: any): string {
  const schedules = allSchedules.value.filter(
    s => s.employee_id === member.id && s.schedule_type === 'work'
  )
  if (schedules.length === 0) return '当前空闲'
  const dates = schedules.map(s => s.schedule_date).filter(Boolean).sort()
  const lastDate = dates[dates.length - 1]
  if (!lastDate) return '当前空闲'
  const today = fmtDate(new Date())
  if (lastDate < today) return '当前空闲'
  const ld = new Date(lastDate)
  ld.setDate(ld.getDate() + 1)
  return `${fmtDate(ld)} 释放`
}

function parseResponseData(resp: any): any {
  return resp.data?.data ?? resp.data
}

function parseArrayData(data: any): any[] {
  if (Array.isArray(data)) return data
  return data?.items ?? data?.list ?? []
}

async function fetchData() {
  const endDateMs = startDate.value.getTime() + dayCount * 86400000
  const params = {
    start_date: fmtDate(startDate.value),
    end_date: fmtDate(new Date(endDateMs)),
  }

  const results = await Promise.allSettled([
    request.get('/hr/employees'),
    request.get('/hr/teams'),
    request.get('/hr/schedules', { params }),
    request.get('/projects', { params: { page: 1, page_size: 200 } }),
    request.get('/requirements', { params: { page: 1, page_size: 500 } }),
  ])

  if (results[0].status === 'fulfilled') {
    allEmployees.value = parseArrayData(parseResponseData(results[0].value))
  }
  if (results[1].status === 'fulfilled') {
    teams.value = parseArrayData(parseResponseData(results[1].value))
  }
  if (results[2].status === 'fulfilled') {
    allSchedules.value = parseArrayData(parseResponseData(results[2].value))
  }
  if (results[3].status === 'fulfilled') {
    const projData = parseResponseData(results[3].value)
    const items = projData?.items ?? (Array.isArray(projData) ? projData : [])
    projectOptions.value = items.map((p: any) => ({ label: p.name, value: p.id }))
  }
  if (results[4].status === 'fulfilled') {
    const reqData = parseResponseData(results[4].value)
    const items = reqData?.items ?? (Array.isArray(reqData) ? reqData : [])
    requirementOptions.value = items.map((r: any) => ({ label: r.title || r.name || `需求#${r.id}`, value: r.id }))
  }

  if (fromRequirementId.value && allSchedules.value.length === 0 && highlightEmployeeIds.value.size > 0) {
    await fetchRequirementSchedules()
  }

  buildGantt()
}

async function fetchRequirementSchedules() {
  if (!fromRequirementId.value) return
  try {
    const resp = await request.get(`/requirements/${fromRequirementId.value}/node-members`)
    const members = parseArrayData(parseResponseData(resp))
    if (members.length === 0) return

    const scheduleItems: any[] = []
    for (const m of members) {
      if (!m.planned_time || !m.employee_id) continue
      const parts = m.planned_time.split(' ~ ')
      if (parts.length !== 2) continue
      const [startStr, endStr] = parts
      const start = new Date(startStr)
      const end = new Date(endStr)
      if (isNaN(start.getTime()) || isNaN(end.getTime())) continue
      const nodeLabel = ({ requirement_review: '需求评审', tech_review: '技术评审', case_review: '用例评审', testing: '测试执行', acceptance: '验收测试', released: '发布上线', regression: '线上回归' } as Record<string, string>)[m.node] || m.node
      const current = new Date(start)
      while (current <= end) {
        if (current.getDay() !== 0 && current.getDay() !== 6) {
          scheduleItems.push({
            id: `req-${m.id}-${fmtDate(current)}`,
            employee_id: m.employee_id,
            project_id: null,
            title: `${nodeLabel} (需求排期)`,
            schedule_date: fmtDate(current),
            schedule_type: 'work',
            description: `来自需求 #${fromRequirementId.value}`,
          })
        }
        current.setDate(current.getDate() + 1)
      }
    }
    if (scheduleItems.length > 0) {
      allSchedules.value = [...allSchedules.value, ...scheduleItems]
    }
  } catch { /* requirement data is supplementary */ }
}

function applyQueryParams(q: Record<string, any>) {
  if (q.start_date) {
    const d = new Date(q.start_date as string)
    if (!isNaN(d.getTime())) startDate.value = getMonday(d)
  }
  if (q.employee_id) {
    highlightEmployeeIds.value = new Set([Number(q.employee_id)])
  }
  if (q.employee_ids) {
    const ids = (q.employee_ids as string).split(',').map(Number).filter(n => !isNaN(n))
    highlightEmployeeIds.value = new Set(ids)
  }
  if (q.requirement_id) {
    fromRequirementId.value = Number(q.requirement_id)
  }
}

onMounted(() => {
  applyQueryParams(route.query as Record<string, any>)
  fetchData()
})

watch(() => route.query, (q) => {
  applyQueryParams(q as Record<string, any>)
  fetchData()
})
</script>

<style scoped>
.gantt-header-row {
  height: 52px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 12px;
}
.gantt-team-row {
  height: 36px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 12px;
}
.gantt-member-row {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 12px;
}
.gantt-day-header {
  width: 52px;
  min-width: 52px;
  text-align: center;
  padding: 8px 0;
  border-right: 1px solid #f3f4f6;
  font-size: 11px;
  color: #6b7280;
}
.gantt-day-cell {
  width: 52px;
  min-width: 52px;
  height: 100%;
  border-right: 1px solid #f3f4f6;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gantt-bar {
  position: absolute;
  top: 50%;
  left: 2px;
  right: 2px;
  transform: translateY(-50%);
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 0 6px;
  cursor: pointer;
  z-index: 5;
  transition: filter 0.15s;
  overflow: hidden;
}
.gantt-bar:hover {
  filter: brightness(0.92);
}
.gantt-bar-schedule {
  background: #dbeafe;
  color: #1d4ed8;
  border: 1px solid #93c5fd;
}
.gantt-bar-leave {
  background: #ffedd5;
  color: #c2410c;
  border: 1px solid #fdba74;
}
.gantt-bar-training {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}
.gantt-bar-meeting {
  background: #f3e8ff;
  color: #7e22ce;
  border: 1px solid #c084fc;
}
</style>
