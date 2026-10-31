"""Structured error responses and HTTP exception helpers."""
from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def error_response(code: str, message: str, retry_after: int | None = None) -> dict:
    """Return the standard error envelope."""
    return {"error": {"code": code, "message": message, "retry_after": retry_after}}


def rate_limited(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=error_response("rate_limited", "Rate limit exceeded", retry_after),
        headers={"Retry-After": str(retry_after)},
    )


def busy() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail=error_response("busy", "A run is already active on this thread"),
    )


def not_found() -> HTTPException:
    """Never reveal whether a resource doesn't exist or belongs to another user."""
    return HTTPException(
        status_code=404,
        detail=error_response("not_found", "Resource not found"),
    )
