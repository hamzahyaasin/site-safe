from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from alerts.models import Alert, AlertConfig, AlertType
from sitemap.models import Zone

from .mqtt_handlers import apply_vest_telemetry
from .models import ActivityLog, SmartVest, Worker
from .presence import is_vest_online, observed_occupancy, sweep_stale_vests

SQUARE = [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 1}, {"lat": 1, "lng": 1}, {"lat": 1, "lng": 0}]
INNER = [{"lat": 0.4, "lng": 0.4}, {"lat": 0.4, "lng": 0.6}, {"lat": 0.6, "lng": 0.6}, {"lat": 0.6, "lng": 0.4}]


def officer():
    u = User.objects.create_user(email="o@x.io", password="pw12345678")
    u.role = Role.SAFETY_OFFICER
    u.save()
    return u


class VestAssignmentTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(officer())
        self.v1 = SmartVest.objects.create(vest_id="V-1")
        self.v2 = SmartVest.objects.create(vest_id="V-2")

    def test_create_worker_with_and_without_vest(self):
        r = self.client.post("/api/workers/", {"name": "Ali", "vest": self.v1.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["vest_id"], "V-1")
        r = self.client.post("/api/workers/", {"name": "Sara"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(r.data["vest_id"])

    def test_vest_cannot_be_double_assigned(self):
        self.client.post("/api/workers/", {"name": "Ali", "vest": self.v1.id}, format="json")
        r = self.client.post("/api/workers/", {"name": "Sara", "vest": self.v1.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reassign_and_unassign(self):
        w = Worker.objects.create(name="Ali")
        self.client.patch(f"/api/workers/{w.id}/", {"vest": self.v1.id}, format="json")
        r = self.client.patch(f"/api/workers/{w.id}/", {"vest": self.v2.id}, format="json")
        self.assertEqual(r.data["vest_id"], "V-2")
        self.v1.refresh_from_db()
        self.assertIsNone(self.v1.worker_id)
        r = self.client.patch(f"/api/workers/{w.id}/", {"vest": None}, format="json")
        self.assertIsNone(r.data["vest_id"])

    def test_deactivating_releases_vest(self):
        w = Worker.objects.create(name="Ali")
        self.v1.worker = w
        self.v1.save()
        r = self.client.patch(f"/api/workers/{w.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.v1.refresh_from_db()
        self.assertIsNone(self.v1.worker_id)

    def test_blank_name_rejected(self):
        r = self.client.post("/api/workers/", {"name": "  "}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vest_side_assignment_rejects_worker_with_vest(self):
        w = Worker.objects.create(name="Ali")
        self.v1.worker = w
        self.v1.save()
        r = self.client.patch(f"/api/v1/vests/{self.v2.id}/", {"worker": w.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        gone = Worker.objects.create(name="Gone", is_active=False)
        r = self.client.patch(f"/api/v1/vests/{self.v2.id}/", {"worker": gone.id}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registry_cannot_write_telemetry(self):
        r = self.client.patch(
            f"/api/v1/vests/{self.v1.id}/", {"battery_level": 90, "sos_active": True}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.v1.refresh_from_db()
        self.assertIsNone(self.v1.battery_level)
        self.assertFalse(self.v1.sos_active)


@override_settings(VEST_OFFLINE_AFTER_SECONDS=60)
class PresenceTests(TestCase):
    def setUp(self):
        self.worker = Worker.objects.create(name="Ali")
        self.vest = SmartVest.objects.create(vest_id="V-1", worker=self.worker)

    def test_never_reported_is_offline(self):
        self.assertFalse(is_vest_online(self.vest))

    def test_goes_offline_after_timeout(self):
        apply_vest_telemetry("V-1", {"battery_level": 80})
        self.vest.refresh_from_db()
        self.assertTrue(is_vest_online(self.vest))
        later = timezone.now() + timedelta(seconds=61)
        self.assertFalse(is_vest_online(self.vest, now=later))

    def test_sweep_persists_and_broadcasts(self):
        apply_vest_telemetry("V-1", {"battery_level": 80})
        SmartVest.objects.filter(pk=self.vest.pk).update(last_seen=timezone.now() - timedelta(minutes=5))
        with mock.patch("alerts.events._send") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(sweep_stale_vests(), 1)
        self.vest.refresh_from_db()
        self.assertFalse(self.vest.is_online)
        self.assertIn("vest_updated", [c.args[0] for c in send.call_args_list])
        self.assertEqual(sweep_stale_vests(), 0)

    def test_api_reports_stale_vest_offline_without_sweep(self):
        apply_vest_telemetry("V-1", {"battery_level": 80})
        SmartVest.objects.filter(pk=self.vest.pk).update(last_seen=timezone.now() - timedelta(minutes=5))
        from .serializers import SmartVestSerializer

        self.vest.refresh_from_db()
        self.assertTrue(self.vest.is_online)  # stored flag not yet swept
        self.assertFalse(SmartVestSerializer(self.vest).data["is_online"])


class ZoneBreachTests(TestCase):
    def setUp(self):
        self.site = Zone.objects.create(name="Site", boundaries=SQUARE, risk_level="MEDIUM", max_occupancy=1)
        self.restricted = Zone.objects.create(name="Crane", boundaries=INNER, risk_level="RESTRICTED")
        self.ali = Worker.objects.create(name="Ali", zone=self.site)
        self.sara = Worker.objects.create(name="Sara", zone=self.site)
        SmartVest.objects.create(vest_id="V-1", worker=self.ali)
        SmartVest.objects.create(vest_id="V-2", worker=self.sara)

    def breaches(self):
        return Alert.objects.filter(alert_type=AlertType.ZONE_BREACH)

    def test_restricted_entry_raises_once(self):
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        apply_vest_telemetry("V-1", {"latitude": 0.51, "longitude": 0.5})
        self.assertEqual(self.breaches().count(), 1)
        self.assertIn("restricted", self.breaches().get().description)
        # Leaving and re-entering is a new breach.
        apply_vest_telemetry("V-1", {"latitude": 0.1, "longitude": 0.1})
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        self.assertEqual(self.breaches().count(), 2)

    def test_assigned_worker_may_enter_restricted(self):
        self.ali.zone = self.restricted
        self.ali.save()
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        self.assertEqual(self.breaches().count(), 0)

    def test_overlap_prefers_restricted_zone(self):
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        log = ActivityLog.objects.filter(action=ActivityLog.Action.ZONE_ENTER).first()
        self.assertEqual(log.zone, self.restricted)

    def test_over_capacity(self):
        apply_vest_telemetry("V-1", {"latitude": 0.1, "longitude": 0.1})
        self.assertEqual(self.breaches().count(), 0)
        self.assertEqual(observed_occupancy(self.site.pk), 1)
        apply_vest_telemetry("V-2", {"latitude": 0.2, "longitude": 0.2})
        self.assertEqual(observed_occupancy(self.site.pk), 2)
        self.assertEqual(self.breaches().count(), 1)
        self.assertIn("over capacity", self.breaches().get().description)

    def test_rule_disables_breaches(self):
        AlertConfig.objects.filter(alert_type=AlertType.ZONE_BREACH, zone=None).update(is_enabled=False)
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        self.assertEqual(self.breaches().count(), 0)

    def test_battery_only_report_does_not_move_worker(self):
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        apply_vest_telemetry("V-1", {"battery_level": 50})
        self.assertEqual(ActivityLog.objects.count(), 1)

    def test_stale_vest_not_counted_in_occupancy(self):
        apply_vest_telemetry("V-1", {"latitude": 0.1, "longitude": 0.1})
        SmartVest.objects.filter(vest_id="V-1").update(last_seen=timezone.now() - timedelta(hours=1))
        self.assertEqual(observed_occupancy(self.site.pk), 0)

    def test_breach_alert_reports_zone_where_it_happened(self):
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        from alerts.serializers import AlertSerializer

        self.assertEqual(AlertSerializer(self.breaches().get()).data["zone_name"], "Crane")

    def test_zone_api_shows_assigned_and_observed(self):
        apply_vest_telemetry("V-1", {"latitude": 0.1, "longitude": 0.1})
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(officer())
        data = {z["name"]: z for z in c.get("/api/v1/zones/").data}
        self.assertEqual(data["Site"]["worker_count"], 2)
        self.assertEqual(data["Site"]["current_occupancy"], 1)
        self.assertEqual(data["Crane"]["current_occupancy"], 0)


class DashboardStatsTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(officer())

    def test_empty_site(self):
        r = self.client.get("/api/dashboard/stats/", {"tz": "Asia/Karachi"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["timezone"], "Asia/Karachi")
        self.assertEqual(r.data["workers_on_site"], 0)
        self.assertEqual(len(r.data["daily_7d"]), 7)
        self.assertTrue(all(d["total"] == 0 for d in r.data["daily_7d"]))
        self.assertIsNone(r.data["mean_resolution_minutes_7d"])

    def test_counts_reconcile(self):
        w = Worker.objects.create(name="Ali")
        SmartVest.objects.create(vest_id="V-1", worker=w)
        apply_vest_telemetry("V-1", {"battery_level": 70})
        Worker.objects.create(name="No vest")
        a = Alert.objects.create(alert_type="FALL", severity="CRITICAL")
        Alert.objects.create(alert_type="SOS", severity="CRITICAL", source="SIMULATED")
        Alert.objects.filter(pk=a.pk).update(
            is_resolved=True, resolved_at=a.timestamp + timedelta(minutes=10)
        )
        r = self.client.get("/api/dashboard/stats/", {"tz": "UTC"}).data
        self.assertEqual((r["active_workers"], r["workers_with_vest"], r["workers_on_site"]), (2, 1, 1))
        self.assertEqual(r["total_alerts_today"], 2)
        self.assertEqual(r["simulated_alerts_today"], 1)
        self.assertEqual(r["unresolved_alerts"], 1)
        self.assertEqual(sum(h["count"] for h in r["hourly_today"]), 2)
        self.assertEqual(r["daily_7d"][-1]["total"], 2)
        self.assertEqual(r["daily_7d"][-1]["resolved"], 1)
        self.assertEqual(r["mean_resolution_minutes_7d"], 10.0)
        self.assertEqual(r["today_by_type"]["FALL"], 1)

    def test_bad_timezone_falls_back(self):
        r = self.client.get("/api/dashboard/stats/", {"tz": "Not/AZone"})
        self.assertEqual(r.data["timezone"], "UTC")


class BadgeTests(APITestCase):
    def setUp(self):
        self.officer = officer()
        self.worker = Worker.objects.create(name="Ali", role="Rigger")

    def test_each_worker_gets_unique_code(self):
        other = Worker.objects.create(name="Sara")
        self.assertTrue(self.worker.badge_code)
        self.assertNotEqual(self.worker.badge_code, other.badge_code)

    def test_badge_payload_requires_officer(self):
        viewer = User.objects.create_user(email="v@x.io", password="pw12345678")
        viewer.role = Role.VIEWER
        viewer.save()
        self.client.force_authenticate(viewer)
        self.assertEqual(self.client.get(f"/api/workers/{self.worker.id}/badge/").status_code, 403)
        listing = self.client.get("/api/workers/").data[0]
        self.assertNotIn("badge_code", listing)
        self.client.force_authenticate(self.officer)
        r = self.client.get(f"/api/workers/{self.worker.id}/badge/")
        self.assertEqual(r.data["payload"], f"SSW1:{self.worker.badge_code}")

    def test_reissue_revokes_old_code(self):
        self.client.force_authenticate(self.officer)
        old = self.worker.badge_payload
        new = self.client.post(f"/api/workers/{self.worker.id}/badge/").data["payload"]
        self.assertNotEqual(old, new)
        self.assertIsNone(Worker.from_badge(old))
        self.assertEqual(Worker.from_badge(new), self.worker)

    def test_deactivated_worker_badge_not_recognised(self):
        self.worker.is_active = False
        self.worker.save()
        self.assertIsNone(Worker.from_badge(self.worker.badge_payload))


class CameraBadgeIdentityTests(APITestCase):
    def setUp(self):
        _, key = ServiceToken.issue("cam", ServiceToken.Kind.CAMERA)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")
        self.worker = Worker.objects.create(name="Ali")

    def post(self, badge):
        import uuid

        return self.client.post(
            "/api/v1/camera-events/",
            {
                "event_id": str(uuid.uuid4()),
                "camera_id": "CAM-01",
                "alert_type": "PPE_VIOLATION",
                "severity": "HIGH",
                "description": "Missing PPE: no-helmet",
                "badge_code": badge,
            },
            format="json",
        )

    def test_known_badge_attributes_worker(self):
        r = self.post(self.worker.badge_payload)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["worker"], self.worker.id)
        self.assertIn("identified by QR badge", r.data["description"])

    def test_unknown_badge_stays_unidentified(self):
        r = self.post("SSW1:not-a-real-code")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data["worker"])
        self.assertIn("not recognised", r.data["description"])

    def test_no_badge(self):
        r = self.post("")
        self.assertIsNone(r.data["worker"])
        self.assertNotIn("badge", r.data["description"])
