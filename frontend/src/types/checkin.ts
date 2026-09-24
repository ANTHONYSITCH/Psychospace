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

export type SensorMeasurement = {
  id: number
  mission_id: number
  sensor_name: string
  sensor_type: string
  location?: string | null
  unit?: string | null
  latest_value?: number | null
  quality_status?: string | null
  last_recorded_at?: string | null
}

export type Certificate = {
  id: number
  event_type: string
  event_id: string
  actor_name?: string | null
  previous_hash: string
  current_hash: string
  event_payload?: string | null
  created_at?: string | null
}
