"""Job identity hashing — the zero-duplicate-email guarantee starts here.

content_hash = sha256(company_id | norm(title) | norm(location) | canonical_path(apply_url))
See docs/04-database-schema.md §3.
"""
import hashlib
import re
from urllib.parse import urlsplit

_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_text(value: str | None) -> str:
    """Lowercase, strip punctuation, collapse whitespace. Idempotent."""
    if not value:
        return ""
    value = _PUNCT.sub(" ", value.lower())
    return _WHITESPACE.sub(" ", value).strip()


def canonical_url_path(url: str) -> str:
    """Host + path only — query params and fragments (tracking) are identity noise."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    return f"{host}{path}"


def job_content_hash(
    company_id: str, title: str, location: str | None, apply_url: str
) -> str:
    identity = "|".join(
        [
            company_id,
            normalize_text(title),
            normalize_text(location),
            canonical_url_path(apply_url),
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
