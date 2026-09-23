import { test } from 'node:test'
import assert from 'node:assert/strict'
import { categoryLabel, sourceLabel, memoryPayload, validMemoryDraft } from '../src/memory.js'

test('human labels never expose unknown technical categories or invent provenance', () => {
  assert.equal(categoryLabel('coping_strategy'), 'Ce qui m’aide à souffler')
  assert.equal(categoryLabel('internal_category'), 'Un repère personnel')
  assert.equal(sourceLabel('user_chat'), 'Partagé pendant une conversation')
  assert.equal(sourceLabel('unknown'), 'Enregistré dans ta mémoire PsychoSpace')
})
test('contract keeps identity date and source, omits UI fields and validates scores', () => {
  const draft = { id: 'test', user_id: 'ASTRO-001', created_at: '2080-04-01T07:10:00Z', source: 'user_chat', category: 'interest', content: '  Une information  ', importance: 8, step: 3 }
  assert.deepEqual(memoryPayload(draft), { id: 'test', user_id: 'ASTRO-001', category: 'interest', content: 'Une information', importance: 8, source: 'user_chat', created_at: '2080-04-01T07:10:00Z' })
  assert.equal(validMemoryDraft(draft), true)
  for (const importance of [0, 11, 3.5, '8', null]) assert.equal(validMemoryDraft({ ...draft, importance }), false)
  assert.equal(validMemoryDraft({ ...draft, content: '  ' }), false)
})
