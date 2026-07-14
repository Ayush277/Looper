"""The only component that touches the network for scraping (docs/06 §3).

Politeness enforced centrally: per-domain min-interval throttle, rotating
realistic user agents, exponential backoff with jitter on transient failures,
robots.txt consultation. Throttle/cache state is in-process for now; it moves
to Redis in M4 when multiple workers exist.
"""
import asyncio
import random
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger

from app.scraping.types import FetchError, FetchResponse

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}


class Fetcher:
    def __init__(
        self,
        min_domain_interval: float = 2.0,
        max_attempts: int = 3,
        timeout: float = 20.0,
        respect_robots: bool = True,
    ):
        self.min_domain_interval = min_domain_interval
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.respect_robots = respect_robots
        self._last_hit: dict[str, float] = {}
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self._client = httpx.AsyncClient(follow_redirects=True, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, url: str, *, is_json: bool = False) -> FetchResponse:
        return await self._request("GET", url, is_json=is_json)

    async def post_json(self, url: str, body: dict[str, object]) -> FetchResponse:
        """POST a JSON body (Workday CxS-style search endpoints)."""
        return await self._request("POST", url, is_json=True, json_body=body)

    async def _request(
        self,
        method: str,
        url: str,
        *,
        is_json: bool = False,
        json_body: dict[str, object] | None = None,
    ) -> FetchResponse:
        domain = urlsplit(url).netloc.lower()
        if self.respect_robots and not await self._robots_allowed(url, domain):
            raise FetchError(url, "disallowed by robots.txt")

        lock = self._domain_locks.setdefault(domain, asyncio.Lock())
        last_error = "unknown"
        for attempt in range(1, self.max_attempts + 1):
            async with lock:
                await self._throttle(domain)
                ua = random.choice(USER_AGENTS)
                headers = {"User-Agent": ua, "Accept-Language": "en"}
                if is_json:
                    headers["Accept"] = "application/json"
                try:
                    resp = await self._client.request(
                        method, url, headers=headers, json=json_body
                    )
                except httpx.HTTPError as exc:
                    last_error = f"{exc.__class__.__name__}: {exc}"
                    logger.debug("fetch attempt {} failed: {} ({})", attempt, url, last_error)
                    await self._backoff(attempt)
                    continue

            if resp.status_code in TRANSIENT_STATUSES:
                last_error = f"HTTP {resp.status_code}"
                logger.debug("fetch attempt {} got {}: {}", attempt, resp.status_code, url)
                await self._backoff(attempt)
                continue

            return FetchResponse(
                url=str(resp.url),
                status_code=resp.status_code,
                text=resp.text,
                content_type=resp.headers.get("content-type", ""),
            )

        raise FetchError(url, f"exhausted {self.max_attempts} attempts, last: {last_error}")

    async def _throttle(self, domain: str) -> None:
        elapsed = time.monotonic() - self._last_hit.get(domain, 0.0)
        wait = self.min_domain_interval - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_hit[domain] = time.monotonic()

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep((2**attempt) + random.uniform(0, 1))

    async def _robots_allowed(self, url: str, domain: str) -> bool:
        if domain not in self._robots:
            parser = RobotFileParser()
            try:
                resp = await self._client.get(
                    f"https://{domain}/robots.txt",
                    headers={"User-Agent": USER_AGENTS[0]},
                    timeout=8.0,
                )
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                    self._robots[domain] = parser
                else:
                    self._robots[domain] = None  # no rules -> allowed
            except httpx.HTTPError:
                self._robots[domain] = None
        parser_or_none = self._robots[domain]
        if parser_or_none is None:
            return True
        return parser_or_none.can_fetch("*", url)
