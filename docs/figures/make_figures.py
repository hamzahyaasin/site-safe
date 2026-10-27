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
    "Report": ("reports", ["id", "report_type", "file_format", "date_from", "date_to", "includes_evidence", "created_by_id"]),
    # Cameras are identified by camera_id strings shared with zones and alerts, not foreign keys.
    "Camera": ("cameras", ["id", "camera_id", "people_count", "counted_at", "latitude", "longitude", "heading"]),
    "CameraArea": ("camera_areas", ["id", "camera_id", "name", "polygon", "severity", "is_active"]),
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
        ["AlertConfig", "SmartVest", "Detection", "Camera", "CameraArea"],
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
              "N:1 many-to-one, 1:1 one-to-one. Cameras are matched by camera_id.", fontsize=5.6, style="italic", color=LINE)
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


def activity_node(d, cx, cy, text, w=1.42, h=0.34, kind="server", dashed=False):
    """Rounded action box centred on (cx, cy); text may hold a line break."""
    fill, edge = COLORS[kind]
    d.ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h, boxstyle="round,pad=0.01,rounding_size=0.09", fc=fill, ec=edge, lw=0.9,
        ls=(0, (3, 2)) if dashed else "-",
    ))
    d.ax.text(cx, cy, text, ha="center", va="center", fontsize=5.7, color=INK, linespacing=1.15)
    return {"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h}


def decision(d, cx, cy, text, w=1.3, h=0.38):
    d.ax.add_patch(plt.Polygon(
        [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)], closed=True,
        fc=COLORS["client"][0], ec=COLORS["client"][1], lw=0.9,
    ))
    d.ax.text(cx, cy, text, ha="center", va="center", fontsize=5.6, color=INK)
    return {"x": cx - w / 2, "y": cy - h / 2, "w": w, "h": h}


def terminal(d, cx, cy, end=False):
    from matplotlib.patches import Circle

    if end:
        d.ax.add_patch(Circle((cx, cy), 0.085, fc="white", ec=INK, lw=0.9))
    d.ax.add_patch(Circle((cx, cy), 0.055, fc=INK, ec=INK))
    return {"x": cx - 0.085, "y": cy - 0.085, "w": 0.17, "h": 0.17}


def elbow(d, points, label="", label_at=None):
    """Polyline whose last segment ends in an arrowhead."""
    xs, ys = zip(*points)
    d.ax.plot(xs[:-1], ys[:-1], color=LINE, lw=0.8)
    d.arrow(points[-2], points[-1])
    if label:
        x, y = label_at or points[1]
        d.ax.text(x, y, label, ha="center", va="center", fontsize=5.6, color=INK,
                  bbox=dict(fc="white", ec="none", pad=0.5))


def activity_workflow():
    """Whole-system workflow, from site set-up to the compliance report."""
    apps = django_models()
    check_fields(apps.get_model("alerts", "Alert"), ["event_id", "snapshot", "model_version", "is_resolved", "hot_work_permit"])
    check_fields(apps.get_model("alerts", "AlertConfig"), ["is_enabled", "notify_push", "notify_email"])
    check_fields(apps.get_model("workers", "Worker"), ["badge_code"])
    check_fields(apps.get_model("sitemap", "Zone"), ["boundaries", "camera_ids"])
    check_fields(apps.get_model("sitemap", "HotWorkPermit"), ["starts_at", "ends_at", "revoked_at"])

    lanes = ["Admin / Safety Officer", "Camera pipeline (edge)", "Backend (Django)", "Web and mobile clients"]
    width, lane_w, top, step = 6.4, 1.6, 0.42, 0.47
    rows = 15.3
    height = top + 0.2 + step * rows
    d = Diagram(width, height)
    for i, name in enumerate(lanes):
        kind = ["external", "edge", "server", "client"][i]
        fill, edge = COLORS[kind]
        d.ax.add_patch(FancyBboxPatch((i * lane_w + 0.02, 0.02), lane_w - 0.04, 0.28, boxstyle="round,pad=0.005,rounding_size=0.04",
                                      fc=fill, ec=edge, lw=0.8))
        d.ax.text(i * lane_w + lane_w / 2, 0.16, name, ha="center", va="center", fontsize=6.4, weight="bold", color=edge)
        if i:
            d.ax.plot([i * lane_w, i * lane_w], [0.02, height - 0.2], color="#9ca3af", lw=0.6, ls=(0, (4, 2)))
    cx = [lane_w * i + lane_w / 2 for i in range(4)]

    def y(row):
        return top + 0.12 + row * step

    start = terminal(d, cx[0], y(0))
    register = activity_node(d, cx[0], y(1), "Register workers;\nprint QR badges", kind="external")
    zones = activity_node(d, cx[0], y(2), "Draw zones, assign cameras,\nset alert rules", kind="external")
    permit = activity_node(d, cx[0], y(3), "Issue hot-work permits\nfor planned flame work", kind="external")
    capture = activity_node(d, cx[1], y(4), "Capture frame\n(RTSP, HTTP or USB)", kind="edge")
    detect = activity_node(d, cx[1], y(5), "Run PPE, person/vehicle,\npose, QR and fire models", kind="edge")
    hazard = decision(d, cx[1], y(6), "Hazard confirmed?")
    evidence = activity_node(d, cx[1], y(7), "Attach badge identity,\nconfidence, model, snapshot", kind="edge")
    outbox = activity_node(d, cx[1], y(8), "Queue in outbox; POST\nwith device token", kind="edge")
    vest = activity_node(d, cx[2], y(7), "Vest telemetry: position,\nSOS (Figure 4.8)", kind="future", dashed=True)
    validate = activity_node(d, cx[2], y(8), "Authenticate device;\nvalidate payload")
    enabled = decision(d, cx[2], y(9), "Rule enabled?")
    stop = terminal(d, cx[2] + 0.98, y(9), end=True)
    severity = activity_node(d, cx[2], y(10), "Set severity; FIRE/SMOKE\nchecks hot-work permit")
    store = activity_node(d, cx[2], y(11), "Store alert once per event;\nupdate attendance")
    live = activity_node(d, cx[3], y(11), "Alert shown live;\npush and e-mail per rule", kind="client")
    review = activity_node(d, cx[3], y(12), "Officer reviews alert\nand snapshot; acts on site", kind="client")
    resolve = activity_node(d, cx[3], y(13), "Resolve alert\n(all sessions update)", kind="client")
    report = activity_node(d, cx[3], y(14), "Generate DOCX or PDF\ncompliance report", kind="client")
    end = terminal(d, cx[3], y(14.75), end=True)

    for a, b in [(start, register), (register, zones), (zones, permit), (capture, detect), (detect, hazard),
                 (evidence, outbox), (vest, validate), (validate, enabled), (severity, store),
                 (live, review), (review, resolve), (resolve, report), (report, end)]:
        d.arrow(mid(a, "b"), mid(b, "t"))
    d.arrow(mid(hazard, "b"), mid(evidence, "t"))
    d.ax.text(cx[1] + 0.1, y(6.5), "yes", fontsize=5.6, color=INK, va="center")
    d.arrow(mid(enabled, "b"), mid(severity, "t"))
    d.ax.text(cx[2] + 0.1, y(9.5), "yes", fontsize=5.6, color=INK, va="center")
    elbow(d, [mid(permit, "b"), (cx[0], y(3.55)), (cx[1], y(3.55)), mid(capture, "t")], "site running", (cx[0] + 0.55, y(3.55)))
    left = cx[1] - lane_w / 2 + 0.1
    elbow(d, [mid(hazard, "l"), (left, y(6)), (left, y(4)), mid(capture, "l")], "no", (left + 0.1, y(6) - 0.1))
    elbow(d, [mid(outbox, "r"), mid(validate, "l")])
    d.arrow(mid(enabled, "r"), mid(stop, "l"))
    d.ax.text(cx[2] + 0.79, y(9) - 0.11, "no: 202", ha="center", fontsize=5.6, color=INK)
    d.arrow(mid(store, "r"), mid(live, "l"))
    d.ax.text(cx[2] + 0.8, y(11) - 0.24, "on commit", ha="center", va="center", fontsize=5.6, color=INK)
    d.ax.text(0.06, height - 0.08, "Every hazard type follows the camera path; the vest path (dashed) enters at validation. "
              "Failed delivery leaves the event in the outbox for retry (Figure 4.9).",
              fontsize=5.6, style="italic", color=LINE, va="bottom")
    d.save("fig_activity_workflow.png")


def dfd_level0():
    """Context-level data flow diagram: one process, external entities, no stores."""
    from matplotlib.patches import Ellipse

    d = Diagram(6.4, 3.5)
    cx, cy, rx, ry = 2.75, 1.72, 0.8, 0.55
    d.ax.add_patch(Ellipse((cx, cy), 2 * rx, 2 * ry, fc=COLORS["server"][0], ec=COLORS["server"][1], lw=1.0))
    d.ax.text(cx, cy - 0.27, "0", ha="center", va="center", fontsize=7, weight="bold", color=COLORS["server"][1])
    d.ax.text(cx, cy + 0.05, "Site-Safe\nSystem", ha="center", va="center", fontsize=7.5, weight="bold",
              color=COLORS["server"][1], linespacing=1.1)

    def entity(x, y, title, sub):
        return d.box(x, y, 1.35, 0.5, title, [sub], kind="external", align="center")

    camera = entity(0.05, 0.3, "IP Camera", "site video stream")
    vest = entity(0.05, 2.75, "Smart Vest Gateway", "hardware or simulator")
    admin = entity(5.0, 0.15, "Admin", "site configuration")
    officer = entity(5.0, 1.45, "Safety Officer", "web and mobile user")
    notify = entity(5.0, 2.75, "Notification Services", "Firebase push, e-mail")

    d.arrow(mid(camera, "r"), (cx - 0.55, cy - 0.38), "video frames\n(badges in view)", label_pos=0.45, offset=(0.3, -0.05))
    d.arrow(mid(vest, "r"), (cx - 0.55, cy + 0.38), "position,\nbattery, SOS", label_pos=0.45, offset=(0.25, 0.05))
    d.arrow(mid(admin, "l", 0.3), (cx + 0.45, cy - 0.46), "workers, zones, cameras,\nalert rules", label_pos=0.35, offset=(-0.05, -0.17))
    d.arrow((cx + 0.6, cy - 0.36), mid(admin, "l", 0.8), "QR badges, reports", label_pos=0.62, offset=(0.05, 0.13))
    d.arrow(mid(officer, "l", 0.3), (cx + 0.8, cy - 0.06), "permits, resolutions,\nreport requests", label_pos=0.5, offset=(0, -0.2))
    d.arrow((cx + 0.79, cy + 0.12), mid(officer, "l", 0.75), "live alerts, snapshots,\ntimelines, reports", label_pos=0.5, offset=(0, 0.21))
    d.arrow((cx + 0.55, cy + 0.4), mid(notify, "l"), "alert notifications", label_pos=0.5, offset=(0.1, 0.12))
    d.ax.text(0.05, 3.42, "Workers are not an entity: their QR badge reaches the system through the camera, their SOS through the vest. "
              "Figure 3.4 decomposes process 0.", fontsize=5.6, style="italic", color=LINE, va="bottom")
    d.save("fig_dfd_level0.png")


def interface_figures():
    """Figures 4.3 and 4.4 from the user manual's screenshots (docs/manual/), side by side."""
    from PIL import Image

    manual = OUT.parent / "manual"

    def row(names, height, gap):
        images = [Image.open(manual / n).convert("RGB") for n in names]
        images = [im.resize((round(im.width * height / im.height), height), Image.LANCZOS) for im in images]
        canvas = Image.new("RGB", (sum(im.width for im in images) + gap * (len(images) - 1), height), "white")
        x = 0
        for im in images:
            canvas.paste(im, (x, 0))
            x += im.width + gap
        return canvas

    row(["web_area_live.jpg", "web_sitemap.jpg"], 500, 16).save(OUT / "fig_web_interface.jpg", quality=90)
    row(["mobile_alerts.jpg", "mobile_map.jpg", "mobile_camera.jpg", "mobile_alert.jpg"], 1100, 24).save(
        OUT / "fig_mobile_interface.jpg", quality=88
    )
    print("  wrote fig_web_interface.jpg, fig_mobile_interface.jpg")


if __name__ == "__main__":
    interface_figures()
    activity_workflow()
    dfd_level0()
    component_view()
    deployment_view()
    rels = erd()
    print(f"  {len(rels)} relations drawn from the models")
    camera_classes()
    sequence_camera()
    sequence_vest()
    training_pipeline()
