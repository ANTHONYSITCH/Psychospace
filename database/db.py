import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "psychospace_db"),
        user=os.getenv("DB_USER", "psy_user"),
        password=os.getenv("DB_PASSWORD", "psy_password"),
    )


def test_connection():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()

        return result[0] == 1

    finally:
        connection.close()


def get_astronaut_context(astronaut_id: int):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM astronaut_daily_context
                WHERE astronaut_id = %s
                ORDER BY checkin_date DESC
                LIMIT 1;
                """,
                (astronaut_id,),
            )

            return cursor.fetchone()

    finally:
        connection.close()


def get_astronaut_onboarding_history(astronaut_id: int, onboarding_days: int = 7):
    """
    Récupère les TOUT PREMIERS check-ins d'un astronaute
    (par ordre chronologique croissant), pour établir une baseline
    FIXE de la période d'onboarding.

    Contrairement à une fenêtre glissante, cette fonction ne bouge
    jamais avec le temps : elle ancre la baseline sur la toute
    première période d'observation, pour qu'un jour de dérive
    ultérieur ne puisse jamais polluer la référence utilisée
    pour le détecter.
    """
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT *
                FROM astronaut_daily_context
                WHERE astronaut_id = %s
                ORDER BY checkin_date ASC
                LIMIT %s;
                """,
                (astronaut_id, onboarding_days),
            )

            return cursor.fetchall()

    finally:
        connection.close()


def get_astronaut_history(astronaut_id: int, days: int = 14, before_date=None):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            if before_date is not None:
                cursor.execute(
                    """
                    SELECT *
                    FROM astronaut_daily_context
                    WHERE astronaut_id = %s
                      AND checkin_date < %s
                    ORDER BY checkin_date DESC
                    LIMIT %s;
                    """,
                    (astronaut_id, before_date, days),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM astronaut_daily_context
                    WHERE astronaut_id = %s
                    ORDER BY checkin_date DESC
                    LIMIT %s;
                    """,
                    (astronaut_id, days),
                )

            rows = cursor.fetchall()

        return list(reversed(rows))

    finally:
        connection.close()


def save_drift_result(astronaut_id: int, checkin_date, z_scores: dict, concerning_signals: list):
    import json

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO drift_history
                    (astronaut_id, checkin_date, z_scores, concerning_signals)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (astronaut_id, checkin_date)
                DO UPDATE SET
                    z_scores = EXCLUDED.z_scores,
                    concerning_signals = EXCLUDED.concerning_signals;
                """,
                (
                    astronaut_id,
                    checkin_date,
                    json.dumps(z_scores),
                    json.dumps(concerning_signals),
                ),
            )

        connection.commit()

    finally:
        connection.close()


def get_drift_history(astronaut_id: int, days: int = 14):
    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT z_scores, concerning_signals
                FROM drift_history
                WHERE astronaut_id = %s
                ORDER BY checkin_date DESC
                LIMIT %s;
                """,
                (astronaut_id, days),
            )

            rows = cursor.fetchall()

        return list(reversed(rows))

    finally:
        connection.close()