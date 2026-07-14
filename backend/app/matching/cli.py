"""Matching CLI — the M3 demo surface.

  python -m app.matching.cli run          # match all status=new jobs
  python -m app.matching.cli run --all    # re-match everything (after keyword edits)
  python -m app.matching.cli report       # show matched jobs with reasons
"""
import argparse
import asyncio

from sqlalchemy import select

from app.db.engine import SessionFactory
from app.db.models import Company, Job
from app.matching.embedders import get_embedder
from app.matching.pipeline import match_jobs
from app.shared.logging import setup_logging


async def run(rematch_all: bool) -> None:
    embedder = get_embedder()
    async with SessionFactory() as session:
        query = select(Job)
        if not rematch_all:
            query = query.where(Job.status == "new")
        jobs = list((await session.execute(query)).scalars().all())
        if not jobs:
            print("nothing to match")
            return
        stats = await match_jobs(session, embedder, jobs)
        print(
            f"processed {stats.processed}: "
            f"{stats.matched} matched, {stats.excluded} excluded, {stats.unmatched} unmatched"
        )


async def report() -> None:
    async with SessionFactory() as session:
        rows = (
            await session.execute(
                select(Job, Company.name)
                .join(Company, Company.id == Job.company_id)
                .where(Job.status == "matched")
                .order_by(Job.match_score.desc())
            )
        ).all()
        print(f"\n{len(rows)} matched jobs\n" + "=" * 60)
        for job, company in rows:
            reasons = ", ".join(
                f"{r['term']}"
                + (f" ({r['similarity']})" if r.get("similarity") is not None else "")
                for r in job.match_reasons
            )
            loc = f" · {job.location}" if job.location else ""
            print(f"[{job.match_score:.2f}] {company}: {job.title}{loc}")
            print(f"       matched: {reasons}")
            print(f"       apply: {job.apply_url[:90]}")


async def main() -> None:
    parser = argparse.ArgumentParser(prog="loopjob-match")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--all", action="store_true", help="re-match every job")
    sub.add_parser("report")
    args = parser.parse_args()

    setup_logging()
    if args.cmd == "run":
        await run(args.all)
    else:
        await report()


if __name__ == "__main__":
    asyncio.run(main())
