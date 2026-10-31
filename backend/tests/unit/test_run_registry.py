"""Unit tests for the run registry."""
import asyncio

import pytest

from app.core.run_registry import RunRegistry


@pytest.mark.asyncio
async def test_second_run_same_thread_raises():
    registry = RunRegistry(max_concurrent=3)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def hold_run():
        async with registry.run("thread-1"):
            entered.set()
            await release.wait()

    task = asyncio.create_task(hold_run())
    await entered.wait()

    # A second run on the same thread should raise RuntimeError
    with pytest.raises(RuntimeError):
        async with registry.run("thread-1"):
            pass

    release.set()
    await task


@pytest.mark.asyncio
async def test_different_threads_can_run_concurrently():
    registry = RunRegistry(max_concurrent=5)

    async def short_run(tid: str):
        async with registry.run(tid):
            await asyncio.sleep(0)

    # Two different threads – should not raise
    await asyncio.gather(short_run("t1"), short_run("t2"))


@pytest.mark.asyncio
async def test_lock_released_after_run():
    registry = RunRegistry(max_concurrent=3)
    async with registry.run("thread-x"):
        pass
    # After the first run exits, a second run should be allowed
    async with registry.run("thread-x"):
        pass
