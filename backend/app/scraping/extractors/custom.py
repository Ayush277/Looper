"""Company-specific job-API adapters for portals with stable public JSON
endpoints that generic probing can't discover (Amazon, Microsoft).

Registered by lowercase company name; the job_api strategy consults this
registry before generic ATS probing.
"""
import contextlib
import json
import re
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

    A global "intern" search is dominated by US/CN/EU listings, so India-targeted
    passes run explicitly (normalized_country_code) — otherwise India postings
    never appear in the first page of results.
    """
    jobs: list[RawJob] = []
    seen: set[str] = set()
    queries = [
        # (base_query, extra params) — global early-career + India-specific passes
        ("intern", ""),
        ("graduate", ""),
        ("intern", "&normalized_country_code%5B%5D=IND"),
        ("software engineer", "&normalized_country_code%5B%5D=IND"),
        ("university", "&normalized_country_code%5B%5D=IND"),
    ]
    for query, extra in queries:
        url = (
            "https://www.amazon.jobs/en/search.json"
            f"?base_query={query}&result_limit=100&offset=0&sort=recent{extra}"
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


async def uber(fetcher: Fetcher) -> list[RawJob]:
    """Uber's careers search API. It rejects requests without a CSRF header;
    a placeholder token satisfies the check for this public search endpoint."""
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for query in ("intern", "university", "new grad"):
        resp = await fetcher.post_json(
            "https://www.uber.com/api/loadSearchJobsResults?localeCode=en",
            {"params": {"query": query}, "page": 0, "limit": 100},
            extra_headers={"x-csrf-token": "x"},
        )
        if resp.status_code != 200:
            continue
        try:
            # A query with no hits returns results: null, not [].
            results = json.loads(resp.text)["data"]["results"] or []
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        for j in results:
            job_id = str(j.get("id", ""))
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)
            loc = j.get("location") or {}
            location = ", ".join(
                p for p in [loc.get("city"), loc.get("countryName")] if p
            ) or None
            posted = None
            if isinstance(j.get("creationDate"), str):
                with contextlib.suppress(ValueError):
                    posted = datetime.fromisoformat(
                        j["creationDate"].replace("Z", "+00:00")
                    ).date()
            try:
                jobs.append(
                    RawJob(
                        title=j["title"],
                        apply_url=f"https://www.uber.com/careers/list/{job_id}/",
                        location=location,
                        external_id=job_id,
                        posted_at=posted,
                    )
                )
            except (KeyError, ValueError):
                continue
    if jobs:
        logger.info("uber adapter: {} jobs", len(jobs))
    return jobs


_SLUG_TAIL = re.compile(r"/jobs/\d+/([^/]+)/job", re.I)


async def atlassian(fetcher: Fetcher) -> list[RawJob]:
    """Atlassian publishes a full listings feed; titles live in the URL slug
    (the feed itself carries no title field)."""
    resp = await fetcher.get(
        "https://www.atlassian.com/endpoint/careers/listings", is_json=True
    )
    if resp.status_code != 200:
        return []
    try:
        items = json.loads(resp.text)
    except json.JSONDecodeError:
        return []
    jobs: list[RawJob] = []
    for item in items:
        post = item.get("portalJobPost") or {}
        url = post.get("portalUrl")
        if not url:
            continue
        title = post.get("title")
        if not title:
            m = _SLUG_TAIL.search(url)
            if not m:
                continue
            title = m.group(1).replace("-", " ").strip().title()
        posted = None
        if isinstance(post.get("updatedDate"), str):
            with contextlib.suppress(ValueError):
                posted = datetime.fromisoformat(post["updatedDate"][:10]).date()
        try:
            jobs.append(
                RawJob(
                    title=title,
                    apply_url=url,
                    external_id=str(post.get("id")) if post.get("id") else None,
                    posted_at=posted,
                )
            )
        except ValueError:
            continue
    if jobs:
        logger.info("atlassian adapter: {} jobs", len(jobs))
    return jobs


async def debugwithshubham(fetcher: Fetcher) -> list[RawJob]:
    """DebugWithShubham job board — a curated India-focused feed of fresher /
    2026-2027-batch roles across many employers (its own aggregation of company
    postings). One source unlocks dozens of companies. Employer name is folded
    into the title; the batch/experience tag drives the early-career + 2027
    signals downstream."""
    jobs: list[RawJob] = []
    seen: set[str] = set()
    base = "https://debugwithshubham-web-page.onrender.com/api/jobs/"
    for page in range(1, 8):  # ~70 most-recent postings, both types
        resp = await fetcher.get(f"{base}?page={page}&limit=100", is_json=True)
        if resp.status_code != 200:
            break
        try:
            items = json.loads(resp.text)
        except json.JSONDecodeError:
            break
        if not items:
            break
        for j in items:
            jid = str(j.get("id", ""))
            role = (j.get("role") or "").strip()
            url = j.get("apply_url")
            if not jid or jid in seen or not role or not url:
                continue
            seen.add(jid)
            employer = (j.get("company_name") or "").strip()
            title = f"{employer} · {role}" if employer else role
            # Fold batch/experience/type into the snippet so the gates can read
            # "Fresher", "Batch 2026/2027", etc.
            snippet = " | ".join(
                p for p in [j.get("experience"), j.get("job_type"), j.get("work_type")]
                if p and str(p).strip()
            ) or None
            posted = None
            if isinstance(j.get("posted_at"), str):
                with contextlib.suppress(ValueError):
                    posted = datetime.fromisoformat(j["posted_at"][:19]).date()
            try:
                jobs.append(
                    RawJob(
                        title=title,
                        apply_url=url,
                        location=j.get("location"),
                        external_id=jid,
                        posted_at=posted,
                        description_snippet=snippet,
                    )
                )
            except (KeyError, ValueError):
                continue
    if jobs:
        logger.info("debugwithshubham adapter: {} jobs", len(jobs))
    return jobs


ADAPTERS: dict[str, Adapter] = {
    "amazon": amazon,
    "microsoft": microsoft,
    "uber": uber,
    "atlassian": atlassian,
    "debugwithshubham": debugwithshubham,
    "job board (india)": debugwithshubham,
}
