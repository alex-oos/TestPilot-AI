import request from '../utils/request'

export async function getRoleConfigs() {
  return request.get('/config-center/role-configs/list')
}

export async function createRoleConfig(payload: any) {
  return request.post('/config-center/role-configs/create', payload)
}

export async function editRoleConfig(payload: any) {
  return request.put('/config-center/role-configs/edit', payload)
}

export async function deleteRoleConfig(configId: string) {
  return request.delete(`/config-center/role-configs/delete/${encodeURIComponent(configId)}`)
}
