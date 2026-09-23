import { test } from 'node:test'
import assert from 'node:assert/strict'
import { missionTimestamp } from '../src/utils/missionClock.js'
import { MISSION_CLOCK } from '../src/config.js'
import { latest } from '../src/overview.js'

test('default demo date is April 16, 2080 and the timestamp is valid UTC ISO', () => {
  const timestamp = missionTimestamp(new Date(2026, 8, 23, 14, 35, 12, 345))
  assert.equal(timestamp, '2080-04-16T14:35:12.345Z')
  assert.equal(new Date(timestamp).toISOString(), timestamp)
  assert.equal(timestamp.slice(0, 10), MISSION_CLOCK.demoDate)
})
test('time advances between calls, including seconds and milliseconds', () => {
  const first = new Date(2026, 8, 23, 14, 35, 0, 100)
  const second = new Date(first.getTime() + 61750)
  assert.equal(Date.parse(missionTimestamp(second)) - Date.parse(missionTimestamp(first)), 61750)
})
test('demo date stays fixed at local midnight and near the end of the day', () => {
  for (const hour of [0, 23]) {
    assert.equal(missionTimestamp(new Date(2026, 8, 23, hour, 59)).slice(0, 10), '2080-04-16')
  }
})
test('real mode preserves existing 2026 timestamps and their exact instant', () => {
  const now = new Date('2026-09-23T13:34:14.366Z')
  assert.equal(missionTimestamp(now, { mode: 'real' }), '2026-09-23T13:34:14.366Z')
})
test('date is configurable and invalid settings never silently fall back to real time', () => {
  assert.match(missionTimestamp(new Date(), { mode: 'demo', demoDate: '2080-04-17' }), /^2080-04-17T/)
  for (const demoDate of ['2080-02-30', '2080-13-01', 'not-a-date']) {
    assert.throws(() => missionTimestamp(new Date(), { mode: 'demo', demoDate }))
  }
  assert.throws(() => missionTimestamp(new Date(), { mode: 'unknown' }))
})
test('overview chooses a mission check-in after April 15 and preserves older 2026 records', () => {
  const old = { timestamp: '2026-09-23T13:34:14.366Z' }
  const seed = { timestamp: '2080-04-15T18:00:00Z' }
  const current = { timestamp: missionTimestamp(new Date()) }
  const records = [current, seed, old]
  assert.equal(latest(records, 'timestamp'), current)
  assert.equal(records.length, 3)
})
