import React from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, DownloadSimple, CheckCircle, FilmSlate, Clock, Check } from '@phosphor-icons/react'

const Page6 = ({ project, onBack, onExport }) => {
  const { t } = useTranslation()
  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-serif font-bold text-charcoal-700 mb-2">{t('page6.title')}</h2>
        <p className="text-charcoal-500 font-serif">
          {project.final_video ? t('page6.subtitleReady') : t('page6.subtitleLoading')}
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
                <p className="font-serif">{t('page6.videoLoading')}</p>
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
          <div className="text-charcoal-400 text-sm font-serif mb-1">{t('page6.sceneCount')}</div>
          <div className="text-2xl font-serif font-bold text-charcoal-700">
            {project.scene_videos?.length || 0}
          </div>
        </div>
        <div className="content-card text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-caramel-100 flex items-center justify-center">
            <Clock size={24} weight="duotone" className="text-caramel-400" />
          </div>
          <div className="text-charcoal-400 text-sm font-serif mb-1">{t('page6.duration')}</div>
          <div className="text-2xl font-serif font-bold text-charcoal-700">
            {project.scene_videos?.length ? `${project.scene_videos.length * 4}s` : '0s'}
          </div>
        </div>
        <div className="content-card text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-moss/10 flex items-center justify-center">
            <CheckCircle size={24} weight="duotone" className="text-moss" />
          </div>
          <div className="text-charcoal-400 text-sm font-serif mb-1">{t('page6.status')}</div>
          <div className="text-2xl font-serif font-bold text-moss">{t('page6.statusDone')}</div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          className="btn-secondary flex items-center gap-2"
          onClick={onBack}
        >
          <ArrowLeft size={18} />
          {t('page6.back')}
        </button>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={onExport}
        >
          <DownloadSimple size={18} weight="bold" />
          {t('page6.download')}
        </button>
      </div>
    </div>
  )
}

export default Page6
