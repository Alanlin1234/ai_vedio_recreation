import React from 'react'
import { ArrowLeft, DownloadSimple, CheckCircle, FilmSlate, Clock, Check } from '@phosphor-icons/react'

const Page6 = ({ project, onBack, onExport }) => {
  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">完成</h2>
        <p className="text-charcoal-500 font-serif">
          {project.final_video ? '新片出炉，可以下载了' : '正在拼接...'}
        </p>
      </div>

      <div className="mb-8">
        <div className="video-container mb-6">
          {project.final_video ? (
            <video
              src={project.final_video}
              controls
              className="w-full h-full rounded-lg"
              poster={project.storyboard && project.storyboard[0]?.image}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-paper-200 rounded-lg">
              <div className="text-center text-charcoal-400">
                <FilmSlate size={48} weight="duotone" className="mx-auto mb-3" />
                <p className="font-serif">视频正在加载中...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="content-card text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-moss/10 flex items-center justify-center">
            <FilmSlate size={24} weight="duotone" className="text-moss" />
          </div>
          <div className="text-charcoal-400 text-sm font-serif mb-1">场景数量</div>
          <div className="text-2xl font-serif font-bold text-charcoal-700">
            {project.scene_videos?.length || 0}
          </div>
        </div>
        <div className="content-card text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-caramel-100 flex items-center justify-center">
            <Clock size={24} weight="duotone" className="text-caramel-400" />
          </div>
          <div className="text-charcoal-400 text-sm font-serif mb-1">总时长</div>
          <div className="text-2xl font-serif font-bold text-charcoal-700">
            {project.scene_videos?.length ? `${project.scene_videos.length * 4}s` : '0s'}
          </div>
        </div>
        <div className="content-card text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-moss/10 flex items-center justify-center">
            <CheckCircle size={24} weight="duotone" className="text-moss" />
          </div>
          <div className="text-charcoal-400 text-sm font-serif mb-1">状态</div>
          <div className="text-2xl font-serif font-bold text-moss">完成</div>
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
          onClick={onExport}
        >
          <DownloadSimple size={18} weight="bold" />
          下载视频
        </button>
      </div>
    </div>
  )
}

export default Page6
