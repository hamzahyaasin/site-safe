#!/usr/bin/env python3
"""
Site-Safe PPE: webcam YOLO inference with optional Django alert API integration.
Run from ai-module/: python inference.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests
from ultralytics import YOLO

# ============== CONFIG ==============
MODEL_PATH = "/Users/hamza/code/site-safe/ai-module/runs/detect/runs/train/sitesafe_ppe_fast/weights/best.pt"
API_BASE = "http://127.0.0.1:8000/api"
ADMIN_EMAIL = "hamzahyaasin@gmail.com"
ADMIN_PASSWORD = "admin@sitesafe"
COOLDOWN_SECONDS = 15
CAMERA_INDEX = 0
# ====================================


def module_root() -> Path:
    return Path(__file__).resolve().parent


def resolve_model_path() -> Path:
    p = Path(MODEL_PATH)
    if p.is_absolute():
        return p
    return module_root() / p


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
) -> tuple[int | None, str]:
    """POST PPE violation alert. Returns (status_code, message)."""
    if not online or session is None:
        return None, "offline"

    payload = {
        "alert_type": "PPE_VIOLATION",
        "severity": "HIGH",
        "source": "AI_CAMERA",
        "description": f"Missing PPE: {violation_label} (conf: {confidence:.2f})",
    }
    try:
        r = session.post(api_url("alerts", ""), json=payload, timeout=10)
        return r.status_code, r.text[:500]
    except Exception as exc:
        return None, str(exc)


def draw_fps(frame: np.ndarray, fps: float) -> None:
    h, w = frame.shape[:2]
    text = f"FPS: {fps:.1f}"
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = w - tw - 12
    y = 28
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)


def draw_status_bar(frame: np.ndarray, violations: list[tuple[str, float]]) -> None:
    """Top-left status strip: green ALL CLEAR or red with violation names."""
    h, w = frame.shape[:2]
    bar_h = 44
    overlay = frame.copy()
    if violations:
        color = (0, 0, 220)  # BGR red-ish
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


def main() -> None:
    os.chdir(module_root())
    model_path = resolve_model_path()
    if not model_path.is_file():
        print(f"Model not found: {model_path}", file=sys.stderr)
        sys.exit(1)

    session, online = connect_api()

    model = YOLO(str(model_path))
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Could not open camera index {CAMERA_INDEX}", file=sys.stderr)
        sys.exit(1)

    last_alert_time: dict[str, float] = {}
    paused = False
    total_frames = 0
    alerts_sent = 0
    t_start = time.perf_counter()
    fps_smooth = 0.0
    t_prev = time.perf_counter()

    print("Controls: Q quit | S force test alert | P pause/unpause")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
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
                print(f"[{'PAUSED' if paused else 'RESUME'}] detection")
            if key == ord("s"):
                forced = {
                    "alert_type": "PPE_VIOLATION",
                    "severity": "HIGH",
                    "source": "AI_CAMERA",
                    "description": "Manual test alert (forced via keyboard)",
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
                cv2.imshow("Site-Safe PPE Inference", frame)
                continue

            results = model.predict(frame, verbose=False, conf=0.25)
            result = results[0]
            names = result.names
            violations: list[tuple[str, float]] = []
            if result.boxes is not None and len(result.boxes) > 0:
                xyxy = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                clss = result.boxes.cls.cpu().numpy().astype(int)
                violations = plot_detections(frame, names, xyxy, confs, clss)

            draw_status_bar(frame, violations)
            draw_fps(frame, fps_smooth)

            if online and session and violations:
                for vname, vconf in violations:
                    last_t = last_alert_time.get(vname, 0.0)
                    if time.time() - last_t >= COOLDOWN_SECONDS:
                        code, body = post_ppe_alert(session, online, vname, vconf)
                        last_alert_time[vname] = time.time()
                        if code == 201:
                            alerts_sent += 1
                            print(f"[ALERT] {vname} detected ({vconf:.2f}) → API response: {code}")
                        else:
                            print(f"[ALERT] {vname} detected ({vconf:.2f}) → API response: {code} {body[:200]}")

            cv2.imshow("Site-Safe PPE Inference", frame)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        duration = time.perf_counter() - t_start
        print()
        print("=== Session summary ===")
        print(f"  Total frames processed: {total_frames}")
        print(f"  Total alerts sent:      {alerts_sent}")
        print(f"  Session duration:       {duration:.1f}s")


if __name__ == "__main__":
    main()
