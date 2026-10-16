from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User

from .geofence import point_in_polygon
from .models import Zone

SQUARE = [
    {"lat": 0, "lng": 0},
    {"lat": 0, "lng": 1},
    {"lat": 1, "lng": 1},
    {"lat": 1, "lng": 0},
]


class GeofenceTests(APITestCase):
    def test_point_in_polygon(self):
        self.assertTrue(point_in_polygon(0.5, 0.5, SQUARE))
        self.assertFalse(point_in_polygon(1.5, 0.5, SQUARE))
        self.assertFalse(point_in_polygon(0.5, 0.5, SQUARE[:2]))

    def test_for_camera(self):
        z = Zone.objects.create(name="A", camera_ids=["CAM-01", "CAM-02"])
        Zone.objects.create(name="B", camera_ids=["CAM-03"])
        self.assertEqual(list(Zone.objects.for_camera("CAM-02")), [z])
        self.assertFalse(Zone.objects.for_camera("").exists())


class ZoneValidationTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user(email="a@x.io", password="pw12345678")
        admin.role = Role.ADMIN
        admin.save()
        self.client.force_authenticate(admin)

    def post(self, **fields):
        return self.client.post("/api/v1/zones/", {"name": "Z", **fields}, format="json")

    def test_valid_zone(self):
        r = self.post(boundaries=SQUARE, camera_ids=["CAM-01"])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

    def test_empty_boundary_allowed(self):
        self.assertEqual(self.post(boundaries=[]).status_code, status.HTTP_201_CREATED)

    def test_invalid_geometry_rejected(self):
        for boundaries in (
            SQUARE[:2],
            [{"lat": 0, "lng": 0}] * 3,
            [{"lat": 100, "lng": 0}, *SQUARE[1:]],
            [{"x": 1}, *SQUARE[1:]],
            "not a list",
        ):
            r = self.post(boundaries=boundaries)
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, boundaries)

    def test_invalid_camera_ids_rejected(self):
        for cams in (["CAM-01", "CAM-01"], [""], [5], "CAM-01"):
            r = self.post(camera_ids=cams)
            self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, cams)

    def test_negative_occupancy_rejected(self):
        self.assertEqual(self.post(max_occupancy=-1).status_code, status.HTTP_400_BAD_REQUEST)
