import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

// Request interceptor: injeta Bearer token em todas as requisicoes
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: tenta refresh em 401; logout em falha do refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const refresh = localStorage.getItem('refresh_token')
        // Usar axios puro (nao a instancia api) para evitar interceptor recursivo
        const { data } = await axios.post('/api/auth/token/refresh/', { refresh })
        localStorage.setItem('access_token', data.access)
        // simplejwt com ROTATE_REFRESH_TOKENS=True devolve novo refresh token
        if (data.refresh) {
          localStorage.setItem('refresh_token', data.refresh)
        }
        // Atualiza cookie do Grafana com o novo access token
        const maxAge = 12 * 3600
        document.cookie = `fs_access_token=${data.access}; path=/grafana; secure; samesite=strict; max-age=${maxAge}`
        original.headers.Authorization = `Bearer ${data.access}`
        return api(original)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        document.cookie = 'fs_access_token=; path=/grafana; max-age=0'
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
