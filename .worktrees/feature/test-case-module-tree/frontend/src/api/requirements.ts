import request from '../utils/request'

export const getRequirements = (params?: any) => request.get('/requirements', { params })
export const createRequirement = (data: any) => request.post('/requirements', data)
export const getRequirement = (id: number) => request.get(`/requirements/${id}`)
export const updateRequirement = (id: number, data: any) => request.put(`/requirements/${id}`, data)
export const deleteRequirement = (id: number) => request.delete(`/requirements/${id}`)
export const getRequirementTraces = (id: number) => request.get(`/requirements/${id}/traces`)
