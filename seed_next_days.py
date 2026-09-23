"""
Insère 2 jours SUPPLÉMENTAIRES (après le dernier jour déjà en base)
avec des données dégradées, pour tester la progression de
consecutive_days et le déclenchement de drift_detected.

Usage :
    python seed_next_days.py
"""

from datetime import date, timedelta

from database.db import get_connection


ASTRONAUT_ID = 1

# Le seed initial avait mis le dernier jour à "aujourd'hui" (offset 0).
# On ajoute donc J+1 et J+2, encore plus dégradés.
NEXT_CHECKINS = [
    # (offset_jours_apres_aujourdhui, sleep_h, fatigue, energy, mood)
    (1, 4.5, 8, 3, 3),
    (2, 4.2, 8, 3, 2),
]


def seed_next():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            for offset, sleep_h, fatigue, energy, mood in NEXT_CHECKINS:
                checkin_date = date.today() + timedelta(days=offset)

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
        print(f"{len(NEXT_CHECKINS)} nouveaux check-ins insérés pour l'astronaute {ASTRONAUT_ID}.")

    finally:
        connection.close()


if __name__ == "__main__":
    seed_next()