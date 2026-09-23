CREATE TABLE IF NOT EXISTS drift_history (
    id SERIAL PRIMARY KEY,

    astronaut_id INTEGER NOT NULL REFERENCES astronauts(id),

    checkin_date DATE NOT NULL,

    z_scores JSONB NOT NULL,
    concerning_signals JSONB NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (astronaut_id, checkin_date)
);

CREATE INDEX IF NOT EXISTS idx_drift_history_astronaut_date
ON drift_history(astronaut_id, checkin_date);