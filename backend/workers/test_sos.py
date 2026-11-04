"""Vest SOS: the alert follows the wearer's presses and cancels, and survives a vest restart."""

from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import ServiceToken
from alerts.models import Alert, AlertSource, AlertType

from .models import SmartVest, Worker
from .mqtt_handlers import apply_vest_telemetry


class SosAlertTests(TestCase):
    def setUp(self):
        self.ali = Worker.objects.create(name="Ali")
        self.vest = SmartVest.objects.create(vest_id="V-1", worker=self.ali)

    def report(self, active, presses):
        apply_vest_telemetry("V-1", {"sos_active": active, "sos_presses": presses})

    def sos(self):
        return Alert.objects.filter(alert_type=AlertType.SOS).order_by("id")

    def resolve_on_dashboard(self):
        self.sos().filter(is_resolved=False).update(is_resolved=True)

    def test_a_press_raises_one_alert_and_retries_do_not_duplicate(self):
        for _ in range(3):  # the vest resends until the server confirms
            self.report(True, 1)
        alert = self.sos().get()
        self.assertFalse(alert.is_resolved)
        self.assertEqual(alert.source, AlertSource.SMART_VEST)

    def test_wearer_cancel_resolves_the_alert_with_a_note(self):
        self.report(True, 1)
        self.report(False, 1)
        alert = self.sos().get()
        self.assertTrue(alert.is_resolved)
        self.assertIsNotNone(alert.resolved_at)
        self.assertTrue(alert.description.endswith("; cancelled by the wearer"))

    def test_repeat_press_while_the_alert_is_open_does_not_duplicate(self):
        self.report(True, 1)
        self.report(True, 2)
        self.assertEqual(self.sos().count(), 1)

    def test_repeat_press_after_a_supervisor_resolved_raises_again(self):
        self.report(True, 1)
        self.resolve_on_dashboard()
        self.report(True, 1)  # still in SOS, no new press: nothing new
        self.assertEqual(self.sos().count(), 1)
        self.report(True, 2)
        self.assertEqual(self.sos().count(), 2)
        self.assertFalse(self.sos().last().is_resolved)

    def test_press_after_a_cancel_raises_a_new_alert(self):
        self.report(True, 1)
        self.report(False, 1)
        self.report(True, 2)
        first, second = self.sos()
        self.assertTrue(first.is_resolved)
        self.assertFalse(second.is_resolved)

    def test_vest_restart_does_not_count_as_a_cancel(self):
        self.report(True, 3)
        self.report(False, 0)  # rebooted (power bank ran out): SOS state lost
        self.assertFalse(self.sos().get().is_resolved)
        self.vest.refresh_from_db()
        self.assertEqual(self.vest.sos_presses, 0)

    def test_vests_without_a_press_count_still_raise_and_cancel(self):
        apply_vest_telemetry("V-1", {"sos_active": True})
        apply_vest_telemetry("V-1", {"sos_active": False})
        self.assertTrue(self.sos().get().is_resolved)


class SosTelemetryApiTests(APITestCase):
    def setUp(self):
        SmartVest.objects.create(vest_id="V-1", worker=Worker.objects.create(name="Ali"))
        _, key = ServiceToken.issue("vest-1", ServiceToken.Kind.VEST_GATEWAY)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")

    def test_press_count_is_accepted_and_validated(self):
        url = "/api/v1/vests/telemetry/"
        ok = self.client.post(url, {"vest_id": "V-1", "sos_active": True, "sos_presses": 1}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(SmartVest.objects.get(vest_id="V-1").sos_presses, 1)
        bad = self.client.post(url, {"vest_id": "V-1", "sos_presses": -1}, format="json")
        self.assertEqual(bad.status_code, 400)
