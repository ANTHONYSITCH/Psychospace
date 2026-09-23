import { test } from 'node:test'
import assert from 'node:assert/strict'
import { interventionLabel, interventionState, relevantIntervention, interventionHistory } from '../src/care.js'

test('types and the three backend states have human labels', () => {
  assert.equal(interventionLabel('physical_activity'), 'Une courte activité')
  assert.equal(interventionLabel('quiet_time'), 'Un moment au calme')
  assert.equal(interventionLabel('unknown_type'), 'Une proposition PsychoSpace')
  assert.equal(interventionState({ accepted: false, completed: false }), 'Proposition')
  assert.equal(interventionState({ accepted: true, completed: false }), 'En cours')
  assert.equal(interventionState({ accepted: true, completed: true }), 'Terminé')
})
test('active moment takes priority, then latest proposal; history respects microseconds', () => {
  const rows = [
    { id: 'a', created_at: '2080-04-15T18:00:00.000001Z', accepted: true, completed: false },
    { id: 'b', created_at: '2080-04-15T18:00:00.000002Z', accepted: false, completed: false },
    { id: 'c', created_at: '2080-04-16T18:00:00Z', accepted: true, completed: true },
  ]
  const copy = structuredClone(rows)
  assert.equal(relevantIntervention(rows).id, 'a')
  assert.equal(relevantIntervention(rows.slice(1)).id, 'b')
  assert.deepEqual(interventionHistory(rows).map(item => item.id), ['c', 'b', 'a'])
  assert.deepEqual(rows, copy)
  assert.equal(relevantIntervention([]), null)
})
