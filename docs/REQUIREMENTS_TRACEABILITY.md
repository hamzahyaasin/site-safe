# Site-Safe requirements traceability matrix

Started 16 October 2026 (Stage 0 of `FYP_COMPLETION_PLAN_2026-10-16.md`). It traces each requirement to its code, tests and evidence. It feeds report Chapter 3 (SRS) and Chapter 5 (testing), and it is the only basis for a completion percentage.

**Status meanings.** Each level includes the ones before it.

| Status | Meaning |
|---|---|
| Missing | No implementation. |
| Coded | The code exists. |
| Tested | Automated tests cover the behaviour. |
| Integrated | Verified end-to-end across real running services. |
| Physical | Verified with real hardware or a real camera scene. |
| Accepted | The supervisor has agreed it meets the acceptance criterion. |

Nothing is *Physical* or *Accepted* yet. The acceptance criteria are proposals until the supervisor agrees them, and the priority column (M = must, S = should) is also a proposal.

## Functional requirements

| ID | Requirement (report objective) | Pri | Acceptance criterion (proposed) | Code | Tests / evidence | Status |
|---|---|---|---|---|---|---|
| FR-01 | Users sign in with email and password; sessions renew without re-login | M | Valid login gets tokens. Expired access token renews silently. Revoked/invalid refresh token returns to login. | `accounts/`, `frontend/src/api/axios.js` | `accounts/tests.py`; browser check 16 Oct (corrupted token → refresh → retried requests 200) | Integrated |
| FR-02 | Three roles (Admin, Safety Officer, Viewer) enforced by the API | M | Every forbidden role action returns 403; each permitted counterpart succeeds | `accounts/permissions.py` | `accounts/tests.py` (16) | Tested |
| FR-03 | UI offers only actions the user's role permits | S | Viewer sees no resolve/edit/generate controls | `AuthContext.jsx` (Zones only) | — | Coded (partial) |
| FR-04 | Detect missing PPE (10 classes) from a camera | M | Event precision ≥90% and episode recall ≥85% per retained class, on a sealed target-camera set | `ai-module/inference.py`, `models/sitesafe_v5.pt` | Held-out mAP50 0.562 on a leaky split (not a valid claim) | Coded |
| FR-05 | One alert per person per violation episode | M | Two people with the same violation give two alerts; a single-frame flicker gives none | — | — | Missing |
| FR-06 | Detect falls from camera pose | M | Positive and hard-negative videos meet the AI event targets | `ai-module/fall_detection.py` | `alerts/test_fall.py` (21) | Tested |
| FR-07 | Warn when a worker is too close to a vehicle | M | Calibrated distance threshold; video evaluation | `ai-module/proximity.py` | `alerts/test_proximity.py` (9) | Tested |
| FR-08 | Detect prolonged inactivity; timeout configurable from the dashboard | M | Changing the INACTIVITY rule changes the camera timeout within 60 s | `ai-module/inactivity.py`, `CameraRules` | `alerts/test_inactivity.py` (10), `test_inference_config.py` | Tested |
| FR-09 | Fire/smoke detection with hot-work permit suppression | M | Licensed fixture videos pass; a permitted hot-work fire is downgraded, not dropped | — | — | Missing |
| FR-10 | QR worker identification linking camera events to a worker | M | Measured correct-association rate at a defined size, distance and lighting | — | — | Missing |
| FR-11 | Camera events reach the API reliably | M | 100 events queued in a 5-minute outage arrive exactly once after recovery | `ai-module/event_outbox.py`, `CameraEventView` | `test_event_outbox.py` (8), `alerts/test_ingest.py`; e2e 16 Oct (3 queued while API down → 2 stored, 1 dead-lettered for wrong camera) | Integrated (small fixture) |
| FR-12 | Only authorised devices can submit data | M | Anonymous, revoked, wrong-kind or wrong-camera tokens are rejected | `accounts/service_auth.py` | `alerts/test_ingest.py` | Tested |
| FR-13 | Live dashboard updates for every alert/vest/worker change | M | Two sessions converge after create, resolve, SOS and reconnect | `alerts/events.py`, signals, `WebSocketContext.jsx` | `alerts/test_realtime.py`; e2e 16 Oct (two clients each got created, created, resolved); browser check (live FALL appears, resolve removes it) | Integrated |
| FR-14 | Websocket requires a valid user token from an allowed origin | M | No token, a bad token or an expired token gives close code 4401; a foreign origin is refused | `sitesafe/ws_auth.py`, `asgi.py`, `consumers.py` | `alerts/test_realtime.py` | Tested |
| FR-15 | Alert rules (enable, threshold, notify) change runtime behaviour | M | A disabled type stores nothing. Notify flags gate push/email. SOS cannot be disabled. | `alerts/rules.py`, `notify.py`, seed migration 0009 | `alerts/test_ingest.py` | Tested |
| FR-16 | Push notifications to subscribed users | S | An installed client receives a test push; preferences are respected | `sitesafe/notifications.py`, `alerts/notify.py` | Mocked in tests | Coded (no client) |
| FR-17 | Email notifications | S | Mail to opted-in users when the rule enables it | `alerts/notify.py` | `alerts/test_ingest.py` (locmem) | Tested |
| FR-18 | Worker registry: create, edit, deactivate from the UI | M | All three operations work in the browser | API in `workers/` | — | Coded (API only) |
| FR-19 | Zones with polygon boundaries and camera assignment | M | Invalid geometry/camera lists are rejected; map editor | `sitemap/` | `sitemap/tests.py` (7) | Tested (no map UI) |
| FR-20 | Automatic restricted-zone breach and over-occupancy alerts | M | Entering a RESTRICTED polygon raises ZONE_BREACH | — | — | Missing |
| FR-21 | Smart vest: GPS position, SOS button, LoRa link | M | Physical SOS reaches the dashboard; delay and packet loss measured | Server: `workers/`, `run_mqtt_consumer` | `alerts/test_ingest.py`, `test_realtime.py` (SOS broadcast) | Coded (server only, no hardware) |
| FR-22 | Vest telemetry is validated | M | Out-of-range latitude/longitude, a lone coordinate, or battery outside 0–100 returns 400 | `VestTelemetrySerializer` | `alerts/test_ingest.py` | Tested |
| FR-23 | Vest offline detection | S | No report within `VEST_OFFLINE_AFTER_SECONDS` shows the vest offline | setting only | — | Missing |
| FR-24 | Worker activity history (check-in/out, idle, zone transitions) | M | Generated automatically and reconciled with annotated scenarios | `workers/` (manual logs, GPS zone logs) | — | Coded (partial) |
| FR-25 | Incident list, detail, resolve, CSV export | M | Resolve is broadcast; the filters include every type | `frontend/src/components/incidents/` | — | Coded (FALL filter missing) |
| FR-26 | Dashboard KPIs and charts reflect recorded data only | M | Every displayed number reconciles to the API; nothing is fabricated | `frontend/src/lib/utils.js`, `DashboardCharts.jsx` | — | **Fails** (fabricated vitals and charts) |
| FR-27 | Incident and compliance reports in DOCX and PDF | M | Fixtures reconcile exactly; PDF is produced | `report-service/`, `reports/` | — | Coded (DOCX only) |
| FR-28 | Mobile app: login, alerts, resolve, push | M | An Android build receives a push and resolves an incident | — | — | Missing |
| FR-29 | Alert evidence (snapshot, confidence, model version) | S | Each AI incident is traceable to its frame and model | `Alert.confidence`, `Alert.snapshot` field | — | Coded (confidence only) |

## Non-functional requirements

| ID | Requirement | Target (proposed) | Evidence | Status |
|---|---|---|---|---|
| NFR-01 | Event-to-dashboard latency | p95 ≤ 2 s from commit on a local network | — | Not measured |
| NFR-02 | Outage tolerance | No lost or duplicated events across a 5-minute API outage and sender restart | Unit + small e2e fixture | Partially verified |
| NFR-03 | Security of producers | No anonymous write endpoints; no credentials in source | `alerts/test_ingest.py`, `test_inference_config.py` | Tested |
| NFR-04 | Inference throughput | ≥ 10 FPS with all detectors on the demo machine | — | Not measured |
| NFR-05 | Soak | 2-hour full-stack run with controlled disconnect | — | Not run |
| NFR-06 | Reproducible setup | Fresh machine reaches a working demo from the README | README updated 16 Oct | Not verified |
| NFR-07 | Code quality gate | Backend + AI tests pass; frontend build passes, lint clean | 98 + 22 pass; build OK; **lint: 7 pre-existing errors** | Partial |

## Progress ledger

```text
Phase / task IDs: Stage 0 (baseline, matrix), Stage 1 (security, validation, events, rules, outbox)
Status: tested; integration-checked on a throwaway SQLite database; not run against PostgreSQL
Requirement IDs covered: FR-01, FR-11–FR-15, FR-17, FR-19, FR-22, NFR-02, NFR-03
Commit / working-tree reference: uncommitted working tree on main, 16 Oct 2026
Files changed and migration notes:
  backend: accounts (ServiceToken, service_auth, create_service_token), alerts (events, rules,
  notify, CameraEventView, CameraConfigView, consumer), sitesafe (ws_auth, asgi, mqtt,
  settings, validation), workers (telemetry serializer, signals, run_mqtt_consumer),
  sitemap (validation, portable for_camera)
  migrations: accounts 0006 (ServiceToken); alerts 0008 (Alert.confidence, Alert.event_id,
  AlertConfig uniqueness — dedupes existing duplicate rules, keeping the newest) and 0009 (seed
  one global rule per alert type). Not yet applied to the dev PostgreSQL database.
  frontend: token refresh, env-driven API/WS URLs, authenticated socket with 4401 renewal,
  resync on reconnect, update/resolve/vest events
  ai-module: credentials removed, device-token auth, event_outbox.py, CameraRules
Tests run (16 Oct 2026):
  backend: manage.py test --settings=sitesafe.test_settings → 98 OK (was 59)
  ai-module: unittest test_inference_config test_dataset_audit test_prepare_dataset_v2
             test_event_outbox → 22 OK (was 10)
  frontend: npm ci; npm run build → OK; npm run lint → 7 errors, all pre-existing
            (react-hooks/set-state-in-effect etc.)
  e2e: daphne + SQLite; Node websocket clients; outbox outage replay; browser login,
       token renewal, live FALL event, resolve
Known defects / limitations:
  - The old admin password was committed in git history (inference.py); rotate it.
  - Access tokens now last 30 minutes; the report service forwards the user's JWT, so a very
    long report run could outlive it.
  - Notification delivery runs on an in-process thread pool, not a durable queue; a crash
    between commit and send drops that notification (the incident itself is stored).
  - Single site only ("default" group); the site selector in the UI is still decorative.
Human inputs still needed: rotate the old admin password; agree acceptance targets and priorities
Next independent task: Stage 2 — remove fabricated dashboard data, worker forms, map zone editor,
  automatic ZONE_BREACH, vest offline timeout, lint clean-up
```
