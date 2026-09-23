from fastapi import APIRouter, Request, Response

from ..services.ai_service import analyze_and_save_drift, get_drift_history

router = APIRouter(prefix="/api/drift", tags=["drift"])


@router.get("/{user_id}")
def read_history(user_id: str, request: Request):
    return get_drift_history(request.app.state.database_path, user_id)


@router.post("/{user_id}/analyze", responses={204: {"description": "Aucun changement détecté"}})
def analyze(user_id: str, request: Request):
    event = analyze_and_save_drift(request.app.state.database_path, user_id)
    return Response(status_code=204) if event is None else event
