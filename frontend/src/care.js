import { latest } from './overview.js'

export const interventionTypes = {
  music_break: 'Un moment avec ta musique',
  short_activity: 'Une courte activité', physical_activity: 'Une courte activité',
  quiet_break: 'Un moment au calme', quiet_time: 'Un moment au calme',
  conversation: 'Prendre un moment pour parler', calm_conversation: 'Prendre un moment pour parler',
  breathing: 'Quelques respirations',
}
export function interventionLabel(type) { return interventionTypes[type] || 'Une proposition PsychoSpace' }
export function interventionState(item) { return item.completed ? 'Terminé' : item.accepted ? 'En cours' : 'Proposition' }
export function relevantIntervention(items) {
  return latest(items.filter(item => item.accepted && !item.completed), 'created_at')
    || latest(items.filter(item => !item.completed), 'created_at') || latest(items, 'created_at')
}
export function interventionHistory(items) {
  const remaining = [...items], result = []
  while (remaining.length) {
    const item = latest(remaining, 'created_at')
    if (!item) break
    result.push(item); remaining.splice(remaining.indexOf(item), 1)
  }
  return result
}
