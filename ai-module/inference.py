#!/usr/bin/env python3
"""
Site-Safe vision pipeline: PPE, vehicle-proximity, inactivity, and fall
warnings, with optional Django alert API integration.
Run from ai-module/: python inference.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
from pathlib import Path
from typing import Any

import threading

import cv2
import numpy as np
import requests
from ultralytics import YOLO

import danger_areas
import evidence
import fall_detection
import fire_detection
import identity
from event_outbox import EventOutbox
import inactivity
import live_feed
from latest_sender import LatestSender
import ppe_episodes
import proximity

# ============== CONFIG ==============
MODEL_PATH = "models/sitesafe_v5.pt"
# The PPE model is trained only on equipment classes and has no person or
# vehicle class, so proximity and inactivity warnings need a second detector.
# The COCO-pretrained YOLOv11 nano weights supply person and vehicle boxes.
PROXIMITY_MODEL_PATH = "yolo11n.pt"
# Fall detection needs body keypoints, which a plain detection model does not
# emit, so it uses a third, independent model: the COCO-pretrained YOLO11
# nano *pose* weights.
FALL_MODEL_PATH = "yolo11n-pose.pt"
# Fire/smoke is a separate detector trained with fire/train_fire_smoke_colab.ipynb.
# Without these weights the rest of the pipeline runs and fire is disabled.
FIRE_MODEL_PATH = "models/fire_smoke.pt"
# Fire grows over seconds, so sampling every fifth frame keeps its cost low
# without delaying confirmation meaningfully.
FIRE_FRAME_INTERVAL = 5
API_BASE = os.environ.get("SITESAFE_API_BASE", "http://127.0.0.1:8000/api")
# Camera device token issued with
#   python manage.py create_service_token CAM-01 --kind CAMERA --camera-id CAM-01
# It can only post camera events and read this camera's rules; it is never a
# human login. Without it the pipeline still runs and queues events locally.
DEVICE_KEY_ENV = "SITESAFE_DEVICE_KEY"
OUTBOX_DIR = os.environ.get("SITESAFE_OUTBOX_DIR", "outbox")
# Alert evidence (FR-29): a downscaled JPEG of the confirming frame is sent
# with each AI alert. Set SITESAFE_SNAPSHOTS=0 (or pass --no-snapshots) where
# site policy does not allow images of workers to leave the camera host.
SNAPSHOTS_ENV = "SITESAFE_SNAPSHOTS"
# Live view (Cameras page): the annotated frame is sent to the API a few times
# a second for Safety Officers and Admins to watch. Never stored server-side.
# Set SITESAFE_LIVE=0 (or pass --no-live) to keep video on the camera host.
LIVE_ENV = "SITESAFE_LIVE"
# Rules and danger areas saved in the dashboard reach the camera within this long.
RULES_REFRESH_SECONDS = 15
# Temporary global PPE candidate threshold.  It is exposed through the CLI so
# Phase 4 can calibrate it without editing source; the clean validation work
# will replace this with per-class thresholds.
PPE_CONF = 0.15
# Source can be a local webcam index (0, 1, ...) or a network stream URL
# (RTSP/HTTP, e.g. a phone running "IP Webcam", or an existing NVR/IP camera).
DEFAULT_CAMERA_SOURCE = os.environ.get("SITESAFE_CAMERA_SOURCE", "0")
DEFAULT_CAMERA_ID = os.environ.get("SITESAFE_CAMERA_ID", "CAM-01")
# A dropped frame is expected on a flaky WiFi network stream; only give up
# after this many *consecutive* failed reads.
MAX_CONSECUTIVE_READ_FAILURES = 30
READ_RETRY_DELAY_SECONDS = 0.25
# Running a second model on every frame roughly halves throughput, so the
# COCO person/vehicle detector is sampled instead. Vehicles and people move
# slowly relative to frame rate, so every third frame loses little temporal
# resolution for these alert types.
PROXIMITY_FRAME_INTERVAL = 3
PROXIMITY_CONF = 0.35
# The pose model is a separate forward pass from the COCO detector above, so
# it has its own sampling interval. Every third frame matches the original
# design's stated cadence and comfortably out-samples the multi-second
# persistence window fall detection requires.
FALL_FRAME_INTERVAL = 3
FALL_CONF = 0.35
# ====================================


def module_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_model_path() -> Path:
    p = Path(MODEL_PATH)
    if p.is_absolute():
        return p
    return module_root() / p


def resolve_proximity_model_path() -> Path:
    p = Path(PROXIMITY_MODEL_PATH)
    if p.is_absolute():
        return p
    return module_root() / p


def resolve_fire_model_path() -> Path:
    p = Path(FIRE_MODEL_PATH)
    return p if p.is_absolute() else module_root() / p


def fire_detections(names, boxes_xyxy, confs, clss) -> list[tuple[str, float, tuple]]:
    return [
        (class_name(names, int(clss[i])), float(confs[i]), tuple(float(v) for v in boxes_xyxy[i].tolist()))
        for i in range(len(clss))
    ]


def draw_fire(frame: np.ndarray, detections: list[tuple[str, float, tuple]]) -> None:
    for name, conf, box in detections:
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 128, 255), 2)
        cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(y1 - 6, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 128, 255), 1, cv2.LINE_AA)


def resolve_fall_model_path() -> Path:
    p = Path(FALL_MODEL_PATH)
    if p.is_absolute():
        return p
    return module_root() / p


def pick_device(requested: str) -> str:
    """'auto' picks the fastest available: CUDA GPU, Apple GPU (mps), else CPU.

    Ultralytics' own default is the CPU even when an Apple GPU is present,
    which measured 9.8 FPS against 13.4 FPS on mps for the full pipeline
    (tools/measure/fps.py, Apple M4).
    """
    if requested != "auto":
        return requested
    import torch

    if torch.cuda.is_available():
        return "0"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_camera_source(raw: str) -> int | str:
    """A plain integer string means a local device index; anything else
    (an rtsp://, http://, or file path) is passed straight to OpenCV as a
    stream URL — this is what lets a phone or an existing NVR feed stand
    in for a dedicated camera."""
    try:
        return int(raw)
    except ValueError:
        return raw


def is_network_source(source: int | str) -> bool:
    return isinstance(source, str)


def is_file_source(source: int | str) -> bool:
    """A recorded video on disk, which ``--loop`` can rewind."""
    return isinstance(source, str) and Path(source).is_file()


def api_url(*parts: str) -> str:
    base = API_BASE.rstrip("/")
    return base + "/" + "/".join(parts)


def class_name(names, cid: int) -> str:
    if isinstance(names, (list, tuple)):
        raw = names[cid] if cid < len(names) else cid
    elif isinstance(names, dict):
        raw = names.get(cid, names.get(str(cid), cid))
    else:
        raw = cid
    return str(raw)


def violation_boxes(names, boxes_xyxy, confs, clss) -> list[tuple[str, float, tuple]]:
    """Every violation detection as (class_name, conf, box), one per box."""
    out = []
    for i in range(len(clss)):
        name = class_name(names, int(clss[i]))
        if is_violation_class(name):
            out.append((name, float(confs[i]), tuple(float(v) for v in boxes_xyxy[i].tolist())))
    return out


def badged_violations(
    detections: list[tuple[str, float, tuple]],
    tracker: identity.IdentityTracker | None,
) -> list[ppe_episodes.Violation]:
    """Attach the wearer's QR badge and tracked person id (or None) to each violation box.

    Boxes are kept apart, not merged per class, so that the episode tracker
    can tell two people with the same violation apart; the person id keeps
    one person's moving box in one episode.
    """
    return [
        ppe_episodes.Violation(
            name, conf, box, tracker.identify_box(box) if tracker else None, tracker.person_at(box) if tracker else None
        )
        for name, conf, box in detections
    ]


def is_violation_class(name: str) -> bool:
    n = name.strip().lower()
    return n.startswith("no-") or n.startswith("no_")


def frame_views(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return an untouched model input and an independent display canvas."""
    return frame, frame.copy()


def build_api_session(device_key: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    if device_key:
        session.headers["Authorization"] = f"Device {device_key}"
    return session


def make_sender(session: requests.Session):
    """Outbox sender: POST one queued item, return the HTTP status code.

    Alerts go to /v1/camera-events/; items carrying ``_endpoint`` (worker
    activity) go to that endpoint instead.
    """

    def send(payload: dict) -> int:
        body = dict(payload)
        endpoint = body.pop("_endpoint", "camera-events")
        return session.post(api_url("v1", endpoint, ""), json=body, timeout=5).status_code

    return send


# Badge sightings place a worker in the camera's zone for 60 s on the server
# (CAMERA_PRESENCE_SECONDS), so they are repeated well within that.
SIGHTING_INTERVAL_SECONDS = 15
# People in view feed the zone's head count; the server drops a count after 30 s.
PEOPLE_COUNT_INTERVAL_SECONDS = 5


def people_count_payload(camera_id: str, people: int, unix_time: float) -> dict:
    """How many people the camera sees, for /v1/camera-counts/."""
    from datetime import datetime, timezone

    return {
        "camera_id": camera_id,
        "people": int(people),
        "observed_at": datetime.fromtimestamp(unix_time, tz=timezone.utc).isoformat(),
    }


def make_count_sender(session: requests.Session):
    """Post one people count; return the HTTP status code."""

    def send(payload: dict) -> int:
        return session.post(api_url("v1", "camera-counts", ""), json=payload, timeout=2).status_code

    return send


def wall_clock(t: float, now: float | None = None) -> float:
    """Unix time of pipeline time ``t``.

    ``now`` is the pipeline's current time on the same clock: perf_counter()
    when live (the default), or the clip position with --video-clock, where
    an event's real-world time is when this run observed it.
    """
    now = time.perf_counter() if now is None else now
    return time.time() - (now - t)


def activity_payload(kind: str, badge: str, camera_id: str, unix_time: float) -> dict:
    """Worker activity for an identified person; the outbox adds event_id."""
    from datetime import datetime, timezone

    return {
        "_endpoint": "camera-activity",
        "kind": kind,
        "badge_code": badge,
        "camera_id": camera_id,
        "occurred_at": datetime.fromtimestamp(unix_time, tz=timezone.utc).isoformat(),
    }


class SightingThrottle:
    """Send at most one SIGHTING per badge per interval; check-in/out needs no more."""

    def __init__(self, interval: float = SIGHTING_INTERVAL_SECONDS):
        self.interval = interval
        self.last: dict[str, float] = {}

    def due(self, badge: str, now: float) -> bool:
        if now - self.last.get(badge, float("-inf")) >= self.interval:
            self.last[badge] = now
            return True
        return False


PPE_CLASS_IN_DESCRIPTION = re.compile(r"^Missing PPE: (\S+)")


def event_label(payload: dict) -> str:
    """What an event reports: the missing item for PPE, else its alert type or activity kind."""
    if payload.get("alert_type") == "PPE_VIOLATION":
        match = PPE_CLASS_IN_DESCRIPTION.match(payload.get("description", ""))
        if match:
            return match.group(1)
    return payload.get("alert_type") or payload.get("kind") or "UNKNOWN"


class RecordingOutbox:
    """An outbox that also appends every queued event to a JSON-lines file.

    ``clock`` gives the pipeline's current time, so with ``--video-clock``
    each record carries the position in the clip where the event fired;
    tools/measure/evaluate_clip.py scores these records against annotations.
    """

    def __init__(self, outbox: EventOutbox, path: str, clock):
        self._outbox = outbox
        self._file = open(path, "a", encoding="utf-8")
        self._clock = clock

    def enqueue(self, payload: dict, snapshot: bytes | None = None):
        record = {
            "t": round(self._clock(), 3),
            "event": event_label(payload),
            "alert_type": payload.get("alert_type"),
            "badge": payload.get("badge_code"),
            "confidence": payload.get("confidence"),
            "description": payload.get("description"),
        }
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()
        return self._outbox.enqueue(payload, snapshot)

    def close(self):
        self._file.close()
        return self._outbox.close()

    def __getattr__(self, name):
        return getattr(self._outbox, name)


def open_outbox(camera_id: str, session: requests.Session) -> EventOutbox:
    directory = Path(OUTBOX_DIR)
    if not directory.is_absolute():
        directory = module_root() / directory
    directory.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in camera_id)
    return EventOutbox(directory / f"{safe_id}.sqlite3", make_sender(session))


class CameraRules:
    """Alert rules saved in the dashboard, polled from the API for this camera.

    Until the first successful fetch (or if the API is down) every alert type
    stays enabled, so an outage never silently switches detection off. The
    API applies the same rules again when it receives an event.
    """

    def __init__(self, session: requests.Session, camera_id: str):
        self.session = session
        self.camera_id = camera_id
        self.rules: dict[str, dict] = {}
        self.zone: str | None = None
        self.areas: list[danger_areas.Area] = []
        self._stop = threading.Event()

    def refresh(self) -> bool:
        try:
            r = self.session.get(
                api_url("v1", "camera-config", ""),
                params={"camera_id": self.camera_id},
                timeout=5,
            )
            if r.status_code != 200:
                return False
            data = r.json()
        except (requests.RequestException, ValueError):
            return False
        self.rules = data.get("rules") or {}
        self.zone = data.get("zone")
        self.areas = danger_areas.parse_areas(data.get("areas"))
        return True

    def enabled(self, alert_type: str) -> bool:
        return self.rules.get(alert_type, {}).get("is_enabled", True)

    def threshold(self, alert_type: str) -> float | None:
        value = self.rules.get(alert_type, {}).get("threshold_seconds")
        return float(value) if value else None

    def start(self) -> None:
        def run():
            while not self._stop.wait(RULES_REFRESH_SECONDS):
                self.refresh()

        threading.Thread(target=run, name="sitesafe-rules", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()


def ppe_payload(
    violation_label: str, confidence: float, camera_id: str, badge: str | None = None
) -> dict:
    payload = {
        "alert_type": "PPE_VIOLATION",
        "severity": "HIGH",
        "description": f"Missing PPE: {violation_label} (conf: {confidence:.2f})",
        "camera_id": camera_id,
        "confidence": round(float(confidence), 4),
    }
    if badge:
        payload["badge_code"] = badge
    return payload


def with_badge(payload: dict, badge: str | None) -> dict:
    if badge:
        payload = {**payload, "badge_code": badge}
    return payload


def proximity_payload(event: dict, camera_id: str) -> dict:
    return {
        "alert_type": "VEHICLE_PROXIMITY",
        "severity": proximity.severity_for(event),
        "description": proximity.describe(event),
        "camera_id": camera_id,
    }


def with_model(payload: dict, version: str) -> dict:
    """Name the weights that produced this event (FR-29)."""
    return {**payload, "model_version": version}


def env_enabled(name: str) -> bool:
    return os.environ.get(name, "1").strip().lower() not in ("0", "false", "no", "off")


def snapshots_enabled_by_default() -> bool:
    return env_enabled(SNAPSHOTS_ENV)


def make_live_sender(session: requests.Session, camera_id: str):
    """Post one JPEG to /v1/camera-frames/; return the HTTP status code."""

    def send(jpeg: bytes) -> int:
        return session.post(
            api_url("v1", "camera-frames", ""),
            params={"camera_id": camera_id},
            data=jpeg,
            headers={"Content-Type": "image/jpeg"},
            timeout=2,
        ).status_code

    return send


def queue_event(
    outbox: EventOutbox,
    rules: CameraRules,
    payload: dict,
    snapshot: evidence.FrameSnapshot | None = None,
) -> bool:
    """Persist a confirmed event, with its frame snapshot if any. Returns False if a rule disables it.

    The snapshot is encoded only after the rule check, so a disabled alert
    type costs no JPEG encoding.
    """
    if not rules.enabled(payload["alert_type"]):
        return False
    outbox.enqueue(payload, snapshot.get() if snapshot is not None else None)
    return True


def draw_proximity(
    frame: np.ndarray,
    persons: list,
    vehicles: list,
    event: dict | None,
) -> None:
    """Outline detected people and vehicles, and draw a line between the
    closest breaching pair so the operator can see what triggered a warning."""
    for box in persons:
        x1, y1, x2, y2 = (int(v) for v in box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
        cv2.putText(
            frame, "person", (x1, max(y1 - 6, 16)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1, cv2.LINE_AA,
        )

    for box, label in vehicles:
        x1, y1, x2, y2 = (int(v) for v in box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
        cv2.putText(
            frame, label, (x1, max(y1 - 6, 16)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1, cv2.LINE_AA,
        )

    if event is None:
        return

    def centre(b):
        return (int((b[0] + b[2]) / 2), int((b[1] + b[3]) / 2))

    p_c = centre(event["person_box"])
    v_c = centre(event["vehicle_box"])
    cv2.line(frame, p_c, v_c, (0, 0, 255), 2, cv2.LINE_AA)
    mid = ((p_c[0] + v_c[0]) // 2, (p_c[1] + v_c[1]) // 2)
    cv2.putText(
        frame,
        f"{event['normalised_gap']:.2f}",
        mid,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        2,
        cv2.LINE_AA,
    )


def draw_poses(
    frame: np.ndarray,
    poses: list[tuple[list, list]],
    fired_this_frame: list[dict],
) -> None:
    """Draw a dot per confidently detected keypoint, and mark the centroid
    of any track that confirmed a fall on this exact sampled frame."""
    for xy, conf in poses:
        for (x, y), c in zip(xy, conf):
            if c < fall_detection.DEFAULT_MIN_KEYPOINT_CONF:
                continue
            cv2.circle(frame, (int(x), int(y)), 3, (255, 0, 200), -1)

    for event in fired_this_frame:
        cx, cy = (int(v) for v in event["centroid"])
        cv2.circle(frame, (cx, cy), 26, (0, 0, 255), 3)
        cv2.putText(
            frame, "FALL", (cx - 24, cy - 32),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA,
        )


def draw_identities(frame: np.ndarray, tracker: identity.IdentityTracker | None) -> None:
    """Label people identified by a QR badge with the badge's last characters."""
    if tracker is None:
        return
    for track in tracker.tracks:
        if not track.badge:
            continue
        x1, y1 = int(track.box[0]), int(track.box[1])
        cv2.putText(
            frame,
            f"ID ..{track.badge[-4:]}",
            (x1, max(y1 - 22, 30)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 200, 0),
            1,
            cv2.LINE_AA,
        )


def draw_fps(frame: np.ndarray, fps: float) -> None:
    h, w = frame.shape[:2]
    text = f"FPS: {fps:.1f}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = w - tw - 12
    y = 28
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def draw_danger_areas(frame: np.ndarray, areas: list[danger_areas.Area], occupied: set[int]) -> None:
    """Outline each danger area; fill it red while someone is inside."""
    h, w = frame.shape[:2]
    for area in areas:
        pts = np.array([[int(x * w), int(y * h)] for x, y in area.polygon], dtype=np.int32)
        inside = area.id in occupied
        color = (0, 0, 255) if inside else (0, 200, 255)  # BGR red / amber
        if inside:
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)
        x, y = pts.min(axis=0)
        cv2.putText(frame, area.name, (int(x) + 4, max(int(y) - 6, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)


def draw_status_bar(
    frame: np.ndarray,
    violations: list[tuple[str, float]],
    proximity_event: dict | None = None,
    fall_fired_this_frame: bool = False,
    danger_area: str | None = None,
) -> None:
    """Top-left status strip: green ALL CLEAR, or red naming what is wrong.

    A confirmed fall outranks everything else in the banner — a worker down
    is the most urgent condition this pipeline can raise. Someone inside a
    danger area comes next, then a proximity breach, since a worker beside
    moving plant is more immediate than a missing hardhat.
    """
    h, w = frame.shape[:2]
    bar_h = 44
    overlay = frame.copy()
    if fall_fired_this_frame:
        color = (0, 0, 220)  # BGR red-ish
        label = "FALL DETECTED"
    elif danger_area is not None:
        color = (0, 0, 220)
        label = f"DANGER AREA - {danger_area}"
    elif proximity_event is not None:
        color = (0, 0, 220)  # BGR red-ish
        label = f"VEHICLE PROXIMITY - {proximity_event['vehicle_label']}"
    elif violations:
        color = (0, 0, 220)
        names = ", ".join(sorted({v[0] for v in violations}))
        label = f"VIOLATION DETECTED - {names}"
    else:
        color = (0, 160, 60)  # BGR green
        label = "ALL CLEAR"
    cv2.rectangle(overlay, (0, 0), (w, bar_h), color, -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.putText(
        frame,
        label[:120],
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def plot_detections(
    frame: np.ndarray,
    names: dict[int, str] | dict[str, str] | Any,
    boxes_xyxy: np.ndarray,
    confs: np.ndarray,
    clss: np.ndarray,
) -> list[tuple[str, float]]:
    """Draw boxes; return list of (class_name, conf) for violations (one entry per class, max conf)."""
    violations_map: dict[str, float] = {}
    h, w = frame.shape[:2]
    for i in range(len(clss)):
        cid = int(clss[i])
        if isinstance(names, (list, tuple)):
            raw = names[cid] if cid < len(names) else cid
        elif isinstance(names, dict):
            raw = names.get(cid, names.get(str(cid), cid))
        else:
            raw = cid
        name = str(raw)
        conf = float(confs[i])
        x1, y1, x2, y2 = map(int, boxes_xyxy[i].tolist())
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        if is_violation_class(name):
            color = (0, 0, 255)
            violations_map[name] = max(conf, violations_map.get(name, 0.0))
        else:
            color = (0, 200, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cap = f"{name} {conf:.2f}"
        cv2.putText(
            frame,
            cap,
            (x1, max(y1 - 6, 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )
    return list(violations_map.items())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=DEFAULT_CAMERA_SOURCE,
        help=(
            "Camera source: a local device index (e.g. 0) or a stream URL "
            "(e.g. rtsp://... or http://<phone-ip>:8080/video for a phone "
            "running IP Webcam). Defaults to $SITESAFE_CAMERA_SOURCE or 0."
        ),
    )
    parser.add_argument(
        "--camera-id",
        default=DEFAULT_CAMERA_ID,
        help="Identifier for this camera, attached to every alert it raises "
        "and used to resolve which zone it's assigned to. Defaults to "
        "$SITESAFE_CAMERA_ID or CAM-01. Give each concurrent instance a "
        "distinct id (CAM-ENTRANCE, CAM-BAY-2, ...).",
    )
    parser.add_argument(
        "--ppe-conf",
        type=float,
        default=PPE_CONF,
        help="Global PPE candidate confidence threshold (default: "
        f"{PPE_CONF}). This is not temporal confirmation; calibrate it on a "
        "clean validation set before deployment.",
    )
    parser.add_argument(
        "--no-proximity",
        action="store_true",
        help="Disable vehicle proximity detection. PPE and inactivity remain "
        "enabled; combine with --no-inactivity to skip the COCO detector. "
        "Useful for a camera covering an area with no vehicle traffic.",
    )
    parser.add_argument(
        "--proximity-threshold",
        type=float,
        default=proximity.DEFAULT_THRESHOLD,
        help="How close a worker must be to a vehicle to count as a breach, "
        "measured in person-heights (default: "
        f"{proximity.DEFAULT_THRESHOLD}). Roughly one person-height is about "
        "1.7 m when worker and vehicle are at similar distance from the camera.",
    )
    parser.add_argument(
        "--proximity-persistence",
        type=int,
        default=proximity.DEFAULT_PERSISTENCE,
        help="Evaluated frames a person must be near a vehicle, with no gap over "
        f"{proximity.DEFAULT_MAX_GAP_SECONDS:g}s, before an alert is raised "
        f"(default: {proximity.DEFAULT_PERSISTENCE}). Filters out single-frame "
        "detection noise.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Restart a video file from the beginning when it ends, for "
        "demonstrations and long-running tests. Ignored for cameras and streams.",
    )
    parser.add_argument(
        "--video-clock",
        action="store_true",
        help="Time every tracker by the video file's own timestamps instead of "
        "the wall clock, so a recorded clip behaves as it did live (for evaluation).",
    )
    parser.add_argument(
        "--events-out",
        metavar="FILE",
        help="Also append every queued event, with the pipeline's time, to this "
        "JSON-lines file (read by tools/measure/evaluate_clip.py).",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without the preview window (keyboard controls are then "
        "unavailable; stop with Ctrl+C or SIGTERM, which still prints the summary).",
    )
    parser.add_argument(
        "--ppe-persistence",
        type=float,
        default=ppe_episodes.DEFAULT_PERSISTENCE_SECONDS,
        help="Seconds a missing-PPE detection must persist on one person before "
        f"it raises an alert (default {ppe_episodes.DEFAULT_PERSISTENCE_SECONDS:g}).",
    )
    parser.add_argument(
        "--ppe-clear-seconds",
        type=float,
        default=ppe_episodes.DEFAULT_CLEAR_SECONDS,
        help="Seconds a person's violation must be unseen before the episode "
        f"closes and a new one can alert (default {ppe_episodes.DEFAULT_CLEAR_SECONDS:g}).",
    )
    parser.add_argument(
        "--no-inactivity",
        action="store_true",
        help="Disable person inactivity detection. The feature is enabled by "
        "default and shares the sampled COCO detector used for proximity.",
    )
    parser.add_argument(
        "--inactivity-timeout",
        type=float,
        default=inactivity.DEFAULT_TIMEOUT_SECONDS,
        help="Seconds a person centroid must remain stationary before an "
        f"INACTIVITY alert is raised (default: {inactivity.DEFAULT_TIMEOUT_SECONDS:g}).",
    )
    parser.add_argument(
        "--inactivity-movement-threshold",
        type=float,
        default=inactivity.DEFAULT_MOVEMENT_THRESHOLD,
        help="Maximum centroid displacement, in image pixels, still treated "
        f"as stationary (default: {inactivity.DEFAULT_MOVEMENT_THRESHOLD:g}). "
        "Calibrate this per camera resolution and view.",
    )
    parser.add_argument(
        "--device",
        default=os.environ.get("SITESAFE_INFERENCE_DEVICE", "auto"),
        help="Inference device: auto (default), cpu, mps or a CUDA index such as 0.",
    )
    parser.add_argument(
        "--no-qr",
        action="store_true",
        help="Disable QR badge identification. When enabled (the default) it "
        "needs the person detector, so it is also off with both "
        "--no-proximity and --no-inactivity. People are still followed "
        "(for one PPE alert per person) whenever the person detector runs.",
    )
    parser.add_argument(
        "--no-fire",
        action="store_true",
        help="Disable fire/smoke detection (it is also off when models/fire_smoke.pt is missing).",
    )
    parser.add_argument(
        "--fire-conf",
        type=float,
        default=fire_detection.DEFAULT_CONF,
        help=f"Fire/smoke detector confidence threshold (default {fire_detection.DEFAULT_CONF}).",
    )
    parser.add_argument(
        "--fire-persistence",
        type=float,
        default=fire_detection.DEFAULT_PERSISTENCE_SECONDS,
        help="Seconds fire or smoke must keep appearing before an alert "
        f"(default {fire_detection.DEFAULT_PERSISTENCE_SECONDS:g}).",
    )
    parser.add_argument(
        "--no-fall",
        action="store_true",
        help="Disable fall detection. Uses its own pose model independent of "
        "--no-proximity/--no-inactivity's shared COCO detector.",
    )
    parser.add_argument(
        "--fall-persistence",
        type=float,
        default=fall_detection.DEFAULT_PERSISTENCE_SECONDS,
        help="Seconds a collapsed posture must be sustained before a FALL "
        f"alert is raised (default: {fall_detection.DEFAULT_PERSISTENCE_SECONDS:g}). "
        "Filters out a crouch or a bend to pick something up.",
    )
    parser.add_argument(
        "--no-snapshots",
        action="store_true",
        default=not snapshots_enabled_by_default(),
        help="Do not attach a frame snapshot to alerts (alert evidence, FR-29). "
        f"Also set by {SNAPSHOTS_ENV}=0. The model version is still sent.",
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        default=not env_enabled(LIVE_ENV),
        help=f"Do not send the live view to the dashboard's Cameras page. Also set by {LIVE_ENV}=0.",
    )
    parser.add_argument(
        "--live-fps",
        type=float,
        default=live_feed.DEFAULT_FPS,
        help=f"Live view frames per second sent to the dashboard (default {live_feed.DEFAULT_FPS:g}).",
    )
    args = parser.parse_args()
    if not 0.0 <= args.ppe_conf <= 1.0:
        parser.error("--ppe-conf must be between zero and one")
    if args.ppe_persistence < 0:
        parser.error("--ppe-persistence must be zero or greater")
    if args.ppe_clear_seconds <= 0:
        parser.error("--ppe-clear-seconds must be greater than zero")
    if args.inactivity_timeout <= 0:
        parser.error("--inactivity-timeout must be greater than zero")
    if args.inactivity_movement_threshold < 0:
        parser.error("--inactivity-movement-threshold must be zero or greater")
    if args.fall_persistence <= 0:
        parser.error("--fall-persistence must be greater than zero")
    if not 0.0 <= args.fire_conf <= 1.0:
        parser.error("--fire-conf must be between zero and one")
    if args.fire_persistence <= 0:
        parser.error("--fire-persistence must be greater than zero")
    if not 0.0 < args.live_fps <= 15.0:
        parser.error("--live-fps must be greater than zero and at most 15")
    if args.video_clock and args.loop:
        parser.error("--video-clock cannot be combined with --loop (time would restart each loop)")
    if args.video_clock and not is_file_source(resolve_camera_source(args.source)):
        parser.error("--video-clock needs a video file as --source")
    return args


def main() -> None:
    os.chdir(module_root())
    args = parse_args()
    camera_id = args.camera_id
    source = resolve_camera_source(args.source)
    networked = is_network_source(source)

    model_path = resolve_model_path()
    if not model_path.is_file():
        print(f"Model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    device = pick_device(args.device)
    print(f"[{camera_id}] inference device: {device}")
    device_key = os.environ.get(DEVICE_KEY_ENV, "").strip()
    session = build_api_session(device_key)
    if not device_key:
        print(
            f"[{camera_id}] {DEVICE_KEY_ENV} is not set: events are queued locally "
            "and delivered once a camera device token is configured",
            file=sys.stderr,
        )
    rules = CameraRules(session, camera_id)
    if rules.refresh():
        print(f"[{camera_id}] loaded alert rules (zone: {rules.zone or 'unassigned'})")
    else:
        print(f"[{camera_id}] could not load alert rules; all alert types enabled", file=sys.stderr)
    rules.start()
    outbox = open_outbox(camera_id, session)
    t_now = 0.0  # the pipeline's clock; set per frame below
    if args.events_out:
        outbox = RecordingOutbox(outbox, args.events_out, lambda: t_now)
    outbox.start()
    live = None
    if not args.no_live:
        live = live_feed.LiveFeed(make_live_sender(session, camera_id), fps=args.live_fps)
        live.start()
        print(f"[{camera_id}] live view to the dashboard at up to {args.live_fps:g} FPS")
    pending = outbox.stats()["pending"]
    if pending:
        print(f"[{camera_id}] resuming delivery of {pending} queued event(s)")

    model = YOLO(str(model_path))
    ppe_version = evidence.model_version(model_path)
    print(f"[{camera_id}] PPE model {ppe_version}")
    if args.no_snapshots:
        print(f"[{camera_id}] alert snapshots disabled; alerts carry the model version only")

    coco_model = None
    people_counts = None
    coco_version = ""
    proximity_tracker = None
    inactivity_tracker = None
    if not (args.no_proximity and args.no_inactivity):
        proximity_model_path = resolve_proximity_model_path()
        if proximity_model_path.is_file():
            coco_model = YOLO(str(proximity_model_path))
            # Latest people count for the zone head count; never queued (latest_sender).
            people_counts = LatestSender(
                make_count_sender(session),
                interval=PEOPLE_COUNT_INTERVAL_SECONDS,
                encode=lambda value: people_count_payload(camera_id, *value),
                name="sitesafe-counts",
            )
            people_counts.start()
            coco_version = evidence.model_version(proximity_model_path)
            if not args.no_proximity:
                proximity_tracker = proximity.ProximityTracker(
                    threshold=args.proximity_threshold,
                    persistence=args.proximity_persistence,
                )
                print(
                    f"[{camera_id}] vehicle proximity enabled "
                    f"(threshold {args.proximity_threshold} person-heights, "
                    f"confirm after {args.proximity_persistence} samples, "
                    f"one alert per person until {proximity.DEFAULT_CLEAR_SECONDS:g}s clear)"
                )
            if not args.no_inactivity:
                # A timeout saved in the dashboard's INACTIVITY rule overrides
                # the command-line default for this camera.
                saved_timeout = rules.threshold("INACTIVITY")
                if saved_timeout:
                    args.inactivity_timeout = saved_timeout
                inactivity_tracker = inactivity.InactivityTracker(
                    timeout_seconds=args.inactivity_timeout,
                    movement_threshold=args.inactivity_movement_threshold,
                )
                print(
                    f"[{camera_id}] inactivity detection enabled "
                    f"(timeout {args.inactivity_timeout:g}s, movement threshold "
                    f"{args.inactivity_movement_threshold:g}px)"
                )
        else:
            # Missing COCO weights should degrade to PPE-only rather than
            # taking down the whole pipeline.
            print(
                f"[{camera_id}] person/vehicle model not found at {proximity_model_path}; "
                "continuing with PPE detection only",
                file=sys.stderr,
            )

    pose_model = None
    pose_version = ""
    fall_tracker = None
    if not args.no_fall:
        fall_model_path = resolve_fall_model_path()
        if fall_model_path.is_file():
            pose_model = YOLO(str(fall_model_path))
            pose_version = evidence.model_version(fall_model_path)
            fall_tracker = fall_detection.FallTracker(
                persistence_seconds=args.fall_persistence,
            )
            print(
                f"[{camera_id}] fall detection enabled "
                f"(persistence {args.fall_persistence:g}s)"
            )
        else:
            # Same degrade-gracefully behaviour as the COCO detector above:
            # a missing pose model should not take down PPE/proximity/
            # inactivity detection.
            print(
                f"[{camera_id}] pose model not found at {fall_model_path}; "
                "continuing without fall detection",
                file=sys.stderr,
            )

    fire_model = None
    fire_version = ""
    fire_tracker = None
    if not args.no_fire:
        fire_model_path = resolve_fire_model_path()
        if fire_model_path.is_file():
            fire_model = YOLO(str(fire_model_path))
            fire_version = evidence.model_version(fire_model_path)
            fire_tracker = fire_detection.FireTracker(persistence_seconds=args.fire_persistence)
            print(f"[{camera_id}] fire/smoke detection enabled (confirm after {args.fire_persistence:g}s)")
        else:
            print(
                f"[{camera_id}] fire/smoke model not found at {fire_model_path}; fire detection disabled",
                file=sys.stderr,
            )

    # People are followed whenever the person detector runs: their ids keep
    # one person's PPE violations in one episode. QR badges, when enabled,
    # add who each person is.
    qr_decoder = None
    identity_tracker = identity.IdentityTracker() if coco_model is not None else None
    # Danger areas follow the same tracked people; areas come with the rules.
    danger_tracker = danger_areas.DangerAreaTracker() if identity_tracker is not None else None
    if danger_tracker is None:
        print(f"[{camera_id}] danger areas need the person detector; disabled", file=sys.stderr)
    sightings = None
    if not args.no_qr:
        if coco_model is not None:
            qr_decoder = identity.QrDecoder()
            sightings = SightingThrottle()
            print(f"[{camera_id}] QR badge identification enabled")
        else:
            print(
                f"[{camera_id}] QR badge identification needs the person detector; disabled",
                file=sys.stderr,
            )

    print(f"[{camera_id}] opening {'stream' if networked else 'device index'}: {source}")
    cap = cv2.VideoCapture(source)
    if networked:
        # Keep only the newest frame so a slow/laggy WiFi link doesn't pile
        # up a backlog and make detection run behind real time. Not every
        # backend honours this, so it's a best-effort setting.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        print(f"[{camera_id}] could not open source: {source}", file=sys.stderr)
        sys.exit(1)

    window_title = f"Site-Safe Inference [{camera_id}]"
    looping = args.loop and is_file_source(source)
    loops = 0

    def show(image) -> None:
        """Present the operator's view: the preview window and the dashboard's live view."""
        if not args.no_display:
            cv2.imshow(window_title, image)
        if live is not None:
            live.offer(image)

    def stop_on_sigterm(signum, frame):  # noqa: ARG001
        raise KeyboardInterrupt

    # A stop request from a test harness or service manager still runs the
    # finally block below, so queued events are kept and the summary prints.
    signal.signal(signal.SIGTERM, stop_on_sigterm)
    ppe_episodes_tracker = ppe_episodes.EpisodeTracker(
        persistence_seconds=args.ppe_persistence, clear_seconds=args.ppe_clear_seconds
    )
    paused = False
    total_frames = 0
    alerts_sent = 0
    proximity_alerts_sent = 0
    inactivity_alerts_sent = 0
    fall_alerts_sent = 0
    consecutive_read_failures = 0
    # Latched so the overlay keeps showing the last proximity result on
    # frames where the sampled detector did not run.
    last_persons: list = []
    last_vehicles: list = []
    last_proximity_event: dict | None = None
    last_poses: list = []
    last_fire: list = []
    t_start = time.perf_counter()
    fps_smooth = 0.0
    t_prev = 0.0 if args.video_clock else time.perf_counter()

    print("Controls: Q quit | S force test alert | P pause/unpause")

    try:
        while True:
            ok, frame = cap.read()
            if not ok and looping and consecutive_read_failures == 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                loops += 1
                ok, frame = cap.read()
            if not ok:
                consecutive_read_failures += 1
                # A single dropped frame is routine on a phone/RTSP stream
                # over WiFi; only give up after a sustained run of failures
                # (a genuinely disconnected source, or a real local webcam
                # that's gone away).
                if consecutive_read_failures >= MAX_CONSECUTIVE_READ_FAILURES:
                    print(
                        f"[{camera_id}] lost source after "
                        f"{consecutive_read_failures} consecutive failed reads",
                        file=sys.stderr,
                    )
                    break
                if networked:
                    time.sleep(READ_RETRY_DELAY_SECONDS)
                continue
            consecutive_read_failures = 0
            total_frames += 1
            t_now = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0 if args.video_clock else time.perf_counter()
            dt = max(t_now - t_prev, 1e-6)
            t_prev = t_now
            fps_smooth = 0.9 * fps_smooth + 0.1 * (1.0 / dt)

            key = -1 if args.no_display else cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("p"):
                paused = not paused
                if inactivity_tracker is not None:
                    # Paused time is not observed time and must not count
                    # toward a stationary timeout.
                    inactivity_tracker.reset()
                if fall_tracker is not None:
                    # Same reasoning: paused time must not silently count
                    # toward a collapsed-posture persistence window either.
                    fall_tracker.reset()
                if danger_tracker is not None:
                    danger_tracker.reset()
                if proximity_tracker is not None:
                    proximity_tracker.reset()
                if identity_tracker is not None:
                    identity_tracker.reset()
                if fire_tracker is not None:
                    fire_tracker.reset()
                print(f"[{'PAUSED' if paused else 'RESUME'}] detection")
            if key == ord("s"):
                forced = {
                    "alert_type": "PPE_VIOLATION",
                    "severity": "HIGH",
                    "description": "Manual test alert (forced via keyboard)",
                    "camera_id": camera_id,
                }
                if queue_event(outbox, rules, forced):
                    alerts_sent += 1
                    print("[ALERT] forced test queued")
                else:
                    print("[ALERT] forced test skipped: PPE alerts disabled by rule")

            if paused:
                draw_status_bar(frame, [])
                cv2.putText(
                    frame,
                    "PAUSED",
                    (frame.shape[1] // 2 - 60, frame.shape[0] // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                draw_fps(frame, fps_smooth)
                show(frame)
                continue

            # Keep detector inputs free of visual overlays.  ``plot_detections``
            # and the draw helpers mutate their image argument, so drawing on
            # ``frame`` before the COCO/pose passes would feed artificial boxes
            # and text into those models.  All inference uses ``raw_frame``;
            # only ``display_frame`` is annotated for the operator.
            raw_frame, display_frame = frame_views(frame)
            # Evidence comes from the raw frame, never the annotated one, and
            # is encoded only if an event below is confirmed on this frame.
            snapshot = evidence.FrameSnapshot(raw_frame, enabled=not args.no_snapshots)

            results = model.predict(raw_frame, verbose=False, conf=args.ppe_conf, device=device)
            result = results[0]
            names = result.names
            violations: list[tuple[str, float]] = []
            violation_dets: list[tuple[str, float, tuple]] = []
            if result.boxes is not None and len(result.boxes) > 0:
                xyxy = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                clss = result.boxes.cls.cpu().numpy().astype(int)
                violations = plot_detections(display_frame, names, xyxy, confs, clss)
                violation_dets = violation_boxes(names, xyxy, confs, clss)

            # The shared COCO detector runs on a sampled subset of frames;
            # between samples the previous proximity result is reused for its
            # overlay, while inactivity timing uses the actual sample times.
            confirmed_proximity: list[dict] = []
            confirmed_inactivity: list[dict] = []
            confirmed_danger: list[dict] = []
            if coco_model is not None and total_frames % PROXIMITY_FRAME_INTERVAL == 0:
                p_result = coco_model.predict(
                    raw_frame, verbose=False, conf=PROXIMITY_CONF, device=device
                )[0]
                if p_result.boxes is not None and len(p_result.boxes) > 0:
                    p_xyxy = p_result.boxes.xyxy.cpu().numpy()
                    p_clss = p_result.boxes.cls.cpu().numpy().astype(int)
                    last_persons, last_vehicles = proximity.split_detections(p_xyxy, p_clss)
                else:
                    last_persons, last_vehicles = [], []
                if people_counts is not None:
                    people_counts.offer((len(last_persons), wall_clock(t_now, t_now)))

                if inactivity_tracker is not None:
                    confirmed_inactivity = inactivity_tracker.update(
                        last_persons, now=t_now
                    )
                if identity_tracker is not None:
                    badges = qr_decoder.decode(raw_frame) if qr_decoder is not None else []
                    identity_tracker.update(last_persons, badges, now=t_now)
                    in_view = [t for t in identity_tracker.tracks if t.last_seen == t_now]
                    if proximity_tracker is not None:
                        confirmed_proximity = proximity_tracker.update(
                            [(t.track_id, t.box) for t in in_view], last_vehicles, now=t_now
                        )
                        last_proximity_event = proximity.closest_proximity(
                            last_persons, last_vehicles, args.proximity_threshold
                        )
                    if danger_tracker is not None:
                        fh, fw = raw_frame.shape[:2]
                        feet = [(t.track_id, danger_areas.foot_point(t.box, fw, fh)) for t in in_view]
                        confirmed_danger = danger_tracker.update(feet, rules.areas, now=t_now)
                    # Attendance evidence: identified people currently in view.
                    for track in identity_tracker.tracks:
                        if track.badge and track.last_seen == t_now and sightings and sightings.due(track.badge, t_now):
                            outbox.enqueue(activity_payload("SIGHTING", track.badge, camera_id, wall_clock(t_now, t_now)))
                    if inactivity_tracker is not None:
                        for moved in inactivity_tracker.resumed:
                            badge = identity_tracker.identify_box(moved["person_box"])
                            if badge:
                                outbox.enqueue(
                                    activity_payload("IDLE_END", badge, camera_id, wall_clock(moved["resumed_at"], t_now))
                                )

            # The pose model is an independent forward pass with its own
            # sampling interval — it does not share the COCO detector above.
            confirmed_fall: list[dict] = []
            if pose_model is not None and total_frames % FALL_FRAME_INTERVAL == 0:
                f_result = pose_model.predict(raw_frame, verbose=False, conf=FALL_CONF, device=device)[0]
                last_poses = []
                if f_result.keypoints is not None and len(f_result.keypoints) > 0:
                    xy_all = f_result.keypoints.xy.cpu().numpy()
                    conf_all = f_result.keypoints.conf.cpu().numpy()
                    last_poses = [
                        ([tuple(p) for p in xy_all[i].tolist()], conf_all[i].tolist())
                        for i in range(len(xy_all))
                    ]
                if fall_tracker is not None:
                    confirmed_fall = fall_tracker.update(last_poses, now=t_now)

            confirmed_fire: list[dict] = []
            if fire_model is not None and total_frames % FIRE_FRAME_INTERVAL == 0:
                fr = fire_model.predict(raw_frame, verbose=False, conf=args.fire_conf, device=device)[0]
                last_fire = (
                    fire_detections(fr.names, fr.boxes.xyxy.cpu().numpy(), fr.boxes.conf.cpu().numpy(), fr.boxes.cls.cpu().numpy().astype(int))
                    if fr.boxes is not None and len(fr.boxes) > 0
                    else []
                )
                h, w = raw_frame.shape[:2]
                confirmed_fire = fire_tracker.update(last_fire, frame_area=float(h * w), now=t_now)
            if fire_model is not None:
                draw_fire(display_frame, last_fire)

            if proximity_tracker is not None:
                draw_proximity(display_frame, last_persons, last_vehicles, last_proximity_event)
            if pose_model is not None:
                draw_poses(display_frame, last_poses, confirmed_fall)

            if danger_tracker is not None:
                draw_danger_areas(display_frame, rules.areas, danger_tracker.occupied)
            draw_identities(display_frame, identity_tracker)
            occupied = [a.name for a in rules.areas if danger_tracker is not None and a.id in danger_tracker.occupied]
            draw_status_bar(
                display_frame, violations, last_proximity_event, bool(confirmed_fall), occupied[0] if occupied else None
            )
            draw_fps(display_frame, fps_smooth)

            # Confirmed events go to the durable outbox; a background thread
            # delivers them, so a slow or offline API never stalls capture
            # and an outage does not lose the event.
            # One alert per person per violation episode (FR-05): each
            # violation box is tied to its person and tracked, confirmed after
            # it persists and re-alerted only after it has cleared.
            people = identity_tracker.people() if identity_tracker is not None else None
            for episode in ppe_episodes_tracker.update(
                badged_violations(violation_dets, identity_tracker), now=t_now, people=people
            ):
                vname, vconf, badge = episode["class"], episode["confidence"], episode["badge"]
                if queue_event(outbox, rules, with_model(ppe_payload(vname, vconf, camera_id, badge), ppe_version), snapshot):
                    alerts_sent += 1
                    who = f" [{badge}]" if badge else ""
                    print(f"[ALERT] {vname}{who} detected ({vconf:.2f}, episode {episode['track_id']}) → queued")

            # One alert per person per encounter (proximity.ProximityTracker);
            # a camera-wide cooldown would drop a second worker at risk.
            for event in confirmed_proximity:
                badge = next((t.badge for t in identity_tracker.tracks if t.track_id == event["person"]), None)
                payload = with_model(with_badge(proximity_payload(event, camera_id), badge), coco_version)
                if queue_event(outbox, rules, payload, snapshot):
                    alerts_sent += 1
                    proximity_alerts_sent += 1
                    who = f" [{badge}]" if badge else ""
                    print(f"[ALERT] {proximity.describe(event)}{who} → queued")

            # The tracker itself latches each temporary person track until
            # movement re-arms it, so a second global cooldown would suppress
            # legitimate simultaneous events from different people.
            for event in confirmed_inactivity:
                badge = identity_tracker.identify_box(event["person_box"]) if identity_tracker else None
                if badge:
                    # Idle time is recorded even if INACTIVITY alerts are switched off.
                    outbox.enqueue(
                        activity_payload("IDLE_START", badge, camera_id, wall_clock(event["stationary_since"], t_now))
                    )
                payload = with_model(with_badge(inactivity.alert_payload(event, camera_id), badge), coco_version)
                if queue_event(outbox, rules, payload, snapshot):
                    alerts_sent += 1
                    inactivity_alerts_sent += 1
                    print(f"[ALERT] {inactivity.describe(event)} → queued")

            # Same reasoning as inactivity above: FallTracker latches per
            # track, so no additional cooldown is applied here.
            for event in confirmed_fall:
                badge = identity_tracker.identify(event["centroid"]) if identity_tracker else None
                payload = with_model(with_badge(fall_detection.alert_payload(event, camera_id), badge), pose_version)
                if queue_event(outbox, rules, payload, snapshot):
                    alerts_sent += 1
                    fall_alerts_sent += 1
                    print(f"[ALERT] {fall_detection.describe(event)} → queued")

            # One alert per person per entry into a danger area (DangerAreaTracker
            # latches each entry until the person has been out of it a while).
            for event in confirmed_danger:
                badge = next((t.badge for t in identity_tracker.tracks if t.track_id == event["person"]), None)
                payload = with_model(with_badge(danger_areas.alert_payload(event, camera_id), badge), coco_version)
                if queue_event(outbox, rules, payload, snapshot):
                    alerts_sent += 1
                    who = f" [{badge}]" if badge else ""
                    print(f"[ALERT] {danger_areas.describe(event, camera_id)}{who} → queued")

            # FireTracker latches per class until the scene is clear, so no
            # extra cooldown is needed; the server applies hot-work permits.
            for event in confirmed_fire:
                if queue_event(outbox, rules, with_model(fire_detection.alert_payload(event, camera_id), fire_version), snapshot):
                    alerts_sent += 1
                    print(f"[ALERT] {fire_detection.describe(event)} → queued")

            show(display_frame)
    except KeyboardInterrupt:
        print(f"[{camera_id}] stopped")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        rules.stop()
        if live is not None:
            live.stop()
        if people_counts is not None:
            people_counts.stop()
        outbox.stop()
        delivery = outbox.stats()
        outbox.close()
        duration = time.perf_counter() - t_start
        print()
        print("=== Session summary ===")
        print(f"  Camera:                 {camera_id} ({source})")
        print(f"  Total frames processed: {total_frames}")
        print(f"  Total alerts queued:    {alerts_sent}")
        print(f"    of which proximity:   {proximity_alerts_sent}")
        print(f"    of which inactivity:  {inactivity_alerts_sent}")
        print(f"    of which fall:        {fall_alerts_sent}")
        print(f"  Still queued on disk:   {delivery['pending']} (delivered on next start)")
        print(f"  Rejected by the API:    {delivery['dead']}")
        if delivery["evicted"]:
            print(f"  Evicted (queue full):   {delivery['evicted']}")
        if delivery["last_error"]:
            print(f"  Last delivery error:    {delivery['last_error']}")
        if live is not None:
            print(f"  Live frames sent:       {live.sent} ({live.failed} failed)")
        if people_counts is not None:
            print(f"  People counts sent:     {people_counts.sent} ({people_counts.failed} failed)")
        print(f"  Session duration:       {duration:.1f}s")
        if looping:
            print(f"  Times the clip looped:  {loops}")


if __name__ == "__main__":
    main()
