export type Checkin = {
  id: number
  astronaut_id: number
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
  created_at?: string | null
}
