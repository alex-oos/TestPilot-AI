import request from '../utils/request'

// Test Cases
export const getTestCases = (params?: any) => request.get('/test-cases', { params })
export const getTestCase = (id: number) => request.get(`/test-cases/${id}`)
export const createTestCase = (data: any) => request.post('/test-cases', data)
export const updateTestCase = (id: number, data: any) => request.put(`/test-cases/${id}`, data)
export const deleteTestCase = (id: number) => request.delete(`/test-cases/${id}`)
export const batchAdoptTestCases = (data: any) => request.post('/test-cases/batch-adopt', data)
export const getTestCaseModules = (params?: any) => request.get('/test-cases/modules', { params })
export const getTestCaseStats = (params?: any) => request.get('/test-cases/stats/summary', { params })

// Test Executions
export const getTestExecutions = (params?: any) => request.get('/test-executions', { params })
export const getTestExecution = (id: number) => request.get(`/test-executions/${id}`)
export const createTestExecution = (data: any) => request.post('/test-executions', data)
export const updateTestExecution = (id: number, data: any) => request.put(`/test-executions/${id}`, data)
export const deleteTestExecution = (id: number) => request.delete(`/test-executions/${id}`)
export const startTestExecution = (id: number) => request.put(`/test-executions/${id}/start`)
export const abortTestExecution = (id: number) => request.put(`/test-executions/${id}/abort`)
export const updateExecutionCases = (executionId: number, data: any) =>
  request.put(`/test-executions/${executionId}/cases`, data)
export const updateExecutionResult = (executionId: number, resultId: number, data: any) =>
  request.put(`/test-executions/${executionId}/results/${resultId}`, data)

// Test Reports
export const getTestReports = (params?: any) => request.get('/test-reports', { params })
export const getTestReport = (id: number) => request.get(`/test-reports/${id}`)
export const generateTestReport = (executionId: number) =>
  request.post(`/test-executions/${executionId}/report`)
