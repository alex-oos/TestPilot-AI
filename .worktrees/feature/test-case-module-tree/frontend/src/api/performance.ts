import request from '../utils/request'

export const getPerfScenarios = (params?: any) => request.get('/performance/scenarios', { params })
export const createPerfScenario = (data: any) => request.post('/performance/scenarios', data)
export const getPerfScenario = (id: number) => request.get(`/performance/scenarios/${id}`)
export const updatePerfScenario = (id: number, data: any) => request.put(`/performance/scenarios/${id}`, data)
export const deletePerfScenario = (id: number) => request.delete(`/performance/scenarios/${id}`)

export const getPerfScripts = (scenarioId: number) => request.get(`/performance/scenarios/${scenarioId}/scripts`)
export const createPerfScript = (scenarioId: number, data: any) => request.post(`/performance/scenarios/${scenarioId}/scripts`, data)

export const getPerfExecutions = (params?: any) => request.get('/performance/executions', { params })
export const getPerfBaselines = (params?: any) => request.get('/performance/baselines', { params })
export const createPerfBaseline = (data: any) => request.post('/performance/baselines', data)
