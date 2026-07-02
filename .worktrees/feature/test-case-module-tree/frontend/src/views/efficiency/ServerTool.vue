<template>
  <div class="server-tool">
    <!-- SSH 连接配置 -->
    <div class="config-panel">
      <div class="panel-header">
        <h3>SSH 服务器连接</h3>
      </div>
      <el-form :model="sshForm" label-width="80px" size="default" class="config-form">
        <div class="form-row">
          <el-form-item label="主机">
            <el-input v-model="sshForm.host" placeholder="192.168.1.100" />
          </el-form-item>
          <el-form-item label="端口" class="port-field">
            <el-input-number v-model="sshForm.port" :min="1" :max="65535" controls-position="right" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="用户名">
            <el-input v-model="sshForm.username" placeholder="root" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="sshForm.password" type="password" show-password placeholder="请输入密码" />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item>
            <el-button type="primary" @click="handleSSHTest" :loading="sshTesting">
              测试连接
            </el-button>
          </el-form-item>
        </div>
      </el-form>
      <div v-if="sshConnectResult" class="connect-status" :class="sshConnected ? 'success' : 'error'">
        <span>{{ sshConnected ? '✅' : '❌' }}</span>
        <span>{{ sshConnectResult }}</span>
      </div>
    </div>

    <!-- 命令执行区 -->
    <div v-if="sshConnected" class="workspace" style="margin-top: 16px;">
      <!-- 模式切换 -->
      <div class="mode-switcher">
        <el-radio-group v-model="cmdMode" size="small">
          <el-radio-button value="manual">Linux 命令</el-radio-button>
          <el-radio-button value="ai">AI 自然语言</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 手动命令模式 -->
      <div v-if="cmdMode === 'manual'" class="cmd-editor" style="margin-top: 12px;">
        <div class="editor-header">
          <span>命令编辑器</span>
          <div class="editor-actions">
            <el-button size="small" type="primary" @click="handleExecuteCmd" :loading="cmdLoading">
              执行
            </el-button>
            <el-button size="small" @click="cmdInput = ''" text>清空</el-button>
          </div>
        </div>
        <div class="codemirror-wrapper">
          <Codemirror
            v-model="cmdInput"
            :style="{ height: '120px' }"
            :extensions="shellExtensions"
            placeholder="输入 Linux 命令，如 tail -n 100 /var/log/syslog"
          />
        </div>
        <!-- 常用命令快捷按钮 -->
        <div class="quick-commands">
          <span class="quick-label">常用命令：</span>
          <el-tag
            v-for="qc in quickCommands" :key="qc.cmd"
            class="quick-tag" effect="plain" size="small"
            @click="cmdInput = qc.cmd"
          >
            {{ qc.label }}
          </el-tag>
        </div>
      </div>

      <!-- AI 自然语言模式 -->
      <div v-if="cmdMode === 'ai'" class="ai-editor" style="margin-top: 12px;">
        <div class="editor-header">
          <span>AI 自然语言命令</span>
          <div class="editor-actions">
            <el-button size="small" type="primary" @click="handleAICommand" :loading="aiLoading">
              生成并执行
            </el-button>
          </div>
        </div>
        <div class="ai-input-area">
          <el-input
            v-model="aiPrompt"
            type="textarea"
            :rows="3"
            placeholder="用自然语言描述你想执行的操作，例如：&#10;- 查看 /var/log 下最近修改的日志文件&#10;- 查看系统内存和磁盘使用情况&#10;- 查看 nginx 错误日志最新 50 行"
            class="ai-textarea"
          />
        </div>
        <div v-if="generatedCmd" class="generated-cmd">
          <div class="generated-header">
            <span>AI 生成的命令</span>
            <el-button size="small" text @click="useGeneratedCmd">编辑此命令</el-button>
          </div>
          <div class="codemirror-wrapper readonly">
            <Codemirror
              :model-value="generatedCmd"
              :style="{ height: 'auto', minHeight: '36px' }"
              :extensions="shellReadonlyExtensions"
              :disabled="true"
            />
          </div>
        </div>
      </div>

      <!-- 执行结果输出 -->
      <div v-if="cmdResult" class="cmd-output" style="margin-top: 12px;">
        <div class="output-header">
          <span>执行结果</span>
          <el-tag :type="cmdResult.exit_code === 0 ? 'success' : 'danger'" size="small">
            exit {{ cmdResult.exit_code }}
          </el-tag>
        </div>
        <div class="terminal-output">
          <pre v-if="cmdResult.stdout">{{ cmdResult.stdout }}</pre>
          <pre v-if="cmdResult.stderr" class="stderr">{{ cmdResult.stderr }}</pre>
          <pre v-if="!cmdResult.stdout && !cmdResult.stderr" class="empty">(无输出)</pre>
        </div>
      </div>
    </div>

    <!-- 网络诊断区（折叠） -->
    <el-collapse v-model="diagOpen" style="margin-top: 16px;">
      <el-collapse-item title="网络诊断工具" name="diag">
        <!-- Ping 测试 -->
        <div class="diag-section">
          <h4>Ping 连通性测试</h4>
          <el-form :model="pingForm" label-width="60px" size="small" inline>
            <el-form-item label="主机">
              <el-input v-model="pingForm.host" placeholder="IP 或域名" style="width: 240px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handlePing" :loading="pingLoading" size="small">Ping</el-button>
            </el-form-item>
          </el-form>
          <div v-if="pingResult" class="connect-status small" :class="pingResult.reachable ? 'success' : 'error'">
            <span>{{ pingResult.reachable ? '✅ 网络可达' : '❌ 网络不可达' }}</span>
          </div>
          <div v-if="pingResult?.output" class="ping-output">
            <pre>{{ pingResult.output }}</pre>
          </div>
        </div>

        <!-- 批量端口检测 -->
        <div class="diag-section" style="margin-top: 16px;">
          <h4>批量端口检测</h4>
          <el-form :model="portForm" label-width="60px" size="small" inline>
            <el-form-item label="主机">
              <el-input v-model="portForm.host" placeholder="IP 或域名" style="width: 200px" />
            </el-form-item>
            <el-form-item label="端口">
              <el-input v-model="portForm.portsText" placeholder="22,80,443,3306" style="width: 260px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleBatchPortCheck" :loading="portLoading" size="small">检测</el-button>
            </el-form-item>
          </el-form>
          <div class="quick-ports">
            <span class="quick-label">常用端口：</span>
            <el-tag
              v-for="qp in quickPorts" :key="qp.port"
              class="quick-tag" effect="plain" size="small"
              @click="addQuickPort(qp.port)"
            >
              {{ qp.label }} ({{ qp.port }})
            </el-tag>
          </div>
          <div v-if="portResults.length > 0" class="port-results" style="margin-top: 12px;">
            <el-table :data="portResults" stripe border size="small" style="max-width: 400px;">
              <el-table-column prop="port" label="端口" width="80" align="center" />
              <el-table-column label="服务" width="100" align="center">
                <template #default="{ row }">{{ getPortService(row.port) }}</template>
              </el-table-column>
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.is_open ? 'success' : 'danger'" size="small">
                    {{ row.is_open ? '开放' : '关闭' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Codemirror } from 'vue-codemirror'
import { StreamLanguage } from '@codemirror/language'
import { shell } from '@codemirror/legacy-modes/mode/shell'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import {
  pingServer, checkServerPort, batchPortCheck,
  sshTestConnection, sshExecute, aiServerCommand,
} from '../../api/efficiency-tools'

// ---- SSH 连接 ----
const sshForm = ref({ host: '', port: 22, username: 'root', password: '' })
const sshTesting = ref(false)
const sshConnected = ref(false)
const sshConnectResult = ref('')

// ---- 命令模式 ----
const cmdMode = ref<'manual' | 'ai'>('manual')
const cmdInput = ref('')
const cmdLoading = ref(false)
const cmdResult = ref<{ stdout: string; stderr: string; exit_code: number } | null>(null)

// ---- AI 模式 ----
const aiPrompt = ref('')
const aiLoading = ref(false)
const generatedCmd = ref('')

// ---- 网络诊断 ----
const diagOpen = ref<string[]>([])
const pingForm = ref({ host: '' })
const pingLoading = ref(false)
const pingResult = ref<{ reachable: boolean; output?: string } | null>(null)
const portForm = ref({ host: '', portsText: '22,80,443,3306,8080' })
const portLoading = ref(false)
const portResults = ref<{ port: number; is_open: boolean }[]>([])

// ---- CodeMirror 扩展 ----
const shellExtensions = [
  StreamLanguage.define(shell),
  oneDark,
  EditorView.lineWrapping,
]

const shellReadonlyExtensions = [
  StreamLanguage.define(shell),
  oneDark,
  EditorView.lineWrapping,
  EditorState.readOnly.of(true),
]

// ---- 常用命令 ----
const quickCommands = [
  { label: '磁盘使用', cmd: 'df -h' },
  { label: '内存使用', cmd: 'free -h' },
  { label: '系统负载', cmd: 'top -bn1 | head -20' },
  { label: '进程列表', cmd: 'ps aux --sort=-%mem | head -20' },
  { label: '网络连接', cmd: 'ss -tulnp' },
  { label: 'syslog', cmd: 'tail -n 50 /var/log/syslog' },
  { label: '系统信息', cmd: 'uname -a && cat /etc/os-release' },
  { label: 'Docker容器', cmd: 'docker ps -a' },
]

const quickPorts = [
  { port: 22, label: 'SSH' }, { port: 80, label: 'HTTP' },
  { port: 443, label: 'HTTPS' }, { port: 3306, label: 'MySQL' },
  { port: 5432, label: 'PG' }, { port: 6379, label: 'Redis' },
  { port: 8080, label: '8080' }, { port: 9090, label: '9090' },
]

const portServiceMap: Record<number, string> = {
  21: 'FTP', 22: 'SSH', 80: 'HTTP', 443: 'HTTPS',
  3306: 'MySQL', 5432: 'PostgreSQL', 6379: 'Redis',
  27017: 'MongoDB', 8080: 'HTTP Alt', 9090: 'Prometheus',
}

function getPortService(port: number) { return portServiceMap[port] || '-' }

function addQuickPort(port: number) {
  const current = portForm.value.portsText.split(',').map(s => s.trim()).filter(Boolean)
  if (!current.includes(String(port))) {
    current.push(String(port))
    portForm.value.portsText = current.join(',')
  }
}

function useGeneratedCmd() {
  cmdInput.value = generatedCmd.value
  cmdMode.value = 'manual'
}

// ---- SSH 测试 ----
async function handleSSHTest() {
  if (!sshForm.value.host || !sshForm.value.username) {
    ElMessage.warning('请填写主机和用户名')
    return
  }
  sshTesting.value = true
  sshConnected.value = false
  sshConnectResult.value = ''
  cmdResult.value = null
  try {
    const res: any = await sshTestConnection({ ...sshForm.value, command: 'uname -a' })
    if (res.code === 0 && res.data?.connected) {
      sshConnected.value = true
      sshConnectResult.value = `连接成功 | ${res.data.system_info}`
    } else {
      sshConnectResult.value = res.msg || '连接失败'
    }
  } catch (e: any) {
    sshConnectResult.value = e.message || '连接失败'
  } finally {
    sshTesting.value = false
  }
}

// ---- 执行命令 ----
async function handleExecuteCmd() {
  if (!cmdInput.value.trim()) {
    ElMessage.warning('请输入命令')
    return
  }
  cmdLoading.value = true
  cmdResult.value = null
  try {
    const res: any = await sshExecute({ ...sshForm.value, command: cmdInput.value })
    if (res.code === 0) {
      cmdResult.value = res.data
    } else {
      ElMessage.error(res.msg || '执行失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '执行失败')
  } finally {
    cmdLoading.value = false
  }
}

// ---- AI 命令 ----
async function handleAICommand() {
  if (!aiPrompt.value.trim()) {
    ElMessage.warning('请输入自然语言描述')
    return
  }
  aiLoading.value = true
  cmdResult.value = null
  generatedCmd.value = ''
  try {
    const res: any = await aiServerCommand({ ...sshForm.value, prompt: aiPrompt.value })
    if (res.code === 0) {
      generatedCmd.value = res.data.generated_command || ''
      if (res.data.executed) {
        cmdResult.value = {
          stdout: res.data.stdout || '',
          stderr: res.data.stderr || '',
          exit_code: res.data.exit_code ?? -1,
        }
      } else if (res.data.error) {
        ElMessage.warning(res.data.error)
      }
    } else {
      ElMessage.error(res.msg || 'AI 命令失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'AI 命令失败')
  } finally {
    aiLoading.value = false
  }
}

// ---- Ping ----
async function handlePing() {
  if (!pingForm.value.host) { ElMessage.warning('请输入主机地址'); return }
  pingLoading.value = true
  pingResult.value = null
  try {
    const res: any = await pingServer({ host: pingForm.value.host })
    if (res.code === 0) pingResult.value = res.data
    else ElMessage.error(res.msg || 'Ping 失败')
  } catch (e: any) { ElMessage.error(e.message || 'Ping 失败') }
  finally { pingLoading.value = false }
}

// ---- 批量端口 ----
async function handleBatchPortCheck() {
  if (!portForm.value.host) { ElMessage.warning('请输入主机地址'); return }
  const ports = portForm.value.portsText.split(',').map(s => parseInt(s.trim())).filter(p => !isNaN(p) && p > 0 && p <= 65535)
  if (!ports.length) { ElMessage.warning('请输入有效端口号'); return }
  portLoading.value = true
  portResults.value = []
  try {
    const res: any = await batchPortCheck({ host: portForm.value.host, ports })
    if (res.code === 0) portResults.value = res.data.results || []
    else ElMessage.error(res.msg || '检测失败')
  } catch (e: any) { ElMessage.error(e.message || '检测失败') }
  finally { portLoading.value = false }
}
</script>

<style scoped>
.server-tool { max-width: 1400px; }

.config-panel {
  background: white; border: 1px solid #e5e7eb;
  border-radius: 10px; padding: 20px;
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;
}
.panel-header h3 { margin: 0; font-size: 15px; font-weight: 600; color: #1e293b; }
.config-form { max-width: 900px; }
.form-row { display: flex; gap: 16px; }
.form-row > .el-form-item { flex: 1; }
.port-field { max-width: 200px; }

.connect-status {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 12px;
}
.connect-status.small { padding: 6px 10px; font-size: 12px; margin-top: 8px; }
.connect-status.success { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.connect-status.error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

.workspace {}

.mode-switcher { display: flex; align-items: center; gap: 12px; }

.cmd-editor, .ai-editor {
  background: white; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
}
.editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e5e7eb;
  font-size: 13px; font-weight: 600; color: #475569;
}
.editor-actions { display: flex; gap: 6px; }

.codemirror-wrapper {}
.codemirror-wrapper :deep(.cm-editor) { font-size: 13px; }
.codemirror-wrapper :deep(.cm-editor .cm-scroller) { font-family: 'Menlo', 'Monaco', 'Courier New', monospace; }
.codemirror-wrapper.readonly :deep(.cm-editor) { cursor: default; }

.quick-commands {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px;
  padding: 10px 14px; border-top: 1px solid #f1f5f9;
}
.quick-label { font-size: 12px; color: #94a3b8; }
.quick-tag { cursor: pointer; transition: all 0.15s; }
.quick-tag:hover { border-color: #6366f1; color: #6366f1; }

.ai-input-area { padding: 0; }
.ai-textarea :deep(.el-textarea__inner) {
  border: none; border-radius: 0; font-size: 13px; line-height: 1.6;
  resize: none; padding: 12px 14px;
}

.generated-cmd { border-top: 1px solid #e5e7eb; }
.generated-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 14px; background: #f0fdf4; border-bottom: 1px solid #e5e7eb;
  font-size: 12px; font-weight: 600; color: #166534;
}

.cmd-output {
  background: white; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
}
.output-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e5e7eb;
  font-size: 13px; font-weight: 600; color: #475569;
}
.terminal-output {
  background: #1e293b; padding: 14px; max-height: 500px; overflow: auto;
}
.terminal-output pre {
  margin: 0; color: #a5f3fc; font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all;
}
.terminal-output pre.stderr { color: #fca5a5; }
.terminal-output pre.empty { color: #64748b; font-style: italic; }

.quick-ports {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: 8px;
}
.diag-section h4 { margin: 0 0 10px 0; font-size: 14px; color: #334155; }
.ping-output {
  margin-top: 8px; background: #1e293b; border-radius: 8px; padding: 12px; overflow-x: auto;
}
.ping-output pre {
  margin: 0; color: #a5f3fc; font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all;
}
</style>
