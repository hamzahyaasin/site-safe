"""Vest gas sensor: one GAS alert per exposure, re-armed after the level stays low."""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import ServiceToken
from alerts.models import Alert, AlertConfig, AlertSource, AlertType, Severity
from alerts.rules import rule_for

from .models import SmartVest, Worker
from .mqtt_handlers import apply_vest_telemetry


def report_at(when, **payload):
    with patch("workers.mqtt_handlers.timezone.now", return_value=when):
        return apply_vest_telemetry("V-1", payload)


@override_settings(GAS_ALERT_PPM=2000, GAS_CLEAR_SECONDS=60)
class GasAlertTests(TestCase):
    def setUp(self):
        self.ali = Worker.objects.create(name="Ali")
        self.vest = SmartVest.objects.create(vest_id="V-1", worker=self.ali)
        self.t0 = timezone.now()

    def gas_alerts(self):
        return Alert.objects.filter(alert_type=AlertType.GAS)

    def at(self, seconds, **payload):
        return report_at(self.t0 + timedelta(seconds=seconds), **payload)

    def test_reading_is_stored_and_low_levels_raise_nothing(self):
        self.at(0, gas_ppm=350)
        self.vest.refresh_from_db()
        self.assertEqual(self.vest.gas_ppm, 350)
        self.assertEqual(self.gas_alerts().count(), 0)

    def test_one_alert_per_exposure_with_worker_and_position(self):
        self.at(0, latitude=33.6844, longitude=73.0479, gas_ppm=2600)
        for s in (5, 10, 15):
            self.at(s, gas_ppm=3100)
        alert = self.gas_alerts().get()
        self.assertEqual((alert.worker, alert.severity, alert.source), (self.ali, Severity.CRITICAL, AlertSource.SMART_VEST))
        self.assertEqual(alert.location, {"lat": 33.6844, "lng": 73.0479})
        self.assertIn("2,600 ppm on V-1 (limit 2,000)", alert.description)

    def test_rearmed_only_after_the_level_stays_low(self):
        self.at(0, gas_ppm=2500)
        self.at(10, gas_ppm=900)
        self.at(40, gas_ppm=2400)  # back up after 30 s below: same exposure
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
        self.at(5, battery_level=80)
        self.vest.refresh_from_db()
        self.assertEqual(self.vest.gas_ppm, 400)

    def test_vest_without_a_worker_still_alerts(self):
        self.vest.worker = None
        self.vest.save()
        self.at(0, gas_ppm=5000)
        self.assertIsNone(self.gas_alerts().get().worker)

    def test_sos_and_gas_without_a_position(self):
        # A vest with no GPS module sends no position; neither alert claims one.
        self.at(0, sos_active=True, gas_ppm=2600)
        sos = Alert.objects.get(alert_type=AlertType.SOS)
        self.assertEqual((sos.description, sos.location), ("SOS activated (no position reported)", None))
        gas = self.gas_alerts().get()
        self.assertIsNone(gas.location)
        self.assertNotIn(" at (", gas.description)

    def test_gas_alerts_cannot_be_disabled(self):
        AlertConfig.objects.filter(alert_type=AlertType.GAS, zone=None).update(is_enabled=False)
        self.assertTrue(rule_for(AlertType.GAS, None).is_enabled)


class GasTelemetryApiTests(APITestCase):
    def setUp(self):
        SmartVest.objects.create(vest_id="V-1", worker=Worker.objects.create(name="Ali"))
        _, key = ServiceToken.issue("vest-1", ServiceToken.Kind.VEST_GATEWAY)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")

    def post(self, **payload):
        return self.client.post("/api/v1/vests/telemetry/", {"vest_id": "V-1", **payload}, format="json")

    def test_gateway_reports_gas(self):
        self.assertEqual(self.post(gas_ppm=2400).status_code, 200)
        self.assertEqual(Alert.objects.get().alert_type, AlertType.GAS)

    def test_vest_list_shows_the_reading_and_whether_it_is_over_the_limit(self):
        from accounts.models import Role, User

        self.post(gas_ppm=2400)
        officer = User.objects.create_user(email="o@x.io", password="pw12345678")
        officer.role = Role.SAFETY_OFFICER
        officer.save()
        self.client.force_authenticate(officer)
        row = self.client.get("/api/v1/vests/").data
        row = (row.get("results", row) if isinstance(row, dict) else row)[0]
        self.assertEqual((row["gas_ppm"], row["gas_over_limit"]), (2400, True))

    def test_rejects_impossible_readings(self):
        self.assertEqual(self.post(gas_ppm=-1).status_code, 400)
        self.assertEqual(self.post(gas_ppm=1_000_000).status_code, 400)
        self.assertEqual(Alert.objects.count(), 0)

    def test_seeded_rule_exists(self):
        self.assertTrue(AlertConfig.objects.filter(alert_type=AlertType.GAS, zone=None, is_enabled=True).exists())
