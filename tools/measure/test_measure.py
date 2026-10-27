import socket
import socketserver
import tempfile
import threading
import time
import unittest
from pathlib import Path

import common
import make_tables
from recovery import SwitchableProxy


class StatsTests(unittest.TestCase):
    def test_percentiles(self):
        self.assertEqual(common.percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(common.percentile([5], 0.95), 5)
        self.assertIsNone(common.percentile([], 0.5))
        s = common.summarise([10, 20, 30])
        self.assertEqual((s["n"], s["p50"], s["max"]), (3, 20, 30))
        self.assertEqual(common.summarise([]), {"n": 0})

    def test_socket_url(self):
        self.assertEqual(common.socket_url("http://h:8000/api", "T"), "ws://h:8000/ws/dashboard/?token=T")
        self.assertEqual(common.socket_url("https://site/api/", "T"), "wss://site/ws/dashboard/?token=T")


class ProxyTests(unittest.TestCase):
    def test_switches_between_refused_and_forwarding(self):
        class Echo(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.sendall(self.request.recv(100))

        server = socketserver.TCPServer(("127.0.0.1", 0), Echo)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        proxy = SwitchableProxy("127.0.0.1", server.server_address[1])
        proxy.start()

        def talk():
            with socket.create_connection(("127.0.0.1", proxy.port), timeout=2) as c:
                c.sendall(b"ping")
                return c.recv(100)

        self.assertEqual(talk(), b"ping")
        proxy.stop()
        with self.assertRaises(ConnectionRefusedError):
            talk()
        proxy.start()  # same port again
        self.assertEqual(talk(), b"ping")
        proxy.stop()

    def test_stop_cuts_open_connections(self):
        class Hold(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.recv(100)

        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Hold)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        proxy = SwitchableProxy("127.0.0.1", server.server_address[1])
        proxy.start()
        held = socket.create_connection(("127.0.0.1", proxy.port), timeout=2)
        self.addCleanup(held.close)
        deadline = time.monotonic() + 2
        while not proxy.writers and time.monotonic() < deadline:  # wait until accepted and forwarding
            time.sleep(0.01)
        proxy.stop()  # must not hang on the open connection
        held.settimeout(2)
        try:
            data = held.recv(10)
        except ConnectionResetError:
            data = b""  # aborted connections may surface as a reset
        self.assertEqual(data, b"")  # connection was cut


def result(kind, **data):
    return {"measurement": kind, "recorded_at": "2026-10-20T10:00:00+00:00", "environment": {"cpu": "Apple M4", "memory_gb": 16, "git_commit": "abc1234"}, **data}


class TableTests(unittest.TestCase):
    def test_renders_present_and_missing(self):
        latency = result(
            "latency",
            settings={"interval_s": 0.5},
            api_ms=common.summarise([5, 6, 7]),
            end_to_end_ms=common.summarise([20, 30, 2500]),
            sent=3, delivered_on_socket=3, missed_on_socket=0, target="p95 <= 2000 ms",
        )
        text = make_tables.render({"latency": latency})
        self.assertIn("| End to end (event → dashboard) | 3 |", text)
        self.assertIn("**FAIL**", text)  # p95 above 2000 ms
        self.assertIn("Not yet measured", text)
        self.assertIn("recovery, fps, soak", text)

    def test_soak_pids_option(self):
        import soak

        self.assertEqual(soak.parse_pids("api=12, camera=34"), {"api": 12, "camera": 34})
        self.assertEqual(soak.parse_pids(""), {})
        with self.assertRaises(ValueError):
            soak.parse_pids("browser=1")
        with self.assertRaises(ValueError):
            soak.parse_pids("api=x")

    def test_short_soak_is_not_a_pass(self):
        soak = result(
            "soak",
            settings={"hours": 0.08, "probe_interval_s": 2, "processes_found": ["api"]},
            end_to_end_ms=common.summarise([30, 40]),
            probes_missed=0, unexpected_socket_drops=0, forced_reconnect_s=1.2,
            memory={"api": {"first_mb": 100, "last_mb": 101, "max_mb": 102, "change_mb": 1}},
            error_count=0, target="2 h",
        )
        text = make_tables.render({"soak": soak})
        self.assertIn("validation run only", text)
        self.assertNotIn("**PASS**", text)

    def test_recovery_history_keeps_failures(self):
        def run(recovered, ok, when):
            r = result("recovery", settings={"events": 100, "outage_s": 300, "max_backoff_s": 60 if not ok else 30, "sender_restart_at_s": 150},
                       queued_when_restored=100, recovery_s=recovered, stored_once=100, lost=0, duplicated=0, passed=ok, target="60 s")
            r["recorded_at"] = when
            return r

        runs = [run(60.3, False, "2026-10-20T11:51"), run(30.0, True, "2026-10-20T12:01")]
        text = make_tables.render({"recovery": runs[-1]}, runs)
        self.assertIn("60.3", text)
        self.assertIn("**FAIL**", text)
        self.assertIn("**PASS**", text)

    def test_latest_picks_newest_per_kind(self):
        import json

        with tempfile.TemporaryDirectory() as d:
            for name, when in (("latency_a", "2026-10-19"), ("latency_b", "2026-10-20"), ("fps_mps_x", "2026-10-20")):
                Path(d, f"{name}.json").write_text(json.dumps({"recorded_at": when, "id": name}))
            got = make_tables.latest(Path(d))
            self.assertEqual(got["latency"]["id"], "latency_b")
            self.assertIn("fps_mps", got)


if __name__ == "__main__":
    unittest.main()
