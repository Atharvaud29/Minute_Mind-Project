import { http } from './http'

export const fetchMeetings = async () => {
  const { data } = await http.get('/meetings')
  return data
}

export const createMeeting = async (payload) => {
  const { data } = await http.post('/meetings', payload)
  return data
}

export const uploadAndTranscribe = async (file) => {
  const form = new FormData()
  form.append('audio', file)
  const { data } = await http.post('/transcribe', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}

export const generateWithPhi3 = async ({ prompt, max_tokens, temperature, top_p }) => {
  const { data } = await http.post('/phi3/generate', { prompt, max_tokens, temperature, top_p })
  return data
}


