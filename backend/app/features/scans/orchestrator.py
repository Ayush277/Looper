"""ScanOrchestrator — one scan run end to end (docs/07 §1).

Fan out over active companies (bounded concurrency, per-company isolation) →
strategy chain → dedup insert → match → assemble digest of never-emailed
matches → notify → mark email_sent_at in the same transaction as email_log.
Idempotent: rerunning produces no new rows and no duplicate emails.
"""
import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import SessionFactory
from app.db.models import (
    AppSettings,
    Company,
    CrawlResult,
    EmailLog,
    EmailLogJob,
    Job,
    ScanRun,
    utcnow,
)
from app.matching.embedders import get_embedder
from app.matching.pipeline import match_jobs
from app.notifications.base import Digest, DigestJob
from app.notifications.senders import get_notifier
from app.scraping.fetcher import Fetcher
from app.scraping.strategies import run_strategy_chain
from app.scraping.types import ScrapeOutcome
from app.shared.hashing import job_content_hash

DIGEST_JOB_CAP = 25


async def _scan_company(
    fetcher: Fetcher, company: Company, session: AsyncSession, run: ScanRun
) -> tuple[ScrapeOutcome, list[Job]]:
    start = datetime.now(timezone.utc)
    outcome = await run_strategy_chain(
        fetcher, company.name, company.careers_url, company.preferred_strategy
    )
    new_jobs: list[Job] = []
    if outcome.ok:
        for raw in outcome.jobs:
            h = job_content_hash(company.id, raw.title, raw.location, raw.apply_url)
            existing = (
                await session.execute(select(Job).where(Job.content_hash == h))
            ).scalar_one_or_none()
            if existing:
                existing.last_seen_at = utcnow()
                continue
            job = Job(
                company_id=company.id,
                content_hash=h,
                title=raw.title,
                location=raw.location,
                apply_url=raw.apply_url,
                external_id=raw.external_id,
                posted_at=raw.posted_at,
                description_snippet=raw.description_snippet,
                source_strategy=outcome.strategy_used or "unknown",
            )
            session.add(job)
            new_jobs.append(job)
        company.last_success_at = utcnow()
        company.preferred_strategy = outcome.strategy_used
        company.consecutive_failures = 0
        company.health = "healthy"
    else:
        company.consecutive_failures += 1
        company.health = "degraded" if company.consecutive_failures < 3 else "failing"
    company.last_crawl_at = utcnow()

    session.add(
        CrawlResult(
            scan_run_id=run.id,
            company_id=company.id,
            strategy=outcome.strategy_used or "none",
            strategies_attempted=[
                {"strategy": a.strategy, "ok": a.ok, "jobs": a.jobs, "error": a.error}
                for a in outcome.attempts
            ],
            status="success" if outcome.ok else "failed",
            jobs_found=len(outcome.jobs),
            jobs_new=len(new_jobs),
            duration_ms=int((datetime.now(timezone.utc) - start).total_seconds() * 1000),
            error=None if outcome.ok else "; ".join(
                f"{a.strategy}: {a.error}" for a in outcome.attempts if a.error
            )[:500],
        )
    )
    await session.flush()
    return outcome, new_jobs


async def _send_digest(session: AsyncSession, run: ScanRun, scanned: int) -> None:
    app = (await session.execute(select(AppSettings))).scalar_one()
    if not app.email_enabled or not app.notification_email:
        logger.info("digest skipped: email disabled or no recipient configured")
        return
    rows = (
        await session.execute(
            select(Job, Company.name)
            .join(Company, Company.id == Job.company_id)
            .where(Job.status == "matched", Job.email_sent_at.is_(None))
            .order_by(Job.match_score.desc())
        )
    ).all()
    if not rows:
        logger.info("digest skipped: no new matches")
        return

    companies = list(dict.fromkeys(name for _, name in rows))
    subject_tail = ", ".join(companies[:2]) + (
        f" +{len(companies) - 2}" if len(companies) > 2 else ""
    )
    digest = Digest(
        subject=f"LoopJob: {len(rows)} new internship match"
        f"{'es' if len(rows) != 1 else ''} ({subject_tail})",
        jobs=[
            DigestJob(
                company=name,
                title=job.title,
                location=job.location,
                posted_at=str(job.posted_at) if job.posted_at else None,
                apply_url=job.apply_url,
                reasons=[str(r["term"]) for r in job.match_reasons if r["kind"] != "exclude"][:5],
            )
            for job, name in rows[:DIGEST_JOB_CAP]
        ],
        scanned_companies=scanned,
        scan_time=datetime.now(timezone.utc).strftime("%H:%M UTC"),
    )
    notifier = get_notifier()
    result = await notifier.send(app.notification_email, digest)

    log = EmailLog(
        scan_run_id=run.id,
        recipient=app.notification_email,
        subject=digest.subject,
        job_count=len(rows),
        status="sent" if result.ok else "failed",
        provider_message_id=result.provider_message_id,
        error=result.error,
    )
    session.add(log)
    await session.flush()
    if result.ok:
        # Same transaction as the log: the zero-duplicate guarantee.
        for job, _ in rows:
            job.email_sent_at = utcnow()
            session.add(EmailLogJob(email_log_id=log.id, job_id=job.id))


async def run_scan(trigger: str = "manual", company_id: str | None = None) -> str:
    """Execute a full scan run. Returns the scan_run id."""
    fetcher = Fetcher()
    embedder = get_embedder()
    try:
        async with SessionFactory() as session:
            run = ScanRun(trigger=trigger)
            session.add(run)
            await session.flush()
            run_id = run.id
            log = logger.bind(scan_run_id=run_id)

            query = select(Company).where(Company.status == "active")
            if company_id:
                query = query.where(Company.id == company_id)
            companies = list((await session.execute(query)).scalars().all())
            run.companies_total = len(companies)

            app = (await session.execute(select(AppSettings))).scalar_one()
            sem = asyncio.Semaphore(app.scan_concurrency)
            all_new: list[Job] = []

            async def one(company: Company) -> None:
                async with sem:
                    try:
                        outcome, new_jobs = await _scan_company(fetcher, company, session, run)
                    except Exception:  # noqa: BLE001 — isolation per company
                        log.exception("company {} crashed the scanner", company.name)
                        company.consecutive_failures += 1
                        company.health = "failing"
                        run.companies_failed += 1
                        return
                    if outcome.ok:
                        run.companies_ok += 1
                    else:
                        run.companies_failed += 1
                    run.jobs_found += len(outcome.jobs)
                    all_new.extend(new_jobs)

            # NOTE: single session shared across tasks — SQLAlchemy sessions are
            # not task-safe, so with SQLite dev we run sequentially; Celery (M4
            # full) gives true parallelism with a session per worker task.
            for company in companies:
                await one(company)

            run.jobs_new = len(all_new)
            if all_new:
                stats = await match_jobs(session, embedder, all_new)
                run.jobs_matched = stats.matched

            await _send_digest(session, run, scanned=len(companies))

            run.status = (
                "completed" if run.companies_failed == 0 else "completed_with_errors"
            )
            run.finished_at = utcnow()
            await session.commit()
            log.info(
                "scan run done: {}/{} companies ok, {} new, {} matched",
                run.companies_ok, run.companies_total, run.jobs_new, run.jobs_matched,
            )
            return run_id
    finally:
        await fetcher.aclose()
