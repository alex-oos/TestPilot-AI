<template>
  <div class="min-h-screen bg-gray-50 flex">
    
    <!-- Sidebar -->
    <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col transition-all duration-300 relative z-20 shadow-xl">
      <!-- Logo Area -->
      <div class="h-16 flex items-center px-6 bg-slate-950/50 border-b border-slate-800">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-indigo-500 shadow-lg shadow-indigo-500/30 flex items-center justify-center text-white font-bold select-none">
            AI
          </div>
          <span class="text-lg font-bold text-white tracking-tight">AI 测试平台</span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        <router-link 
          to="/dashboard" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200"
          :class="route.path === '/dashboard' ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 font-medium' : 'hover:bg-slate-800 hover:text-white'"
        >
          <span class="i-mdi-view-dashboard text-xl opacity-80 decoration-slate-400">📊</span>
          <span>数据看板</span>
        </router-link>

        <router-link 
          to="/generate" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200"
          :class="route.path === '/generate' ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 font-medium' : 'hover:bg-slate-800 hover:text-white'"
        >
          <span class="i-mdi-robot-outline text-xl opacity-80">🤖</span>
          <span>用例生成</span>
        </router-link>

        <router-link 
          to="/tasks" 
          class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200"
          :class="(route.path === '/tasks' || route.path.startsWith('/task/')) ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 font-medium' : 'hover:bg-slate-800 hover:text-white'"
        >
          <span class="i-mdi-format-list-bulleted text-xl opacity-80 decoration-slate-400">📋</span>
          <span>任务列表</span>
        </router-link>
      </nav>

      <!-- User Area at bottom of sidebar -->
      <div class="p-4 bg-slate-950/30 border-t border-slate-800">
        <div class="flex items-center gap-3 px-2 py-2">
          <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-500 text-white flex items-center justify-center text-sm font-bold shadow-inner">
            AD
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-white truncate">超级管理员</p>
            <p class="text-xs text-slate-400 truncate">admin@system</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
      <!-- Navbar -->
      <header class="h-16 bg-white/80 backdrop-blur-md border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-10">
        <div class="flex items-center">
          <h2 class="text-lg font-semibold text-slate-800">{{ pageTitle }}</h2>
        </div>
        
        <div class="flex items-center gap-4">
          <el-button @click="handleLogout" text class="hover:bg-red-50 hover:text-red-600 !rounded-lg text-slate-500 transition-colors">
            <span class="mr-1">🚪</span> 退出登录
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
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const pageTitle = computed(() => {
  switch (true) {
    case route.path === '/tasks': return '任务列表'
    case route.path === '/dashboard': return '数据看板'
    case route.path === '/generate': return '智能用例生成'
    case route.path.startsWith('/task/'): return '任务详情'
    default: return ''
  }
})

const handleLogout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
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
