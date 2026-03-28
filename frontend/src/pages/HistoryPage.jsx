import { useTranslation } from 'react-i18next'

function HistoryPage() {
  const { t } = useTranslation()
  return (
    <div className="phantom-section-inner py-16">
      <h2 className="phantom-heading mb-4" style={{ fontFamily: "'Noto Serif SC', serif" }}>
        {t('history.title')}
      </h2>
      <p className="text-charcoal-500 text-sm leading-relaxed">{t('history.body')}</p>
    </div>
  )
}

export default HistoryPage
