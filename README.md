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

### Zones and automatic breaches

Draw zone boundaries on the map on the **Zones** page (Admin only). Vest GPS positions then produce zone entry/exit history and automatic **ZONE_BREACH** alerts in two cases:

- A worker enters a RESTRICTED zone that is not their assigned zone.
- An entry takes a zone above its maximum occupancy.

Where zones overlap, the highest-risk zone wins. Occupancy counts only workers whose vests are online. Camera-only zones have no boundary, so they have no GPS presence.

### QR worker badges

On the **Workers** page, edit a worker and choose **Print badge**. The QR code encodes only a random code (`SSW1:…`), never a name or phone number. Print it at 100% scale (60 mm) and wear it on the helmet front or chest. **Reissue badge** revokes every earlier printout.

A camera reads badges on the sampled frames and links each one to the person box that contains it. A PPE, fall or inactivity alert for that person is then attributed to the worker. A badge that is ambiguous (overlapping people), unreadable or revoked leaves the alert unidentified. The camera never guesses. Disable reading with `--no-qr`.

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
3. Make sure the backend is running, then:

```bash
cd ai-module
source .venv/bin/activate
SITESAFE_DEVICE_KEY=ss_... python inference.py --camera-id CAM-01
```

**Controls:** `Q` quit · `P` pause/unpause · `S` queue a test alert

Confirmed events are written to a local outbox (`ai-module/outbox/<camera>.sqlite3`) and delivered by a background thread with retries, so capture never waits on the network. Events queued while the API is down are delivered when it returns, including after a restart. Each event has an ID, so a retry is never stored twice. The camera also polls its alert rules from the dashboard every 60 seconds. A disabled alert type is not sent, and the INACTIVITY rule's `threshold_seconds` sets the stationary timeout.

A lower-level webcam script without API integration is also available:

```bash
python scripts/inference_webcam.py --weights runs/train/ppe_yolov10n/weights/best.pt
```

---

## Running the full stack

Open three terminals:

| Terminal | Directory | Command |
|----------|-----------|---------|
| 1 | `backend/` | `source .venv/bin/activate && python manage.py runserver` |
| 2 | `frontend/` | `npm run dev` |
| 3 | `ai-module/` | `source .venv/bin/activate && python inference.py` |

Then open **http://localhost:5173**, sign in, and use the Dashboard, Alerts, and Workers pages. PPE violations detected by the camera appear as alerts with source **AI Camera**.

---

## API overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/token/` | Public | Obtain JWT (`email`, `password`) |
| `POST` | `/api/token/refresh/` | Public | Refresh access token |
| `GET` | `/api/dashboard/stats/` | JWT | Dashboard summary stats |
| `GET/POST` | `/api/alerts/` | JWT | List / create alerts |
| `POST` | `/api/alerts/{id}/resolve/` | JWT | Mark alert resolved |
| `POST` | `/api/alerts/simulate/` | JWT | Create a simulated alert |
| `POST` | `/api/alerts/ingest/` | Vest gateway token | Ingest a vest alert by `vest_id` |
| `POST` | `/api/v1/vests/telemetry/` | Vest gateway token | Vest GPS/battery/SOS telemetry |
| `POST` | `/api/v1/camera-events/` | Camera token | Idempotent camera event (`event_id`, optional `badge_code`) |
| `GET/POST` | `/api/workers/{id}/badge/` | Safety Officer | Badge payload to print / reissue (revokes the old one) |
| `POST` | `/api/v1/reports/generate/` | Safety Officer | `report_type`, `date_from`, `date_to`, `file_format` (DOCX/PDF), `tz` |
| `GET` | `/api/v1/camera-config/?camera_id=` | Camera token | Effective alert rules for a camera |
| `WS` | `/ws/dashboard/?token=<access>` | JWT | Live `alert_created/updated/resolved`, `vest_updated`, `worker_status_update` |
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
Check the session summary printed on exit. *Still queued* means the API was unreachable or the device key was missing or rejected (`HTTP 401`). *Rejected by the API* means the payload failed validation, for example because the token is not allowed for that `camera_id`. Also check that the alert type is enabled in **Settings**. Alerts respect a cooldown period per violation type.

---

## License

Academic / FYP project. See `docs/` for the full project report.
