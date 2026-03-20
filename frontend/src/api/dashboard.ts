import request from '../utils/request'

export async function getDashboardOverview() {
  return request.get('/dashboard/overview')
}
