from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from alerts.models import Alert


class Command(BaseCommand):
    help = (
        "Delete alert snapshot images older than the retention period (FR-29). "
        "The alert, its confidence and model version are kept. Run it daily, e.g. from cron."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Keep snapshots this many days (default: ALERT_SNAPSHOT_RETENTION_DAYS).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted.")

    def handle(self, *args, days, dry_run, **options):
        days = settings.ALERT_SNAPSHOT_RETENTION_DAYS if days is None else days
        if days < 0:
            raise CommandError("--days must be zero or greater.")
        cutoff = timezone.now() - timedelta(days=days)
        expired = Alert.objects.filter(timestamp__lt=cutoff).exclude(snapshot="").exclude(snapshot__isnull=True)
        count = expired.count()
        if dry_run:
            self.stdout.write(f"{count} snapshot(s) older than {days} day(s) would be deleted.")
            return
        deleted = 0
        for alert in expired.only("pk", "snapshot").iterator():
            alert.snapshot.delete(save=False)
            deleted += 1
        # A queryset update clears the field without re-broadcasting each alert.
        expired.update(snapshot="")
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} snapshot(s) older than {days} day(s)."))
