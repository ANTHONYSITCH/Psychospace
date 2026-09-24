import { test } from 'node:test'
import assert from 'node:assert/strict'
import { latest, percent, number, rhythmText } from '../src/overview.js'

test('latest event uses UTC time including microseconds, then id, not input order', () => {
  const records = [
    { id: 'Z', detected_at: '2080-04-15T18:00:00.000001Z' },
    { id: 'A', detected_at: '2080-04-15T18:00:00.000001Z' },
    { id: 'OLDER', detected_at: '2080-04-15T18:00:00Z' },
  ]
  assert.equal(latest(records, 'detected_at').id, 'Z')
  assert.equal(latest([], 'detected_at'), null)
})
test('scores are percentages, missing values never look like zero', () => {
  assert.equal(percent(0.62), '62 %')
  assert.equal(percent(null), '—')
  assert.equal(number(null), '—')
  assert.equal(number(7.342857), '7,34')
})
test('absence of drift is not presented as an assessment of stability', () => {
  assert.equal(rhythmText(null), 'Un moment pour retrouver ton rythme.')
  assert.match(rhythmText({ level: 'moderate', status: 'open' }), /Ton rythme évolue/)
  assert.match(rhythmText({ level: 'high', status: 'resolved' }), /résolu/)
})
