import axios from 'axios'

const api = axios.create({
  baseURL: 'https://ai-document-chatbot-oqd9.onrender.com',
})

// Don't attach a (possibly stale/expired) token to the endpoints that issue tokens
const PUBLIC_ENDPOINTS = ['/auth/login', '/auth/signup']

api.interceptors.request.use((config) => {
  const isPublic = PUBLIC_ENDPOINTS.some((endpoint) => config.url?.startsWith(endpoint))
  if (!isPublic) {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// If the token is invalid/expired, any request will come back 401 - clear it and
// bounce to login instead of leaving the user stuck on a broken page
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
