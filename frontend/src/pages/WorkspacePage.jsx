import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft } from '@phosphor-icons/react'
import StepIndicator from '../components/StepIndicator'
import AgentProgress from '../components/AgentProgress'
import PromptDebugPanel from '../components/PromptDebugPanel'
import Page1 from './Page1'
import Page2 from './Page2'
import Page3 from './Page3'
import Page4 from './Page4'
import Page5 from './Page5'
import Page6 from './Page6'

function WorkspacePage() {
  const { t } = useTranslation()
  const location = useLocation()
  const [currentStep, setCurrentStep] = useState(1)
  const [completedSteps, setCompletedSteps] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [agentStatuses, setAgentStatuses] = useState({})
  const [currentAgent, setCurrentAgent] = useState(null)
  const [project, setProject] = useState({
    id: null,
    video_file: null,
    video_url: null,
    analysis: null,
    review: null,
    new_story: null,
    storyboard: null,
    scene_videos: null,
    final_video: null,
    creatorNotes: '',
    debugPrompts: [],
  })

  useEffect(() => {
    if (location.state?.videoFile) {
      setProject((prev) => ({ ...prev, video_file: location.state.videoFile }))
    }
  }, [location.state])

  const resetProject = () => {
    setProject({
      id: null,
      video_file: null,
      video_url: null,
      analysis: null,
      review: null,
      new_story: null,
      storyboard: null,
      scene_videos: null,
      final_video: null,
      creatorNotes: '',
      debugPrompts: [],
    })
    setCompletedSteps([])
    setCurrentStep(1)
    setAgentStatuses({})
    setCurrentAgent(null)
  }

  const goToStep = (step) => {
    setCurrentStep(step)
  }

  const handleStepClick = (step) => {
    setCurrentStep(step)
  }

  const markStepCompleted = (step) => {
    setCompletedSteps((prev) => (prev.includes(step) ? prev : [...prev, step]))
  }

  const updateAgentStatus = (agentId, status) => {
    setAgentStatuses((prev) => ({ ...prev, [agentId]: status }))
    if (status === 'running') {
      setCurrentAgent(agentId)
    } else if (status === 'completed' || status === 'failed') {
      setCurrentAgent(null)
    }
  }

  const handleUploadVideo = async (file) => {
    setIsLoading(true)
    setLoadingMessage(t('workspace.loadingUpload'))
    try {
      const { uploadVideo } = await import('../utils/api')
      const response = await uploadVideo(file)
      setProject((prev) => ({ ...prev, id: response.recreation_id, video_file: file }))
      markStepCompleted(1)
      setCurrentStep(2)
      setIsLoading(false)
      return response
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const handleAnalyzeVideo = async () => {
    setIsLoading(true)
    setLoadingMessage(t('workspace.loadingAnalyze'))
    updateAgentStatus('education_expert', 'running')
    try {
      const { analyzeVideo, reviewVideo } = await import('../utils/api')
      const response = await analyzeVideo(project.id, {
        creator_notes: project.creatorNotes || '',
      })
      setProject((prev) => ({
        ...prev,
        analysis: {
          story_content: response.story_content,
          highlights: response.highlights,
          educational_meaning: response.educational_meaning,
          educational_points: response.educational_points || [],
        },
        debugPrompts: [
          ...(prev.debugPrompts || []),
          ...(response.debug_prompts || []),
        ],
      }))
      updateAgentStatus('education_expert', 'completed')

      updateAgentStatus('reviewer', 'running')
      try {
        const reviewResponse = await reviewVideo(project.id, {
          creator_notes: project.creatorNotes || '',
        })
        setProject((prev) => ({
          ...prev,
          debugPrompts: [
            ...(prev.debugPrompts || []),
            ...(reviewResponse.debug_prompts || []),
          ],
          review: {
            score: reviewResponse.score,
            passed: reviewResponse.passed,
            scores: reviewResponse.scores,
            summary: reviewResponse.summary,
            pass_threshold: reviewResponse.pass_threshold,
            message: reviewResponse.message,
            suggestions: reviewResponse.suggestions,
          },
        }))
        updateAgentStatus('reviewer', 'completed')

        const passed = reviewResponse.passed !== false && reviewResponse.passed !== 0
        if (passed) {
          updateAgentStatus('story_writer', 'running')
          markStepCompleted(2)
          setCurrentStep(3)
        } else {
          updateAgentStatus('reviewer', 'failed')
          alert(reviewResponse.message || t('workspace.reviewFailed'))
          resetProject()
          setIsLoading(false)
          return
        }
      } catch (reviewErr) {
        const status = reviewErr.response?.status
        if (status === 404) {
          updateAgentStatus('reviewer', 'completed')
          updateAgentStatus('story_writer', 'running')
          markStepCompleted(2)
          setCurrentStep(3)
        } else {
          updateAgentStatus('reviewer', 'failed')
          alert(
            reviewErr.response?.data?.message ||
              reviewErr.message ||
              t('workspace.reviewNoEducational')
          )
          resetProject()
          setIsLoading(false)
          return
        }
      }

      setIsLoading(false)
    } catch (error) {
      updateAgentStatus('education_expert', 'failed')
      setIsLoading(false)
      throw error
    }
  }

  const serializeStoryField = (value) => {
    if (value == null) return ''
    if (typeof value === 'string') return value
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }

  const handleGenerateNewStory = async () => {
    setIsLoading(true)
    setLoadingMessage(t('workspace.loadingStory'))
    try {
      const { generateNewStory } = await import('../utils/api')
      const response = await generateNewStory(project.id, {
        original_highlights: serializeStoryField(project.analysis?.highlights),
        original_educational: serializeStoryField(
          Array.isArray(project.analysis?.educational_points) &&
            project.analysis.educational_points.length > 0
            ? project.analysis.educational_points.join('\n')
            : project.analysis?.educational_meaning
        ),
      })
      setProject((prev) => ({
        ...prev,
        new_story: {
          story: response.new_story,
          highlights: response.highlights,
          educational_meaning: response.educational_meaning,
        },
        debugPrompts: [
          ...(prev.debugPrompts || []),
          ...(response.debug_prompts || []),
        ],
      }))
      updateAgentStatus('story_writer', 'completed')
      markStepCompleted(3)
      setCurrentStep(4)
      setIsLoading(false)
    } catch (error) {
      updateAgentStatus('story_writer', 'failed')
      setIsLoading(false)
      throw error
    }
  }

  const handleGenerateStoryboard = async () => {
    setIsLoading(true)
    setLoadingMessage(t('workspace.loadingStoryboard'))
    try {
      const { generateStoryboard } = await import('../utils/api')
      const response = await generateStoryboard(project.id)
      setProject((prev) => ({ ...prev, storyboard: response.storyboard }))
      updateAgentStatus('storyboard', 'completed')
      markStepCompleted(4)
      setCurrentStep(5)
      setIsLoading(false)
    } catch (error) {
      updateAgentStatus('storyboard', 'failed')
      setIsLoading(false)
      throw error
    }
  }

  const handleGenerateSceneVideos = async () => {
    if (isLoading) return
    if (project.scene_videos && project.scene_videos.length > 0) {
      setCurrentStep(6)
      return
    }

    setIsLoading(true)
    setLoadingMessage(t('workspace.loadingRender'))
    try {
      const { generateSceneVideosAgent, generateSceneVideos } = await import('../utils/api')
      let response
      try {
        response = await generateSceneVideosAgent(project.id)
      } catch {
        response = null
      }
      if (!response?.success) {
        response = await generateSceneVideos(project.id)
      }
      if (!response?.success) {
        throw new Error(response?.error || response?.message || t('workspace.sceneVideoFailed'))
      }
      const list =
        response.result?.scene_videos ||
        response.result?.generated_videos ||
        response.generated_videos ||
        []
      const morePrompts =
        response.debug_prompts ||
        response.result?.debug_prompts ||
        []
      setProject((prev) => ({
        ...prev,
        scene_videos: list,
        debugPrompts: [...(prev.debugPrompts || []), ...morePrompts],
      }))
      updateAgentStatus('video_generator', 'completed')
      markStepCompleted(5)
      setCurrentStep(6)
      setIsLoading(false)
    } catch (error) {
      updateAgentStatus('video_generator', 'failed')
      setIsLoading(false)
      throw error
    }
  }

  const handleCombineVideo = async () => {
    setIsLoading(true)
    setLoadingMessage(t('workspace.loadingCombine'))
    updateAgentStatus('video_composer', 'running')
    try {
      const { combineVideo, getFinalPreviewUrl } = await import('../utils/api')
      const response = await combineVideo(project.id)
      if (!response?.success) {
        throw new Error(response?.error || t('workspace.combineFailed'))
      }
      const previewUrl = await getFinalPreviewUrl(project.id)
      setProject((prev) => ({
        ...prev,
        final_video: previewUrl,
      }))
      updateAgentStatus('video_composer', 'completed')
      markStepCompleted(6)
      setCurrentStep(7)
      setIsLoading(false)
    } catch (error) {
      updateAgentStatus('video_composer', 'failed')
      setIsLoading(false)
      throw error
    }
  }

  const handleExportVideo = async () => {
    setIsLoading(true)
    setLoadingMessage('正在导出...')
    updateAgentStatus('video_composer', 'running')
    try {
      const { exportVideo } = await import('../utils/api')
      await exportVideo(project.id)
      updateAgentStatus('video_composer', 'completed')
      markStepCompleted(7)
      setIsLoading(false)
      alert(t('workspace.exportSuccess'))
    } catch (error) {
      updateAgentStatus('video_composer', 'failed')
      setIsLoading(false)
      throw error
    }
  }

  const renderPage = () => {
    if (currentStep <= 2) {
      return (
        <Page1
          project={project}
          creatorNotes={project.creatorNotes || ''}
          onCreatorNotesChange={(v) =>
            setProject((prev) => ({ ...prev, creatorNotes: v }))
          }
          onUpload={handleUploadVideo}
          onAnalyze={handleAnalyzeVideo}
          onReset={resetProject}
          isLoading={isLoading}
          loadingMessage={loadingMessage}
        />
      )
    }
    switch (currentStep) {
      case 3:
        return (
          <Page2
            project={project}
            onGenerateNewStory={handleGenerateNewStory}
            onBack={() => goToStep(2)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 4:
        return (
          <Page3
            project={project}
            onGenerateStoryboard={handleGenerateStoryboard}
            onBack={() => goToStep(3)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 5:
        return (
          <Page4
            project={project}
            onGenerateSceneVideos={handleGenerateSceneVideos}
            onBack={() => goToStep(4)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 6:
        return (
          <Page5
            project={project}
            onCombineVideo={handleCombineVideo}
            onBack={() => goToStep(5)}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
      case 7:
        return (
          <Page6
            project={project}
            onExport={handleExportVideo}
            onBack={() => goToStep(6)}
          />
        )
      default:
        return (
          <Page1
            project={project}
            creatorNotes={project.creatorNotes || ''}
            onCreatorNotesChange={(v) =>
              setProject((prev) => ({ ...prev, creatorNotes: v }))
            }
            onUpload={handleUploadVideo}
            onAnalyze={handleAnalyzeVideo}
            onReset={resetProject}
            isLoading={isLoading}
            loadingMessage={loadingMessage}
          />
        )
    }
  }

  return (
    <div className="min-h-screen bg-paper">
      <div className="phantom-section-inner py-8">
        <div className="flex gap-8 min-h-[calc(100vh-128px)]">
          <div className="w-[280px] flex-shrink-0 flex flex-col gap-6">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-charcoal-500 hover:text-moss transition-colors"
            >
              <ArrowLeft size={16} />
              <span className="text-sm font-medium">{t('workspace.backHome')}</span>
            </Link>

            <div className="content-card p-6 flex-1 flex flex-col gap-6">
              <StepIndicator
                currentStep={currentStep}
                completedSteps={completedSteps}
                onStepClick={handleStepClick}
              />

              <div className="border-t border-charcoal-100 pt-6">
                <AgentProgress
                  currentAgent={currentAgent}
                  agentStatuses={agentStatuses}
                  isRunning={isLoading}
                />
              </div>

              <div className="border-t border-charcoal-100 pt-6">
                <PromptDebugPanel
                  entries={project.debugPrompts}
                  onClear={() =>
                    setProject((prev) => ({ ...prev, debugPrompts: [] }))
                  }
                />
              </div>
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="content-card p-8 h-full">{renderPage()}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WorkspacePage
