import { useState } from 'react'
import Page1 from './pages/Page1'
import Page2 from './pages/Page2'
import Page3 from './pages/Page3'
import Page4 from './pages/Page4'
import Page5 from './pages/Page5'
import Page6 from './pages/Page6'
import StepIndicator from './components/StepIndicator'
import { VideoCamera, ArrowRight } from '@phosphor-icons/react'
import { uploadVideo, analyzeVideo, generateNewStory, generateStoryboard, generateSceneVideos, combineVideo, exportVideo, getProject } from './utils/api'

function App() {
  const [currentStep, setCurrentStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [project, setProject] = useState({
    id: null,
    video_file: null,
    video_url: null,
    analysis: null,
    new_story: null,
    storyboard: null,
    scene_videos: null,
    final_video: null
  })

  const goToStep = (step) => {
    setCurrentStep(step)
  }

  const handleUploadVideo = async (file) => {
    setIsLoading(true)
    setLoadingMessage('正在上传...')
    try {
      const response = await uploadVideo(file)
      setProject(prev => ({ ...prev, id: response.recreation_id, video_file: file }))
      setIsLoading(false)
      return response
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const handleAnalyzeVideo = async () => {
    setIsLoading(true)
    setLoadingMessage('正在看片，别催...')
    console.log('[DEBUG] 开始分析视频, project.id:', project.id)
    try {
      const response = await analyzeVideo(project.id)
      console.log('[DEBUG] analyzeVideo 响应:', response)
      setProject(prev => ({
        ...prev,
        analysis: {
          story_content: response.story_content,
          highlights: response.highlights,
          educational_meaning: response.educational_meaning
        }
      }))
      console.log('[DEBUG] 准备跳转到步骤 2')
      setCurrentStep(2)
      console.log('[DEBUG] 跳转完成')
      setIsLoading(false)
    } catch (error) {
      console.error('[DEBUG] 分析视频失败:', error)
      setIsLoading(false)
      throw error
    }
  }

  const handleGenerateNewStory = async () => {
    setIsLoading(true)
    setLoadingMessage('正在憋剧本...')
    try {
      const response = await generateNewStory(project.id)
      setProject(prev => ({
        ...prev,
        new_story: {
          story: response.new_story,
          highlights: response.highlights,
          educational_meaning: response.educational_meaning
        }
      }))
      setCurrentStep(3)
      setIsLoading(false)
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const handleGenerateStoryboard = async () => {
    setIsLoading(true)
    setLoadingMessage('正在画分镜...')
    try {
      const response = await generateStoryboard(project.id)
      setProject(prev => ({ ...prev, storyboard: response.storyboard }))
      setCurrentStep(4)
      setIsLoading(false)
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const handleGenerateSceneVideos = async () => {
    setIsLoading(true)
    setLoadingMessage('渲染中...')
    try {
      const response = await generateSceneVideos(project.id)
      setProject(prev => ({ ...prev, scene_videos: response.generated_videos }))
      setCurrentStep(5)
      setIsLoading(false)
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const handleCombineVideo = async () => {
    setIsLoading(true)
    setLoadingMessage('正在拼接...')
    try {
      const response = await combineVideo(project.id)
      setProject(prev => ({ ...prev, final_video: response.final_video_path }))
      setCurrentStep(6)
      setIsLoading(false)
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const handleExportVideo = async () => {
    setIsLoading(true)
    setLoadingMessage('正在导出...')
    try {
      await exportVideo(project.id)
      setIsLoading(false)
      alert('视频导出成功！')
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const renderPage = () => {
    switch (currentStep) {
      case 1:
        return (
          <Page1
            project={project}
            onUpload={handleUploadVideo}
            onAnalyze={handleAnalyzeVideo}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 2:
        return (
          <Page2
            project={project}
            onGenerateNewStory={handleGenerateNewStory}
            onBack={() => goToStep(1)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 3:
        return (
          <Page3
            project={project}
            onGenerateStoryboard={handleGenerateStoryboard}
            onBack={() => goToStep(2)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 4:
        return (
          <Page4
            project={project}
            onGenerateSceneVideos={handleGenerateSceneVideos}
            onBack={() => goToStep(3)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 5:
        return (
          <Page5
            project={project}
            onCombineVideo={handleCombineVideo}
            onBack={() => goToStep(4)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 6:
        return (
          <Page6
            project={project}
            onExport={handleExportVideo}
            onBack={() => goToStep(5)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      default:
        return <Page1 project={project} onUpload={handleUploadVideo} onAnalyze={handleAnalyzeVideo} isLoading={isLoading} loadingMessage={loadingMessage} />
    }
  }

  return (
    <div className="min-h-screen bg-paper">
      <div className="max-w-5xl mx-auto px-5 py-10 md:px-8 md:py-14">
        <header className="mb-12">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-12 h-12 rounded-xl bg-moss flex items-center justify-center">
              <VideoCamera size={24} weight="duotone" className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-charcoal-700">影坊</h1>
            </div>
          </div>
          <p className="text-charcoal-500 font-serif text-lg">
            把原视频丢进来，5 分钟后还你一个新故事
          </p>
        </header>

        <StepIndicator currentStep={currentStep} />

        <div className="card p-8 md:p-10">
          {renderPage()}
        </div>
      </div>
    </div>
  )
}

export default App
