from fastapi import APIRouter, HTTPException

from database.db import get_astronaut_context, get_astronaut_history
from backend.analysis.drift_engine import DriftEngine
from backend.analysis.mapping import map_checkin_to_metrics, build_baseline_input
from baseline import BaselineManager

router = APIRouter()


@router.get("/astronaut/{astronaut_id}/drift")
def get_astronaut_drift(astronaut_id: int):

    # ------------------------------------------------------------
    # 1. Check-in du jour
    # ------------------------------------------------------------

    today_checkin = get_astronaut_context(astronaut_id)

    if today_checkin is None:
        raise HTTPException(
            status_code=404,
            detail="Aucun check-in trouvé pour cet astronaute."
        )

    # ------------------------------------------------------------
    # 2. Historique (pour la baseline)
    # ------------------------------------------------------------

    history = get_astronaut_history(astronaut_id, days=14)

    onboarding_days = 7

    if len(history) < onboarding_days:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Pas assez de données pour calculer une baseline "
                f"({len(history)}/{onboarding_days} jours)."
            )
        )

    # ------------------------------------------------------------
    # 3. Mapping vers le format attendu par les moteurs
    # ------------------------------------------------------------

    baseline_input = build_baseline_input(history)
    today_metrics = map_checkin_to_metrics(today_checkin)

    # ------------------------------------------------------------
    # 4. Baseline + drift
    # ------------------------------------------------------------

    baseline_mgr = BaselineManager(onboarding_days=onboarding_days)
    baseline = baseline_mgr.calculate_initial_baseline(baseline_input)

    drift_engine = DriftEngine()

    z_today = drift_engine.evaluate_daily_signals(today_metrics, baseline)

    # NOTE : ceci ne gère pas encore l'historique multi-jours de
    # z-scores (nécessaire pour consecutive_days). Pour l'instant,
    # on analyse le jour courant isolément. On branchera le suivi
    # persistant (history_z stocké quelque part, ex. en base ou en
    # mémoire) à l'étape suivante.
    drift_result = drift_engine.evaluate_drift_with_context([z_today])

    return {
        "astronaut_id": astronaut_id,
        "checkin_date": str(today_checkin["checkin_date"]),
        "baseline": baseline,
        "today_metrics": today_metrics,
        "drift_result": drift_result,
    }