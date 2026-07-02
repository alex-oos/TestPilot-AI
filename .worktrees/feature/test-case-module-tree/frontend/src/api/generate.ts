import request from '../utils/request'

export async function createTask(formData: FormData) {
  return request.post('/tasks/create', formData)
}
