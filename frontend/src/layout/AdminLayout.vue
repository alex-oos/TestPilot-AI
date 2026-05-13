<template>
  <div class="min-h-screen bg-gray-50 flex">
    
    <!-- Mobile overlay -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/40 z-10 md:hidden"
      @click="sidebarOpen = false"
    ></div>

    <!-- Sidebar -->
    <aside
      class="bg-slate-900 text-slate-300 flex flex-col transition-all duration-300 z-20 shadow-xl fixed md:relative inset-y-0 left-0"
      :class="[
        sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        sidebarCollapsed ? 'w-16' : 'w-64'
      ]"
    >
      <!-- Logo Area -->
      <div class="h-14 flex items-center bg-slate-950/50 border-b border-slate-800" :class="sidebarCollapsed ? 'justify-center px-2' : 'px-6'">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30 flex items-center justify-center text-white text-base select-none shrink-0">
            🌙
          </div>
          <span v-show="!sidebarCollapsed" class="text-[15px] font-bold text-white tracking-tight whitespace-nowrap">月亮邮寄员</span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto" :class="sidebarCollapsed ? 'p-2 space-y-1' : 'p-3 space-y-1'">

        <!-- 数据看板 -->
        <router-link 
          to="/dashboard" 
          class="nav-item"
          :class="[isActive('/dashboard') && 'nav-active', sidebarCollapsed && 'justify-center !px-0 !gap-0']"
          :title="sidebarCollapsed ? '数据看板' : ''"
        >
          <span>📊</span>
          <span v-show="!sidebarCollapsed">数据看板</span>
        </router-link>

        <!-- 项目工作流 -->
        <div v-show="!sidebarCollapsed" class="mt-2 mb-1 px-3">
          <span class="text-[10px] font-semibold uppercase tracking-widest text-slate-500">项目工作流</span>
        </div>
        <template v-if="sidebarCollapsed">
          <router-link to="/projects" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/projects') && 'nav-active'" title="项目管理"><span>📁</span></router-link>
          <router-link to="/requirements" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/requirements') && 'nav-active'" title="需求管理"><span>📝</span></router-link>
          <router-link to="/hr-calendar" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/hr-calendar') && 'nav-active'" title="人力排期"><span>📅</span></router-link>
          <router-link to="/hr/employees" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/hr/') && 'nav-active'" title="人力管理"><span>👥</span></router-link>
        </template>
        <template v-else>
          <button
            class="nav-item w-full justify-between"
            :class="isWorkflowActive && 'nav-active'"
            @click="toggleMenu('workflow')"
          >
            <div class="flex items-center gap-3">
              <span>🔗</span>
              <span>项目工作流</span>
            </div>
            <span class="text-xs opacity-80">{{ openMenus.workflow ? '▲' : '▼' }}</span>
          </button>
          <div v-show="openMenus.workflow" class="ml-4 space-y-0.5 relative">
            <div class="absolute left-3 top-1 bottom-1 w-px bg-slate-600/40"></div>
            <router-link to="/projects" class="sub-nav-item flex items-center gap-2 !pl-6 relative" :class="isActive('/projects') && 'sub-nav-active'">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-indigo-400 bg-slate-900"></span>
              <span>📁</span> 项目管理
            </router-link>
            <router-link to="/requirements" class="sub-nav-item flex items-center gap-2 !pl-6 relative" :class="isActive('/requirements') && 'sub-nav-active'">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-purple-400 bg-slate-900"></span>
              <span>📝</span> 需求管理
            </router-link>
            <router-link to="/hr-calendar" class="sub-nav-item flex items-center gap-2 !pl-6 relative" :class="isActive('/hr-calendar') && 'sub-nav-active'">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-green-400 bg-slate-900"></span>
              <span>📅</span> 人力排期
            </router-link>
            <router-link to="/hr/employees" class="sub-nav-item flex items-center gap-2 !pl-6 relative" :class="isActive('/hr/') && 'sub-nav-active'">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-orange-400 bg-slate-900"></span>
              <span>👥</span> 人力管理
            </router-link>
          </div>
        </template>

        <!-- 质量中心 -->
        <div v-show="!sidebarCollapsed" class="mt-2 mb-1 px-3">
          <span class="text-[10px] font-semibold uppercase tracking-widest text-slate-500">质量中心</span>
        </div>
        <template v-if="sidebarCollapsed">
          <router-link to="/ai-testcase/generate" class="nav-item justify-center !px-0 !gap-0" :class="route.path === '/ai-testcase/generate' && 'nav-active'" title="用例生成"><span>🤖</span></router-link>
          <router-link to="/test-cases" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/test-cases') && 'nav-active'" title="用例管理"><span>📝</span></router-link>
          <router-link to="/api-automation/endpoints" class="nav-item justify-center !px-0 !gap-0" :class="route.path === '/api-automation/endpoints' && 'nav-active'" title="接口管理"><span>🔌</span></router-link>
          <router-link to="/defects" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/defects') && 'nav-active'" title="缺陷管理"><span>🐛</span></router-link>
          <router-link to="/efficiency/database" class="nav-item justify-center !px-0 !gap-0" :class="route.path === '/efficiency/database' && 'nav-active'" title="数据库工具"><span>🗄️</span></router-link>
        </template>
        <template v-else>
          <button
            class="nav-item w-full justify-between"
            :class="isTesterActive && 'nav-active'"
            @click="toggleMenu('tester')"
          >
            <div class="flex items-center gap-3">
              <span>🧪</span>
              <span>质量中心</span>
            </div>
            <span class="text-xs opacity-80">{{ openMenus.tester ? '▲' : '▼' }}</span>
          </button>
          <div v-show="openMenus.tester" class="ml-4 space-y-0.5 relative">
            <div class="absolute left-3 top-1 bottom-1 w-px bg-slate-600/40"></div>
            <!-- AI 测试用例 -->
            <div class="!pl-6 relative py-1">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-violet-400 bg-slate-900 top-3"></span>
              <span class="text-[10px] font-semibold text-slate-500 tracking-wide">AI 测试用例</span>
            </div>
            <router-link to="/ai-testcase/generate" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/ai-testcase/generate' && 'sub-nav-active'">
              <span>🤖</span> 用例生成
            </router-link>
            <router-link to="/ai-testcase/tasks" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="(route.path === '/ai-testcase/tasks' || route.path.startsWith('/ai-testcase/task/')) && 'sub-nav-active'">
              <span>📋</span> 生成任务
            </router-link>
            <!-- 测试用例 -->
            <div class="!pl-6 relative py-1 mt-1">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-emerald-400 bg-slate-900 top-3"></span>
              <span class="text-[10px] font-semibold text-slate-500 tracking-wide">测试用例</span>
            </div>
            <router-link to="/test-cases" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="(route.path === '/test-cases' || (route.path.startsWith('/test-cases/') && !route.path.startsWith('/test-cases/strategies') && !route.path.startsWith('/test-cases/reports'))) && 'sub-nav-active'">
              <span>📝</span> 用例管理
            </router-link>
            <router-link to="/test-cases/strategies" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path.startsWith('/test-cases/strategies') && 'sub-nav-active'">
              <span>🎯</span> 测试策略
            </router-link>
            <!-- 缺陷管理 (移入质量中心) -->
            <div class="!pl-6 relative py-1 mt-1">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-red-400 bg-slate-900 top-3"></span>
              <span class="text-[10px] font-semibold text-slate-500 tracking-wide">缺陷管理</span>
            </div>
            <router-link to="/defects" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="isActive('/defects') && 'sub-nav-active'">
              <span>🐛</span> 缺陷列表
            </router-link>
            <!-- 接口自动化 -->
            <div class="!pl-6 relative py-1 mt-1">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-cyan-400 bg-slate-900 top-3"></span>
              <span class="text-[10px] font-semibold text-slate-500 tracking-wide">接口自动化</span>
            </div>
            <router-link to="/api-automation/endpoints" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/api-automation/endpoints' && 'sub-nav-active'">
              <span>🔌</span> 接口管理
            </router-link>
            <router-link to="/api-automation/executions" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/api-automation/executions' && 'sub-nav-active'">
              <span>📊</span> 执行报告
            </router-link>
            <!-- 性能管理 -->
            <div class="!pl-6 relative py-1 mt-1">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-amber-400 bg-slate-900 top-3"></span>
              <span class="text-[10px] font-semibold text-slate-500 tracking-wide">性能管理</span>
            </div>
            <router-link to="/performance/scenarios" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/performance/scenarios' && 'sub-nav-active'">
              <span>⚡</span> 性能场景
            </router-link>
            <router-link to="/performance/reports" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/performance/reports' && 'sub-nav-active'">
              <span>📈</span> 执行报告
            </router-link>
            <!-- 效率提升 -->
            <div class="!pl-6 relative py-1 mt-1">
              <span class="absolute left-[7px] w-2 h-2 rounded-full border-2 border-rose-400 bg-slate-900 top-3"></span>
              <span class="text-[10px] font-semibold text-slate-500 tracking-wide">效率提升</span>
            </div>
            <router-link to="/efficiency/database" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/efficiency/database' && 'sub-nav-active'">
              <span>🗄️</span> 数据库工具
            </router-link>
            <router-link to="/efficiency/server" class="sub-nav-item flex items-center gap-2 !pl-10"
              :class="route.path === '/efficiency/server' && 'sub-nav-active'">
              <span>🖥️</span> 服务器工具
            </router-link>
          </div>
        </template>

        <!-- 配置中心 -->
        <template v-if="sidebarCollapsed">
          <router-link to="/config-center/ai" class="nav-item justify-center !px-0 !gap-0" :class="isActive('/config-center') && 'nav-active'" title="配置中心"><span>⚙️</span></router-link>
        </template>
        <template v-else>
          <button
            class="nav-item w-full justify-between"
            :class="isActive('/config-center') && 'nav-active'"
            @click="toggleMenu('config')"
          >
            <div class="flex items-center gap-3">
              <span>⚙️</span>
              <span>配置中心</span>
            </div>
            <span class="text-xs opacity-80">{{ openMenus.config ? '▲' : '▼' }}</span>
          </button>
          <div v-show="openMenus.config" class="ml-8 space-y-1">
            <router-link to="/config-center/ai" class="sub-nav-item" :class="route.path === '/config-center/ai' && 'sub-nav-active'">
              AI 模型配置
            </router-link>
            <router-link to="/config-center/role-configs" class="sub-nav-item" :class="route.path === '/config-center/role-configs' && 'sub-nav-active'">
              角色配置
            </router-link>
            <router-link to="/config-center/prompts" class="sub-nav-item" :class="route.path === '/config-center/prompts' && 'sub-nav-active'">
              提示词配置
            </router-link>
            <router-link to="/config-center/notifications" class="sub-nav-item" :class="route.path === '/config-center/notifications' && 'sub-nav-active'">
              消息提醒
            </router-link>
            <router-link to="/config-center/behavior" class="sub-nav-item" :class="route.path === '/config-center/behavior' && 'sub-nav-active'">
              生成行为配置
            </router-link>
            <router-link to="/config-center/skills" class="sub-nav-item" :class="route.path === '/config-center/skills' && 'sub-nav-active'">
              QA Skills 中心
            </router-link>
          </div>
        </template>
      </nav>

      <!-- User Area at bottom of sidebar -->
      <div class="bg-slate-950/30 border-t border-slate-800" :class="sidebarCollapsed ? 'p-2' : 'p-4'">
        <div class="flex items-center gap-3" :class="sidebarCollapsed ? 'justify-center py-2' : 'px-2 py-2'">
          <div class="w-9 h-9 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-500 text-white flex items-center justify-center text-xs font-bold shadow-inner shrink-0" :title="sidebarCollapsed ? (userStore.username || '管理员') : ''">
            {{ userAvatar }}
          </div>
          <div v-show="!sidebarCollapsed" class="flex-1 min-w-0">
            <p class="text-sm font-medium text-white truncate">{{ userStore.username || '管理员' }}</p>
            <p class="text-xs text-slate-400 truncate">{{ userStore.username ? userStore.username + '@system' : 'admin@system' }}</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
      <!-- Navbar -->
      <header class="h-14 bg-white/80 backdrop-blur-md border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-10">
        <div class="flex items-center gap-3">
          <button
            class="p-2 rounded-lg hover:bg-gray-100 text-slate-500 transition-colors"
            @click="sidebarCollapsed = !sidebarCollapsed"
            :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <nav class="flex items-center text-sm text-slate-500">
            <router-link to="/dashboard" class="hover:text-indigo-600 transition-colors">首页</router-link>
            <template v-for="(crumb, idx) in breadcrumbs" :key="idx">
              <span class="mx-1.5 text-slate-300">/</span>
              <span v-if="idx === breadcrumbs.length - 1" class="text-slate-800 font-medium">{{ crumb.label }}</span>
              <router-link v-else-if="crumb.path" :to="crumb.path" class="hover:text-indigo-600 transition-colors">{{ crumb.label }}</router-link>
              <span v-else class="text-slate-500">{{ crumb.label }}</span>
            </template>
          </nav>
        </div>
        
        <div class="flex items-center gap-2">
          <div class="relative" v-if="!searchActive">
            <button @click="searchActive = true" class="p-2 rounded-lg hover:bg-gray-100 text-slate-400 transition-colors" title="全局搜索">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </button>
          </div>
          <div v-else class="flex items-center bg-gray-100 rounded-lg px-3 py-1.5 gap-2 w-64 transition-all">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <input
              ref="searchInputRef"
              v-model="searchQuery"
              placeholder="搜索项目、需求、缺陷..."
              class="bg-transparent border-none outline-none text-sm text-slate-700 w-full placeholder-slate-400"
              @blur="searchActive = false"
              @keyup.escape="searchActive = false"
            />
          </div>
          <button class="p-2 rounded-lg hover:bg-gray-100 text-slate-400 transition-colors relative" title="通知">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <el-button @click="handleLogout" text size="small" class="hover:bg-red-50 hover:text-red-600 !rounded-lg text-slate-400 transition-colors ml-1">
            <span class="mr-1">🚪</span> 退出
          </el-button>
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 overflow-x-hidden overflow-y-auto bg-slate-50 p-8">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
      <footer class="h-10 border-t border-gray-200 bg-white text-gray-400 text-xs flex items-center justify-center gap-2">
        <span>🌙 月亮邮寄员项目管理平台</span>
        <span class="text-gray-300">|</span>
        <span>v1.0.0</span>
        <span class="text-gray-300">|</span>
        <span>&copy; 2026 ALex. All rights reserved.</span>
      </footer>
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const userStore = useUserStore()
const sidebarOpen = ref(true)
const sidebarCollapsed = ref(false)
const searchActive = ref(false)
const searchQuery = ref('')
const searchInputRef = ref<HTMLInputElement | null>(null)

watch(searchActive, (v) => {
  if (v) nextTick(() => searchInputRef.value?.focus())
})

const _isTesterPath = (p: string) => p.startsWith('/ai-testcase') || p.startsWith('/test-cases') || p.startsWith('/api-automation') || p.startsWith('/performance') || p.startsWith('/efficiency') || p.startsWith('/defects')

const openMenus = reactive({
  workflow: route.path.startsWith('/projects') || route.path.startsWith('/requirements') || route.path.startsWith('/hr-calendar') || route.path.startsWith('/hr/'),
  tester: _isTesterPath(route.path),
  config: route.path.startsWith('/config-center'),
})

const isWorkflowActive = computed(() =>
  route.path.startsWith('/projects') || route.path.startsWith('/requirements') || route.path.startsWith('/hr-calendar') || route.path.startsWith('/hr/')
)

const isTesterActive = computed(() => _isTesterPath(route.path))

watch(
  () => route.path,
  (path) => {
    if (path.startsWith('/projects') || path.startsWith('/requirements') || path.startsWith('/hr-calendar') || path.startsWith('/hr/')) openMenus.workflow = true
    if (_isTesterPath(path)) openMenus.tester = true
    if (path.startsWith('/config-center')) openMenus.config = true
  }
)

const isActive = (prefix: string) => route.path.startsWith(prefix)

const toggleMenu = (key: keyof typeof openMenus) => {
  openMenus[key] = !openMenus[key]
}

const breadcrumbMap: Record<string, { label: string; path?: string }[]> = {
  '/dashboard': [{ label: '数据看板' }],
  '/projects': [{ label: '项目工作流' }, { label: '项目管理' }],
  '/requirements': [{ label: '项目工作流' }, { label: '需求管理' }],
  '/hr-calendar': [{ label: '项目工作流' }, { label: '人力排期' }],
  '/hr/employees': [{ label: '项目工作流' }, { label: '人力管理' }],
  '/ai-testcase/generate': [{ label: '质量中心' }, { label: '用例生成' }],
  '/ai-testcase/tasks': [{ label: '质量中心' }, { label: '生成任务' }],
  '/test-cases': [{ label: '质量中心' }, { label: '用例管理' }],
  '/test-cases/strategies': [{ label: '质量中心' }, { label: '测试策略' }],
  '/api-automation/endpoints': [{ label: '质量中心' }, { label: '接口管理' }],
  '/api-automation/executions': [{ label: '质量中心' }, { label: '执行报告' }],
  '/performance/scenarios': [{ label: '质量中心' }, { label: '性能场景' }],
  '/performance/reports': [{ label: '质量中心' }, { label: '性能报告' }],
  '/efficiency/database': [{ label: '质量中心' }, { label: '数据库工具' }],
  '/efficiency/server': [{ label: '质量中心' }, { label: '服务器工具' }],
  '/defects': [{ label: '质量中心' }, { label: '缺陷管理' }],
  '/config-center/ai': [{ label: '配置中心' }, { label: 'AI 模型配置' }],
  '/config-center/role-configs': [{ label: '配置中心' }, { label: '角色配置' }],
  '/config-center/prompts': [{ label: '配置中心' }, { label: '提示词配置' }],
  '/config-center/notifications': [{ label: '配置中心' }, { label: '消息提醒' }],
  '/config-center/behavior': [{ label: '配置中心' }, { label: '生成行为配置' }],
  '/config-center/skills': [{ label: '配置中心' }, { label: 'QA Skills 中心' }],
}

const breadcrumbs = computed(() => {
  const path = route.path
  if (breadcrumbMap[path]) return breadcrumbMap[path]
  if (path.startsWith('/projects/')) return [{ label: '项目工作流' }, { label: '项目管理', path: '/projects' }, { label: '项目详情' }]
  if (path.startsWith('/requirements/')) return [{ label: '项目工作流' }, { label: '需求管理', path: '/requirements' }, { label: '需求详情' }]
  if (path.startsWith('/defects/')) return [{ label: '质量中心' }, { label: '缺陷管理', path: '/defects' }, { label: '缺陷详情' }]
  if (path.startsWith('/test-cases/')) return [{ label: '质量中心' }, { label: '用例管理', path: '/test-cases' }, { label: '详情' }]
  if (path.startsWith('/ai-testcase/task/')) return [{ label: '质量中心' }, { label: '生成任务', path: '/ai-testcase/tasks' }, { label: '任务详情' }]
  return []
})

const userAvatar = computed(() => {
  const name = userStore.username || '管理员'
  return name.slice(0, 2).toUpperCase()
})

const handleLogout = () => {
  userStore.logout()
}
</script>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 1rem;
  border-radius: 0.75rem;
  transition: all 0.2s;
  cursor: pointer;
  font-size: 0.9rem;
}
.nav-item:hover {
  background: rgb(51 65 85);
  color: white;
}
.nav-active {
  background: rgb(79 70 229) !important;
  color: white !important;
  font-weight: 500;
  box-shadow: 0 4px 6px -1px rgb(79 70 229 / 0.2);
}
.sub-nav-item {
  display: block;
  padding: 0.4rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.82rem;
  transition: all 0.2s;
}
.sub-nav-item:hover {
  background: rgb(51 65 85);
  color: white;
}
.sub-nav-active {
  background: rgb(51 65 85) !important;
  color: white !important;
}
.fade-transform-enter-active,
.fade-transform-leave-active {
  transition: all 0.3s ease;
}
.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}
.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(10px);
}
</style>
