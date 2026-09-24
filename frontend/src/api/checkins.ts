import { apiClient } from './client'

export type CheckinPayload = {
  astronaut_id?: number | null
  astronaut_first_name?: string | null
  astronaut_last_name?: string | null
  checkin_date: string
  sleep_duration_hours?: number | null
  sleep_quality?: number | null
  fatigue?: number | null
  energy?: number | null
  stress?: number | null
  stress_source?: string | null
  mood?: number | null
  motivation?: number | null
  concentration?: number | null
  unusual_difficulty?: string | null
  overall_state?: number | null
  compared_to_yesterday?: string | null
  comment?: string | null
}

export type Checkin = CheckinPayload & {
  id: number
  created_at?: string | null
}

export const getCheckins = () => apiClient.get<Checkin[]>('/api/checkins')
export const createCheckin = (payload: CheckinPayload) => apiClient.post<Checkin>('/api/checkins', payload)
