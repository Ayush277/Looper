"""Scraping CLI — the M2 demo surface.

  python -m app.scraping.cli scan-company Google
  python -m app.scraping.cli scan-company Rubrik --url https://... [--save]
  python -m app.scraping.cli scan-all [--save]

--save persists via the dedup insert path (jobs get status=new; matching is M3).
"""
import argparse
import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import SessionFactory
from app.db.models import Company, Job, utcnow
from app.scraping.fetcher import Fetcher
from app.scraping.strategies import run_strategy_chain
from app.scraping.types import ScrapeOutcome
from app.shared.hashing import job_content_hash
from app.shared.logging import setup_logging


async def save_jobs(session: AsyncSession, company: Company, outcome: ScrapeOutcome) -> int:
    """Insert-if-new by content hash; existing jobs get last_seen_at touched."""
    new_count = 0
    for raw in outcome.jobs:
        h = job_content_hash(company.id, raw.title, raw.location, raw.apply_url)
        existing = (
            await session.execute(select(Job).where(Job.content_hash == h))
        ).scalar_one_or_none()
        if existing:
            existing.last_seen_at = utcnow()
            continue
        session.add(
            Job(
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
        )
        new_count += 1
    return new_count


def print_outcome(name: str, outcome: ScrapeOutcome, new_count: int | None = None) -> None:
    print(f"\n=== {name} ===")
    for att in outcome.attempts:
        mark = "✓" if att.ok else "✗"
        detail = f"{att.jobs} jobs" if att.ok else att.error
        print(f"  {mark} {att.strategy}: {detail}")
    if outcome.ok:
        print(f"  strategy used: {outcome.strategy_used}, jobs: {len(outcome.jobs)}")
        if new_count is not None:
            print(f"  new (after dedup): {new_count}")
        for job in outcome.jobs[:8]:
            loc = f" · {job.location}" if job.location else ""
            print(f"    - {job.title}{loc}")
        if len(outcome.jobs) > 8:
            print(f"    … and {len(outcome.jobs) - 8} more")
    else:
        print("  FAILED — no strategy produced jobs")


async def scan_one(
    fetcher: Fetcher, session: AsyncSession, company: Company, save: bool
) -> ScrapeOutcome:
    outcome = await run_strategy_chain(
        fetcher, company.name, company.careers_url, company.preferred_strategy
    )
    company.last_crawl_at = datetime.now(timezone.utc)
    if outcome.ok:
        company.last_success_at = datetime.now(timezone.utc)
        company.preferred_strategy = outcome.strategy_used
        company.consecutive_failures = 0
        company.health = "healthy"
    else:
        company.consecutive_failures += 1
        company.health = "degraded" if company.consecutive_failures < 3 else "failing"
    new_count = None
    if save and outcome.ok:
        new_count = await save_jobs(session, company, outcome)
    await session.commit()
    print_outcome(company.name, outcome, new_count)
    return outcome


async def main() -> None:
    parser = argparse.ArgumentParser(prog="loopjob-scrape")
    sub = parser.add_subparsers(dest="cmd", required=True)
    one = sub.add_parser("scan-company")
    one.add_argument("name")
    one.add_argument("--url", help="override/set careers URL")
    one.add_argument("--save", action="store_true")
    all_p = sub.add_parser("scan-all")
    all_p.add_argument("--save", action="store_true")
    args = parser.parse_args()

    setup_logging()
    fetcher = Fetcher()
    try:
        async with SessionFactory() as session:
            if args.cmd == "scan-company":
                company = (
                    await session.execute(select(Company).where(Company.name == args.name))
                ).scalar_one_or_none()
                if company is None:
                    logger.error("company {} not found — run `make seed`?", args.name)
                    return
                if args.url:
                    company.careers_url = args.url
                await scan_one(fetcher, session, company, args.save)
            else:
                companies = (
                    (
                        await session.execute(
                            select(Company).where(Company.status == "active")
                        )
                    )
                    .scalars()
                    .all()
                )
                ok = 0
                for company in companies:
                    outcome = await scan_one(fetcher, session, company, args.save)
                    ok += outcome.ok
                print(f"\n{ok}/{len(companies)} companies scannable")
    finally:
        await fetcher.aclose()


if __name__ == "__main__":
    asyncio.run(main())
