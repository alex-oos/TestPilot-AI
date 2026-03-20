import axios from 'axios'

const normalizeBase = (base: string) => (base || '').replace(/\/$/, '')

export const DEFAULT_API_BASE = '/api'
export const DIRECT_BACKEND_API_BASE = normalizeBase(
  import.meta.env.VITE_DIRECT_BACKEND_API_BASE || 'http://127.0.0.1:8000/api'
)
export const API_BASE_URL = normalizeBase(import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE)

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const payload = response?.data
    if (
      payload &&
      typeof payload === 'object' &&
      Object.prototype.hasOwnProperty.call(payload, 'code') &&
      payload.code !== 0
    ) {
      const error: any = new Error(payload.msg || '请求失败')
      error.response = response
      error.data = payload
      return Promise.reject(error)
    }
    return response
  },
  (error) => {
    const message =
      error?.response?.data?.msg ||
      error?.response?.data?.detail ||
      error?.message ||
      '网络请求失败'
    if (!error.message) {
      error.message = message
    }
    return Promise.reject(error)
  }
)

export default request
