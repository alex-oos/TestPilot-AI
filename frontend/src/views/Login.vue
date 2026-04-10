<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-indigo-50 to-blue-100 relative overflow-hidden">
    <!-- Decorative background elements -->
    <div class="absolute top-[-10%] left-[-10%] w-96 h-96 bg-purple-300 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob"></div>
    <div class="absolute top-[-10%] right-[-10%] w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob animation-delay-2000"></div>
    <div class="absolute bottom-[-20%] left-[20%] w-96 h-96 bg-pink-300 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-blob animation-delay-4000"></div>

    <div class="flex-1 flex items-center justify-center">
      <div class="z-10 bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl overflow-hidden flex max-w-4xl w-full border border-white/40">
      
      <!-- Left side: Illustration / Details -->
      <div class="w-1/2 p-12 bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex flex-col justify-center relative hidden md:flex">
        <div class="absolute inset-0 bg-black/10"></div>
        <div class="relative z-10">
          <h2 class="text-4xl font-bold mb-6 font-display tracking-tight">秒级生成测试用例。</h2>
          <p class="text-indigo-100 text-lg mb-8 leading-relaxed">
            利用 AI 的力量，瞬间将您的产品需求转化为全面的测试用例。轻松连接飞书和钉钉文档，或直接本地上传。
          </p>
          <div class="flex items-center gap-4 text-sm font-medium text-indigo-200">
            <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-green-400"></span> 快速</div>
            <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-green-400"></span> 准确</div>
            <div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-green-400"></span> 一体化</div>
          </div>
        </div>
      </div>

        <!-- Right side: Login Form -->
        <div class="w-full md:w-1/2 p-12 flex flex-col justify-center">
        <div class="mb-10 text-center md:text-left">
          <h1 class="text-3xl font-bold text-gray-900 mb-2">欢迎回来</h1>
          <p class="text-gray-500">登录 AI 测试平台</p>
        </div>

        <el-form :model="loginForm" @submit.prevent="handleLogin" class="space-y-6" size="large">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">用户名</label>
            <el-input 
              v-model="loginForm.username" 
              placeholder="请输入用户名 (admin)" 
              class="!rounded-xl select-none"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">密码</label>
            <el-input 
              v-model="loginForm.password" 
              type="password" 
              placeholder="请输入密码 (123456)" 
              show-password
              class="!rounded-xl select-none"
            />
          </div>

          <div class="flex items-center justify-between mb-6">
            <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
            <a href="#" class="text-sm font-medium text-indigo-600 hover:text-indigo-500 transition-colors">忘记密码？</a>
          </div>

          <el-button 
            type="primary" 
            class="w-full !rounded-xl !h-12 !text-base font-semibold shadow-lg shadow-indigo-200 hover:shadow-indigo-300 transition-all" 
            @click="handleLogin" 
            :loading="loading"
            color="#4f46e5"
          >
            登录
          </el-button>
        </el-form>
        </div>
      </div>
    </div>

    <footer class="h-10 text-gray-600 text-sm flex items-center justify-center z-10">
      2026 ALex 版权所有
    </footer>
    </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { loginByFallback } from '../api/login'

const router = useRouter()
const loading = ref(false)

const loginForm = reactive({
  username: 'admin',
  password: '123456',
  remember: false
})

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  
  loading.value = true
  try {
    let response
    response = await loginByFallback(loginForm.username, loginForm.password)

    const payload = response.data?.data || {}
    if (!payload.token) {
      ElMessage.error(response.data?.msg || '登录失败：未获取到 token')
      return
    }

    localStorage.setItem('token', payload.token)
    localStorage.setItem('username', payload.user || loginForm.username)
    if (payload.user_id) {
      localStorage.setItem('user_id', String(payload.user_id))
    }
    ElMessage.success('登录成功！')
    router.push('/tasks')
  } catch (error: any) {
    if (error?.response?.status === 502 || !error?.response) {
      ElMessage.error('登录失败：后端服务不可达，请检查后端是否已启动（127.0.0.1:8001）')
      return
    }
    ElMessage.error(error.response?.data?.msg || error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Keyframes for blob animation are managed in tailwind config theoretically, but we can do inline or add to css if needed. We'll rely on static mix-blend for now or inject raw animation below */
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}
.animate-blob {
  animation: blob 7s infinite;
}
.animation-delay-2000 {
  animation-delay: 2s;
}
.animation-delay-4000 {
  animation-delay: 4s;
}
:deep(.el-input__wrapper) {
  border-radius: 0.75rem;
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  padding: 8px 15px;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #4f46e5 inset;
}
</style>
