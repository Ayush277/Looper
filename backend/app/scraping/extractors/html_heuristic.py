"""Heuristic extraction of job listings from arbitrary careers-page HTML.

Approach: find the densest cluster of same-shaped links whose href looks like
a job posting (contains /job/, /jobs/, /careers/, /position/, an id-like tail…)
and whose text looks like a title. Deliberately conservative: bad extractions
poison the pipeline, empty ones just trigger the next strategy.
"""
import re
from collections import defaultdict
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.scraping.types import RawJob

JOB_HREF = re.compile(
    r"/(jobs?|careers?|positions?|openings?|opportunit|vacanc|requisition|posting)[s/\-_?#]",
    re.I,
)
# Real job postings carry a requisition/post id; category & nav pages don't.
JOB_ID = re.compile(r"\d{3,}|[?&](gh_jid|jid|jobid|lever-id)=", re.I)
NOISE_TEXT = re.compile(
    r"^(apply|learn more|read more|view|see|all jobs|search|home|about|share|save)\b"
    r"|\(\s*\d+\s*\)\s*$",  # "Product Development ( 475 )" = category filter, not a job
    re.I,
)


def _looks_like_job_link(href: str, text: str) -> bool:
    if not href or not text or len(text) < 4 or len(text) > 140:
        return False
    if NOISE_TEXT.search(text.strip()):
        return False
    return bool(JOB_HREF.search(href)) and bool(JOB_ID.search(href))


def _container_signature(a_tag) -> str:  # type: ignore[no-untyped-def]
    """Group links by their structural position (parent chain of tag names/classes)."""
    parts = []
    node = a_tag
    for _ in range(3):
        node = node.parent
        if node is None or node.name is None:
            break
        cls = ".".join(sorted(node.get("class", []))[:2])
        parts.append(f"{node.name}[{cls}]")
    return ">".join(parts)


def extract_html_jobs(html: str, page_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "lxml")
    groups: dict[str, list[RawJob]] = defaultdict(list)

    for a in soup.find_all("a", href=True):
        if not isinstance(a, Tag):
            continue
        text = a.get_text(" ", strip=True)
        href = str(a.get("href") or "")
        if not _looks_like_job_link(href, text):
            continue
        url = urljoin(page_url, href)
        location = None
        parent = a.find_parent(["li", "tr", "article", "div"])
        if parent:
            parent_text = parent.get_text(" | ", strip=True)
            after = parent_text.split(text, 1)
            if len(after) == 2:
                candidate = after[1].strip(" |").split("|")[0].strip()
                if 2 < len(candidate) < 80:
                    location = candidate
        try:
            job = RawJob(title=text, apply_url=url, location=location)
        except ValueError:
            continue
        groups[_container_signature(a)].append(job)

    if not groups:
        return []
    # The densest structural group is the job list; singletons are nav noise.
    best = max(groups.values(), key=len)
    if len(best) < 3:
        logger.debug("html_heuristic found no dense job cluster on {}", page_url)
        return []
    # De-dup within the page by apply_url.
    seen: set[str] = set()
    unique = []
    for j in best:
        if j.apply_url not in seen:
            seen.add(j.apply_url)
            unique.append(j)
    logger.debug("html_heuristic extracted {} jobs from {}", len(unique), page_url)
    return unique
