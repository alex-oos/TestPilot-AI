<template>
  <div class="skills-center">
    <div class="page-header">
      <div>
        <h2>QA Skills 中心</h2>
        <p class="subtitle">基于 awesome-qa-skills 的方法论 + 项目级 Output Contract + 业务自定义</p>
      </div>
      <div class="header-actions">
        <el-button @click="loadList(true)" :loading="loading">刷新</el-button>
        <el-button type="primary" @click="onReload">重新加载缓存</el-button>
      </div>
    </div>

    <el-alert v-if="!summary?.enabled" type="warning" show-icon
      title="QA Skills 已禁用（USE_QA_SKILLS=false）" :closable="false" style="margin-bottom: 12px" />

    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">已加载 Skill</div>
          <div class="stat-value">{{ summary?.skills?.length ?? 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">Few-shot</div>
          <div class="stat-value">{{ summary?.fewshot_enabled ? '开' : '关' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">智能路由</div>
          <div class="stat-value">{{ summary?.discover_enabled ? '开' : '关' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">Token 预算</div>
          <div class="stat-value">{{ summary?.prompt_token_budget ?? 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab" style="margin-top: 16px">
      <el-tab-pane label="角色映射" name="mapping">
        <el-table :data="roleRows" size="small" border>
          <el-table-column prop="role" label="角色" width="140" />
          <el-table-column prop="default_skill_id" label="默认 Skill" />
          <el-table-column prop="env_override" label=".env 覆盖">
            <template #default="{ row }">
              <span v-if="row.env_override">{{ row.env_override }}</span>
              <span v-else style="color: #aaa">—</span>
            </template>
          </el-table-column>
          <el-table-column label="生效">
            <template #default="{ row }">
              <el-tag size="small" type="success">{{ row.effective_skill_id }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Skill 列表" name="skills">
        <div style="margin-bottom: 8px">
          <el-radio-group v-model="langFilter" size="small" @change="loadList(false)">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="zh">中文</el-radio-button>
            <el-radio-button label="en">English</el-radio-button>
          </el-radio-group>
        </div>
        <el-table :data="summary?.skills || []" size="small" border @row-click="onRowClick">
          <el-table-column prop="skill_id" label="Skill ID" width="240" />
          <el-table-column prop="name" label="名称" width="200" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="lang" label="lang" width="60" />
          <el-table-column label="资源" width="240">
            <template #default="{ row }">
              <el-tag size="small" type="info">prompts {{ row.prompt_files?.length || 0 }}</el-tag>
              <el-tag size="small" type="warning" style="margin-left: 4px">tpl {{ row.templates?.length || 0 }}</el-tag>
              <el-tag size="small" type="success" style="margin-left: 4px">ex {{ row.examples?.length || 0 }}</el-tag>
              <el-tag v-if="row.overlays_applied?.length" size="small" style="margin-left: 4px">overlay {{ row.overlays_applied.length }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column label="hash" width="100">
            <template #default="{ row }">
              <code style="font-size: 11px">{{ row.content_hash || '-' }}</code>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="智能路由 / 调试" name="discover">
        <el-input v-model="discoverInput" type="textarea" :rows="6"
          placeholder="贴入需求文档或片段以预览路由结果" />
        <div style="margin-top: 8px">
          <el-button type="primary" @click="onDiscover" :loading="discoverLoading">预览路由</el-button>
          <span v-if="!summary?.discover_enabled" style="margin-left: 12px; color: #e6a23c">
            （提示：当前未启用 QA_SKILL_DISCOVER_ENABLED，预览仅本地路由测试）
          </span>
        </div>
        <el-card v-if="discoverResult" style="margin-top: 12px" shadow="never">
          <pre style="margin: 0">{{ JSON.stringify(discoverResult, null, 2) }}</pre>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="健康检查" name="health">
        <div style="margin-bottom: 8px">
          <el-button size="small" @click="loadHealth" :loading="healthLoading">刷新健康检查</el-button>
          <el-tag v-if="health" :type="health.ok ? 'success' : 'danger'" style="margin-left: 8px">
            {{ health.ok ? 'OK' : '失败' }} | total={{ health.total }} failed={{ health.failed }} warning_only={{ health.warning_only }}
          </el-tag>
        </div>
        <el-alert v-if="health && health.role_mapping_issues?.length" type="error" show-icon
          :title="`角色映射问题：${health.role_mapping_issues.length} 处`" :closable="false" style="margin-bottom: 8px">
          <ul>
            <li v-for="(it, i) in health.role_mapping_issues" :key="i">{{ it }}</li>
          </ul>
        </el-alert>
        <el-table v-if="health" :data="health.checks" size="small" border>
          <el-table-column prop="skill_id" label="Skill ID" width="240" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.ok ? 'success' : 'danger'">{{ row.ok ? 'OK' : 'FAIL' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="version" label="ver" width="80" />
          <el-table-column prop="lang" label="lang" width="60" />
          <el-table-column prop="prompts" label="prompts" width="80" />
          <el-table-column prop="primary_chars" label="primary 字数" width="120" />
          <el-table-column label="问题">
            <template #default="{ row }">
              <div v-for="(it, i) in row.issues" :key="i" style="color:#f56c6c">✗ {{ it }}</div>
              <div v-for="(it, i) in row.warnings" :key="'w'+i" style="color:#e6a23c">⚠ {{ it }}</div>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Token 统计" name="stats">
        <el-button size="small" @click="loadStats" :loading="statsLoading">刷新统计</el-button>
        <div style="margin-top: 12px" v-if="stats">
          <h4>按角色（Role）</h4>
          <el-table :data="stats.by_role" size="small" border>
            <el-table-column prop="role" label="角色" />
            <el-table-column prop="calls" label="调用次数" />
            <el-table-column prop="prompt_actual_sum" label="prompt tokens (实际累计)" />
            <el-table-column prop="completion_actual_sum" label="completion tokens (实际累计)" />
            <el-table-column prop="prompt_est_avg" label="prompt 估算均值" />
            <el-table-column prop="over_budget_count" label="超预算次数" />
            <el-table-column prop="fewshot_used" label="few-shot 命中次数" />
          </el-table>
          <h4 style="margin-top: 16px">按 Skill</h4>
          <el-table :data="stats.by_skill" size="small" border>
            <el-table-column prop="skill_id" label="Skill" />
            <el-table-column prop="calls" label="调用次数" />
            <el-table-column prop="prompt_actual_sum" label="prompt tokens (实际累计)" />
            <el-table-column prop="completion_actual_sum" label="completion tokens (实际累计)" />
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="审计记录" name="audit">
        <div style="margin-bottom: 8px; display: flex; gap: 8px; align-items: center">
          <el-input v-model="auditTaskId" size="small" placeholder="按 task_id 过滤" clearable style="width: 320px" />
          <el-select v-model="auditRole" size="small" placeholder="按角色过滤" clearable style="width: 180px">
            <el-option v-for="r in ['analysis','generation','review','supplement','discover']"
              :key="r" :value="r" :label="r" />
          </el-select>
          <el-button size="small" @click="loadAudit">查询</el-button>
          <el-button size="small" type="danger" plain @click="onClearAudit">清空</el-button>
        </div>
        <el-table :data="auditItems" size="small" border>
          <el-table-column label="时间" width="160">
            <template #default="{ row }">{{ formatTs(row.ts) }}</template>
          </el-table-column>
          <el-table-column prop="role" label="角色" width="100" />
          <el-table-column prop="skill_id" label="Skill" width="220" />
          <el-table-column prop="skill_version" label="ver" width="60" />
          <el-table-column prop="skill_lang" label="lang" width="60" />
          <el-table-column prop="task_id" label="任务 ID" show-overflow-tooltip />
          <el-table-column label="few-shot" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.used_fewshot" size="small" type="success">是</el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column label="tokens≈" width="100">
            <template #default="{ row }">
              <span :style="row.over_budget ? 'color:#f56c6c;font-weight:600' : ''">
                {{ row.prompt_tokens_est }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="hash" width="100">
            <template #default="{ row }">
              <code style="font-size: 11px">{{ row.content_hash || '-' }}</code>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="detailVisible" :title="selected?.skill_id" width="80%" top="6vh">
      <div v-if="selected">
        <p><b>Name</b>: {{ selected.name }} &nbsp; | &nbsp; <b>v</b>{{ selected.version }} &nbsp; | &nbsp; <b>lang</b>={{ selected.lang }} &nbsp; | &nbsp; <b>hash</b>=<code>{{ selected.content_hash }}</code></p>
        <p style="color:#666">{{ selected.description }}</p>
        <el-tabs v-model="detailTab">
          <el-tab-pane label="SKILL.md" name="md">
            <pre class="src">{{ selected.skill_md_body }}</pre>
          </el-tab-pane>
          <el-tab-pane :label="`prompts (${Object.keys(selected.prompts || {}).length})`" name="prompts">
            <el-collapse>
              <el-collapse-item v-for="(content, name) in selected.prompts" :key="name" :title="name">
                <pre class="src">{{ content }}</pre>
              </el-collapse-item>
            </el-collapse>
          </el-tab-pane>
          <el-tab-pane :label="`templates (${Object.keys(selected.output_templates || {}).length})`" name="tpl">
            <el-collapse>
              <el-collapse-item v-for="(content, name) in selected.output_templates" :key="name" :title="name">
                <pre class="src">{{ content }}</pre>
              </el-collapse-item>
            </el-collapse>
          </el-tab-pane>
          <el-tab-pane :label="`examples (${(selected.examples_full || []).length})`" name="ex">
            <el-collapse>
              <el-collapse-item v-for="ex in selected.examples_full || []" :key="ex.filename" :title="`[${ex.kind}] ${ex.filename}`">
                <pre class="src">{{ ex.is_binary ? '(binary)' : ex.content }}</pre>
              </el-collapse-item>
            </el-collapse>
          </el-tab-pane>
          <el-tab-pane label="README" name="readme">
            <pre class="src">{{ selected.readme }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listSkills, getSkill, reloadSkills, listAuditRecent, clearAudit, discoverFor, getSkillsHealth, getAuditStats } from '../api/skills'

const loading = ref(false)
const summary = ref<any>(null)
const langFilter = ref('')
const activeTab = ref('mapping')
const detailVisible = ref(false)
const detailTab = ref('md')
const selected = ref<any>(null)

const auditItems = ref<any[]>([])
const auditTaskId = ref('')
const auditRole = ref('')

const discoverInput = ref('')
const discoverResult = ref<any>(null)
const discoverLoading = ref(false)

const health = ref<any>(null)
const healthLoading = ref(false)
const stats = ref<any>(null)
const statsLoading = ref(false)

async function loadHealth() {
  healthLoading.value = true
  try {
    const res: any = await getSkillsHealth()
    health.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.message || '健康检查失败')
  } finally {
    healthLoading.value = false
  }
}

async function loadStats() {
  statsLoading.value = true
  try {
    const res: any = await getAuditStats()
    stats.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.message || '加载统计失败')
  } finally {
    statsLoading.value = false
  }
}

const roleRows = computed(() => {
  if (!summary.value?.role_mapping) return []
  return Object.entries(summary.value.role_mapping).map(([role, v]: any) => ({ role, ...v }))
})

async function loadList(showOk: boolean) {
  loading.value = true
  try {
    const res: any = await listSkills(langFilter.value || undefined)
    summary.value = res.data
    if (showOk) ElMessage.success(`已加载 ${summary.value.skills.length} 个 skill`)
  } catch (e: any) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onRowClick(row: any) {
  if (row.error) return
  try {
    const res: any = await getSkill(row.skill_id)
    selected.value = res.data
    detailTab.value = 'md'
    detailVisible.value = true
  } catch (e: any) {
    ElMessage.error(e?.message || '查看 skill 失败')
  }
}

async function onReload() {
  try {
    await reloadSkills()
    ElMessage.success('Skill 缓存已重载')
    await loadList(false)
  } catch (e: any) {
    ElMessage.error(e?.message || '重载失败')
  }
}

async function loadAudit() {
  try {
    const res: any = await listAuditRecent({
      limit: 100,
      role: auditRole.value || undefined,
      task_id: auditTaskId.value || undefined,
    })
    auditItems.value = res.data?.items || []
  } catch (e: any) {
    ElMessage.error(e?.message || '加载审计失败')
  }
}

async function onClearAudit() {
  await ElMessageBox.confirm('清空当前进程内的审计记录？', '确认', { type: 'warning' })
  await clearAudit()
  ElMessage.success('已清空')
  loadAudit()
}

async function onDiscover() {
  if (!discoverInput.value.trim()) {
    ElMessage.warning('请贴入待路由的文本')
    return
  }
  discoverLoading.value = true
  try {
    const res: any = await discoverFor(discoverInput.value)
    discoverResult.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.message || '路由失败')
  } finally {
    discoverLoading.value = false
  }
}

function formatTs(ts: number): string {
  if (!ts) return '-'
  const d = new Date(ts * 1000)
  return d.toLocaleString()
}

onMounted(() => {
  loadList(false)
  loadAudit()
})
</script>

<style scoped>
.skills-center { padding: 16px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.subtitle { color: #999; margin-top: 4px; }
.stat-label { color: #888; font-size: 13px; }
.stat-value { font-size: 24px; font-weight: 600; margin-top: 6px; }
pre.src { background: #fafafa; padding: 12px; border-radius: 4px; max-height: 540px; overflow: auto; font-size: 12px; line-height: 1.55; white-space: pre-wrap; }
.header-actions { display: flex; gap: 8px; }
</style>
