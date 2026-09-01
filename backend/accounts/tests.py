"""Tests for role-based access control.

Section 3.7 of the project report specifies Admin, Safety Officer and
read-only Viewer roles enforced at the API level. These tests assert that
the enforcement is real — that a Viewer is actually refused a write by the
API rather than merely having the button hidden in the interface.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from alerts.models import Alert, AlertType, Severity
from sitemap.models import Zone

from .models import Role, User


class RoleModelTests(APITestCase):
    def test_rank_ordering(self):
        self.assertGreater(Role.rank(Role.ADMIN), Role.rank(Role.SAFETY_OFFICER))
        self.assertGreater(Role.rank(Role.SAFETY_OFFICER), Role.rank(Role.VIEWER))

    def test_unknown_role_ranks_lowest(self):
        self.assertEqual(Role.rank("NOT_A_ROLE"), 0)

    def test_legacy_admin_flag_still_grants_admin(self):
        """Accounts created before roles existed must not lose privileges."""
        legacy = User.objects.create_user(email="legacy@x.io", password="pw12345678")
        legacy.is_admin = True
        legacy.role = Role.VIEWER  # column never populated properly
        legacy.save()
        self.assertTrue(legacy.has_role_at_least(Role.ADMIN))

    def test_viewer_is_not_safety_officer(self):
        viewer = User.objects.create_user(email="v@x.io", password="pw12345678")
        viewer.role = Role.VIEWER
        viewer.save()
        self.assertTrue(viewer.has_role_at_least(Role.VIEWER))
        self.assertFalse(viewer.has_role_at_least(Role.SAFETY_OFFICER))
        self.assertFalse(viewer.has_role_at_least(Role.ADMIN))


class RolePermissionTests(APITestCase):
    """Exercises the real API surface for each role."""

    def setUp(self):
        def mk(email, role):
            u = User.objects.create_user(email=email, password="pw12345678")
            u.role = role
            u.save()
            return u

        self.viewer = mk("viewer@x.io", Role.VIEWER)
        self.officer = mk("officer@x.io", Role.SAFETY_OFFICER)
        self.admin = mk("admin@x.io", Role.ADMIN)

        self.zone = Zone.objects.create(name="Bay 1")
        self.alert = Alert.objects.create(
            alert_type=AlertType.PPE_VIOLATION,
            severity=Severity.HIGH,
        )

    # ---- reads ----

    def test_all_roles_can_read_alerts(self):
        for user in (self.viewer, self.officer, self.admin):
            self.client.force_authenticate(user)
            r = self.client.get("/api/alerts/")
            self.assertEqual(r.status_code, status.HTTP_200_OK, f"{user.role} should read")

    def test_all_roles_can_read_zones(self):
        for user in (self.viewer, self.officer, self.admin):
            self.client.force_authenticate(user)
            r = self.client.get("/api/v1/zones/")
            self.assertEqual(r.status_code, status.HTTP_200_OK, f"{user.role} should read")

    def test_anonymous_is_refused(self):
        r = self.client.get("/api/alerts/")
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- operational writes: Safety Officer and above ----

    def test_viewer_cannot_resolve_alert(self):
        self.client.force_authenticate(self.viewer)
        r = self.client.post(f"/api/alerts/{self.alert.id}/resolve/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.alert.refresh_from_db()
        self.assertFalse(self.alert.is_resolved, "viewer must not mutate state")

    def test_officer_can_resolve_alert(self):
        self.client.force_authenticate(self.officer)
        r = self.client.post(f"/api/alerts/{self.alert.id}/resolve/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.is_resolved)

    def test_viewer_cannot_create_worker(self):
        self.client.force_authenticate(self.viewer)
        r = self.client.post("/api/workers/", {"name": "X", "vest_id": "V-1"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_officer_can_create_worker(self):
        self.client.force_authenticate(self.officer)
        r = self.client.post("/api/workers/", {"name": "X", "vest_id": "V-1"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    # ---- configuration writes: Admin only ----

    def test_officer_cannot_create_zone(self):
        """Zones are site configuration, which the report places under Admin."""
        self.client.force_authenticate(self.officer)
        r = self.client.post("/api/v1/zones/", {"name": "New Zone"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_zone(self):
        self.client.force_authenticate(self.admin)
        r = self.client.post("/api/v1/zones/", {"name": "New Zone"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_viewer_cannot_delete_zone(self):
        self.client.force_authenticate(self.viewer)
        r = self.client.delete(f"/api/v1/zones/{self.zone.id}/")
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Zone.objects.filter(id=self.zone.id).exists())

    # ---- role is reported to the client ----

    def test_profile_exposes_role(self):
        self.client.force_authenticate(self.officer)
        r = self.client.get("/api/v1/profile/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["role"], Role.SAFETY_OFFICER.value)
        self.assertEqual(r.data["role_label"], "Safety Officer")

    def test_profile_reports_admin_for_legacy_flag(self):
        legacy = User.objects.create_user(email="old@x.io", password="pw12345678")
        legacy.is_admin = True
        legacy.save()
        self.client.force_authenticate(legacy)
        r = self.client.get("/api/v1/profile/")
        self.assertEqual(r.data["role"], Role.ADMIN.value)
