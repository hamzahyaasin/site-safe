"""Camera-based worker location and zone head counts (FR-31)."""

import uuid
from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User
from alerts.models import Alert, AlertConfig, AlertType
from sitemap.models import Camera, Zone

from . import location
from .mqtt_handlers import apply_vest_telemetry
from .models import ActivityLog, SmartVest, Worker

SQUARE = [{"lat": 0, "lng": 0}, {"lat": 0, "lng": 1}, {"lat": 1, "lng": 1}, {"lat": 1, "lng": 0}]


def officer():
    user = User.objects.create_user(email=f"o{uuid.uuid4().hex[:6]}@x.io", password="pw12345678")
    user.role = Role.SAFETY_OFFICER
    user.save()
    return user


class LocationTestCase(APITestCase):
    def setUp(self):
        self.bay = Zone.objects.create(name="Bay 1", camera_ids=["CAM-01", "CAM-02"], max_occupancy=0)
        self.crane = Zone.objects.create(name="Crane", camera_ids=["CAM-09"], risk_level="RESTRICTED")
        self.ali = Worker.objects.create(name="Ali", zone=self.bay)
        _, self.key = ServiceToken.issue("cams", ServiceToken.Kind.CAMERA)

    def sight(self, camera_id, when=None, worker=None):
        self.client.force_authenticate(None)  # a signed-in user would override the device token
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {self.key}")
        r = self.client.post(
            "/api/v1/camera-activity/",
            {
                "event_id": str(uuid.uuid4()),
                "camera_id": camera_id,
                "badge_code": (worker or self.ali).badge_payload,
                "kind": "SIGHTING",
                "occurred_at": (when or timezone.now()).isoformat(),
            },
            format="json",
        )
        self.client.credentials()
        return r

    def count(self, camera_id, people, when=None, key=None):
        self.client.force_authenticate(None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key or self.key}")
        r = self.client.post(
            "/api/v1/camera-counts/",
            {"camera_id": camera_id, "people": people, "observed_at": (when or timezone.now()).isoformat()},
            format="json",
        )
        self.client.credentials()
        return r

    def zone_logs(self):
        return list(
            ActivityLog.objects.filter(worker=self.ali, action__in=["ZONE_ENTER", "ZONE_EXIT"])
            .order_by("timestamp", "id")
            .values_list("action", "zone__name")
        )

    def breaches(self):
        return Alert.objects.filter(alert_type=AlertType.ZONE_BREACH)


class CameraPlacementTests(LocationTestCase):
    def test_sighting_places_worker_in_the_cameras_zone(self):
        self.assertEqual(self.sight("CAM-01").status_code, 200)
        self.ali.refresh_from_db()
        self.assertEqual((self.ali.location_zone, self.ali.location_source, self.ali.location_device), (self.bay, "camera", "CAM-01"))
        self.assertEqual(self.zone_logs(), [("ZONE_ENTER", "Bay 1")])
        log = ActivityLog.objects.get(action="ZONE_ENTER")
        self.assertEqual(log.metadata["source"], "camera CAM-01")
        self.assertTrue(location.is_current(self.ali))

    def test_moving_between_cameras_of_one_zone_is_one_visit(self):
        now = timezone.now()
        self.sight("CAM-01", now - timedelta(seconds=30))
        self.sight("CAM-02", now - timedelta(seconds=15))
        self.sight("CAM-01", now)
        self.assertEqual(self.zone_logs(), [("ZONE_ENTER", "Bay 1")])
        self.ali.refresh_from_db()
        self.assertEqual(self.ali.location_device, "CAM-01")

    def test_camera_in_another_zone_moves_the_worker(self):
        now = timezone.now()
        self.sight("CAM-01", now - timedelta(seconds=10))
        self.sight("CAM-09", now)
        self.assertEqual(self.zone_logs(), [("ZONE_ENTER", "Bay 1"), ("ZONE_EXIT", "Bay 1"), ("ZONE_ENTER", "Crane")])

    def test_camera_without_a_zone_records_the_sighting_but_no_zone(self):
        self.sight("CAM-LOOSE")
        self.ali.refresh_from_db()
        self.assertIsNone(self.ali.location_zone)
        self.assertEqual(self.ali.location_device, "CAM-LOOSE")
        self.assertEqual(self.zone_logs(), [])

    def test_late_sighting_does_not_move_the_worker_back(self):
        now = timezone.now()
        self.sight("CAM-09", now)
        self.sight("CAM-01", now - timedelta(seconds=20))  # delivered late by the outbox
        self.ali.refresh_from_db()
        self.assertEqual(self.ali.location_zone, self.crane)

    def test_not_seen_any_more_records_exit_at_the_last_sighting(self):
        seen = timezone.now() - timedelta(seconds=90)
        self.sight("CAM-01", seen)
        self.ali.refresh_from_db()
        self.assertFalse(location.is_current(self.ali))
        zones = location.sweep_camera_exits()
        self.assertEqual(zones, {self.bay})
        exit_log = ActivityLog.objects.get(action="ZONE_EXIT")
        self.assertEqual(exit_log.timestamp, seen)
        self.assertEqual(location.sweep_camera_exits(), set(), "recorded once")
        self.ali.refresh_from_db()
        self.assertEqual(self.ali.location_zone, self.bay, "still 'last seen' in Bay 1")

    def test_simulator_sightings_place_nobody(self):
        _, sim = ServiceToken.issue("sim", ServiceToken.Kind.CAMERA, is_simulator=True)
        self.key = sim
        self.assertEqual(self.sight("CAM-01").status_code, 202)
        self.ali.refresh_from_db()
        self.assertIsNone(self.ali.location_at)

    def test_api_shows_current_and_last_seen_location(self):
        self.sight("CAM-01")
        self.client.force_authenticate(officer())
        loc = self.client.get(f"/api/workers/{self.ali.pk}/").data["location"]
        self.assertEqual((loc["zone_name"], loc["source"], loc["device"], loc["current"]), ("Bay 1", "camera", "CAM-01", True))
        Worker.objects.filter(pk=self.ali.pk).update(location_at=timezone.now() - timedelta(minutes=5))
        loc = self.client.get(f"/api/workers/{self.ali.pk}/").data["location"]
        self.assertFalse(loc["current"])
        self.assertIsNone(self.client.get(f"/api/workers/{Worker.objects.create(name='New').pk}/").data["location"])


class GpsAndCameraTests(LocationTestCase):
    def setUp(self):
        super().setUp()
        self.bay.boundaries = SQUARE
        self.bay.save()
        SmartVest.objects.create(vest_id="V-1", worker=self.ali)

    def test_recent_camera_sighting_takes_precedence_over_gps(self):
        self.sight("CAM-09")  # crane camera, no boundary of its own
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})  # GPS inside Bay 1
        self.ali.refresh_from_db()
        self.assertEqual((self.ali.location_zone, self.ali.location_source), (self.crane, "camera"))

    def test_gps_places_the_worker_once_the_camera_sighting_is_old(self):
        self.sight("CAM-09", timezone.now() - timedelta(seconds=90))
        apply_vest_telemetry("V-1", {"latitude": 0.5, "longitude": 0.5})
        self.ali.refresh_from_db()
        self.assertEqual((self.ali.location_zone, self.ali.location_source, self.ali.location_device), (self.bay, "vest", "V-1"))


class BreachTests(LocationTestCase):
    def test_camera_sees_unassigned_badge_in_restricted_zone(self):
        self.sight("CAM-09")
        breach = self.breaches().get()
        self.assertIn("restricted zone Crane", breach.description)
        self.assertIn("CAM-09", breach.description)
        self.assertEqual((breach.worker, breach.camera_id, breach.source), (self.ali, "CAM-09", "AI_CAMERA"))
        self.sight("CAM-09")
        self.assertEqual(self.breaches().count(), 1, "staying in view is not a new entry")

    def test_assigned_worker_may_be_in_restricted_zone(self):
        self.ali.zone = self.crane
        self.ali.save()
        self.sight("CAM-09")
        self.assertEqual(self.breaches().count(), 0)


class HeadCountTests(LocationTestCase):
    def test_overlapping_views_use_the_largest_count(self):
        self.count("CAM-01", 3)
        self.count("CAM-02", 2)
        occ = location.zone_occupancy(self.bay)
        self.assertEqual((occ["count"], occ["camera_count"], occ["method"], occ["cameras_reporting"]), (3, 3, "max", 2))

    def test_separate_views_add_up(self):
        self.bay.camera_views_overlap = False
        self.bay.save()
        self.count("CAM-01", 3)
        self.count("CAM-02", 2)
        occ = location.zone_occupancy(self.bay)
        self.assertEqual((occ["count"], occ["method"]), (5, "sum"))

    def test_identified_workers_are_never_double_counted(self):
        self.sight("CAM-01")
        self.count("CAM-01", 1)  # the same person, also counted by the camera
        occ = location.zone_occupancy(self.bay)
        self.assertEqual((occ["count"], occ["identified"], occ["camera_count"]), (1, 1, 1))
        sara = Worker.objects.create(name="Sara")
        self.sight("CAM-02", worker=sara)  # badge read but CAM-02's count still says nothing
        self.assertEqual(location.zone_occupancy(self.bay)["count"], 2, "never below the identified workers")

    def test_stale_camera_counts_drop_out(self):
        self.count("CAM-01", 4, when=timezone.now() - timedelta(seconds=45))
        occ = location.zone_occupancy(self.bay)
        self.assertEqual((occ["count"], occ["camera_count"], occ["cameras_reporting"]), (0, None, 0))

    def test_count_endpoint_validates_and_keeps_the_latest(self):
        now = timezone.now()
        self.assertEqual(self.count("CAM-01", 2, now).status_code, 204)
        self.assertEqual(self.count("CAM-01", 9, now - timedelta(seconds=5)).status_code, 200, "older: ignored")
        self.assertEqual(Camera.objects.get(camera_id="CAM-01").people_count, 2)
        self.assertEqual(self.count("CAM-01", -1).status_code, 400)
        self.assertEqual(self.count("CAM-01", 1, now - timedelta(minutes=20)).status_code, 400)
        _, scoped = ServiceToken.issue("cam-gate", ServiceToken.Kind.CAMERA, ["CAM-GATE"])
        self.assertEqual(self.count("CAM-01", 1, key=scoped).status_code, 400, "token for another camera")
        _, sim = ServiceToken.issue("sim", ServiceToken.Kind.CAMERA, is_simulator=True)
        self.assertEqual(self.count("CAM-01", 7, key=sim).status_code, 202)
        self.assertEqual(Camera.objects.get(camera_id="CAM-01").people_count, 2)
        self.client.force_authenticate(officer())
        self.assertEqual(self.client.post("/api/v1/camera-counts/", {}, format="json").status_code, 403)


class CapacityTests(LocationTestCase):
    """Over-capacity alerts with hysteresis: confirm after 10 s over, re-arm after 60 s within."""

    def setUp(self):
        super().setUp()
        self.bay.max_occupancy = 2
        self.bay.save()
        self.t0 = timezone.now()

    def at(self, seconds, people=None):
        """Advance to t0 + seconds, optionally with a new CAM-01 count, and evaluate capacity."""
        when = self.t0 + timedelta(seconds=seconds)
        if people is not None:
            location.record_camera_count("CAM-01", people, when)
        location.check_capacity(self.bay, now=when)
        self.bay.refresh_from_db()

    def test_alert_needs_the_zone_over_for_the_confirm_time(self):
        self.at(0, people=3)
        self.at(5)
        self.assertEqual(self.breaches().count(), 0, "5 s over: not yet")
        self.at(11)
        self.assertEqual(self.breaches().count(), 1)
        self.assertIn("Bay 1 over capacity: 3 present, limit 2", self.breaches().get().description)
        self.assertIsNotNone(self.bay.capacity_alerted_at)

    def test_a_steady_count_confirms_on_the_next_report(self):
        # Unchanged reports (every 5 s from the camera) still advance the state.
        for second in (0, 5, 10, 15):
            location.record_camera_count("CAM-01", 3, self.t0 + timedelta(seconds=second))
        self.assertEqual(self.breaches().count(), 1)

    def test_brief_spike_never_alerts(self):
        self.at(0, people=3)
        self.at(4, people=1)
        self.at(20)
        self.assertEqual(self.breaches().count(), 0)
        self.assertIsNone(self.bay.over_capacity_since)

    def test_one_alert_per_period_and_re_arm_after_the_clear_time(self):
        self.at(0, people=3)
        self.at(11)
        self.at(15, people=1)  # dips below...
        self.at(25, people=4)  # ...and back over within the clear time: same period
        self.at(40)
        self.assertEqual(self.breaches().count(), 1)
        self.at(45, people=1)
        self.at(80, people=1)
        self.assertIsNotNone(self.bay.capacity_alerted_at, "35 s within: not re-armed yet")
        self.at(106, people=1)
        self.assertIsNone(self.bay.capacity_alerted_at, "61 s within: re-armed")
        self.at(110, people=3)
        self.at(121)
        self.assertEqual(self.breaches().count(), 2, "a new period")

    def test_stale_counts_end_the_period(self):
        self.at(0, people=3)
        self.at(11)
        location.sweep_zone_counts(now=self.t0 + timedelta(seconds=45))  # CAM-01 went quiet: count stale
        location.sweep_zone_counts(now=self.t0 + timedelta(seconds=106))
        self.bay.refresh_from_db()
        self.assertIsNone(self.bay.capacity_alerted_at)

    def test_rule_disables_capacity_alerts(self):
        AlertConfig.objects.filter(alert_type=AlertType.ZONE_BREACH, zone=None).update(is_enabled=False)
        self.at(0, people=5)
        self.at(11)
        self.assertEqual(self.breaches().count(), 0)


class ZoneApiTests(LocationTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(User.objects.create_superuser(email="admin@x.io", password="pw12345678"))

    def test_zone_api_reports_head_count_and_how(self):
        self.count("CAM-01", 2)
        self.sight("CAM-02")
        self.client.force_authenticate(officer())
        bay = next(z for z in self.client.get("/api/v1/zones/").data if z["name"] == "Bay 1")
        self.assertEqual(bay["current_occupancy"], 2)
        self.assertEqual(bay["occupancy"]["identified"], 1)
        self.assertEqual(bay["occupancy"]["method"], "max")
        self.assertTrue(bay["camera_views_overlap"])

    def test_a_camera_belongs_to_one_zone(self):
        r = self.client.post(
            "/api/v1/zones/", {"name": "Yard", "camera_ids": ["CAM-02", "CAM-20"], "boundaries": []}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("CAM-02 (Bay 1)", str(r.data["camera_ids"]))
        r = self.client.patch(f"/api/v1/zones/{self.bay.pk}/", {"camera_ids": ["CAM-01", "CAM-03"]}, format="json")
        self.assertEqual(r.status_code, 200, "a zone keeps its own cameras when edited")

    def test_count_changes_are_broadcast(self):
        with mock.patch("alerts.events.publish_zones") as publish:
            self.count("CAM-01", 2)
            self.count("CAM-01", 2)
        self.assertEqual(publish.call_count, 1, "an unchanged count is not re-broadcast")


class DashboardTests(LocationTestCase):
    def test_camera_seen_workers_are_on_site(self):
        self.sight("CAM-01")
        self.client.force_authenticate(officer())
        r = self.client.get("/api/dashboard/stats/", {"tz": "UTC"}).data
        self.assertEqual((r["workers_on_site"], r["workers_on_site_by_camera"], r["workers_on_site_by_vest"]), (1, 1, 0))


@override_settings(CAMERA_PRESENCE_SECONDS=60)
class SweepTests(LocationTestCase):
    def test_sweep_broadcasts_only_changed_counts(self):
        from django.core.cache import cache

        cache.delete(location.LAST_PUBLISHED_KEY)
        self.sight("CAM-01")
        with mock.patch("alerts.events.publish_zones") as publish:
            location.sweep_zone_counts()
            location.sweep_zone_counts()
        first, second = (c.args[0] for c in publish.call_args_list)
        self.assertEqual({z.name for z in first}, {"Bay 1", "Crane"})
        self.assertEqual(second, [])


class BroadcastPayloadTests(LocationTestCase):
    def test_worker_and_zone_payloads_are_plain_json(self):
        # The dashboard socket encodes payloads with json.dumps; a datetime
        # in one closed every client's socket (live run, 27 Oct).
        import json

        from sitemap.serializers import ZoneDetailSerializer

        from .serializers import WorkerSerializer

        self.sight("CAM-01")
        self.count("CAM-01", 2)
        self.ali.refresh_from_db()
        json.dumps(WorkerSerializer(self.ali).data)
        self.bay.refresh_from_db()
        json.dumps(ZoneDetailSerializer(self.bay).data)
