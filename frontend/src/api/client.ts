import axios from 'axios'
import { supabase } from '../lib/supabase'

const apiClient = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '',
})

// Request interceptor: attach Supabase JWT as Bearer token
apiClient.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession()
  if (data.session?.access_token) {
    config.headers.Authorization = `Bearer ${data.session.access_token}`
  }
  return config
})

// Response interceptor: on 401, refresh session and retry once
apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401 &&
      error.config &&
      !(error.config as unknown as Record<string, unknown>)._retry
    ) {
      const config = error.config as unknown as Record<string, unknown>
      config._retry = true
      const { data } = await supabase.auth.refreshSession()
      if (data.session?.access_token) {
        error.config.headers = error.config.headers ?? {}
        error.config.headers.Authorization = `Bearer ${data.session.access_token}`
        return apiClient(error.config)
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
