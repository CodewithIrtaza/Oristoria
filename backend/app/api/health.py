"""Health check router."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness check. Does not touch the DB."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> JSONResponse:
    """Readiness check. Pings the DB.
    TODO Task 1: add real DB ping via pool."""
    # For now, just confirm the app is up.
    return JSONResponse({"status": "ready"})
