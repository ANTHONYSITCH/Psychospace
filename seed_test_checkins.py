"""
Script à lancer UNE FOIS pour insérer des check-ins de test
pour un astronaute donné, afin de pouvoir tester
GET /astronaut/{id}/drift sans attendre 7 jours réels.

Usage :
    python seed_test_checkins.py
"""

from datetime import date, timedelta

from database.db import get_connection


ASTRONAUT_ID = 1

CHECKINS = [
    (7, 7.5, 2, 8, 8),
    (6, 7.2, 3, 7, 7),
    (5, 7.8, 2, 9, 8),
    (4, 7.4, 3, 8, 7),
    (3, 7.1, 2, 8, 8),
    (2, 7.6, 2, 7, 7),
    (1, 7.3, 3, 8, 8),
    (0, 4.8, 7, 4, 4),
]


def seed():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            for offset, sleep_h, fatigue, energy, mood in CHECKINS:
                checkin_date = date.today() - timedelta(days=offset)

                cursor.execute(
                    """
                    INSERT INTO daily_checkins
                        (astronaut_id, checkin_date, sleep_duration_hours,
                         fatigue, energy, mood)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (astronaut_id, checkin_date)
                    DO UPDATE SET
                        sleep_duration_hours = EXCLUDED.sleep_duration_hours,
                        fatigue = EXCLUDED.fatigue,
                        energy = EXCLUDED.energy,
                        mood = EXCLUDED.mood;
                    """,
                    (ASTRONAUT_ID, checkin_date, sleep_h, fatigue, energy, mood),
                )

        connection.commit()
        print(f"{len(CHECKINS)} check-ins insérés pour l'astronaute {ASTRONAUT_ID}.")

    finally:
        connection.close()


if __name__ == "__main__":
    seed()