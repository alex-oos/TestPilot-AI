import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '../router'

export interface EmployeeInfo {
  id: number
  name: string
  role: string
  position: string
  department: string
  level: string
  email: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const userId = ref(localStorage.getItem('user_id') || '')
  const employee = ref<EmployeeInfo | null>(
    JSON.parse(localStorage.getItem('employee_info') || 'null')
  )

  const isLoggedIn = computed(() => !!token.value)
  const employeeId = computed(() => employee.value?.id ?? null)
  const employeeRole = computed(() => employee.value?.role ?? '')

  function setUser(data: { token: string; user: string; user_id?: string | number }) {
    token.value = data.token
    username.value = data.user
    userId.value = String(data.user_id || '')
    localStorage.setItem('token', data.token)
    localStorage.setItem('username', data.user)
    if (data.user_id) localStorage.setItem('user_id', String(data.user_id))
  }

  function setEmployee(emp: EmployeeInfo | null) {
    employee.value = emp
    if (emp) {
      localStorage.setItem('employee_info', JSON.stringify(emp))
    } else {
      localStorage.removeItem('employee_info')
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    userId.value = ''
    employee.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('user_id')
    localStorage.removeItem('employee_info')
    router.push('/login')
  }

  return { token, username, userId, employee, employeeId, employeeRole, isLoggedIn, setUser, setEmployee, logout }
})
