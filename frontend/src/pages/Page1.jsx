import { useState, useRef } from 'react'
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
      setError('请上传视频文件')
    }
  }

  const handleFileSelect = async (file) => {
    if (!file.type.startsWith('video/')) {
      setError('请选择视频文件')
      return
    }

    setError('')
    try {
      await onUpload(file)
    } catch (err) {
      setError(err.response?.data?.error || err.message || '上传失败')
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">上传视频</h2>
        <p className="text-charcoal-500 font-serif">拖放或点击，把视频丢进来</p>
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
              {isDragging ? '松开鼠标上传视频' : '拖放视频到这里'}
            </p>
            <p className="text-charcoal-400 text-sm">或点击选择文件</p>
            <p className="text-charcoal-400 text-sm mt-3">支持 MP4, AVI, MOV 等格式</p>
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
              title="重新上传"
            >
              <ArrowCounterClockwise size={20} />
            </button>
          </div>

          <div className="content-card border border-charcoal-100/80">
            <label
              htmlFor="piece-notes"
              className="block text-sm font-serif font-semibold text-charcoal-700 mb-2"
            >
              片子说明
            </label>
            <p className="text-xs text-charcoal-500 font-sans mb-3 leading-relaxed">
              简要介绍这部素材的内容、风格，以及你希望做的二创方向。审核员会结合解析结果与你的说明，从内容、画风、叙事与二创潜力等维度打分，并判断是否适合进入二创流程。
            </p>
            <textarea
              id="piece-notes"
              value={creatorNotes}
              onChange={(e) => onCreatorNotesChange(e.target.value)}
              rows={5}
              disabled={isLoading}
              placeholder="例如：原片是科普类短视频，希望改成悬疑叙事风；或说明画面偏纪实、希望统一成某种画风……"
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
                  解析视频
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
