"""FastAPI application factory. Run: uvicorn app.main:app --reload"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import scheduler_service
from app.api.health import router as health_router
from app.api.v1 import router as v1_router
from app.config import get_settings
from app.shared.logging import setup_logging

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await scheduler_service.start_scheduler()
    yield
    await scheduler_service.stop_scheduler()


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    app = FastAPI(
        title="LoopJob API",
        version="0.1.0",
        description="Never miss another internship opening.",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        # dev: the preview/dev server may sit on any localhost port
        allow_origin_regex=r"http://localhost:\d+" if settings.is_dev else None,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(v1_router, prefix=API_PREFIX)
    return app


app = create_app()
