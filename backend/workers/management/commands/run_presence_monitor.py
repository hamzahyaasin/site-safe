import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from workers.presence import sweep_stale_vests


class Command(BaseCommand):
    help = "Periodically mark vests that stopped reporting as offline (and broadcast it)."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=30.0, help="Seconds between sweeps")
        parser.add_argument("--once", action="store_true", help="Run a single sweep and exit")

    def handle(self, *args, interval, once, **options):
        while True:
            close_old_connections()
            changed = sweep_stale_vests()
            if changed:
                self.stdout.write(f"Marked {changed} vest(s) offline")
            if once:
                return
            time.sleep(interval)
