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
    if (error?.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('user_id')
      window.location.href = '/login'
      return Promise.reject(error)
    }
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

/** 从标准 { code, data, msg } envelope 中取出业务数据；Blob 等原始响应原样返回。 */
export function unwrapApiData<T = unknown>(response: { data?: unknown }): T {
  const payload = response?.data
  if (payload instanceof Blob || payload instanceof ArrayBuffer) {
    return payload as T
  }
  if (
    payload &&
    typeof payload === 'object' &&
    Object.prototype.hasOwnProperty.call(payload, 'code') &&
    Object.prototype.hasOwnProperty.call(payload, 'data')
  ) {
    return (payload as { data: T }).data
  }
  return payload as T
}

export default request
