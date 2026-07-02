<template>
  <div class="flex h-full">
    <!-- Left Module Sidebar -->
    <div class="w-[240px] flex-shrink-0 border-r border-gray-200 bg-white overflow-y-auto">
      <div class="p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-gray-700">用例模块</h3>
          <el-button link size="small" type="primary" @click="startAddModule">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        <div
          class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="selectedModule === null ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'"
          @click="selectModule(null)"
        >
          <span class="text-sm font-medium">全部用例</span>
          <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{{ total }}</span>
        </div>
        <!-- 需求根节点 + 子模块 -->
        <div v-for="group in requirementGroups" :key="'req-' + group.requirement_id" class="mb-1">
          <div
            class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors"
            :class="selectedModule === reqRootKey(group.requirement_id) ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'"
            @click="selectModule(reqRootKey(group.requirement_id))"
          >
            <div class="flex items-center gap-1 flex-1 min-w-0" @click.stop="toggleRequirement(group.requirement_id)">
              <span class="text-xs text-gray-400 w-3">{{ expandedRequirements.has(group.requirement_id) ? '▼' : '▶' }}</span>
              <span class="text-sm font-medium truncate" :title="group.requirement_title">{{ group.requirement_title }}</span>
            </div>
            <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full ml-1">{{ group.count }}</span>
          </div>
          <div v-if="expandedRequirements.has(group.requirement_id)" class="ml-1 mt-0.5">
            <ModuleTreeNodes
              :nodes="buildModuleTree(group.modules)"
              :scope="'requirement'"
              :requirement-id="group.requirement_id"
              :selected-key="selectedModule"
              :expanded-keys="expandedModulePaths"
              @select="(node) => selectModule(reqModulePathKey(group.requirement_id, node.fullPath))"
              @toggle="toggleModulePath('requirement', group.requirement_id, $event)"
            />
          </div>
        </div>
        <!-- 无需求的独立模块（多级树） -->
        <div class="ml-0 mt-0.5">
          <ModuleTreeNodes
            :nodes="standaloneModuleTree"
            :scope="'standalone'"
            :selected-key="selectedModule"
            :expanded-keys="expandedModulePaths"
            @select="(node) => selectModule(standaloneModulePathKey(node.fullPath))"
            @toggle="toggleModulePath('standalone', undefined, $event)"
          />
        </div>
        <!-- 新建模块输入框 -->
        <div v-if="addingModule" class="px-3 py-2 mb-1">
          <input
            v-model="newModuleName"
            class="w-full text-sm px-2 py-1.5 border border-indigo-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-200"
            placeholder="输入模块名称，回车创建"
            @keyup.enter="confirmAddModule"
            @keyup.escape="addingModule = false"
            ref="newModuleInput"
          />
        </div>
        <div
          class="flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors mb-1"
          :class="selectedModule === '__unassigned__' ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-gray-50 text-gray-700'"
          @click="selectModule('__unassigned__')"
        >
          <span class="text-sm text-gray-400 italic">未分配模块</span>
          <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{{ unassignedCount }}</span>
        </div>
      </div>
    </div>

    <!-- Right Main Area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- Top Action Bar -->
      <div class="flex items-center justify-between p-4 border-b border-gray-100 bg-white">
        <div class="flex items-center gap-2">
          <el-button type="primary" color="#4f46e5" class="!rounded-lg" @click="openCreateDialog">
            <el-icon class="mr-1"><Plus /></el-icon>新建
          </el-button>
          <el-button class="!rounded-lg" disabled>
            <el-icon class="mr-1"><Upload /></el-icon>导入
          </el-button>
          <el-button class="!rounded-lg" color="#7c3aed" @click="router.push('/ai-testcase/generate')">
            <el-icon class="mr-1"><MagicStick /></el-icon>AI 生成
          </el-button>
        </div>
        <div class="flex items-center gap-3">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="搜索用例名称..."
            class="!w-56"
            @keyup.enter="fetchList"
            @clear="fetchList"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button-group>
            <el-button :type="viewMode === 'table' ? 'primary' : 'default'" @click="viewMode = 'table'" class="!rounded-l-lg">
              表格
            </el-button>
            <el-button :type="viewMode === 'mindmap' ? 'primary' : 'default'" @click="viewMode = 'mindmap'" class="!rounded-r-lg">
              脑图
            </el-button>
          </el-button-group>
        </div>
      </div>

      <!-- Table View -->
      <div v-if="viewMode === 'table'" class="flex-1 overflow-auto p-4" v-loading="loading">
        <el-table
          :data="tableData"
          stripe
          class="w-full"
          @selection-change="handleSelectionChange"
          row-class-name="cursor-pointer"
        >
          <el-table-column type="selection" width="45" />
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="用例名称" min-width="220">
            <template #default="{ row }">
              <span class="text-indigo-600 hover:text-indigo-800 cursor-pointer font-medium" @click="openEditDialog(row)">
                {{ row.title }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="module" label="所属模块" width="130">
            <template #default="{ row }">
              <span class="text-gray-600">{{ row.module || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="用例等级" width="100">
            <template #default="{ row }">
              <el-tag :color="priorityColor(row.priority)" effect="dark" size="small" class="!border-0 !text-white !rounded-md">
                {{ row.priority || '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="评审状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" effect="light" size="small" round>
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="标签" width="100">
            <template #default="{ row }">
              <el-tag effect="plain" size="small" class="!rounded-md">
                {{ caseTypeLabel(row.case_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="80">
            <template #default="{ row }">
              <el-tag :type="row.source === 'ai' ? 'warning' : 'info'" effect="light" size="small" round>
                {{ row.source === 'ai' ? 'AI' : '手工' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="assignee" label="责任人" width="100">
            <template #default="{ row }">
              <span class="text-gray-600">{{ row.assignee || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="160">
            <template #default="{ row }">
              <span class="text-gray-500 text-xs">{{ formatTime(row.updated_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button link type="success" size="small" @click="handleExecute(row)">执行</el-button>
              <el-popconfirm title="确认删除该用例？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button link type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- Pagination -->
        <div class="flex justify-end mt-4 pt-4 border-t border-gray-100" v-if="total > 0">
          <el-pagination
            v-model:current-page="query.page"
            v-model:page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            background
            @size-change="fetchList"
            @current-change="fetchList"
          />
        </div>
      </div>

      <!-- MindMap View -->
      <div v-else class="flex-1 overflow-hidden p-4 min-h-0 flex flex-col" v-loading="mindMapLoading">
        <div v-if="!mindMapData || !mindMapData.children?.length" class="flex-1 flex flex-col items-center justify-center text-gray-400">
          <p class="text-lg mb-2">暂无数据</p>
          <p class="text-sm">请先在侧边栏创建模块，或切换到表格视图新建用例</p>
        </div>
        <MindMapComponent
          v-else
          :key="mindMapKey"
          class="flex-1 min-h-0"
          :data="mindMapData"
          :editable="true"
          @save="handleMindMapSave"
        />
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingCase ? '编辑用例' : '新建用例'"
      width="720px"
      class="!rounded-2xl"
      destroy-on-close
    >
      <el-form :model="form" label-width="90px" class="pr-4">
        <el-form-item label="用例名称" required>
          <el-input v-model="form.title" placeholder="请输入用例名称" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="所属模块">
            <el-autocomplete
              v-model="form.module"
              :fetch-suggestions="queryModuleSuggestions"
              placeholder="输入或选择模块"
              class="w-full"
            />
          </el-form-item>
          <el-form-item label="用例等级">
            <el-select v-model="form.priority" placeholder="选择等级" class="w-full">
              <el-option label="P0 - 最高" value="P0" />
              <el-option label="P1 - 高" value="P1" />
              <el-option label="P2 - 中" value="P2" />
              <el-option label="P3 - 低" value="P3" />
            </el-select>
          </el-form-item>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="用例类型">
            <el-select v-model="form.case_type" placeholder="选择类型" class="w-full">
              <el-option label="功能测试" value="functional" />
              <el-option label="性能测试" value="performance" />
              <el-option label="安全测试" value="security" />
              <el-option label="兼容性测试" value="compatibility" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联项目">
            <el-input v-model.number="form.project_id" placeholder="项目 ID（可选）" type="number" />
          </el-form-item>
        </div>
        <el-form-item label="前置条件">
          <el-input v-model="form.precondition" type="textarea" :rows="2" placeholder="测试前置条件" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="用例描述信息" />
        </el-form-item>

        <!-- Steps -->
        <el-form-item label="测试步骤">
          <div class="w-full">
            <el-table :data="form.steps" border size="small" class="mb-2">
              <el-table-column label="序号" width="60" align="center">
                <template #default="{ $index }">{{ $index + 1 }}</template>
              </el-table-column>
              <el-table-column label="操作步骤" min-width="180">
                <template #default="{ row }">
                  <el-input v-model="row.action" size="small" placeholder="输入操作步骤" />
                </template>
              </el-table-column>
              <el-table-column label="预期结果" min-width="180">
                <template #default="{ row }">
                  <el-input v-model="row.expected" size="small" placeholder="输入预期结果" />
                </template>
              </el-table-column>
              <el-table-column label="测试数据" width="140">
                <template #default="{ row }">
                  <el-input v-model="row.test_data" size="small" placeholder="测试数据" />
                </template>
              </el-table-column>
              <el-table-column label="" width="60" align="center">
                <template #default="{ $index }">
                  <el-button link type="danger" size="small" @click="removeStep($index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button size="small" @click="addStep" class="!rounded-lg">
              <el-icon class="mr-1"><Plus /></el-icon>添加步骤
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false" class="!rounded-lg">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="handleSave" :loading="saving" class="!rounded-lg">
          {{ editingCase ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Search, Upload, MagicStick, Delete } from '@element-plus/icons-vue'
import { getTestCases, createTestCase, updateTestCase, deleteTestCase, getTestCaseModules } from '../../api/test-cases'
import { unwrapApiData } from '../../utils/request'
import MindMapComponent from '../../components/MindMap.vue'
import type { MindMapNode } from '../../components/MindMap.vue'
import ModuleTreeNodes from '../../components/ModuleTreeNodes.vue'
import {
  buildCaseModuleMindMapBranches,
  buildModuleTree,
  joinModulePath,
  moduleExpandKey,
  moduleMatchesPrefix,
  parseModulePath,
  parseModuleSelection,
  reqModulePathKey,
  reqRootKey,
  standaloneModulePathKey,
  type ModuleTreeNode,
} from '../../utils/modulePath'

interface TestStep {
  action: string
  expected: string
  test_data: string
}

interface TestCase {
  id: number
  title: string
  module: string | null
  priority: string
  status: string
  case_type: string
  source: string
  assignee: string | null
  precondition: string
  description: string
  steps: TestStep[]
  project_id: number | null
  requirement_id: number | null
  updated_at: string
  created_at: string
}

interface ModuleInfo {
  name: string
  count: number
}

interface RequirementModuleGroup {
  requirement_id: number
  requirement_title: string
  count: number
  modules: ModuleInfo[]
}

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const tableData = ref<TestCase[]>([])
const total = ref(0)
const modules = ref<ModuleInfo[]>([])
const requirementGroups = ref<RequirementModuleGroup[]>([])
const standaloneModules = ref<ModuleInfo[]>([])
const expandedRequirements = ref<Set<number>>(new Set())
const expandedModulePaths = ref<Set<string>>(new Set())
const selectedModule = ref<string | null>(null)
const viewMode = ref<'table' | 'mindmap'>('table')
const dialogVisible = ref(false)
const editingCase = ref<TestCase | null>(null)
const selectedRows = ref<TestCase[]>([])
const unassignedCount = ref(0)

const addingModule = ref(false)
const newModuleName = ref('')
const newModuleInput = ref<HTMLInputElement | null>(null)
const renamingModule = ref<string | null>(null)
const renameValue = ref('')
const renameInput = ref<HTMLInputElement | null>(null)
const customModules = ref<string[]>(JSON.parse(localStorage.getItem('custom_modules') || '[]'))

const query = reactive({
  keyword: '',
  module: '' as string | null,
  module_prefix: '' as string | null,
  requirement_id: null as number | null,
  page: 1,
  page_size: 20,
})

const standaloneModuleTree = computed(() => buildModuleTree(standaloneModules.value))

const form = reactive({
  title: '',
  module: '',
  priority: 'P2',
  case_type: 'functional',
  precondition: '',
  description: '',
  project_id: null as number | null,
  requirement_id: null as number | null,
  steps: [{ action: '', expected: '', test_data: '' }] as TestStep[],
})

const allCasesForMindMap = ref<TestCase[]>([])
const mindMapLoading = ref(false)
const mindMapKey = ref(0)

function caseToMindMapNode(tc: TestCase): MindMapNode {
  return {
    content: tc.title,
    children: (tc.steps || []).map((s, i) => ({
      content: `${i + 1}. ${s.action}`,
      payload: { description: (s as any).expected_result || s.expected || '' },
    })),
    payload: { id: String(tc.id), priority: tc.priority, type: tc.case_type },
  }
}

function filterCasesForMindMap(cases: TestCase[]): TestCase[] {
  const sel = selectedModule.value
  if (!sel) return cases
  if (sel === '__unassigned__') return cases.filter(tc => !tc.module)
  const parsed = parseModuleSelection(sel)
  if (parsed.kind === 'requirement') {
    return cases.filter(tc => Number(tc.requirement_id) === parsed.requirementId)
  }
  if (parsed.kind === 'requirement_path') {
    return cases.filter(
      tc => Number(tc.requirement_id) === parsed.requirementId
        && moduleMatchesPrefix(tc.module, parsed.modulePath || ''),
    )
  }
  if (parsed.kind === 'standalone_path') {
    return cases.filter(
      tc => !tc.requirement_id && moduleMatchesPrefix(tc.module, parsed.modulePath || ''),
    )
  }
  if (parsed.kind === 'legacy') {
    return cases.filter(tc => moduleMatchesPrefix(tc.module, parsed.legacyModule || ''))
  }
  return cases
}

const mindMapData = computed<MindMapNode | null>(() => {
  const cases = filterCasesForMindMap(allCasesForMindMap.value)
  if (!cases.length) return null

  const reqTitleMap = new Map(
    requirementGroups.value.map(g => [Number(g.requirement_id), g.requirement_title]),
  )
  const reqCaseMap = new Map<number, TestCase[]>()
  const standaloneCases: TestCase[] = []
  const unassigned: TestCase[] = []

  for (const tc of cases) {
    if (!tc.module) {
      unassigned.push(tc)
      continue
    }
    const reqId = tc.requirement_id != null ? Number(tc.requirement_id) : null
    if (reqId != null && !Number.isNaN(reqId)) {
      if (!reqCaseMap.has(reqId)) reqCaseMap.set(reqId, [])
      reqCaseMap.get(reqId)!.push(tc)
    } else {
      standaloneCases.push(tc)
    }
  }

  const children: MindMapNode[] = []

  for (const [reqId, reqCases] of [...reqCaseMap.entries()].sort((a, b) => {
    const ta = reqTitleMap.get(a[0]) || ''
    const tb = reqTitleMap.get(b[0]) || ''
    return ta.localeCompare(tb, 'zh-CN')
  })) {
    children.push({
      content: reqTitleMap.get(reqId) || `需求#${reqId}`,
      children: buildCaseModuleMindMapBranches(
        reqCases,
        tc => tc.module,
        tc => caseToMindMapNode(tc as TestCase),
        reqId,
      ) as MindMapNode[],
      payload: { type: 'requirement', requirement_id: reqId },
    })
  }

  if (standaloneCases.length) {
    children.push(...buildCaseModuleMindMapBranches(
      standaloneCases,
      tc => tc.module,
      tc => caseToMindMapNode(tc as TestCase),
    ) as MindMapNode[])
  }

  if (unassigned.length) {
    children.push({
      content: '未分配模块',
      children: unassigned.map(caseToMindMapNode),
      payload: { type: 'module', module_path: '' },
    })
  }

  if (!children.length) return null
  return { content: '测试用例', children }
})

async function fetchAllCasesForMindMap() {
  mindMapLoading.value = true
  try {
    const pageSize = 100
    let page = 1
    let totalCount = 0
    const merged: TestCase[] = []
    do {
      const res = await getTestCases({ page, page_size: pageSize })
      const payload = unwrapApiData<{ items?: TestCase[]; list?: TestCase[]; total?: number }>(res)
      const batch = payload?.items ?? payload?.list ?? []
      totalCount = payload?.total ?? batch.length
      merged.push(...batch)
      page += 1
    } while (merged.length < totalCount && page <= 50)
    allCasesForMindMap.value = merged
    mindMapKey.value += 1
  } catch (e: any) {
    allCasesForMindMap.value = []
    ElMessage.error(e.message || '加载脑图数据失败')
  } finally {
    mindMapLoading.value = false
  }
}

function priorityColor(p: string) {
  const map: Record<string, string> = { P0: '#ef4444', P1: '#f97316', P2: '#3b82f6', P3: '#9ca3af' }
  return map[p] || '#9ca3af'
}

function statusTagType(s: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    active: 'success', draft: 'info', deprecated: 'danger'
  }
  return map[s] || 'info'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { active: '已评审', draft: '草稿', deprecated: '已废弃' }
  return map[s] || s || '草稿'
}

function caseTypeLabel(t: string) {
  const map: Record<string, string> = { functional: '功能', performance: '性能', security: '安全', compatibility: '兼容' }
  return map[t] || t || '功能'
}

function formatTime(t: string) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function toggleModulePath(
  scope: 'requirement' | 'standalone',
  reqId: number | undefined,
  node: ModuleTreeNode,
) {
  const scopeKey = scope === 'requirement' ? `req-${reqId}` : 'standalone'
  const key = moduleExpandKey(scopeKey, node.fullPath)
  const next = new Set(expandedModulePaths.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedModulePaths.value = next
}

function expandAllModulePaths() {
  const next = new Set<string>()
  for (const group of requirementGroups.value) {
    const walk = (nodes: ModuleTreeNode[], scopeKey: string) => {
      for (const node of nodes) {
        if (node.children.length) {
          next.add(moduleExpandKey(scopeKey, node.fullPath))
          walk(node.children, scopeKey)
        }
      }
    }
    walk(buildModuleTree(group.modules), `req-${group.requirement_id}`)
  }
  walk(standaloneModuleTree.value, 'standalone')
  expandedModulePaths.value = next
}

function toggleRequirement(reqId: number) {
  const next = new Set(expandedRequirements.value)
  if (next.has(reqId)) next.delete(reqId)
  else next.add(reqId)
  expandedRequirements.value = next
}

function selectModule(mod: string | null) {
  selectedModule.value = mod
  query.requirement_id = null
  query.module = ''
  query.module_prefix = ''
  if (mod === null) {
    // 全部用例
  } else if (mod === '__unassigned__') {
    query.module = '__unassigned__'
  } else {
    const parsed = parseModuleSelection(mod)
    if (parsed.kind === 'requirement') {
      query.requirement_id = parsed.requirementId ?? null
    } else if (parsed.kind === 'requirement_path') {
      query.requirement_id = parsed.requirementId ?? null
      query.module_prefix = parsed.modulePath || ''
    } else if (parsed.kind === 'standalone_path') {
      query.module_prefix = parsed.modulePath || ''
    } else if (parsed.kind === 'legacy') {
      query.module_prefix = parsed.legacyModule || ''
    }
  }
  query.page = 1
  fetchList()
  if (viewMode.value === 'mindmap') {
    mindMapKey.value += 1
  }
}

function handleSelectionChange(rows: TestCase[]) {
  selectedRows.value = rows
}

function openCreateDialog() {
  editingCase.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: TestCase) {
  editingCase.value = row
  form.title = row.title
  form.module = row.module || ''
  form.priority = row.priority || 'P2'
  form.case_type = row.case_type || 'functional'
  form.precondition = row.precondition || ''
  form.description = row.description || ''
  form.project_id = row.project_id
  form.requirement_id = row.requirement_id
  form.steps = row.steps?.length ? [...row.steps] : [{ action: '', expected: '', test_data: '' }]
  dialogVisible.value = true
}

function resetForm() {
  form.title = ''
  form.module = ''
  form.priority = 'P2'
  form.case_type = 'functional'
  form.precondition = ''
  form.description = ''
  form.project_id = null
  form.requirement_id = null
  form.steps = [{ action: '', expected: '', test_data: '' }]
}

function addStep() {
  form.steps.push({ action: '', expected: '', test_data: '' })
}

function removeStep(index: number) {
  if (form.steps.length > 1) {
    form.steps.splice(index, 1)
  }
}

function queryModuleSuggestions(queryString: string, cb: (results: any[]) => void) {
  const names = new Set<string>()
  for (const m of standaloneModules.value) names.add(m.name)
  for (const g of requirementGroups.value) {
    for (const m of g.modules) names.add(m.name)
  }
  for (const m of modules.value) names.add(m.name)
  const suggestions = [...names]
    .map(name => ({ value: name }))
    .filter(s => !queryString || s.value.toLowerCase().includes(queryString.toLowerCase()))
  cb(suggestions)
}

function handleExecute(row: TestCase) {
  ElMessage.info(`执行用例: ${row.title}`)
}

async function fetchList() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { ...query }
    if (!params.requirement_id) delete params.requirement_id
    if (!params.module) delete params.module
    if (!params.module_prefix) delete params.module_prefix
    const res = await getTestCases(params)
    const payload = unwrapApiData<{ items?: TestCase[]; list?: TestCase[]; total?: number }>(res)
    tableData.value = payload?.items ?? payload?.list ?? []
    total.value = payload?.total ?? 0
  } catch (e: any) {
    ElMessage.error(e.message || '加载用例列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchModules() {
  try {
    const res = await getTestCaseModules()
    const payload = unwrapApiData<{
      modules?: ModuleInfo[]
      requirement_groups?: RequirementModuleGroup[]
      standalone_modules?: ModuleInfo[]
      unassigned_count?: number
    } | string[]>(res)
    const normalizeModuleName = (name: string) =>
      name.replace(/<[^>]+>/g, '').trim()
    requirementGroups.value = (Array.isArray(payload) ? [] : (payload?.requirement_groups ?? []))
      .map(g => ({
        ...g,
        modules: (g.modules || [])
          .map(m => ({ ...m, name: normalizeModuleName(m.name) }))
          .filter(m => m.name),
      }))
    standaloneModules.value = (Array.isArray(payload) ? [] : (payload?.standalone_modules ?? []))
      .map(m => ({ ...m, name: normalizeModuleName(m.name) }))
      .filter(m => m.name)
    expandedRequirements.value = new Set(requirementGroups.value.map(g => g.requirement_id))
    expandAllModulePaths()
    const rawModules = Array.isArray(payload)
      ? payload.map((name) => ({ name: String(name), count: 0 }))
      : payload?.modules ?? []
    const serverModules: ModuleInfo[] = rawModules
      .map((m: any) => (typeof m === 'string' ? { name: m, count: 0 } : m))
      .filter((m: ModuleInfo) => m.name)
    unassignedCount.value = Array.isArray(payload)
      ? 0
      : Number(payload?.unassigned_count ?? 0)
    const serverNames = new Set(serverModules.map(m => m.name))
    const extra: ModuleInfo[] = customModules.value
      .filter(n => !serverNames.has(n))
      .map(n => ({ name: n, count: 0 }))
    modules.value = [...serverModules, ...extra]
    standaloneModules.value = [
      ...standaloneModules.value,
      ...extra.filter(e => !standaloneModules.value.some(s => s.name === e.name)),
    ]
  } catch {
    modules.value = customModules.value.map(n => ({ name: n, count: 0 }))
    requirementGroups.value = []
    standaloneModules.value = modules.value
  }
}

function startAddModule() {
  addingModule.value = true
  newModuleName.value = ''
  nextTick(() => {
    (newModuleInput.value as any)?.focus?.()
  })
}

function confirmAddModule() {
  const name = newModuleName.value.trim()
  if (!name) { addingModule.value = false; return }
  if (modules.value.some(m => m.name === name) || standaloneModules.value.some(m => m.name === name)) {
    ElMessage.warning('模块已存在')
    return
  }
  customModules.value.push(name)
  localStorage.setItem('custom_modules', JSON.stringify(customModules.value))
  standaloneModules.value.push({ name, count: 0 })
  addingModule.value = false
  ElMessage.success(`模块「${name}」已创建`)
}

function handleModuleAction(cmd: string, modName: string) {
  if (cmd === 'rename') {
    renamingModule.value = modName
    renameValue.value = modName
    nextTick(() => {
      (renameInput.value as any)?.[0]?.focus?.()
    })
  } else if (cmd === 'delete') {
    const mod = standaloneModules.value.find(m => m.name === modName)
    if (mod && mod.count > 0) {
      ElMessage.warning('该模块下有用例，请先移除或转移用例')
      return
    }
    customModules.value = customModules.value.filter(n => n !== modName)
    localStorage.setItem('custom_modules', JSON.stringify(customModules.value))
    standaloneModules.value = standaloneModules.value.filter(m => m.name !== modName)
    modules.value = modules.value.filter(m => m.name !== modName)
    if (selectedModule.value === modName) selectModule(null)
    ElMessage.success('模块已删除')
  }
}

async function confirmRenameModule(oldName: string) {
  const newName = renameValue.value.trim()
  renamingModule.value = null
  if (!newName || newName === oldName) return
  if (modules.value.some(m => m.name === newName)) {
    ElMessage.warning('模块名已存在')
    return
  }
  const mod = modules.value.find(m => m.name === oldName)
  if (mod && mod.count > 0) {
    try {
      const res = await getTestCases({ module: oldName, page: 1, page_size: 100 })
      const payload = unwrapApiData<{ items?: TestCase[]; list?: TestCase[] }>(res)
      const cases = payload?.items ?? payload?.list ?? []
      for (const tc of cases) {
        await updateTestCase(tc.id, { ...tc, module: newName })
      }
    } catch {
      ElMessage.error('重命名失败')
      return
    }
  }
  const idx = customModules.value.indexOf(oldName)
  if (idx >= 0) customModules.value[idx] = newName
  else customModules.value.push(newName)
  localStorage.setItem('custom_modules', JSON.stringify(customModules.value))
  if (selectedModule.value === oldName) selectedModule.value = newName
  ElMessage.success('模块已重命名')
  fetchModules()
  fetchList()
}

async function handleMindMapSave(data: MindMapNode) {
  if (!data.children?.length) return
  saving.value = true
  try {
    let created = 0
    let updated = 0

    async function saveSingleCase(
      caseNode: MindMapNode,
      modulePath: string | null,
      requirementId: number | null,
    ) {
      const title = caseNode.content
      if (!title?.trim()) return
      const steps = (caseNode.children || [])
        .map(s => ({
          action: s.content?.replace(/^\d+\.\s*/, '') || '',
          expected: s.payload?.description || '',
          test_data: '',
        }))
        .filter(s => s.action.trim())
      const caseData: any = {
        title,
        module: modulePath,
        priority: caseNode.payload?.priority || 'P2',
        case_type: caseNode.payload?.type || 'functional',
        requirement_id: requirementId,
        steps,
      }
      const existingId = caseNode.payload?.id ? parseInt(caseNode.payload.id) : null
      if (existingId && !isNaN(existingId)) {
        await updateTestCase(existingId, caseData)
        updated++
      } else {
        await createTestCase(caseData)
        created++
      }
    }

    async function saveModuleBranch(
      node: MindMapNode,
      requirementId: number | null,
    ) {
      const modulePath = node.payload?.module_path
        ? String(node.payload.module_path)
        : (node.content === '未分配模块' ? null : node.content)

      for (const child of node.children || []) {
        if (child.payload?.type === 'module') {
          await saveModuleBranch(child, requirementId)
        } else if (child.payload?.id) {
          await saveSingleCase(child, modulePath, requirementId)
        }
      }
    }

    for (const rootNode of data.children) {
      if (rootNode.payload?.type === 'requirement') {
        const reqId = rootNode.payload?.requirement_id ?? null
        for (const modNode of rootNode.children || []) {
          await saveModuleBranch(modNode, reqId)
        }
      } else if (rootNode.payload?.type === 'module') {
        await saveModuleBranch(rootNode, null)
      } else if (rootNode.content === '未分配模块') {
        for (const caseNode of rootNode.children || []) {
          if (caseNode.payload?.id) await saveSingleCase(caseNode, null, null)
        }
      }
    }

    ElMessage.success(`保存成功${created ? `，新建 ${created} 条` : ''}${updated ? `，更新 ${updated} 条` : ''}`)
    fetchList()
    fetchModules()
    fetchAllCasesForMindMap()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

async function handleSave() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入用例名称')
    return
  }
  saving.value = true
  try {
    const data = {
      title: form.title,
      module: form.module || null,
      priority: form.priority,
      case_type: form.case_type,
      precondition: form.precondition,
      description: form.description,
      project_id: form.project_id || null,
      requirement_id: form.requirement_id || null,
      steps: form.steps.filter(s => s.action.trim()),
    }
    if (editingCase.value) {
      await updateTestCase(editingCase.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await createTestCase(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchList()
    fetchModules()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deleteTestCase(id)
    ElMessage.success('删除成功')
    fetchList()
    fetchModules()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

watch(viewMode, (mode) => {
  if (mode === 'mindmap') fetchAllCasesForMindMap()
})

onMounted(() => {
  fetchList()
  fetchModules()
})
</script>

<style scoped>
:deep(.el-table .cell) {
  padding: 8px 12px;
}
</style>
