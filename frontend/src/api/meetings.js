// import { http } from './http'

// export const fetchMeetings = async () => {
//   const { data } = await http.get('/meetings')
//   return data
// }

// export const createMeeting = async (payload) => {
//   const { data } = await http.post('/meetings', payload)
//   return data
// }

// export const uploadAndTranscribe = async (file) => {
//   const form = new FormData()
//   form.append('audio', file)
//   // Calls unified endpoint that transcribes first, then summarizes
//   const { data } = await http.post(
//     '/transcribe_and_summarize',
//     form,
//     {
//       headers: { 'Content-Type': 'multipart/form-data' },
//       // Disable timeout for potentially long inference jobs (0 = no timeout)
//       timeout: 0,
//     }
//   )
//   return data
// }

// // Fallback: client-side manual summary generation if needed (unused with unified endpoint)
// export const getFullAnalysis = async (transcript) => {
//   const instruction = 'You are a helpful assistant that writes concise, structured meeting summaries. Summarize the following meeting transcript into key points, decisions, action items (with owners and deadlines if mentioned), and risks.'
//   const prompt = `${instruction}\n\nTranscript:\n${transcript}\n\nSummary:`
//   const { data } = await http.post('/phi3/generate', { 
//     prompt,
//     max_tokens: 256,  // Reduced token limit
//     temperature: 0.3  // Lower temperature for faster generation
//   }, {
//     timeout: 300000, // 5 minutes timeout for analysis (reduced from 10)
//   })
//   return { analysis: data?.text || '' }
// }

import { http } from './http'

export const fetchMeetings = async () => {
  const { data } = await http.get('/meetings')
  return data
}

export const createMeeting = async (payload) => {
  const { data } = await http.post('/meetings', payload)
  return data
}

export const uploadAndTranscribe = async (file, meetingData = {}) => {
  const form = new FormData()
  form.append('audio', file)
  
  // Add meeting form data if provided
  if (meetingData.title) form.append('title', meetingData.title)
  if (meetingData.date) form.append('date', meetingData.date)
  if (meetingData.location) form.append('location', meetingData.location)
  if (meetingData.host) form.append('host', meetingData.host)
  if (meetingData.presentees) form.append('presentees', meetingData.presentees)
  if (meetingData.absentees) form.append('absentees', meetingData.absentees)
  if (meetingData.agenda) form.append('agenda', meetingData.agenda)
  if (meetingData.time) form.append('adjournment_time', meetingData.time)

  const { data } = await http.post(
    '/summary',  // Use summary endpoint which does everything including MoM generation
    form,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
    }
  )
  return data
}

// Text transcript analysis (fallback)
export const getFullAnalysis = async (transcript) => {
  console.log('Calling getFullAnalysis with transcript length:', transcript.length)
  const { data } = await http.post(
    '/process_transcript',
    { transcript },
    { timeout: 300000 }
  )
  console.log('getFullAnalysis response:', data)
  return data
}
