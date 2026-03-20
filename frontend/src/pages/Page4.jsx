import { useState } from 'react'
import { ArrowLeft, ArrowRight, FrameCorners, Play } from '@phosphor-icons/react'

const Page4 = ({ project, onGenerateSceneVideos, onBack, isLoading, loadingMessage }) => {
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    setError('')
    try {
      await onGenerateSceneVideos()
    } catch (err) {
      setError(err.response?.data?.error || err.message || '生成视频失败')
    }
  }

  const storyboard = project.storyboard || []

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">分镜脚本</h2>
        <p className="text-charcoal-500 font-serif">
          {storyboard.length > 0 ? '把故事拆成镜头语言，看看每个镜头怎么拍' : '正在画分镜...'}
        </p>
      </div>

      {storyboard.length > 0 ? (
        <div className="mb-8 overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-paper-300">
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-16">序号</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-24">景别</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-72">画面</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-56">情节</th>
                <th className="text-left p-3 text-charcoal-500 font-serif font-medium w-56">台词</th>
              </tr>
            </thead>
            <tbody>
              {storyboard.map((scene, index) => (
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
                            alt={`场景${scene.scene_number || index + 1}`}
                            className="w-full h-32 object-cover rounded-lg"
                          />
                        </div>
                      )}
                      <p className="text-charcoal-500 text-sm font-serif leading-relaxed">
                        {scene.description || '暂无画面描述'}
                      </p>
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="bg-paper-100 rounded-xl p-3">
                      <p className="text-charcoal-600 text-sm font-serif leading-relaxed">
                        {scene.plot || '暂无情节描述'}
                      </p>
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="bg-caramel-50 rounded-xl p-3 border-l-2 border-caramel-300">
                      <p className="text-charcoal-600 text-sm font-serif leading-relaxed">
                        {scene.dialogue || '暂无台词'}
                      </p>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-16 mb-8">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-paper-200 flex items-center justify-center">
            <FrameCorners size={32} weight="duotone" className="text-charcoal-400" />
          </div>
          <p className="text-charcoal-400 font-serif animate-pulse-soft">分镜图马上好...</p>
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
              渲染镜头
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
