"""Generate a self-contained premium jobs dashboard from the database.

Run after each scan; the GitHub Actions workflow publishes the output to
GitHub Pages — a public, always-available, hourly-updated dashboard of every
matched early-career India role. No email dependency, no server.

  python -m app.export_page  ->  writes site/index.html

Design: Hallmark · genre modern-minimal · theme Cobalt · macrostructure Workbench.
"""
import asyncio
import json
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.engine import SessionFactory
from app.db.models import Company, Job

OUT = Path("site/index.html")
TEMPLATE = Path(__file__).parent / "dashboard_template.html"


def _classify_type(title: str, snippet: str) -> str:
    t = f"{title} {snippet}".lower()
    if "intern" in t:
        return "Internship"
    return "Full-time"


def _classify_mode(location: str, snippet: str) -> str:
    t = f"{location} {snippet}".lower()
    if "remote" in t or "work from home" in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if "onsite" in t or "on-site" in t or "in office" in t:
        return "On-site"
    return "On-site"


async def collect() -> list[dict[str, object]]:
    async with SessionFactory() as session:
        rows = (
            await session.execute(
                select(Job, Company.name)
                .join(Company, Company.id == Job.company_id)
                .where(Job.status == "matched")
                .order_by(Job.posted_at.desc().nulls_last(), Job.first_seen_at.desc())
            )
        ).all()
    jobs: list[dict[str, object]] = []
    for job, company in rows:
        reasons = [
            str(r.get("term"))
            for r in (job.match_reasons or [])
            if r.get("kind") not in ("exclude", "gate")
        ]
        snippet = job.description_snippet or ""
        jobs.append(
            {
                "id": job.content_hash,
                "company": company,
                "title": job.title,
                "location": job.location or "India",
                "type": _classify_type(job.title, snippet),
                "mode": _classify_mode(job.location or "", snippet),
                "posted": str(job.posted_at) if job.posted_at else "",
                "found": job.first_seen_at.strftime("%Y-%m-%d")
                if job.first_seen_at
                else "",
                "batch": snippet,
                "score": round(job.match_score, 2) if job.match_score is not None else None,
                "reasons": reasons[:5],
                "url": job.apply_url,
                "emailed": bool(job.email_sent_at),
            }
        )
    return jobs


async def main() -> None:
    jobs = await collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    updated = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__JOBS_JSON__", json.dumps(jobs))
        .replace("__TOTAL__", str(len(jobs)))
        .replace("__UPDATED__", updated)
        .replace("__TODAY__", date.today().isoformat())
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} with {len(jobs)} matched jobs")


if __name__ == "__main__":
    asyncio.run(main())
