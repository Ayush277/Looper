"""Company-specific job-API adapters for portals with stable public JSON
endpoints that generic probing can't discover (Amazon, Microsoft).

Registered by lowercase company name; the job_api strategy consults this
registry before generic ATS probing.
"""
import contextlib
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from loguru import logger

from app.scraping.fetcher import Fetcher
from app.scraping.types import RawJob

Adapter = Callable[[Fetcher], Awaitable[list[RawJob]]]


async def amazon(fetcher: Fetcher) -> list[RawJob]:
    """amazon.jobs search API. Filtered to intern-ish queries to bound volume —
    Amazon lists tens of thousands of roles; we only ever need the early-career slice.
    """
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for query in ("intern", "graduate"):
        url = (
            "https://www.amazon.jobs/en/search.json"
            f"?base_query={query}&result_limit=100&offset=0&sort=recent"
        )
        resp = await fetcher.get(url, is_json=True)
        if resp.status_code != 200:
            continue
        data: dict[str, Any] = json.loads(resp.text)
        for j in data.get("jobs", []):
            path = j.get("job_path", "")
            if not path or path in seen:
                continue
            seen.add(path)
            posted = None
            with contextlib.suppress(ValueError):
                posted = datetime.strptime(j.get("posted_date", ""), "%B %d, %Y").date()
            try:
                jobs.append(
                    RawJob(
                        title=j["title"],
                        apply_url=f"https://www.amazon.jobs{path}",
                        location=j.get("normalized_location") or j.get("location"),
                        external_id=j.get("id_icims") or j.get("id"),
                        posted_at=posted,
                        description_snippet=(j.get("description_short") or "")[:1000] or None,
                    )
                )
            except (KeyError, ValueError):
                continue
    if jobs:
        logger.info("amazon adapter: {} jobs", len(jobs))
    return jobs


async def microsoft(fetcher: Fetcher) -> list[RawJob]:
    """Microsoft careers search API (gcsservices). Early-career filtered."""
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for query in ("intern", "graduate"):
        url = (
            "https://gcsservices.careers.microsoft.com/search/api/v1/search"
            f"?q={query}&l=en_us&pg=1&pgSz=100"
        )
        resp = await fetcher.get(url, is_json=True)
        if resp.status_code != 200:
            continue
        try:
            data: dict[str, Any] = json.loads(resp.text)
            items = data["operationResult"]["result"]["jobs"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        for j in items:
            job_id = str(j.get("jobId", ""))
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)
            props = j.get("properties") or {}
            locations = props.get("locations") or []
            posted = None
            if isinstance(j.get("postingDate"), str):
                with contextlib.suppress(ValueError):
                    posted = datetime.fromisoformat(
                        j["postingDate"].replace("Z", "+00:00")
                    ).date()
            try:
                jobs.append(
                    RawJob(
                        title=j["title"],
                        apply_url=f"https://jobs.careers.microsoft.com/global/en/job/{job_id}",
                        location=", ".join(locations[:2]) or props.get("primaryLocation"),
                        external_id=job_id,
                        posted_at=posted,
                    )
                )
            except (KeyError, ValueError):
                continue
    if jobs:
        logger.info("microsoft adapter: {} jobs", len(jobs))
    return jobs


ADAPTERS: dict[str, Adapter] = {
    "amazon": amazon,
    "microsoft": microsoft,
}
