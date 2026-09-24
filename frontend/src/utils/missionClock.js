import { MISSION_CLOCK } from '../config.js'

/** Demo mission time uses the machine's local time of day on a fixed mission date.
 * The resulting mission clock is serialized as UTC, independently of Earth offsets.
 * Real mode returns the unmodified instant. Read the clock for every submission.
 */
export function missionTimestamp(now = new Date(), settings = MISSION_CLOCK) {
  if (!Number.isFinite(now.getTime())) throw new Error('Invalid clock')
  if (settings.mode === 'real') return now.toISOString()
  if (settings.mode !== 'demo') throw new Error('Invalid mission clock mode')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(settings.demoDate)) throw new Error('Invalid mission date')
  const mission = new Date(`${settings.demoDate}T00:00:00.000Z`)
  if (!Number.isFinite(mission.getTime()) || mission.toISOString().slice(0, 10) !== settings.demoDate) {
    throw new Error('Invalid mission date')
  }
  mission.setUTCHours(now.getHours(), now.getMinutes(), now.getSeconds(), now.getMilliseconds())
  return mission.toISOString()
}
