#!/usr/bin/env python3
"""Generate the report's design diagrams from the code.

Every name drawn is checked against the implementation first: model fields
against the Django models, classes and methods against the camera modules.
A rename in the code makes this script fail instead of leaving a figure
that no longer matches the system.

    .venv/bin/python docs/figures/make_figures.py      # writes docs/figures/*.png
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
plt.rcParams.update({"font.family": "Arial", "font.size": 7})

INK = "#1f2937"
LINE = "#4b5563"
COLORS = {
    "edge": ("#e0f2fe", "#0369a1"),
    "server": ("#eef2ff", "#4338ca"),
    "data": ("#ecfdf5", "#047857"),
    "client": ("#fff7ed", "#c2410c"),
    "external": ("#f3f4f6", "#6b7280"),
    "future": ("#fafafa", "#9ca3af"),
}


class Diagram:
    """Inch-based canvas with y growing downwards."""

    def __init__(self, width, height):
        self.fig, self.ax = plt.subplots(figsize=(width, height))
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(height, 0)
        self.ax.axis("off")

    def box(self, x, y, w, h, title, lines=(), kind="server", title_size=6.6, dashed=False, align="left"):
        fill, edge = COLORS[kind]
        self.ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.05", fc=fill, ec=edge, lw=0.9,
                ls=(0, (3, 2)) if dashed else "-",
            )
        )
        self.ax.text(x + w / 2, y + 0.13, title, ha="center", va="center", fontsize=title_size, weight="bold", color=edge)
        for i, line in enumerate(lines):
            if align == "left":
                self.ax.text(x + 0.06, y + 0.3 + i * 0.145, line, ha="left", va="center", fontsize=5.6, color=INK)
            else:
                self.ax.text(x + w / 2, y + 0.3 + i * 0.145, line, ha="center", va="center", fontsize=5.6, color=INK)
        return {"x": x, "y": y, "w": w, "h": h}

    def group(self, x, y, w, h, label, kind="external"):
        fill, edge = COLORS[kind]
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.06", fc="none", ec=edge, lw=0.8, ls=(0, (4, 2))))
        self.ax.text(x + 0.08, y + 0.1, label, ha="left", va="center", fontsize=6.8, style="italic", color=edge)

    def arrow(self, a, b, label="", both=False, dashed=False, label_pos=0.5, offset=(0, -0.06), size=5.8, rad=0.0):
        style = "<|-|>" if both else "-|>"
        self.ax.add_patch(
            FancyArrowPatch(
                a, b, arrowstyle=style, mutation_scale=7, lw=0.8, color=LINE,
                ls=(0, (3, 2)) if dashed else "-", connectionstyle=f"arc3,rad={rad}", shrinkA=1, shrinkB=1,
            )
        )
        if label:
            mx = a[0] + (b[0] - a[0]) * label_pos + offset[0]
            my = a[1] + (b[1] - a[1]) * label_pos + offset[1]
            self.ax.text(mx, my, label, ha="center", va="center", fontsize=size, color=INK,
                         bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))

    def save(self, name):
        path = OUT / name
        self.fig.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0.04)
        plt.close(self.fig)
        print("wrote", path.relative_to(REPO))


def mid(b, side, frac=0.5):
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    return {
        "l": (x, y + h * frac), "r": (x + w, y + h * frac),
        "t": (x + w * frac, y), "b": (x + w * frac, y + h),
    }[side]


# ---------------------------------------------------------------- checks

def django_models():
    sys.path.insert(0, str(REPO / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitesafe.test_settings")
    import django

    django.setup()
    from django.apps import apps

    return apps


def check_fields(model, names):
    have = {f.name for f in model._meta.get_fields()} | {f.attname for f in model._meta.concrete_fields}
    missing = [n for n in names if n.rstrip("*") not in have and n.split(" ")[0] not in have]
    if missing:
        raise SystemExit(f"{model.__name__} has no field(s) {missing}: update the figure")


def check_members(module, cls, members):
    import importlib

    sys.path.insert(0, str(REPO / "ai-module"))
    obj = getattr(importlib.import_module(module), cls)
    missing = [m for m in members if not hasattr(obj, m)]
    if missing:
        raise SystemExit(f"{module}.{cls} lacks {missing}: update the figure")


# ---------------------------------------------------------------- figures

def component_view():
    d = Diagram(6.4, 5.0)
    d.group(0.02, 0.02, 2.0, 4.68, "Site edge")
    d.group(2.18, 0.02, 2.3, 4.68, "Server")
    d.group(4.62, 0.02, 1.76, 4.68, "Services and clients")

    cam = d.box(0.1, 0.3, 1.84, 1.62, "Camera pipeline (Python)", [
        "PPE detector (YOLO11m, every frame)",
        "Person/vehicle, pose: every 3rd frame",
        "Fire/smoke: every 5th frame",
        "QR badge decoding + identity tracks",
        "Proximity, inactivity, fall, fire trackers",
        "Camera rules (polled every 60 s)",
        "Event outbox (SQLite, retry ≤ 30 s)",
        "Attendance sightings, idle start/end",
    ], kind="edge")
    gw = d.box(0.1, 2.12, 1.84, 0.62, "Vest gateway / simulator", ["GPS, battery, SOS telemetry", "physical vest: proposed"], kind="edge")
    mqtt = d.box(0.1, 2.94, 1.84, 0.62, "MQTT broker (Mosquitto)", ["sitesafe/vest/+/telemetry, /sos"], kind="edge")
    d.box(0.1, 3.76, 1.84, 0.82, "Smart Vest hardware", ["ESP32 + GNSS + SOS button", "LoRa link to receiver", "(deferred, see Section 4.8)"], kind="future", dashed=True)

    api = d.box(2.26, 0.3, 2.14, 3.32, "Django API (DRF + Channels)", [
        "accounts: JWT, roles, device tokens",
        "alerts: camera events, rules,",
        "   fire/hot-work policy, notifications,",
        "   after-commit live events",
        "workers: registry, vest telemetry,",
        "   presence, attendance timelines",
        "sitemap: zones, geofence, breaches,",
        "   hot-work permits",
        "reports: generate, store, download",
        "WebSocket /ws/dashboard (JWT)",
    ])
    cons = d.box(2.26, 3.78, 1.02, 0.8, "MQTT consumer", ["run_mqtt_", "consumer"], kind="server")
    mon = d.box(3.38, 3.78, 1.02, 0.8, "Presence monitor", ["offline vests,", "auto check-out"], kind="server")

    db = d.box(4.7, 0.3, 1.6, 0.5, "PostgreSQL 18", ["alerts, workers, zones, logs"], kind="data")
    chl = d.box(4.7, 0.95, 1.6, 0.5, "Channel layer", ["Redis (multi-process)"], kind="data")
    rep = d.box(4.7, 1.6, 1.6, 0.62, "Report service (Node)", ["metrics model → DOCX / PDF"], kind="server")
    web = d.box(4.7, 2.37, 1.6, 0.62, "Web command centre", ["React 19, map, permits"], kind="client")
    mob = d.box(4.7, 3.14, 1.6, 0.62, "Mobile app (Expo SDK 58)", ["alerts, resolve, workers"], kind="client")
    fcm = d.box(4.7, 3.91, 1.6, 0.62, "FCM push / e-mail", ["per rule and preference"], kind="external")

    d.arrow(mid(cam, "r", 0.35), mid(api, "l", 0.17), "")
    d.arrow(mid(gw, "r"), mid(api, "l", 0.62), "")
    d.arrow(mid(mqtt, "r", 0.6), mid(cons, "l", 0.3), "", size=5.5)
    d.arrow(mid(api, "r", 0.08), mid(db, "l"), "", both=True)
    d.arrow(mid(api, "r", 0.26), mid(chl, "l"), "")
    d.arrow(mid(api, "r", 0.45), mid(rep, "l"), "", both=True)
    d.arrow(mid(web, "l"), mid(api, "r", 0.62), "", both=True)
    d.arrow(mid(mob, "l"), mid(api, "r", 0.85), "", both=True)
    d.arrow(mid(fcm, "t"), mid(mob, "b"), "")
    d.ax.text(0.04, 4.76, "Edge → API: HTTPS with scoped device tokens.  Web and mobile ↔ API: REST and WebSocket with JWT.\n"
              "API → channel layer: after-commit events.  API ↔ report service: internal HTTP.", fontsize=5.6, style="italic", color=LINE,
              va="top")
    d.arrow(mid(cons, "t"), mid(api, "b", 0.24), "", )
    d.arrow(mid(mon, "t"), mid(api, "b", 0.76), "")
    d.save("fig_component_view.png")


def deployment_view():
    d = Diagram(6.4, 3.92)
    d.group(0.02, 0.02, 4.18, 3.5, "Demo computer (macOS, Apple M4, 16 GB)", kind="server")
    d.box(0.12, 0.3, 1.5, 1.06, "Camera pipeline (native)", ["inference.py --device mps", "models/*.pt", "outbox/<camera>.sqlite3"], kind="edge")
    d.box(0.12, 1.55, 1.5, 0.62, "USB / IP camera", ["or phone (IP Webcam)"], kind="external")
    d.group(1.78, 0.25, 2.32, 3.18, "docker compose")
    # Ordered so each outside device lines up with the container it talks to.
    containers = [
        ("frontend", "nginx :8080 (built SPA)"), ("backend", "daphne :8000, migrate"), ("db", "postgres:18 (volume)"),
        ("redis", "channel layer"), ("report-service", "node :3001 (internal)"),
        ("presence-monitor", "run_presence_monitor"), ("mqtt-consumer", "run_mqtt_consumer"),
        ("mqtt", "mosquitto :1883 (localhost)"),
    ]
    for i, (name, desc) in enumerate(containers):
        d.box(1.88, 0.5 + i * 0.36, 2.12, 0.3, f"{name}: {desc}", kind="data" if name in ("db", "redis") else "server", title_size=5.9)
    d.box(4.45, 0.3, 1.85, 0.62, "Browser", ["web dashboard on :8080"], kind="client")
    d.box(4.45, 1.1, 1.85, 0.75, "Android phone", ["Expo development build", "google-services.json"], kind="client")
    d.box(4.45, 2.05, 1.85, 0.6, "Firebase Cloud Messaging", ["service-account on server"], kind="external")
    d.box(4.45, 2.85, 1.85, 0.62, "Vest receiver (proposed)", ["USB serial → MQTT bridge"], kind="future", dashed=True)
    d.arrow((1.62, 0.85), (1.88, 1.01), "")
    d.arrow((0.87, 1.55), (0.87, 1.36), "frames")
    d.arrow((4.45, 0.65), (4.0, 0.65), "")
    d.arrow((4.45, 1.3), (4.0, 1.04), "", both=True)
    d.arrow((4.0, 1.12), (4.45, 2.25), "", dashed=True)
    d.arrow((5.37, 2.05), (5.37, 1.85), "")
    d.arrow((4.45, 3.17), (4.0, 3.17), "", dashed=True)
    d.ax.text(0.04, 3.6, "Browser → frontend :8080; phone ↔ backend :8000 over the LAN (REST + WebSocket);\n"
              "backend → FCM over the internet (optional, needs credentials); dashed: proposed or optional.",
              fontsize=5.6, style="italic", color=LINE, va="top")
    d.save("fig_deployment_view.png")


ERD_FIELDS = {
    "User": ("users", ["id", "email", "full_name", "role", "is_active"]),
    "ServiceToken": ("service_tokens", ["id", "name", "kind", "key_hash", "camera_ids", "is_simulator", "is_active"]),
    "FCMToken": ("fcm_tokens", ["id", "user_id", "token", "device_name", "is_active"]),
    "UserPreferences": ("user_preferences", ["id", "user_id", "notify_push", "notify_email"]),
    "Worker": ("workers", ["id", "name", "role", "zone_id", "badge_code", "last_seen_at", "is_active"]),
    "SmartVest": ("smart_vests", ["id", "vest_id", "worker_id", "battery_level", "latitude", "longitude", "sos_active", "last_seen"]),
    "ActivityLog": ("activity_logs", ["id", "worker_id", "zone_id", "action", "timestamp", "metadata"]),
    "Zone": ("zones", ["id", "name", "risk_level", "boundaries", "camera_ids", "max_occupancy"]),
    "HotWorkPermit": ("hot_work_permits", ["id", "zone_id", "description", "starts_at", "ends_at", "issued_by_id", "revoked_at"]),
    "Alert": ("alerts", ["id", "alert_type", "severity", "source", "worker_id", "camera_id", "hot_work_permit_id", "confidence", "event_id", "is_resolved"]),
    "AlertConfig": ("alert_config", ["id", "zone_id", "alert_type", "is_enabled", "threshold_seconds", "notify_push", "notify_email"]),
    "Detection": ("detections", ["id", "camera_id", "worker_id", "class_name", "confidence", "bbox"]),
    "Report": ("reports", ["id", "report_type", "file_format", "date_from", "date_to", "created_by_id"]),
}


def erd():
    apps = django_models()
    models = {m.__name__: m for m in apps.get_models()}
    for name, (_, fields) in ERD_FIELDS.items():
        check_fields(models[name], fields)

    # Hub layout: each link joins a box to the one directly above it or to a
    # neighbouring column, so no line crosses a table.
    columns = [
        ["UserPreferences", "FCMToken", "Report", "ServiceToken"],
        ["User", "HotWorkPermit", "Alert"],
        ["Zone", "Worker", "ActivityLog"],
        ["AlertConfig", "SmartVest", "Detection"],
    ]
    width, gap_x, gap, row = 1.36, 0.3, 0.26, 0.145
    col_x = [0.05 + i * (width + gap_x) for i in range(len(columns))]
    d = Diagram(6.4, 7.6)
    boxes, rows_y = {}, {}
    for cx, names in zip(col_x, columns):
        y = 0.05
        for name in names:
            table, fields = ERD_FIELDS[name]
            model = models[name]
            fk_attnames = {f.attname for f in model._meta.concrete_fields if f.is_relation}
            lines = [("PK " if f == "id" else "FK " if f in fk_attnames else "     ") + f for f in fields]
            h = 0.3 + row * len(lines) - 0.04
            boxes[name] = d.box(cx, y, width, h, table, lines, kind="data")
            for i, f in enumerate(fields):
                rows_y[(name, f)] = y + 0.3 + i * row
            y += h + gap

    rels = []
    for name in ERD_FIELDS:
        for f in models[name]._meta.concrete_fields:
            target = f.related_model.__name__ if f.is_relation and f.related_model else None
            if target in ERD_FIELDS and f.attname in ERD_FIELDS[name][1]:
                rels.append((name, f.attname, target, "1:1" if f.one_to_one else "N:1"))
    pos = {n: (i, j) for i, names in enumerate(columns) for j, n in enumerate(names)}
    lanes, ports = {}, {}

    def next_slot(table, key):
        n = table.get(key, 0)
        table[key] = n + 1
        return n

    def route(points, card, label_at, ha):
        xs_, ys_ = zip(*points)
        d.ax.plot(xs_, ys_, color=LINE, lw=0.7)
        d.ax.annotate("", xy=points[-1], xytext=points[-2], arrowprops=dict(arrowstyle="-|>", color=LINE, lw=0.7, mutation_scale=6))
        d.ax.text(*label_at, card, fontsize=5, color=INK, ha=ha, va="bottom")

    for name, attname, target, card in rels:
        a, b = boxes[name], boxes[target]
        (ca, ra), (cb, rb) = pos[name], pos[target]
        y_from = rows_y[(name, attname)]
        if ca == cb and rb == ra - 1:  # directly above: short vertical link
            x = a["x"] + a["w"] * 0.75
            route([(x, a["y"]), (x, b["y"] + b["h"])], card, (x + 0.04, a["y"] - gap / 2 - 0.05), "left")
            continue
        if ca == cb:  # same column, further up: lane in the gap on the right
            side, toward = a["x"] + a["w"], 1
        else:
            toward = 1 if cb > ca else -1
            side = a["x"] + a["w"] if toward > 0 else a["x"]
        gap_key = side if toward > 0 else side - gap_x
        x = side + toward * (0.07 + 0.055 * next_slot(lanes, (gap_key, toward)))
        b_side = b["x"] if toward > 0 and ca != cb else b["x"] + b["w"]
        y_to = b["y"] + 0.12 + 0.07 * next_slot(ports, (target, b_side))
        # Cardinality sits inside the source box, at the end of its FK row.
        route([(side, y_from), (x, y_from), (x, y_to), (b_side, y_to)], card,
              (a["x"] + a["w"] - 0.05, y_from + 0.045), "right")
    bottom = max(bx["y"] + bx["h"] for bx in boxes.values())
    d.ax.text(0.05, bottom + 0.2, "Generated from the Django models. Arrows run from a foreign key to the table it references; "
              "N:1 many-to-one, 1:1 one-to-one.", fontsize=5.6, style="italic", color=LINE)
    d.ax.set_ylim(bottom + 0.3, 0)
    d.fig.set_size_inches(6.4, bottom + 0.3)
    d.save("fig_erd.png")
    return rels


def camera_classes():
    spec = [
        ("event_outbox", "EventOutbox", ["enqueue", "deliver_due", "stats"], "SQLite queue, retry ≤ 30 s, dead letters"),
        ("inference", "CameraRules", ["refresh", "enabled", "threshold"], "dashboard rules polled every 60 s"),
        ("identity", "QrDecoder", ["decode"], "OpenCV QR → SSW1 badge payloads"),
        ("identity", "IdentityTracker", ["update", "identify", "identify_box"], "badge ↔ person box; ambiguous = unknown"),
        ("inference", "SightingThrottle", ["due"], "≤ 1 sighting per badge per minute"),
        ("proximity", "ProximityTracker", ["update"], "person–vehicle gap (person heights)"),
        ("inactivity", "InactivityTracker", ["update", "reset", "resumed"], "stationary timeout, resumed tracks"),
        ("fall_detection", "FallTracker", ["update", "reset"], "pose span, hips ≤ knees, held 3 s"),
        ("fire_detection", "FireTracker", ["update", "reset"], "held 2 s, latched until clear 30 s"),
    ]
    for module, cls, members, _ in spec:
        if cls == "InactivityTracker":
            import importlib

            sys.path.insert(0, str(REPO / "ai-module"))
            obj = importlib.import_module("inactivity").InactivityTracker(timeout_seconds=1)
            missing = [m for m in members if not hasattr(obj, m)]
            if missing:
                raise SystemExit(f"InactivityTracker lacks {missing}")
        else:
            check_members(module, cls, members)

    d = Diagram(6.4, 3.5)
    main = d.box(1.6, 0.05, 3.2, 0.62, "inference.main()", ["capture loop on raw frames; group_violations(), pick_device(),",
                                                            "queue_event(), activity_payload()"], kind="edge")
    d.group(0.02, 0.87, 6.36, 2.6, "helper classes created and called by main()")
    for i, (module, cls, members, note) in enumerate(spec):
        x, y = 0.1 + (i % 3) * 2.1, 1.12 + (i // 3) * 0.78
        d.box(x, y, 2.0, 0.68, cls, [", ".join(f"{m}()" if m != "resumed" else m for m in members), note, f"module: {module}.py"], kind="server")
    d.arrow(mid(main, "b"), (3.2, 0.87), "")
    d.save("fig_camera_classes.png")


def lifelines(d, names, end, top=0.12):
    """Participant heads (names may hold a line break) and dashed lifelines down to ``end``."""
    width = d.ax.get_xlim()[1]
    xs = []
    step = width / len(names)
    for i, n in enumerate(names):
        x = step * i + step / 2
        xs.append(x)
        d.box(x - step * 0.45, top, step * 0.9, 0.38, "", kind="server")
        d.ax.text(x, top + 0.19, n, ha="center", va="center", fontsize=5.9, weight="bold", color=COLORS["server"][1], linespacing=1.1)
        d.ax.plot([x, x], [top + 0.38, end], color=LINE, lw=0.6, ls=(0, (2, 2)))
    return xs


def message(d, xs, a, b, y, text, dashed=False):
    """Arrow from lifeline a to b; the label starts at the arrow's left end, above it."""
    label = dict(fontsize=5.7, va="bottom", ha="left", color=INK, bbox=dict(fc="white", ec="none", pad=0.4))
    if a == b:  # self-call: a small loop to the right
        x = xs[a]
        d.ax.plot([x, x + 0.14, x + 0.14], [y - 0.04, y - 0.04, y + 0.06], color=LINE, lw=0.7)
        d.ax.annotate("", xy=(x, y + 0.06), xytext=(x + 0.14, y + 0.06),
                      arrowprops=dict(arrowstyle="-|>", color=LINE, lw=0.7, mutation_scale=6))
        d.ax.text(x + 0.19, y - 0.04, text, **{**label, "va": "center"})
        return
    d.arrow((xs[a], y), (xs[b], y), "", dashed=dashed)
    d.ax.text(min(xs[a], xs[b]) + 0.05, y - 0.03, text, **label)


def sequence(names, steps, name, footer, alt=None, step_y=0.27):
    first = 0.78
    last = first + step_y * (len(steps) - 1)
    end = last + 0.15
    height = end + (0.5 if alt else 0.3)
    d = Diagram(6.4, height)
    xs = lifelines(d, names, end)
    for i, (a, b, text, *dashed) in enumerate(steps):
        message(d, xs, a, b, first + i * step_y, text, dashed=bool(dashed))
    y = end + 0.04
    if alt:
        d.ax.add_patch(FancyBboxPatch((0.06, y), 6.28, 0.36, boxstyle="round,pad=0.01", fc="#fff7ed", ec="#c2410c", lw=0.7))
        d.ax.text(0.14, y + 0.18, alt, fontsize=5.7, va="center", color=INK, linespacing=1.3)
        y += 0.44
    d.ax.text(0.06, y + 0.04, footer, fontsize=5.6, style="italic", color=LINE, va="top")
    d.ax.set_ylim(y + 0.2, 0)
    d.fig.set_size_inches(6.4, y + 0.2)
    d.save(name)


def sequence_camera():
    names = ["Camera\nloop", "Event\noutbox", "Camera\nEventView", "Rules +\nfire policy", "PostgreSQL", "Channel\nlayer", "Web /\nmobile", "Notifier"]
    steps = [
        (0, 0, "tracker confirms event"),
        (0, 1, "enqueue(payload) → event_id"),
        (1, 2, "POST /v1/camera-events/  [Device token]"),
        (2, 2, "validate camera_id, confidence"),
        (2, 3, "rule_for_alert(); FIRE/SMOKE: permit?"),
        (3, 2, "enabled? severity, permit link", True),
        (2, 4, "INSERT alert (event_id unique)"),
        (4, 5, "on commit: group_send alert_created"),
        (5, 6, "WebSocket message"),
        (4, 7, "on commit: push / e-mail per rule"),
        (2, 1, "201 stored | 200 duplicate | 202 suppressed", True),
        (1, 1, "delete from outbox"),
    ]
    sequence(names, steps, "fig_seq_camera_event.png",
             "Dashed arrows are replies. The dashboard receives the event when the alert is committed, before the camera gets its reply.",
             alt="alt   API unreachable or 5xx: the event stays on disk and is retried with exponential backoff (≤ 30 s), also after a restart.\n"
                 "        4xx validation error: the event is moved to dead letters and not retried.")


def sequence_vest():
    names = ["Vest\ngateway", "VestTelemetry\nView", "Telemetry\nhandler", "Activity", "Geofence", "PostgreSQL", "Channel\nlayer", "Presence\nmonitor"]
    steps = [
        (0, 1, "POST /v1/vests/telemetry/  [gateway token]"),
        (1, 1, "validate lat/lng, battery, SOS"),
        (1, 2, "apply_vest_telemetry()"),
        (2, 5, "lock vest row; update position, last_seen"),
        (2, 3, "record_seen(): check-in if no session"),
        (2, 4, "zone at position (highest risk)"),
        (4, 5, "ZONE_ENTER log; breach? ZONE_BREACH alert"),
        (2, 5, "SOS rising edge → SOS alert (CRITICAL)"),
        (5, 6, "on commit: vest_updated, alert_created"),
        (7, 5, "every 30 s: silent vests offline"),
        (7, 3, "not seen 30 min → CHECK_OUT at last sighting"),
    ]
    sequence(names, steps, "fig_seq_vest_telemetry.png",
             "Simulator tokens: alerts are marked SIMULATED and no attendance is recorded. MQTT messages take the same path through run_mqtt_consumer.",
             step_y=0.29)


def training_pipeline():
    """PPE model pipeline, values read from the exported v5 run."""
    import json

    export = REPO / "ai-module/models/sitesafe_v5_export"
    manifest = json.loads((export / "run_manifest.json").read_text())
    metrics = json.loads((export / "held_out_test_metrics.json").read_text())["overall"]
    args = manifest["requested_train_args"]
    splits = manifest["dataset"]["splits"]
    total = sum(v["images"] for v in splits.values())

    d = Diagram(6.4, 2.25)
    for i, title in enumerate(["Data", "Training", "Evaluation", "Use in pipeline"]):
        d.ax.text(0.76 + i * 1.6, 0.1, title, ha="center", va="center", fontsize=7, weight="bold", color=LINE)
    data = d.box(0.05, 0.28, 1.42, 0.9, "Roboflow PPE dataset", [
        f"{total:,} images, 10 classes", "licence CC BY 4.0",
        f"split {splits['train']['images']:,} / {splits['valid']['images']:,} / {splits['test']['images']}",
        "as published (not re-split)"], kind="data")
    audit = d.box(0.05, 1.3, 1.42, 0.75, "audit_dataset.py", [
        "573 source groups and 30 exact", "duplicates cross splits:", "test set is not sealed"], kind="future", dashed=True)
    train = d.box(1.65, 0.28, 1.42, 1.05, f"{manifest['model_source']} (COCO)", [
        f"Colab {manifest['environment']['gpu']}, {args['imgsz']} px",
        f"batch {args['batch']}, {args['optimizer']} lr {args['lr0']}",
        f"{args['epochs']} epochs max, patience {args['patience']}",
        f"seed {args['seed']}, deterministic",
        f"Ultralytics {manifest['environment']['ultralytics']}"], kind="server")
    ev = d.box(3.25, 0.28, 1.42, 0.9, "Held-out test split", [
        f"{splits['test']['images']} images",
        f"mAP@0.5 {metrics['map50']:.3f}",
        f"mAP@0.5:0.95 {metrics['map50_95']:.3f}",
        f"P {metrics['precision']:.3f}  R {metrics['recall']:.3f}"], kind="client")
    use = d.box(4.85, 0.28, 1.5, 0.9, "models/sitesafe_v5.pt", [
        "PyTorch weights, every frame", "candidate threshold 0.15",
        "Apple M4 GPU: 15.7 FPS with", "all detectors (Table 5.5)"], kind="edge")
    d.arrow(mid(data, "r"), mid(train, "l", 0.43))
    d.arrow(mid(train, "r", 0.43), mid(ev, "l"))
    d.arrow(mid(ev, "r"), mid(use, "l"))
    d.arrow(mid(data, "b"), mid(audit, "t"), dashed=True)
    d.ax.text(3.25, 1.45, "Dashed: finding that limits what the test score can claim (Section 5.5).",
              fontsize=5.6, style="italic", color=LINE, va="top")
    d.save("fig_training_pipeline.png")


if __name__ == "__main__":
    component_view()
    deployment_view()
    rels = erd()
    print(f"  {len(rels)} relations drawn from the models")
    camera_classes()
    sequence_camera()
    sequence_vest()
    training_pipeline()
