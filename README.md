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

Start the API server:

```bash
python manage.py runserver
```

The API runs at **http://127.0.0.1:8000/**.

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

Verify the dataset before training:

```bash
python verify_dataset.py
```

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

1. Copy your trained weights to `ai-module/models/sitesafe_final.pt` (or update `MODEL_PATH` in `inference.py`).
2. Edit the **CONFIG** block at the top of `ai-module/inference.py`:
   - `API_BASE` — backend URL (default `http://127.0.0.1:8000/api`)
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` — credentials for a backend user with API access
   - `CAMERA_INDEX` — webcam device index (usually `0`)
   - `COOLDOWN_SECONDS` — minimum time between repeated alerts for the same violation
3. Make sure the backend is running, then:

```bash
cd ai-module
source .venv/bin/activate
python inference.py
```

**Controls:** `Q` quit · `P` pause/unpause · `S` send a test alert

If the API is unreachable, inference continues in offline mode (detections still shown, no alerts sent).

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
| `POST` | `/api/alerts/ingest/` | Public | Ingest alert from external source |
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
Ensure the backend is on port 8000. CORS is configured for `http://localhost:5173` in `backend/sitesafe/settings.py`.

**Login returns 401**  
Users authenticate with **email**, not username. Create an account with `createsuperuser` or Django admin.

**`Model not found` in inference**  
Train a model or place weights at the path set in `MODEL_PATH` inside `ai-module/inference.py`.

**Camera not opening**  
Try a different `CAMERA_INDEX` (e.g. `1` or `2`). Close other apps using the webcam.

**No alerts from the AI module**  
Check that the backend is running, credentials in `inference.py` are correct, and violations are detected (class names starting with `no-`). Alerts respect a cooldown period per violation type.

---

## License

Academic / FYP project. See `docs/` for the full project report.
