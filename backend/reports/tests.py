from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock
from zoneinfo import ZoneInfo

import requests
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Role, User
from alerts.models import Alert

from .models import Report

PDF = b"%PDF-1.7 fake"


def upstream(status_code=200, content=PDF, content_type="application/pdf", json_body=None):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.content = content
    resp.headers = {
        "Content-Type": content_type,
        "Content-Disposition": 'attachment; filename="incident_report_2026-10-01_2026-10-16.pdf"',
    }
    resp.text = "" if json_body is None else str(json_body)
    resp.json = mock.Mock(return_value=json_body) if json_body is not None else mock.Mock(side_effect=ValueError)
    return resp


@override_settings(MEDIA_ROOT="/tmp/sitesafe-test-media")
class GenerateReportTests(APITestCase):
    url = "/api/v1/reports/generate/"
    body = {"report_type": "INCIDENT", "date_from": "2026-10-01", "date_to": "2026-10-16", "file_format": "PDF", "tz": "Asia/Karachi"}

    def setUp(self):
        self.user = User.objects.create_user(email="o@x.io", password="pw12345678")
        self.user.role = Role.SAFETY_OFFICER
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}")

    def test_pdf_generated_saved_and_downloadable(self):
        with mock.patch("reports.proxy.requests.post", return_value=upstream()) as post:
            r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertEqual(r.content, PDF)
        sent = post.call_args.kwargs["json"]
        self.assertEqual((sent["format"], sent["tz"]), ("PDF", "Asia/Karachi"))
        report = Report.objects.get()
        self.assertEqual(report.file_format, "PDF")
        d = self.client.get(f"/api/v1/reports/{report.id}/download/")
        self.assertEqual(d["Content-Type"], "application/pdf")
        self.assertEqual(d.content, PDF)

    def test_dashboard_origin_can_read_the_file_name(self):
        with mock.patch("reports.proxy.requests.post", return_value=upstream()):
            r = self.client.post(self.url, self.body, format="json", HTTP_ORIGIN="http://localhost:5173")
        self.assertIn("Content-Disposition", r["Access-Control-Expose-Headers"])

    def test_evidence_is_included_by_default_and_recorded(self):
        with mock.patch("reports.proxy.requests.post", return_value=upstream()) as post:
            self.client.post(self.url, self.body, format="json")
        self.assertIs(post.call_args.kwargs["json"]["include_evidence"], True)
        report = Report.objects.get()
        self.assertTrue(report.includes_evidence)
        listed = self.client.get("/api/v1/reports/").data[0]
        self.assertIs(listed["includes_evidence"], True)

    def test_evidence_can_be_left_out(self):
        with mock.patch("reports.proxy.requests.post", return_value=upstream()) as post:
            self.client.post(self.url, {**self.body, "include_evidence": False}, format="json")
        self.assertIs(post.call_args.kwargs["json"]["include_evidence"], False)
        self.assertFalse(Report.objects.get().includes_evidence)

    def test_upstream_error_body_is_relayed_and_nothing_saved(self):
        with mock.patch(
            "reports.proxy.requests.post",
            return_value=upstream(status_code=400, json_body={"detail": "bad dates"}),
        ):
            r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data, {"detail": "bad dates"})
        self.assertFalse(Report.objects.exists())

    def test_service_down(self):
        with mock.patch("reports.proxy.requests.post", side_effect=requests.ConnectionError("refused")):
            r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 502)
        self.assertFalse(Report.objects.exists())

    def test_wrong_or_empty_document_rejected(self):
        for bad in (upstream(content=b""), upstream(content_type="text/html")):
            with mock.patch("reports.proxy.requests.post", return_value=bad):
                r = self.client.post(self.url, self.body, format="json")
            self.assertEqual(r.status_code, 502)
        self.assertFalse(Report.objects.exists())

    def test_bad_timezone_and_dates(self):
        r = self.client.post(self.url, {**self.body, "tz": "Mars/Base"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post(self.url, {**self.body, "date_from": "2026-10-20"}, format="json")
        self.assertEqual(r.status_code, 400)


class LocalDateFilterTests(APITestCase):
    def setUp(self):
        user = User.objects.create_user(email="v@x.io", password="pw12345678")
        self.client.force_authenticate(user)

    def make(self, when):
        a = Alert.objects.create(alert_type="FALL", severity="HIGH")
        Alert.objects.filter(pk=a.pk).update(timestamp=when)
        return a

    def test_day_bounds_follow_requested_timezone(self):
        pkt = ZoneInfo("Asia/Karachi")  # UTC+5
        # 23:30 on 15 Oct in Karachi is 18:30 UTC on 15 Oct.
        late = self.make(datetime(2026, 10, 15, 23, 30, tzinfo=pkt))
        # 00:30 on 16 Oct in Karachi is 19:30 UTC on 15 Oct (still the 15th in UTC).
        early = self.make(datetime(2026, 10, 16, 0, 30, tzinfo=pkt))
        r = self.client.get("/api/alerts/", {"start_date": "2026-10-16", "end_date": "2026-10-16", "tz": "Asia/Karachi"})
        self.assertEqual([a["id"] for a in r.data], [early.id])
        r = self.client.get("/api/alerts/", {"start_date": "2026-10-15", "end_date": "2026-10-15", "tz": "UTC"})
        self.assertEqual({a["id"] for a in r.data}, {late.id, early.id})
