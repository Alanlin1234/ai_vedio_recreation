import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight, UploadSimple, Sparkle, FilmStrip, Warning } from '@phosphor-icons/react'

const githubUrl = import.meta.env.VITE_PROJECT_GITHUB_URL?.trim()
const paperUrl = import.meta.env.VITE_PROJECT_PAPER_URL?.trim()

function LandingPage() {
  const { t } = useTranslation()
  return (
    <>
      <div className="phantom-hero relative overflow-hidden">
        <div className="phantom-section-inner pt-16 pb-12 md:pt-20 md:pb-16">
          <div className="max-w-3xl mx-auto text-center">
            <h1
              className="text-4xl md:text-6xl font-bold text-[var(--phantom-hero-text)] mb-4"
              style={{ fontFamily: "'Noto Serif SC', serif" }}
            >
              {t('landing.brand')}
            </h1>
            <p className="phantom-hero-subtitle">
              Agentic Video Narration Pipeline — multi-agent understanding, story adaptation, storyboard and scene
              generation with consistency checks.
            </p>
            <p className="text-lg text-[var(--phantom-hero-muted)] mb-6">{t('landing.tagline')}</p>
            {(githubUrl || paperUrl) && (
              <div className="phantom-link-row">
                {paperUrl ? (
                  <a className="phantom-link-external" href={paperUrl} target="_blank" rel="noreferrer">
                    {t('landing.research')}
                  </a>
                ) : null}
                {githubUrl ? (
                  <a className="phantom-link-external" href={githubUrl} target="_blank" rel="noreferrer">
                    GitHub
                  </a>
                ) : null}
              </div>
            )}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/login"
                state={{ from: '/workspace' }}
                className="btn-hero-primary inline-flex items-center justify-center gap-2"
              >
                {t('landing.ctaLogin')}
                <ArrowRight size={18} weight="bold" />
              </Link>
              <Link to="/workspace" className="btn-hero-ghost inline-flex items-center justify-center">
                {t('landing.ctaWorkspace')}
              </Link>
            </div>
          </div>
        </div>
      </div>

      <section className="phantom-section phantom-section-light">
        <div className="phantom-section-inner">
          <h2 className="phantom-heading">{t('landing.flowTitle')}</h2>
          <p className="phantom-lead">{t('landing.flowIntro')}</p>
          <div className="phantom-card-grid">
            <div className="phantom-feature-card">
              <UploadSimple size={22} className="text-moss mb-2" weight="duotone" aria-hidden />
              <h3>{t('landing.flow1h')}</h3>
              <p>{t('landing.flow1p')}</p>
            </div>
            <div className="phantom-feature-card">
              <Sparkle size={22} className="text-moss mb-2" weight="duotone" aria-hidden />
              <h3>{t('landing.flow2h')}</h3>
              <p>{t('landing.flow2p')}</p>
            </div>
            <div className="phantom-feature-card">
              <FilmStrip size={22} className="text-moss mb-2" weight="duotone" aria-hidden />
              <h3>{t('landing.flow3h')}</h3>
              <p>{t('landing.flow3p')}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="phantom-section phantom-section-dark">
        <div className="phantom-section-inner">
          <h2 className="phantom-heading">{t('landing.agentsTitle')}</h2>
          <p className="phantom-lead">{t('landing.agentsIntro')}</p>
          <div className="phantom-card-grid">
            <div className="phantom-feature-card">
              <h3>{t('landing.agent1h')}</h3>
              <p>{t('landing.agent1p')}</p>
            </div>
            <div className="phantom-feature-card">
              <h3>{t('landing.agent2h')}</h3>
              <p>{t('landing.agent2p')}</p>
            </div>
            <div className="phantom-feature-card">
              <h3>{t('landing.agent3h')}</h3>
              <p>{t('landing.agent3p')}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="phantom-section phantom-section-light">
        <div className="phantom-section-inner">
          <h2 className="phantom-heading">{t('landing.tipsTitle')}</h2>
          <p className="phantom-lead">{t('landing.tipsIntro')}</p>
          <div className="phantom-feature-card max-w-2xl flex gap-3 items-start">
            <Warning size={22} className="text-warm flex-shrink-0 mt-0.5" weight="duotone" aria-hidden />
            <div>
              <h3>{t('landing.tips1h')}</h3>
              <p>{t('landing.tips1p')}</p>
            </div>
          </div>
        </div>
      </section>

      <footer className="phantom-footer">
        <div className="phantom-footer-inner">
          <h2>{t('landing.noteTitle')}</h2>
          <p>
            {t('landing.noteBody')}{' '}
            <code className="mono text-xs bg-paper-200 px-1 py-0.5 rounded">{t('landing.noteApi')}</code>
            {t('landing.noteBody2')}
          </p>
          <p className="text-charcoal-400">{t('landing.footer')}</p>
        </div>
      </footer>
    </>
  )
}

export default LandingPage
