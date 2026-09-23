export const memoryCategories = {
  support_preference: 'Ce qui m’aide',
  communication_preference: 'Comment je préfère échanger',
  motivation: 'Ce qui compte pour moi',
  interest: 'Ce que j’aime',
  coping_strategy: 'Ce qui m’aide à souffler',
}
export function categoryLabel(category) { return memoryCategories[category] || 'Un repère personnel' }
export function sourceLabel(source) {
  return ({ user: 'Ajouté par toi', user_chat: 'Partagé pendant une conversation' })[source] || 'Enregistré dans ta mémoire PsychoSpace'
}
export function validMemoryDraft(draft) {
  return typeof draft.category === 'string' && Boolean(draft.category.trim()) && typeof draft.content === 'string' && Boolean(draft.content.trim()) && Number.isInteger(draft.importance) && draft.importance >= 1 && draft.importance <= 10
}
// Explicit contract fields only. Existing identity, creation date and provenance survive edits.
export function memoryPayload(draft) {
  return Object.fromEntries(['id', 'user_id', 'category', 'content', 'importance', 'source', 'created_at'].map(key => [key, key === 'content' ? draft.content.trim() : draft[key]]))
}
