# Site-Safe

Site-Safe is a construction site safety monitoring system. It combines a **Django REST API** and **PostgreSQL** backend, a **React** dashboard, and a **YOLOv10** computer-vision module that detects PPE violations from a webcam and pushes alerts into the platform.

## Architecture

```
┌─────────────────┐     JWT REST API      ┌──────────────────┐
│  React (Vite)   │ ◄────────────────────►│  Django backend  │
│  localhost:5173 │                       │  localhost:8000  │
└─────────────────┘                       └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │   PostgreSQL     │
                                          └──────────────────┘

┌─────────────────┐     POST /api/alerts/ ┌──────────────────┐
│  ai-module      │ ──────────────────────►│  Django backend  │
│  (webcam YOLO)  │                        └──────────────────┘
└─────────────────┘
```

| Layer | Stack | Purpose |
|-------|-------|---------|
| `frontend/` | React 19, Vite, React Router, Recharts | Dashboard, alerts, worker management |
| `backend/` | Django 6, DRF, SimpleJWT, PostgreSQL | Auth, alerts, workers, dashboard stats |
| `ai-module/` | Ultralytics YOLOv10, OpenCV | PPE detection and alert ingestion |

## Prerequisites

- **Python** 3.12+ (required for Django 6)
- **Node.js** 18+ and npm
- **PostgreSQL** 14+
- **Webcam** (optional, for live PPE inference)

## Project structure

```
site-safe/
├── backend/          # Django API
├── frontend/         # React dashboard
├── ai-module/        # YOLO training & webcam inference
│   ├── ppe_dataset/  # YOLO dataset (images not in git)
│   ├── models/       # Trained weights (not in git — add locally)
│   └── scripts/      # Training & inference utilities
└── docs/             # Project documentation
```

---

## 1. Database setup

Create a PostgreSQL database and user (adjust names/passwords as needed):

```bash
psql postgres
```

```sql
CREATE USER sitesafe WITH PASSWORD 'sitesafe';
CREATE DATABASE sitesafe OWNER sitesafe;
GRANT ALL PRIVILEGES ON DATABASE sitesafe TO sitesafe;
\q
```

---

## 2. Backend setup

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your SECRET_KEY and database credentials

python manage.py migrate
python manage.py createsuperuser
```

`createsuperuser` prompts for an **email** and password (not a username). Use these credentials to log in to the dashboard.

Apply migrations (they also seed one default alert rule per alert type), then start the ASGI server. `daphne` serves both HTTP and the dashboard websocket; `runserver` also works for development because `daphne` is installed as an app.

```bash
python manage.py migrate
daphne -b 127.0.0.1 -p 8000 sitesafe.asgi:application
```

The API runs at **http://127.0.0.1:8000/**.

### Device tokens (cameras and vest gateways)

Cameras and the vest gateway never log in as a person. Each gets a device token that can only post its own kind of data:

```bash
python manage.py create_service_token CAM-01 --kind CAMERA --camera-id CAM-01
python manage.py create_service_token gateway-1 --kind VEST_GATEWAY
```

The key is printed once; only its hash is stored. Revoke a token in Django admin (**Service tokens → untick Active**). Producers send it as `Authorization: Device <key>`.

### MQTT consumer (vest telemetry)

```bash
python manage.py run_mqtt_consumer
```

Run it alongside the ASGI server. When they are separate processes, set `REDIS_URL` so live updates from vests reach dashboard websockets.

### Vest presence monitor

```bash
python manage.py run_presence_monitor
```

A vest counts as online only while it keeps reporting. If it is silent for longer than `VEST_OFFLINE_AFTER_SECONDS` (default 120), the API shows it as offline even without this process. The monitor records the change and pushes it to open dashboards every 30 seconds.

### Vest simulator (no hardware)

The physical Smart Vest is proposed future work (see `docs/SCOPE_CHANGE_SMART_VEST.md`). To demonstrate the vest features, the simulator sends the same telemetry a vest gateway would:

```bash
python manage.py create_service_token vest-sim --kind VEST_GATEWAY --simulator
SITESAFE_DEVICE_KEY=ss_... python tools/vest_simulator.py tools/vest_scenarios/demo.json --speedup 5
```

Register the scenario's vests and assign them to workers first. Each vest walks its waypoints. A vest can press SOS on reaching a given waypoint (`sos_at`) or go silent after one (`stop_at`) to show offline detection. Everything sent with a `--simulator` token is marked SIMULATED: it is labelled in the dashboard and app and excluded from report figures. `--dry-run` prints the messages without sending them.

### Zones and automatic breaches

Draw zone boundaries on the map on the **Zones** page (Admin only). Vest GPS positions then produce zone entry/exit history and automatic **ZONE_BREACH** alerts in two cases:

- A worker enters a RESTRICTED zone that is not their assigned zone.
- An entry takes a zone above its maximum occupancy.

Where zones overlap, the highest-risk zone wins. Occupancy counts only workers whose vests are online. Camera-only zones have no boundary, so they have no GPS presence.

### Worker attendance and idle time

Attendance is recorded automatically from evidence that a worker is on site:

- their vest reporting;
- a camera reading their QR badge. Cameras send at most one sighting per badge per minute.

The first evidence opens a session. The session closes once the worker has not been seen for `CHECKOUT_AFTER_MINUTES` (default 30), at the time they were last seen. That close is done by `run_presence_monitor`. Idle time is recorded when an identified worker stays still in camera view past the inactivity timeout, and ends when they move again. This happens even if INACTIVITY alerts are switched off.

Camera events carry the time they happened, so the outbox can deliver them late without distorting the records. Simulator data never enters attendance. The Workers page shows each worker's day as a timeline, and the safety-performance report lists attendance per worker and per day. Workers with no vest and no readable badge have no attendance evidence; they are shown as unknown, never as absent.

### Fire and smoke detection, hot-work permits

The camera pipeline runs a fire/smoke detector when `ai-module/models/fire_smoke.pt` exists. Train it with `ai-module/fire/train_fire_smoke_colab.ipynb`, or with `ai-module/fire/train_fire_smoke_kaggle.ipynb`, which runs unattended as a Kaggle *Save & Run All* version and stops before the 12-hour session limit, on a dataset you are licensed to use. The current weights (D-Fire, YOLO11s) and their held-out metrics are in `ai-module/models/fire_smoke_v1_export/`. If your copy of D-Fire is the Parquet mirror (for example on Hugging Face), convert it first with `python fire/unpack_parquet_dataset.py --parquet <folder> --out fire/datasets/D-Fire --classes smoke,fire`. To train on this machine instead, run `python fire/train_fire_local.py --data fire/datasets/fire_v1/data.yaml --hours 9 --install`, which uses the same recipe and writes the same export folder. Prepare the dataset with `ai-module/fire/prepare_fire_dataset.py`, which remaps classes, keeps clip frames in one split, keeps negatives, and leaves out images with broken labels. An alert needs fire or smoke to persist for 2 s (`--fire-persistence`). Afterwards the camera stays quiet until the scene has been clear for 30 s.

The server sets the severity:

| Situation | FIRE | SMOKE |
|---|---|---|
| No active hot-work permit for the camera's zone | Critical | High |
| Active permit (Zones page) | Medium, linked to the permit | Low, linked to the permit |

A permit never hides fire, and FIRE alerts cannot be disabled in Settings. Safety Officers issue permits for up to 12 hours and can revoke them early. Set `TIME_ZONE` (for example `Asia/Karachi`) so permit times written into alerts use local time.

### QR worker badges

On the **Workers** page, edit a worker and choose **Print badge**. The QR code encodes only a random code (`SSW1:…`), never a name or phone number. Print it at 100% scale (60 mm) and wear it on the helmet front or chest. **Reissue badge** revokes every earlier printout.

A camera reads badges on the sampled frames and links each one to the person box that contains it. A PPE, fall or inactivity alert for that person is then attributed to the worker. A badge that is ambiguous (overlapping people), unreadable or revoked leaves the alert unidentified. The camera never guesses. Disable reading with `--no-qr`. People are still followed without badges whenever the person detector runs, so each person's PPE violations stay one alert per item even as they move.

### Alert evidence: snapshots and model version

Each AI camera alert records the weights that raised it (`model_version`, for example `sitesafe_v5.pt@1a2b3c4d5e6f`: the file name and the first 12 hex digits of its SHA-256), so an incident can be traced to the exact model even after a retrain under the same name. It also carries a snapshot: the raw frame that confirmed the event, without overlays, scaled to at most 640 px and saved as a JPEG of about 30–80 KB. The snapshot is stored in the camera's outbox with the event, so it survives an outage the same way.

The camera sends the snapshot base64-encoded in the JSON body (`snapshot`), not as a multipart upload, so the outbox replays one self-contained document. The API accepts only a JPEG of at most 512 KB and 4096 px per side. It stores the file under `MEDIA_ROOT/alert_snapshots/` with a random name. A retried or duplicate `event_id` never stores a second image. The alert's `snapshot` field holds the path `/api/alerts/{id}/snapshot/`, which serves the image only to signed-in users, with the same roles that can read the alert. The incident detail on the web and the alert screen on mobile show it. Media files are never served publicly when `DEBUG=False`.

Privacy controls:

- **Turn snapshots off.** Do it at the camera with `--no-snapshots` or `SITESAFE_SNAPSHOTS=0`, and the image never leaves the host. Do it at the server with `ALERT_SNAPSHOTS_ENABLED=False`, and incoming images are discarded. Either way, the confidence and model version are still recorded.
- **Retention.** `python manage.py purge_alert_snapshots` deletes images older than `ALERT_SNAPSHOT_RETENTION_DAYS` (default 30). It keeps the alerts themselves. Add `--days N` to override the period, or `--dry-run` to only count. Schedule it daily, for example with cron: `0 3 * * * cd /app && python manage.py purge_alert_snapshots`. Deleting an alert also deletes its image.

### Worker location and zone head counts

Workers are located without a vest too. When a camera reads a worker's QR badge, the worker is placed in that camera's zone (assign cameras to zones on the Zones page; a camera belongs to one zone). Cameras repeat sightings every 15 s. A location counts as current for `CAMERA_PRESENCE_SECONDS` (60) after the last sighting, or while the vest is online for vest GPS. After that the worker is "last seen" there, and the presence monitor records the zone exit, dated to the last sighting. Zone entries and exits appear in the worker's timeline whichever source produced them. A recent camera sighting takes precedence over GPS, so a worker near a zone edge is not flipped back and forth.

Each camera also reports how many people it sees, at most every 5 s. A zone's head count is the larger of two figures: the identified workers placed there, and its cameras' counts. With the zone setting **"These cameras can see the same people"** (the default) the largest single camera count is used, which never double-counts; turned off, the counts are added. A count older than `CAMERA_COUNT_STALE_SECONDS` (30) is ignored. The Zones page shows each count and how it was reached ("cameras 3 (largest of 2) · 1 identified"), and the map keeps live head counts on every zone. The Workers page and the mobile app show "In Bay 1 · CAM-02" or "Last seen in Bay 1 · CAM-02 · 4 min ago".

Zone breaches from cameras:

- An identified worker seen in a restricted zone they are not assigned to raises a ZONE_BREACH, naming the camera.
- Over capacity uses hysteresis, because a head count is a noisy reading. The zone must be over its limit for `ZONE_CAPACITY_CONFIRM_SECONDS` (10) before one alert is raised. Another alert can only follow after the zone has been back within its limit for `ZONE_CAPACITY_CLEAR_SECONDS` (60).

Run the presence monitor (`python manage.py run_presence_monitor`) so exits are recorded and counts that go stale update the dashboard.

### Live camera view

The **Cameras** page (Safety Officers and Admins only) shows a live grid of every camera: those assigned to a zone, those named by a camera token, and any camera currently sending, including a test webcam. Each camera running `inference.py` sends its annotated view (boxes, status banner) as a 640 px JPEG up to 5 times a second (`--live-fps`). It sends from a background thread, so detection never waits, and it drops old frames rather than queueing them. The API relays frames over `/ws/cameras/` and keeps only the latest frame per camera, in memory for 30 s. Live frames are never written to disk and never go through the outbox. A camera with no frame for 5 s shows as offline. Click a tile to enlarge it.

Turn it off on a camera with `--no-live` or `SITESAFE_LIVE=0`, or for the whole server with `LIVE_VIEW_ENABLED=False`. When the API runs as several processes, set `REDIS_URL`, which shares the latest frames through Redis.

### Cameras on the site map

Each camera can be placed on the site map with where it is mounted, the direction it faces, its view angle and how far it usefully sees. The map then draws it as a marker with a view cone, on the Zones page and in the **Site Map** card on the dashboard:

- **Green**: the camera's live view is current.
- **Grey, dashed cone**: the camera is offline.
- **Red, pulsing**: for a minute after the camera raises an alert. It turns red the moment the alert arrives over the dashboard socket.

Hovering a camera shows how many people it sees. Clicking it shows its zone, people in view, open alerts and its latest alert. Safety Officers and Admins also see a live thumbnail, refreshed every second, and a link that opens that camera on the Cameras page (`/cameras?camera=CAM-01`). Viewers get the map and status without any picture.

To place a camera, an Admin opens **Zones → Site Map**, chooses **Place** (or **Move**) next to the camera, and clicks the map where it is mounted. Three sliders set where it faces (0–355°), its view angle (20–150°) and its range (5–150 m); the cone follows as they move. **Remove** takes a camera off the map without affecting its alerts or live view. Every known camera is listed, whether placed or not: those assigned to a zone, those named by a camera token, and those currently sending. The dashboard card links to the unplaced ones.

The cone is drawn from what the Admin enters; nothing is measured from the picture. Changed people counts and placements arrive over the dashboard socket (`camera_updated`); live status is refreshed every 10 s.

### Danger areas on the camera picture

A danger area is a polygon drawn on one camera's picture, such as a crane's swing radius, an excavation edge or a loading bay. Areas are stored as fractions of the picture (0–1), so they still fit if the camera's resolution changes. They need not cover a whole zone.

- **Drawing.** An Admin opens a camera on the Cameras page and chooses **Draw a danger area**. They click the corners on the live picture (3 to 24), then enter a name and severity (Critical, High or Medium). Areas can be switched off while the hazard is absent, and deleted. Safety Officers see the areas but cannot change them.
- **Detection.** A person is inside when the bottom-centre of their box, where their feet are, is inside the polygon. Using the box centre would wrongly count someone standing in front of the area. The camera fetches its areas with its alert rules every 15 s (`RULES_REFRESH_SECONDS`), so a new or changed area takes effect within 15 s without restarting it.
- **Alerts.** A person inside an active area for 1 s (at least 2 samples, no gap over 1 s) raises one DANGER_AREA alert with a snapshot, the area's severity, and the worker's name if their QR badge was read. Walking past a corner raises nothing. The same person can only be alerted for that area again after 10 s outside it. If the detector loses someone and finds them again close by under a new track, their entry continues rather than alerting twice.
- **Display.** The live view outlines every area in amber and fills it red while someone is inside, with a "DANGER AREA – name" banner.

Danger-area alerts apply to anyone, badged or not. The Danger area rule on the Settings page (Alert Configuration) switches them all off, or changes how they are notified.

### Report service

```bash
cd report-service && npm ci
DJANGO_API_URL=http://localhost:8000/api/ npm start   # listens on :3001
npm test
```

Reports come in Word or PDF. Each report covers whole calendar days in the requesting user's time zone. The safety performance report gives counts, time to resolve and days without a recorded PPE violation per zone. It gives no compliance percentage, because the system records detected violations, not compliant observations, so there is no denominator. Its method section states each definition.

### Backend environment variables

Copy `backend/.env.example` to `backend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | *(required in production)* |
| `DEBUG` | Enable debug mode | `True` |
| `DB_NAME` | PostgreSQL database name | `sitesafe` |
| `DB_USER` | PostgreSQL user | `sitesafe` |
| `DB_PASSWORD` | PostgreSQL password | `sitesafe` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed for the API and websocket | `http://localhost:5173,http://127.0.0.1:5173` |
| `JWT_ACCESS_MINUTES` | Access-token lifetime (the dashboard refreshes automatically) | `30` |
| `REDIS_URL` | Channel layer for multi-process live updates | *(in-memory)* |
| `REPORT_SERVICE_URL` | Report generation service | `http://localhost:3001/generate` |
| `EMAIL_BACKEND` | Email notification backend | console (prints mail) |
| `FIREBASE_CREDENTIALS_PATH` | Service-account JSON enabling push | *(push disabled)* |
| `MQTT_BROKER_HOST` / `MQTT_PORT` / `MQTT_USERNAME` / `MQTT_PASSWORD` | Vest telemetry broker | `localhost` / `1883` |
| `ALERT_SNAPSHOTS_ENABLED` | Store camera snapshots sent with alerts | `True` |
| `ALERT_SNAPSHOT_RETENTION_DAYS` | Age after which `purge_alert_snapshots` deletes snapshots | `30` |
| `ALERT_SNAPSHOT_MAX_BYTES` | Largest snapshot accepted, in bytes | `524288` |
| `LIVE_VIEW_ENABLED` | Relay camera live views to the Cameras page | `True` |
| `MEDIA_ROOT` | Where uploaded files (alert snapshots) are stored | `backend/media` |
| `CAMERA_PRESENCE_SECONDS` | How long a camera badge sighting keeps a worker placed in its zone | `60` |
| `CAMERA_COUNT_STALE_SECONDS` | Age after which a camera's people count stops counting | `30` |
| `ZONE_CAPACITY_CONFIRM_SECONDS` / `ZONE_CAPACITY_CLEAR_SECONDS` | Over-capacity alert after this long over the limit / re-armed after this long back within it | `10` / `60` |

---

## 3. Frontend setup

In a **new terminal**:

```bash
cd frontend

npm install
npm run dev
```

The dashboard runs at **http://localhost:5173/**.

Log in with the superuser email and password you created. The frontend talks to the backend at `http://localhost:8000/api/`.

### Other frontend commands

```bash
npm run build    # Production build → frontend/dist/
npm run preview  # Preview production build
npm run lint     # ESLint
```

---

## 4. AI module setup (optional)

The AI module detects PPE violations (helmet, vest, gloves, goggles, boots) from a webcam and creates alerts in the backend.

### Install dependencies

Use a separate virtual environment (recommended — Ultralytics/OpenCV are heavy):

```bash
cd ai-module

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements-vision.txt
```

### Dataset

Training images are **not** committed to git. Place a YOLO-format dataset under `ai-module/ppe_dataset/` with this layout:

```
ppe_dataset/
├── data.yaml
├── train/images/   train/labels/
├── valid/images/   valid/labels/
└── test/images/    test/labels/
```

The dataset config at `ai-module/ppe_dataset/data.yaml` defines 10 classes: compliant PPE (`helmet`, `vest`, …) and violations (`no-helmet`, `no-vest`, …).

Audit split integrity and labels before training:

```bash
python audit_dataset.py
python verify_dataset.py
```

`audit_dataset.py` is read-only. It reports source identities shared across
splits, exact duplicate images, conflicting labels, malformed annotations,
background-image counts, and image/label pairing errors. Add `--strict` to
make any blocker return a non-zero exit code. The current legacy dataset is
expected to fail strict mode until its source-grouped splits are rebuilt.

Build a non-destructive dataset-v2 review and split proposal:

```bash
python prepare_dataset_v2.py
```

This writes ignored artifacts to `ai-module/dataset_v2_plan/`: a row-level
manifest, connected source/duplicate groups, a CSV and HTML review pack for
contradictory exact-image labels, and an optimized 70/15/15 split proposal.
Source siblings, inferred video sessions, exact duplicates, and conservatively
verified visual duplicates are indivisible. The command returns exit code `2`
while label conflicts remain and never changes the legacy dataset.

### Train a model

Quick training (defaults to YOLOv10n, 50 epochs):

```bash
python train.py
```

Or use the configurable script:

```bash
python scripts/train_yolov10_ppe.py --epochs 50 --batch 16 --device mps
```

Weights are saved to `ai-module/runs/train/<run-name>/weights/best.pt`.

Evaluate on the test split:

```bash
python test_model.py
```

### Run live webcam inference

1. Place the PPE weights at `ai-module/models/sitesafe_v5.pt` (or update `MODEL_PATH` in `inference.py`).
2. Issue a camera device token (see *Device tokens* above) and configure the environment:
   - `SITESAFE_DEVICE_KEY` — the camera's device token (required to deliver alerts)
   - `SITESAFE_API_BASE` — backend URL (default `http://127.0.0.1:8000/api`)
   - `SITESAFE_CAMERA_SOURCE` / `SITESAFE_CAMERA_ID` — or `--source` / `--camera-id`
   - `--ppe-conf` — runtime PPE candidate threshold (default `0.15`; calibrate on a clean validation set)
   - `SITESAFE_SNAPSHOTS=0` or `--no-snapshots` — send alerts without a frame snapshot (see *Alert evidence*)
   - `SITESAFE_LIVE=0` or `--no-live` — do not send the live view to the Cameras page; `--live-fps` sets its rate (default 5)
   - `--source clip.mp4 --loop` — play a recorded video as a camera, rewinding at the end (demonstrations, long tests)
   - `--no-display` — run without the preview window (stop with Ctrl+C; the summary still prints)
3. Make sure the backend is running, then:

```bash
cd ai-module
source .venv/bin/activate
SITESAFE_DEVICE_KEY=ss_... python inference.py --camera-id CAM-01
```

**Controls:** `Q` quit · `P` pause/unpause · `S` queue a test alert

Confirmed events are written to a local outbox (`ai-module/outbox/<camera>.sqlite3`) and delivered by a background thread with retries, so capture never waits on the network. Events queued while the API is down are delivered when it returns, including after a restart. Each event has an ID, so a retry is never stored twice. The camera also polls its alert rules from the dashboard every 15 seconds, together with its danger areas. A disabled alert type is not sent, and the INACTIVITY rule's `threshold_seconds` sets the stationary timeout.

**When a camera raises an alert.** Every detector waits for a condition to persist before alerting, then raises one alert for that person (or, for fire and smoke, for the scene) until the condition has cleared. Someone who stays in the same situation is not alerted again and again. People are followed between frames by the person detector, and a QR badge read on a person names them on every person alert below.

| Alert | Confirmed after | Raised again only after |
|---|---|---|
| PPE violation | the missing item is seen on the person for 1 s (at least 3 frames, no gap over 0.5 s) | that item has been unseen on them for 30 s |
| Vehicle proximity | the person is within 1 person-height of a car, truck, bus or motorbike in 3 samples, with no gap over 1 s | they have not been near any vehicle for 15 s |
| Danger area | the person's feet are inside the area for 1 s | they have been outside it for 10 s |
| Inactivity | the person has not moved more than 15 px for 5 min (the INACTIVITY rule) | they move again |
| Fall | a collapsed posture for 3 s | the posture clears |
| Fire / smoke | seen for 2 s, no gap over 1 s | the scene has been clear for 30 s |

A lower-level webcam script without API integration is also available:

```bash
python scripts/inference_webcam.py --weights runs/train/ppe_yolov10n/weights/best.pt
```

---

## 5. Mobile app (`mobile/`)

The mobile app is for site supervisors, built with React Native (Expo SDK 58). Supervisors sign in, see open and all alerts live, open an alert, resolve it if their role allows, and check worker presence. The app renews expired sessions automatically and reloads after reconnecting.

```bash
cd mobile
npm ci
npx expo start            # scan the QR with Expo Go on a phone on the same Wi-Fi
npm test && npm run lint && npm run typecheck
```

At sign-in, enter the backend computer's LAN address (for example `192.168.1.20:8000`). Run the backend on `0.0.0.0` and add that address to `ALLOWED_HOSTS`. The app needs no CORS entry and connects to the live socket without an Origin header, but still authenticates with its JWT.

**Push notifications** go through Firebase Cloud Messaging, the same path the backend already uses. Setup:

1. Create a Firebase project and add an Android app with package `com.sitesafe.mobile`.
2. Put its `google-services.json` in `mobile/`. The file is git-ignored, and `app.config.js` picks it up.
3. Point the backend's `FIREBASE_CREDENTIALS_PATH` at the project's service-account JSON.
4. Make a development build. Expo Go cannot receive remote pushes. Use `npx expo run:android` with a phone connected over USB, or `npx eas-cli@latest build --profile development --platform android`.

The app registers the phone after sign-in and unregisters it on sign-out. Tapping a notification opens that alert. iOS and the web build receive alerts live only while open, because the backend does not send to APNs.

## Running the full stack

### With Docker (demo machine)

```bash
cp .env.docker.example .env.docker      # set SECRET_KEY and DB_PASSWORD
docker compose --env-file .env.docker up --build
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py create_service_token CAM-01 --kind CAMERA --camera-id CAM-01
```

This starts PostgreSQL, Redis, Mosquitto, the API, the MQTT consumer, the presence monitor, the report service and the dashboard. The dashboard is at http://localhost:8080 and the API at http://localhost:8000. The camera pipeline runs natively on the host, because it needs webcam access, and points `SITESAFE_API_BASE` at the API. The admin site's styling is not served when `DEBUG=False`.

### Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request:

- backend tests on PostgreSQL and SQLite, with a migration completeness check;
- the AI, simulator and report-service tests;
- frontend lint and build;
- mobile lint, typecheck and tests.

### Manually, in terminals


Open three terminals:

| Terminal | Directory | Command |
|----------|-----------|---------|
| 1 | `backend/` | `source .venv/bin/activate && python manage.py runserver` |
| 2 | `frontend/` | `npm run dev` |
| 3 | `ai-module/` | `source .venv/bin/activate && python inference.py` |

Then open **http://localhost:5173**, sign in, and use the Dashboard, Alerts, and Workers pages. PPE violations detected by the camera appear as alerts with source **AI Camera**.

---

## Measuring performance (Chapter 5)

`tools/measure/` holds four scripts. Each saves a JSON result recording the machine, the commit, the settings and the sample sizes. `make_tables.py` turns the latest results into report tables with pass/fail against the proposed targets.

```bash
pip install -r tools/measure/requirements.txt
python manage.py create_service_token measure-cam --kind CAMERA --simulator   # alerts it creates are marked SIMULATED
export SITESAFE_API_BASE=http://127.0.0.1:8000/api SITESAFE_DEVICE_KEY=ss_... SITESAFE_EMAIL=... SITESAFE_PASSWORD=...

python tools/measure/latency.py --count 100 --resolve                 # event → dashboard socket
python tools/measure/recovery.py --events 100 --outage 300 --resolve  # API outage + camera restart
python tools/measure/fps.py --images ai-module/ppe_dataset/test/images --device mps   # all detectors
python tools/measure/soak.py --hours 2                                # run with the full stack up
python tools/measure/make_tables.py --out docs/evidence/CHAPTER5_MEASUREMENTS.md
```

If a second copy of the stack runs on the same machine, give `soak.py` the processes to watch: `--pids api=1234,camera=5678,presence_monitor=91011`.

**Recording a clip.** `python tools/measure/record_clip.py --out clips/name.mp4 --seconds 60` records raw camera frames, with no overlays, at the camera's measured frame rate, and writes `name.json` beside the clip. Keep clips of people out of git (`tools/measure/results/` is ignored).

**Scoring detection on a recorded clip.** `tools/measure/evaluate_clip.py` runs the full pipeline on a video, headless and offline, timing every tracker by the video's own clock (`--video-clock`). It then scores the alerts against a CSV of the true episodes: detections, misses, duplicates, false alerts and delay per event type. Copy `tools/measure/clip_annotations_template.csv`, write one row per true episode (event, start and end in seconds, badge if worn), then run:

```bash
python tools/measure/evaluate_clip.py --video clip.mp4 --annotations clip.csv
python tools/measure/evaluate_clip.py --events events.jsonl --annotations clip.csv   # re-score a saved run
```

Run them on the demo machine with the configuration you will present. Prefer a separate database: measurement traffic is labelled SIMULATED, but it still creates alerts and notifications. The recovery test simulates the outage with a local proxy, so the API keeps running. The FPS figure covers detection only; the camera's real frame rate is at most that.

## API overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/token/` | Public | Obtain JWT (`email`, `password`) |
| `POST` | `/api/token/refresh/` | Public | Refresh access token |
| `GET` | `/api/dashboard/stats/` | JWT | Dashboard summary stats |
| `GET/POST` | `/api/alerts/` | JWT | List / create alerts |
| `POST` | `/api/alerts/{id}/resolve/` | JWT | Mark alert resolved |
| `GET` | `/api/alerts/{id}/snapshot/` | JWT | Evidence JPEG of a camera alert (404 if none or purged) |
| `POST` | `/api/alerts/simulate/` | JWT | Create a simulated alert |
| `POST` | `/api/alerts/ingest/` | Vest gateway token | Ingest a vest alert by `vest_id` |
| `POST` | `/api/v1/vests/telemetry/` | Vest gateway token | Vest GPS/battery/SOS telemetry |
| `POST` | `/api/v1/camera-events/` | Camera token | Idempotent camera event (`event_id`, optional `badge_code`, `model_version`, base64 JPEG `snapshot`) |
| `GET/POST` | `/api/workers/{id}/badge/` | Safety Officer | Badge payload to print / reissue (revokes the old one) |
| `POST` | `/api/v1/reports/generate/` | Safety Officer | `report_type`, `date_from`, `date_to`, `file_format` (DOCX/PDF), `tz` |
| `GET` | `/api/v1/camera-config/?camera_id=` | Camera token | Effective alert rules and active danger areas for a camera |
| `GET/POST/PATCH/DELETE` | `/api/v1/camera-areas/?camera_id=` | JWT read, Admin write | Danger areas (`camera_id`, `name`, `polygon` as `[[x, y], …]` fractions, `severity`, `is_active`) |
| `POST` | `/api/v1/camera-frames/?camera_id=` | Camera token | Live-view JPEG (`image/jpeg` body, max 256 KB); relayed, not stored |
| `POST` | `/api/v1/camera-counts/` | Camera token | People in view (`camera_id`, `people`, `observed_at`) for zone head counts |
| `GET` | `/api/v1/cameras/` | Safety Officer | Every known camera with zone and live status |
| `GET` | `/api/v1/camera-map/` | JWT | Every known camera for the site map: `placement`, `live`, `people_in_view`, `open_alerts`, `last_alert` |
| `PUT/DELETE` | `/api/v1/camera-map/{camera_id}/` | Admin | Place or move a camera (`latitude`, `longitude`, `heading`, `field_of_view`, `view_range_m`), or take it off the map |
| `GET` | `/api/v1/camera-frames/latest/?camera_id=` | Safety Officer | The camera's latest live-view JPEG (404 if none in the last 30 s) |
| `WS` | `/ws/cameras/?token=<access>` | Safety Officer | Live frames: binary `camera_id`, newline, JPEG |
| `POST` | `/api/v1/camera-activity/` | Camera token | Badge sighting / idle start / idle end with `occurred_at` |
| `GET` | `/api/v1/activity/timeline/?worker_id=&date=&tz=` | JWT | One worker's day: sessions, idle, zone visits, totals |
| `GET` | `/api/v1/activity/daily/?start_date=&end_date=&tz=` | JWT | Per-worker daily attendance (max 31 days) |
| `WS` | `/ws/dashboard/?token=<access>` | JWT | Live `alert_created/updated/resolved`, `vest_updated`, `worker_status_update`, `zone_updated`, `camera_updated` |
| `GET/POST/…` | `/api/workers/` | JWT | Worker CRUD |
| — | `/admin/` | Staff | Django admin |

Example — obtain a token:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password"}'
```

---

## Troubleshooting

**Database connection errors**  
Confirm PostgreSQL is running and that `backend/.env` matches your database name, user, and password.

**Frontend cannot reach the API**  
Ensure the backend is on port 8000 and the frontend origin is listed in `CORS_ALLOWED_ORIGINS`. Point the frontend elsewhere with `VITE_API_URL` / `VITE_WS_URL` (see `frontend/.env.example`).

**Login returns 401**  
Users authenticate with **email**, not username. Create an account with `createsuperuser` or Django admin.

**`Model not found` in inference**  
Train a model or place weights at the path set in `MODEL_PATH` inside `ai-module/inference.py`.

**Camera not opening**  
Try a different `CAMERA_INDEX` (e.g. `1` or `2`). Close other apps using the webcam.

**No alerts from the AI module**  
Check the session summary printed on exit. *Still queued* means the API was unreachable or the device key was missing or rejected (`HTTP 401`). *Rejected by the API* means the payload failed validation, for example because the token is not allowed for that `camera_id`. Also check that the alert type is enabled in **Settings**. A camera raises one alert per person per episode (a missing PPE item, a vehicle encounter, a danger-area entry), so a person who stays in the same situation is not alerted again until it has cleared.

---

## License

Academic / FYP project. See `docs/` for the full project report.
