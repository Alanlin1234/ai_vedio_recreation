import { useState } from 'react'
import { ArrowLeft, ArrowRight, BookOpen, Sparkle, Lightbulb } from '@phosphor-icons/react'

const Page2 = ({ project, onGenerateNewStory, onBack, isLoading, loadingMessage }) => {
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    setError('')
    try {
      await onGenerateNewStory()
    } catch (err) {
      setError(err.response?.data?.error || err.message || '生成新故事失败')
    }
  }

  const analysis = project.analysis || {}

  const stripMarkdown = (text) => {
    if (!text) return ''
    return text
      .replace(/#{1,6}\s?/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">原片分析</h2>
        <p className="text-charcoal-500 font-serif">
          {analysis.story_content ? '这是 AI 对原片的理解' : '正在看片，别催...'}
        </p>
      </div>

      <div className="space-y-5 mb-8">
        <div className="content-card content-card-moss">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-moss/10 flex items-center justify-center">
              <BookOpen size={20} weight="duotone" className="text-moss" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">故事内容</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {analysis.story_content ? stripMarkdown(analysis.story_content) : <span className="animate-pulse-soft text-charcoal-400">正在加载...</span>}
            </p>
          </div>
        </div>

        <div className="content-card content-card-caramel">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-caramel-100 flex items-center justify-center">
              <Sparkle size={20} weight="duotone" className="text-caramel-400" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">故事亮点</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {analysis.highlights ? stripMarkdown(analysis.highlights) : <span className="animate-pulse-soft text-charcoal-400">正在加载...</span>}
            </p>
          </div>
        </div>

        <div className="content-card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-moss/10 flex items-center justify-center">
              <Lightbulb size={20} weight="duotone" className="text-moss" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">教育意义</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {analysis.educational_meaning ? stripMarkdown(analysis.educational_meaning) : <span className="animate-pulse-soft text-charcoal-400">正在加载...</span>}
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          className="btn-secondary flex items-center gap-2"
          onClick={onBack}
        >
          <ArrowLeft size={18} />
          上一回
        </button>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleGenerate}
          disabled={isLoading || !analysis.story_content}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>{loadingMessage}</span>
            </>
          ) : (
            <>
              换个结局试试
              <ArrowRight size={18} weight="bold" />
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-center">
          {error}
        </div>
      )}
    </div>
  )
}

export default Page2
