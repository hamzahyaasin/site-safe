from django.core.management.base import BaseCommand, CommandError

from accounts.models import ServiceToken


class Command(BaseCommand):
    help = "Issue a device token for a camera worker or vest gateway. The key is printed once."

    def add_arguments(self, parser):
        parser.add_argument("name", help="Unique token name, e.g. CAM-01 or gateway-1")
        parser.add_argument("--kind", choices=ServiceToken.Kind.values, required=True)
        parser.add_argument(
            "--camera-id",
            action="append",
            default=[],
            dest="camera_ids",
            help="Restrict a camera token to this camera_id (repeatable).",
        )
        parser.add_argument(
            "--simulator",
            action="store_true",
            help="Mark everything sent with this token as simulated test data.",
        )

    def handle(self, *args, name, kind, camera_ids, simulator, **options):
        if ServiceToken.objects.filter(name=name).exists():
            raise CommandError(f"A token named {name!r} already exists; revoke it in admin first.")
        if camera_ids and kind != ServiceToken.Kind.CAMERA:
            raise CommandError("--camera-id only applies to CAMERA tokens.")
        _, key = ServiceToken.issue(name, kind, camera_ids, is_simulator=simulator)
        label = f"{kind} simulator" if simulator else kind
        self.stdout.write(self.style.SUCCESS(f"Created {label} token {name!r}. Store this key now:"))
        self.stdout.write(key)
