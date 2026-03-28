import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../context/AuthContext'

function LoginPage() {
  const { t } = useTranslation()
  const { login, authenticated, loading: authLoading, useSupabaseAuth } = useAuth()
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
      setError(useSupabaseAuth ? t('login.errorCredentials') : t('login.errorCredentialsLocal'))
      return
    }
    setSubmitting(true)
    try {
      const result = await login(username.trim(), password)
      if (result.success) {
        navigate(from, { replace: true })
      } else {
        setError(result.error || t('login.errorFailed'))
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('login.errorFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-[50vh] w-full flex items-center justify-center">
        <div className="phantom-section-inner text-charcoal-500 text-sm text-center py-16">
          {t('login.loading')}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] w-full">
      <div className="phantom-section-inner py-16 flex items-center justify-center min-h-[calc(100vh-4rem)]">
        <div className="w-full max-w-md">
          <div className="content-card p-8 md:p-10 shadow-soft">
            <h1
              className="text-2xl font-semibold text-charcoal-800 mb-2 text-center"
              style={{ fontFamily: "'Noto Serif SC', serif" }}
            >
              {t('login.title')}
            </h1>
            <p className="text-sm text-charcoal-500 text-center mb-8">
              {useSupabaseAuth ? t('login.subtitleSupabase') : t('login.subtitleLocal')}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-charcoal-600 mb-1.5">
                  {useSupabaseAuth ? t('login.email') : t('login.username')}
                </label>
                <input
                  id="username"
                  type={useSupabaseAuth ? 'email' : 'text'}
                  autoComplete={useSupabaseAuth ? 'email' : 'username'}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-field"
                  placeholder={useSupabaseAuth ? t('login.placeholderEmail') : t('login.placeholderUser')}
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-charcoal-600 mb-1.5">
                  {t('login.password')}
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  placeholder={useSupabaseAuth ? '' : t('login.placeholderPass')}
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-100 text-red-600 text-sm text-center">
                  {error}
                </div>
              )}

              <button type="submit" disabled={submitting} className="btn-primary w-full justify-center py-3.5">
                {submitting ? t('login.submitting') : t('login.submit')}
              </button>
            </form>

            <p className="mt-8 text-center text-sm text-charcoal-500">
              <Link to="/" className="text-moss hover:underline">
                {t('login.backHome')}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
