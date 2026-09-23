import { API_PREFIX, DEMO_USER_ID } from './config'
import { missionTimestamp } from './utils/missionClock.js'

async function get(resource, signal, empty) {
  const response = await fetch(`${API_PREFIX}/${resource}/${encodeURIComponent(DEMO_USER_ID)}`, { signal, headers: { Accept: 'application/json' } })
  if (response.status === 404) return empty
  if (!response.ok) throw new Error('Core unavailable')
  return response.json()
}

export async function loadOverview(signal) {
  const [profile, baseline, drift, checkins] = await Promise.all([
    get('profile', signal, null), get('baseline', signal, null),
    get('drift', signal, []), get('checkins', signal, []),
  ])
  if ((profile && typeof profile.first_name !== 'string') || !Array.isArray(drift) || !Array.isArray(checkins)
      || (baseline && typeof baseline !== 'object')) throw new Error('Invalid overview')
  return { profile, baseline, drift, checkins }
}

export function loadProfile(signal) { return get('profile', signal, null) }

export async function submitCheckin(answers) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30000)
  try {
    const response = await fetch(`${API_PREFIX}/checkins`, {
      method: 'POST', signal: controller.signal,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ ...answers, user_id: DEMO_USER_ID, timestamp: missionTimestamp() }),
    })
    if (response.status !== 201) throw new Error('Save failed')
    const result = await response.json()
    if (result.success !== true || !Number.isInteger(result.checkin_id)) throw new Error('Invalid receipt')
    return result
  } finally { clearTimeout(timer) }
}
