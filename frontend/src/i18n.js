import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import zh from './locale/zh.json'
import en from './locale/en.json'

export const APP_LANGUAGE_STORAGE_KEY = 'app_language'

export function getStoredAppLanguage() {
  try {
    const v = localStorage.getItem(APP_LANGUAGE_STORAGE_KEY)
    if (v === 'en' || v === 'zh') return v
  } catch {
    /* ignore */
  }
  return 'zh'
}

export function setStoredAppLanguage(lng) {
  const v = lng === 'en' ? 'en' : 'zh'
  try {
    localStorage.setItem(APP_LANGUAGE_STORAGE_KEY, v)
  } catch {
    /* ignore */
  }
  return v
}

i18n.use(initReactI18next).init({
  resources: {
    zh: { translation: zh },
    en: { translation: en },
  },
  lng: getStoredAppLanguage(),
  fallbackLng: 'zh',
  interpolation: { escapeValue: false },
})

export default i18n
