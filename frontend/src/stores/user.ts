import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '../router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const userId = ref(localStorage.getItem('user_id') || '')

  const isLoggedIn = computed(() => !!token.value)

  function setUser(data: { token: string; user: string; user_id?: string | number }) {
    token.value = data.token
    username.value = data.user
    userId.value = String(data.user_id || '')
    localStorage.setItem('token', data.token)
    localStorage.setItem('username', data.user)
    if (data.user_id) localStorage.setItem('user_id', String(data.user_id))
  }

  function logout() {
    token.value = ''
    username.value = ''
    userId.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('user_id')
    router.push('/login')
  }

  return { token, username, userId, isLoggedIn, setUser, logout }
})
