"""Playwright rendering escalation — used only when static HTML is a JS shell.

One shared headless Chromium per process, lazily launched, pages pooled to one
at a time (personal-scale). If Playwright/browsers aren't installed the
renderer reports unavailable and the strategy chain simply moves on.
"""
import asyncio
import contextlib
from typing import Any

from loguru import logger

from app.scraping.types import FetchError, FetchResponse

RENDER_TIMEOUT_MS = 30_000
SETTLE_MS = 2_500


def looks_like_js_shell(html: str) -> bool:
    """Heuristic: page has scripts but almost no visible text content."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return len(text) < 400


class Renderer:
    def __init__(self) -> None:
        self._browser: Any = None
        self._pw: Any = None
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        try:
            import playwright  # noqa: F401

            return True
        except ImportError:
            return False

    async def render(self, url: str) -> FetchResponse:
        if not self.available:
            raise FetchError(url, "playwright not installed")
        async with self._lock:  # one page at a time
            try:
                if self._browser is None:
                    from playwright.async_api import async_playwright

                    self._pw = await async_playwright().start()
                    self._browser = await self._pw.chromium.launch(headless=True)
                page = await self._browser.new_page()
                try:
                    await page.goto(url, timeout=RENDER_TIMEOUT_MS, wait_until="domcontentloaded")
                    # Lazy-loading portals paint their list well after DOMContentLoaded:
                    # wait for network to settle, then scroll to trigger lazy batches.
                    with contextlib.suppress(Exception):  # busy pages never go idle
                        await page.wait_for_load_state("networkidle", timeout=12_000)
                    for _ in range(4):
                        await page.mouse.wheel(0, 2400)
                        await page.wait_for_timeout(700)
                    await page.wait_for_timeout(SETTLE_MS)
                    html = await page.content()
                    final_url = page.url
                finally:
                    await page.close()
            except FetchError:
                raise
            except Exception as exc:  # noqa: BLE001 — playwright raises many types
                raise FetchError(url, f"render failed: {exc.__class__.__name__}") from exc
        logger.debug("rendered {} ({} bytes)", url, len(html))
        return FetchResponse(url=final_url, status_code=200, text=html, content_type="text/html")

    async def aclose(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._pw is not None:
            await self._pw.stop()
