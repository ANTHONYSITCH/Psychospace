import { API_PREFIX, DEMO_USER_ID } from './config'

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
