import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from workers.activity import sweep_checkouts
from workers.location import sweep_camera_exits, sweep_zone_counts
from workers.presence import sweep_stale_vests


class Command(BaseCommand):
    help = (
        "Periodically mark silent vests offline, record zone exits of workers cameras no longer see, "
        "update zone head counts and check out workers no longer seen."
    )

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=30.0, help="Seconds between sweeps")
        parser.add_argument("--once", action="store_true", help="Run a single sweep and exit")

    def handle(self, *args, interval, once, **options):
        while True:
            close_old_connections()
            changed = sweep_stale_vests()
            if changed:
                self.stdout.write(f"Marked {changed} vest(s) offline")
            exited = sweep_camera_exits()
            if exited:
                self.stdout.write(f"Recorded zone exits in {len(exited)} zone(s)")
            sweep_zone_counts()
            closed = sweep_checkouts()
            if closed:
                self.stdout.write(f"Checked out {closed} worker(s)")
            if once:
                return
            time.sleep(interval)
