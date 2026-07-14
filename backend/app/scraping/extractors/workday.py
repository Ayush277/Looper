"""Workday CxS prober — covers Nvidia/Adobe/Salesforce-class portals.

Workday career sites expose an unauthenticated JSON search endpoint:
  POST https://{tenant}.wd{N}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Tenant/N/site are parsed from the careers URL, e.g.
  https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
"""
import json
import re
from typing import Any

from loguru import logger

from app.scraping.fetcher import Fetcher
from app.scraping.types import RawJob

WD_URL = re.compile(
    r"https?://(?P<tenant>[\w\-]+)\.(?P<wd>wd\d+)\.myworkdayjobs\.com"
    r"(?:/(?:[a-z]{2}-[A-Z]{2}/)?(?P<site>[\w\-]+))?",
)
PAGE_SIZE = 20
MAX_PAGES = 5


def parse_workday_url(careers_url: str) -> tuple[str, str, str] | None:
    m = WD_URL.match(careers_url)
    if not m or not m.group("site"):
        return None
    return m.group("tenant"), m.group("wd"), m.group("site")


async def fetch_workday_jobs(fetcher: Fetcher, careers_url: str) -> list[RawJob]:
    parsed = parse_workday_url(careers_url)
    if parsed is None:
        return []
    tenant, wd, site = parsed
    base = f"https://{tenant}.{wd}.myworkdayjobs.com"
    endpoint = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    jobs: list[RawJob] = []
    for page in range(MAX_PAGES):
        body: dict[str, object] = {
            "limit": PAGE_SIZE,
            "offset": page * PAGE_SIZE,
            "searchText": "",
            "appliedFacets": {},
        }
        resp = await fetcher.post_json(endpoint, body)
        if resp.status_code != 200:
            return jobs
        try:
            data: dict[str, Any] = json.loads(resp.text)
        except json.JSONDecodeError:
            return jobs
        postings = data.get("jobPostings", [])
        for p in postings:
            title = p.get("title")
            path = p.get("externalPath")
            if not title or not path:
                continue
            try:
                jobs.append(
                    RawJob(
                        title=title,
                        apply_url=f"{base}/en-US/{site}{path}",
                        location=p.get("locationsText"),
                        external_id=(p.get("bulletFields") or [None])[0],
                    )
                )
            except ValueError:
                continue
        total = int(data.get("total", 0))
        if (page + 1) * PAGE_SIZE >= total or not postings:
            break
    if jobs:
        logger.info("workday: {} jobs from {}/{}", len(jobs), tenant, site)
    return jobs
