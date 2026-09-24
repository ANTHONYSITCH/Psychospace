import { test } from 'node:test'
import assert from 'node:assert/strict'
import { detectionWindow, fingerprintData, dimensions, contourPoints, visualRatio, organicPath } from '../src/fingerprint.js'

test('window excludes future values including a single microsecond and sorts without mutation', () => {
  const rows = [4, 1, 3, 2, 0].map(n => ({ id: String(n), timestamp: `2080-04-15T18:05:00.00000${n}Z` }))
  const copy = structuredClone(rows)
  assert.deepEqual(detectionWindow(rows, '2080-04-15T18:05:00.000003Z').map(row => row.id), ['1', '2', '3'])
  assert.deepEqual(rows, copy)
  assert.deepEqual(detectionWindow(rows, 'invalid'), [])
})

test('three original records form the average; graphics never mutate original units or affected signals', () => {
  const rows = [13, 14, 15, 16].map(day => Object.fromEntries([['timestamp', `2080-04-${day}T18:00:00Z`], ...dimensions.map(d => [d.key, day === 16 ? 99 : 6])]))
  const baseline = Object.fromEntries(dimensions.map(d => [d.baseline, 8]))
  const drift = { detected_at: '2080-04-15T18:05:00Z', affected_signals: ['fatigue'] }
  const before = structuredClone({ rows, baseline, drift })
  const data = fingerprintData(rows, baseline, drift)
  assert.equal(data.ready, true)
  assert.ok(data.values.every(value => value.recent === 6 && value.usual === 8))
  assert.deepEqual(data.values.filter(value => value.affected).map(value => value.key), ['fatigue'])
  assert.notEqual(organicPath(contourPoints(data.values)), organicPath(contourPoints(data.values, 1)))
  assert.deepEqual({ rows, baseline, drift }, before)
  assert.equal(visualRatio(8, 8), 1)
  assert.ok(visualRatio(9, 8) > 1)
  assert.ok(visualRatio(7, 8) < 1)
  assert.equal(fingerprintData(rows.slice(0, 2), baseline, drift).ready, false)
  assert.equal(fingerprintData(rows, { ...baseline, energy_avg: 0 }, drift).ready, false)
})
