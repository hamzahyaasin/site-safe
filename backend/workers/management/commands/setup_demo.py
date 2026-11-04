"""Set up a demo site: users, zones, workers with badges and vests, a gas monitor, device tokens, a placed camera.

Configuration only. It creates no alerts, readings or other observations:
everything a demo shows comes from the running camera pipeline and the vest
simulator, whose token marks its data as simulated. Safe to run again:
existing items are left as they are, and passwords and device keys are
printed only when they are created. docs/DEMO_SCRIPT.md walks through a demo.

The default centre matches the vest simulator's tools/vest_scenarios/demo.json
and the dashboard's default map centre.
"""

import secrets

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role, ServiceToken, User
from sitemap.models import Camera, GasMonitor, Zone
from workers.models import SmartVest, Worker

DEFAULT_CENTER = (33.6844, 73.0479)
# The restricted zone sits where demo.json walks VEST-002 to (33.6849, 73.0485).
CRANE_OFFSET = (0.0005, 0.0006)
SITE_HALF = 0.0004  # degrees, about 45 m north-south
CRANE_HALF = 0.00022

USERS = [
    ("demo-admin@sitesafe.test", "Demo Admin", Role.ADMIN),
    ("demo-officer@sitesafe.test", "Demo Safety Officer", Role.SAFETY_OFFICER),
    ("demo-viewer@sitesafe.test", "Demo Viewer", Role.VIEWER),
]
WORKERS = [
    ("Ali Raza (demo)", "Rigger", "VEST-001"),
    ("Sara Khan (demo)", "Electrician", "VEST-002"),
    ("Bilal Ahmed (demo)", "Labourer", None),
]
CAMERA_ID = "CAM-01"
CAMERA_TOKEN = "demo-cam-01"
GATEWAY_TOKEN = "demo-vest-gateway"
GAS_MONITOR_ID = "GM-01"
GAS_TOKEN = "demo-gas-monitor"
# The gas monitor sits in the Site zone, north-west of its centre.
GAS_OFFSET = (0.0002, -0.0002)


def square(lat, lng, half):
    return [
        {"lat": round(lat - half, 6), "lng": round(lng - half, 6)},
        {"lat": round(lat - half, 6), "lng": round(lng + half, 6)},
        {"lat": round(lat + half, 6), "lng": round(lng + half, 6)},
        {"lat": round(lat + half, 6), "lng": round(lng - half, 6)},
    ]


def parse_center(value):
    try:
        lat, lng = (float(v) for v in value.split(","))
    except ValueError as exc:
        raise CommandError("--center must be LAT,LNG, e.g. 33.6844,73.0479") from exc
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise CommandError("--center is outside the world.")
    return lat, lng


class Command(BaseCommand):
    help = "Create a demo site (configuration only; no alerts). Safe to run again."

    def add_arguments(self, parser):
        parser.add_argument(
            "--center",
            default=f"{DEFAULT_CENTER[0]},{DEFAULT_CENTER[1]}",
            help="Site centre as LAT,LNG (default: the vest simulator's demo scenario).",
        )

    @transaction.atomic
    def handle(self, *args, center, **options):
        lat, lng = parse_center(center)
        created = []

        for email, name, role in USERS:
            user = User.objects.filter(email=email).first()
            if user is None:
                password = secrets.token_urlsafe(12)
                user = User.objects.create_user(email=email, password=password, full_name=name)
                user.role = role
                user.save()
                created.append(f"user      {email} ({role.label})  password: {password}")
            else:
                self.stdout.write(f"kept      {email} (password unchanged)")

        site, made = Zone.objects.get_or_create(
            name="Site",
            defaults={
                "description": "Demo work area watched by CAM-01.",
                "risk_level": Zone.RiskLevel.MEDIUM,
                "boundaries": square(lat, lng, SITE_HALF),
                "camera_ids": [CAMERA_ID],
                "max_occupancy": 4,
            },
        )
        if made:
            created.append("zone      Site (medium risk, up to 4 people, camera CAM-01)")
        crane_lat, crane_lng = lat + CRANE_OFFSET[0], lng + CRANE_OFFSET[1]
        crane, made = Zone.objects.get_or_create(
            name="Crane",
            defaults={
                "description": "Demo restricted area: only assigned workers may enter.",
                "risk_level": Zone.RiskLevel.RESTRICTED,
                "boundaries": square(crane_lat, crane_lng, CRANE_HALF),
            },
        )
        if made:
            created.append("zone      Crane (restricted)")

        for name, trade, vest_id in WORKERS:
            worker, made = Worker.objects.get_or_create(name=name, defaults={"role": trade, "zone": site})
            if made:
                created.append(f"worker    {name}, badge {worker.badge_payload}")
            if vest_id and not SmartVest.objects.filter(vest_id=vest_id).exists():
                SmartVest.objects.create(vest_id=vest_id, worker=worker)
                created.append(f"vest      {vest_id} worn by {name}")

        if not GasMonitor.objects.filter(monitor_id=GAS_MONITOR_ID).exists():
            GasMonitor.objects.create(
                monitor_id=GAS_MONITOR_ID,
                name="Site store (demo)",
                zone=site,
                latitude=round(lat + GAS_OFFSET[0], 6),
                longitude=round(lng + GAS_OFFSET[1], 6),
            )
            created.append(f"monitor   {GAS_MONITOR_ID} (gas) in zone Site")

        camera, _ = Camera.objects.get_or_create(camera_id=CAMERA_ID)
        if not camera.is_placed:
            # South-west corner of the site, looking across it.
            camera.latitude, camera.longitude = lat - SITE_HALF, lng - SITE_HALF
            camera.heading, camera.field_of_view, camera.view_range_m = 45, 70, 90
            camera.save()
            created.append(f"camera    {CAMERA_ID} placed on the map at the site's south-west corner")

        if not ServiceToken.objects.filter(name=CAMERA_TOKEN).exists():
            _, key = ServiceToken.issue(CAMERA_TOKEN, ServiceToken.Kind.CAMERA, [CAMERA_ID])
            created.append(f"token     {CAMERA_TOKEN} (camera {CAMERA_ID})  key: {key}")
        if not ServiceToken.objects.filter(name=GATEWAY_TOKEN).exists():
            _, key = ServiceToken.issue(GATEWAY_TOKEN, ServiceToken.Kind.VEST_GATEWAY, is_simulator=True)
            created.append(f"token     {GATEWAY_TOKEN} (vest simulator; its data is marked simulated)  key: {key}")
        if not ServiceToken.objects.filter(name=GAS_TOKEN).exists():
            _, key = ServiceToken.issue(GAS_TOKEN, ServiceToken.Kind.GAS_MONITOR, is_simulator=True)
            created.append(f"token     {GAS_TOKEN} (gas monitor in the simulator; its data is marked simulated)  key: {key}")

        if created:
            self.stdout.write(self.style.SUCCESS("Created (passwords and keys are shown only now; store them):"))
            for line in created:
                self.stdout.write(f"  {line}")
        else:
            self.stdout.write("The demo site already exists; nothing created.")
        self.stdout.write(
            "Next: docs/DEMO_SCRIPT.md (print badges from the Workers page; start the camera with the "
            f"{CAMERA_TOKEN} key as {CAMERA_ID}; run the vest simulator with the {GATEWAY_TOKEN} and "
            f"{GAS_TOKEN} keys)."
        )
