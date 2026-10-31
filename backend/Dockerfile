# ── Build stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache-dir -e .

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=app:app . .

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
