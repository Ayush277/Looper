"""Canonical shapes flowing through the scraping engine."""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Strategy(str, Enum):
    CAREERS_PAGE = "careers_page"
    JOB_API = "job_api"
    SEARCH_ENGINE = "search_engine"
    FALLBACK_SEARCH = "fallback_search"
    LLM_EXTRACTION = "llm_extraction"


class RawJob(BaseModel):
    """A job as extracted from any source, before normalization/persistence."""

    title: str = Field(min_length=2)
    apply_url: str = Field(min_length=8)
    location: str | None = None
    external_id: str | None = None
    posted_at: date | None = None
    description_snippet: str | None = None


@dataclass
class FetchResponse:
    url: str
    status_code: int
    text: str
    content_type: str = ""

    @property
    def is_json(self) -> bool:
        return "json" in self.content_type


class FetchError(Exception):
    def __init__(self, url: str, cause: str):
        self.url = url
        self.cause = cause
        super().__init__(f"fetch failed for {url}: {cause}")


@dataclass
class StrategyAttempt:
    strategy: str
    ok: bool
    jobs: int = 0
    error: str | None = None


@dataclass
class ScrapeOutcome:
    """Result of running the strategy chain for one company."""

    jobs: list[RawJob] = field(default_factory=list)
    strategy_used: str | None = None
    attempts: list[StrategyAttempt] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.strategy_used is not None
