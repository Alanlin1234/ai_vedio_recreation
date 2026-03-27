/**
 * 将教育意义统一成可读的短文案（兼容接口误返回嵌套对象）。
 */
export function pickEducationalSummary(raw) {
  if (raw == null || raw === '') return ''
  if (typeof raw === 'object' && !Array.isArray(raw)) {
    const inner =
      raw.educational && typeof raw.educational === 'object'
        ? raw.educational
        : raw
    const line =
      (typeof inner.overall_educational_value === 'string' && inner.overall_educational_value) ||
      (typeof raw.summary === 'string' && raw.summary) ||
      ''
    return line.trim().slice(0, 200)
  }
  const s = String(raw).trim()
  return s.slice(0, 200)
}
