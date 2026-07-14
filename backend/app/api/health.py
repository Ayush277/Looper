"""Liveness and deep health checks."""
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db.engine import SessionFactory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/deep")
async def health_deep() -> dict[str, object]:
    """Per-dependency status. Redis/worker checks land with M4."""
    checks: dict[str, str] = {}

    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 — health check must never raise
        checks["database"] = f"error: {exc.__class__.__name__}"

    checks["redis"] = "not_configured"  # M4
    checks["worker"] = "not_configured"  # M4

    settings = get_settings()
    checks["openai_key"] = "present" if settings.openai_api_key else "absent (local embedder)"
    checks["resend_key"] = "present" if settings.resend_api_key else "absent (console notifier)"

    status = "ok" if checks["database"] == "ok" else "degraded"
    return {"status": status, "checks": checks}
