"""Notifier implementations: Resend (prod) and Console (dev / no key)."""
from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from app.config import get_settings
from app.notifications.base import Digest, Notifier, NotifyResult

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


def render_digest_html(digest: Digest) -> str:
    return _env.get_template("digest.html").render(
        jobs=digest.jobs,
        scanned_companies=digest.scanned_companies,
        scan_time=digest.scan_time,
    )


def render_digest_text(digest: Digest) -> str:
    lines = [f"LoopJob — {len(digest.jobs)} new matches", ""]
    for j in digest.jobs:
        lines += [
            f"{j.company}: {j.title}" + (f" · {j.location}" if j.location else ""),
            f"  matched: {', '.join(j.reasons)}",
            f"  apply: {j.apply_url}",
            "",
        ]
    lines.append(f"Scanned {digest.scanned_companies} companies at {digest.scan_time}")
    return "\n".join(lines)


class ResendNotifier:
    name = "resend"

    def __init__(self, api_key: str, sender: str = "LoopJob <onboarding@resend.dev>"):
        self._api_key = api_key
        self._sender = sender

    async def send(self, recipient: str, digest: Digest) -> NotifyResult:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._sender,
                    "to": [recipient],
                    "subject": digest.subject,
                    "html": render_digest_html(digest),
                    "text": render_digest_text(digest),
                },
            )
        if resp.status_code in (200, 201):
            return NotifyResult(ok=True, provider_message_id=resp.json().get("id"))
        return NotifyResult(ok=False, error=f"resend HTTP {resp.status_code}: {resp.text[:200]}")


class ConsoleNotifier:
    """Dev notifier — prints the digest instead of sending (no key required)."""

    name = "console"

    async def send(self, recipient: str, digest: Digest) -> NotifyResult:
        logger.info("=== EMAIL (console notifier) to {} ===\n{}", recipient,
                    render_digest_text(digest))
        return NotifyResult(ok=True, provider_message_id="console")


def get_notifier() -> Notifier:
    settings = get_settings()
    if settings.resend_api_key:
        return ResendNotifier(settings.resend_api_key)
    return ConsoleNotifier()
