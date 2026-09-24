export const steps = [
  { key: 'sleep_hours', label: 'Sommeil', question: 'Comment s’est passée ta nuit ?', hint: 'Combien de temps as-tu dormi ?', unit: 'h', max: 24, increment: 0.5, choices: [5, 6, 6.5, 7, 7.5, 8, 9] },
  { key: 'mood', label: 'Humeur', question: 'Comment te sens-tu aujourd’hui ?', hint: 'Prends le repère qui te ressemble le plus.', low: 'Moral très bas', high: 'Très bon moral' },
  { key: 'stress', label: 'Pression ressentie', question: 'Tu te sens sous pression aujourd’hui ?', hint: 'Il n’y a pas de bonne ou de mauvaise réponse.', low: 'Très peu', high: 'Beaucoup' },
  { key: 'fatigue', label: 'Fatigue', question: 'Et ta fatigue ?', hint: 'Écoute simplement ton ressenti.', low: 'Très légère', high: 'Très forte' },
  { key: 'energy', label: 'Énergie', question: 'Comment est ton énergie ?', hint: 'Pense à l’énergie dont tu disposes maintenant.', low: 'Très basse', high: 'Très élevée' },
  { key: 'social_level', label: 'Échanges', question: 'Quelle place ont eue les échanges aujourd’hui ?', hint: 'Un repère pour tes interactions avec les autres.', low: 'Très peu d’échanges', high: 'Beaucoup d’échanges' },
  { key: 'activity_minutes', label: 'Activité', question: 'Combien de temps as-tu bougé aujourd’hui ?', hint: 'Même quelques minutes comptent.', unit: 'min', max: 1440, increment: 1, choices: [0, 15, 30, 45, 60, 90] },
]

export function validAnswer(step, value) {
  if (!Number.isFinite(value)) return false
  return step.unit ? value >= 0 && value <= step.max && Number.isInteger(value / step.increment)
    : Number.isInteger(value) && value >= 1 && value <= 10
}

export function answerLabel(step, value) {
  if (!Number.isFinite(value)) return 'À toi de choisir'
  if (step.key === 'sleep_hours') {
    const hours = Math.floor(value), minutes = Math.round((value - hours) * 60)
    return `${hours} h${minutes ? ` ${minutes}` : ''}`
  }
  return `${value}${step.unit ? ` ${step.unit}` : ' / 10'}`
}
