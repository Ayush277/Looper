"""Known-ATS JSON endpoints — the most stable extraction path when applicable.

Given a careers URL (or a company slug guess), probe the uniform public APIs of
Greenhouse, Lever, Ashby and Workday(CxS). Each prober returns [] quietly when
the company isn't on that ATS.
"""
import json
import re
from datetime import datetime

from loguru import logger

from app.scraping.fetcher import Fetcher
from app.scraping.types import FetchError, RawJob


def _slug_candidates(company_name: str, careers_url: str | None) -> list[str]:
    """Slugs to probe. Name-guessed slugs are only trusted when the company has
    no careers URL of its own (or the URL is already on an ATS domain) —
    otherwise a name collision can return a *different* company's board
    (observed: a Greenhouse test board squatting on a big-co name).
    """
    slugs = []
    url_is_ats = False
    if careers_url:
        m = re.search(
            r"(?:greenhouse\.io|lever\.co|ashbyhq\.com|myworkdayjobs\.com|smartrecruiters\.com)"
            r"/([\w\-]+)",
            careers_url,
        )
        if m:
            slugs.append(m.group(1).lower())
            url_is_ats = True
        m = re.search(r"https?://([\w\-]+)\.wd\d+\.myworkdayjobs\.com", careers_url)
        if m:
            slugs.append(m.group(1).lower())
            url_is_ats = True
    if not careers_url or url_is_ats:
        base = re.sub(r"[^a-z0-9]", "", company_name.lower())
        slugs.extend([base, company_name.lower().replace(" ", "-")])
    return list(dict.fromkeys(slugs))


async def _greenhouse(fetcher: Fetcher, slug: str) -> list[RawJob]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    resp = await fetcher.get(url, is_json=True)
    if resp.status_code != 200:
        return []
    data = json.loads(resp.text)
    jobs = []
    for j in data.get("jobs", []):
        try:
            jobs.append(
                RawJob(
                    title=j["title"],
                    apply_url=j["absolute_url"],
                    location=(j.get("location") or {}).get("name"),
                    external_id=str(j.get("id", "")) or None,
                    posted_at=_iso_date(j.get("updated_at")),
                )
            )
        except (KeyError, ValueError):
            continue
    return jobs


async def _lever(fetcher: Fetcher, slug: str) -> list[RawJob]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    resp = await fetcher.get(url, is_json=True)
    if resp.status_code != 200:
        return []
    data = json.loads(resp.text)
    if not isinstance(data, list):
        return []
    jobs = []
    for j in data:
        try:
            jobs.append(
                RawJob(
                    title=j["text"],
                    apply_url=j["hostedUrl"],
                    location=(j.get("categories") or {}).get("location"),
                    external_id=j.get("id"),
                    posted_at=_epoch_date(j.get("createdAt")),
                )
            )
        except (KeyError, ValueError):
            continue
    return jobs


async def _ashby(fetcher: Fetcher, slug: str) -> list[RawJob]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    resp = await fetcher.get(url, is_json=True)
    if resp.status_code != 200:
        return []
    data = json.loads(resp.text)
    jobs = []
    for j in data.get("jobs", []):
        try:
            jobs.append(
                RawJob(
                    title=j["title"],
                    apply_url=j.get("jobUrl") or j.get("applyUrl", ""),
                    location=j.get("location"),
                    external_id=j.get("id"),
                )
            )
        except (KeyError, ValueError):
            continue
    return jobs


async def _smartrecruiters(fetcher: Fetcher, slug: str) -> list[RawJob]:
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
    resp = await fetcher.get(url, is_json=True)
    if resp.status_code != 200:
        return []
    data = json.loads(resp.text)
    jobs = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        city = loc.get("city")
        country = loc.get("country")
        location = ", ".join(p for p in [city, (country or "").upper() or None] if p) or None
        try:
            jobs.append(
                RawJob(
                    title=j["name"],
                    apply_url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
                    location=location,
                    external_id=str(j.get("id")),
                    posted_at=_iso_date(j.get("releasedDate")),
                )
            )
        except (KeyError, ValueError):
            continue
    return jobs


def _iso_date(value: object):  # type: ignore[no-untyped-def]
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _epoch_date(value: object):  # type: ignore[no-untyped-def]
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000).date()
    return None


PROBERS = [
    ("greenhouse", _greenhouse),
    ("lever", _lever),
    ("ashby", _ashby),
    ("smartrecruiters", _smartrecruiters),
]


async def probe_ats(
    fetcher: Fetcher, company_name: str, careers_url: str | None
) -> list[RawJob]:
    for slug in _slug_candidates(company_name, careers_url)[:3]:
        for ats_name, prober in PROBERS:
            try:
                jobs = await prober(fetcher, slug)
            except (FetchError, json.JSONDecodeError):
                continue
            if jobs:
                logger.info("ats probe hit: {} on {} ({} jobs)", slug, ats_name, len(jobs))
                return jobs
    return []
