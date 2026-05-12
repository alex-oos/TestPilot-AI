import request from '../utils/request'

export const getEmployees = (params?: any) => request.get('/hr/employees', { params })
export const createEmployee = (data: any) => request.post('/hr/employees', data)
export const updateEmployee = (id: number, data: any) => request.put(`/hr/employees/${id}`, data)
export const deleteEmployee = (id: number) => request.delete(`/hr/employees/${id}`)

export const getTeams = () => request.get('/hr/teams')
export const createTeam = (data: any) => request.post('/hr/teams', data)

export const getSchedules = (params?: any) => request.get('/hr/schedules', { params })
export const createSchedule = (data: any) => request.post('/hr/schedules', data)

export const getLeaves = (params?: any) => request.get('/hr/leaves', { params })
export const createLeave = (data: any) => request.post('/hr/leaves', data)

export const getEmployeeSkills = (empId: number) => request.get(`/hr/employees/${empId}/skills`)
export const addEmployeeSkill = (empId: number, data: any) => request.post(`/hr/employees/${empId}/skills`, data)

export const getSyncPlatforms = () => request.get('/hr/sync/platforms')
export const fetchPlatformUsers = (data: any) => request.post('/hr/sync/fetch', data)
export const importPlatformUsers = (data: any) => request.post('/hr/sync/import', data)
export const enableLogin = (empId: number) => request.post(`/hr/sync/enable-login/${empId}`)
export const disableLogin = (empId: number) => request.post(`/hr/sync/disable-login/${empId}`)
