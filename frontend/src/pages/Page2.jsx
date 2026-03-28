import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Sparkle,
  Lightbulb,
  SealCheck,
} from '@phosphor-icons/react'

import { pickEducationalSummary } from '../utils/educationalDisplay'

const Page2 = ({ project, onGenerateNewStory, onBack, isLoading, loadingMessage }) => {
  const { t } = useTranslation()
  const [error, setError] = useState('')

  const reviewScoreLabels = useMemo(
    () => ({
      content: t('page2.dimContent'),
      visual_style: t('page2.dimVisual'),
      story_recreation: t('page2.dimStory'),
      creator_notes_alignment: t('page2.dimNotes'),
    }),
    [t]
  )

  const handleGenerate = async () => {
    setError('')
    try {
      await onGenerateNewStory()
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('page2.errorStory'))
    }
  }

  const analysis = project.analysis || {}
  const review = project.review
  const eduPoints = Array.isArray(analysis.educational_points) ? analysis.educational_points : []
  const eduSummary = pickEducationalSummary(analysis.educational_meaning)

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
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">{t('page2.title')}</h2>
        <p className="text-charcoal-500 font-serif">
          {analysis.story_content ? t('page2.subtitleReady') : t('page2.subtitleLoading')}
        </p>
      </div>

      <div className="space-y-5 mb-8">
        {review && (
          <div className="content-card border-2 border-moss/25 bg-moss/[0.06]">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-moss/15 flex items-center justify-center flex-shrink-0">
                <SealCheck size={22} weight="duotone" className="text-moss" />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page2.reviewTitle')}</h3>
                <p className="text-sm text-charcoal-500 mt-0.5">{t('page2.reviewSubtitle')}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 mb-4">
              <p className="text-2xl font-serif font-bold text-charcoal-800">
                {t('page2.total')}{' '}
                <span className="text-moss tabular-nums">
                  {review.score != null ? Number(review.score).toFixed(1) : '—'}
                </span>
                <span className="text-base font-normal text-charcoal-500"> / 100</span>
              </p>
              {review.pass_threshold != null && (
                <p className="text-sm text-charcoal-600">
                  {t('page2.threshold')}<span className="tabular-nums">{review.pass_threshold}</span>
                </p>
              )}
              {review.passed != null && (
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    review.passed
                      ? 'bg-moss/15 text-moss'
                      : 'bg-red-100 text-red-700'
                  }`}
                >
                  {review.passed ? t('page2.passed') : t('page2.notPassed')}
                </span>
              )}
            </div>
            {review.scores && typeof review.scores === 'object' && (
              <ul className="grid sm:grid-cols-2 gap-2 mb-4">
                {Object.entries(review.scores).map(([key, val]) => (
                  <li
                    key={key}
                    className="flex justify-between gap-3 text-sm bg-paper-100 rounded-lg px-3 py-2"
                  >
                    <span className="text-charcoal-600">
                      {reviewScoreLabels[key] || key}
                    </span>
                    <span className="font-medium text-charcoal-800 tabular-nums">
                      {val != null ? Number(val).toFixed(1) : '—'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {review.summary && (
              <div className="bg-paper-100 rounded-xl p-4 border border-charcoal-100">
                <p className="text-xs font-medium text-charcoal-500 mb-1">{t('page2.reviewSummary')}</p>
                <p className="text-charcoal-700 font-serif text-[15px] leading-relaxed whitespace-pre-wrap">
                  {stripMarkdown(review.summary)}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="content-card content-card-moss">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-moss/10 flex items-center justify-center">
              <BookOpen size={20} weight="duotone" className="text-moss" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page2.storyContent')}</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {analysis.story_content ? stripMarkdown(analysis.story_content) : <span className="animate-pulse-soft text-charcoal-400">{t('page2.loading')}</span>}
            </p>
          </div>
        </div>

        <div className="content-card content-card-caramel">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-caramel-100 flex items-center justify-center">
              <Sparkle size={20} weight="duotone" className="text-caramel-400" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page2.highlights')}</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5">
            <p className="text-charcoal-600 font-serif whitespace-pre-wrap leading-relaxed text-[15px]">
              {analysis.highlights ? stripMarkdown(analysis.highlights) : <span className="animate-pulse-soft text-charcoal-400">{t('page2.loading')}</span>}
            </p>
          </div>
        </div>

        <div className="content-card">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-moss/10 flex items-center justify-center">
              <Lightbulb size={20} weight="duotone" className="text-moss" />
            </div>
            <h3 className="text-lg font-serif font-semibold text-charcoal-700">{t('page2.educational')}</h3>
          </div>
          <div className="bg-paper-100 rounded-xl p-5 space-y-4">
            {eduPoints.length > 0 ? (
              <>
                <p className="text-xs font-medium text-charcoal-500 tracking-wide">{t('page2.corePoints')}</p>
                <ul className="space-y-2.5">
                  {eduPoints.map((line, idx) => (
                    <li
                      key={idx}
                      className="flex gap-3 text-charcoal-600 text-[14px] leading-relaxed"
                    >
                      <span
                        className="flex-shrink-0 w-6 h-6 rounded-md bg-moss/12 text-moss text-xs font-semibold flex items-center justify-center mt-0.5"
                        aria-hidden
                      >
                        {idx + 1}
                      </span>
                      <span className="font-serif">{stripMarkdown(line)}</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : eduSummary ? (
              <p className="text-charcoal-700 font-serif leading-relaxed text-[15px]">
                {stripMarkdown(eduSummary)}
              </p>
            ) : (
              <span className="animate-pulse-soft text-charcoal-400">{t('page2.loading')}</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          className="btn-secondary flex items-center gap-2"
          onClick={onBack}
        >
          <ArrowLeft size={18} />
          {t('page2.back')}
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
              {t('page2.next')}
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
