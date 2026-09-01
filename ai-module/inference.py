#!/usr/bin/env python3
"""
Site-Safe vision pipeline: PPE, vehicle-proximity, inactivity, and fall
warnings, with optional Django alert API integration.
Run from ai-module/: python inference.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests
from ultralytics import YOLO

import fall_detection
import inactivity
import proximity

# ============== CONFIG ==============
MODEL_PATH = "/Users/hamza/code/site-safe/ai-module/models/sitesafe_final.pt"
# The PPE model is trained only on equipment classes and has no person or
# vehicle class, so proximity and inactivity warnings need a second detector.
# The COCO-pretrained YOLOv11 nano weights supply person and vehicle boxes.
PROXIMITY_MODEL_PATH = "yolo11n.pt"
# Fall detection needs body keypoints, which a plain detection model does not
# emit, so it uses a third, independent model: the COCO-pretrained YOLO11
# nano *pose* weights.
FALL_MODEL_PATH = "yolo11n-pose.pt"
API_BASE = "http://127.0.0.1:8000/api"
ADMIN_EMAIL = "hamzahyaasin@gmail.com"
ADMIN_PASSWORD = "admin@sitesafe"
COOLDOWN_SECONDS = 15
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


def resolve_fall_model_path() -> Path:
    p = Path(FALL_MODEL_PATH)
    if p.is_absolute():
        return p
    return module_root() / p


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


def api_url(*parts: str) -> str:
    base = API_BASE.rstrip("/")
    return base + "/" + "/".join(parts)


def is_violation_class(name: str) -> bool:
    n = name.strip().lower()
    return n.startswith("no-") or n.startswith("no_")


def connect_api() -> tuple[requests.Session | None, bool]:
    """Return (session with Bearer set, online_ok)."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    try:
        r = session.post(
            api_url("token", ""),
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        token = data.get("access")
        if not token:
            print("API connection failed: no access token in response", file=sys.stderr)
            return session, False
        session.headers["Authorization"] = f"Bearer {token}"
        print("Connected to Site-Safe API")
        return session, True
    except Exception as exc:
        print(f"API connection failed ({exc}), running in offline mode", file=sys.stderr)
        session.headers.pop("Authorization", None)
        return session, False


def post_ppe_alert(
    session: requests.Session | None,
    online: bool,
    violation_label: str,
    confidence: float,
    camera_id: str,
) -> tuple[int | None, str]:
    """POST PPE violation alert. Returns (status_code, message)."""
    if not online or session is None:
        return None, "offline"

    payload = {
        "alert_type": "PPE_VIOLATION",
        "severity": "HIGH",
        "source": "AI_CAMERA",
        "description": f"Missing PPE: {violation_label} (conf: {confidence:.2f})",
        "camera_id": camera_id,
    }
    try:
        r = session.post(api_url("alerts", ""), json=payload, timeout=10)
        return r.status_code, r.text[:500]
    except Exception as exc:
        return None, str(exc)


def post_proximity_alert(
    session: requests.Session | None,
    online: bool,
    event: dict,
    camera_id: str,
) -> tuple[int | None, str]:
    """POST a vehicle proximity alert. Returns (status_code, message)."""
    if not online or session is None:
        return None, "offline"

    payload = {
        "alert_type": "VEHICLE_PROXIMITY",
        "severity": proximity.severity_for(event),
        "source": "AI_CAMERA",
        "description": proximity.describe(event),
        "camera_id": camera_id,
    }
    try:
        r = session.post(api_url("alerts", ""), json=payload, timeout=10)
        return r.status_code, r.text[:500]
    except Exception as exc:
        return None, str(exc)


def post_inactivity_alert(
    session: requests.Session | None,
    online: bool,
    event: dict,
    camera_id: str,
) -> tuple[int | None, str]:
    """POST a camera-level inactivity alert. Returns (status_code, message).

    The COCO detector provides no worker identity, so this intentionally leaves
    ``worker`` unset.  The camera id still lets the backend resolve the zone.
    """
    if not online or session is None:
        return None, "offline"

    payload = inactivity.alert_payload(event, camera_id)
    try:
        r = session.post(api_url("alerts", ""), json=payload, timeout=10)
        return r.status_code, r.text[:500]
    except Exception as exc:
        return None, str(exc)


def post_fall_alert(
    session: requests.Session | None,
    online: bool,
    event: dict,
    camera_id: str,
) -> tuple[int | None, str]:
    """POST a camera-level fall alert. Returns (status_code, message).

    As with inactivity, the pose model provides no worker identity, so this
    leaves ``worker`` unset; camera_id still lets the backend resolve a zone.
    """
    if not online or session is None:
        return None, "offline"

    payload = fall_detection.alert_payload(event, camera_id)
    try:
        r = session.post(api_url("alerts", ""), json=payload, timeout=10)
        return r.status_code, r.text[:500]
    except Exception as exc:
        return None, str(exc)


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


def draw_fps(frame: np.ndarray, fps: float) -> None:
    h, w = frame.shape[:2]
    text = f"FPS: {fps:.1f}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = w - tw - 12
    y = 28
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def draw_status_bar(
    frame: np.ndarray,
    violations: list[tuple[str, float]],
    proximity_event: dict | None = None,
    fall_fired_this_frame: bool = False,
) -> None:
    """Top-left status strip: green ALL CLEAR, or red naming what is wrong.

    A confirmed fall outranks everything else in the banner — a worker down
    is the most urgent condition this pipeline can raise. A proximity breach
    in turn outranks a plain PPE violation, since a worker beside moving
    plant is more immediate than a missing hardhat.
    """
    h, w = frame.shape[:2]
    bar_h = 44
    overlay = frame.copy()
    if fall_fired_this_frame:
        color = (0, 0, 220)  # BGR red-ish
        label = "FALL DETECTED"
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
        help="Consecutive evaluated frames a breach must hold before an alert "
        f"is raised (default: {proximity.DEFAULT_PERSISTENCE}). Filters out "
        "single-frame detection noise.",
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
    args = parser.parse_args()
    if args.inactivity_timeout <= 0:
        parser.error("--inactivity-timeout must be greater than zero")
    if args.inactivity_movement_threshold < 0:
        parser.error("--inactivity-movement-threshold must be zero or greater")
    if args.fall_persistence <= 0:
        parser.error("--fall-persistence must be greater than zero")
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

    session, online = connect_api()

    model = YOLO(str(model_path))

    coco_model = None
    proximity_tracker = None
    inactivity_tracker = None
    if not (args.no_proximity and args.no_inactivity):
        proximity_model_path = resolve_proximity_model_path()
        if proximity_model_path.is_file():
            coco_model = YOLO(str(proximity_model_path))
            if not args.no_proximity:
                proximity_tracker = proximity.ProximityTracker(
                    threshold=args.proximity_threshold,
                    persistence=args.proximity_persistence,
                )
                print(
                    f"[{camera_id}] vehicle proximity enabled "
                    f"(threshold {args.proximity_threshold} person-heights, "
                    f"confirm after {args.proximity_persistence} frames)"
                )
            if not args.no_inactivity:
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
    fall_tracker = None
    if not args.no_fall:
        fall_model_path = resolve_fall_model_path()
        if fall_model_path.is_file():
            pose_model = YOLO(str(fall_model_path))
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
    last_alert_time: dict[str, float] = {}
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
    t_start = time.perf_counter()
    fps_smooth = 0.0
    t_prev = time.perf_counter()

    print("Controls: Q quit | S force test alert | P pause/unpause")

    try:
        while True:
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
            t_now = time.perf_counter()
            dt = max(t_now - t_prev, 1e-6)
            t_prev = t_now
            fps_smooth = 0.9 * fps_smooth + 0.1 * (1.0 / dt)

            key = cv2.waitKey(1) & 0xFF
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
                print(f"[{'PAUSED' if paused else 'RESUME'}] detection")
            if key == ord("s"):
                forced = {
                    "alert_type": "PPE_VIOLATION",
                    "severity": "HIGH",
                    "source": "AI_CAMERA",
                    "description": "Manual test alert (forced via keyboard)",
                    "camera_id": camera_id,
                }
                if online and session:
                    try:
                        r = session.post(api_url("alerts", ""), json=forced, timeout=10)
                        code, body = r.status_code, r.text[:300]
                        if code == 201:
                            alerts_sent += 1
                        print(f"[ALERT] forced test → API response: {code}")
                    except Exception as exc:
                        print(f"[ALERT] forced test → API error: {exc}")
                else:
                    print("[ALERT] forced test skipped (offline mode)")

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
                cv2.imshow(window_title, frame)
                continue

            results = model.predict(frame, verbose=False, conf=0.15)
            result = results[0]
            names = result.names
            violations: list[tuple[str, float]] = []
            if result.boxes is not None and len(result.boxes) > 0:
                xyxy = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                clss = result.boxes.cls.cpu().numpy().astype(int)
                violations = plot_detections(frame, names, xyxy, confs, clss)

            # The shared COCO detector runs on a sampled subset of frames;
            # between samples the previous proximity result is reused for its
            # overlay, while inactivity timing uses the actual sample times.
            confirmed_proximity = None
            confirmed_inactivity: list[dict] = []
            if coco_model is not None and total_frames % PROXIMITY_FRAME_INTERVAL == 0:
                p_result = coco_model.predict(
                    frame, verbose=False, conf=PROXIMITY_CONF
                )[0]
                if p_result.boxes is not None and len(p_result.boxes) > 0:
                    p_xyxy = p_result.boxes.xyxy.cpu().numpy()
                    p_clss = p_result.boxes.cls.cpu().numpy().astype(int)
                    last_persons, last_vehicles = proximity.split_detections(p_xyxy, p_clss)
                else:
                    last_persons, last_vehicles = [], []

                if proximity_tracker is not None:
                    confirmed_proximity = proximity_tracker.update(last_persons, last_vehicles)
                    last_proximity_event = proximity.closest_proximity(
                        last_persons, last_vehicles, args.proximity_threshold
                    )
                if inactivity_tracker is not None:
                    confirmed_inactivity = inactivity_tracker.update(
                        last_persons, now=t_now
                    )

            # The pose model is an independent forward pass with its own
            # sampling interval — it does not share the COCO detector above.
            confirmed_fall: list[dict] = []
            if pose_model is not None and total_frames % FALL_FRAME_INTERVAL == 0:
                f_result = pose_model.predict(frame, verbose=False, conf=FALL_CONF)[0]
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

            if proximity_tracker is not None:
                draw_proximity(frame, last_persons, last_vehicles, last_proximity_event)
            if pose_model is not None:
                draw_poses(frame, last_poses, confirmed_fall)

            draw_status_bar(frame, violations, last_proximity_event, bool(confirmed_fall))
            draw_fps(frame, fps_smooth)

            if online and session and violations:
                for vname, vconf in violations:
                    last_t = last_alert_time.get(vname, 0.0)
                    if time.time() - last_t >= COOLDOWN_SECONDS:
                        code, body = post_ppe_alert(session, online, vname, vconf, camera_id)
                        last_alert_time[vname] = time.time()
                        if code == 201:
                            alerts_sent += 1
                            print(f"[ALERT] {vname} detected ({vconf:.2f}) → API response: {code}")
                        else:
                            print(f"[ALERT] {vname} detected ({vconf:.2f}) → API response: {code} {body[:200]}")

            if confirmed_proximity is not None:
                last_t = last_alert_time.get("VEHICLE_PROXIMITY", 0.0)
                if time.time() - last_t >= COOLDOWN_SECONDS:
                    last_alert_time["VEHICLE_PROXIMITY"] = time.time()
                    desc = proximity.describe(confirmed_proximity)
                    code, body = post_proximity_alert(
                        session, online, confirmed_proximity, camera_id
                    )
                    if code == 201:
                        alerts_sent += 1
                        proximity_alerts_sent += 1
                        print(f"[ALERT] {desc} → API response: {code}")
                    else:
                        print(f"[ALERT] {desc} → API response: {code} {body[:200]}")

            # The tracker itself latches each temporary person track until
            # movement re-arms it, so a second global cooldown would suppress
            # legitimate simultaneous events from different people.
            for event in confirmed_inactivity:
                desc = inactivity.describe(event)
                code, body = post_inactivity_alert(session, online, event, camera_id)
                if code == 201:
                    alerts_sent += 1
                    inactivity_alerts_sent += 1
                    print(f"[ALERT] {desc} → API response: {code}")
                else:
                    print(f"[ALERT] {desc} → API response: {code} {body[:200]}")

            # Same reasoning as inactivity above: FallTracker latches per
            # track, so no additional cooldown is applied here.
            for event in confirmed_fall:
                desc = fall_detection.describe(event)
                code, body = post_fall_alert(session, online, event, camera_id)
                if code == 201:
                    alerts_sent += 1
                    fall_alerts_sent += 1
                    print(f"[ALERT] {desc} → API response: {code}")
                else:
                    print(f"[ALERT] {desc} → API response: {code} {body[:200]}")

            cv2.imshow(window_title, frame)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        duration = time.perf_counter() - t_start
        print()
        print("=== Session summary ===")
        print(f"  Camera:                 {camera_id} ({source})")
        print(f"  Total frames processed: {total_frames}")
        print(f"  Total alerts sent:      {alerts_sent}")
        print(f"    of which proximity:   {proximity_alerts_sent}")
        print(f"    of which inactivity:  {inactivity_alerts_sent}")
        print(f"    of which fall:        {fall_alerts_sent}")
        print(f"  Session duration:       {duration:.1f}s")


if __name__ == "__main__":
    main()
