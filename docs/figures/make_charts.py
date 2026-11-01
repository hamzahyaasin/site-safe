#!/usr/bin/env python3
"""Draw the Chapter 5 result charts from the saved measurements.

Every value comes from a results file in the repository, never typed in, so
a chart cannot drift from the tables beside it:

- Figure 5.1: per-class mAP@0.5 of the deployed PPE weights on the held-out
  split (ai-module/models/sitesafe_v5_export/held_out_test_metrics.json)
- Figure 5.2: the confusion matrix of the same weights and split
  (held_out_confusion_matrix.json, from ai-module/scripts/held_out_confusion.py)
- Figure 5.3: end-to-end latency of the 1,431 probes of the two-hour soak
  (tools/measure/results/soak_20261022T174720.csv, Table 5.6)

    .venv/bin/python docs/figures/make_charts.py      # writes docs/figures/fig_*.png
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
PPE = REPO / "ai-module" / "models" / "sitesafe_v5_export"
SOAK_CSV = REPO / "tools" / "measure" / "results" / "soak_20261022T174720.csv"
SOAK_JSON = REPO / "tools" / "measure" / "results" / "soak_20261022T144721Z.json"

plt.rcParams.update({"font.family": "Arial", "font.size": 7.5, "axes.edgecolor": "#9ca3af", "axes.linewidth": 0.6})
INK = "#1f2937"
MUTED = "#6b7280"
GRID = "#e5e7eb"
PRESENT = "#2a78d6"  # categorical slot 1
MISSING = "#eb6834"  # categorical slot 2
BLUES = LinearSegmentedColormap.from_list("blues", ["#ffffff", "#cfe0f6", "#7aaee8", "#2a78d6", "#0d3f7a"])


def axes_style(ax, grid_axis):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis=grid_axis, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK, length=2.5, width=0.6)


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"  wrote {name}")


def per_class_map():
    metrics = json.loads((PPE / "held_out_test_metrics.json").read_text())
    rows = metrics["per_class"]
    # Pair each item with its "no-" class so the gap between them reads at a glance.
    items = [r["class_name"] for r in rows if not r["class_name"].startswith("no-")]
    by_name = {r["class_name"]: r for r in rows}
    fig, ax = plt.subplots(figsize=(6.0, 2.7))
    y = np.arange(len(items))
    h = 0.36
    for offset, prefix, color, label in ((-h / 2, "", PRESENT, "Item worn"), (h / 2, "no-", MISSING, "Item missing (alert class)")):
        values = [by_name[prefix + item]["map50"] for item in items]
        counts = [by_name[prefix + item]["test_instances"] for item in items]
        ax.barh(y + offset, values, height=h - 0.04, color=color, label=label)
        for yi, v, n in zip(y + offset, values, counts):
            ax.text(v + 0.012, yi, f"{v:.2f}  (n={n})", va="center", fontsize=6.6, color=INK)
    overall = metrics["overall"]["map50"]
    ax.axvline(overall, color=MUTED, lw=0.8, ls=(0, (3, 2)))
    ax.text(overall + 0.01, -0.62, f"all classes {overall:.3f}", ha="left", fontsize=6.6, color=MUTED)
    ax.set_yticks(y, [i.capitalize() for i in items])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.18)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_xlabel("mAP@0.5 on the held-out test split (n = test instances)", color=INK)
    axes_style(ax, "x")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, fontsize=6.8)
    save(fig, "fig_ppe_per_class_map.png")


def confusion_matrix():
    data = json.loads((PPE / "held_out_confusion_matrix.json").read_text())
    names = data["classes"]
    matrix = np.array(data["matrix"], dtype=float)  # [predicted][true]
    # Each column is one true class; normalise so a column shows where its instances went.
    totals = matrix.sum(axis=0, keepdims=True)
    share = np.divide(matrix, totals, out=np.zeros_like(matrix), where=totals > 0)
    share[:, -1] = 0  # background has no true instances to share out; its column holds false positives
    fig, ax = plt.subplots(figsize=(5.6, 4.9))
    ax.imshow(share, cmap=BLUES, vmin=0, vmax=1)
    for i in range(len(names)):
        for j in range(len(names)):
            count = int(matrix[i, j])
            if count:
                dark = share[i, j] > 0.55
                ax.text(j, i, str(count), ha="center", va="center", fontsize=6.2,
                        color="white" if dark else INK, weight="bold" if i == j else "normal")
    ax.set_xticks(range(len(names)), names, rotation=45, ha="right")
    ax.set_yticks(range(len(names)), names)
    ax.set_xlabel(f"True class (boxes at confidence {data['conf']}; shading: share of the column's instances)", color=INK)
    ax.set_ylabel("Predicted class", color=INK)
    ax.tick_params(colors=INK, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(names)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(names)), minor=True)
    ax.grid(which="minor", color="white", lw=1.2)
    ax.tick_params(which="minor", length=0)
    save(fig, "fig_ppe_confusion_matrix.png")


def soak_latency():
    with SOAK_CSV.open() as f:
        values = np.array([float(r["value"]) for r in csv.DictReader(f) if r["kind"] == "latency_ms"])
    summary = json.loads(SOAK_JSON.read_text())["end_to_end_ms"]
    assert len(values) == summary["n"], "Soak CSV and JSON describe different runs"
    limit = 100
    fig, ax = plt.subplots(figsize=(6.0, 2.4))
    ax.hist(values[values <= limit], bins=np.arange(10, limit + 2.5, 2.5), color=PRESENT, edgecolor="white", linewidth=0.6)
    top = ax.get_ylim()[1] * 1.12
    ax.set_ylim(0, top)
    for key, label in (("p50", "median"), ("p95", "95th percentile")):
        ax.axvline(summary[key], color=INK, lw=0.8, ls=(0, (3, 2)))
        ax.text(summary[key] + 1, top * 0.95, f"{label} {summary[key]:.1f} ms", fontsize=6.8, color=INK)
    over = int((values > limit).sum())
    ax.text(limit, top * 0.55, f"{over} probes above {limit} ms\n(max {summary['max']:.0f} ms)",
            ha="right", fontsize=6.8, color=MUTED)
    ax.set_xlim(10, limit)
    ax.set_xlabel(f"Event-to-dashboard latency (ms), {summary['n']:,} probes over two hours", color=INK)
    ax.set_ylabel("Probes", color=INK)
    axes_style(ax, "y")
    save(fig, "fig_soak_latency.png")


if __name__ == "__main__":
    per_class_map()
    confusion_matrix()
    soak_latency()
