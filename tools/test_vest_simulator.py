import contextlib
import io
import json
import tempfile
import unittest

import vest_simulator as sim


class SimulatorTests(unittest.TestCase):
    def vest(self, **kw):
        return sim.Vest(vest_id="V", waypoints=[(0.0, 0.0), (0.0, 0.001), (0.001, 0.001)], **kw)

    def test_walk_follows_waypoints_at_speed(self):
        v = self.vest(speed_mps=1.0)
        leg = sim.distance_m((0, 0), (0, 0.001))
        self.assertAlmostEqual(leg, 111.2, delta=0.5)
        (lat, lng), reached = sim.position_at(v, leg / 2)
        self.assertAlmostEqual(lng, 0.0005, places=6)
        self.assertEqual(reached, 0)
        self.assertEqual(sim.position_at(v, 10_000), ((0.001, 0.001), 2))

    def test_frames_cover_route_and_hold(self):
        v = self.vest(speed_mps=10.0)
        frames = sim.build_frames([v], interval=5, hold=10)
        self.assertEqual(frames[0].payload["latitude"], 0.0)
        self.assertEqual((frames[-1].payload["latitude"], frames[-1].payload["longitude"]), (0.001, 0.001))
        self.assertGreaterEqual(frames[-1].t, sim.route_seconds(v) + 10 - 5)

    def test_sos_sent_once_when_waypoint_reached(self):
        frames = sim.build_frames([self.vest(speed_mps=10.0, sos_at=1)], interval=2)
        sos = [f for f in frames if f.payload.get("sos_active")]
        self.assertEqual(len(sos), 1)
        self.assertGreaterEqual(sos[0].t, sim.distance_m((0, 0), (0, 0.001)) / 10.0 - 2)

    def test_stop_at_goes_silent(self):
        frames = sim.build_frames([self.vest(speed_mps=10.0, stop_at=1)], interval=2, hold=60)
        last = frames[-1]
        self.assertLess(last.t, sim.route_seconds(self.vest(speed_mps=10.0)))
        self.assertAlmostEqual(last.payload["longitude"], 0.001, places=4)

    def test_gas_monitor_baseline_then_leak_for_its_duration(self):
        monitor = sim.GasMonitor("GM", gas_ppm=300, leak_at_seconds=4, leak_ppm=2800, leak_seconds=6)
        frames = sim.build_frames([self.vest(speed_mps=10.0)], interval=2, hold=20, monitors=[monitor])
        gas = [f for f in frames if f.kind == sim.GAS]
        levels = [f.payload["gas_ppm"] for f in gas]
        self.assertEqual(levels[0], 300)
        self.assertEqual(levels.count(2800), 3, "6 s of leak at one report every 2 s")
        self.assertEqual(levels[-1], 300, "back to the baseline after the leak")
        self.assertEqual({f.device_id for f in gas}, {"GM"})

    def test_monitor_reports_past_its_leak_even_without_vests(self):
        monitor = sim.GasMonitor("GM", leak_at_seconds=30, leak_ppm=5000, leak_seconds=10)
        frames = sim.build_frames([], interval=5, monitors=[monitor])
        self.assertGreaterEqual(frames[-1].t, 40)
        self.assertEqual(frames[-1].payload["gas_ppm"], 300)

    def test_vests_send_no_gas(self):
        frames = sim.build_frames([self.vest(speed_mps=10.0)], interval=2)
        self.assertFalse(any("gas_ppm" in f.payload for f in frames))
        self.assertEqual({f.kind for f in frames}, {sim.VEST})

    def test_battery_drains_and_is_bounded(self):
        v = self.vest(battery_start=10, battery_drain_per_min=60)
        self.assertEqual(sim._battery(v, 0)["battery_level"], 10)
        self.assertEqual(sim._battery(v, 3600)["battery_level"], 0)

    def test_scenario_validation(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"vests": [{"vest_id": "V", "waypoints": [[95, 0]]}]}, fh)
        with self.assertRaises(ValueError):
            sim.load_scenario(fh.name)

    def test_demo_scenario_loads(self):
        scenario = sim.load_scenario("vest_scenarios/demo.json")
        self.assertEqual([v.vest_id for v in scenario.vests], ["VEST-001", "VEST-002"])
        self.assertEqual([m.monitor_id for m in scenario.monitors], ["GM-01"])
        frames = scenario.frames()
        self.assertTrue(any(f.payload.get("sos_active") for f in frames if f.device_id == "VEST-002"))
        self.assertTrue(any(f.payload.get("gas_ppm", 0) >= 2000 for f in frames if f.device_id == "GM-01"))

    def test_dry_run_needs_no_key(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(sim.main(["vest_scenarios/demo.json", "--dry-run"]), 0)
        self.assertIn("sos_active", out.getvalue())
        self.assertIn("GM-01", out.getvalue())

    def test_live_run_needs_a_key_for_each_kind_of_device(self):
        import os
        from unittest import mock

        with mock.patch.dict(os.environ, {"SITESAFE_DEVICE_KEY": "ss_x", "SITESAFE_GAS_MONITOR_KEY": ""}):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(sim.main(["vest_scenarios/demo.json"]), 2)
        self.assertIn("SITESAFE_GAS_MONITOR_KEY", err.getvalue())


if __name__ == "__main__":
    unittest.main()
