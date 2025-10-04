import { http } from './http'

export const fetchConflicts = async () => {
  const { data } = await http.get('/conflicts')
  return data
}

export const updateConflict = async (id, payload) => {
  const { data } = await http.patch(`/conflicts/${id}`, payload)
  return data
}

export const createConflict = async (payload) => {
  const { data } = await http.post('/conflicts', payload)
  return data
}


