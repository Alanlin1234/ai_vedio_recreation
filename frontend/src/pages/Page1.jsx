import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { VideoCamera, Check, ArrowRight, ArrowCounterClockwise } from '@phosphor-icons/react'

const Page1 = ({
  project,
  creatorNotes,
  onCreatorNotesChange,
  onUpload,
  onAnalyze,
  onReset,
  isLoading,
  loadingMessage,
}) => {
  const { t } = useTranslation()
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const videoFile = files.find((f) => f.type.startsWith('video/'))

    if (videoFile) {
      handleFileSelect(videoFile)
    } else {
      setError(t('page1.errorNoFile'))
    }
  }

  const handleFileSelect = async (file) => {
    if (!file.type.startsWith('video/')) {
      setError(t('page1.errorPick'))
      return
    }

    setError('')
    try {
      await onUpload(file)
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('page1.errorUpload'))
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">{t('page1.title')}</h2>
        <p className="text-charcoal-500 font-serif">{t('page1.subtitle')}</p>
      </div>

      {!project.video_file ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`dropzone ${isDragging ? 'drag-over' : ''}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
            className="hidden"
          />

          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-paper-200 flex items-center justify-center">
              <VideoCamera size={32} weight="duotone" className="text-moss" />
            </div>
            <p className="text-lg font-serif font-medium text-charcoal-700 mb-2">
              {isDragging ? t('page1.drop') : t('page1.dropHint')}
            </p>
            <p className="text-charcoal-400 text-sm">{t('page1.orClick')}</p>
            <p className="text-charcoal-400 text-sm mt-3">{t('page1.formats')}</p>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="content-card flex items-center gap-4 border border-moss/20">
            <div className="w-12 h-12 rounded-xl bg-moss/10 flex items-center justify-center flex-shrink-0">
              <Check size={24} weight="bold" className="text-moss" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-serif font-semibold text-charcoal-700 truncate">{project.video_file.name}</h3>
              <p className="text-sm text-charcoal-400">
                {(project.video_file.size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
            <button
              onClick={onReset}
              className="p-2 rounded-lg hover:bg-charcoal-100 text-charcoal-500 hover:text-charcoal-700 transition-colors"
              title={t('page1.reupload')}
            >
              <ArrowCounterClockwise size={20} />
            </button>
          </div>

          <div className="content-card border border-charcoal-100/80">
            <label
              htmlFor="piece-notes"
              className="block text-sm font-serif font-semibold text-charcoal-700 mb-2"
            >
              {t('page1.notesLabel')}
            </label>
            <p className="text-xs text-charcoal-500 font-sans mb-3 leading-relaxed">{t('page1.notesHelp')}</p>
            <textarea
              id="piece-notes"
              value={creatorNotes}
              onChange={(e) => onCreatorNotesChange(e.target.value)}
              rows={5}
              disabled={isLoading}
              placeholder={t('page1.notesPlaceholder')}
              className="w-full rounded-xl border border-charcoal-200 bg-paper px-4 py-3 text-sm text-charcoal-700 font-sans placeholder:text-charcoal-400 focus:outline-none focus:ring-2 focus:ring-moss/30 focus:border-moss/40 resize-y min-h-[120px]"
            />
          </div>

          <div className="flex justify-start">
            <button
              className="btn-primary flex items-center gap-2"
              onClick={onAnalyze}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>{loadingMessage}</span>
                </>
              ) : (
                <>
                  {t('page1.analyze')}
                  <ArrowRight size={18} weight="bold" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 text-center">
          {error}
        </div>
      )}
    </div>
  )
}

export default Page1
