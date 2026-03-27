import { useState } from 'react'
import { ArrowLeft, ArrowRight, Check, Warning, Play } from '@phosphor-icons/react'

const Page5 = ({ project, onCombineVideo, onBack, isLoading, loadingMessage }) => {
  const [error, setError] = useState('')

  const handleCombine = async () => {
    setError('')
    try {
      await onCombineVideo()
    } catch (err) {
      setError(err.response?.data?.error || err.message || '合成视频失败')
    }
  }

  const sceneVideos = project.scene_videos || []

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">分镜视频</h2>
        <p className="text-charcoal-500 font-serif">
          {sceneVideos.length > 0 ? '每个镜头都在渲染中，确认无误后可以拼接成片' : '正在渲染镜头...'}
        </p>
      </div>

      {sceneVideos.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
          {sceneVideos.map((video, index) => (
            <div key={index} className={`content-card ${video.success ? 'border border-paper-300' : 'border border-red-200'}`}>
              <div className="flex items-center mb-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-sans font-semibold ${
                  video.success
                    ? 'bg-moss'
                    : 'bg-red-400'
                }`}>
                  {video.success ? (
                    <Check size={20} weight="bold" />
                  ) : (
                    <Warning size={20} weight="bold" />
                  )}
                </div>
                <div className="ml-3">
                  <h3 className="text-lg font-serif font-semibold text-charcoal-700">
                    场景 {video.scene_index !== undefined ? video.scene_index + 1 : index + 1}
                  </h3>
                  <span className={`text-xs font-serif px-2 py-1 rounded-full ${
                    video.success
                      ? 'bg-moss/10 text-moss'
                      : 'bg-red-100 text-red-500'
                  }`}>
                    {video.success ? '渲染成功' : '渲染失败'}
                  </span>
                </div>
              </div>

              {video.success ? (
                <div className="space-y-3">
                  <div className="video-container">
                    {video.video_url || video.video_path || video.local_path ? (
                      <video
                        src={video.video_url || video.video_path || video.local_path}
                        controls
                        className="w-full h-full rounded-lg"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-paper-200 rounded-lg">
                        <div className="text-center text-charcoal-400">
                          <Play size={32} weight="fill" className="mx-auto mb-2" />
                          <p className="text-sm font-serif">视频预览</p>
                        </div>
                      </div>
                    )}
                  </div>
                  {video.local_path && (
                    <p className="text-xs text-charcoal-400 font-serif truncate">
                      {video.local_path}
                    </p>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <Warning size={32} className="mx-auto mb-2 text-red-400" />
                  <p className="text-sm text-charcoal-400 font-serif">{video.error || '渲染失败'}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 mb-8">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-paper-200 flex items-center justify-center">
            <Play size={32} weight="duotone" className="text-charcoal-400" />
          </div>
          <p className="text-charcoal-400 font-serif animate-pulse-soft">镜头渲染中...</p>
        </div>
      )}

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
          onClick={handleCombine}
          disabled={isLoading || sceneVideos.length === 0}
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>{loadingMessage}</span>
            </>
          ) : (
            <>
              拼接成片
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

export default Page5
