import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { VideoCamera, SignIn, SignOut } from '@phosphor-icons/react'
import { useAuth } from '../context/AuthContext'
import { setStoredAppLanguage } from '../i18n'

function Navbar() {
  const { t, i18n } = useTranslation()
  const location = useLocation()
  const { user, authenticated, logout, loading } = useAuth()

  const onLanguageChange = (e) => {
    const lng = setStoredAppLanguage(e.target.value)
    i18n.changeLanguage(lng)
  }
  const isHome = location.pathname === '/'

  const isActive = (path) => location.pathname === path

  const handleLogout = async () => {
    await logout()
  }

  return (
    <nav
      className={`sticky top-0 z-50 transition-colors duration-300 ${
        isHome
          ? 'bg-black/20 backdrop-blur-md border-b border-white/10'
          : 'bg-white/85 backdrop-blur-md border-b border-gray-100'
      }`}
    >
      <div className="w-full px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105 ${
              isHome ? 'bg-white/15 ring-1 ring-white/20' : 'bg-moss'
            }`}
          >
            <VideoCamera size={20} weight="duotone" className="text-white" />
          </div>
          <span
            className={`text-xl font-semibold tracking-tight ${
              isHome ? 'text-white' : 'text-charcoal-800'
            }`}
            style={{ fontFamily: "'Noto Serif SC', serif" }}
          >
            {t('nav.brand')}
          </span>
        </Link>

        <div className="flex items-center gap-4 md:gap-6">
          <Link
            to="/"
            className={`${isHome ? 'nav-link-dark' : 'nav-link'} ${isActive('/') ? 'active' : ''}`}
          >
            {t('nav.home')}
          </Link>
          <Link
            to="/workspace"
            className={`${isHome ? 'nav-link-dark' : 'nav-link'} ${
              isActive('/workspace') ? 'active' : ''
            }`}
          >
            {t('nav.workspace')}
          </Link>
          <Link
            to="/history"
            className={`${isHome ? 'nav-link-dark' : 'nav-link'} ${
              isActive('/history') ? 'active' : ''
            }`}
          >
            {t('nav.history')}
          </Link>

          <label
            className={`flex items-center gap-1.5 text-sm font-medium font-sans ${
              isHome ? 'text-white/90' : 'text-charcoal-600'
            }`}
          >
            <span className="sr-only md:not-sr-only md:inline">{t('nav.language')}</span>
            <select
              value={i18n.language?.startsWith('en') ? 'en' : 'zh'}
              onChange={onLanguageChange}
              aria-label={t('nav.language')}
              className={`rounded-lg border px-2 py-1 text-sm font-sans outline-none focus:ring-2 focus:ring-moss/40 ${
                isHome
                  ? 'bg-white/10 border-white/25 text-white'
                  : 'bg-white border-charcoal-200 text-charcoal-800'
              }`}
            >
              <option value="zh">{t('nav.langZh')}</option>
              <option value="en">{t('nav.langEn')}</option>
            </select>
          </label>

          {!loading && (
            <>
              {authenticated ? (
                <div
                  className={`flex items-center gap-3 pl-2 border-l ${
                    isHome ? 'border-white/20' : 'border-charcoal-200'
                  }`}
                >
                  <span
                    className={`text-sm max-w-[100px] truncate hidden sm:inline ${
                      isHome ? 'text-white/90' : 'text-charcoal-600'
                    }`}
                  >
                    {user?.username || user?.email}
                  </span>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className={`inline-flex items-center gap-1.5 text-sm font-medium font-sans ${
                      isHome
                        ? 'text-white/85 hover:text-white'
                        : 'text-charcoal-500 hover:text-moss'
                    }`}
                  >
                    <SignOut size={18} />
                    <span className="hidden sm:inline">{t('nav.logout')}</span>
                  </button>
                </div>
              ) : (
                <Link
                  to="/login"
                  state={{ from: location.pathname }}
                  className={`inline-flex items-center gap-1.5 text-sm font-semibold font-sans ${
                    isHome ? 'btn-hero-ghost py-2 px-3' : 'text-moss hover:underline'
                  }`}
                >
                  <SignIn size={18} />
                  {t('nav.login')}
                </Link>
              )}
            </>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
