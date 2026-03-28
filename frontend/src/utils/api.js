import axios from 'axios'
import { getSupabaseAccessToken, isSupabaseAuthConfigured } from '../lib/supabaseClient'
import { getStoredAppLanguage } from '../i18n'

const API_BASE_URL = '/api/pipeline'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1800000,
  withCredentials: true,
})

const reviewApi = axios.create({
  baseURL: '/api',
  timeout: 60000,
  withCredentials: true,
})

const agentApi = axios.create({
  baseURL: '/api/agent',
  timeout: 1800000,
  withCredentials: true,
})

const authApi = axios.create({
  baseURL: '/api/auth',
  timeout: 30000,
  withCredentials: true,
})

function attachBearer(instance) {
  instance.interceptors.request.use(async (config) => {
    config.headers = config.headers || {}
    config.headers['X-Output-Language'] = getStoredAppLanguage()
    if (isSupabaseAuthConfigured()) {
      const t = await getSupabaseAccessToken()
      if (t) {
        config.headers.Authorization = `Bearer ${t}`
      }
    }
    return config
  })
}

attachBearer(api)
attachBearer(reviewApi)
attachBearer(agentApi)
attachBearer(authApi)

export const login = async (username, password) => {
  const response = await authApi.post('/login', { username, password })
  return response.data
}

export const logout = async () => {
  const response = await authApi.post('/logout')
  return response.data
}

export const fetchMe = async () => {
  const response = await authApi.get('/me')
  return response.data
}

export const uploadVideo = async (file) => {
  const formData = new FormData()
  formData.append('video', file)

  const response = await api.post('/upload-video', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export const analyzeVideo = async (recreationId, data = {}) => {
  const response = await api.post(`/analyze-video/${recreationId}`, data)
  return response.data
}

export const reviewVideo = async (recreationId, data = {}) => {
  const response = await reviewApi.post(`/reviewer/${recreationId}`, data)
  return response.data
}

export const generateNewStory = async (recreationId, data = {}) => {
  const response = await api.post(`/generate-new-story/${recreationId}`, data)
  return response.data
}

export const generateStoryboard = async (recreationId, data = {}) => {
  const response = await api.post(`/generate-storyboard/${recreationId}`, data)
  return response.data
}

export const generateSceneVideos = async (recreationId) => {
  const response = await api.post(`/generate-scene-videos/${recreationId}`)
  return response.data
}

export const combineVideo = async (recreationId) => {
  const response = await api.post(`/combine-video/${recreationId}`)
  return response.data
}

export const generateSceneVideosAgent = async (recreationId) => {
  const response = await agentApi.post(`/generate-videos/${recreationId}`)
  return response.data
}

export const getVideoStatus = async (recreationId) => {
  const response = await agentApi.get(`/video-status/${recreationId}`)
  return response.data
}

export const getProject = async (recreationId) => {
  const response = await api.get(`/project/${recreationId}`)
  return response.data
}

export const getPipelineConfig = async () => {
  const response = await api.get('/config')
  return response.data
}

export const exportVideo = async (recreationId) => {
  const t = await getSupabaseAccessToken()
  const q = t ? `?access_token=${encodeURIComponent(t)}` : ''
  window.open(`${API_BASE_URL}/export-video/${recreationId}${q}`, '_blank')
}

export const getFinalPreviewUrl = async (recreationId) => {
  const t = await getSupabaseAccessToken()
  const q = t ? `?access_token=${encodeURIComponent(t)}` : ''
  return `${API_BASE_URL}/final-preview/${recreationId}${q}`
}

export const fetchYingfangAgents = async () => {
  const response = await api.get('/yingfang-agents')
  return response.data
}

export default api
