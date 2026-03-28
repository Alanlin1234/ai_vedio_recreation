import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { login as apiLogin, logout as apiLogout, fetchMe } from '../utils/api'
import { isSupabaseAuthConfigured, supabase } from '../lib/supabaseClient'
import i18n from '../i18n'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      if (isSupabaseAuthConfigured()) {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) {
          setUser(null)
          return
        }
      }
      const data = await fetchMe()
      if (data.authenticated && data.user) {
        setUser(data.user)
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    if (!isSupabaseAuthConfigured()) return undefined
    const { data: sub } = supabase.auth.onAuthStateChange(() => {
      refresh()
    })
    return () => sub.subscription.unsubscribe()
  }, [refresh])

  const login = useCallback(async (usernameOrEmail, password) => {
    if (isSupabaseAuthConfigured()) {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: (usernameOrEmail || '').trim(),
        password,
      })
      if (error) {
        return { success: false, error: error.message || i18n.t('login.errorFailed') }
      }
      if (data.session) {
        const me = await fetchMe()
        if (me.authenticated && me.user) {
          setUser(me.user)
          return { success: true }
        }
      }
      return { success: false, error: i18n.t('login.errorFailed') }
    }
    const data = await apiLogin(usernameOrEmail, password)
    if (data.success && data.user) {
      setUser(data.user)
      return { success: true }
    }
    return { success: false, error: data.error || i18n.t('login.errorFailed') }
  }, [])

  const logout = useCallback(async () => {
    try {
      if (isSupabaseAuthConfigured()) {
        await supabase.auth.signOut()
      } else {
        await apiLogout()
      }
    } finally {
      setUser(null)
    }
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      authenticated: !!user,
      login,
      logout,
      refresh,
      useSupabaseAuth: isSupabaseAuthConfigured(),
    }),
    [user, loading, login, logout, refresh]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
