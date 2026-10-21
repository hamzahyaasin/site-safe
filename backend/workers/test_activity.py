"""Automatic check-in/out, idle periods and daily timelines."""

import uuid
from datetime import date, datetime, timedelta, timezone as dt_tz
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import Role, ServiceToken, User

from . import activity
from .models import ActivityLog, SmartVest, Worker
from .mqtt_handlers import apply_vest_telemetry
from .timeline import build_timeline

UTC = dt_tz.utc
PKT = ZoneInfo("Asia/Karachi")


def at(h, m=0, day=15):
    return datetime(2026, 10, day, h, m, tzinfo=UTC)


def actions(worker):
    return list(ActivityLog.objects.filter(worker=worker).order_by("timestamp", "id").values_list("action", flat=True))


@override_settings(CHECKOUT_AFTER_MINUTES=30)
class SessionTests(TestCase):
    def setUp(self):
        self.w = Worker.objects.create(name="Ali")

    def test_first_sighting_checks_in_once(self):
        activity.record_seen(self.w, at(8), "camera CAM-01")
        activity.record_seen(self.w, at(8, 5), "camera CAM-01")
        self.assertEqual(actions(self.w), ["CHECK_IN"])
        self.w.refresh_from_db()
        self.assertEqual(self.w.last_seen_at, at(8, 5))

    def test_checkout_dated_to_last_sighting(self):
        activity.record_seen(self.w, at(8))
        activity.record_seen(self.w, at(12))
        self.assertEqual(activity.sweep_checkouts(now=at(12, 20)), 0)  # within 30 min
        self.assertEqual(activity.sweep_checkouts(now=at(12, 40)), 1)
        out = ActivityLog.objects.get(action="CHECK_OUT")
        self.assertEqual(out.timestamp, at(12))
        self.assertTrue(out.metadata["automatic"])
        self.assertEqual(activity.sweep_checkouts(now=at(13)), 0)  # already closed

    def test_return_after_checkout_starts_new_session(self):
        activity.record_seen(self.w, at(8))
        activity.sweep_checkouts(now=at(9))
        activity.record_seen(self.w, at(13))
        self.assertEqual(actions(self.w), ["CHECK_IN", "CHECK_OUT", "CHECK_IN"])

    def test_late_event_does_not_rewind_last_seen(self):
        activity.record_seen(self.w, at(12))
        activity.record_seen(self.w, at(11, 50), "late outbox delivery")
        self.w.refresh_from_db()
        self.assertEqual(self.w.last_seen_at, at(12))
        self.assertEqual(actions(self.w), ["CHECK_IN"])
        self.assertEqual(ActivityLog.objects.get().timestamp, at(11, 50))  # session starts earlier

    def test_late_event_after_auto_checkout_extends_session(self):
        activity.record_seen(self.w, at(8))
        activity.sweep_checkouts(now=at(9))  # checked out at 08:00 (last seen)
        activity.record_seen(self.w, at(8, 10), "late outbox delivery")
        self.assertEqual(actions(self.w), ["CHECK_IN", "CHECK_OUT"])
        self.assertEqual(ActivityLog.objects.get(action="CHECK_OUT").timestamp, at(8, 10))

    def test_far_apart_events_are_separate_sessions(self):
        activity.record_seen(self.w, at(12))
        activity.record_seen(self.w, at(9), "much earlier")
        self.assertEqual(actions(self.w), ["CHECK_IN", "CHECK_OUT", "CHECK_IN"])
        t = build_timeline(self.w, date(2026, 10, 15), UTC, now=at(12, 30))
        self.assertEqual(t["on_site_minutes"], 30)  # 12:00–12:30 only, not 09:00–12:30

    def test_idle_period_and_checkout_closes_open_idle(self):
        activity.idle_start(self.w, at(10))
        activity.idle_start(self.w, at(10, 1))  # duplicate ignored
        activity.idle_end(self.w, at(10, 20))
        activity.idle_start(self.w, at(11))
        activity.sweep_checkouts(now=at(12))
        self.assertEqual(actions(self.w), ["CHECK_IN", "IDLE_START", "IDLE_END", "IDLE_START", "IDLE_END", "CHECK_OUT"])

    def test_inactive_worker_ignored(self):
        self.w.is_active = False
        self.w.save()
        activity.record_seen(self.w, at(8))
        self.assertEqual(actions(self.w), [])

    def test_vest_telemetry_checks_in_simulator_does_not(self):
        SmartVest.objects.create(vest_id="V-1", worker=self.w)
        apply_vest_telemetry("V-1", {"battery_level": 80}, simulated=True)
        self.assertEqual(actions(self.w), [])
        apply_vest_telemetry("V-1", {"battery_level": 80})
        self.assertEqual(actions(self.w), ["CHECK_IN"])
        self.assertTrue(ActivityLog.objects.get().metadata["source"].startswith("vest"))


class TimelineTests(TestCase):
    def setUp(self):
        self.w = Worker.objects.create(name="Ali")

    def log(self, action, when, zone=None):
        ActivityLog.objects.create(worker=self.w, action=action, timestamp=when, zone=zone)

    def test_totals_and_intervals(self):
        from sitemap.models import Zone

        bay = Zone.objects.create(name="Bay 1")
        self.log("CHECK_IN", at(8))
        self.log("ZONE_ENTER", at(8, 30), bay)
        self.log("IDLE_START", at(10))
        self.log("IDLE_END", at(10, 15))
        self.log("ZONE_EXIT", at(11, 30), bay)
        self.log("CHECK_OUT", at(12))
        t = build_timeline(self.w, date(2026, 10, 15), UTC, now=at(20))
        self.assertEqual(t["on_site_minutes"], 240)
        self.assertEqual(t["idle_minutes"], 15)
        self.assertEqual(t["zone_minutes"], {"Bay 1": 180})
        self.assertEqual(t["first_check_in"], at(8).isoformat())
        self.assertFalse(t["sessions"][0]["open"])

    def test_night_shift_is_split_at_local_midnight(self):
        # 22:00–02:00 PKT = 17:00–21:00 UTC on the 15th.
        self.log("CHECK_IN", at(17))
        self.log("CHECK_OUT", at(21))
        first = build_timeline(self.w, date(2026, 10, 15), PKT, now=at(23))
        second = build_timeline(self.w, date(2026, 10, 16), PKT, now=at(23))
        self.assertEqual(first["on_site_minutes"], 120)
        self.assertEqual(second["on_site_minutes"], 120)
        self.assertIsNone(second["first_check_in"])  # carried over, not a new check-in

    def test_open_session_today_runs_to_now(self):
        self.log("CHECK_IN", at(8))
        t = build_timeline(self.w, date(2026, 10, 15), UTC, now=at(9, 30))
        self.assertEqual(t["on_site_minutes"], 90)
        self.assertTrue(t["sessions"][0]["open"])

    def test_no_activity_day(self):
        t = build_timeline(self.w, date(2026, 10, 15), UTC, now=at(20))
        self.assertFalse(t["has_activity"])
        self.assertEqual(t["on_site_minutes"], 0)


class ActivityApiTests(APITestCase):
    def setUp(self):
        self.w = Worker.objects.create(name="Ali")
        viewer = User.objects.create_user(email="v@x.io", password="pw12345678")
        viewer.role = Role.VIEWER
        viewer.save()
        self.viewer = viewer
        _, self.key = ServiceToken.issue("cam", ServiceToken.Kind.CAMERA)
        _, self.sim = ServiceToken.issue("simcam", ServiceToken.Kind.CAMERA, is_simulator=True)

    def post(self, key, kind="SIGHTING", badge=None, when=None):
        self.client.credentials(HTTP_AUTHORIZATION=f"Device {key}")
        return self.client.post(
            "/api/v1/camera-activity/",
            {
                "event_id": str(uuid.uuid4()),
                "camera_id": "CAM-01",
                "badge_code": badge or self.w.badge_payload,
                "kind": kind,
                "occurred_at": (when or timezone.now()).isoformat(),
            },
            format="json",
        )

    def test_camera_sighting_and_idle(self):
        now = timezone.now()
        self.assertEqual(self.post(self.key, when=now - timedelta(minutes=10)).status_code, 200)
        self.post(self.key, "IDLE_START", when=now - timedelta(minutes=8))
        self.post(self.key, "IDLE_END", when=now - timedelta(minutes=2))
        self.assertEqual(actions(self.w), ["CHECK_IN", "IDLE_START", "IDLE_END"])

    def test_unknown_badge_and_simulator_ignored(self):
        self.assertEqual(self.post(self.key, badge="SSW1:nope").status_code, 202)
        self.assertEqual(self.post(self.sim).status_code, 202)
        self.assertEqual(actions(self.w), [])

    def test_occurred_at_bounds(self):
        self.assertEqual(self.post(self.key, when=timezone.now() + timedelta(minutes=5)).status_code, 400)
        self.assertEqual(self.post(self.key, when=timezone.now() - timedelta(days=2)).status_code, 400)

    def test_requires_camera_token(self):
        self.client.force_authenticate(self.viewer)
        r = self.client.post("/api/v1/camera-activity/", {}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_timeline_and_daily_endpoints(self):
        # Yesterday's shift: a shift today would still be partly in the
        # future before noon, and the timeline rightly stops at "now".
        today = timezone.now().astimezone(PKT).date()
        day = today - timedelta(days=1)
        start = datetime.combine(day, datetime.min.time(), tzinfo=PKT) + timedelta(hours=9)
        ActivityLog.objects.create(worker=self.w, action="CHECK_IN", timestamp=start)
        ActivityLog.objects.create(worker=self.w, action="CHECK_OUT", timestamp=start + timedelta(hours=3))
        self.client.credentials()
        self.client.force_authenticate(self.viewer)
        t = self.client.get("/api/v1/activity/timeline/", {"worker_id": self.w.id, "date": day.isoformat(), "tz": "Asia/Karachi"}).data
        self.assertEqual(t["on_site_minutes"], 180)
        rows = self.client.get(
            "/api/v1/activity/daily/",
            {"start_date": (today - timedelta(days=2)).isoformat(), "end_date": today.isoformat(), "tz": "Asia/Karachi"},
        ).data
        self.assertEqual([(r["worker_name"], r["on_site_minutes"]) for r in rows], [("Ali", 180)])
        s = self.client.get("/api/v1/activity/summary/", {"worker_id": self.w.id, "date": day.isoformat(), "tz": "Asia/Karachi"}).data
        self.assertEqual(s["hours_worked"], 3.0)
        bad = self.client.get("/api/v1/activity/daily/", {"start_date": "2026-01-01", "end_date": "2026-03-01"})
        self.assertEqual(bad.status_code, 400)
