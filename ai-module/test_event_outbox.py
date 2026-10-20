"""Outbox delivery semantics: durability, idempotent retry, backoff, dead letters."""

from __future__ import annotations

import base64
import sqlite3
import tempfile
import unittest
from pathlib import Path

from event_outbox import EventOutbox


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Recorder:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, payload):
        self.calls.append(payload)
        r = self.responses.pop(0) if self.responses else 201
        if isinstance(r, Exception):
            raise r
        return r


class EventOutboxTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "outbox.sqlite3"
        self.clock = FakeClock()

    def box(self, sender, **kw):
        b = EventOutbox(self.path, sender, clock=self.clock, **kw)
        self.addCleanup(b.close)
        return b

    def test_assigns_stable_event_id_and_delivers(self):
        sender = Recorder(201)
        box = self.box(sender)
        event_id = box.enqueue({"alert_type": "FALL"})
        self.assertEqual(box.deliver_due(), 1)
        self.assertEqual(sender.calls[0]["event_id"], event_id)
        self.assertEqual(box.stats()["pending"], 0)

    def test_outage_retries_with_same_event_id_and_backoff(self):
        sender = Recorder(ConnectionError("refused"), 503, 200)
        box = self.box(sender, base_backoff=1.0)
        box.enqueue({"alert_type": "FALL"})

        self.assertEqual(box.deliver_due(), 0)
        self.assertEqual(box.deliver_due(), 0, "not due again until backoff elapses")
        self.assertEqual(len(sender.calls), 1)

        self.clock.t += 1.0
        self.assertEqual(box.deliver_due(), 0)  # 503
        self.clock.t += 1.9
        self.assertEqual(box.deliver_due(), 0, "second backoff is 2s")
        self.clock.t += 0.2
        self.assertEqual(box.deliver_due(), 1)  # 200 = already stored
        self.assertEqual(len({c["event_id"] for c in sender.calls}), 1)

    def test_events_survive_restart(self):
        down = Recorder(ConnectionError("down"))
        first = self.box(down)
        first.enqueue({"alert_type": "PPE_VIOLATION"})
        first.enqueue({"alert_type": "FALL"})
        first.deliver_due()
        first.close()

        self.clock.t += 120
        up = Recorder()
        second = self.box(up)
        self.assertEqual(second.stats()["pending"], 2)
        self.assertEqual(second.deliver_due(), 2)
        self.assertEqual([c["alert_type"] for c in up.calls], ["PPE_VIOLATION", "FALL"])

    def test_rejected_payload_goes_to_dead_letters_without_blocking(self):
        sender = Recorder(400, 201)
        box = self.box(sender)
        box.enqueue({"alert_type": "BAD"})
        box.enqueue({"alert_type": "FALL"})
        box.deliver_due()
        self.assertEqual(box.stats()["dead"], 1)
        self.assertEqual(box.stats()["pending"], 0)
        self.assertEqual(box.dead_letters()[0]["payload"]["alert_type"], "BAD")

    def test_auth_failure_is_kept_for_retry(self):
        sender = Recorder(401)
        box = self.box(sender)
        box.enqueue({"alert_type": "FALL"})
        box.deliver_due()
        self.assertEqual(box.stats(), {"pending": 1, "dead": 0, "evicted": 0, "last_error": "HTTP 401"})

    def test_suppressed_counts_as_delivered(self):
        box = self.box(Recorder(202))
        box.enqueue({"alert_type": "FALL"})
        self.assertEqual(box.deliver_due(), 1)

    def test_bounded_queue_evicts_oldest(self):
        box = self.box(Recorder(), max_pending=2)
        for i in range(4):
            self.clock.t += 1
            box.enqueue({"n": i})
        self.assertEqual(box.stats()["pending"], 2)
        self.assertEqual(box.stats()["evicted"], 2)
        sender = Recorder()
        box.sender = sender
        box.deliver_due()
        self.assertEqual([c["n"] for c in sender.calls], [2, 3])

    def test_duplicate_enqueue_is_ignored(self):
        box = self.box(Recorder())
        box.enqueue({"event_id": "abc", "n": 1})
        box.enqueue({"event_id": "abc", "n": 2})
        self.assertEqual(box.stats()["pending"], 1)

    def test_snapshot_survives_restart_and_is_sent_base64(self):
        jpeg = b"\xff\xd8\xff\xe0fake-jpeg-bytes\xff\xd9"
        first = self.box(Recorder(ConnectionError("down")))
        first.enqueue({"alert_type": "FALL"}, snapshot=jpeg)
        first.enqueue({"alert_type": "PPE_VIOLATION"})
        first.deliver_due()
        first.close()

        self.clock.t += 120
        up = Recorder()
        second = self.box(up)
        self.assertEqual(second.deliver_due(), 2)
        self.assertEqual(base64.b64decode(up.calls[0]["snapshot"]), jpeg)
        self.assertNotIn("snapshot", up.calls[1])

    def test_duplicate_enqueue_keeps_first_snapshot(self):
        sender = Recorder()
        box = self.box(sender)
        box.enqueue({"event_id": "abc"}, snapshot=b"first")
        box.enqueue({"event_id": "abc"}, snapshot=b"second")
        box.deliver_due()
        self.assertEqual(len(sender.calls), 1)
        self.assertEqual(base64.b64decode(sender.calls[0]["snapshot"]), b"first")

    def test_queue_file_from_before_snapshots_is_upgraded(self):
        db = sqlite3.connect(self.path)
        db.execute(
            "CREATE TABLE events (event_id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at REAL NOT NULL, "
            "attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
            "last_status INTEGER, last_error TEXT)"
        )
        db.execute(
            "INSERT INTO events (event_id, payload, created_at, next_attempt) VALUES ('old', '{\"n\": 1}', 0, 0)"
        )
        db.commit()
        db.close()
        sender = Recorder()
        box = self.box(sender)
        box.enqueue({"n": 2}, snapshot=b"img")
        self.assertEqual(box.deliver_due(), 2)
        self.assertEqual([c["n"] for c in sender.calls], [1, 2])
        self.assertNotIn("snapshot", sender.calls[0])
        self.assertEqual(base64.b64decode(sender.calls[1]["snapshot"]), b"img")


if __name__ == "__main__":
    unittest.main()
