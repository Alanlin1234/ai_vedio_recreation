import { Link, useLocation } from 'react-router-dom'
import { VideoCamera, SignIn, SignOut } from '@phosphor-icons/react'
import { useAuth } from '../context/AuthContext'

function Navbar() {
  const location = useLocation()
  const { user, authenticated, logout, loading } = useAuth()
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
            影坊
          </span>
        </Link>

        <div className="flex items-center gap-4 md:gap-6">
          <Link
            to="/"
            className={`${isHome ? 'nav-link-dark' : 'nav-link'} ${isActive('/') ? 'active' : ''}`}
          >
            首页
          </Link>
          <Link
            to="/workspace"
            className={`${isHome ? 'nav-link-dark' : 'nav-link'} ${
              isActive('/workspace') ? 'active' : ''
            }`}
          >
            工作台
          </Link>
          <Link
            to="/history"
            className={`${isHome ? 'nav-link-dark' : 'nav-link'} ${
              isActive('/history') ? 'active' : ''
            }`}
          >
            历史
          </Link>

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
                    {user?.username}
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
                    <span className="hidden sm:inline">退出</span>
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
                  登录
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
