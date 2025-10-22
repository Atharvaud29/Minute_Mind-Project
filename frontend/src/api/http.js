// import axios from 'axios'

// export const http = axios.create({
//   baseURL: '/api',
//   timeout: 0, // No default timeout - let individual requests set their own timeouts
// })

import axios from 'axios'

export const http = axios.create({
  baseURL: '/api', // All requests will be prefixed with /api
  timeout: 60000,  // 60 seconds default timeout
})

// Request interceptor (optional: add auth headers if needed)
http.interceptors.request.use(
  (config) => {
    // Example: add token from localStorage/sessionStorage
    const token = localStorage.getItem('authToken') || sessionStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for global error handling
http.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)
