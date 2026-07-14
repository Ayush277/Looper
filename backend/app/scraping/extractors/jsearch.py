"""JSearch (RapidAPI) client — powers the search-engine strategy and global
discovery. Wraps Google-for-Jobs data: reaches postings on portals that block
direct crawling (docs/15).

Quota-aware: free tier is limited, so callers make at most ONE request per
company per scan; results are only fetched for companies whose direct
strategies failed.
"""
import contextlib
import json
from datetime import datetime

import httpx
from loguru import logger

from app.config import get_settings
from app.scraping.types import FetchError, RawJob

API = "https://jsearch.p.rapidapi.com/search"


async def jsearch_jobs(
    query: str, country: str = "in", employer_filter: str | None = None
) -> list[RawJob]:
    key = get_settings().jsearch_api_key
    if not key:
        raise FetchError(API, "not_configured (JSEARCH_API_KEY missing)")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            API,
            params={"query": query, "country": country, "page": 1, "num_pages": 1},
            headers={"x-rapidapi-host": "jsearch.p.rapidapi.com", "x-rapidapi-key": key},
        )
    if resp.status_code == 429:
        raise FetchError(API, "jsearch quota exceeded")
    if resp.status_code != 200:
        raise FetchError(API, f"jsearch HTTP {resp.status_code}")
    try:
        items = resp.json().get("data", [])
    except json.JSONDecodeError as exc:
        raise FetchError(API, "jsearch bad JSON") from exc

    jobs: list[RawJob] = []
    for j in items:
        employer = (j.get("employer_name") or "").lower()
        if employer_filter and employer_filter.lower() not in employer:
            continue
        title = j.get("job_title")
        url = j.get("job_apply_link")
        if not title or not url:
            continue
        posted = None
        if isinstance(j.get("job_posted_at_datetime_utc"), str):
            with contextlib.suppress(ValueError):
                posted = datetime.fromisoformat(
                    j["job_posted_at_datetime_utc"].replace("Z", "+00:00")
                ).date()
        location = ", ".join(
            p for p in [j.get("job_city"), j.get("job_state"), j.get("job_country")] if p
        ) or None
        try:
            jobs.append(
                RawJob(
                    title=title,
                    apply_url=url,
                    location=location,
                    external_id=j.get("job_id"),
                    posted_at=posted,
                    description_snippet=(j.get("job_description") or "")[:1000] or None,
                )
            )
        except ValueError:
            continue
    logger.info("jsearch '{}' ({}): {} jobs{}", query, country, len(jobs),
                f" [employer≈{employer_filter}]" if employer_filter else "")
    return jobs
