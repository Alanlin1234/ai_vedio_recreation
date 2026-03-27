import axios from 'axios'

const API_BASE_URL = '/api/pipeline'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1800000
})

const reviewApi = axios.create({
  baseURL: '/api',
  timeout: 60000
})

const agentApi = axios.create({
  baseURL: '/api/agent',
  timeout: 1800000
})

export const uploadVideo = async (file) => {
  const formData = new FormData()
  formData.append('video', file)

  const response = await api.post('/upload-video', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

export const analyzeVideo = async (recreationId) => {
  const response = await api.post(`/analyze-video/${recreationId}`)
  return response.data
}

export const reviewVideo = async (recreationId) => {
  const response = await reviewApi.post(`/reviewer/${recreationId}`)
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

export const exportVideo = async (recreationId) => {
  window.open(`${API_BASE_URL}/export-video/${recreationId}`, '_blank')
}

export default api
