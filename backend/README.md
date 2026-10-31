# Oristoria Backend

FastAPI + LangGraph + Neon Postgres backend.

## Local Development

```bash
uv sync --extra dev
uv run pytest tests/unit -v
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
