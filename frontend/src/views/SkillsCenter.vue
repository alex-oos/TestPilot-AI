<template>
  <div class="skills-center">
    <div class="page-header">
      <div>
        <h2>QA Skills 中心</h2>
        <p class="subtitle">基于 awesome-qa-skills 的方法论 + 项目级 Output Contract + 业务自定义</p>
      </div>
      <div class="header-actions">
        <el-button type="success" @click="importVisible = true">导入 Skill</el-button>
        <el-button @click="loadList(true)" :loading="loading">刷新</el-button>
        <el-button type="primary" @click="onReload">重新加载缓存</el-button>
      </div>
    </div>

    <el-alert v-if="summary && !summary.enabled" type="warning" show-icon
      title="QA Skills 已禁用（配置中心总开关或 USE_QA_SKILLS=false）" :closable="false" style="margin-bottom: 12px" />

    <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px">
      <span style="font-size: 13px; color: #606266">全局 Skill 总开关</span>
      <el-switch
        v-model="qaSkillsEnabled"
        :loading="globalToggleLoading"
        active-text="启用"
        inactive-text="关闭"
        @change="onGlobalSkillToggle"
      />
      <span v-if="summary" style="font-size: 12px; color: #909399">
        环境变量：{{ summary.env_enabled ? '开' : '关' }}
      </span>
    </div>

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
      <el-tab-pane label="角色配置" name="role-config">
        <div style="margin-bottom: 12px; display: flex; gap: 8px; align-items: center">
          <el-button type="primary" size="small" @click="onSaveRoleConfig" :loading="roleConfigSaving">保存配置</el-button>
          <el-button type="success" size="small" @click="openBindRoleDialog">新增绑定</el-button>
          <el-button size="small" @click="loadRoleConfig" :loading="roleConfigLoading">刷新</el-button>
        </div>
        <el-table :data="roleConfigDraft" size="small" border v-loading="roleConfigLoading">
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">{{ roleLabel(row.role) }}</template>
          </el-table-column>
          <el-table-column label="绑定 Skill" min-width="280">
            <template #default="{ row }">
              <el-select v-model="row.skill_id" filterable placeholder="选择 Skill" style="width: 100%">
                <el-option
                  v-for="opt in skillOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="启用 Skill" width="110" align="center">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" />
            </template>
          </el-table-column>
          <el-table-column label="生效 Skill" width="220">
            <template #default="{ row }">
              <el-tag size="small" :type="row.skill_exists === false ? 'danger' : 'success'">
                {{ row.effective_skill_id || '（legacy prompt）' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="120" />
          <el-table-column prop="env_override" label=".env 覆盖" width="180">
            <template #default="{ row }">
              <span v-if="row.env_override">{{ row.env_override }}</span>
              <span v-else style="color: #aaa">—</span>
            </template>
          </el-table-column>
        </el-table>
        <p style="margin-top: 8px; font-size: 12px; color: #909399">
          优先级：配置中心绑定 &gt; skills 短映射 &gt; .env 覆盖 &gt; 目录默认。关闭「启用 Skill」或全局总开关时，对应阶段走 legacy prompt。
        </p>
      </el-tab-pane>

      <el-tab-pane label="Skill 列表" name="skills">
        <div style="margin-bottom: 8px">
          <el-radio-group v-model="langFilter" size="small" @change="loadList(false)">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="zh">中文</el-radio-button>
            <el-radio-button value="en">English</el-radio-button>
          </el-radio-group>
        </div>
        <el-table :data="summary?.skills || []" size="small" border @row-click="onRowClick">
          <el-table-column prop="skill_id" label="Skill ID" width="220" />
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column label="标记" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.protected" size="small" type="info">内置</el-tag>
              <el-tag
                v-if="row.referenced_by_roles?.length"
                size="small"
                type="warning"
                style="margin-left: 4px"
              >
                引用×{{ row.referenced_by_roles.length }}
              </el-tag>
            </template>
          </el-table-column>
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
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :disabled="!!row.error" @click.stop="onExportSkill(row)">
                导出
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                :disabled="!!row.error || row.protected || !row.deletable"
                @click.stop="onDeleteSkill(row)"
              >
                删除
              </el-button>
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

      <el-tab-pane label="LLM 治理" name="llm">
        <div style="margin-bottom: 12px">
          <el-button size="small" @click="loadLlm" :loading="llmLoading">刷新</el-button>
          <el-button size="small" @click="onPurgeLlmCache">清理过期缓存</el-button>
          <el-button size="small" type="danger" plain @click="onClearLlmCache">清空全部缓存</el-button>
          <el-button size="small" type="warning" plain @click="onPurgeAudit">清理 30 天前审计</el-button>
          <el-input-number v-model="costDays" :min="1" :max="90" size="small" style="margin-left: 12px; width: 120px" />
          <span style="margin-left: 6px; color:#888; font-size:12px">天</span>
        </div>

        <el-row :gutter="12" v-if="llm">
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat-label">缓存命中率</div>
              <div class="stat-value">{{ formatPct(llm.cache?.hit_rate) }}</div>
              <div style="color:#888;font-size:12px;margin-top:4px">
                hit {{ llm.cache?.hits ?? 0 }} / miss {{ llm.cache?.misses ?? 0 }} / put {{ llm.cache?.puts ?? 0 }}
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat-label">缓存条目（内存 / SQLite）</div>
              <div class="stat-value">{{ llm.cache?.mem_size ?? 0 }} / {{ llm.cache?.sqlite_size ?? 0 }}</div>
              <div style="color:#888;font-size:12px;margin-top:4px">
                TTL {{ llm.cache?.ttl_hours ?? '-' }}h · 容量 {{ llm.cache?.mem_max ?? '-' }}
                <span v-if="llm.cache && !llm.cache.enabled" style="color:#e6a23c">（已禁用）</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat-label">并发使用</div>
              <div class="stat-value">{{ llm.concurrency?.current ?? 0 }} / {{ llm.concurrency?.max ?? 0 }}</div>
              <div style="color:#888;font-size:12px;margin-top:4px">
                峰值 {{ llm.concurrency?.peak ?? 0 }} · 累计 {{ llm.concurrency?.total_holds ?? 0 }} 次
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <div class="stat-label">{{ costDays }} 天总成本（USD）</div>
              <div class="stat-value" style="color:#f56c6c">${{ formatCost(llm.cost?.total?.cost_usd) }}</div>
              <div style="color:#888;font-size:12px;margin-top:4px">
                {{ llm.cost?.total?.calls ?? 0 }} 次调用 ·
                缓存命中 {{ llm.cost?.total?.cache_hits ?? 0 }} ·
                重试 {{ llm.cost?.total?.retries ?? 0 }}
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="12" v-if="llm" style="margin-top:12px">
          <el-col :span="12">
            <el-card shadow="never">
              <h4 style="margin:0 0 8px 0">按模型聚合</h4>
              <el-table :data="llm.cost?.by_model || []" size="small" border empty-text="暂无数据">
                <el-table-column prop="model" label="模型" />
                <el-table-column prop="calls" label="调用" width="70" />
                <el-table-column label="prompt" width="100">
                  <template #default="{ row }">{{ formatNum(row.prompt_tokens) }}</template>
                </el-table-column>
                <el-table-column label="completion" width="110">
                  <template #default="{ row }">{{ formatNum(row.completion_tokens) }}</template>
                </el-table-column>
                <el-table-column label="USD" width="100">
                  <template #default="{ row }">${{ formatCost(row.cost_usd) }}</template>
                </el-table-column>
                <el-table-column prop="cache_hits" label="cache" width="70" />
                <el-table-column prop="retries" label="retry" width="70" />
              </el-table>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <h4 style="margin:0 0 8px 0">按角色聚合</h4>
              <el-table :data="llm.cost?.by_role || []" size="small" border empty-text="暂无数据">
                <el-table-column prop="role" label="角色" width="120" />
                <el-table-column prop="calls" label="调用" width="80" />
                <el-table-column label="prompt" width="100">
                  <template #default="{ row }">{{ formatNum(row.prompt_tokens) }}</template>
                </el-table-column>
                <el-table-column label="completion" width="120">
                  <template #default="{ row }">{{ formatNum(row.completion_tokens) }}</template>
                </el-table-column>
                <el-table-column label="USD">
                  <template #default="{ row }">${{ formatCost(row.cost_usd) }}</template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
        </el-row>

        <el-card v-if="llm?.pricing" shadow="never" style="margin-top:12px">
          <h4 style="margin:0 0 8px 0">
            单价表（{{ llm.pricing?.unit || 'per_1M_tokens' }}, {{ llm.pricing?.currency || 'USD' }}）
          </h4>
          <el-table :data="pricingRows" size="small" border>
            <el-table-column prop="model" label="模型" />
            <el-table-column label="prompt" width="120">
              <template #default="{ row }">${{ row.prompt }}</template>
            </el-table-column>
            <el-table-column label="completion" width="140">
              <template #default="{ row }">${{ row.completion }}</template>
            </el-table-column>
            <el-table-column prop="source" label="来源" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="row.source === 'override' ? 'warning' : 'info'">{{ row.source }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
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

    <el-dialog v-model="importVisible" title="Skill 管理 — 导入" width="720px" @closed="resetImportForm">
      <el-tabs v-model="importMode">
        <el-tab-pane label="方式一：GitHub 一键导入" name="github">
          <el-alert type="info" show-icon :closable="false" style="margin-bottom: 12px"
            title="支持 GitHub tree/blob 链接、仓库简写路径，或仅输入 skill_id（默认从 awesome-qa-skills 自动探测）" />

          <el-form label-width="96px">
            <el-form-item label="来源">
              <el-input
                v-model="importSource"
                type="textarea"
                :rows="3"
                placeholder="例如：https://github.com/naodeng/awesome-qa-skills/tree/main/skills/zh/testing-types/api-test-pytest&#10;或：requirements-analysis-plus"
              />
            </el-form-item>
            <el-form-item label="分支">
              <el-input v-model="importBranch" placeholder="留空则使用链接中的分支或 main" clearable />
            </el-form-item>
            <el-form-item label="本地 ID">
              <el-input v-model="importSkillId" placeholder="可选，覆盖导入后的 skill 目录名" clearable />
            </el-form-item>
            <el-form-item label="覆盖">
              <el-switch v-model="importOverwrite" active-text="覆盖已存在的同名 Skill" />
            </el-form-item>
          </el-form>

          <div style="margin-bottom: 12px; display: flex; gap: 8px;">
            <el-button @click="onPreviewImport" :loading="importPreviewLoading">预览</el-button>
            <el-button type="primary" @click="onImportSkill" :loading="importLoading">一键导入</el-button>
          </div>

          <el-card v-if="importPreview" shadow="never">
            <div style="margin-bottom: 8px">
              <el-tag type="success">{{ importPreview.ref?.skill_id }}</el-tag>
              <el-tag style="margin-left: 8px" v-if="importPreview.exists_locally" type="warning">本地已存在</el-tag>
            </div>
            <div style="color:#666; font-size: 13px; line-height: 1.7">
              <div>仓库：{{ importPreview.ref?.owner }}/{{ importPreview.ref?.repo }} @ {{ importPreview.ref?.branch }}</div>
              <div>路径：{{ importPreview.ref?.skill_path }}</div>
              <div>文件数：{{ importPreview.remote_file_count }}，体积：{{ formatBytes(importPreview.remote_total_bytes) }}</div>
              <div v-if="importPreview.ref?.github_tree_url">
                <a :href="importPreview.ref.github_tree_url" target="_blank" rel="noopener">在 GitHub 查看</a>
              </div>
            </div>
            <pre v-if="importPreview.sample_files?.length" class="src" style="margin-top: 8px; max-height: 160px">{{ importPreview.sample_files.join('\n') }}</pre>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="方式二：ZIP 手动导入" name="zip">
          <el-alert type="info" show-icon :closable="false" style="margin-bottom: 12px"
            title="上传 Skill 目录 ZIP 包，系统自动解析 SKILL.md 位置与 skill_id（支持单层目录包裹或根目录直出）" />

          <el-form label-width="96px">
            <el-form-item label="ZIP 包">
              <el-upload
                drag
                :auto-upload="false"
                :limit="1"
                accept=".zip,application/zip"
                :on-change="onZipFileChange"
                :on-remove="onZipFileRemove"
                :file-list="zipFileList"
              >
                <div style="padding: 12px 0">
                  <div>拖拽 ZIP 到此处，或点击选择文件</div>
                  <div style="color:#999;font-size:12px;margin-top:6px">建议压缩单个 Skill 目录，需包含 SKILL.md</div>
                </div>
              </el-upload>
            </el-form-item>
            <el-form-item label="本地 ID">
              <el-input v-model="zipSkillId" placeholder="可选，不填则自动从目录名或 ZIP 文件名推断" clearable />
            </el-form-item>
            <el-form-item label="覆盖">
              <el-switch v-model="zipOverwrite" active-text="覆盖已存在的同名 Skill" />
            </el-form-item>
          </el-form>

          <div style="margin-bottom: 12px; display: flex; gap: 8px;">
            <el-button @click="onPreviewZipImport" :loading="zipPreviewLoading" :disabled="!zipFile">解析预览</el-button>
            <el-button type="primary" @click="onImportZipSkill" :loading="zipImportLoading" :disabled="!zipFile">导入 ZIP</el-button>
          </div>

          <el-card v-if="zipPreview" shadow="never">
            <div style="margin-bottom: 8px">
              <el-tag type="success">{{ zipPreview.analysis?.skill_id }}</el-tag>
              <el-tag style="margin-left: 8px" v-if="zipPreview.exists_locally" type="warning">本地已存在</el-tag>
              <el-tag style="margin-left: 8px" type="info">{{ zipPreview.analysis?.detected_from }}</el-tag>
            </div>
            <div style="color:#666; font-size: 13px; line-height: 1.7">
              <div>Skill 根路径：{{ zipPreview.analysis?.skill_root }}</div>
              <div v-if="zipPreview.analysis?.skill_md_preview?.name">名称：{{ zipPreview.analysis.skill_md_preview.name }}</div>
              <div v-if="zipPreview.analysis?.skill_md_preview?.description">描述：{{ zipPreview.analysis.skill_md_preview.description }}</div>
              <div>文件数：{{ zipPreview.analysis?.file_count }}，体积：{{ formatBytes(zipPreview.analysis?.total_bytes) }}</div>
            </div>
            <pre v-if="zipPreview.analysis?.sample_files?.length" class="src" style="margin-top: 8px; max-height: 160px">{{ zipPreview.analysis.sample_files.join('\n') }}</pre>
          </el-card>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

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

    <el-dialog v-model="bindRoleDialogVisible" title="新增角色 Skill 绑定" width="480px" destroy-on-close>
      <el-form label-width="100px">
        <el-form-item label="角色" required>
          <el-select v-model="bindRoleForm.role" placeholder="选择 pipeline 角色" style="width: 100%">
            <el-option
              v-for="r in availableRolesForAdd"
              :key="r"
              :label="roleLabel(r)"
              :value="r"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定 Skill" required>
          <el-select v-model="bindRoleForm.skill_id" filterable placeholder="选择 Skill" style="width: 100%">
            <el-option
              v-for="opt in skillOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="启用 Skill">
          <el-switch v-model="bindRoleForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindRoleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onConfirmBindRole">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listSkills, getSkill, reloadSkills, listAuditRecent, clearAudit, discoverFor, getSkillsHealth, getAuditStats,
  getLlmCacheStats, purgeLlmCache, clearLlmCache, getLlmConcurrencyStats, getLlmPricing, getLlmCostRecent, purgeAudit,
  previewGithubSkillImport, importGithubSkill, previewZipSkillImport, importZipSkill,
  exportSkill, deleteSkill } from '../api/skills'
import { getSkillRoleBinding, updateSkillRoleBinding } from '../api/skillRoleConfig'
import { unwrapApiData } from '../utils/request'

const ROLE_LABELS: Record<string, string> = {
  analysis: '需求分析',
  generation: '用例编写',
  review: '用例评审',
}

const PIPELINE_ROLES = ['analysis', 'generation', 'review'] as const

const DEFAULT_SKILL_BY_ROLE: Record<string, string> = {
  analysis: 'requirements-analysis-plus',
  generation: 'testcase-writer-plus',
  review: 'test-case-reviewer-plus',
}

const loading = ref(false)
const summary = ref<any>(null)
const langFilter = ref('')
const activeTab = ref('role-config')
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

const llm = ref<any>(null)
const llmLoading = ref(false)
const costDays = ref(7)

const importVisible = ref(false)
const importMode = ref('github')
const importSource = ref('')
const importBranch = ref('')
const importSkillId = ref('')
const importOverwrite = ref(false)
const importPreview = ref<any>(null)
const importPreviewLoading = ref(false)
const importLoading = ref(false)

const zipFile = ref<File | null>(null)
const zipFileList = ref<any[]>([])
const zipSkillId = ref('')
const zipOverwrite = ref(false)
const zipPreview = ref<any>(null)
const zipPreviewLoading = ref(false)
const zipImportLoading = ref(false)

const qaSkillsEnabled = ref(true)
const globalToggleLoading = ref(false)
const roleConfig = ref<any>(null)
const roleConfigDraft = ref<any[]>([])
const roleConfigLoading = ref(false)
const roleConfigSaving = ref(false)

const bindRoleDialogVisible = ref(false)
const bindRoleForm = ref({ role: '', skill_id: '', enabled: true })

const availableRolesForAdd = computed(() =>
  PIPELINE_ROLES.filter((r) => !roleConfigDraft.value.some((row: any) => row.role === r)),
)

function openBindRoleDialog() {
  if (!availableRolesForAdd.value.length) {
    ElMessage.warning('analysis / generation / review 均已绑定，请直接编辑表格中的 Skill')
    return
  }
  bindRoleForm.value = {
    role: availableRolesForAdd.value[0],
    skill_id: DEFAULT_SKILL_BY_ROLE[availableRolesForAdd.value[0]] || skillOptions.value[0]?.value || '',
    enabled: true,
  }
  bindRoleDialogVisible.value = true
}

function onConfirmBindRole() {
  const { role, skill_id, enabled } = bindRoleForm.value
  if (!role) {
    ElMessage.warning('请选择角色')
    return
  }
  if (!skill_id) {
    ElMessage.warning('请选择 Skill')
    return
  }
  if (roleConfigDraft.value.some((row: any) => row.role === role)) {
    ElMessage.warning('该角色已有绑定，请直接编辑表格')
    return
  }
  roleConfigDraft.value.push({
    role,
    config_id: `skill-${role}-${Date.now()}`,
    skill_id,
    enabled,
    effective_skill_id: skill_id,
    source: 'config',
    skill_exists: true,
    default_skill_id: DEFAULT_SKILL_BY_ROLE[role] || '',
    env_override: '',
  })
  bindRoleDialogVisible.value = false
  ElMessage.success('已添加绑定，请点击「保存配置」生效')
}

function roleLabel(role: string) {
  return ROLE_LABELS[role] || role
}

const skillOptions = computed(() =>
  (summary.value?.skills || [])
    .filter((s: any) => !s.error)
    .map((s: any) => ({
      value: s.skill_id,
      label: s.name ? `${s.skill_id} — ${s.name}` : s.skill_id,
    })),
)

function resetImportForm() {
  importPreview.value = null
  importMode.value = 'github'
  importSource.value = ''
  importBranch.value = ''
  importSkillId.value = ''
  importOverwrite.value = false
  zipFile.value = null
  zipFileList.value = []
  zipSkillId.value = ''
  zipOverwrite.value = false
  zipPreview.value = null
}

function formatBytes(v: number | null | undefined): string {
  const n = Number(v || 0)
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

function buildImportPayload() {
  return {
    source: importSource.value.trim(),
    branch: importBranch.value.trim() || undefined,
    skill_id: importSkillId.value.trim() || undefined,
    overwrite: importOverwrite.value,
  }
}

async function onPreviewImport() {
  if (!importSource.value.trim()) {
    ElMessage.warning('请输入 GitHub 链接或 skill 来源')
    return
  }
  importPreviewLoading.value = true
  try {
    const res = await previewGithubSkillImport(buildImportPayload())
    importPreview.value = unwrapApiData(res)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '预览失败')
  } finally {
    importPreviewLoading.value = false
  }
}

async function onImportSkill() {
  if (!importSource.value.trim()) {
    ElMessage.warning('请输入 GitHub 链接或 skill 来源')
    return
  }
  if (importPreview.value?.exists_locally && !importOverwrite.value) {
    try {
      await ElMessageBox.confirm(
        `本地已存在 Skill「${importPreview.value.ref?.skill_id}」，是否覆盖导入？`,
        '确认覆盖',
        { type: 'warning', confirmButtonText: '覆盖导入', cancelButtonText: '取消' },
      )
      importOverwrite.value = true
    } catch {
      return
    }
  }
  importLoading.value = true
  try {
    const res = await importGithubSkill(buildImportPayload())
    ElMessage.success(`已导入 Skill：${unwrapApiData<any>(res)?.skill_id}`)
    importVisible.value = false
    await loadList(false)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导入失败')
  } finally {
    importLoading.value = false
  }
}

function onZipFileChange(uploadFile: any) {
  zipFile.value = uploadFile?.raw || null
  zipFileList.value = uploadFile ? [uploadFile] : []
  zipPreview.value = null
}

function onZipFileRemove() {
  zipFile.value = null
  zipFileList.value = []
  zipPreview.value = null
}

async function onPreviewZipImport() {
  if (!zipFile.value) {
    ElMessage.warning('请先选择 ZIP 文件')
    return
  }
  zipPreviewLoading.value = true
  try {
    const res = await previewZipSkillImport(zipFile.value, zipSkillId.value || undefined)
    zipPreview.value = unwrapApiData(res)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '解析失败')
  } finally {
    zipPreviewLoading.value = false
  }
}

async function onImportZipSkill() {
  if (!zipFile.value) {
    ElMessage.warning('请先选择 ZIP 文件')
    return
  }
  if (!zipPreview.value) {
    await onPreviewZipImport()
    if (!zipPreview.value) return
  }
  if (zipPreview.value?.exists_locally && !zipOverwrite.value) {
    try {
      await ElMessageBox.confirm(
        `本地已存在 Skill「${zipPreview.value.analysis?.skill_id}」，是否覆盖导入？`,
        '确认覆盖',
        { type: 'warning', confirmButtonText: '覆盖导入', cancelButtonText: '取消' },
      )
      zipOverwrite.value = true
    } catch {
      return
    }
  }
  zipImportLoading.value = true
  try {
    const res = await importZipSkill(
      zipFile.value,
      zipSkillId.value || undefined,
      zipOverwrite.value,
    )
    ElMessage.success(`已导入 Skill：${unwrapApiData<any>(res)?.skill_id}`)
    importVisible.value = false
    await loadList(false)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导入失败')
  } finally {
    zipImportLoading.value = false
  }
}

async function loadLlm() {
  llmLoading.value = true
  try {
    const [cacheRes, concRes, priceRes, costRes] = await Promise.all([
      getLlmCacheStats(),
      getLlmConcurrencyStats(),
      getLlmPricing(),
      getLlmCostRecent(costDays.value),
    ])
    llm.value = {
      cache: unwrapApiData(cacheRes),
      concurrency: unwrapApiData(concRes),
      pricing: unwrapApiData(priceRes),
      cost: unwrapApiData(costRes),
    }
  } catch (e: any) {
    ElMessage.error(e?.message || 'LLM 治理数据加载失败')
  } finally {
    llmLoading.value = false
  }
}

async function onPurgeLlmCache() {
  try {
    const res = await purgeLlmCache()
    ElMessage.success(`已清理 ${unwrapApiData<any>(res)?.purged_expired ?? 0} 条过期缓存`)
    loadLlm()
  } catch (e: any) {
    ElMessage.error(e?.message || '清理失败')
  }
}

async function onClearLlmCache() {
  await ElMessageBox.confirm('清空全部 LLM 缓存（含 SQLite 持久化）？', '确认', { type: 'warning' })
  try {
    const res = await clearLlmCache()
    ElMessage.success(`已清空 ${unwrapApiData<any>(res)?.cleared ?? 0} 条 LLM 缓存`)
    loadLlm()
  } catch (e: any) {
    ElMessage.error(e?.message || '清空失败')
  }
}

async function onPurgeAudit() {
  await ElMessageBox.confirm('清理 30 天前的审计记录？', '确认', { type: 'warning' })
  try {
    const res = await purgeAudit(30)
    ElMessage.success(`已清理 ${unwrapApiData<any>(res)?.purged ?? 0} 条审计记录`)
  } catch (e: any) {
    ElMessage.error(e?.message || '清理失败')
  }
}

const pricingRows = computed<any[]>(() => {
  const p = llm.value?.pricing
  if (!p) return []
  const merged: Record<string, any> = {}
  for (const [model, rec] of Object.entries(p.default || {})) {
    const r: any = rec
    merged[model] = { model, prompt: r.prompt ?? r.input ?? '-', completion: r.completion ?? r.output ?? '-', source: 'default' }
  }
  for (const [model, rec] of Object.entries(p.overrides || {})) {
    const r: any = rec
    merged[model] = { model, prompt: r.prompt ?? r.input ?? '-', completion: r.completion ?? r.output ?? '-', source: 'override' }
  }
  return Object.values(merged)
})

function formatPct(v: number | null | undefined): string {
  if (v == null || isNaN(Number(v))) return '-'
  return (Number(v) * 100).toFixed(1) + '%'
}
function formatNum(v: number | null | undefined): string {
  if (v == null) return '0'
  return Number(v).toLocaleString()
}
function formatCost(v: number | null | undefined): string {
  if (v == null) return '0.0000'
  return Number(v).toFixed(4)
}

async function loadHealth() {
  healthLoading.value = true
  try {
    const res = await getSkillsHealth()
    health.value = unwrapApiData(res)
  } catch (e: any) {
    ElMessage.error(e?.message || '健康检查失败')
  } finally {
    healthLoading.value = false
  }
}

async function loadStats() {
  statsLoading.value = true
  try {
    const res = await getAuditStats()
    stats.value = unwrapApiData(res)
  } catch (e: any) {
    ElMessage.error(e?.message || '加载统计失败')
  } finally {
    statsLoading.value = false
  }
}

async function loadRoleConfig() {
  roleConfigLoading.value = true
  try {
    const data = unwrapApiData(await getSkillRoleBinding())
    roleConfig.value = data
    qaSkillsEnabled.value = !!data?.qa_skills_enabled
    roleConfigDraft.value = (data?.roles || []).map((r: any) => ({ ...r }))
  } catch (e: any) {
    ElMessage.error(e?.message || '加载角色配置失败')
  } finally {
    roleConfigLoading.value = false
  }
}

async function onSaveRoleConfig() {
  roleConfigSaving.value = true
  try {
    await updateSkillRoleBinding({
      qa_skills_enabled: qaSkillsEnabled.value,
      skill_configs: roleConfigDraft.value.map((r: any) => ({
        id: r.config_id,
        role: r.role,
        skill_id: r.skill_id,
        enabled: r.enabled,
      })),
    })
    ElMessage.success('角色配置已保存')
    await loadRoleConfig()
    await loadList(false)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '保存失败')
  } finally {
    roleConfigSaving.value = false
  }
}

async function onGlobalSkillToggle(val: boolean) {
  globalToggleLoading.value = true
  try {
    await updateSkillRoleBinding({ qa_skills_enabled: val })
    ElMessage.success(val ? '已启用 QA Skills' : '已关闭 QA Skills')
    await loadRoleConfig()
    await loadList(false)
  } catch (e: any) {
    qaSkillsEnabled.value = !val
    ElMessage.error(e?.message || '切换失败')
  } finally {
    globalToggleLoading.value = false
  }
}

async function onExportSkill(row: any) {
  try {
    const res: any = await exportSkill(row.skill_id)
    const blob = res.data instanceof Blob ? res.data : new Blob([res.data])
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.skill_id}.zip`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${row.skill_id}.zip`)
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  }
}

async function onDeleteSkill(row: any) {
  if (row.protected) {
    ElMessage.warning('内置 Skill 不可删除')
    return
  }
  if (row.referenced_by_roles?.length) {
    ElMessage.warning(`仍被角色引用：${row.referenced_by_roles.join('、')}，请先在「角色配置」修改绑定`)
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除 Skill「${row.skill_id}」？此操作不可恢复。`, '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteSkill(row.skill_id)
    ElMessage.success('已删除')
    await loadList(false)
    if (activeTab.value === 'role-config') {
      await loadRoleConfig()
    }
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    if (typeof detail === 'object' && detail?.references?.length) {
      const roles = detail.references.map((r: any) => r.role).join('、')
      ElMessage.error(`${detail.message || '删除失败'}（引用角色：${roles}）`)
    } else {
      ElMessage.error(typeof detail === 'string' ? detail : e?.message || '删除失败')
    }
  }
}

async function loadList(showOk: boolean) {
  loading.value = true
  try {
    const data = unwrapApiData(await listSkills(langFilter.value || undefined))
    summary.value = data
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
    const data = unwrapApiData(await getSkill(row.skill_id))
    selected.value = data
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
    const data = unwrapApiData(await listAuditRecent({
      limit: 100,
      role: auditRole.value || undefined,
      task_id: auditTaskId.value || undefined,
    }))
    auditItems.value = data?.items || []
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
    const res = await discoverFor(discoverInput.value)
    discoverResult.value = unwrapApiData(res)
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

watch(activeTab, (v) => {
  if (v === 'role-config' && !roleConfig.value) loadRoleConfig()
  if (v === 'llm' && !llm.value) loadLlm()
  if (v === 'health' && !health.value) loadHealth()
  if (v === 'stats' && !stats.value) loadStats()
})
watch(costDays, () => {
  if (activeTab.value === 'llm') loadLlm()
})

onMounted(async () => {
  await loadList(false)
  await loadRoleConfig()
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
