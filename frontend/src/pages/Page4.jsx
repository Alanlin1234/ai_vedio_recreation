import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, ArrowRight, FrameCorners, Play } from '@phosphor-icons/react'

const Page4 = ({ project, onGenerateSceneVideos, onBack, isLoading, loadingMessage }) => {
  const { t } = useTranslation()
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    setError('')
    try {
      await onGenerateSceneVideos()
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('page4.error'))
    }
  }

  const storyboard = project.storyboard || []

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">{t('page4.title')}</h2>
        <p className="text-charcoal-500 font-serif">
          {storyboard.length > 0 ? t('page4.subtitleReady') : t('page4.subtitleLoading')}
        </p>
      </div>

      {storyboard.length > 0 ? (
        <div className="mb-8 overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-paper-300">
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-16">{t('page4.colIndex')}</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-24">{t('page4.colShot')}</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-72">{t('page4.colVisual')}</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-56">{t('page4.colPlot')}</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-56">{t('page4.colDialogue')}</th>
              </tr>
            </thead>
            <tbody>
              {storyboard.map((scene, index) => {
                const dialogueRaw = (scene.dialogue != null && String(scene.dialogue).trim()) || ''
                const dialogueBad =
                  !dialogueRaw ||
                  dialogueRaw === '暂无台词' ||
                  dialogueRaw === '暂无' ||
                  dialogueRaw === 'No dialogue'
                const dialogueDisplay = dialogueBad ? t('page4.noDialogue') : dialogueRaw
                return (
                <tr key={index} className="border-b border-paper-200 hover:bg-paper-100/50 transition-colors">
                  <td className="p-3">
                    <div className="w-10 h-10 rounded-full bg-moss text-white flex items-center justify-center font-sans font-semibold text-sm">
                      {scene.scene_number || index + 1}
                    </div>
                  </td>
                  <td className="p-3">
                    <span className="text-charcoal-600 font-serif">
                      {scene.shot_type || '-'}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="bg-paper-100 rounded-xl p-3">
                      {scene.image && (
                        <div className="mb-3">
                          <img
                            src={scene.image}
                            alt={t('page4.sceneAlt', { n: scene.scene_number || index + 1 })}
                            className="w-full h-32 object-cover rounded-lg"
                          />
                        </div>
                      )}
                      <p className="text-charcoal-500 text-sm font-serif leading-relaxed whitespace-pre-wrap">
                        {scene.description || t('page4.noDescription')}
                      </p>
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="bg-paper-100 rounded-xl p-3">
                      <p className="text-charcoal-600 text-sm font-serif leading-relaxed whitespace-pre-wrap">
                        {scene.plot || t('page4.noPlot')}
                      </p>
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="bg-caramel-50 rounded-xl p-3 border-l-2 border-caramel-300">
                      <p className="text-charcoal-600 text-sm font-serif leading-relaxed whitespace-pre-wrap">
                        {dialogueDisplay}
                      </p>
                    </div>
                  </td>
                </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-16 mb-8">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-paper-200 flex items-center justify-center">
            <FrameCorners size={32} weight="duotone" className="text-charcoal-400" />
          </div>
          <p className="text-charcoal-400 font-serif animate-pulse-soft">{t('page4.waiting')}</p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          className="btn-secondary flex items-center gap-2"
          onClick={onBack}
        >
          <ArrowLeft size={18} />
          {t('page4.back')}
        </button>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={handleGenerate}
          disabled={isLoading || storyboard.length === 0}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>{loadingMessage}</span>
            </>
          ) : (
            <>
              {t('page4.next')}
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

export default Page4
