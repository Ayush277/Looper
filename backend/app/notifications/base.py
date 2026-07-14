"""Notifier interface (FR-7.6) — email in v1, Telegram/Discord/Slack later."""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class DigestJob:
    company: str
    title: str
    location: str | None
    posted_at: str | None
    apply_url: str
    reasons: list[str]


@dataclass
class Digest:
    subject: str
    jobs: list[DigestJob]
    scanned_companies: int
    scan_time: str


@dataclass
class NotifyResult:
    ok: bool
    provider_message_id: str | None = None
    error: str | None = None


class Notifier(Protocol):
    name: str

    async def send(self, recipient: str, digest: Digest) -> NotifyResult: ...
