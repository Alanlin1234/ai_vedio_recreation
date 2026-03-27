import { Link } from 'react-router-dom'
import { ArrowRight } from '@phosphor-icons/react'

function LandingPage() {
  return (
    <div className="phantom-hero relative overflow-hidden">
      <div className="phantom-section-inner pt-16 pb-24 md:pt-20 md:pb-32">
        <div className="max-w-3xl mx-auto text-center">
          <h1
            className="text-4xl md:text-6xl font-bold text-[var(--phantom-hero-text)] mb-4"
            style={{ fontFamily: "'Noto Serif SC', serif" }}
          >
            影坊
          </h1>
          <p className="text-lg text-[var(--phantom-hero-muted)] mb-10">
            多智能体视频叙事创作 · 登录后进入工作台开始项目
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/login" state={{ from: '/workspace' }} className="btn-hero-primary inline-flex items-center justify-center gap-2">
              登录并开始
              <ArrowRight size={18} weight="bold" />
            </Link>
            <Link to="/workspace" className="btn-hero-ghost inline-flex items-center justify-center">
              前往工作台
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LandingPage
