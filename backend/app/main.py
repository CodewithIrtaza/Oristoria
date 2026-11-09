"""Application factory and lifespan for Oristoria backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.messages import router as messages_router
from app.config import settings
from app.db import pool as pool_module
from app.db.migrate import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Open pool, run migrations, init checkpointer
    await pool_module.open_pool(settings.database_url)
    app.state.pool = pool_module.pool  # type: ignore[assignment]
    await run_migrations(app.state.pool)  # type: ignore[union-attr]

    checkpointer = AsyncPostgresSaver(app.state.pool)  # type: ignore[union-attr]
    await checkpointer.setup()
    app.state.checkpointer = checkpointer

    yield

    # Close pool
    await pool_module.close_pool()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Oristoria API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    # Routers
    application.include_router(health_router, prefix="/api")
    application.include_router(messages_router, prefix="/api")
    application.include_router(conversations_router, prefix="/api")

    return application


app = create_app()
