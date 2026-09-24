import { test } from 'node:test'
import assert from 'node:assert/strict'
import { dailyRecords, visualDeviation, rhythmMetrics, metricValue, recentSummary, timeline, tracePath } from '../src/evolution.js'

test('daily records preserve originals and select the last microsecond chronologically', () => {
  const records = [{ timestamp: '2080-04-16T10:00:00.000002Z', sleep_hours: 5.8 }, { timestamp: '2026-09-23T10:00:00Z' }, { timestamp: '2080-04-16T10:00:00.000001Z', sleep_hours: 7 }]
  const before = structuredClone(records)
  const days = dailyRecords(records)
  assert.deepEqual(days.map(day => day.day), ['2026-09-23', '2080-04-16'])
  assert.equal(days[1].count, 2)
  assert.equal(days[1].record, records[0])
  assert.deepEqual(records, before)
})

test('visual normalization keeps real units and handles absent or zero reference', () => {
  assert.equal(visualDeviation(6, 8), -.25)
  assert.equal(visualDeviation(6, 0), null)
  assert.equal(visualDeviation(null, 8), null)
  assert.equal(metricValue(rhythmMetrics[0], 5.8), '5 h 48')
  assert.equal(metricValue(rhythmMetrics[1], 4), '4 / 10')
  assert.equal(metricValue(rhythmMetrics[3], 37), '37 min')
})

test('timeline uses actual elapsed time and leaves missing days unconnected', () => {
  const days = dailyRecords([1, 2, 4].map(day => ({ timestamp: `2080-04-0${day}T12:00:00Z`, energy: 6 })))
  const baseline = { energy_avg: 8 }
  const coordinates = timeline(days, baseline, 840)
  const first = coordinates.x(days[0].record.timestamp), second = coordinates.x(days[1].record.timestamp), last = coordinates.x(days[2].record.timestamp)
  assert.equal(last - second, 2 * (second - first))
  assert.deepEqual(tracePath(days, rhythmMetrics[1], baseline, coordinates).match(/[ML]/g), ['M', 'L', 'M'])
})

test('recent description only states comparisons shared by available records', () => {
  const days = [{ record: { sleep_hours: 6, energy: 4 } }, { record: { sleep_hours: 5.8, energy: 9 } }]
  const summary = recentSummary(days, { sleep_hours_avg: 7.34, energy_avg: 8, fatigue_avg: 3 })
  assert.match(summary, /ton sommeil est plus court/)
  assert.doesNotMatch(summary, /énergie|fatigue/)
  assert.match(recentSummary(days, null), /pas encore disponible/)
})
