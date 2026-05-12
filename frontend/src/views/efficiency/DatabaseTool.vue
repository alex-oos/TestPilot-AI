<template>
  <div class="database-tool">
    <!-- 连接配置区 -->
    <div class="config-panel">
      <div class="panel-header">
        <h3>数据库连接</h3>
        <div class="header-actions">
          <el-select v-model="dbForm.db_type" size="small" style="width: 140px">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
          </el-select>
        </div>
      </div>
      <el-form :model="dbForm" label-width="80px" size="default" class="config-form">
        <div class="form-row">
          <el-form-item label="主机">
            <el-input v-model="dbForm.host" placeholder="127.0.0.1" />
          </el-form-item>
          <el-form-item label="端口" class="port-field">
            <el-input-number v-model="dbForm.port" :min="1" :max="65535" controls-position="right" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="用户名">
            <el-input v-model="dbForm.username" placeholder="root" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="dbForm.password" type="password" show-password placeholder="请输入密码" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="数据库">
            <el-select
              v-model="dbForm.database"
              filterable allow-create clearable
              placeholder="选择或输入数据库名"
              style="width: 100%"
            >
              <el-option v-for="db in databaseList" :key="db" :label="db" :value="db" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <div class="btn-group">
              <el-button type="primary" @click="handleTestDBConnect" :loading="dbConnecting">
                测试连接
              </el-button>
              <el-button @click="handleLoadTables" :disabled="!dbConnected || !dbForm.database" :loading="tablesLoading">
                加载表
              </el-button>
            </div>
          </el-form-item>
        </div>
      </el-form>
      <div v-if="dbConnectResult" class="connect-status" :class="dbConnected ? 'success' : 'error'">
        <span class="status-icon">{{ dbConnected ? '✅' : '❌' }}</span>
        <span>{{ dbConnectResult }}</span>
      </div>
    </div>

    <!-- 工作区 -->
    <div v-if="dbConnected" class="workspace">
      <div class="workspace-layout">
        <!-- 左侧: 表列表 -->
        <div class="table-sidebar" v-if="tableList.length > 0">
          <div class="sidebar-header">
            <span class="sidebar-title">表列表 ({{ tableList.length }})</span>
            <el-input
              v-model="tableSearch" size="small"
              placeholder="搜索表名" clearable prefix-icon="Search"
              class="table-search"
            />
          </div>
          <div class="table-list">
            <div
              v-for="table in filteredTables" :key="table"
              class="table-item"
              :class="{ active: selectedTable === table }"
              @click="handleSelectTable(table)"
            >
              <span class="table-name">{{ table }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧: 查询区 -->
        <div class="query-area">
          <!-- 查询模式切换 -->
          <div class="mode-switcher">
            <el-radio-group v-model="queryMode" size="small">
              <el-radio-button value="sql">SQL 查询</el-radio-button>
              <el-radio-button value="ai">AI 自然语言</el-radio-button>
            </el-radio-group>
          </div>

          <!-- SQL 模式 -->
          <div v-if="queryMode === 'sql'" class="sql-editor">
            <div class="editor-header">
              <span>SQL 编辑器</span>
              <div class="editor-actions">
                <el-button size="small" type="primary" @click="handleExecuteQuery" :loading="queryLoading">
                  执行
                </el-button>
                <el-button size="small" @click="sqlInput = ''" text>清空</el-button>
              </div>
            </div>
            <div class="codemirror-wrapper">
              <Codemirror
                v-model="sqlInput"
                :style="{ height: '180px' }"
                :extensions="sqlExtensions"
                placeholder="输入 SQL 查询语句（仅支持 SELECT / SHOW / DESCRIBE / EXPLAIN）"
              />
            </div>
          </div>

          <!-- AI 自然语言模式 -->
          <div v-if="queryMode === 'ai'" class="ai-editor">
            <div class="editor-header">
              <span>AI 自然语言查询</span>
              <div class="editor-actions">
                <el-button size="small" type="primary" @click="handleAIQuery" :loading="aiLoading">
                  生成并执行
                </el-button>
              </div>
            </div>
            <div class="ai-input-area">
              <el-input
                v-model="aiPrompt"
                type="textarea"
                :rows="3"
                placeholder="用自然语言描述你想查询的数据，例如：&#10;- 查看用户表里最近注册的 10 个用户&#10;- 统计每个部门的员工人数&#10;- 找出所有状态为活跃的订单"
                class="ai-textarea"
              />
            </div>
            <div v-if="generatedSQL" class="generated-sql">
              <div class="generated-header">
                <span>AI 生成的 SQL</span>
                <el-button size="small" text @click="useGeneratedSQL">编辑此 SQL</el-button>
              </div>
              <div class="codemirror-wrapper readonly">
                <Codemirror
                  :model-value="generatedSQL"
                  :style="{ height: 'auto', minHeight: '40px' }"
                  :extensions="sqlReadonlyExtensions"
                  :disabled="true"
                />
              </div>
            </div>
          </div>

          <!-- 查询结果 -->
          <div v-if="queryResult" class="query-result">
            <div class="result-header">
              <span>查询结果</span>
              <span class="result-meta">
                共 {{ queryResult.total }} 条{{ queryResult.truncated ? '（显示前500条）' : '' }}
              </span>
            </div>
            <el-table
              :data="queryResult.rows.map((row: any[]) => rowToObj(queryResult!.columns, row))"
              stripe border size="small" max-height="400" class="result-table"
            >
              <el-table-column
                v-for="col in queryResult.columns" :key="col"
                :prop="col" :label="col" min-width="120" show-overflow-tooltip
              />
            </el-table>
          </div>

          <!-- 表结构 -->
          <div v-if="tableSchema" class="query-result">
            <div class="result-header">
              <span>表结构: {{ selectedTable }}</span>
            </div>
            <el-table
              :data="tableSchema.rows.map((row: any[]) => rowToObj(tableSchema!.columns, row))"
              stripe border size="small" max-height="400" class="result-table"
            >
              <el-table-column
                v-for="col in tableSchema.columns" :key="col"
                :prop="col" :label="col" min-width="120" show-overflow-tooltip
              />
            </el-table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Codemirror } from 'vue-codemirror'
import { sql, MySQL, PostgreSQL } from '@codemirror/lang-sql'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import {
  testDBConnection, executeDBQuery, listDBTables, getTableSchema, aiDBQuery,
} from '../../api/efficiency-tools'

const dbForm = ref({
  host: '', port: 3306, username: 'root', password: '', database: '', db_type: 'mysql',
})

watch(() => dbForm.value.db_type, (val) => {
  dbForm.value.port = val === 'postgresql' ? 5432 : 3306
})

const dbConnecting = ref(false)
const dbConnected = ref(false)
const dbConnectResult = ref('')
const databaseList = ref<string[]>([])
const tableList = ref<string[]>([])
const tablesLoading = ref(false)
const tableSearch = ref('')
const selectedTable = ref('')
const tableSchema = ref<{ columns: string[]; rows: any[][] } | null>(null)

const queryMode = ref<'sql' | 'ai'>('sql')
const sqlInput = ref('')
const queryLoading = ref(false)
const queryResult = ref<{ columns: string[]; rows: any[][]; total: number; truncated: boolean } | null>(null)

const aiPrompt = ref('')
const aiLoading = ref(false)
const generatedSQL = ref('')

const sqlDialect = computed(() => dbForm.value.db_type === 'postgresql' ? PostgreSQL : MySQL)

const sqlExtensions = computed(() => [
  sql({ dialect: sqlDialect.value, upperCaseKeywords: true }),
  oneDark,
  EditorView.lineWrapping,
])

const sqlReadonlyExtensions = computed(() => [
  sql({ dialect: sqlDialect.value }),
  oneDark,
  EditorView.lineWrapping,
  EditorState.readOnly.of(true),
])

const filteredTables = computed(() => {
  if (!tableSearch.value) return tableList.value
  const keyword = tableSearch.value.toLowerCase()
  return tableList.value.filter(t => t.toLowerCase().includes(keyword))
})

function rowToObj(columns: string[], row: any[]): Record<string, any> {
  const obj: Record<string, any> = {}
  columns.forEach((col, i) => { obj[col] = row[i] })
  return obj
}

function useGeneratedSQL() {
  sqlInput.value = generatedSQL.value
  queryMode.value = 'sql'
}

async function handleTestDBConnect() {
  if (!dbForm.value.host || !dbForm.value.username) {
    ElMessage.warning('请填写主机和用户名')
    return
  }
  dbConnecting.value = true
  dbConnected.value = false
  dbConnectResult.value = ''
  tableList.value = []
  queryResult.value = null
  tableSchema.value = null
  try {
    const res: any = await testDBConnection(dbForm.value)
    if (res.code === 0 && res.data?.connected) {
      dbConnected.value = true
      const label = dbForm.value.db_type === 'postgresql' ? 'PostgreSQL' : 'MySQL'
      dbConnectResult.value = `连接成功 | ${label} ${res.data.version}`
      if (res.data.databases?.length) {
        databaseList.value = res.data.databases
      }
    } else {
      dbConnectResult.value = res.msg || '连接失败'
    }
  } catch (e: any) {
    dbConnectResult.value = e.message || '连接失败'
  } finally {
    dbConnecting.value = false
  }
}

async function handleLoadTables() {
  if (!dbForm.value.database) return
  tablesLoading.value = true
  tableList.value = []
  try {
    const res: any = await listDBTables(dbForm.value)
    if (res.code === 0) {
      tableList.value = res.data.tables || []
    } else {
      ElMessage.error(res.msg || '加载失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    tablesLoading.value = false
  }
}

async function handleSelectTable(table: string) {
  selectedTable.value = table
  const q = dbForm.value.db_type === 'postgresql'
    ? `SELECT * FROM "${table}" LIMIT 50`
    : `SELECT * FROM \`${table}\` LIMIT 50`
  sqlInput.value = q
  tableSchema.value = null
  try {
    const res: any = await getTableSchema({ ...dbForm.value, sql: table })
    if (res.code === 0) tableSchema.value = res.data
  } catch {}
}

async function handleExecuteQuery() {
  if (!sqlInput.value.trim()) {
    ElMessage.warning('请输入 SQL 语句')
    return
  }
  queryLoading.value = true
  queryResult.value = null
  try {
    const res: any = await executeDBQuery({ ...dbForm.value, sql: sqlInput.value })
    if (res.code === 0) {
      queryResult.value = res.data
    } else {
      ElMessage.error(res.msg || '查询失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '查询失败')
  } finally {
    queryLoading.value = false
  }
}

async function handleAIQuery() {
  if (!aiPrompt.value.trim()) {
    ElMessage.warning('请输入自然语言描述')
    return
  }
  aiLoading.value = true
  queryResult.value = null
  generatedSQL.value = ''
  try {
    const res: any = await aiDBQuery({ ...dbForm.value, prompt: aiPrompt.value })
    if (res.code === 0) {
      generatedSQL.value = res.data.generated_sql || ''
      if (res.data.executed && res.data.columns) {
        queryResult.value = {
          columns: res.data.columns,
          rows: res.data.rows,
          total: res.data.total,
          truncated: res.data.truncated,
        }
      } else if (res.data.error) {
        ElMessage.warning(res.data.error)
      }
    } else {
      ElMessage.error(res.msg || 'AI 查询失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'AI 查询失败')
  } finally {
    aiLoading.value = false
  }
}
</script>

<style scoped>
.database-tool { max-width: 1400px; }

.config-panel {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 20px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.panel-header h3 {
  margin: 0; font-size: 15px; font-weight: 600; color: #1e293b;
}
.config-form { max-width: 900px; }
.form-row { display: flex; gap: 16px; }
.form-row > .el-form-item { flex: 1; }
.port-field { max-width: 200px; }
.btn-group { display: flex; gap: 8px; }

.connect-status {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 12px;
}
.connect-status.success { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.connect-status.error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

.workspace { margin-top: 16px; }
.workspace-layout { display: flex; gap: 16px; min-height: 500px; }

.table-sidebar {
  width: 240px; flex-shrink: 0; background: white;
  border: 1px solid #e5e7eb; border-radius: 10px;
  display: flex; flex-direction: column; overflow: hidden;
}
.sidebar-header { padding: 12px; border-bottom: 1px solid #f1f5f9; }
.sidebar-title { font-size: 13px; font-weight: 600; color: #475569; }
.table-search { margin-top: 8px; }
.table-list { flex: 1; overflow-y: auto; padding: 4px; }
.table-item {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: #475569; transition: all 0.15s;
}
.table-item:hover { background: #f1f5f9; }
.table-item.active { background: #eef2ff; color: #4338ca; font-weight: 500; }
.table-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.query-area {
  flex: 1; display: flex; flex-direction: column; gap: 16px; min-width: 0;
}

.mode-switcher {
  display: flex; align-items: center; gap: 12px;
}

.sql-editor, .ai-editor {
  background: white; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
}
.editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e5e7eb;
  font-size: 13px; font-weight: 600; color: #475569;
}
.editor-actions { display: flex; gap: 6px; }

.codemirror-wrapper { border-bottom: 1px solid #e5e7eb; }
.codemirror-wrapper :deep(.cm-editor) { font-size: 13px; }
.codemirror-wrapper :deep(.cm-editor .cm-scroller) { font-family: 'Menlo', 'Monaco', 'Courier New', monospace; }
.codemirror-wrapper.readonly :deep(.cm-editor) { cursor: default; }

.ai-input-area { padding: 0; }
.ai-textarea :deep(.el-textarea__inner) {
  border: none; border-radius: 0;
  font-size: 13px; line-height: 1.6; resize: none;
  padding: 12px 14px;
}

.generated-sql {
  border-top: 1px solid #e5e7eb;
}
.generated-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 14px; background: #f0fdf4; border-bottom: 1px solid #e5e7eb;
  font-size: 12px; font-weight: 600; color: #166534;
}

.query-result {
  background: white; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
}
.result-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e5e7eb;
  font-size: 13px; font-weight: 600; color: #475569;
}
.result-meta { font-weight: 400; color: #94a3b8; font-size: 12px; }
.result-table { width: 100%; }
</style>
