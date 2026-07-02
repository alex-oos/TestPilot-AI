import request from '../utils/request'

export const getApiEndpoints = (params?: any) => request.get('/api-automation/endpoints', { params })
export const createApiEndpoint = (data: any) => request.post('/api-automation/endpoints', data)
export const updateApiEndpoint = (id: number, data: any) => request.put(`/api-automation/endpoints/${id}`, data)
export const deleteApiEndpoint = (id: number) => request.delete(`/api-automation/endpoints/${id}`)

export const getApiEnvironments = (params?: any) => request.get('/api-automation/environments', { params })
export const createApiEnvironment = (data: any) => request.post('/api-automation/environments', data)

export const getApiTestCases = (params?: any) => request.get('/api-automation/test-cases', { params })
export const createApiTestCase = (data: any) => request.post('/api-automation/test-cases', data)

export const getApiExecutions = (params?: any) => request.get('/api-automation/executions', { params })
export const createApiExecution = (data: any) => request.post('/api-automation/executions', data)
