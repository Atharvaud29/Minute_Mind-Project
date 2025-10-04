import { http } from './http'

export const fetchTasks = async () => {
  const { data } = await http.get('/tasks')
  return data
}

export const updateTask = async (id, payload) => {
  const { data } = await http.patch(`/tasks/${id}`, payload)
  return data
}

export const createTask = async (payload) => {
  const { data } = await http.post('/tasks', payload)
  return data
}


