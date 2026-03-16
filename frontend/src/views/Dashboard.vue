<template>
  <div class="space-y-6">
    <!-- Welcome Section -->
    <div class="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-8 text-white shadow-lg relative overflow-hidden">
      <div class="relative z-10">
        <h1 class="text-3xl font-bold mb-2">欢迎回来，管理员！ 👋</h1>
        <p class="text-indigo-100 max-w-xl text-lg">这是您测试环境今天的重点数据。您的团队本周共生成 124 个新测试用例。</p>
      </div>
      <!-- Decorative rings -->
      <div class="absolute right-0 top-0 w-64 h-64 bg-white opacity-10 rounded-full blur-3xl transform translate-x-1/2 -translate-y-1/2"></div>
      <div class="absolute right-40 bottom-0 w-48 h-48 bg-white opacity-10 rounded-full blur-2xl transform translate-y-1/2"></div>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      
      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-blue-50 text-blue-600 rounded-xl">
            <span class="text-xl">📄</span>
          </div>
          <span class="text-sm font-medium text-green-500 bg-green-50 px-2 py-1 rounded-md">+12%</span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">已解析文档总量</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">1,248</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
            <span class="text-xl">⚡</span>
          </div>
          <span class="text-sm font-medium text-green-500 bg-green-50 px-2 py-1 rounded-md">+24%</span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">已生成用例总数</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">8,459</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-green-50 text-green-600 rounded-xl">
            <span class="text-xl">✔️</span>
          </div>
          <span class="text-sm font-medium text-slate-400 bg-slate-50 px-2 py-1 rounded-md">--</span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">测试用例覆盖率</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">92.4%</p>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="p-3 bg-orange-50 text-orange-600 rounded-xl">
            <span class="text-xl">⏱️</span>
          </div>
          <span class="text-sm font-medium text-red-500 bg-red-50 px-2 py-1 rounded-md">-5%</span>
        </div>
        <div>
          <h3 class="text-slate-500 text-sm font-medium">平均生成耗时</h3>
          <p class="text-3xl font-bold text-slate-800 mt-1">1.2s</p>
        </div>
      </div>

    </div>

    <!-- Charts / Activity Mock -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <div class="lg:col-span-2 bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-6">用例生成动态</h3>
        <div class="h-64 flex items-end justify-between gap-2 px-4 pb-4 border-b border-slate-100">
          <!-- Mock Chart Bars -->
          <div class="w-full bg-slate-100 rounded-t-sm h-[40%] hover:bg-indigo-100 transition-colors relative group"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">40</div></div>
          <div class="w-full bg-slate-100 rounded-t-sm h-[65%] hover:bg-indigo-100 transition-colors relative group"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">65</div></div>
          <div class="w-full bg-slate-100 rounded-t-sm h-[80%] hover:bg-indigo-100 transition-colors relative group"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">80</div></div>
          <div class="w-full bg-indigo-500 rounded-t-sm h-[100%] hover:bg-indigo-600 transition-colors relative group shadow-[0_0_15px_rgba(99,102,241,0.5)]"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">124</div></div>
          <div class="w-full bg-slate-100 rounded-t-sm h-[45%] hover:bg-indigo-100 transition-colors relative group"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">45</div></div>
          <div class="w-full bg-slate-100 rounded-t-sm h-[70%] hover:bg-indigo-100 transition-colors relative group"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">70</div></div>
          <div class="w-full bg-slate-100 rounded-t-sm h-[55%] hover:bg-indigo-100 transition-colors relative group"><div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">55</div></div>
        </div>
        <div class="flex justify-between text-xs text-slate-400 mt-2 px-4">
          <span>周一</span>
          <span>周二</span>
          <span>周三</span>
          <span class="text-indigo-600 font-medium">周四</span>
          <span>周五</span>
          <span>周六</span>
          <span>周日</span>
        </div>
      </div>

      <div class="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm">
        <h3 class="text-lg font-semibold text-slate-800 mb-6">最近需求来源文档</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-blue-50 text-blue-500 flex items-center justify-center text-lg">📄</div>
              <div>
                <p class="text-sm font-medium text-slate-700">飞书文档</p>
                <p class="text-xs text-slate-400">540 个用例</p>
              </div>
            </div>
            <span class="text-sm font-semibold text-slate-600">45%</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-indigo-50 text-indigo-500 flex items-center justify-center text-lg">💬</div>
              <div>
                <p class="text-sm font-medium text-slate-700">钉钉文档</p>
                <p class="text-xs text-slate-400">420 个用例</p>
              </div>
            </div>
            <span class="text-sm font-semibold text-slate-600">35%</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-emerald-50 text-emerald-500 flex items-center justify-center text-lg">📁</div>
              <div>
                <p class="text-sm font-medium text-slate-700">本地上传文件</p>
                <p class="text-xs text-slate-400">288 个用例</p>
              </div>
            </div>
            <span class="text-sm font-semibold text-slate-600">20%</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
// Dashboard logic
</script>
