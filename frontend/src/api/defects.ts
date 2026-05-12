import request from '../utils/request'

export const getDefects = (params?: any) => request.get('/defects', { params })
export const createDefect = (data: any) => request.post('/defects', data)
export const getDefect = (id: number) => request.get(`/defects/${id}`)
export const updateDefect = (id: number, data: any) => request.put(`/defects/${id}`, data)
export const deleteDefect = (id: number) => request.delete(`/defects/${id}`)
export const getDefectComments = (id: number) => request.get(`/defects/${id}/comments`)
export const addDefectComment = (id: number, data: any) => request.post(`/defects/${id}/comments`, data)
export const getDefectHistory = (id: number) => request.get(`/defects/${id}/history`)
export const getDefectStats = (params?: any) => request.get('/defects/stats/summary', { params })
