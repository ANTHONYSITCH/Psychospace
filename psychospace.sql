-- ============================================================
-- BASE DE DONNEES : ASTRONAUT MONITORING
-- =====================================================-- ============================================================
-- MISSIONS
-- ============================================================

CREATE TABLE missions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(30) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- ASTRONAUTES
-- ============================================================

CREATE TABLE astronauts (
    id SERIAL PRIMARY KEY,
    mission_id INTEGER NOT NULL REFERENCES missions(id),

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    email VARCHAR(255) UNIQUE NOT NULL,

    -- Démonstration uniquement.
    -- En production : Argon2id/bcrypt généré par le backend.
    password_hash VARCHAR(255) NOT NULL,

    role VARCHAR(50) DEFAULT 'astronaut',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- QUESTIONNAIRES QUOTIDIENS
-- ============================================================

CREATE TABLE daily_checkins (
    id SERIAL PRIMARY KEY,

    astronaut_id INTEGER NOT NULL REFERENCES astronauts(id),

    checkin_date DATE NOT NULL,

    sleep_duration_hours NUMERIC(4,2),
    sleep_quality INTEGER,

    fatigue INTEGER,
    energy INTEGER,
    stress INTEGER,

    stress_source TEXT,

    mood INTEGER,
    motivation INTEGER,
    concentration INTEGER,

    unusual_difficulty VARCHAR(100),

    overall_state INTEGER,

    compared_to_yesterday VARCHAR(50),

    comment TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (astronaut_id, checkin_date),

    CHECK (sleep_duration_hours >= 0),
    CHECK (sleep_quality BETWEEN 0 AND 10),
    CHECK (fatigue BETWEEN 0 AND 10),
    CHECK (energy BETWEEN 0 AND 10),
    CHECK (stress BETWEEN 0 AND 10),
    CHECK (mood BETWEEN 0 AND 10),
    CHECK (motivation BETWEEN 0 AND 10),
    CHECK (concentration BETWEEN 0 AND 10),
    CHECK (overall_state BETWEEN 0 AND 10)
);


-- ============================================================
-- CAPTEURS
-- ============================================================

CREATE TABLE sensors (
    id SERIAL PRIMARY KEY,

    mission_id INTEGER NOT NULL REFERENCES missions(id),

    sensor_name VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,

    location VARCHAR(100),

    unit VARCHAR(30),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- MESURES DES CAPTEURS
-- ============================================================

CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,

    sensor_id INTEGER NOT NULL REFERENCES sensors(id),

    recorded_at TIMESTAMP NOT NULL,

    value NUMERIC(12,4) NOT NULL,

    quality_status VARCHAR(30) DEFAULT 'valid',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- INDEX
-- ============================================================

CREATE INDEX idx_checkins_astronaut_date
ON daily_checkins(astronaut_id, checkin_date);

CREATE INDEX idx_sensor_readings_sensor_date
ON sensor_readings(sensor_id, recorded_at);

CREATE INDEX idx_astronauts_mission
ON astronauts(mission_id);


-- ============================================================
-- VUE POUR LE FUTUR BACKEND / OLLAMA
-- ============================================================

CREATE VIEW astronaut_daily_context AS
SELECT
    a.id AS astronaut_id,
    a.first_name,
    a.last_name,

    m.name AS mission_name,

    d.checkin_date,

    d.sleep_duration_hours,
    d.sleep_quality,
    d.fatigue,
    d.energy,
    d.stress,
    d.stress_source,
    d.mood,
    d.motivation,
    d.concentration,
    d.unusual_difficulty,
    d.overall_state,
    d.compared_to_yesterday,
    d.comment

FROM astronauts a

JOIN missions m
    ON a.mission_id = m.id

JOIN daily_checkins d
    ON a.id = d.astronaut_id;