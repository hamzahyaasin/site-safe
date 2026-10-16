"""Durable local outbox for camera events.

Inference must never block on, or lose events to, the network. A confirmed
event is written to a local SQLite file first and a background thread
delivers it to the API, retrying with exponential backoff. Each event carries
a UUID ``event_id`` that the API uses as an idempotency key, so a delivery
whose response was lost is safely resent. Events survive a process restart.

Delivery outcomes by HTTP status:

* 200 / 201 / 202 — delivered (stored, duplicate, or suppressed by a rule); removed.
* 401 / 403 — credential problem; kept and retried later, never discarded.
* other 4xx (except 408/429) — the API rejected the payload; moved to ``dead``
  so one bad event cannot block the queue. Inspect with :meth:`dead_letters`.
* 5xx, 408, 429, timeouts, connection errors — retried with backoff.

The queue is bounded: when ``max_pending`` is reached the oldest pending event
is evicted and counted in ``evicted``, so a long outage cannot fill the disk.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

DELIVERED = frozenset({200, 201, 202})
AUTH_FAILURE = frozenset({401, 403})
RETRYABLE_4XX = frozenset({408, 429})

# A sender posts one payload and returns the HTTP status code; it raises on
# transport failure (timeout, refused connection, DNS).
Sender = Callable[[dict], int]


class EventOutbox:
    def __init__(
        self,
        path: str | Path,
        sender: Sender,
        *,
        max_pending: int = 10_000,
        base_backoff: float = 1.0,
        max_backoff: float = 60.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = str(path)
        self.sender = sender
        self.max_pending = max_pending
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.clock = clock
        self.evicted = 0
        self.last_error: str | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                last_status INTEGER,
                last_error TEXT
            )
            """
        )

    # ---- producer side -------------------------------------------------

    def enqueue(self, payload: dict) -> str:
        """Persist an event for delivery and return its event_id."""
        payload = dict(payload)
        event_id = str(payload.setdefault("event_id", str(uuid.uuid4())))
        now = self.clock()
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO events (event_id, payload, created_at, next_attempt) "
                "VALUES (?, ?, ?, ?)",
                (event_id, json.dumps(payload), now, now),
            )
            overflow = self._count("pending") - self.max_pending
            if overflow > 0:
                self._db.execute(
                    "DELETE FROM events WHERE event_id IN (SELECT event_id FROM events "
                    "WHERE status='pending' ORDER BY created_at LIMIT ?)",
                    (overflow,),
                )
                self.evicted += overflow
        return event_id

    # ---- delivery side -------------------------------------------------

    def _count(self, status: str) -> int:
        return self._db.execute("SELECT COUNT(*) FROM events WHERE status=?", (status,)).fetchone()[0]

    def _backoff(self, attempts: int) -> float:
        return min(self.base_backoff * (2 ** max(attempts - 1, 0)), self.max_backoff)

    def deliver_due(self, limit: int = 50) -> int:
        """Attempt every pending event whose retry time has come. Returns the number delivered."""
        now = self.clock()
        with self._lock:
            rows = self._db.execute(
                "SELECT event_id, payload, attempts FROM events "
                "WHERE status='pending' AND next_attempt<=? ORDER BY created_at LIMIT ?",
                (now, limit),
            ).fetchall()

        delivered = 0
        for event_id, payload, attempts in rows:
            attempts += 1
            try:
                code = self.sender(json.loads(payload))
                error = None
            except Exception as exc:  # noqa: BLE001 - any transport failure is retried
                code, error = None, f"{type(exc).__name__}: {exc}"

            with self._lock:
                if code in DELIVERED:
                    self._db.execute("DELETE FROM events WHERE event_id=?", (event_id,))
                    delivered += 1
                    self.last_error = None
                    continue
                if code is not None and 400 <= code < 500 and code not in AUTH_FAILURE | RETRYABLE_4XX:
                    self._db.execute(
                        "UPDATE events SET status='dead', attempts=?, last_status=? WHERE event_id=?",
                        (attempts, code, event_id),
                    )
                    self.last_error = f"HTTP {code} (event discarded to dead letters)"
                    continue
                self.last_error = error or f"HTTP {code}"
                self._db.execute(
                    "UPDATE events SET attempts=?, next_attempt=?, last_status=?, last_error=? "
                    "WHERE event_id=?",
                    (attempts, self.clock() + self._backoff(attempts), code, error, event_id),
                )
            # The API is unreachable or refusing us; later events would fail
            # the same way, so stop this pass instead of hammering it.
            break
        return delivered

    def stats(self) -> dict:
        with self._lock:
            return {
                "pending": self._count("pending"),
                "dead": self._count("dead"),
                "evicted": self.evicted,
                "last_error": self.last_error,
            }

    def dead_letters(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT event_id, payload, last_status FROM events WHERE status='dead' ORDER BY created_at"
            ).fetchall()
        return [{"event_id": e, "payload": json.loads(p), "status": s} for e, p, s in rows]

    # ---- background thread ---------------------------------------------

    def start(self, interval: float = 0.5) -> None:
        if self._thread is not None:
            return

        def run() -> None:
            while not self._stop.is_set():
                try:
                    self.deliver_due()
                except Exception as exc:  # noqa: BLE001 - keep the worker alive
                    self.last_error = f"{type(exc).__name__}: {exc}"
                self._stop.wait(interval)

        self._thread = threading.Thread(target=run, name="sitesafe-outbox", daemon=True)
        self._thread.start()

    def stop(self, flush_timeout: float = 3.0) -> None:
        """Stop the worker after a best-effort final flush; undelivered events stay on disk."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        deadline = time.monotonic() + flush_timeout
        while time.monotonic() < deadline and self.stats()["pending"]:
            if not self.deliver_due():
                break

    def close(self) -> None:
        self._db.close()
