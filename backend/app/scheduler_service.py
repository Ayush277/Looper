"""In-process APScheduler (M4-lite).

Runs inside the API process during dev — no Redis/Celery needed. The prod path
(separate scheduler process dispatching Celery tasks) lands with full M4 once
Redis exists; this module keeps the same DB-driven schedule semantics.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import select

from app.db.engine import SessionFactory
from app.db.models import AppSettings, Schedule

_scheduler: AsyncIOScheduler | None = None


async def _scheduled_scan() -> None:
    logger.info("scheduled scan firing")
    # Lazy import: keeps the heavy scan deps (scraping/matching) out of the
    # base API import graph so the web dashboard host can stay slim.
    from app.features.scans.orchestrator import run_scan

    await run_scan(trigger="scheduled")


async def reload_schedules() -> None:
    """(Re)register cron triggers from the schedules table. Called at startup
    and after any schedule edit — no restart needed (FR-6.2)."""
    assert _scheduler is not None
    async with SessionFactory() as session:
        app = (await session.execute(select(AppSettings))).scalar_one_or_none()
        tz = app.timezone if app else "Asia/Kolkata"
        slots = (
            (await session.execute(select(Schedule).where(Schedule.enabled)))
            .scalars()
            .all()
        )
    for job in _scheduler.get_jobs():
        job.remove()
    for slot in slots:
        _scheduler.add_job(
            _scheduled_scan,
            CronTrigger(hour=slot.hour, minute=slot.minute, timezone=tz),
            id=f"scan-{slot.hour:02d}{slot.minute:02d}",
            replace_existing=True,
        )
    logger.info("scheduler loaded {} slots (tz={})", len(slots), tz)


def next_run_time() -> str | None:
    if _scheduler is None:
        return None
    times = [j.next_run_time for j in _scheduler.get_jobs() if j.next_run_time]
    return min(times).isoformat() if times else None


async def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.start()
    await reload_schedules()


async def stop_scheduler() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
