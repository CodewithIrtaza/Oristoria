"""Application factory and lifespan for Oristoria backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.health import router as health_router
from app.api.messages import router as messages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO Task 1: open psycopg pool, run SQL migrations, init checkpointer
    yield
    # TODO Task 1: close pool


def create_app() -> FastAPI:
    application = FastAPI(
        title="Oristoria API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
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

    return application


app = create_app()
