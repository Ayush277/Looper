"""Extract schema.org JobPosting objects embedded as JSON-LD.

Many career pages embed these for Google Jobs indexing — the most reliable
zero-API extraction path.
"""
import json
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger

from app.scraping.types import RawJob


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _location_of(posting: dict[str, Any]) -> str | None:
    loc = posting.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            parts = [
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("addressCountry"),
            ]
            joined = ", ".join(str(p) for p in parts if p)
            return joined or None
        if isinstance(addr, str):
            return addr
    return None


def _job_from_posting(posting: dict[str, Any], page_url: str) -> RawJob | None:
    title = posting.get("title")
    url = posting.get("url") or posting.get("sameAs") or page_url
    if not title or not isinstance(title, str):
        return None
    desc = posting.get("description")
    snippet = None
    if isinstance(desc, str):
        snippet = BeautifulSoup(desc, "lxml").get_text(" ", strip=True)[:1000]
    ident = posting.get("identifier")
    external_id = None
    if isinstance(ident, dict):
        external_id = str(ident.get("value")) if ident.get("value") else None
    elif isinstance(ident, str | int):
        external_id = str(ident)
    try:
        return RawJob(
            title=title.strip(),
            apply_url=str(url),
            location=_location_of(posting),
            external_id=external_id,
            posted_at=_parse_date(posting.get("datePosted")),
            description_snippet=snippet,
        )
    except ValueError:
        return None


def _walk(node: object) -> list[dict[str, Any]]:
    """Find JobPosting dicts anywhere in a JSON-LD structure (incl. @graph)."""
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if node.get("@type") == "JobPosting":
            found.append(node)
        for value in node.values():
            found.extend(_walk(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk(item))
    return found


def extract_jsonld_jobs(html: str, page_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "lxml")
    jobs: list[RawJob] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for posting in _walk(data):
            job = _job_from_posting(posting, page_url)
            if job:
                jobs.append(job)
    if jobs:
        logger.debug("jsonld extracted {} jobs from {}", len(jobs), page_url)
    return jobs
