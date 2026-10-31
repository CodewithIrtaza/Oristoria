"""FastAPI dependency: validate and extract X-Anon-Id header."""
from __future__ import annotations

import uuid

from fastapi import Header, HTTPException


async def get_anon_id(x_anon_id: str = Header(...)) -> str:
    """Parse and validate the X-Anon-Id UUID header.

    Returns the validated UUID string or raises 422.
    """
    try:
        return str(uuid.UUID(x_anon_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="X-Anon-Id must be a valid UUID")
