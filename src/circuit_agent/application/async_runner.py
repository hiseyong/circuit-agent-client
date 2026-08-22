"""Single background asyncio loop shared by all desktop I/O."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

SuccessCallback = Callable[[Any], None]
ErrorCallback = Callable[[BaseException], None]


class AsyncRunner(QObject):
    """Run coroutines on one dedicated event-loop thread.

    Controllers submit work with ``submit``. Results are delivered through
    Qt signals so callbacks always run on the GUI thread. This avoids creating
    a QThread per request and keeps the QML UI responsive.
    """

    _succeeded = Signal(object, object)
    _failed = Signal(object, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="circuit-agent-asyncio",
            daemon=True,
        )
        self._succeeded.connect(self._dispatch_success)
        self._failed.connect(self._dispatch_error)
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def submit(
        self,
        coro: Coroutine[Any, Any, Any],
        on_success: SuccessCallback,
        on_error: ErrorCallback,
    ) -> None:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        def _done(done_future: Any) -> None:
            try:
                result = done_future.result()
            except Exception as exc:  # noqa: BLE001 - surface all backend failures
                self._failed.emit(on_error, exc)
            else:
                self._succeeded.emit(on_success, result)

        future.add_done_callback(_done)

    @Slot(object, object)
    def _dispatch_success(self, callback: SuccessCallback, result: Any) -> None:
        callback(result)

    @Slot(object, object)
    def _dispatch_error(self, callback: ErrorCallback, exc: BaseException) -> None:
        callback(exc)

    def stop(self, timeout: float = 2.0) -> None:
        if self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=timeout)
        if not self._loop.is_closed():
            self._loop.close()
