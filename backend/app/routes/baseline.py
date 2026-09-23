from fastapi import APIRouter, Request

from ..services.ai_service import calculate_and_save_baseline, get_baseline

router = APIRouter(prefix="/api/baseline", tags=["baseline"])


@router.get("/{user_id}")
def read_baseline(user_id: str, request: Request):
    return get_baseline(request.app.state.database_path, user_id)


@router.post("/{user_id}/calculate", status_code=201)
def calculate(user_id: str, request: Request):
    return calculate_and_save_baseline(request.app.state.database_path, user_id)
