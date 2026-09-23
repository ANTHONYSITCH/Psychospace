export const DEMO_USER_ID = 'ASTRO-001'
// /api is forwarded to VITE_API_URL by Vite; production needs the same reverse proxy.
export const API_PREFIX = '/api'

export const MISSION_CLOCK = {
  mode: import.meta.env?.VITE_MISSION_CLOCK_MODE || 'demo',
  demoDate: import.meta.env?.VITE_MISSION_DEMO_DATE || '2080-04-16',
}
