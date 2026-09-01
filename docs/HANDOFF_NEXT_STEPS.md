# Site-Safe — Handoff / Next Steps

> Paste this whole file into ChatGPT as context before asking it to do any task below.
> It is written so someone with **no prior knowledge of this repo** can act on it.

---

## 0. Ground rules (read first — these are non-negotiable)

This project's report previously contained figures that the repository itself contradicted
(a claimed 93% mAP against an actual 54.4%, and a table of "passing" integration tests for
features that were never built). That has been corrected. **Do not reintroduce that class of error.**

1. **Never write a number into the report that you have not measured.** If you claim an
   accuracy, a latency, or a test result, there must be a command that reproduces it.
2. **Never mark something as tested/implemented unless it exists in code.** If it is designed
   but not built, it belongs in the Future Work section, not in a results table.
3. **State verification status explicitly.** "Verified against X" / "not yet verified against Y"
   is always better than an unqualified claim.
4. Follow the department SOP at `docs/Revised_FYP_SOP (1).pdf` for all formatting.

---

## 1. Current state of the repository

**Path:** `/Users/hamza/code/site-safe`  **Branch:** `main`
**Git:** 12 commits ahead of `origin/main` — **not yet pushed**.

### Stack (actual, verified versions)

| Component | Version |
|---|---|
| Python | 3.14.3 |
| Django | 6.0.4 |
| Django REST Framework | 3.17.1 |
| PostgreSQL | 18.3 |
| Node.js | 25.8.1 |
| React | 19.2.5 |
| Vite | 8.0.10 |
| Ultralytics | 8.4.41 |
| Tailwind CSS | 4.3.0 |

### Layout

```
backend/        Django REST API (accounts, alerts, workers, sitemap, reports)
frontend/       React + Vite + Tailwind dashboard (7 pages)
ai-module/      YOLO vision pipeline (inference.py, proximity.py)
report-service/ Node.js .docx report generator
docs/           FYP report V7 + department SOP
```

### Run it

```bash
# backend  (from repo root)
.venv/bin/python backend/manage.py runserver 8000

# frontend
npm --prefix frontend run dev          # http://localhost:5173

# vision pipeline (from ai-module/)
../.venv/bin/python inference.py --source 0 --camera-id CAM-01

# tests  (MUST cd into backend/ first, or discovery finds nothing)
cd backend && ../.venv/bin/python manage.py test
```

### What is genuinely built and working

- PPE detection pipeline (YOLO), posts alerts to the backend
- Multi-camera support: `--source` takes a webcam index **or** an RTSP/HTTP stream URL
- Camera→zone association (`Alert.camera_id`, `Zone.camera_ids`)
- Vehicle proximity detection (second COCO detector + geometry in `ai-module/proximity.py`)
- Role-based access control: Admin / Safety Officer / Viewer, enforced server-side
- 16 automated tests (all passing) in `backend/accounts/tests.py`
- Django REST backend, React dashboard, WebSocket live alerts, .docx report generation

### What is designed in the report but NOT built

QR worker identification · Fall detection (pose) · Fire/smoke detection ·
Mobile app (React Native) · Smart Vest hardware + LoRa · Celery/Redis ·
Map/GPS visualisation · Automatic inactivity & break detection

---

## 2. TASK 1 — Restructure report chapters for FYP-II  *(do this first)*

**Why:** The FYP-II grading rubric in the SOP explicitly awards marks for
`Chapter 5: Testing Results & discussion` and `Chapter 6: Conclusion & Future works`.
The report currently has Chapters 1–4 plus a **Chapter 5 named "Conclusion and Future Work"**.
That numbering will lose marks.

**Required end state:**

| Chapter | Title |
|---|---|
| 1 | Introduction |
| 2 | Review of Existing Systems |
| 3 | Proposed System Design |
| 4 | Hardware and Software Implementation |
| **5** | **Testing, Results and Discussion**  ← NEW |
| **6** | **Conclusion and Future Work**  ← rename existing Ch5 |

**Steps:**

1. Rename existing `Chapter 5 / Conclusion and Future Work` → `Chapter 6`.
   Update its internal headings `5.1 Conclusion` → `6.1`, `5.2 Future Work` → `6.2`.
2. Find and update **all cross-references** to `Section 5.2` → `Section 6.2`
   (there are 2, both in Chapter 4 — one in §4.3.3, one in §4.11).
3. Create a new **Chapter 5: Testing, Results and Discussion**. Move/expand the content
   currently in §4.11 (Integration Testing) into it. It should contain:
   - **5.1 Testing Approach** — three tiers: automated tests, model evaluation, manual end-to-end
   - **5.2 Automated Test Results** — the 16 RBAC tests + proximity unit tests. Reproduce with
     `cd backend && ../.venv/bin/python manage.py test`
   - **5.3 Model Evaluation Results** — reference Table 4.6; discuss the presence-vs-absence gap
   - **5.4 End-to-End Verification** — the existing Table 4.10 content
   - **5.5 Discussion** — what the results mean, where the system is weak, threats to validity
4. Update the Table of Contents, List of Tables and List of Figures accordingly.

---

## 3. TASK 2 — Correct the remaining report tables

These are still wrong. All replacement values below are **verified**.

### Table 4.1 — Development Environment

| Row | Report says | Change to |
|---|---|---|
| Python | 3.11 | **3.14.3** |
| Django | 4.2 LTS | **6.0.4** |
| DRF (ref [10]) | 3.14 | **3.17.1** |
| PostgreSQL | 15.4 | **18.3** |
| Node.js | 18 LTS | **25.8.1** |
| React | 18.2 | **19.2.5** |
| Vite | 5.0 | **8.0.10** |
| Ultralytics | 8.1 | **8.4.41** |
| React Native | 0.73 | **DELETE THE ROW** — no mobile app exists in the repo |
| Docker | 24.0 "container orchestration for deployment" | Soften: only `report-service/Dockerfile` exists; there is no docker-compose |
| Mosquitto | 2.0 | Soften: `backend/sitesafe/mqtt.py` exists but `start_mqtt_listener()` **is never called** — it is currently dead code |

Also **add** rows for: Tailwind CSS 4.3.0, Django Channels 4.3.2, Daphne 4.2.3.

### Table 4.7 — Core API Endpoints

| Report claims | Actual route |
|---|---|
| `POST /api/auth/login/` | `POST /api/token/` |
| `POST /api/auth/refresh/` | `POST /api/token/refresh/` |
| `GET/POST /api/workers/` | correct as-is |
| `GET /api/workers/{id}/location/` | **does not exist** — GPS lives on `/api/v1/vests/` |
| `GET/POST /api/detections/` | `/api/v1/detections/` |
| `GET /api/alerts/` | correct as-is |
| `GET/PUT /api/alerts/config/` | `/api/v1/alert-config/` |
| `GET/POST /api/zones/` | `/api/v1/zones/` |
| `GET /api/activity/summary/` | `/api/v1/activity/summary/?worker_id=&date=` |
| `GET /api/activity/worker/{id}/` | **does not exist** — only query-param filtering on the list endpoint |
| `POST /api/reports/generate/` | `/api/v1/reports/generate/` |
| `POST /api/notifications/register/` | `/api/v1/fcm-tokens/` |

**Add these real endpoints that are missing from the table:**
`/api/dashboard/stats/` · `/api/alerts/{id}/resolve/` · `/api/alerts/simulate/` ·
`/api/alerts/ingest/` · `/api/v1/vests/` · `/api/v1/vests/telemetry/` · `/api/v1/profile/` ·
`/api/v1/profile/change-password/` · `/api/v1/reports/` · `/api/v1/reports/{id}/download/`

### Table 4.8 — Database Schema

| Report claims | Reality |
|---|---|
| `workers.qr_code` | **does not exist** — the field is `vest_id` |
| `workers.status` | field is `is_active` |
| `smart_vests.mac_address` | field is `vest_id` |
| `smart_vests.firmware_ver` | field is `firmware_version` |
| `vitals` table | **DOES NOT EXIST AT ALL** — delete the row. GPS/SOS live on `smart_vests` |
| `detections.image` | **does not exist** — only a `bbox` JSON field |
| `cameras` table (implied by "FK: cameras") | **does not exist** — cameras are string ids, not a table |
| `zones.polygon_coords` | field is `boundaries` |
| `activity_logs.entry_ts/exit_ts/status` | actually `action` (TextChoices) + single `timestamp` + `metadata` JSON |
| `alert_config.notify_roles` | **does not exist** — it is `notify_email` / `notify_push` |
| `fcm_tokens.device_token` | field is `token`; there is **no** `platform` field (there is `device_name`) |

**Add rows that are missing:** `reports`, `user_preferences`.
**Add newly-created fields:** `alerts.camera_id`, `zones.camera_ids`, `users.role`.

### AlertType enum — current actual values

`PPE_VIOLATION`, `SOS`, `ZONE_BREACH`, `INACTIVITY`, `VEHICLE_PROXIMITY`

The report mentions `FALL`, `FIRE`, `SMOKE` in Chapters 1 and 3. Those are **not** in the enum.
Keep them in Chapter 3 (design) but make sure Chapters 4–6 do not imply they are implemented.

---

## 4. TASK 3 — Retrain the PPE model  *(highest technical value)*

### The problem, measured

Current weights: `ai-module/models/sitesafe_final.pt` — a **nano** model, 30 epochs, 416px, batch 4.
Measured on the held-out test split: **mAP@0.5 = 0.544**.

The per-class breakdown shows the real issue — the model finds equipment that is **present**
but misses equipment that is **absent**, which is the entire point of violation detection:

| Class | mAP@0.5 | | Class | mAP@0.5 |
|---|---|---|---|---|
| boots | 0.981 | | **no-boots** | **0.175** |
| vest | 0.956 | | **no-vest** | 0.737 |
| helmet | 0.942 | | **no-helmet** | **0.308** |
| goggles | 0.526 | | no-goggles | 0.414 |
| gloves | 0.304 | | **no-gloves** | **0.095** |

### Goal

Raise the negative-class scores. Those drive the product's core function.

### How

Train on Google Colab with a GPU (dataset is at `ai-module/ppe_dataset/`, 5,140 images, 10 classes):

```python
from ultralytics import YOLO
model = YOLO("yolo11m.pt")        # was yolo11n — step up to medium
model.train(
    data="ppe_dataset/data.yaml",
    epochs=150,                    # was 30
    imgsz=640,                     # was 416
    batch=16,                      # was 4
    patience=25,                   # enable early stopping
    optimizer="AdamW",
    lr0=0.001,
    project="runs/train", name="sitesafe_v5",
)
```

If negative classes remain weak after this, the next lever is **class imbalance** — count the
label instances per class in `ppe_dataset/train/labels/` and consider oversampling images that
contain negative classes, or class weighting.

### After training — MANDATORY

1. Copy the new `best.pt` to `ai-module/models/`, update `MODEL_PATH` in `ai-module/inference.py`.
2. **Re-measure on the test split** and update Table 4.6 + §4.3.3 with the new real numbers:

```python
from ultralytics import YOLO
m = YOLO("models/<new_best>.pt")
r = m.val(data="ppe_dataset/data.yaml", split="test", imgsz=640)
print(r.box.map50, r.box.map)                    # overall
for i, c in enumerate(r.box.ap_class_index):     # per class
    print(m.names[int(c)], r.box.p[i], r.box.r[i], r.box.ap50[i])
```

3. Also update Table 4.5 (hyperparameters) to the config you actually ran.

**Do not update the report with expected/hoped-for numbers. Only measured ones.**

---

## 5. TASK 4 — Phase 3: close the code/report gap

For each unbuilt feature, make an explicit **build vs. defer** decision and make the report match.

| Feature | Effort | Recommendation |
|---|---|---|
| **Inactivity / break detection** | Low–Med | **BUILD.** Model + endpoints already exist; only the detection half is missing. Track bounding-box centroid displacement over a rolling window in `inference.py`; raise `INACTIVITY` when displacement stays under a threshold past a timeout. Biggest win per hour. |
| **Fall detection (pose)** | Medium | **BUILD if time allows.** `yolo11n-pose.pt` auto-downloads. Mirror the exact pattern in `ai-module/proximity.py`: separate testable module, sampled frames, persistence filter. Needs a new `FALL` AlertType + migration. |
| **QR worker identification** | Medium | **DEFER or build minimally.** Needs `Worker.qr_code` field, QR generation in the dashboard, and `cv2.QRCodeDetector` in the pipeline. Note: helmets occlude QR at angle/distance. |
| **Fire/smoke detection** | High | **DEFER.** Requires sourcing and training another model. Keep in Chapter 3 design + Future Work. |
| **Mobile app** | Very High | **DEFER.** Do not attempt for FYP-II. Move the whole of §3.6 and Table 4.9 into Future Work framing. |
| **Smart Vest hardware / LoRa** | High (needs hardware) | **DEFER.** Be explicit that the vest is a backend model + dashboard simulator. **Figure 4.1 "Smart Vest Hardware Implementation" and Tables 4.2/4.3 (component specs, GPIO pins) have no artefact backing them — either build the hardware or reframe them as a proposed design.** |

Also still outstanding: the report references **15 figures but only 12 images are embedded** —
at least 3 captions have no figure. Audit and fix.

---

## 6. How to edit the .docx safely

The report is `docs/SiteSafe_FYP_Report_V7.docx`. Editing method that works:

```bash
cd /tmp && mkdir work && cd work
cp /Users/hamza/code/site-safe/docs/SiteSafe_FYP_Report_V7.docx original.docx
unzip -q original.docx -d unpacked/
# edit unpacked/word/document.xml  — do NOT reformat or pretty-print it
python3 -c "import xml.dom.minidom as m; m.parse('unpacked/word/document.xml')"   # must parse
cd unpacked && zip -Xrq ../updated.docx . -x '.*'
```

Then render to check it visually before shipping:

```bash
soffice --headless --convert-to pdf updated.docx
pdftoppm -jpeg -r 120 -f <page> -l <page> updated.pdf page
```

**Critical gotchas:**
- Search for text in the **body**, not the front matter — every table caption appears twice
  (once in the List of Tables, once at the table). Search from a large offset to skip the TOC.
- **Assert occurrence counts before replacing.** e.g. `"16"` appears 6+ times as a table cell
  value; a blind replace corrupts unrelated tables. Scope replacements to the cell after a
  known label.
- Match the document's existing styles: `<w:pStyle w:val="Heading2"/>` for `x.y` headings,
  `Heading3` for `x.y.z`, body paragraphs use
  `<w:spacing w:after="120" w:lineRule="auto"/><w:jc w:val="both"/>`.
- Chapter separator pages use centred bold runs at `w:sz 36` (18pt, chapter number) and
  `w:sz 44` (22pt, chapter title) — this matches the SOP requirement.
- The document uses **curly apostrophes** (’) — match that, don't mix in straight ones.

---

## 7. Suggested order

1. **Task 1** — chapter restructure (fast, directly graded)
2. **Task 2** — table corrections (mechanical, all values supplied above)
3. **Task 3** — retrain (long-running; start the Colab job early and let it run)
4. **Task 4** — build inactivity detection, then fall detection if time allows
5. Re-measure, update Tables 4.5/4.6, finalise Chapter 5

## 8. Housekeeping

- 12 commits sit unpushed on `main`. Push when ready: `git push origin main`
- Two merged branches can be deleted: `merge/ui-redesign`, `claude/site-safe-ui-ux-bgnNi`
- SOP requires **similarity index < 18%** — run the plagiarism check early, the report has
  grown substantially.
- SOP requires Times New Roman 12pt / 1.5 line spacing. The document currently declares **no**
  font explicitly (theme default is Calibri; LibreOffice renders a serif). Worth setting
  explicitly before final submission.
