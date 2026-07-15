"""The adaptive strategy chain (docs/06 D4, docs/07 §2).

Order: preferred (last-successful) strategy first, then the remaining chain in
priority order. First strategy yielding jobs wins; every attempt is recorded.
Search-engine / fallback-search / LLM strategies are stubs until their
dependencies land (search backend config, M3 LLM interface) — they report
"not_configured" and the chain moves on.
"""
from collections.abc import Awaitable, Callable

from loguru import logger

from app.scraping.extractors.ats import probe_ats
from app.scraping.extractors.custom import ADAPTERS
from app.scraping.extractors.html_heuristic import extract_html_jobs
from app.scraping.extractors.jsearch import jsearch_jobs
from app.scraping.extractors.jsonld import extract_jsonld_jobs
from app.scraping.extractors.workday import fetch_workday_jobs
from app.scraping.fetcher import Fetcher
from app.scraping.renderer import Renderer, looks_like_js_shell
from app.scraping.types import (
    FetchError,
    RawJob,
    ScrapeOutcome,
    Strategy,
    StrategyAttempt,
)

StrategyFn = Callable[[Fetcher, str, str | None], Awaitable[list[RawJob]]]


_renderer = Renderer()


def _extract_page(html: str, url: str) -> list[RawJob]:
    jobs = extract_jsonld_jobs(html, url)
    return jobs if jobs else extract_html_jobs(html, url)


async def careers_page(
    fetcher: Fetcher, company_name: str, careers_url: str | None
) -> list[RawJob]:
    """Static fetch of the careers page (JSON-LD → HTML heuristics), escalating
    to Playwright rendering when the response is a JS shell."""
    if not careers_url:
        return []
    try:
        resp = await fetcher.get(careers_url)
    except FetchError:
        resp = None  # hard block (e.g. UA filtering) — try a real browser below
    if resp is not None and resp.status_code == 200:
        jobs = _extract_page(resp.text, resp.url)
        if jobs:
            return jobs
        if not looks_like_js_shell(resp.text):
            return []
    elif resp is not None and resp.status_code not in (403, 406, 451, 429):
        raise FetchError(careers_url, f"HTTP {resp.status_code}")
    if _renderer.available:
        logger.debug("escalating {} to Playwright", company_name)
        rendered = await _renderer.render(careers_url)
        return _extract_page(rendered.text, rendered.url)
    raise FetchError(careers_url, "blocked/JS shell and renderer unavailable")


async def job_api(
    fetcher: Fetcher, company_name: str, careers_url: str | None
) -> list[RawJob]:
    """Priority: company-specific adapter → Workday CxS (from URL) → generic ATS probe."""
    adapter = ADAPTERS.get(company_name.lower())
    if adapter is not None:
        jobs = await adapter(fetcher)
        if jobs:
            return jobs
    if careers_url and "myworkdayjobs.com" in careers_url:
        jobs = await fetch_workday_jobs(fetcher, careers_url)
        if jobs:
            return jobs
    return await probe_ats(fetcher, company_name, careers_url)


async def search_engine(
    fetcher: Fetcher, company_name: str, careers_url: str | None
) -> list[RawJob]:
    """Query the JSearch index (Google for Jobs) — bypasses bot-gated portals.
    One request per company per scan; employer-filtered for precision."""
    return await jsearch_jobs(
        f"software engineer intern OR graduate at {company_name}",
        country="in",
        employer_filter=company_name,
    )


async def fallback_search(
    fetcher: Fetcher, company_name: str, careers_url: str | None
) -> list[RawJob]:
    """Wider net: same index, US board, still employer-filtered."""
    return await jsearch_jobs(
        f"{company_name} software engineer intern",
        country="us",
        employer_filter=company_name,
    )


async def llm_extraction(
    fetcher: Fetcher, company_name: str, careers_url: str | None
) -> list[RawJob]:
    raise FetchError("llm", "not_configured (arrives with M3 embed/LLM interface)")


CHAIN: list[tuple[Strategy, StrategyFn]] = [
    (Strategy.CAREERS_PAGE, careers_page),
    (Strategy.JOB_API, job_api),
    (Strategy.SEARCH_ENGINE, search_engine),
    (Strategy.FALLBACK_SEARCH, fallback_search),
    (Strategy.LLM_EXTRACTION, llm_extraction),
]


# Portals whose JSON API is strictly better than scraping their rendered page:
# the page shows only the first ~20 cards, the API exposes the full searchable
# board. Try job_api first for these regardless of strategy memory.
_API_FIRST_HOSTS = ("myworkdayjobs.com", "greenhouse.io", "lever.co", "ashbyhq.com")


def _api_first(company_name: str, careers_url: str | None) -> bool:
    if company_name.lower() in ADAPTERS:
        return True
    url = careers_url or ""
    return any(h in url for h in _API_FIRST_HOSTS)


async def run_strategy_chain(
    fetcher: Fetcher,
    company_name: str,
    careers_url: str | None,
    preferred: str | None = None,
) -> ScrapeOutcome:
    if _api_first(company_name, careers_url):
        preferred = Strategy.JOB_API.value
    ordered = sorted(CHAIN, key=lambda pair: pair[0].value != preferred)
    outcome = ScrapeOutcome()
    for strategy, fn in ordered:
        try:
            jobs = await fn(fetcher, company_name, careers_url)
        except FetchError as exc:
            outcome.attempts.append(
                StrategyAttempt(strategy=strategy.value, ok=False, error=exc.cause)
            )
            continue
        except Exception as exc:  # noqa: BLE001 — one strategy must not kill the chain
            logger.exception("strategy {} crashed for {}", strategy.value, company_name)
            outcome.attempts.append(
                StrategyAttempt(strategy=strategy.value, ok=False, error=repr(exc))
            )
            continue
        if jobs:
            outcome.attempts.append(
                StrategyAttempt(strategy=strategy.value, ok=True, jobs=len(jobs))
            )
            outcome.jobs = jobs
            outcome.strategy_used = strategy.value
            return outcome
        outcome.attempts.append(
            StrategyAttempt(strategy=strategy.value, ok=False, error="no jobs extracted")
        )
    return outcome
