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


TG_API = "https://api.telegram.org/bot{token}/{method}"
TG_LIMIT = 3900  # Telegram hard-caps a message at 4096 chars


def _tg_escape(text: str) -> str:
    """Escape the characters Telegram's MarkdownV2 treats as syntax."""
    for ch in r"_*[]()~`>#+-=|{}.!\\":
        text = text.replace(ch, "\\" + ch)
    return text


def render_digest_telegram(digest: Digest) -> list[str]:
    """Render the digest as one or more MarkdownV2 messages under the size cap."""
    head = f"*LoopJob · {len(digest.jobs)} new match" + (
        "es*" if len(digest.jobs) != 1 else "*"
    )
    chunks: list[str] = []
    buf = [head, ""]
    size = len(head) + 2
    for j in digest.jobs:
        loc = f" · {j.location}" if j.location else ""
        block = (
            f"*{_tg_escape(j.company)}* — [{_tg_escape(j.title)}]({j.apply_url})\n"
            f"_{_tg_escape(loc.lstrip(' ·') or 'India')}_"
            + (f" · posted {_tg_escape(j.posted_at)}" if j.posted_at else "")
            + (
                f"\n`{_tg_escape(' · '.join(j.reasons[:3]))}`"
                if j.reasons
                else ""
            )
        )
        if size + len(block) + 2 > TG_LIMIT:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(block)
        size += len(block) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


class TelegramNotifier:
    """Push each digest straight to the user's phone. No domain verification,
    no spam filtering, delivers in seconds — the reliable channel."""

    name = "telegram"

    def __init__(self, token: str, chat_id: str = ""):
        self._token = token
        self._chat_id = chat_id

    async def _discover_chat_id(self, client: httpx.AsyncClient) -> str:
        """Read the bot's recent updates to find who messaged it."""
        resp = await client.get(TG_API.format(token=self._token, method="getUpdates"))
        for update in reversed(resp.json().get("result", [])):
            chat = (update.get("message") or update.get("channel_post") or {}).get("chat")
            if chat and chat.get("id"):
                return str(chat["id"])
        return ""

    async def send(self, recipient: str, digest: Digest) -> NotifyResult:
        async with httpx.AsyncClient(timeout=30) as client:
            chat_id = self._chat_id or await self._discover_chat_id(client)
            if not chat_id:
                return NotifyResult(
                    ok=False,
                    error="no telegram chat_id — send your bot a message once, then rescan",
                )
            last_id = None
            for chunk in render_digest_telegram(digest):
                resp = await client.post(
                    TG_API.format(token=self._token, method="sendMessage"),
                    json={
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "MarkdownV2",
                        "disable_web_page_preview": True,
                    },
                )
                data = resp.json()
                if not data.get("ok"):
                    return NotifyResult(
                        ok=False, error=f"telegram: {str(data.get('description'))[:180]}"
                    )
                last_id = str(data["result"]["message_id"])
        logger.info("telegram digest delivered to chat {}", chat_id)
        return NotifyResult(ok=True, provider_message_id=last_id)


class MultiNotifier:
    """Fan the digest out to every configured channel. Succeeds if ANY channel
    delivers, so a broken email provider can't suppress phone notifications."""

    def __init__(self, notifiers: list[Notifier]):
        self._notifiers = notifiers
        self.name = "+".join(n.name for n in notifiers)

    async def send(self, recipient: str, digest: Digest) -> NotifyResult:
        results, errors, msg_id = [], [], None
        for n in self._notifiers:
            try:
                r = await n.send(recipient, digest)
            except Exception as exc:  # noqa: BLE001 — one channel must not kill others
                logger.warning("notifier {} raised: {}", n.name, exc)
                errors.append(f"{n.name}: {exc.__class__.__name__}")
                continue
            results.append(r.ok)
            if r.ok and msg_id is None:
                msg_id = f"{n.name}:{r.provider_message_id}"
            if not r.ok:
                errors.append(f"{n.name}: {r.error}")
        return NotifyResult(
            ok=any(results),
            provider_message_id=msg_id,
            error="; ".join(errors)[:400] or None,
        )


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
    """Every configured channel gets the digest. Telegram is listed first —
    it's the reliable one; email rides along when a key is present."""
    settings = get_settings()
    channels: list[Notifier] = []
    if settings.telegram_bot_token:
        channels.append(
            TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
        )
    if settings.resend_api_key:
        channels.append(ResendNotifier(settings.resend_api_key))
    if not channels:
        return ConsoleNotifier()
    return channels[0] if len(channels) == 1 else MultiNotifier(channels)
