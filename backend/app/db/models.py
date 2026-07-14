"""All ORM models — see docs/04-database-schema.md and docs/15-global-discovery.md.

Portability rules (SQLite dev / Postgres prod):
- UUIDs stored as 36-char strings, generated app-side.
- JSON uses JSONB on Postgres via with_variant.
- Embeddings stored as JSON float lists in v1 (pgvector upgrade is a later,
  additive migration — the matcher only loads vectors, it doesn't query by distance).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PortableJSON = JSON().with_variant(JSONB(), "postgresql")  # type: ignore[no-untyped-call]


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(Text, unique=True)
    careers_url: Mapped[str | None] = mapped_column(Text)
    careers_url_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="active")
    origin: Mapped[str] = mapped_column(String(16), default="user")  # user | discovered
    health: Mapped[str] = mapped_column(String(16), default="unknown")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    preferred_strategy: Mapped[str | None] = mapped_column(String(32))
    last_crawl_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('active','paused','deleted')", name="ck_company_status"),
        CheckConstraint(
            "health IN ('unknown','healthy','degraded','failing')", name="ck_company_health"
        ),
    )


class Keyword(TimestampMixin, Base):
    __tablename__ = "keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    term: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16))  # include | requirement | exclude
    embedding: Mapped[list[float] | None] = mapped_column(PortableJSON)
    embedding_model: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("term", "kind", name="uq_keyword_term_kind"),
        CheckConstraint("kind IN ('include','requirement','exclude')", name="ck_keyword_kind"),
    )


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    external_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(Text)
    description_snippet: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(Date)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    match_score: Mapped[float | None] = mapped_column(Float)
    match_reasons: Mapped[list[dict[str, object]]] = mapped_column(PortableJSON, default=list)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_state: Mapped[str] = mapped_column(String(16), default="none")
    user_state_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_strategy: Mapped[str] = mapped_column(String(32))
    origin: Mapped[str] = mapped_column(String(16), default="tracked")  # tracked | discovery
    discovery_query_id: Mapped[str | None] = mapped_column(
        ForeignKey("discovery_queries.id"), nullable=True
    )
    embedding: Mapped[list[float] | None] = mapped_column(PortableJSON)

    __table_args__ = (
        CheckConstraint(
            "status IN ('new','matched','excluded','unmatched')", name="ck_job_status"
        ),
        CheckConstraint(
            "user_state IN ('none','bookmarked','applied')", name="ck_job_user_state"
        ),
    )


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trigger: Mapped[str] = mapped_column(String(24))  # scheduled | manual | manual_company
    status: Mapped[str] = mapped_column(String(24), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    companies_total: Mapped[int] = mapped_column(Integer, default=0)
    companies_ok: Mapped[int] = mapped_column(Integer, default=0)
    companies_failed: Mapped[int] = mapped_column(Integer, default=0)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    jobs_matched: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class CrawlResult(Base):
    __tablename__ = "crawl_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scan_run_id: Mapped[str] = mapped_column(ForeignKey("scan_runs.id"), index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    strategy: Mapped[str] = mapped_column(String(32))
    strategies_attempted: Mapped[list[dict[str, object]]] = mapped_column(
        PortableJSON, default=list
    )
    status: Mapped[str] = mapped_column(String(16))  # success | empty | failed
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0)
    jobs_matched: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scan_run_id: Mapped[str | None] = mapped_column(ForeignKey("scan_runs.id"))
    recipient: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    job_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16))  # sent | failed
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailLogJob(Base):
    __tablename__ = "email_log_jobs"

    email_log_id: Mapped[str] = mapped_column(ForeignKey("email_logs.id"), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), primary_key=True)


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    hour: Mapped[int] = mapped_column(SmallInteger)
    minute: Mapped[int] = mapped_column(SmallInteger, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("hour", "minute", name="uq_schedule_time"),
        CheckConstraint("hour >= 0 AND hour <= 23", name="ck_schedule_hour"),
        CheckConstraint("minute >= 0 AND minute <= 59", name="ck_schedule_minute"),
    )


class DiscoveryQuery(TimestampMixin, Base):
    __tablename__ = "discovery_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(Text, unique=True)
    keywords: Mapped[list[dict[str, object]]] = mapped_column(PortableJSON, default=list)
    country: Mapped[str] = mapped_column(Text)
    locations: Mapped[list[dict[str, object]]] = mapped_column(PortableJSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppSettings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    timezone: Mapped[str] = mapped_column(Text, default="Asia/Kolkata")
    notification_email: Mapped[str | None] = mapped_column(Text)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    match_threshold: Mapped[float] = mapped_column(Float, default=0.55)
    requirement_boost: Mapped[float] = mapped_column(Float, default=0.05)
    scan_concurrency: Mapped[int] = mapped_column(SmallInteger, default=4)
    embedding_provider: Mapped[str] = mapped_column(String(16), default="openai")
    discovery_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (CheckConstraint("id = 1", name="ck_settings_single_row"),)
