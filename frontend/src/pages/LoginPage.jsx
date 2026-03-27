import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function LoginPage() {
  const { login, authenticated, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from || '/workspace'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (authenticated) {
      navigate(from, { replace: true })
    }
  }, [authenticated, navigate, from])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!username.trim() || !password) {
      setError('请输入用户名和密码')
      return
    }
    setSubmitting(true)
    try {
      const result = await login(username.trim(), password)
      if (result.success) {
        navigate(from, { replace: true })
      } else {
        setError(result.error || '登录失败')
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || '登录失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center text-charcoal-500 text-sm">
        加载中…
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-md">
        <div className="content-card p-8 md:p-10 shadow-soft">
          <h1
            className="text-2xl font-semibold text-charcoal-800 mb-2 text-center"
            style={{ fontFamily: "'Noto Serif SC', serif" }}
          >
            登录影坊
          </h1>
          <p className="text-sm text-charcoal-500 text-center mb-8">
            使用账号访问工作台与历史记录
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-charcoal-600 mb-1.5">
                用户名
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input-field"
                placeholder="默认 admin"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-charcoal-600 mb-1.5">
                密码
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field"
                placeholder="默认 admin123"
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-100 text-red-600 text-sm text-center">
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting} className="btn-primary w-full justify-center py-3.5">
              {submitting ? '登录中…' : '登录'}
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-charcoal-500">
            <Link to="/" className="text-moss hover:underline">
              返回首页
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
