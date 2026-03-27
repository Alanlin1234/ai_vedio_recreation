import axios from 'axios'

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

/** 确认后端分镜上限等（排查是否已部署新代码）：GET /api/pipeline/config */
export const getPipelineConfig = async () => {
  const response = await api.get('/config')
  return response.data
}

export const exportVideo = async (recreationId) => {
  window.open(`${API_BASE_URL}/export-video/${recreationId}`, '_blank')
}

/** 成片预览 URL（Cookie 会话下与 <video src> 同域可用） */
export const getFinalPreviewUrl = (recreationId) =>
  `${API_BASE_URL}/final-preview/${recreationId}`

/** 影坊多 Agent 元数据（与前端 constants/yingfangAgents 同源） */
export const fetchYingfangAgents = async () => {
  const response = await api.get('/yingfang-agents')
  return response.data
}

export default api
