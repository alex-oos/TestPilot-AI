import request from '../utils/request'

export const getProjects = (params?: { page?: number; page_size?: number; status?: string }) =>
  request.get('/projects', { params })
export const createProject = (data: any) => request.post('/projects', data)
export const getProject = (id: number) => request.get(`/projects/${id}`)
export const updateProject = (id: number, data: any) => request.put(`/projects/${id}`, data)
export const deleteProject = (id: number) => request.delete(`/projects/${id}`)
export const getProjectVersions = (id: number) => request.get(`/projects/${id}/versions`)
export const createProjectVersion = (id: number, data: any) => request.post(`/projects/${id}/versions`, data)
export const getProjectMembers = (id: number) => request.get(`/projects/${id}/members`)
export const addProjectMember = (id: number, data: any) => request.post(`/projects/${id}/members`, data)
