"""Application factory and lifespan for Oristoria backend.

Lifespan order (Docs/TECH_DESIGN.md §2, "Data flow: restart"):

    open psycopg pool -> run SQL migrations -> checkpointer.setup()

The pool and the checkpointer live on `app.state`, so each app instance
owns its own connections. Two instances (the integration tests build one
to simulate a restart) never close each other's pool.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.messages import router as messages_router
from app.config import settings
from app.db.migrate import run_migrations
from app.db.pool import close_pool, open_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await open_pool(settings.database_url)
    app.state.pool = pool
    try:
        await run_migrations(pool)
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        yield
    finally:
        await close_pool(pool)


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
    application.include_router(documents_router, prefix="/api")

    return application


app = create_app()
