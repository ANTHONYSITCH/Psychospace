import { test } from 'node:test'
import assert from 'node:assert/strict'
import { steps, validAnswer, answerLabel } from '../src/checkin.js'

test('unanswered fields stay empty, scores must be whole numbers from 1 to 10', () => {
  for (const step of steps) assert.equal(validAnswer(step, undefined), false)
  for (const value of [null, NaN, Infinity, '5', 0, 11, 2.5]) assert.equal(validAnswer(steps[1], value), false)
  for (const value of [1, 10]) assert.equal(validAnswer(steps[1], value), true)
})
test('sleep supports half hours and stays within one day', () => {
  assert.equal(answerLabel(steps[0], 6.5), '6 h 30')
  for (const value of [0, 6.5, 24]) assert.equal(validAnswer(steps[0], value), true)
  for (const value of [-1, 25, 6.2]) assert.equal(validAnswer(steps[0], value), false)
})
test('activity allows precise whole minutes, not more than one day', () => {
  assert.equal(validAnswer(steps[6], 37), true)
  for (const value of [-1, 1441, 1.5]) assert.equal(validAnswer(steps[6], value), false)
})
