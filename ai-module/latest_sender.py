"""Send the newest value of something, at most every ``interval`` seconds.

For state that only matters while it is current (the live view's frames,
the number of people in view), not for events. ``offer`` only stores the
value; a background thread sends the newest one when the rate allows.
Values are never queued: a newer value replaces an unsent one, so a slow
network delays the next update but never builds a backlog, and capture never
waits. A failed send is not retried; after one, sending pauses for
``ERROR_BACKOFF_SECONDS``. Durable events go through ``event_outbox`` instead.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

# After a failed send (API down, token missing) wait this long before the next.
ERROR_BACKOFF_SECONDS = 5.0
SUCCESS = frozenset({200, 202, 204})


class LatestSender:
    def __init__(
        self,
        sender: Callable[[Any], int],
        *,
        interval: float,
        encode: Callable[[Any], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
        name: str = "sitesafe-latest",
    ) -> None:
        """``sender`` posts one encoded value and returns the HTTP status (raises on transport failure);
        ``encode`` turns an offered value into what is sent, returning None to skip it."""
        self.sender = sender
        self.interval = interval
        self.encode = encode
        self.clock = clock
        self.name = name
        self.sent = 0
        self.failed = 0
        self.last_error: str | None = None
        self._value: Any = None
        self._has_value = False
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._next_send = 0.0

    def offer(self, value: Any) -> None:
        """Make ``value`` the one to send next. Do not mutate it afterwards."""
        with self._lock:
            self._value, self._has_value = value, True
        self._wake.set()

    def send_pending(self) -> bool:
        """Send the newest value if one is waiting and the rate allows. Returns True if a send was made."""
        now = self.clock()
        if now < self._next_send:
            return False
        with self._lock:
            if not self._has_value:
                return False
            value, self._value, self._has_value = self._value, None, False
        payload = self.encode(value) if self.encode else value
        if payload is None:
            return False
        try:
            code = self.sender(payload)
            error = None if code in SUCCESS else f"HTTP {code}"
        except Exception as exc:  # noqa: BLE001 - any transport failure just skips this value
            error = f"{type(exc).__name__}: {exc}"
        if error:
            self.failed += 1
            self.last_error = error
            self._next_send = now + ERROR_BACKOFF_SECONDS
        else:
            self.sent += 1
            self.last_error = None
            self._next_send = now + self.interval
        return True

    def start(self) -> None:
        if self._thread is not None:
            return

        def run() -> None:
            while not self._stop.is_set():
                self._wake.wait(timeout=self.interval)
                self._wake.clear()
                wait = self._next_send - self.clock()
                if wait > 0 and self._stop.wait(wait):
                    break
                self.send_pending()

        self._thread = threading.Thread(target=run, name=self.name, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
