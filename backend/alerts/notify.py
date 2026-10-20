"""Push and email notification for new alerts.

Delivery is decided by the effective AlertConfig rule (``notify_push`` /
``notify_email``) and then by each user's own preferences. It runs on a
small background pool after the alert commits, so a slow or failing provider
never delays or rolls back incident storage.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.mail import send_mail
from django.db import close_old_connections, transaction

logger = logging.getLogger(__name__)

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sitesafe-notify")

# Tests set this to True so delivery runs inline and can be asserted.
RUN_INLINE = False


def recipients(channel):
    """Active users who have not switched this notification channel off."""
    from accounts.models import User

    users = User.objects.filter(is_active=True).select_related("preferences")
    out = []
    for user in users:
        prefs = getattr(user, "preferences", None)
        if prefs is None or getattr(prefs, f"notify_{channel}"):
            out.append(user)
    return out


def _message(alert):
    title = f"Site-Safe: {alert.get_alert_type_display()} ({alert.get_severity_display()})"
    where = []
    if alert.worker_id:
        where.append(f"worker {alert.worker.name}")
    if alert.camera_id:
        where.append(f"camera {alert.camera_id}")
    body = alert.description or alert.get_severity_display()
    if where:
        body = f"{body} — {', '.join(where)}"
    return title, body


def deliver(alert_id):
    from sitesafe.notifications import send_push_notification

    from .models import Alert
    from .rules import rule_for_alert

    # Pool threads get their own DB connection; drop it if stale. Inline
    # delivery (tests) runs on the caller's connection, which must be kept.
    if not RUN_INLINE:
        close_old_connections()
    try:
        alert = Alert.objects.select_related("worker").filter(pk=alert_id).first()
        if alert is None:
            return {"push": 0, "email": 0}
        rule = rule_for_alert(alert)
        title, body = _message(alert)
        sent = {"push": 0, "email": 0}

        if rule.notify_push:
            users = recipients("push")
            if users:
                try:
                    send_push_notification(
                        [u.id for u in users],
                        title,
                        body,
                        {"alert_id": alert.id, "alert_type": alert.alert_type, "severity": alert.severity},
                    )
                    sent["push"] = len(users)
                except Exception:  # noqa: BLE001
                    logger.exception("Push delivery failed for alert %s", alert_id)

        if rule.notify_email:
            emails = [u.email for u in recipients("email") if u.email]
            if emails:
                try:
                    send_mail(title, body, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=False)
                    sent["email"] = len(emails)
                except Exception:  # noqa: BLE001
                    logger.exception("Email delivery failed for alert %s", alert_id)
        return sent
    finally:
        if not RUN_INLINE:
            close_old_connections()


def schedule(alert):
    alert_id = alert.pk

    def run():
        if RUN_INLINE:
            deliver(alert_id)
        else:
            _pool.submit(deliver, alert_id)

    transaction.on_commit(run)
