"""Pytest configuration for backend tests.

On Windows the default ProactorEventLoop is incompatible with psycopg 3's
async mode. Force a SelectorEventLoop so psycopg_pool and AsyncPostgresSaver
work under pytest-asyncio and under Starlette's TestClient (which runs the
lifespan in a portal thread).
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Ensure any new event loop (e.g. in TestClient portal threads) is a
    # SelectorEventLoop, which psycopg 3 can use on Windows.
    _orig_new_event_loop = asyncio.new_event_loop

    def _new_selector_loop() -> asyncio.AbstractEventLoop:
        return asyncio.SelectorEventLoop()

    asyncio.new_event_loop = _new_selector_loop
