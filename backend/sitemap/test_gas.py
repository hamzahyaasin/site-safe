"""Fixed gas monitors: zone GAS alerts, one per exposure, re-armed after the level stays low or a resolve."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from alerts.models import Alert, AlertConfig, AlertSource, AlertType, Severity
from alerts.rules import rule_for

from .gas import apply_gas_telemetry, sweep_stale_monitors
from .models import GasMonitor, Zone


def report_at(when, **payload):
    with patch("sitemap.gas.timezone.now", return_value=when):
        return apply_gas_telemetry("GM-1", payload)


@override_settings(GAS_ALERT_PPM=2000, GAS_CLEAR_SECONDS=60)
class GasAlertTests(TestCase):
    def setUp(self):
        self.zone = Zone.objects.create(name="Basement")
        self.monitor = GasMonitor.objects.create(monitor_id="GM-1", zone=self.zone)
        self.t0 = timezone.now()

    def gas_alerts(self):
        return Alert.objects.filter(alert_type=AlertType.GAS)

    def at(self, seconds, **payload):
        return report_at(self.t0 + timedelta(seconds=seconds), **payload)

    def test_reading_is_stored_and_low_levels_raise_nothing(self):
        self.at(0, gas_ppm=350)
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.gas_ppm, 350)
        self.assertTrue(self.monitor.is_online)
        self.assertEqual(self.gas_alerts().count(), 0)

    def test_alert_names_the_zone_not_a_worker(self):
        self.monitor.latitude, self.monitor.longitude = 33.6844, 73.0479
        self.monitor.save()
        self.at(0, gas_ppm=2600)
        for s in (5, 10, 15):
            self.at(s, gas_ppm=3100)
        alert = self.gas_alerts().get()
        self.assertEqual((alert.zone, alert.worker), (self.zone, None))
        self.assertEqual((alert.severity, alert.source), (Severity.CRITICAL, AlertSource.GAS_MONITOR))
        self.assertEqual(alert.location, {"lat": 33.6844, "lng": 73.0479})
        self.assertEqual(alert.description, "Gas 2,600 ppm in Basement, monitor GM-1 (limit 2,000)")

    def test_rearmed_only_after_the_level_stays_low(self):
        self.at(0, gas_ppm=2500)
        self.at(10, gas_ppm=900)
        self.at(40, gas_ppm=2400)  # back up after 30 s below, alert still open: same exposure
        self.assertEqual(self.gas_alerts().count(), 1)
        self.at(50, gas_ppm=800)
        self.at(110, gas_ppm=700)  # 60 s below: re-armed
        self.at(115, gas_ppm=2200)
        self.assertEqual(self.gas_alerts().count(), 2)

    def test_new_rise_after_the_alert_is_resolved_alerts_at_once(self):
        self.at(0, gas_ppm=10000)
        self.gas_alerts().update(is_resolved=True)
        self.at(5, gas_ppm=2400)  # still the same rise: no new alert
        self.assertEqual(self.gas_alerts().count(), 1)
        self.at(10, gas_ppm=40)
        self.at(20, gas_ppm=10000)  # a new rise 10 s later, after the supervisor resolved
        self.assertEqual(self.gas_alerts().count(), 2)
        self.at(25, gas_ppm=30)
        self.at(30, gas_ppm=9000)  # and while that one is open, the wait applies again
        self.assertEqual(self.gas_alerts().count(), 2)

    def test_report_without_a_reading_keeps_the_last_one(self):
        self.at(0, gas_ppm=400)
        self.at(5)  # warming up after a restart: online, no reading
        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.gas_ppm, 400)

    def test_monitor_without_a_zone_still_alerts(self):
        self.monitor.zone = None
        self.monitor.save()
        self.at(0, gas_ppm=5000)
        alert = self.gas_alerts().get()
        self.assertIsNone(alert.zone)
        self.assertIsNone(alert.location)
        self.assertIn("(no zone assigned), monitor GM-1 ", alert.description)
        self.at(5, gas_ppm=10)
        self.at(10, gas_ppm=5000)  # alert still open: no duplicate
        self.assertEqual(self.gas_alerts().count(), 1)

    def test_unknown_monitor(self):
        self.assertIsNone(apply_gas_telemetry("GM-404", {"gas_ppm": 9000}))

    def test_silent_monitor_goes_offline(self):
        self.at(0, gas_ppm=100)
        later = self.t0 + timedelta(minutes=5)
        self.assertEqual(sweep_stale_monitors(now=later), 1)
        self.monitor.refresh_from_db()
        self.assertFalse(self.monitor.is_online)

    def test_gas_alerts_cannot_be_disabled(self):
        AlertConfig.objects.filter(alert_type=AlertType.GAS, zone=None).update(is_enabled=False)
        self.assertTrue(rule_for(AlertType.GAS, None).is_enabled)


class GasMonitorApiTests(APITestCase):
    def setUp(self):
        self.zone = Zone.objects.create(name="Basement")
        GasMonitor.objects.create(monitor_id="GM-1", zone=self.zone)
        _, key = ServiceToken.issue("gm-1", ServiceToken.Kind.GAS_MONITOR)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")

    def post(self, **payload):
        return self.client.post("/api/v1/gas-monitors/telemetry/", {"monitor_id": "GM-1", **payload}, format="json")

    def officer(self):
        user = User.objects.create_user(email="o@x.io", password="pw12345678")
        user.role = Role.SAFETY_OFFICER
        user.save()
        return user

    def test_monitor_reports_gas_and_raises_a_zone_alert(self):
        self.assertEqual(self.post(gas_ppm=2400).status_code, 200)
        alert = Alert.objects.get()
        self.assertEqual((alert.alert_type, alert.zone), (AlertType.GAS, self.zone))

    def test_only_gas_monitor_tokens_may_report(self):
        _, vest_key = ServiceToken.issue("vest-1", ServiceToken.Kind.VEST_GATEWAY)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {vest_key}")
        self.assertEqual(self.post(gas_ppm=2400).status_code, 403)

    def test_simulator_token_labels_the_alert(self):
        _, key = ServiceToken.issue("gm-sim", ServiceToken.Kind.GAS_MONITOR, is_simulator=True)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")
        self.post(gas_ppm=2400)
        self.assertEqual(Alert.objects.get().source, AlertSource.SIMULATED)

    def test_rejects_impossible_readings_and_unknown_monitors(self):
        self.assertEqual(self.post(gas_ppm=-1).status_code, 400)
        self.assertEqual(self.post(gas_ppm=1_000_000).status_code, 400)
        missing = self.client.post("/api/v1/gas-monitors/telemetry/", {"monitor_id": "GM-9", "gas_ppm": 5}, format="json")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(Alert.objects.count(), 0)

    def test_list_shows_the_zone_reading_and_whether_it_is_over_the_limit(self):
        self.post(gas_ppm=2400)
        self.client.credentials()
        self.client.force_authenticate(self.officer())
        rows = self.client.get("/api/v1/gas-monitors/").data
        row = (rows.get("results", rows) if isinstance(rows, dict) else rows)[0]
        self.assertEqual(
            (row["zone_name"], row["gas_ppm"], row["gas_over_limit"], row["is_online"]), ("Basement", 2400, True, True)
        )
        alert = self.client.get("/api/alerts/").data
        alert = (alert.get("results", alert) if isinstance(alert, dict) else alert)[0]
        self.assertEqual((alert["zone"], alert["zone_name"], alert["worker"]), (self.zone.pk, "Basement", None))

    def test_officer_registers_and_places_a_monitor(self):
        self.client.credentials()
        self.client.force_authenticate(self.officer())
        made = self.client.post(
            "/api/v1/gas-monitors/",
            {"monitor_id": "GM-2", "name": "Pump room", "zone": self.zone.pk, "latitude": 33.68, "longitude": 73.04},
            format="json",
        )
        self.assertEqual(made.status_code, 201, made.data)
        half = self.client.post("/api/v1/gas-monitors/", {"monitor_id": "GM-3", "latitude": 33.68}, format="json")
        self.assertEqual(half.status_code, 400)
        reading = self.client.patch(f"/api/v1/gas-monitors/{made.data['id']}/", {"gas_ppm": 9000}, format="json")
        self.assertEqual(reading.status_code, 200)
        self.assertIsNone(GasMonitor.objects.get(monitor_id="GM-2").gas_ppm)  # readings come only from the device

    def test_seeded_rule_exists(self):
        self.assertTrue(AlertConfig.objects.filter(alert_type=AlertType.GAS, zone=None, is_enabled=True).exists())
