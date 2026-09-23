"""
Mapping entre les colonnes réelles de la table daily_checkins
(exposées via la vue astronaut_daily_context) et les clés attendues
par BaselineManager et DriftEngine.

IMPORTANT :
"social" n'existe pas dans le questionnaire actuel.
On travaille donc sur 4 métriques réelles uniquement :
sommeil_h, humeur, fatigue, activite.

Ne pas fabriquer de valeur pour "social" : mieux vaut un modèle
honnête à 4 métriques qu'un modèle à 5 métriques dont une est fausse.
"""


def map_checkin_to_metrics(checkin: dict) -> dict:
    """
    Convertit UNE ligne de check-in (dict issu de
    astronaut_daily_context) vers le format attendu par
    DriftEngine.evaluate_daily_signals().
    """

    return {
        "sommeil_h": float(checkin["sleep_duration_hours"]),
        "humeur": checkin["mood"],
        "fatigue": checkin["fatigue"],
        "activite": checkin["energy"],
    }


def build_baseline_input(history: list[dict]) -> dict:
    """
    Convertit une LISTE de check-ins historiques (dicts issus de
    astronaut_daily_context, triés du plus ancien au plus récent)
    vers le format attendu par
    BaselineManager.calculate_initial_baseline().

    Résultat :
    {
        "sommeil_h": [7.5, 7.2, ...],
        "humeur": [8, 7, ...],
        "fatigue": [2, 3, ...],
        "activite": [8, 7, ...]
    }
    """

    baseline_input = {
        "sommeil_h": [],
        "humeur": [],
        "fatigue": [],
        "activite": [],
    }

    for row in history:
        baseline_input["sommeil_h"].append(float(row["sleep_duration_hours"]))
        baseline_input["humeur"].append(row["mood"])
        baseline_input["fatigue"].append(row["fatigue"])
        baseline_input["activite"].append(row["energy"])

    return baseline_input