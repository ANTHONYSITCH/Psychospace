export const dimensions = [
  { key: 'sleep_hours', baseline: 'sleep_hours_avg', label: 'Sommeil', unit: 'h' },
  { key: 'mood', baseline: 'mood_avg', label: 'Humeur', unit: '/ 10' },
  { key: 'stress', baseline: 'stress_avg', label: 'Stress', unit: '/ 10' },
  { key: 'fatigue', baseline: 'fatigue_avg', label: 'Fatigue', unit: '/ 10' },
  { key: 'energy', baseline: 'energy_avg', label: 'Énergie', unit: '/ 10' },
  { key: 'social_level', baseline: 'social_level_avg', label: 'Vie sociale', unit: '/ 10' },
  { key: 'activity_minutes', baseline: 'activity_minutes_avg', label: 'Activité', unit: 'min' },
]

// API UTC timestamps keep their microseconds, including at the detection boundary.
function instant(value) {
  if (typeof value !== 'string' || !Number.isFinite(Date.parse(value))) return null
  const match = value.match(/^(.*T\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?Z$/)
  return match ? `${match[1]}.${(match[2] || '').padEnd(6, '0')}Z` : null
}

export function detectionWindow(checkins, detectedAt) {
  const end = instant(detectedAt)
  if (!end) return []
  return checkins.filter(record => instant(record.timestamp) && instant(record.timestamp) <= end)
    .toSorted((a, b) => instant(a.timestamp).localeCompare(instant(b.timestamp)) || (a.id || '').localeCompare(b.id || ''))
    .slice(-3)
}

export function fingerprintData(checkins, baseline, drift) {
  const records = detectionWindow(checkins, drift?.detected_at)
  const values = dimensions.map(dimension => {
    const original = records.map(record => record[dimension.key])
    return { ...dimension, usual: baseline?.[dimension.baseline],
      recent: records.length === 3 && original.every(Number.isFinite) ? original.reduce((a, b) => a + b, 0) / 3 : null,
      affected: (drift?.affected_signals || []).includes(dimension.key) }
  })
  return { records, values, ready: records.length === 3 && values.every(value => Number.isFinite(value.usual) && value.usual > 0 && Number.isFinite(value.recent)) }
}

// Rendering only: a bounded displacement prevents large ratios from clipping.
// Higher values always expand; no inversion or health interpretation.
export function visualRatio(value, reference) {
  return 1 + .48 * Math.tanh((value - reference) / reference)
}

export function contourPoints(values, progress = 0) {
  const silhouette = [1.03, .92, 1.07, .97, 1.04, .94, 1.08]
  return values.map((value, index) => {
    const angle = -Math.PI / 2 + index * Math.PI * 2 / values.length
    const radius = 157 * silhouette[index] * (1 + progress * (visualRatio(value.recent, value.usual) - 1))
    return { x: 300 + Math.cos(angle) * radius, y: 280 + Math.sin(angle) * radius }
  })
}

export function organicPath(points) {
  const point = index => points[(index + points.length) % points.length]
  return points.map((current, index) => {
    const previous = point(index - 1), next = point(index + 1), after = point(index + 2)
    return `${index === 0 ? `M${current.x},${current.y} ` : ''}C${current.x + (next.x - previous.x) / 6},${current.y + (next.y - previous.y) / 6} ${next.x - (after.x - current.x) / 6},${next.y - (after.y - current.y) / 6} ${next.x},${next.y}`
  }).join(' ') + 'Z'
}

export function dimensionDescription(value) {
  if (value.recent === value.usual) return 'Ce repère était au même niveau que d’habitude au moment de la détection.'
  const direction = value.recent > value.usual ? 'plus élevé' : 'plus bas'
  return `Ce repère était ${direction} que d’habitude au moment où PsychoSpace a remarqué cette évolution.`
}
