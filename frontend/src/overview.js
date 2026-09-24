// Preserve microsecond ordering rather than rounding the backend's dates to milliseconds.
function dateKey(value = '') {
  const match = value.match(/^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?Z$/)
  return match ? `${match[1]}.${(match[2] || '').padEnd(6, '0')}` : ''
}
export function latest(records, field) {
  return records.reduce((chosen, record) => {
    if (!dateKey(record[field])) return chosen
    if (!chosen) return record
    const a = dateKey(record[field]), b = dateKey(chosen[field])
    return a > b || (a === b && (record.id || '') >= (chosen.id || '')) ? record : chosen
  }, null)
}
export const metricDefinitions = [
  { key: 'sleep_hours', baseline: 'sleep_hours_avg', label: 'Sommeil', unit: 'h', icon: 'moon' },
  { key: 'energy', baseline: 'energy_avg', label: 'Énergie', unit: '/ 10', icon: 'sun' },
  { key: 'fatigue', baseline: 'fatigue_avg', label: 'Fatigue', unit: '/ 10', icon: 'wave' },
  { key: 'activity_minutes', baseline: 'activity_minutes_avg', label: 'Activité', unit: 'min', icon: 'activity' },
]
export function number(value) {
  return Number.isFinite(value) ? new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(value) : '—'
}
export function percent(value) {
  return Number.isFinite(value) && value >= 0 && value <= 1 ? `${Math.round(value * 100)} %` : '—'
}
export function dateLabel(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Pas encore de données'
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(value))
}
export function greeting(hour = new Date().getHours()) {
  return hour < 18 ? 'Bonjour' : 'Bonsoir'
}
export function rhythmText(drift) {
  if (!drift) return 'Un moment pour retrouver ton rythme.'
  if (drift.status === 'resolved') return 'Le dernier changement observé a été marqué comme résolu.'
  return {
    low: 'Ton rythme s’est un peu éloigné de tes habitudes.',
    moderate: 'Ton rythme évolue depuis quelques jours.',
    high: 'Ton rythme s’est davantage éloigné de tes habitudes.',
  }[drift.level] || 'Prenons un moment pour regarder ton rythme.'
}
