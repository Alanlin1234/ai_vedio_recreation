import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, ArrowRight, BookOpen, Sparkle, Lightbulb } from '@phosphor-icons/react'
import { pickEducationalSummary } from '../utils/educationalDisplay'

const Page3 = ({ project, onGenerateStoryboard, onBack, isLoading, loadingMessage }) => {
  const { t } = useTranslation()
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    setError('')
    try {
      await onGenerateStoryboard()
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('page3.error'))
    }
  }

  const newStory = project.new_story || {}
  const eduSummary = pickEducationalSummary(newStory.educational_meaning)

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
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">{t('page3.title')}</h2>
        <p className="text-charcoal-500 font-serif">
          {newStory.story ? t('page3.subtitleReady') : t('page3.subtitleLoading')}
        </p>
      </div>

      <div className="space-y-5 mb-8">
        <div className="content-card content-card-moss">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-moss/10 flex items-center justify-center">
              <BookOpen size={20} weight="duotone" className="text-moss" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page3.storyContent')}</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {newStory.story ? stripMarkdown(newStory.story) : <span className="animate-pulse-soft text-charcoal-400">{t('page3.generatingStory')}</span>}
            </p>
          </div>
        </div>

        <div className="content-card content-card-caramel">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-caramel-100 flex items-center justify-center">
              <Sparkle size={20} weight="duotone" className="text-caramel-400" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page3.storyHighlights')}</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {newStory.highlights ? stripMarkdown(newStory.highlights) : <span className="animate-pulse-soft text-charcoal-400">{t('page3.generating')}</span>}
            </p>
          </div>
        </div>

        <div className="content-card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-moss/10 flex items-center justify-center">
              <Lightbulb size={20} weight="duotone" className="text-moss" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page3.educational')}</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {eduSummary ? stripMarkdown(eduSummary) : <span className="animate-pulse-soft text-charcoal-400">{t('page3.generating')}</span>}
            </p>
          </div>
        </div>
      </div>

      <p className="text-xs text-charcoal-500 font-sans mb-6 max-w-2xl leading-relaxed">
        {t('page3.footer')}
      </p>

      <div className="flex gap-3">
        <button
          className="btn-secondary flex items-center gap-2"
          onClick={onBack}
        >
          <ArrowLeft size={18} />
          {t('page3.back')}
        </button>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleGenerate}
          disabled={isLoading || !newStory.story}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>{loadingMessage}</span>
            </>
          ) : (
            <>
              {t('page3.next')}
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

export default Page3
