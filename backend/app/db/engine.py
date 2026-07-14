"""Async database engine and session factory.

Dev default is SQLite (zero-dependency); prod is PostgreSQL via asyncpg.
All models avoid Postgres-only column types at the Python level so both work
(JSON with a JSONB variant, string UUIDs) — see docs/04-database-schema.md.
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

engine = create_async_engine(get_settings().database_url, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, rolled back on error."""
    async with SessionFactory() as session:
        yield session
