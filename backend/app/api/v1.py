"""API v1 — all resource routes (docs/05).

Kept in one module for v1 velocity; splits into feature routers as they grow.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import scheduler_service
from app.config import get_settings
from app.db.engine import get_session
from app.db.models import (
    AppSettings,
    Company,
    CrawlResult,
    Job,
    Keyword,
    ScanRun,
    Schedule,
    utcnow,
)

# run_scan is imported lazily inside the scan endpoints so the heavy scraping/
# matching deps stay out of the base API import graph (web-dashboard host).

router = APIRouter()

# ── Companies ────────────────────────────────────────────────────────────


class CompanyIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    careers_url: str | None = None
    notes: str | None = None


def _company_out(c: Company, jobs_total: int = 0, jobs_matched: int = 0) -> dict[str, Any]:
    return {
        "id": c.id, "name": c.name, "careers_url": c.careers_url,
        "status": c.status, "health": c.health,
        "consecutive_failures": c.consecutive_failures,
        "preferred_strategy": c.preferred_strategy,
        "last_crawl_at": c.last_crawl_at, "last_success_at": c.last_success_at,
        "jobs_total": jobs_total, "jobs_matched": jobs_matched, "notes": c.notes,
    }


@router.get("/companies")
async def list_companies(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    jobs_count = (
        select(Job.company_id, func.count().label("total"),
               func.sum(func.iif(Job.status == "matched", 1, 0)).label("matched"))
        .group_by(Job.company_id).subquery()
    )
    rows = (
        await session.execute(
            select(Company, jobs_count.c.total, jobs_count.c.matched)
            .outerjoin(jobs_count, jobs_count.c.company_id == Company.id)
            .where(Company.status != "deleted")
            .order_by(Company.name)
        )
    ).all()
    return [_company_out(c, t or 0, m or 0) for c, t, m in rows]


@router.post("/companies", status_code=201)
async def create_company(
    body: CompanyIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    dup = (
        await session.execute(select(Company).where(func.lower(Company.name) == body.name.lower()))
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(409, "company already exists")
    company = Company(name=body.name, careers_url=body.careers_url, notes=body.notes)
    session.add(company)
    await session.commit()
    return _company_out(company)


async def _get_company(session: AsyncSession, company_id: str) -> Company:
    company = (
        await session.execute(select(Company).where(Company.id == company_id))
    ).scalar_one_or_none()
    if company is None or company.status == "deleted":
        raise HTTPException(404, "company not found")
    return company


@router.patch("/companies/{company_id}")
async def update_company(
    company_id: str, body: CompanyIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    company = await _get_company(session, company_id)
    company.name = body.name
    if body.careers_url != company.careers_url:
        company.careers_url = body.careers_url
        company.health = "unknown"
        company.preferred_strategy = None
    company.notes = body.notes
    await session.commit()
    return _company_out(company)


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: str, session: AsyncSession = Depends(get_session)
) -> None:
    company = await _get_company(session, company_id)
    company.status = "deleted"
    await session.commit()


@router.post("/companies/{company_id}/pause")
async def pause_company(
    company_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    company = await _get_company(session, company_id)
    company.status = "paused"
    await session.commit()
    return _company_out(company)


@router.post("/companies/{company_id}/resume")
async def resume_company(
    company_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    company = await _get_company(session, company_id)
    company.status = "active"
    await session.commit()
    return _company_out(company)


@router.post("/companies/{company_id}/scan", status_code=202)
async def scan_company(
    company_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    await _get_company(session, company_id)
    if get_settings().web_mode:
        return _WEB_SCAN_MSG
    from app.features.scans.orchestrator import run_scan

    task = asyncio.create_task(run_scan(trigger="manual_company", company_id=company_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "started"}


# ── Keywords ─────────────────────────────────────────────────────────────


class KeywordIn(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    kind: Literal["include", "requirement", "exclude"]


@router.get("/keywords")
async def list_keywords(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    rows = (await session.execute(select(Keyword).order_by(Keyword.kind, Keyword.term))).scalars()
    return [
        {"id": k.id, "term": k.term, "kind": k.kind, "enabled": k.enabled} for k in rows
    ]


@router.post("/keywords", status_code=201)
async def create_keyword(
    body: KeywordIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    dup = (
        await session.execute(
            select(Keyword).where(
                func.lower(Keyword.term) == body.term.lower(), Keyword.kind == body.kind
            )
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(409, "keyword already exists")
    kw = Keyword(term=body.term, kind=body.kind)
    session.add(kw)
    await session.commit()
    return {"id": kw.id, "term": kw.term, "kind": kw.kind, "enabled": kw.enabled}


@router.delete("/keywords/{keyword_id}", status_code=204)
async def delete_keyword(keyword_id: str, session: AsyncSession = Depends(get_session)) -> None:
    kw = (
        await session.execute(select(Keyword).where(Keyword.id == keyword_id))
    ).scalar_one_or_none()
    if kw is None:
        raise HTTPException(404, "keyword not found")
    await session.delete(kw)
    await session.commit()


# ── Jobs ─────────────────────────────────────────────────────────────────


@router.get("/jobs")
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    search: str | None = None,
    company_id: str | None = None,
    status: str = "matched",
    user_state: str | None = None,
    location: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=50),
) -> dict[str, Any]:
    query = select(Job, Company.name).join(Company, Company.id == Job.company_id)
    if status != "all":
        query = query.where(Job.status == status)
    if search:
        query = query.where(Job.title.ilike(f"%{search}%"))
    if company_id:
        query = query.where(Job.company_id == company_id)
    if user_state:
        query = query.where(Job.user_state == user_state)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    total = (
        await session.execute(select(func.count()).select_from(query.subquery()))
    ).scalar_one()
    rows = (
        await session.execute(
            query.order_by(Job.first_seen_at.desc(), Job.match_score.desc().nulls_last())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [
            {
                "id": j.id, "company": name, "title": j.title, "location": j.location,
                "apply_url": j.apply_url, "posted_at": j.posted_at,
                "first_seen_at": j.first_seen_at, "status": j.status,
                "match_score": j.match_score, "match_reasons": j.match_reasons,
                "email_sent_at": j.email_sent_at, "user_state": j.user_state,
                "source_strategy": j.source_strategy,
            }
            for j, name in rows
        ],
        "total": total, "page": page, "page_size": page_size,
    }


class JobStateIn(BaseModel):
    user_state: Literal["none", "bookmarked", "applied"]


@router.post("/jobs/{job_id}/state")
async def set_job_state(
    job_id: str, body: JobStateIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(404, "job not found")
    job.user_state = body.user_state
    job.user_state_at = utcnow()
    await session.commit()
    return {"id": job.id, "user_state": job.user_state}


# ── Scans ────────────────────────────────────────────────────────────────

_background_tasks: set[asyncio.Task[str]] = set()
_WEB_SCAN_MSG = {
    "status": "scheduled",
    "message": "Scans run automatically in the cloud at 08:00 / 14:00 / 20:00 IST.",
}


@router.post("/scans", status_code=202)
async def trigger_scan(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    if get_settings().web_mode:
        return _WEB_SCAN_MSG
    running = (
        await session.execute(select(ScanRun).where(ScanRun.status == "running"))
    ).scalar_one_or_none()
    if running:
        raise HTTPException(409, "a scan is already running")
    from app.features.scans.orchestrator import run_scan

    task = asyncio.create_task(run_scan(trigger="manual"))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "started"}


@router.get("/scans")
async def list_scans(
    session: AsyncSession = Depends(get_session), page: int = Query(1, ge=1)
) -> dict[str, Any]:
    page_size = 20
    total = (await session.execute(select(func.count()).select_from(ScanRun))).scalar_one()
    runs = (
        (
            await session.execute(
                select(ScanRun).order_by(ScanRun.started_at.desc())
                .offset((page - 1) * page_size).limit(page_size)
            )
        ).scalars().all()
    )
    return {
        "items": [
            {
                "id": r.id, "trigger": r.trigger, "status": r.status,
                "started_at": r.started_at, "finished_at": r.finished_at,
                "companies_total": r.companies_total, "companies_ok": r.companies_ok,
                "companies_failed": r.companies_failed, "jobs_found": r.jobs_found,
                "jobs_new": r.jobs_new, "jobs_matched": r.jobs_matched,
            }
            for r in runs
        ],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/scans/current")
async def current_scan(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    run = (
        await session.execute(
            select(ScanRun).where(ScanRun.status == "running")
            .order_by(ScanRun.started_at.desc())
        )
    ).scalars().first()
    if run is None:
        raise HTTPException(404, "no scan running")
    return {
        "id": run.id, "companies_total": run.companies_total,
        "companies_ok": run.companies_ok, "companies_failed": run.companies_failed,
        "jobs_new": run.jobs_new, "started_at": run.started_at,
    }


@router.get("/scans/{scan_id}")
async def scan_detail(scan_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    run = (
        await session.execute(select(ScanRun).where(ScanRun.id == scan_id))
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(404, "scan not found")
    results = (
        await session.execute(
            select(CrawlResult, Company.name)
            .join(Company, Company.id == CrawlResult.company_id)
            .where(CrawlResult.scan_run_id == scan_id)
        )
    ).all()
    return {
        "id": run.id, "trigger": run.trigger, "status": run.status,
        "started_at": run.started_at, "finished_at": run.finished_at,
        "companies": [
            {
                "company": name, "strategy": cr.strategy, "status": cr.status,
                "jobs_found": cr.jobs_found, "jobs_new": cr.jobs_new,
                "duration_ms": cr.duration_ms, "error": cr.error,
                "attempts": cr.strategies_attempted,
            }
            for cr, name in results
        ],
    }


# ── Schedules ────────────────────────────────────────────────────────────


class ScheduleIn(BaseModel):
    hour: int = Field(ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    enabled: bool = True


@router.get("/schedules")
async def list_schedules(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    slots = (
        (await session.execute(select(Schedule).order_by(Schedule.hour, Schedule.minute)))
        .scalars().all()
    )
    return {
        "items": [
            {"id": s.id, "hour": s.hour, "minute": s.minute, "enabled": s.enabled}
            for s in slots
        ],
        "next_run_at": scheduler_service.next_run_time(),
    }


@router.post("/schedules", status_code=201)
async def create_schedule(
    body: ScheduleIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    dup = (
        await session.execute(
            select(Schedule).where(Schedule.hour == body.hour, Schedule.minute == body.minute)
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(409, "slot already exists")
    slot = Schedule(hour=body.hour, minute=body.minute, enabled=body.enabled)
    session.add(slot)
    await session.commit()
    await scheduler_service.reload_schedules()
    return {"id": slot.id, "hour": slot.hour, "minute": slot.minute, "enabled": slot.enabled}


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str, session: AsyncSession = Depends(get_session)
) -> None:
    slot = (
        await session.execute(select(Schedule).where(Schedule.id == schedule_id))
    ).scalar_one_or_none()
    if slot is None:
        raise HTTPException(404, "schedule not found")
    await session.delete(slot)
    await session.commit()
    await scheduler_service.reload_schedules()


# ── Settings ─────────────────────────────────────────────────────────────


class SettingsIn(BaseModel):
    timezone: str | None = None
    notification_email: str | None = None
    email_enabled: bool | None = None
    match_threshold: float | None = Field(None, ge=0.1, le=0.95)
    requirement_boost: float | None = Field(None, ge=0, le=0.2)
    scan_concurrency: int | None = Field(None, ge=1, le=16)


@router.get("/settings")
async def get_app_settings(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    from app.config import get_settings as env

    app = (await session.execute(select(AppSettings))).scalar_one()
    return {
        "timezone": app.timezone, "notification_email": app.notification_email,
        "email_enabled": app.email_enabled, "match_threshold": app.match_threshold,
        "requirement_boost": app.requirement_boost, "scan_concurrency": app.scan_concurrency,
        "embedding_provider": app.embedding_provider,
        "openai_key_present": bool(env().openai_api_key),
        "resend_key_present": bool(env().resend_api_key),
    }


@router.patch("/settings")
async def patch_settings(
    body: SettingsIn, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    app = (await session.execute(select(AppSettings))).scalar_one()
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(app, field, value)
    await session.commit()
    if body.timezone:
        await scheduler_service.reload_schedules()
    return await get_app_settings(session)


# ── Stats ────────────────────────────────────────────────────────────────


@router.get("/stats/overview")
async def stats_overview(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    active = (
        await session.execute(
            select(func.count()).select_from(Company).where(Company.status == "active")
        )
    ).scalar_one()
    failing = (
        await session.execute(
            select(func.count()).select_from(Company)
            .where(Company.status == "active", Company.health == "failing")
        )
    ).scalar_one()
    found_today = (
        await session.execute(
            select(func.count()).select_from(Job).where(Job.first_seen_at >= today)
        )
    ).scalar_one()
    matched_today = (
        await session.execute(
            select(func.count()).select_from(Job)
            .where(Job.first_seen_at >= today, Job.status == "matched")
        )
    ).scalar_one()
    emailed_total = (
        await session.execute(
            select(func.count()).select_from(Job).where(Job.email_sent_at.isnot(None))
        )
    ).scalar_one()
    last = (
        await session.execute(
            select(ScanRun).where(ScanRun.status != "running")
            .order_by(ScanRun.started_at.desc())
        )
    ).scalars().first()
    return {
        "companies_active": active, "companies_failing": failing,
        "jobs_found_today": found_today, "jobs_matched_today": matched_today,
        "jobs_emailed_total": emailed_total,
        "last_scan": {"at": last.started_at, "status": last.status} if last else None,
        "next_scan_at": scheduler_service.next_run_time(),
    }


@router.get("/stats/timeseries")
async def stats_timeseries(
    session: AsyncSession = Depends(get_session), days: int = Query(14, ge=7, le=90)
) -> dict[str, Any]:
    """Daily counts for the Statistics page: found / matched / emailed."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(Job.first_seen_at)
    rows = (
        await session.execute(
            select(
                day.label("d"),
                func.count(),
                func.sum(func.iif(Job.status == "matched", 1, 0)),
                func.sum(func.iif(Job.email_sent_at.isnot(None), 1, 0)),
            )
            .where(Job.first_seen_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    return {
        "days": [
            {"date": str(d), "found": f or 0, "matched": m or 0, "emailed": e or 0}
            for d, f, m, e in rows
        ]
    }


@router.get("/stats/companies")
async def stats_companies(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                Company.name,
                Company.health,
                func.count(Job.id),
                func.sum(func.iif(Job.status == "matched", 1, 0)),
            )
            .outerjoin(Job, Job.company_id == Company.id)
            .where(Company.status == "active")
            .group_by(Company.id)
            .order_by(func.count(Job.id).desc())
        )
    ).all()
    return [
        {"name": n, "health": h, "jobs": j or 0, "matched": m or 0} for n, h, j, m in rows
    ]


@router.get("/stats/funnel")
async def stats_funnel(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    async def count(*where: Any) -> int:
        return (
            await session.execute(select(func.count()).select_from(Job).where(*where))
        ).scalar_one()

    return {
        "found": await count(),
        "passed_exclusions": await count(Job.status != "excluded"),
        "matched": await count(Job.status == "matched"),
        "emailed": await count(Job.email_sent_at.isnot(None)),
        "applied": await count(Job.user_state == "applied"),
    }
