"""Hot-work policy for fire and smoke alerts.

The server, not the camera, decides severity, from the camera's zone and
any active hot-work permit there:

* No active permit: FIRE is CRITICAL, SMOKE is HIGH.
* Active permit for the camera's zone: FIRE is MEDIUM and SMOKE is LOW. The
  alert is still stored, broadcast and linked to the permit, so supervisors
  see flame work happening under the permit.
* An unzoned camera can never be covered by a permit.

Fire is never suppressed: FIRE alerts cannot be disabled (see rules.py),
and a permit only lowers severity.
"""

from django.utils import timezone

from .models import AlertType, Severity

FIRE_TYPES = frozenset({AlertType.FIRE, AlertType.SMOKE})

UNPERMITTED = {AlertType.FIRE: Severity.CRITICAL, AlertType.SMOKE: Severity.HIGH}
PERMITTED = {AlertType.FIRE: Severity.MEDIUM, AlertType.SMOKE: Severity.LOW}


def apply(alert, zone, when=None):
    """Set severity, description and permit on an unsaved FIRE/SMOKE alert."""
    from sitemap.models import HotWorkPermit

    if alert.alert_type not in FIRE_TYPES:
        return alert
    permit = None
    if zone is not None:
        permit = HotWorkPermit.objects.filter(zone=zone).active_at(when or timezone.now()).first()
    if permit:
        alert.severity = PERMITTED[alert.alert_type]
        alert.hot_work_permit = permit
        alert.description = (
            f"{alert.description} — within hot-work permit #{permit.pk} ({permit.description}), "
            f"valid until {timezone.localtime(permit.ends_at):%H:%M %Z}"
        )
    else:
        alert.severity = UNPERMITTED[alert.alert_type]
        if zone is not None:
            alert.description = f"{alert.description} — no active hot-work permit in {zone.name}"
    return alert
