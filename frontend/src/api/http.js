import axios from 'axios'

export const http = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes timeout for transcription requests
})


