import { latest, metricDefinitions, number } from './overview.js'

export const rhythmMetrics = metricDefinitions.map((metric, index) => ({
  ...metric, color: ['#c4d6b6', '#8ab6c6', '#d7b793', '#b1a2ca'][index],
  dash: ['', '8 5', '2 5', '12 4 2 4'][index],
}))

export function dailyRecords(checkins) {
  const grouped = new Map()
  for (const record of checkins) {
    if (!Number.isFinite(Date.parse(record.timestamp))) continue
    const day = record.timestamp.slice(0, 10)
    grouped.set(day, [...(grouped.get(day) || []), record])
  }
  return [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b))
    .map(([day, records]) => ({ day, count: records.length, record: latest(records, 'timestamp') }))
    .filter(item => item.record)
}

// Only the SVG uses this ratio. It is not a drift score or a detection rule.
export function visualDeviation(value, reference) {
  return Number.isFinite(value) && Number.isFinite(reference) && reference > 0 ? (value - reference) / reference : null
}

export function fullDate(value) {
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(value))
}
export function monthLabel(month) {
  return new Intl.DateTimeFormat('fr-FR', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${month}-01T00:00:00Z`))
}
export function metricValue(metric, value) {
  if (!Number.isFinite(value)) return 'Non renseigné'
  if (metric.key === 'sleep_hours') {
    const minutes = Math.round(value * 60)
    return `${Math.floor(minutes / 60)} h${minutes % 60 ? ` ${String(minutes % 60).padStart(2, '0')}` : ''}`
  }
  return `${number(value)} ${metric.unit}`
}

export function recentSummary(days, baseline) {
  if (!baseline) return 'Ta référence personnelle n’est pas encore disponible. Tes bilans restent consultables.'
  const recent = days.slice(-3)
  if (!recent.length) return 'Tes prochains bilans permettront de retrouver tes repères.'
  const descriptions = {
    sleep_hours: ['ton sommeil est plus court', 'ton sommeil est plus long'],
    energy: ['ton énergie est plus basse', 'ton énergie est plus élevée'],
    fatigue: ['ta fatigue est plus basse', 'ta fatigue est plus élevée'],
    activity_minutes: ['ton activité est plus courte', 'ton activité est plus longue'],
  }
  const changes = rhythmMetrics.flatMap(metric => {
    const usual = baseline[metric.baseline]
    if (!Number.isFinite(usual) || !recent.every(day => Number.isFinite(day.record[metric.key]))) return []
    const values = recent.map(day => day.record[metric.key])
    const side = values.every(value => value < usual) ? 0 : values.every(value => value > usual) ? 1 : -1
    return side === -1 ? [] : [descriptions[metric.key][side]]
  })
  if (!changes.length) return 'Tes bilans varient selon les jours. Tu peux les comparer à tes repères habituels.'
  const count = recent.length
  return `${count === 1 ? 'Sur le dernier jour renseigné' : `Sur les ${count} derniers jours renseignés`}, ${changes.join(', ')} que d’habitude.`
}

export function timeline(days, baseline, width) {
  const start = Date.parse(`${days[0].day}T00:00:00Z`)
  const end = Date.parse(`${days.at(-1).day}T00:00:00Z`) + 86400000
  const x = value => 55 + (Date.parse(value) - start) / (end - start) * (width - 110)
  const deviations = days.flatMap(day => rhythmMetrics.map(metric => visualDeviation(day.record[metric.key], baseline?.[metric.baseline]))).filter(value => value !== null)
  const extent = Math.max(0.25, ...deviations.map(Math.abs))
  const y = value => 180 - value / extent * 112
  return { x, y, start, end }
}

export function tracePath(days, metric, baseline, coordinates) {
  let previousDay = null
  return days.map(day => {
    const deviation = visualDeviation(day.record[metric.key], baseline?.[metric.baseline])
    if (deviation === null) { previousDay = null; return '' }
    const continuous = previousDay && Date.parse(day.day) - Date.parse(previousDay) === 86400000
    previousDay = day.day
    return `${continuous ? 'L' : 'M'}${coordinates.x(day.record.timestamp)},${coordinates.y(deviation)}`
  }).join(' ')
}
