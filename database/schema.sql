-- Enable foreign keys on every connection, before starting a transaction.
PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Store dates and timestamps as ISO 8601 text in UTC.
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    age INTEGER,
    mission_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE profiles (
    user_id TEXT PRIMARY KEY,
    normal_sleep_hours REAL,
    preferred_support TEXT,
    preferred_contact_time TEXT,
    interests TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE daily_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sleep_hours REAL,
    mood INTEGER CHECK (mood BETWEEN 1 AND 10),
    stress INTEGER CHECK (stress BETWEEN 1 AND 10),
    fatigue INTEGER CHECK (fatigue BETWEEN 1 AND 10),
    energy INTEGER CHECK (energy BETWEEN 1 AND 10),
    social_level INTEGER CHECK (social_level BETWEEN 1 AND 10),
    activity_minutes INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    importance INTEGER,
    source TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    sleep_hours_avg REAL,
    mood_avg REAL,
    stress_avg REAL,
    fatigue_avg REAL,
    energy_avg REAL,
    social_level_avg REAL,
    activity_minutes_avg REAL,
    observation_days INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Behavioral changes only; no medical or psychiatric diagnosis.
CREATE TABLE drift_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    level TEXT NOT NULL,
    drift_score REAL,
    confidence REAL,
    affected_signals TEXT,
    explanation TEXT,
    status TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE interventions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    drift_event_id TEXT,
    created_at TEXT NOT NULL,
    type TEXT,
    message TEXT NOT NULL,
    accepted INTEGER CHECK (accepted IN (0, 1)),
    completed INTEGER CHECK (completed IN (0, 1)),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (drift_event_id) REFERENCES drift_events(id)
);

CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- User histories: the leading user_id also supports foreign key lookups.
CREATE INDEX idx_daily_checkins_user_timestamp ON daily_checkins(user_id, timestamp);
CREATE INDEX idx_sensor_readings_user_timestamp ON sensor_readings(user_id, timestamp);
CREATE INDEX idx_memories_user_created_at ON memories(user_id, created_at);
CREATE INDEX idx_baselines_user_calculated_at ON baselines(user_id, calculated_at);
CREATE INDEX idx_drift_events_user_detected_at ON drift_events(user_id, detected_at);
CREATE INDEX idx_interventions_user_created_at ON interventions(user_id, created_at);
CREATE INDEX idx_chat_messages_user_timestamp ON chat_messages(user_id, timestamp);
CREATE INDEX idx_interventions_drift_event_id ON interventions(drift_event_id);

COMMIT;
