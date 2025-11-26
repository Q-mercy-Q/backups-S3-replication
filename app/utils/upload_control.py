import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional


class UploadControl:
    """Controls upload lifecycle and stop behavior."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_requested = False
        self._force_stop = False
        self._executor: Optional[ThreadPoolExecutor] = None

    def reset(self) -> None:
        """Reset control flags before a new upload session."""
        with self._lock:
            self._stop_requested = False
            self._force_stop = False

    def register_executor(self, executor: ThreadPoolExecutor) -> None:
        """Register the current executor to control force shutdown."""
        with self._lock:
            self._executor = executor
            if self._force_stop:
                executor.shutdown(wait=False, cancel_futures=True)

    def clear_executor(self) -> None:
        """Clear executor reference after upload session."""
        with self._lock:
            self._executor = None

    def request_stop(self, finish_current: bool) -> None:
        """Request upload stop.

        Args:
            finish_current: True to allow current uploads to finish,
                            False to stop immediately.
        """
        with self._lock:
            self._stop_requested = True
            self._force_stop = not finish_current
            if self._force_stop and self._executor:
                self._executor.shutdown(wait=False, cancel_futures=True)

    def stop_requested(self) -> bool:
        with self._lock:
            return self._stop_requested

    def force_stop(self) -> bool:
        with self._lock:
            return self._force_stop


upload_control = UploadControl()

