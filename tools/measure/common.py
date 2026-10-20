"""Shared helpers for the Site-Safe measurement scripts.

Every script records *what was measured, how, and on what*: sample counts,
percentiles, the machine, the git commit and the exact settings. A result
without that context cannot support a claim in the report.

Measurement traffic uses a camera token created with ``--simulator``, so
the alerts it creates are marked SIMULATED and stay out of report figures.
"""

from __future__ import annotations

import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
REPO = Path(__file__).resolve().parents[2]


def percentile(values: list[float], p: float) -> float | None:
    """Linear-interpolated percentile, p in [0, 1]."""
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def summarise(values: list[float]) -> dict:
    """Count, mean, p50/p95/p99 and max of a list of measurements."""
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
        "min": min(values),
    }


def environment() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    info = {
        "machine": platform.machine(),
        "processor": platform.processor(),
        "system": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "git_commit": git("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
    }
    try:
        import psutil

        info["cpu_count"] = psutil.cpu_count(logical=True)
        info["memory_gb"] = round(psutil.virtual_memory().total / 1024**3, 1)
    except ImportError:
        pass
    if platform.system() == "Darwin":
        try:
            info["cpu"] = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        except Exception:  # noqa: BLE001
            pass
    return info


def save_result(name: str, data: dict, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{name}_{stamp}.json"
    payload = {
        "measurement": name,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "environment": environment(),
        **data,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def env_or(value: str | None, name: str) -> str:
    value = value or os.environ.get(name, "")
    if not value:
        raise SystemExit(f"Set {name} or pass it as an argument.")
    return value


def login(api: str, email: str, password: str) -> str:
    import requests

    r = requests.post(f"{api.rstrip('/')}/token/", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["access"]


def camera_event(camera_id: str, label: str) -> dict:
    """A camera event payload for measurement traffic (send with a simulator token)."""
    return {
        "event_id": str(uuid.uuid4()),
        "camera_id": camera_id,
        "alert_type": "PPE_VIOLATION",
        "severity": "LOW",
        "description": f"[measurement] {label}",
        "confidence": 0.5,
    }


def socket_url(api: str, access_token: str) -> str:
    base = api.rstrip("/")
    if base.endswith("/api"):
        base = base[: -len("/api")]
    return base.replace("http", "ws", 1) + f"/ws/dashboard/?token={access_token}"


def now() -> float:
    return time.perf_counter()
