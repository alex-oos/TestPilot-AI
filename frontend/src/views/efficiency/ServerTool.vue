<template>
  <div class="server-tool">
    <!-- Ping 测试 -->
    <div class="config-panel">
      <div class="panel-header">
        <h3>🏓 Ping 连通性测试</h3>
      </div>
      <el-form :model="serverForm" label-width="80px" size="default" class="config-form">
        <div class="form-row">
          <el-form-item label="主机">
            <el-input v-model="serverForm.host" placeholder="输入 IP 或域名" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handlePing" :loading="pingLoading">
              Ping
            </el-button>
          </el-form-item>
        </div>
      </el-form>

      <div v-if="pingResult" class="connect-status" :class="pingResult.reachable ? 'success' : 'error'">
        <span class="status-icon">{{ pingResult.reachable ? '✅' : '❌' }}</span>
        <span>{{ pingResult.reachable ? '网络可达' : '网络不可达' }}</span>
      </div>
      <div v-if="pingResult?.output" class="ping-output">
        <pre>{{ pingResult.output }}</pre>
      </div>
    </div>

    <!-- 批量端口检测 -->
    <div class="config-panel" style="margin-top: 16px">
      <div class="panel-header">
        <h3>🔍 批量端口检测</h3>
      </div>
      <el-form :model="portForm" label-width="80px" size="default" class="config-form">
        <div class="form-row">
          <el-form-item label="主机">
            <el-input v-model="portForm.host" placeholder="输入 IP 或域名" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input v-model="portForm.portsText" placeholder="用逗号分隔，如 22,80,443,3306,8080" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleBatchPortCheck" :loading="portLoading">
              检测
            </el-button>
          </el-form-item>
        </div>
      </el-form>

      <!-- 常用端口快捷按钮 -->
      <div class="quick-ports">
        <span class="quick-label">常用端口：</span>
        <el-tag
          v-for="qp in quickPorts"
          :key="qp.port"
          class="quick-tag"
          effect="plain"
          @click="addQuickPort(qp.port)"
        >
          {{ qp.label }} ({{ qp.port }})
        </el-tag>
      </div>

      <!-- 端口检测结果 -->
      <div v-if="portResults.length > 0" class="port-results">
        <el-table :data="portResults" stripe border size="small">
          <el-table-column prop="port" label="端口" width="100" align="center" />
          <el-table-column label="服务" width="120" align="center">
            <template #default="{ row }">
              {{ getPortService(row.port) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_open ? 'success' : 'danger'" size="small">
                {{ row.is_open ? '开放' : '关闭' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 单端口检测 -->
    <div class="config-panel" style="margin-top: 16px">
      <div class="panel-header">
        <h3>🎯 单端口检测</h3>
      </div>
      <el-form :model="singlePortForm" label-width="80px" size="default" class="config-form">
        <div class="form-row">
          <el-form-item label="主机">
            <el-input v-model="singlePortForm.host" placeholder="输入 IP 或域名" />
          </el-form-item>
          <el-form-item label="端口" class="port-field">
            <el-input-number v-model="singlePortForm.port" :min="1" :max="65535" controls-position="right" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSinglePortCheck" :loading="singlePortLoading">
              检测
            </el-button>
          </el-form-item>
        </div>
      </el-form>

      <div v-if="singlePortResult !== null" class="connect-status" :class="singlePortResult ? 'success' : 'error'">
        <span class="status-icon">{{ singlePortResult ? '✅' : '❌' }}</span>
        <span>{{ singlePortForm.host }}:{{ singlePortForm.port }} {{ singlePortResult ? '端口开放' : '端口关闭或不可达' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  pingServer,
  checkServerPort,
  batchPortCheck,
} from '../../api/efficiency-tools'

// ---- Ping ----
const serverForm = ref({ host: '' })
const pingLoading = ref(false)
const pingResult = ref<{ reachable: boolean; output?: string } | null>(null)

// ---- 批量端口 ----
const portForm = ref({ host: '', portsText: '22,80,443,3306,8080' })
const portLoading = ref(false)
const portResults = ref<{ port: number; is_open: boolean }[]>([])

// ---- 单端口 ----
const singlePortForm = ref({ host: '', port: 22 })
const singlePortLoading = ref(false)
const singlePortResult = ref<boolean | null>(null)

const quickPorts = [
  { port: 22, label: 'SSH' },
  { port: 80, label: 'HTTP' },
  { port: 443, label: 'HTTPS' },
  { port: 3306, label: 'MySQL' },
  { port: 5432, label: 'PostgreSQL' },
  { port: 6379, label: 'Redis' },
  { port: 27017, label: 'MongoDB' },
  { port: 8080, label: 'HTTP Alt' },
  { port: 9090, label: 'Prometheus' },
  { port: 3000, label: 'Dev Server' },
]

const portServiceMap: Record<number, string> = {
  21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP',
  53: 'DNS', 80: 'HTTP', 110: 'POP3', 143: 'IMAP',
  443: 'HTTPS', 993: 'IMAPS', 995: 'POP3S',
  3306: 'MySQL', 5432: 'PostgreSQL', 6379: 'Redis',
  27017: 'MongoDB', 8080: 'HTTP Alt', 8443: 'HTTPS Alt',
  9090: 'Prometheus', 3000: 'Dev', 5000: 'Dev',
}

function getPortService(port: number) {
  return portServiceMap[port] || '-'
}

function addQuickPort(port: number) {
  const current = portForm.value.portsText
    .split(',')
    .map(s => s.trim())
    .filter(Boolean)
  if (!current.includes(String(port))) {
    current.push(String(port))
    portForm.value.portsText = current.join(',')
  }
}

async function handlePing() {
  if (!serverForm.value.host) {
    ElMessage.warning('请输入主机地址')
    return
  }
  pingLoading.value = true
  pingResult.value = null
  try {
    const res: any = await pingServer({ host: serverForm.value.host })
    if (res.code === 0) {
      pingResult.value = res.data
    } else {
      ElMessage.error(res.msg || 'Ping 失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || 'Ping 失败')
  } finally {
    pingLoading.value = false
  }
}

async function handleBatchPortCheck() {
  if (!portForm.value.host) {
    ElMessage.warning('请输入主机地址')
    return
  }
  const ports = portForm.value.portsText
    .split(',')
    .map(s => parseInt(s.trim()))
    .filter(p => !isNaN(p) && p > 0 && p <= 65535)
  if (ports.length === 0) {
    ElMessage.warning('请输入有效的端口号')
    return
  }
  portLoading.value = true
  portResults.value = []
  try {
    const res: any = await batchPortCheck({ host: portForm.value.host, ports })
    if (res.code === 0) {
      portResults.value = res.data.results || []
    } else {
      ElMessage.error(res.msg || '检测失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '检测失败')
  } finally {
    portLoading.value = false
  }
}

async function handleSinglePortCheck() {
  if (!singlePortForm.value.host) {
    ElMessage.warning('请输入主机地址')
    return
  }
  singlePortLoading.value = true
  singlePortResult.value = null
  try {
    const res: any = await checkServerPort({
      host: singlePortForm.value.host,
      port: singlePortForm.value.port,
    })
    if (res.code === 0) {
      singlePortResult.value = res.data.is_open
    } else {
      ElMessage.error(res.msg || '检测失败')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '检测失败')
  } finally {
    singlePortLoading.value = false
  }
}
</script>

<style scoped>
.server-tool {
  max-width: 1400px;
}

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
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.config-form {
  max-width: 900px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row > .el-form-item {
  flex: 1;
}

.port-field {
  max-width: 200px;
}

.connect-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-top: 12px;
}

.connect-status.success {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.connect-status.error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.ping-output {
  margin-top: 12px;
  background: #1e293b;
  border-radius: 8px;
  padding: 14px;
  overflow-x: auto;
}

.ping-output pre {
  margin: 0;
  color: #a5f3fc;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.quick-ports {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.quick-label {
  font-size: 12px;
  color: #94a3b8;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.15s;
}

.quick-tag:hover {
  border-color: #6366f1;
  color: #6366f1;
}

.port-results {
  margin-top: 16px;
}
</style>
