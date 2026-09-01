# Site-Safe — Handoff / Next Steps

> Paste this whole file into ChatGPT (or any other assistant) as context before asking it
> to do any task below. It is written so someone with **no prior knowledge of this repo**
> can act on it. This is revision 3 — see §0a for what changed since revision 1, §0b for
> what changed since revision 2.

---

## 0. Ground rules (read first — these are non-negotiable)

This project's report previously contained figures that the repository itself contradicted
(a claimed 93% mAP against an actual 54.4%, and a table of "passing" integration tests for
features that were never built). That has been corrected twice now — once by hand, once by
a ChatGPT/Codex session working from this document. **Do not reintroduce that class of error.**

1. **Never write a number into the report that you have not measured.** If you claim an
   accuracy, a latency, or a test result, there must be a command that reproduces it.
2. **Never mark something as tested/implemented unless it exists in code.** If it is designed
   but not built, it belongs in the Future Work section, not in a results table.
3. **State verification status explicitly.** "Verified against X" / "not yet verified against Y"
   is always better than an unqualified claim.
4. Follow the department SOP at `docs/Revised_FYP_SOP (1).pdf` for all formatting.
5. **The report is now edited programmatically, not by hand.** See §5. Any further report
   change should go through `docs/update_fyp_report.py`, not a one-off script or manual edit,
   so the whole revision history stays reproducible from the source `.docx`.

## 0a. What changed since revision 1 of this document

A ChatGPT/Codex session did the bulk of the work below, then ran out of usage credits with
three files drafted but two safety-guarded placeholders left empty on purpose (the build
script refuses to run without them — see §5). A follow-up session filled those in, fixed four
real bugs found during review (listed in the Task 2 commit message — `git log`), ran the full
pipeline, verified the output by rendering it to PDF and reading it, and shipped it. Everything
in old Tasks 1–2 is **done**. Old Task 3 is **prepared but not run** (needs a human at a Colab
GPU). Old Task 4's highest-priority item (inactivity detection) is **done**; fall detection is
not started. This revision replaces the old task list with what's actually left.

## 0b. What changed since revision 2 of this document

TASK B (fall detection) is now **done** — `ai-module/fall_detection.py`, wired into
`inference.py`, `AlertType.FALL` + migration, 24 new tests (59 total), and the report's
§4.3.4 rewritten from "Not Implemented" to the honest-implementation treatment via
`docs/update_fyp_report.py`. See §3 for what actually shipped and §5 for a schema-validation
gotcha found and fixed while rebuilding the report this round (real, pre-existing corruption
risk in the already-shipped `.docx` — read that before you next touch the report script).
TASK A (retraining) is still **not run** — it needs a human at a Colab GPU; nothing here can
do that step. TASK C (push/cleanup) is still outstanding.

---

## 1. Current state of the repository

**Path:** `/Users/hamza/code/site-safe`  **Branch:** `main`
**Git:** 5 commits ahead of `origin/main` — **not yet pushed**.

### Stack (actual, verified versions — also in report Table 4.1)

| Component | Version |
|---|---|
| Python | 3.14.3 |
| Django | 6.0.4 |
| Django REST Framework | 3.17.1 |
| PostgreSQL | 18.3 |
| Node.js | 25.8.1 |
| React / React DOM | 19.2.8 |
| Vite | 8.2.2 |
| Ultralytics | 8.4.41 |
| Tailwind CSS | 4.3.3 |

### Layout

```
backend/        Django REST API (accounts, alerts, workers, sitemap, reports)
frontend/       React + Vite + Tailwind dashboard (7 pages)
ai-module/      YOLO vision pipeline (inference.py, proximity.py, inactivity.py, fall_detection.py)
report-service/ Node.js .docx report generator
docs/           FYP report V7, department SOP, update_fyp_report.py (report build script)
```

### Run it

```bash
# backend  (from repo root)
.venv/bin/python backend/manage.py runserver 8000

# frontend
npm --prefix frontend run dev          # http://localhost:5173

# vision pipeline (from ai-module/)
../.venv/bin/python inference.py --source 0 --camera-id CAM-01

# full test suite — 59 tests, isolated SQLite, no PostgreSQL permission needed
cd backend && ../.venv/bin/python manage.py test --settings=sitesafe.test_settings
```

### What is genuinely built and working (all covered by the 59 automated tests)

- PPE detection pipeline (YOLO), posts alerts to the backend
- Multi-camera support: `--source` takes a webcam index **or** an RTSP/HTTP stream URL
- Camera→zone association (`Alert.camera_id`, `Zone.camera_ids`)
- Vehicle proximity detection (`ai-module/proximity.py` + a second COCO detector)
- **Camera-level inactivity detection** (`ai-module/inactivity.py`) — centroid tracker,
  timeout/movement/latch logic, wired into `inference.py`; tracks are camera-local, not
  worker identities (no QR yet, so there's no identity to attach)
- **Camera-level fall detection** (`ai-module/fall_detection.py`) — YOLO11 pose model,
  span-ratio + hip/knee geometry, persistence/latch/re-arm tracking (same shape as
  inactivity), wired into `inference.py`; also camera-local, not worker-identity-linked
- Role-based access control: Admin / Safety Officer / Viewer, enforced server-side
- Django REST backend, React dashboard, WebSocket live alerts, .docx report generation

### What is designed in the report but NOT built

QR worker identification · Fire/smoke detection ·
Mobile app (React Native) · Smart Vest hardware + LoRa · Celery/Redis ·
Map/GPS visualisation · Zone entry/exit correlation · Break detection · Hourly activity
aggregation

### Report structure (current, correct for FYP-II)

Ch1 Introduction · Ch2 Review of Existing Systems · Ch3 Proposed System Design ·
Ch4 Hardware and Software Implementation · **Ch5 Testing, Results and Discussion** ·
**Ch6 Conclusion and Future Work**. Every unbuilt Chapter 3 design is labelled
"Proposed... (Not Implemented)" at its Chapter 4 heading.

---

## 2. TASK A — Run the prepared retraining  *(needs a human + Colab GPU; nobody here has run it)*

`ai-module/train_sitesafe_yolo11m_colab.ipynb` is ready: YOLO11**m**, 150 epochs, 640px,
batch 16, early stopping, seeded, dataset-fingerprinted, refuses to overwrite an existing run.

### The problem it's trying to fix, measured on the CURRENT weights

Current: `ai-module/models/sitesafe_final.pt` — nano, 30 epochs, 416px, batch 4.
mAP@0.5 = 0.544 overall, but the negative (violation) classes are weak — this is the whole
point of the retrain:

| Class | mAP@0.5 | | Class | mAP@0.5 |
|---|---|---|---|---|
| boots | 0.981 | | **no-boots** | **0.175** |
| helmet | 0.942 | | **no-helmet** | **0.308** |
| gloves | 0.304 | | **no-gloves** | **0.095** |

### Steps

1. Open the notebook in Google Colab. Runtime → Change runtime type → **T4 GPU** (or better).
2. Upload `ai-module/ppe_dataset/` (or a zip of it) to Google Drive; edit `DATASET_SOURCE` in
   cell 2 to point at it.
3. Run all cells in order. Training can outlast one Colab session — if it disconnects,
   preserve the run directory; do not treat partial weights as a finished result.
4. Cell 7 runs the **mandatory** held-out test evaluation. Do not skip it.
5. Export via cell 8. Copy `best.pt` into `ai-module/models/`, update `MODEL_PATH` in
   `ai-module/inference.py`.
6. Feed the new measured numbers into `docs/update_fyp_report.py`'s `TABLE_45`-equivalent
   data and the `CHAPTER5_SECTIONS["5.3 Model Evaluation Results"]` text (currently states
   plainly that no retrain result is included yet — update that sentence too), then rebuild
   the report per §5 below. **Do not hand-edit the .docx for this — go through the script.**

---

## 3. TASK B — Fall detection — **DONE**

Built to the exact pattern already used twice (`ai-module/proximity.py`, `ai-module/inactivity.py`):
a dependency-free decision module (`ai-module/fall_detection.py`), unit-tested under
`backend/alerts/test_fall.py` via the same `sys.path` trick, wired into `inference.py`'s main
loop. What shipped, for anyone picking this up cold:

1. `yolo11n-pose.pt` (auto-downloaded by `ultralytics`) runs as a second sampled-frame model
   (every 3rd frame, `FALL_FRAME_INTERVAL`), same pattern as the proximity/inactivity COCO
   detector, with graceful degradation if the weights file is missing.
2. Geometric signal: horizontal/vertical keypoint-span ratio **and** hips-at-or-below-knees —
   `is_collapsed_posture()` requires **both**, so a wide arm-flung-out standing pose (span
   ratio alone would trip) doesn't false-positive.
3. Persistence + per-track latch/re-arm, same shape as `InactivityTracker` — a collapsed
   posture must hold for `DEFAULT_PERSISTENCE_SECONDS` (3.0s) before a FALL event fires, and
   won't fire again for the same track until the person is seen upright again first.
4. `AlertType.FALL` added to `backend/alerts/models.py`, migration
   `0007_alter_alert_alert_type_alter_alertconfig_alert_type.py` applied. Severity `CRITICAL`,
   source `AI_CAMERA`, no `worker` link (camera-local track, not a worker identity — no QR yet).
5. 24 new tests in `backend/alerts/test_fall.py` (geometry, tracker persistence/recovery/
   multi-person/stale-track eviction, alert API contract) — 59 total across the suite.
   Additionally hand-verified against real `yolo11n-pose.pt` inference on the Ultralytics
   bundled sample images (`zidane.jpg`, `bus.jpg`) before the tensor-handling code was written.
6. Report §4.3.4 rewritten from "Proposed Fall Detection via Pose Estimation (Not Implemented)"
   to a plain description of what's above, via `docs/update_fyp_report.py`
   (`replace_fall_detection_content` + `FALL_IMPLEMENTATION_PARAGRAPHS`) — not hand-edited.

**Known limitation, stated in the report itself:** no real fall footage has been tested
against — only synthetic keypoints and standing/sitting real-image inference. The geometry is
pixel-based and uncalibrated (no camera-distance normalisation), and a fall toward/away from
the camera risks self-occlusion the span-ratio signal won't catch. If real fall footage
becomes available, that's the next thing to validate against — see §4.3.4's limitations
paragraph for the exact wording already in the report.

Fire/smoke detection and the mobile app remain correctly deferred to Future Work (§6.2 of the
report) — do not attempt either for FYP-II.

---

## 4. TASK C — Push and clean up git state

- 5 commits sit unpushed on `main`. Push when ready: `git push origin main`
- Two merged branches can be deleted: `merge/ui-redesign`, `claude/site-safe-ui-ux-bgnNi`
- SOP requires **similarity index < 18%** — run the plagiarism check early; the report has
  grown substantially across multiple revisions.

---

## 5. How the report is edited now — READ BEFORE TOUCHING THE .docx

**Do not hand-edit `docs/SiteSafe_FYP_Report_V7.docx` and do not write a new ad-hoc XML script.**
Everything now goes through `docs/update_fyp_report.py`, which is idempotent and reproducible
from the source file. It has two passes:

```bash
# 1. build — content/structure edits, placeholder page numbers
.venv/bin/python docs/update_fyp_report.py build \
    docs/SiteSafe_FYP_Report_V7.docx /tmp/built.docx

# 2. render the build to PDF so real page numbers can be measured
soffice --headless --convert-to pdf --outdir /tmp /tmp/built.docx

# 3. finalize — reads the rendered PDF, patches the TOC / List of Figures / List of Tables
#    with the pages headings actually landed on
.venv/bin/python docs/update_fyp_report.py finalize \
    /tmp/built.docx /tmp/built.pdf /tmp/final.docx

# then copy /tmp/final.docx over docs/SiteSafe_FYP_Report_V7.docx
```

`soffice` (LibreOffice headless) must be installed: `brew install --cask libreoffice`.
Both `python-docx` and `pypdf` must be installed in the venv you run this with.

**Always render the result and actually look at it before shipping** — `pdftoppm -jpeg -r 110
-f <page> -l <page> final.pdf out` then view the images. Rendering caught two things that
schema validation alone would not: a table column-count mismatch, and every page number in
the TOC reading "1" because of an anchor bug (both fixed in the current script — but if you
add new content, re-verify by rendering, don't assume).

**If you extend the `replacements` dict inside `replace_chapter4_content`**: match apostrophes
exactly. The document uses curly apostrophes (`’`, U+2019); a straight `'` in your search key
will silently match zero paragraphs and `find_paragraph` will raise `AssertionError: found 0`
— which is at least loud. Quieter and worse: if two paragraphs in the report happen to share
an opening clause, a short/generic key will match both and raise `found 2`. When that happens,
extend the key with enough of the paragraph's actual continuation to be unique — don't shorten
someone else's disambiguation back down.

To add a new placeholder-guarded section (matching how `AUTOMATED_TEST_ROWS` and
`INACTIVITY_IMPLEMENTATION_PARAGRAPHS` work): declare it empty at the top of the file, raise
inside the function that consumes it if it's still empty, and only fill it in once you have
the real, reproducible evidence it describes. That guard is what stopped this report from
being rebuilt with placeholder numbers the first time around — keep using it.

**The script is not idempotent against its own output — always build from the true original.**
The `replacements` dict searches for pre-build placeholder text (e.g. old §4.3.4 wording). Once
the script has run once, the committed `.docx` no longer contains that text — it contains the
script's own prior output. Running `build` against the currently-committed file will fail with
`AssertionError: found 0` (or worse, silently match the wrong thing if old and new text overlap).
Get the true pre-restructure source with
`git show <last-hand-edited-or-known-good-commit>:docs/SiteSafe_FYP_Report_V7.docx > /tmp/original_source.docx`
and build from that, every time you extend the script with new replacements.

**Schema-order matters even though LibreOffice doesn't enforce it.** ECMA-376 requires strict
child-element ordering inside container elements like `w:tblPr` (`CT_TblPrBase`), `w:tcPr`
(`CT_TcPrBase`), and `w:pPr` (`CT_PPrBase`) — e.g. `w:tblInd` must come before `w:tblBorders`,
`w:tcW` before `w:tcBorders`, `w:spacing` before `w:ind`. Blindly `.append()`-ing a new element
onto a container that was `deepcopy`'d from an existing table/paragraph (which may already carry
later-in-sequence children) silently produces an invalid document — LibreOffice renders it fine,
but Word may respond with "unreadable content, do you want us to repair it?" on open. This bit
`set_table_geometry()` and `make_index_paragraph()` in a way that shipped undetected for at
least one prior revision, because nobody had run `scripts/office/validate.py` against the *true*
original — only against an already-corrupted intermediate baseline, which made the errors look
pre-existing-and-therefore-fine rather than a real defect. **Always run
`scripts/office/validate.py --original /tmp/original_source.docx` against the true original**,
not a previous build's output. If you need to append a new child element to a cloned `w:tblPr`
or `w:tcPr`, use the `insert_in_schema_order(parent, new_element, sequence)` helper (with the
`TBL_PR_ORDER` / `TC_PR_ORDER` constants) already in the script instead of `.append()` — it
walks existing children and inserts before the first one that belongs later in the schema.
