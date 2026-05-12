<template>
  <div class="space-y-6">
    <!-- 项目头部 + 立项流程 -->
    <div class="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
      <div class="absolute right-0 top-0 w-64 h-64 bg-white opacity-10 rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2"></div>
      <div class="relative z-10 flex items-start justify-between">
        <div>
          <div class="flex items-center gap-3 mb-2">
            <router-link to="/projects" class="text-indigo-200 hover:text-white transition-colors text-sm">← 返回项目列表</router-link>
          </div>
          <h1 class="text-2xl font-bold mb-1">{{ project.name || '加载中...' }}</h1>
          <p class="text-indigo-100 text-sm max-w-xl">{{ project.description || '暂无描述' }}</p>
        </div>
        <div class="flex items-center gap-3">
          <!-- 项目状态 -->
          <el-tag :type="projectStatusType(project.status)" effect="dark" round size="large">{{ projectStatusLabel(project.status) }}</el-tag>
          <el-button v-if="project.status === 'draft'" type="warning" round class="!bg-amber-400 !border-amber-500 !text-white" @click="handleApproval">
            🚀 立项审批
          </el-button>
          <el-button type="primary" round class="!bg-white/20 !border-white/30 !text-white hover:!bg-white/30" @click="editProject">编辑项目</el-button>
        </div>
      </div>

      <!-- 项目阶段进度条 -->
      <div class="mt-5 relative z-10 bg-white/10 rounded-xl p-4 backdrop-blur-sm">
        <div class="flex items-center justify-between">
          <div v-for="(ps, idx) in projectStages" :key="ps.value" class="flex items-center">
            <div class="flex flex-col items-center gap-1.5">
              <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all"
                :class="projectStageNodeClass(ps.value)">
                <span v-if="isProjectStageComplete(ps.value)">✓</span>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <span class="text-[10px] text-center leading-tight"
                :class="isProjectStageReached(ps.value) ? 'text-white font-medium' : 'text-indigo-300'">
                {{ ps.label }}
              </span>
            </div>
            <div v-if="idx < projectStages.length - 1" class="w-12 h-0.5 mx-1 mt-[-12px]"
              :class="isProjectStageComplete(ps.value) ? 'bg-white' : 'bg-white/30'"></div>
          </div>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-4 gap-4 mt-4 relative z-10">
        <div class="bg-white/15 rounded-xl p-3 backdrop-blur-sm">
          <div class="text-indigo-200 text-xs mb-1">需求总数</div>
          <div class="text-2xl font-bold">{{ stats.requirements }}</div>
        </div>
        <div class="bg-white/15 rounded-xl p-3 backdrop-blur-sm">
          <div class="text-indigo-200 text-xs mb-1">开发中</div>
          <div class="text-2xl font-bold">{{ stats.developing }}</div>
        </div>
        <div class="bg-white/15 rounded-xl p-3 backdrop-blur-sm">
          <div class="text-indigo-200 text-xs mb-1">测试中</div>
          <div class="text-2xl font-bold">{{ stats.testing }}</div>
        </div>
        <div class="bg-white/15 rounded-xl p-3 backdrop-blur-sm">
          <div class="text-indigo-200 text-xs mb-1">已上线</div>
          <div class="text-2xl font-bold">{{ stats.released }}</div>
        </div>
      </div>
    </div>

    <!-- Tab 导航 -->
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm">
      <div class="border-b border-gray-100 px-6">
        <nav class="flex gap-1 -mb-px">
          <button v-for="tab in tabs" :key="tab.key"
            class="px-5 py-3.5 text-sm font-medium transition-all border-b-2 rounded-t-lg"
            :class="activeTab === tab.key ? 'border-indigo-500 text-indigo-600 bg-indigo-50/50' : 'border-transparent text-gray-500 hover:text-gray-700'"
            @click="activeTab = tab.key">
            <span class="mr-1.5">{{ tab.icon }}</span>{{ tab.label }}
          </button>
        </nav>
      </div>

      <div class="p-6">
        <!-- 需求流程看板 -->
        <div v-if="activeTab === 'requirements'">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-800">需求流程看板</h3>
            <el-button v-if="project.status !== 'archived' && project.status !== 'draft'" type="primary" color="#4f46e5" @click="openReqDialog">+ 新建需求</el-button>
            <el-tag v-else-if="project.status === 'archived'" type="info" effect="plain">项目已归档，不可新建需求</el-tag>
          </div>

          <!-- 流程阶段概览 -->
          <div class="flex items-center gap-1 mb-4 flex-wrap">
            <div v-for="(stage, idx) in reqStages" :key="stage.value" class="flex items-center">
              <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs"
                :class="activeReqStage === stage.value ? 'bg-indigo-50 text-indigo-700 font-semibold ring-1 ring-indigo-200' : 'text-gray-500 hover:bg-gray-50 cursor-pointer'"
                @click="activeReqStage = activeReqStage === stage.value ? '' : stage.value">
                <span class="w-2 h-2 rounded-full" :style="{ background: stage.color }"></span>
                {{ stage.label }}
                <span class="bg-gray-100 rounded-full px-1.5 text-[10px]">{{ reqStageCount(stage.value) }}</span>
              </div>
              <span v-if="idx < reqStages.length - 1" class="text-gray-300 text-xs">→</span>
            </div>
          </div>

          <!-- 看板列 -->
          <div class="flex gap-3 overflow-x-auto pb-4">
            <div v-for="stage in visibleReqStages" :key="stage.value" class="w-[250px] shrink-0">
              <div class="flex items-center gap-2 mb-2 px-1">
                <span class="w-2 h-2 rounded-full" :style="{ background: stage.color }"></span>
                <span class="font-medium text-gray-700 text-sm">{{ stage.label }}</span>
                <span class="text-xs text-gray-400">({{ reqsByStage(stage.value).length }})</span>
              </div>
              <div class="space-y-2 max-h-[400px] overflow-y-auto pr-1">
                <div v-for="req in reqsByStage(stage.value)" :key="req.id"
                  class="bg-gray-50 rounded-xl p-3 border border-gray-100 hover:shadow-sm transition-all cursor-pointer group"
                  @click="openReqDetail(req)">
                  <div class="font-medium text-gray-800 text-sm mb-1">{{ req.title }}</div>
                  <div class="flex items-center justify-between">
                    <el-tag :type="priorityType(req.priority)" size="small" effect="light" round>{{ priorityLabel(req.priority) }}</el-tag>
                    <el-button v-if="nextReqStage(stage.value)" link size="small" type="primary"
                      class="!text-[10px] opacity-0 group-hover:opacity-100"
                      @click.stop="advanceReq(req, nextReqStage(stage.value)!)">→</el-button>
                  </div>
                </div>
                <div v-if="reqsByStage(stage.value).length === 0" class="text-center text-xs text-gray-300 py-6">暂无</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 版本迭代 -->
        <div v-if="activeTab === 'versions'">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-800">版本迭代</h3>
            <el-button type="primary" color="#4f46e5" @click="openVersionDialog">+ 新建版本</el-button>
          </div>
          <div class="space-y-3" v-if="versions.length">
            <div v-for="ver in versions" :key="ver.id" class="border border-gray-100 rounded-xl p-4 hover:shadow-sm transition-shadow flex items-center justify-between">
              <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-500 flex items-center justify-center text-lg font-bold">V</div>
                <div>
                  <div class="font-medium text-gray-800">{{ ver.name }}</div>
                  <div class="text-xs text-gray-400">{{ ver.start_date || '未设置' }} ~ {{ ver.end_date || '未设置' }}</div>
                </div>
              </div>
              <el-tag :type="versionStatusType(ver.status)" effect="light" size="small" round>{{ versionStatusLabel(ver.status) }}</el-tag>
            </div>
          </div>
          <el-empty v-else description="暂无版本迭代" />
        </div>

        <!-- 团队成员 -->
        <div v-if="activeTab === 'members'">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-800">团队成员 <span class="text-sm text-gray-400 font-normal ml-2">共 {{ members.length }} 人</span></h3>
            <el-button type="primary" color="#4f46e5" @click="openMemberDialog">+ 添加成员</el-button>
          </div>

          <div v-if="members.length" class="space-y-6">
            <div v-for="roleConf in memberRoles" :key="roleConf.value">
              <template v-if="membersByRole[roleConf.value]?.length">
                <div class="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
                  <span class="text-lg">{{ roleConf.icon }}</span>
                  <span class="font-semibold text-gray-700">{{ roleConf.label }}</span>
                  <span class="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5">{{ membersByRole[roleConf.value].length }}</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                  <div v-for="m in membersByRole[roleConf.value]" :key="m.id"
                    class="bg-white border border-gray-100 rounded-xl p-4 flex items-center gap-3 hover:shadow-md transition-all group">
                    <div class="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                      :style="{ background: roleConf.color }">
                      {{ (m.employee?.name || '?')[0] }}
                    </div>
                    <div class="flex-1 min-w-0">
                      <div class="font-medium text-gray-800 text-sm truncate">{{ m.employee?.name || `员工 #${m.employee_id}` }}</div>
                      <div class="text-xs text-gray-400 truncate">{{ m.employee?.position || m.employee?.department || '' }}</div>
                    </div>
                    <el-button link type="danger" size="small" class="opacity-0 group-hover:opacity-100 transition-opacity"
                      @click="removeMember(m)">移除</el-button>
                  </div>
                </div>
              </template>
            </div>

            <div v-if="membersByRole['other']?.length">
              <div class="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
                <span class="text-lg">👤</span>
                <span class="font-semibold text-gray-700">其他</span>
                <span class="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5">{{ membersByRole['other'].length }}</span>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                <div v-for="m in membersByRole['other']" :key="m.id"
                  class="bg-white border border-gray-100 rounded-xl p-4 flex items-center gap-3 hover:shadow-md transition-all group">
                  <div class="w-10 h-10 rounded-full bg-gray-400 flex items-center justify-center text-white text-sm font-bold shrink-0">
                    {{ (m.employee?.name || '?')[0] }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-gray-800 text-sm truncate">{{ m.employee?.name || `员工 #${m.employee_id}` }}</div>
                    <div class="text-xs text-gray-400 truncate">{{ m.employee?.position || '' }}</div>
                  </div>
                  <el-button link type="danger" size="small" class="opacity-0 group-hover:opacity-100 transition-opacity"
                    @click="removeMember(m)">移除</el-button>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无团队成员" />
        </div>

        <!-- 测试排期甘特图 -->
        <div v-if="activeTab === 'test-schedule'">
          <div v-if="testScheduleLoading" class="flex items-center justify-center py-16">
            <el-icon class="is-loading text-2xl text-indigo-500 mr-2"><Loading /></el-icon>
            <span class="text-gray-500">加载排期数据...</span>
          </div>
          <div v-else-if="testScheduleData.length === 0" class="text-center py-12">
            <el-empty description="暂无排期数据，请在需求详情中为节点分配人员和排期时间" />
          </div>
          <div v-else>
            <!-- 图例 -->
            <div class="flex items-center gap-4 mb-4 flex-wrap">
              <span class="text-sm font-medium text-gray-600 mr-1">节点图例：</span>
              <span v-for="node in ganttNodeTypes" :key="node.value"
                class="inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-md"
                :style="{ background: node.color + '18', color: node.color }">
                <span class="w-2.5 h-2.5 rounded-sm" :style="{ background: node.color }"></span>
                {{ node.label }}
              </span>
            </div>

            <!-- 甘特图区域 -->
            <div class="border border-gray-200 rounded-xl overflow-hidden">
              <!-- 表头：日期轴 -->
              <div class="flex bg-gray-50 border-b border-gray-200 sticky top-0 z-10">
                <div class="w-[240px] shrink-0 px-4 py-2.5 text-sm font-semibold text-gray-700 border-r border-gray-200">
                  需求名称
                </div>
                <div class="flex-1 overflow-x-auto">
                  <div class="flex" :style="{ minWidth: ganttDays.length * 36 + 'px' }">
                    <div v-for="day in ganttDays" :key="day.date"
                      class="text-center text-[10px] leading-tight border-r border-gray-100 shrink-0"
                      :class="day.isWeekend ? 'bg-gray-100 text-gray-400' : day.isToday ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-gray-500'"
                      :style="{ width: '36px' }">
                      <div class="py-1 border-b border-gray-100">{{ day.monthLabel }}</div>
                      <div class="py-1">{{ day.dayLabel }}</div>
                      <div class="pb-1 text-[9px]">{{ day.weekLabel }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 数据行 -->
              <div v-for="req in testScheduleData" :key="req.requirement_id"
                class="flex border-b border-gray-100 last:border-b-0 hover:bg-indigo-50/30 transition-colors">
                <!-- 左侧需求标题 -->
                <div class="w-[240px] shrink-0 px-4 py-3 border-r border-gray-200 flex items-start gap-2">
                  <router-link :to="`/requirements/${req.requirement_id}`"
                    class="text-sm text-indigo-600 hover:text-indigo-800 font-medium line-clamp-2 leading-snug">
                    {{ req.requirement_title }}
                  </router-link>
                </div>
                <!-- 右侧甘特条 -->
                <div class="flex-1 relative overflow-x-auto">
                  <div class="relative" :style="{ minWidth: ganttDays.length * 36 + 'px', height: req.nodes.length > 0 ? (req.nodes.length * 28 + 8) + 'px' : '36px' }">
                    <!-- 周末底色条 -->
                    <div v-for="day in ganttDays.filter(d => d.isWeekend)" :key="'bg-' + day.date"
                      class="absolute top-0 bottom-0 bg-gray-50/80"
                      :style="{ left: day.offset * 36 + 'px', width: '36px' }">
                    </div>
                    <!-- 今天竖线 -->
                    <div v-if="ganttTodayOffset >= 0"
                      class="absolute top-0 bottom-0 border-l-2 border-red-400 z-[5]"
                      :style="{ left: ganttTodayOffset * 36 + 18 + 'px' }">
                    </div>
                    <!-- 节点条 -->
                    <div v-for="(node, nIdx) in req.nodes" :key="node.node"
                      class="absolute h-5 rounded-md flex items-center px-1.5 text-[10px] text-white font-medium truncate cursor-pointer group z-[3]"
                      :style="ganttBarStyle(node, nIdx)"
                      :title="`${node.node_label}: ${node.planned_time || '未设置'}\n人员: ${node.members.map((m: any) => m.name).join(', ')}`">
                      <span class="truncate">{{ node.node_label }}</span>
                      <!-- Tooltip -->
                      <div class="hidden group-hover:block absolute bottom-full left-0 mb-1 bg-gray-900 text-white text-xs rounded-lg p-2.5 whitespace-nowrap z-50 shadow-lg">
                        <div class="font-semibold mb-1">{{ node.node_label }}</div>
                        <div class="text-gray-300">{{ node.planned_time || '未设置时间' }}</div>
                        <div v-if="node.members.length" class="text-gray-300 mt-0.5">
                          人员: {{ node.members.map((m: any) => m.name).join(', ') }}
                        </div>
                      </div>
                    </div>
                    <!-- 无排期提示 -->
                    <div v-if="req.nodes.length === 0"
                      class="absolute inset-0 flex items-center justify-center text-xs text-gray-300">
                      暂无排期
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 项目日历 -->
        <div v-if="activeTab === 'calendar'">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <el-button circle size="small" @click="changeMonth(-1)">‹</el-button>
              <h3 class="text-lg font-semibold text-gray-800">{{ calYear }} 年 {{ calMonth + 1 }} 月</h3>
              <el-button circle size="small" @click="changeMonth(1)">›</el-button>
            </div>
            <el-button type="primary" color="#4f46e5" @click="openScheduleDialog">+ 新建排期</el-button>
          </div>
          <div class="grid grid-cols-7 text-center text-sm font-medium text-gray-500 mb-2">
            <div v-for="d in weekDays" :key="d" class="py-2">{{ d }}</div>
          </div>
          <div class="grid grid-cols-7 gap-px bg-gray-100 rounded-xl overflow-hidden">
            <div v-for="(cell, idx) in calendarCells" :key="idx"
              class="bg-white min-h-[80px] p-1.5 cursor-pointer transition-colors hover:bg-indigo-50/40"
              :class="{ 'opacity-40': !cell.isCurrentMonth }">
              <div class="text-xs font-medium mb-1"
                :class="cell.isToday ? 'text-white bg-indigo-500 rounded-full w-5 h-5 flex items-center justify-center mx-auto text-[10px]' : 'text-gray-700 text-center'">
                {{ cell.day }}
              </div>
              <div v-for="ev in cell.events.slice(0, 2)" :key="ev.id" class="text-[10px] leading-tight px-1 py-0.5 rounded truncate mb-0.5 bg-blue-100 text-blue-700">
                {{ ev.title }}
              </div>
              <div v-if="cell.events.length > 2" class="text-[10px] text-gray-400 text-center">+{{ cell.events.length - 2 }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 需求弹窗 -->
    <el-dialog v-model="reqDialogVisible" :title="editingReq ? '编辑需求' : '新建需求'" width="580px" destroy-on-close>
      <el-form :model="reqForm" label-width="80px" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="reqForm.title" placeholder="请输入需求标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="reqForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-4">
          <el-form-item label="优先级">
            <el-select v-model="reqForm.priority" class="w-full">
              <el-option label="紧急" value="critical" />
              <el-option label="高" value="high" />
              <el-option label="中" value="medium" />
              <el-option label="低" value="low" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联版本">
            <el-select v-model="reqForm.version_id" clearable placeholder="选择版本" class="w-full">
              <el-option v-for="v in versions" :key="v.id" :label="v.name" :value="v.id" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="reqDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="submitReq">确定</el-button>
      </template>
    </el-dialog>

    <!-- 需求详情弹窗(含流程进度) -->
    <el-dialog v-model="reqDetailVisible" :title="detailReq?.title || '需求详情'" width="650px" destroy-on-close>
      <template v-if="detailReq">
        <div class="mb-5 bg-gray-50 rounded-xl p-4">
          <div class="flex items-center justify-between relative">
            <div class="absolute top-4 left-6 right-6 h-0.5 bg-gray-200 z-0"></div>
            <div v-for="(stage, idx) in reqStages" :key="stage.value" class="relative z-10 flex flex-col items-center w-14">
              <div class="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-all"
                :class="detailStageClass(stage.value)">
                {{ idx + 1 }}
              </div>
              <span class="text-[9px] mt-1 text-center leading-tight"
                :class="isReqStageReached(stage.value) ? 'text-gray-700 font-medium' : 'text-gray-400'">
                {{ stage.shortLabel }}
              </span>
            </div>
          </div>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="当前阶段">
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full" :style="{ background: reqStageColor(detailReq.status) }"></span>
              {{ reqStageLabel(detailReq.status) }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityType(detailReq.priority)" size="small" effect="light">{{ priorityLabel(detailReq.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            <div class="whitespace-pre-wrap text-sm text-gray-600">{{ detailReq.description || '暂无' }}</div>
          </el-descriptions-item>
        </el-descriptions>
        <div class="mt-4 flex justify-between">
          <el-button v-if="prevReqStage(detailReq.status)" size="small" @click="advanceReq(detailReq, prevReqStage(detailReq.status)!)">
            ← 回退
          </el-button>
          <span v-else></span>
          <el-button v-if="nextReqStage(detailReq.status)" type="primary" color="#4f46e5" size="small" @click="advanceReq(detailReq, nextReqStage(detailReq.status)!)">
            推进到 {{ reqStageLabel(nextReqStage(detailReq.status)!) }} →
          </el-button>
          <el-tag v-else type="success" effect="dark" round>已上线</el-tag>
        </div>
      </template>
    </el-dialog>

    <!-- 版本弹窗 -->
    <el-dialog v-model="versionDialogVisible" title="新建版本" width="480px" destroy-on-close>
      <el-form :model="versionForm" label-width="80px">
        <el-form-item label="版本名称" required><el-input v-model="versionForm.name" placeholder="如 v1.0.0" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="versionForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="versionForm.start_date" type="date" value-format="YYYY-MM-DD" class="!w-full" /></el-form-item>
        <el-form-item label="结束日期"><el-date-picker v-model="versionForm.end_date" type="date" value-format="YYYY-MM-DD" class="!w-full" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="versionDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="submitVersion">确定</el-button>
      </template>
    </el-dialog>

    <!-- 成员弹窗 -->
    <el-dialog v-model="memberDialogVisible" title="添加成员" width="480px" destroy-on-close>
      <el-form :model="memberForm" label-width="70px">
        <el-form-item label="角色">
          <el-select v-model="memberForm.role" class="w-full" placeholder="选择角色">
            <el-option v-for="r in memberRoles" :key="r.value" :value="r.value">
              <span>{{ r.icon }} {{ r.label }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="员工">
          <el-select v-model="memberForm.employee_id" placeholder="搜索并选择员工" class="w-full" filterable>
            <el-option v-for="e in availableEmployees" :key="e.id" :label="e.name" :value="e.id">
              <div class="flex items-center justify-between">
                <span>{{ e.name }}</span>
                <span class="text-xs text-gray-400">{{ e.position || e.role || '' }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="submitMember">确定</el-button>
      </template>
    </el-dialog>

    <!-- 排期弹窗 -->
    <el-dialog v-model="scheduleDialogVisible" title="新建排期" width="480px" destroy-on-close>
      <el-form :model="scheduleForm" label-width="80px">
        <el-form-item label="成员"><el-select v-model="scheduleForm.employee_id" placeholder="选择成员" class="w-full">
          <el-option v-for="m in members" :key="m.user_id" :label="m.user_name || `用户#${m.user_id}`" :value="m.user_id" />
        </el-select></el-form-item>
        <el-form-item label="标题"><el-input v-model="scheduleForm.title" /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="scheduleForm.schedule_date" type="date" value-format="YYYY-MM-DD" class="!w-full" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="scheduleForm.schedule_type" class="w-full">
          <el-option label="工作排期" value="work" /><el-option label="培训" value="training" /><el-option label="会议" value="meeting" />
        </el-select></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="submitSchedule">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑项目弹窗 -->
    <el-dialog v-model="editDialogVisible" title="编辑项目" width="500px" destroy-on-close>
      <el-form :model="projectForm" label-width="80px">
        <el-form-item label="项目名称" required><el-input v-model="projectForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="projectForm.description" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="projectForm.status" class="w-full">
            <el-option label="草稿" value="draft" />
            <el-option label="已立项" value="approved" />
            <el-option label="进行中" value="active" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" color="#4f46e5" @click="submitProjectEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import request from '../../utils/request'

const route = useRoute()
const projectId = computed(() => Number(route.params.id))

const tabs = [
  { key: 'requirements', label: '需求流程', icon: '🔄' },
  { key: 'test-schedule', label: '测试排期', icon: '📊' },
  { key: 'versions', label: '版本迭代', icon: '🏷️' },
  { key: 'members', label: '团队成员', icon: '👥' },
  { key: 'calendar', label: '项目日历', icon: '📅' },
]
const activeTab = ref('requirements')

const projectStages = [
  { value: 'draft', label: '草稿' },
  { value: 'approved', label: '已立项' },
  { value: 'active', label: '进行中' },
  { value: 'archived', label: '已归档' },
]
const projectStageOrder = projectStages.map(s => s.value)

const reqStages = [
  { value: 'requirement_review', label: '需求评审', shortLabel: '需求评审', color: '#8b5cf6' },
  { value: 'tech_review', label: '技术评审', shortLabel: '技术评审', color: '#6366f1' },
  { value: 'case_review', label: '用例评审', shortLabel: '用例评审', color: '#0ea5e9' },
  { value: 'testing', label: '测试执行', shortLabel: '测试执行', color: '#14b8a6' },
  { value: 'acceptance', label: '验收测试', shortLabel: '验收', color: '#f59e0b' },
  { value: 'released', label: '发布上线', shortLabel: '发布上线', color: '#22c55e' },
  { value: 'regression', label: '线上回归', shortLabel: '线上回归', color: '#ef4444' },
]
const reqStageOrder = reqStages.map(s => s.value)

// ---- Project ----
const project = ref<any>({})
const editDialogVisible = ref(false)
const projectForm = reactive({ name: '', description: '', status: 'draft' })

async function fetchProject() {
  try {
    const resp = await request.get(`/projects/${projectId.value}`)
    project.value = resp.data?.data || {}
  } catch {}
}

function editProject() {
  projectForm.name = project.value.name || ''
  projectForm.description = project.value.description || ''
  projectForm.status = project.value.status || 'draft'
  editDialogVisible.value = true
}

async function submitProjectEdit() {
  await request.put(`/projects/${projectId.value}`, projectForm)
  ElMessage.success('项目已更新')
  editDialogVisible.value = false
  fetchProject()
}

async function handleApproval() {
  await ElMessageBox.confirm('确认将项目立项？立项后可开始创建需求文档。', '项目立项', { confirmButtonText: '确认立项', type: 'info' })
  await request.put(`/projects/${projectId.value}`, { ...project.value, status: 'approved' })
  ElMessage.success('🎉 项目已成功立项！现在可以创建需求文档了。')
  fetchProject()
}

function projectStageNodeClass(stage: string) {
  const si = projectStageOrder.indexOf(stage)
  const ci = projectStageOrder.indexOf(project.value.status || 'draft')
  if (si < ci) return 'bg-white border-white text-indigo-600'
  if (si === ci) return 'bg-white/20 border-white text-white ring-2 ring-white/50'
  return 'bg-transparent border-white/40 text-white/50'
}
function isProjectStageComplete(stage: string) {
  return projectStageOrder.indexOf(stage) < projectStageOrder.indexOf(project.value.status || 'draft')
}
function isProjectStageReached(stage: string) {
  return projectStageOrder.indexOf(stage) <= projectStageOrder.indexOf(project.value.status || 'draft')
}
function projectStatusLabel(s: string) { return { draft: '草稿', approved: '已立项', active: '进行中', archived: '已归档', suspended: '已暂停' }[s] || s }
function projectStatusType(s: string) { return ({ draft: 'info', approved: 'warning', active: 'success', archived: '', suspended: 'danger' } as any)[s] || 'info' }

// ---- Stats ----
const stats = reactive({ requirements: 0, developing: 0, testing: 0, released: 0 })
function updateStats() {
  stats.requirements = requirements.value.length
  stats.developing = requirements.value.filter(r => ['tech_review', 'case_review'].includes(r.status)).length
  stats.testing = requirements.value.filter(r => ['testing', 'acceptance'].includes(r.status)).length
  stats.released = requirements.value.filter(r => ['released', 'regression'].includes(r.status)).length
}

// ---- Requirements ----
const requirements = ref<any[]>([])
const activeReqStage = ref('')
const reqDialogVisible = ref(false)
const editingReq = ref<any>(null)
const reqForm = reactive({ title: '', description: '', priority: 'medium', version_id: null as number | null })
const reqDetailVisible = ref(false)
const detailReq = ref<any>(null)

const visibleReqStages = computed(() => activeReqStage.value ? reqStages.filter(s => s.value === activeReqStage.value) : reqStages)

function reqStageCount(status: string) { return requirements.value.filter(r => r.status === status).length }
function reqsByStage(status: string) { return requirements.value.filter(r => r.status === status) }
function reqStageColor(status: string) { return reqStages.find(s => s.value === status)?.color || '#94a3b8' }
function reqStageLabel(status: string) { return reqStages.find(s => s.value === status)?.label || status }

function nextReqStage(current: string): string | null {
  const idx = reqStageOrder.indexOf(current)
  return idx >= 0 && idx < reqStageOrder.length - 1 ? reqStageOrder[idx + 1] : null
}
function prevReqStage(current: string): string | null {
  const idx = reqStageOrder.indexOf(current)
  return idx > 0 ? reqStageOrder[idx - 1] : null
}

function isReqStageReached(stage: string) {
  if (!detailReq.value) return false
  return reqStageOrder.indexOf(stage) <= reqStageOrder.indexOf(detailReq.value.status)
}
function detailStageClass(stage: string) {
  if (!detailReq.value) return 'bg-white border-gray-300 text-gray-400'
  const si = reqStageOrder.indexOf(stage)
  const ci = reqStageOrder.indexOf(detailReq.value.status)
  if (si < ci) return 'bg-indigo-500 border-indigo-500 text-white'
  if (si === ci) return 'bg-white border-indigo-500 text-indigo-600 ring-2 ring-indigo-200'
  return 'bg-white border-gray-300 text-gray-400'
}

async function advanceReq(req: any, newStatus: string) {
  try {
    const resp = await request.put(`/requirements/${req.id}`, { ...req, status: newStatus })
    ElMessage.success(`已推进到「${reqStageLabel(newStatus)}」`)
    if (detailReq.value?.id === req.id) detailReq.value.status = newStatus

    const result = resp.data?.data
    if (result?.auto_archived) {
      ElMessage.success({ message: '该项目下所有需求已完成线上回归，项目已自动归档', duration: 5000 })
      fetchProject()
    }
    fetchRequirements()
  } catch { ElMessage.error('操作失败') }
}

function openReqDetail(req: any) { detailReq.value = { ...req }; reqDetailVisible.value = true }

function openReqDialog() {
  editingReq.value = null
  reqForm.title = ''; reqForm.description = ''; reqForm.priority = 'medium'; reqForm.version_id = null
  reqDialogVisible.value = true
}

async function submitReq() {
  if (!reqForm.title?.trim()) { ElMessage.warning('请输入需求标题'); return }
  const payload = { ...reqForm, project_id: projectId.value, status: 'requirement_review' }
  if (editingReq.value) {
    await request.put(`/requirements/${editingReq.value.id}`, payload)
    ElMessage.success('需求已更新')
  } else {
    const resp = await request.post('/requirements', payload)
    const result = resp.data?.data
    if (result?.project_activated) {
      ElMessage.success('需求已创建，项目已自动进入「进行中」状态')
      fetchProject()
    } else {
      ElMessage.success('需求已创建，进入需求评审阶段')
    }
  }
  reqDialogVisible.value = false
  fetchRequirements()
}

async function fetchRequirements() {
  try {
    const params: any = { project_id: projectId.value, page_size: 100 }
    const resp = await request.get('/requirements', { params })
    const payload = resp.data?.data
    requirements.value = payload?.items || payload || resp.data?.items || (Array.isArray(resp.data) ? resp.data : [])
    updateStats()
  } catch {}
}

// ---- Versions ----
const versions = ref<any[]>([])
const versionDialogVisible = ref(false)
const versionForm = reactive({ name: '', description: '', start_date: '', end_date: '' })

async function fetchVersions() {
  try { const resp = await request.get(`/projects/${projectId.value}/versions`); versions.value = resp.data?.data || [] } catch {}
}
function openVersionDialog() { versionForm.name = ''; versionForm.description = ''; versionForm.start_date = ''; versionForm.end_date = ''; versionDialogVisible.value = true }
async function submitVersion() {
  await request.post(`/projects/${projectId.value}/versions`, versionForm)
  ElMessage.success('版本已创建'); versionDialogVisible.value = false; fetchVersions()
}
function versionStatusLabel(s: string) { return { planning: '规划中', active: '进行中', released: '已发布', closed: '已关闭' }[s] || s }
function versionStatusType(s: string) { return ({ planning: 'info', active: 'success', released: '', closed: 'info' } as any)[s] || '' }

// ---- Members ----
const members = ref<any[]>([])
const allEmployees = ref<any[]>([])
const memberDialogVisible = ref(false)
const memberForm = reactive({ employee_id: null as number | null, role: 'developer' })

const memberRoles = [
  { value: 'product', label: '产品', icon: '📋', color: '#8b5cf6' },
  { value: 'developer', label: '开发', icon: '💻', color: '#3b82f6' },
  { value: 'tester', label: '测试', icon: '🧪', color: '#22c55e' },
  { value: 'leader', label: '组长', icon: '👑', color: '#f59e0b' },
  { value: 'pm', label: '项目经理', icon: '📊', color: '#ef4444' },
  { value: 'designer', label: '设计', icon: '🎨', color: '#ec4899' },
]

const membersByRole = computed(() => {
  const grouped: Record<string, any[]> = {}
  for (const role of memberRoles) {
    const ms = members.value.filter(m => m.role === role.value)
    if (ms.length > 0) grouped[role.value] = ms
  }
  const knownRoles = new Set(memberRoles.map(r => r.value))
  const others = members.value.filter(m => !knownRoles.has(m.role))
  if (others.length > 0) grouped['other'] = others
  return grouped
})

const availableEmployees = computed(() => {
  const existingIds = new Set(members.value.map(m => m.employee_id).filter(Boolean))
  return allEmployees.value.filter(e => !existingIds.has(e.id) && e.status === 'active')
})

async function fetchMembers() {
  try {
    const resp = await request.get(`/projects/${projectId.value}/members`)
    members.value = resp.data?.data || []
  } catch {}
}

async function fetchAllEmployees() {
  try {
    const resp = await request.get('/hr/employees')
    const data = resp.data?.data
    if (Array.isArray(data)) {
      allEmployees.value = data
    } else if (data?.items) {
      allEmployees.value = data.items
    } else {
      allEmployees.value = []
    }
  } catch {}
}

function openMemberDialog() {
  memberForm.employee_id = null
  memberForm.role = 'developer'
  memberDialogVisible.value = true
}

async function submitMember() {
  if (!memberForm.employee_id) { ElMessage.warning('请选择员工'); return }
  try {
    await request.post(`/projects/${projectId.value}/members`, memberForm)
    ElMessage.success('成员已添加')
    memberDialogVisible.value = false
    fetchMembers()
  } catch (e: any) {
    ElMessage.error(e?.data?.msg || '添加失败')
  }
}

async function removeMember(m: any) {
  try {
    await ElMessageBox.confirm(`确认移除成员「${m.employee?.name || ''}」？`, '提示', { type: 'warning' })
    await request.delete(`/projects/${projectId.value}/members/${m.id}`)
    ElMessage.success('成员已移除')
    fetchMembers()
  } catch {}
}

// ---- Test Schedule (Gantt) ----
const testScheduleLoading = ref(false)
const testScheduleData = ref<any[]>([])
const testScheduleDateRange = ref<{ start: string; end: string } | null>(null)

const ganttNodeTypes = [
  { value: 'requirement_review', label: '需求评审', color: '#8b5cf6' },
  { value: 'tech_review', label: '技术评审', color: '#6366f1' },
  { value: 'case_review', label: '用例评审', color: '#0ea5e9' },
  { value: 'testing', label: '测试执行', color: '#14b8a6' },
  { value: 'acceptance', label: '验收测试', color: '#f59e0b' },
  { value: 'released', label: '发布上线', color: '#22c55e' },
  { value: 'regression', label: '线上回归', color: '#ef4444' },
]

function nodeColor(nodeKey: string): string {
  return ganttNodeTypes.find(n => n.value === nodeKey)?.color || '#94a3b8'
}

const ganttDays = computed(() => {
  const range = testScheduleDateRange.value
  if (!range) return []
  const start = new Date(range.start)
  const end = new Date(range.end)
  start.setDate(start.getDate() - 2)
  end.setDate(end.getDate() + 2)
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const days: any[] = []
  const cur = new Date(start)
  let lastMonth = ''
  while (cur <= end) {
    const y = cur.getFullYear()
    const m = String(cur.getMonth() + 1).padStart(2, '0')
    const d = String(cur.getDate()).padStart(2, '0')
    const dateStr = `${y}-${m}-${d}`
    const weekDay = cur.getDay()
    const weekLabels = ['日', '一', '二', '三', '四', '五', '六']
    const mLabel = `${m}月`
    days.push({
      date: dateStr,
      dayLabel: d,
      monthLabel: mLabel !== lastMonth ? mLabel : '',
      weekLabel: weekLabels[weekDay],
      isWeekend: weekDay === 0 || weekDay === 6,
      isToday: dateStr === todayStr,
      offset: days.length,
    })
    if (mLabel !== lastMonth) lastMonth = mLabel
    cur.setDate(cur.getDate() + 1)
  }
  return days
})

const ganttTodayOffset = computed(() => {
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const idx = ganttDays.value.findIndex(d => d.date === todayStr)
  return idx
})

function ganttBarStyle(node: any, rowIdx: number | string) {
  const row = Number(rowIdx) || 0
  if (!node.start_date || !node.end_date || ganttDays.value.length === 0) {
    return { display: 'none' }
  }
  const startIdx = ganttDays.value.findIndex(d => d.date === node.start_date)
  const endIdx = ganttDays.value.findIndex(d => d.date === node.end_date)
  if (startIdx < 0 || endIdx < 0) return { display: 'none' }
  const left = startIdx * 36
  const width = Math.max((endIdx - startIdx + 1) * 36, 36)
  return {
    left: left + 'px',
    width: width + 'px',
    top: row * 28 + 4 + 'px',
    background: nodeColor(node.node),
  }
}

async function fetchTestSchedule() {
  testScheduleLoading.value = true
  try {
    const resp = await request.get(`/projects/${projectId.value}/test-schedule`)
    const data = resp.data?.data
    testScheduleData.value = data?.requirements || []
    testScheduleDateRange.value = data?.date_range || null
  } catch {
    testScheduleData.value = []
    testScheduleDateRange.value = null
  } finally {
    testScheduleLoading.value = false
  }
}

// ---- Calendar ----
const weekDays = ['一', '二', '三', '四', '五', '六', '日']
const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth())
const schedules = ref<any[]>([])
const scheduleDialogVisible = ref(false)
const scheduleForm = reactive({ employee_id: null as number | null, title: '', schedule_date: '', schedule_type: 'work' })

function changeMonth(d: number) { const dt = new Date(calYear.value, calMonth.value + d, 1); calYear.value = dt.getFullYear(); calMonth.value = dt.getMonth(); fetchSchedules() }

const calendarCells = computed(() => {
  const first = new Date(calYear.value, calMonth.value, 1)
  const startDay = (first.getDay() + 6) % 7
  const daysInMonth = new Date(calYear.value, calMonth.value + 1, 0).getDate()
  const prevDays = new Date(calYear.value, calMonth.value, 0).getDate()
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const cells: any[] = []
  for (let i = startDay - 1; i >= 0; i--) {
    const d = prevDays - i; const m = calMonth.value === 0 ? 12 : calMonth.value; const y = calMonth.value === 0 ? calYear.value - 1 : calYear.value
    const ds = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, date: ds, isCurrentMonth: false, isToday: false, events: eventsForDate(ds) })
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${calYear.value}-${String(calMonth.value + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, date: ds, isCurrentMonth: true, isToday: ds === todayStr, events: eventsForDate(ds) })
  }
  const rem = 42 - cells.length
  for (let d = 1; d <= rem; d++) {
    const m = calMonth.value + 2 > 12 ? 1 : calMonth.value + 2; const y = calMonth.value + 2 > 12 ? calYear.value + 1 : calYear.value
    const ds = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, date: ds, isCurrentMonth: false, isToday: false, events: eventsForDate(ds) })
  }
  return cells
})
function eventsForDate(date: string) { return schedules.value.filter(s => s.schedule_date === date) }

async function fetchSchedules() {
  try {
    const sd = `${calYear.value}-${String(calMonth.value + 1).padStart(2, '0')}-01`
    const ed = `${calYear.value}-${String(calMonth.value + 1).padStart(2, '0')}-31`
    const resp = await request.get('/hr/schedules', { params: { project_id: projectId.value, start_date: sd, end_date: ed } })
    schedules.value = resp.data?.data || []
  } catch {}
}
function openScheduleDialog() { scheduleForm.employee_id = null; scheduleForm.title = ''; scheduleForm.schedule_date = ''; scheduleForm.schedule_type = 'work'; scheduleDialogVisible.value = true }
async function submitSchedule() {
  await request.post('/hr/schedules', { ...scheduleForm, project_id: projectId.value })
  ElMessage.success('排期已创建'); scheduleDialogVisible.value = false; fetchSchedules()
}

// ---- Helpers ----
function priorityLabel(p: string) { return { critical: '紧急', high: '高', medium: '中', low: '低' }[p] || p }
function priorityType(p: string) { return ({ critical: 'danger', high: 'warning', medium: '', low: 'info' } as any)[p] || '' }

// ---- Init ----
onMounted(() => { fetchProject(); fetchRequirements(); fetchVersions(); fetchMembers(); fetchAllEmployees(); fetchSchedules() })
watch(activeTab, (tab) => {
  if (tab === 'calendar') fetchSchedules()
  if (tab === 'test-schedule') fetchTestSchedule()
})
</script>
