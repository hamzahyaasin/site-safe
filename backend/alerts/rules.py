"""Resolve the effective AlertConfig rule for an alert.

A zone-specific rule overrides the global rule (``zone`` null) for the same
alert type. When neither exists the built-in default applies: enabled, with
push and email notification on. SOS and FIRE can never be disabled: a panic
button or a fire must always reach the command centre (hot work is handled
by permits, which lower severity, never by switching fire alerts off).
"""

from dataclasses import dataclass

from .models import AlertConfig, AlertType

ALWAYS_ENABLED = frozenset({AlertType.SOS, AlertType.FIRE})
DEFAULT_THRESHOLD_SECONDS = 300


@dataclass(frozen=True)
class EffectiveRule:
    alert_type: str
    is_enabled: bool = True
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS
    notify_push: bool = True
    notify_email: bool = True
    config_id: int | None = None


def _from_config(cfg: AlertConfig) -> EffectiveRule:
    return EffectiveRule(
        alert_type=cfg.alert_type,
        is_enabled=cfg.is_enabled or cfg.alert_type in ALWAYS_ENABLED,
        threshold_seconds=cfg.threshold_seconds,
        notify_push=cfg.notify_push,
        notify_email=cfg.notify_email,
        config_id=cfg.pk,
    )


def rule_for(alert_type: str, zone=None) -> EffectiveRule:
    configs = AlertConfig.objects.filter(alert_type=alert_type)
    if zone is not None:
        cfg = configs.filter(zone=zone).first()
        if cfg:
            return _from_config(cfg)
    cfg = configs.filter(zone__isnull=True).first()
    if cfg:
        return _from_config(cfg)
    return EffectiveRule(alert_type=alert_type)


def zone_for_alert(alert):
    """The zone an alert belongs to: its camera's zone, else the worker's assigned zone."""
    from sitemap.models import Zone

    if alert.camera_id:
        zone = Zone.objects.for_camera(alert.camera_id).first()
        if zone:
            return zone
    if alert.worker_id and alert.worker.zone_id:
        return alert.worker.zone
    return None


def rule_for_alert(alert) -> EffectiveRule:
    return rule_for(alert.alert_type, zone_for_alert(alert))


def rules_for_camera(camera_id: str) -> dict[str, EffectiveRule]:
    from sitemap.models import Zone

    zone = Zone.objects.for_camera(camera_id).first() if camera_id else None
    return {t.value: rule_for(t.value, zone) for t in AlertType}
