"""The demo site command: configuration only, safe to run again, matches the vest simulator's scenario."""

import io
import json
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from accounts.models import ServiceToken, User
from alerts.models import Alert
from sitemap.geofence import point_in_polygon
from sitemap.models import Camera, GasMonitor, Zone

from .models import SmartVest, Worker

SCENARIO = Path(__file__).resolve().parents[2] / "tools" / "vest_scenarios" / "demo.json"


def run(*args):
    out = io.StringIO()
    call_command("setup_demo", *args, stdout=out)
    return out.getvalue()


class SetupDemoTests(TestCase):
    def test_creates_the_site_once_and_shows_secrets_once(self):
        first = run()
        self.assertEqual(first.count("password:"), 3)
        self.assertEqual(first.count("key:"), 3)
        counts = (User.objects.count(), Zone.objects.count(), Worker.objects.count(), SmartVest.objects.count())
        self.assertEqual(counts, (3, 2, 3, 2))

        second = run()
        self.assertNotIn("password:", second)
        self.assertNotIn("key:", second)
        self.assertIn("nothing created", second)
        self.assertEqual(
            (User.objects.count(), Zone.objects.count(), Worker.objects.count(), SmartVest.objects.count()), counts
        )

    def test_configuration_only(self):
        run()
        self.assertEqual(Alert.objects.count(), 0)
        self.assertTrue(ServiceToken.objects.get(name="demo-vest-gateway").is_simulator)
        self.assertEqual(ServiceToken.objects.get(name="demo-cam-01").camera_ids, ["CAM-01"])
        gas_token = ServiceToken.objects.get(name="demo-gas-monitor")
        self.assertEqual((gas_token.kind, gas_token.is_simulator), (ServiceToken.Kind.GAS_MONITOR, True))
        self.assertTrue(Camera.objects.get(camera_id="CAM-01").is_placed)

    def test_matches_the_vest_scenario(self):
        run()
        scenario = json.loads(SCENARIO.read_text())
        vests = {v["vest_id"]: v for v in scenario["vests"]}
        self.assertEqual(set(vests), set(SmartVest.objects.values_list("vest_id", flat=True)))
        crane = Zone.objects.get(name="Crane").boundaries
        site = Zone.objects.get(name="Site").boundaries
        # VEST-002 ends its walk inside the restricted zone; VEST-001 walks around the site.
        self.assertTrue(point_in_polygon(*vests["VEST-002"]["waypoints"][3], crane))
        self.assertTrue(point_in_polygon(*vests["VEST-001"]["waypoints"][1], site))
        self.assertFalse(point_in_polygon(*vests["VEST-001"]["waypoints"][1], crane))
        # The scenario's gas monitor is the one installed in the Site zone, inside it on the map.
        monitors = {m["monitor_id"] for m in scenario["gas_monitors"]}
        self.assertEqual(monitors, set(GasMonitor.objects.values_list("monitor_id", flat=True)))
        monitor = GasMonitor.objects.get()
        self.assertEqual(monitor.zone.name, "Site")
        self.assertTrue(point_in_polygon(monitor.latitude, monitor.longitude, site))

    def test_rejects_a_bad_centre(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            run("--center", "north")
