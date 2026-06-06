"""

Background Task Manager
Handles async signal processing, routing computation, and housekeeping

"""
import asyncio
import logging
from collections.abc import Coroutine

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue() # Queue used for coroutines
        self._worker_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Background task manager started")

    async def _worker(self):
        while self._running:
            try:
                coro = await asyncio.wait_for(self._queue.get(), timeout=1.0) # wait for single Coroutine to complete
                try:
                    await coro
                except Exception as e:
                    logger.error(f"Background task failed: {e}", exc_info=True)

                finally:
                    self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError: # Task was canceled
                break

    async def stop(self):
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Background task manager stopped")


    async def enqueue(self, coro: Coroutine) -> None:
        await self._queue.put(coro)

    @property
    def queue(self):
        return self._queue
