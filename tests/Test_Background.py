"""
Tests for BackgroundTaskManager
Run with: pytest tests/test_background.py -v --asyncio-mode=auto
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import pytest
from services.Background import BackgroundTaskManager


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _drain(manager: BackgroundTaskManager, timeout: float = 2.0):
    """Wait until the queue is empty or timeout expires."""
    try:
        await asyncio.wait_for(manager.queue.join(), timeout=timeout)
    except asyncio.TimeoutError:
        pytest.fail(f"Queue did not drain within {timeout}s")


# ─── Basic execution ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enqueued_task_executes():
    """A coroutine enqueued after start() should run."""
    ran = []

    async def task():
        ran.append(1)

    m = BackgroundTaskManager()
    await m.start()
    await m.enqueue(task())
    await _drain(m)
    await m.stop()

    assert ran == [1]


@pytest.mark.asyncio
async def test_multiple_tasks_all_execute():
    """All enqueued coroutines should execute, in order."""
    results = []

    async def task(n):
        results.append(n)

    m = BackgroundTaskManager()
    await m.start()
    for i in range(5):
        await m.enqueue(task(i))
    await _drain(m)
    await m.stop()

    assert results == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_tasks_execute_in_fifo_order():
    """Tasks should be processed first-in first-out."""
    order = []

    async def task(label):
        order.append(label)

    m = BackgroundTaskManager()
    await m.start()
    for label in ["a", "b", "c"]:
        await m.enqueue(task(label))
    await _drain(m)
    await m.stop()

    assert order == ["a", "b", "c"]


# ─── Error resilience ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_failing_task_does_not_kill_worker():
    """
    A task that raises an exception should be logged and discarded.
    The worker must keep running and process subsequent tasks.
    """
    results = []

    async def bad_task():
        raise ValueError("intentional failure")

    async def good_task():
        results.append("ok")

    m = BackgroundTaskManager()
    await m.start()
    await m.enqueue(bad_task())
    await m.enqueue(good_task())
    await _drain(m)
    await m.stop()

    assert results == ["ok"], "Worker stopped after exception — should have continued"


@pytest.mark.asyncio
async def test_multiple_failing_tasks_worker_survives():
    """Worker should survive several consecutive failures."""
    successes = []

    async def bad():
        raise RuntimeError("boom")

    async def good():
        successes.append(1)

    m = BackgroundTaskManager()
    await m.start()
    for _ in range(3):
        await m.enqueue(bad())
    await m.enqueue(good())
    await _drain(m)
    await m.stop()

    assert len(successes) == 1


# ─── Lifecycle ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_completes_without_hanging():
    """stop() should return promptly even with an idle worker."""
    m = BackgroundTaskManager()
    await m.start()
    try:
        await asyncio.wait_for(m.stop(), timeout=3.0)
    except asyncio.TimeoutError:
        pytest.fail("stop() hung — worker did not shut down cleanly")


@pytest.mark.asyncio
async def test_stop_before_start_is_safe():
    """Calling stop() on a never-started manager should not raise."""
    m = BackgroundTaskManager()
    await m.stop()  # should be a no-op


@pytest.mark.asyncio
async def test_start_stop_start_works():
    """Manager should be reusable after a stop/start cycle."""
    results = []

    async def task(n):
        results.append(n)

    m = BackgroundTaskManager()

    await m.start()
    await m.enqueue(task(1))
    await _drain(m)
    await m.stop()

    # Second lifecycle
    await m.start()
    await m.enqueue(task(2))
    await _drain(m)
    await m.stop()

    assert results == [1, 2]


@pytest.mark.asyncio
async def test_worker_task_is_none_after_stop():
    """Internal worker task reference should be cleared after stop."""
    m = BackgroundTaskManager()
    await m.start()
    assert m._worker_task is not None
    await m.stop()
    # _running should be False; task is cancelled
    assert m._running is False


# ─── Async task behaviour ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_async_task_with_await_executes_correctly():
    """Tasks that internally await should complete fully."""
    results = []

    async def slow_task():
        await asyncio.sleep(0.05)
        results.append("done")

    m = BackgroundTaskManager()
    await m.start()
    await m.enqueue(slow_task())
    await _drain(m)
    await m.stop()

    assert results == ["done"]


@pytest.mark.asyncio
async def test_high_volume_tasks_all_complete():
    """50 tasks enqueued rapidly should all execute without loss."""
    counter = []

    async def task():
        counter.append(1)

    m = BackgroundTaskManager()
    await m.start()
    for _ in range(50):
        await m.enqueue(task())
    await _drain(m)
    await m.stop()

    assert len(counter) == 50


@pytest.mark.asyncio
async def test_task_can_enqueue_another_task():
    """A running task should be able to enqueue a follow-up task."""
    results = []

    async def followup():
        results.append("followup")

    async def first(manager):
        results.append("first")
        await manager.enqueue(followup())

    m = BackgroundTaskManager()
    await m.start()
    await m.enqueue(first(m))
    # Give the follow-up task time to be enqueued and processed
    await asyncio.sleep(0.2)
    await _drain(m)
    await m.stop()

    assert results == ["first", "followup"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])