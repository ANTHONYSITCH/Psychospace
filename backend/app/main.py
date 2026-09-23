import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .config import get_database_path, load_local_ollama_config
from .database import initialize_database
from .routes.profile import router
from .routes.checkins import router as checkins_router
from .routes.sensors import router as sensors_router
from .routes.baseline import router as baseline_router
from .routes.drift import router as drift_router
from .routes.memories import router as memories_router
from .routes.chat import router as chat_router
from .routes.interventions import router as interventions_router
from .seed_loader import load_seeds

logger = logging.getLogger(__name__)


def create_app(database_path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        load_local_ollama_config()
        initialize_database(application.state.database_path)
        load_seeds(application.state.database_path)
        yield

    application = FastAPI(title="PsychoSpace API", lifespan=lifespan)
    application.state.database_path = database_path if database_path is not None else get_database_path()
    application.include_router(router)
    application.include_router(checkins_router)
    application.include_router(sensors_router)
    application.include_router(baseline_router)
    application.include_router(drift_router)
    application.include_router(memories_router)
    application.include_router(chat_router)
    application.include_router(interventions_router)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": {
                "code": "invalid_data", "message": "Les données fournies sont invalides."
            }},
        )

    @application.get("/health")
    def health():
        return {"status": "ok", "service": "PsychoSpace API"}

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = {400: "invalid_data", 404: "not_found"}.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": {"code": code, "message": str(exc.detail)}},
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logger.error("Erreur interne pendant %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {
                "code": "internal_error", "message": "Une erreur interne est survenue."
            }},
        )

    return application


app = create_app()
