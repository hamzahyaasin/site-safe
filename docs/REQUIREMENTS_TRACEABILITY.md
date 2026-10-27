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
| FR-03 | UI offers only actions the user's role permits | S | Viewer sees no resolve/edit/generate controls | `AuthContext.jsx` (`canOperate`, `isAdmin`) across Dashboard, Incidents, Workers, Vests, Zones, Settings, Reports | Browser check 16 Oct (officer: zones read-only; admin: zone editor); Viewer browser check 26 Oct on every page: no resolve, register, edit, generate, permit or rule controls (Alert Configuration read-only, vest assignment disabled, Reports shows a role notice); only own notification preferences and password are editable; API refused the Viewer's resolve and report generation with 403; same pages as Safety Officer show Resolve, Generate Report, Register worker/vest, Edit and Issue permit | Integrated |
| FR-04 | Detect missing PPE (10 classes) from a camera | M | Event precision ≥90% and episode recall ≥85% per retained class, on a sealed target-camera set | `ai-module/inference.py`, `models/sitesafe_v5.pt` | Held-out mAP50 0.562 on a leaky split (not a valid claim) | Coded |
| FR-05 | One alert per person per violation episode | M | Two people with the same violation give two alerts; a single-frame flicker gives none | `ai-module/ppe_episodes.py`, `badged_violations` + episode loop in `inference.py`, `--ppe-persistence`, `--ppe-clear-seconds`, person ids from `identity.IdentityTracker` (badge, then person, then distance) | `test_ppe_episodes.py` (25); headless pipeline run on a still-image clip: the dataset labels 2 people without helmets and 1 without gloves; 20 Oct (before the duplicate merge) it gave 3 helmet alerts, misread at the time as 3 people (one was a duplicate box, IoU 0.68); 22 Oct with `tools/measure/evaluate_clip.py`: 2 of 2 helmet episodes, gloves missed, 1 goggles alert not in the labels; live webcam run 21 Oct (55 s, one person) found duplicate-box episodes → fixed, replay of its recorded boxes gives one alert per item; 27 Oct live webcam run showed one person re-alerted within seconds (head box moving more than its size); 6 person-association tests reproduce and cover it; test video re-run before/after identical (8 alerts) | Tested (**no annotated video scored yet**) |
| FR-06 | Detect falls from camera pose | M | Positive and hard-negative videos meet the AI event targets | `ai-module/fall_detection.py` | `alerts/test_fall.py` (21) | Tested |
| FR-07 | Warn when a worker is too close to a vehicle | M | Calibrated distance threshold; video evaluation; one alert per person per encounter | `ai-module/proximity.py` (`ProximityTracker`: per-person encounters on `identity.IdentityTracker` tracks, 15 s clear, re-found person within 5 s), badge on the alert | `ai-module/test_proximity.py` (18, moved from the backend); pipeline on test videos 27 Oct: a 60 s clip looped 3 times gave 10 alerts for one worker beside a flickering car, now 2 (one per person, the badge holder named); the 40-scene video gave 2, now 5 (four people beside cars in one street scene, one in a later scene); other alerts unchanged | Tested (**threshold not calibrated against measured distances**) |
| FR-08 | Detect prolonged inactivity; timeout configurable from the dashboard | M | Changing the INACTIVITY rule changes the camera timeout within 60 s | `ai-module/inactivity.py`, `CameraRules` | `alerts/test_inactivity.py` (10), `test_inference_config.py` | Tested |
| FR-09 | Fire/smoke detection with hot-work permit suppression | M | Licensed fixture videos pass; a permitted hot-work fire is downgraded, not dropped | `ai-module/fire_detection.py`, `ai-module/fire/` (prep script, Colab and Kaggle notebooks), `models/fire_smoke.pt` (YOLO11s, D-Fire, sha256 `4bdbf702…2e38d10`; evidence in `models/fire_smoke_v1_export/`), `alerts/fire_policy.py`, `sitemap.HotWorkPermit`, `components/zones/HotWorkPermits.jsx` | `test_fire_detection.py` (8), `fire/test_prepare_fire_dataset.py` (4), `sitemap/tests.py` permit + policy (8); e2e 20 Oct: permit issued in UI → fire in permitted zone MEDIUM + linked, elsewhere CRITICAL; model trained 26–27 Oct on Kaggle (T4, 96 epochs, early stop, best epoch 76); held-out test (4,294 images, never used for training or selection): P 0.775, R 0.720, mAP50 0.787, mAP50-95 0.459 (fire R 0.651 / mAP50 0.726; smoke R 0.789 / mAP50 0.848), reproduced on the Mac to 3 decimals; real detections through `FireTracker` on still images: fire image → 1 FIRE + 1 SMOKE alert after 2 s, negative image → none | Integrated (**model trained; image-level metrics only, no video or hard-negative alert evaluation**) |
| FR-10 | QR worker identification linking camera events to a worker | M | Correct-association, unknown and wrong-person rates measured at a stated size, distance, angle and lighting | `ai-module/identity.py`, `group_violations` in `inference.py`, `Worker.badge_code`, `/workers/{id}/badge/`, `frontend/src/lib/badge.js` | `test_identity.py` (14, including real OpenCV QR encode→decode); `workers/tests.py` Badge/CameraBadgeIdentity (7); e2e 16 Oct (synthetic frame: badge decoded → alert attributed to Ali; second person unidentified) | Integrated (synthetic frames only; **physical camera test pending**) |
| FR-11 | Camera events reach the API reliably | M | 100 events queued in a 5-minute outage arrive exactly once after recovery | `ai-module/event_outbox.py`, `CameraEventView` | `test_event_outbox.py` (8), `alerts/test_ingest.py`; e2e 16 Oct (3 queued while API down → 2 stored, 1 dead-lettered for wrong camera) | Integrated (small fixture) |
| FR-12 | Only authorised devices can submit data | M | Anonymous, revoked, wrong-kind or wrong-camera tokens are rejected | `accounts/service_auth.py` | `alerts/test_ingest.py` | Tested |
| FR-13 | Live dashboard updates for every alert/vest/worker change | M | Two sessions converge after create, resolve, SOS and reconnect | `alerts/events.py`, signals, `WebSocketContext.jsx` | `alerts/test_realtime.py`; e2e 16 Oct (two clients each got created, created, resolved); browser check (live FALL appears, resolve removes it) | Integrated |
| FR-14 | Websocket requires a valid user token from an allowed origin | M | No token, a bad token or an expired token gives close code 4401; a foreign origin is refused | `sitesafe/ws_auth.py`, `asgi.py`, `consumers.py` | `alerts/test_realtime.py` | Tested |
| FR-15 | Alert rules (enable, threshold, notify) change runtime behaviour | M | A disabled type stores nothing. Notify flags gate push/email. SOS cannot be disabled. | `alerts/rules.py`, `notify.py`, seed migration 0009 | `alerts/test_ingest.py` | Tested |
| FR-16 | Push notifications to subscribed users | S | An installed Android client receives a test push; preferences and rules respected; tap opens the alert | `sitesafe/notifications.py` (Android channel `safety-alerts`), `alerts/notify.py`, `mobile/lib/push.ts` | Backend rule/preference tests (mocked FCM); `mobile/__tests__/push.test.ts` | Coded (**needs Firebase project + Android dev build to verify**) |
| FR-17 | Email notifications | S | Mail to opted-in users when the rule enables it | `alerts/notify.py` | `alerts/test_ingest.py` (locmem) | Tested |
| FR-18 | Worker registry: create, edit, deactivate from the UI | M | All three operations work in the browser; one vest per worker | `pages/WorkersPage.jsx`, `WorkerSerializer` (vest assignment), migration workers 0004 | `workers/tests.py` (7); browser check 16 Oct (registered worker with VEST-003) | Integrated |
| FR-19 | Zones with polygon boundaries and camera assignment | M | Invalid geometry/camera lists rejected; boundary drawn on a map | `sitemap/`, `components/map/SiteMap.jsx`, `ZonesPage.jsx` | `sitemap/tests.py` (7); browser check 16 Oct (3-click polygon saved) | Integrated |
| FR-20 | Automatic restricted-zone breach and over-occupancy alerts | M | Entering a RESTRICTED polygon unassigned, or exceeding max occupancy, raises one ZONE_BREACH per entry | `workers/mqtt_handlers.raise_zone_breaches`, `sitemap/geofence.py` | `workers/tests.py` ZoneBreachTests (9); e2e 16 Oct (telemetry into Crane Pit → live breach) | Integrated (GPS simulated by HTTP, no hardware) |
| FR-21 | Smart vest: GPS position, SOS button, LoRa link | M→deferred* | Physical SOS reaches the dashboard; delay and packet loss measured | Server: `workers/`, `run_mqtt_consumer`; `tools/vest_simulator.py` | `workers/tests.py` (incl. SimulatorLabelling 3), `tools/test_vest_simulator.py` (8); e2e 16 Oct: demo scenario → simulated breach + SOS, offline after silence | Software path integrated with simulator; **hardware deferred pending supervisor approval** (`docs/SCOPE_CHANGE_SMART_VEST.md`) |
| FR-22 | Vest telemetry is validated | M | Out-of-range latitude/longitude, a lone coordinate, or battery outside 0–100 returns 400 | `VestTelemetrySerializer` | `alerts/test_ingest.py` | Tested |
| FR-23 | Vest offline detection | S | No report within `VEST_OFFLINE_AFTER_SECONDS` shows the vest offline | `workers/presence.py`, `run_presence_monitor` | `workers/tests.py` PresenceTests (4); browser check (occupancy dropped to 0 after timeout) | Integrated |
| FR-24 | Worker activity history (check-in/out, idle, zone transitions) | M | Generated automatically and reconciled with annotated scenarios | `workers/activity.py`, `workers/timeline.py`, camera `SightingThrottle` + idle events, `WorkerTimeline.jsx`, report attendance tables | `workers/test_activity.py` (18), `test_activity_events.py` (5), report-service attendance tests; e2e 20 Oct: camera sightings + idle → 60 min on site, 20 min idle, auto check-out at last sighting; vest session open; timeline and PDF agree | Integrated (**no annotated real-camera scenario yet**) |
| FR-25 | Incident list, detail, resolve, CSV export | M | Resolve is broadcast; filters include every type | `frontend/src/components/incidents/` | Browser check 26 Oct on a throwaway database with one alert of every type (9 alerts): each of the 8 type filters and 4 severity filters returned exactly the seeded rows; vest search found the 2 vest alerts; row detail shows zone, source and description; an officer's resolve (API) appeared as RESOLVED in the Viewer's open list within 1.5 s without reload; resolve from the UI as Safety Officer; CSV export follows the active filter (FIRE → 1 row; all → header + 9 rows), captured in the page, not downloaded; 27 Oct: responsive table (vest under worker, camera column from 1280 px), fits a 1024 px window with Status and Resolve visible | Integrated |
| FR-26 | Dashboard KPIs and charts reflect recorded data only | M | Every displayed number reconciles to the API; nothing fabricated | `DashboardStatsView`, `KpiStrip.jsx`, `DashboardCharts.jsx`, `WorkerStatusGrid.jsx` | `workers/tests.py` DashboardStatsTests (3); browser check 16 Oct | Integrated |
| FR-27 | Incident and safety-performance reports in DOCX and PDF | M | Fixtures reconcile exactly; PDF produced; no unsupported percentages; period in the user's time zone | `report-service/lib/*`, `templates/*`, `backend/reports/` | `report-service/test` (12); `reports/tests.py` (6); e2e 16 Oct (both types, both formats via API → service; PDF inspected) | Integrated |
| FR-28 | Mobile app: login, alerts, resolve, worker status, push; site map, cameras, live pictures and danger areas | M | Android build receives a push and resolves an incident visible on web; the map, camera list and a camera's live picture match the web | `mobile/` (Expo SDK 58): Alerts (evidence frame, model, Open camera), Map (`SiteMapView` Leaflet page in a WebView, iframe on web; `lib/siteMap.ts`), Cameras (`useCameraMap`), camera screen (`LiveCameraView` with `react-native-svg` area outlines, Admin area switch, latest alerts via `alerts/?camera_id=&limit=`) | `mobile/__tests__` (25); web build checked 16 Oct (sign-in, live alerts, resolve, workers, sign-out) and 27 Oct (see ledger) | Integrated on web target (**device + push pending, C14**) |
| FR-29 | Alert evidence (snapshot, confidence, model version) | S | Each AI incident is traceable to its frame and model | `ai-module/evidence.py` (model id = weights name + SHA-256 prefix; JPEG of the raw frame ≤ 640 px), snapshot BLOB in `event_outbox.py`, `--no-snapshots` / `SITESAFE_SNAPSHOTS`; `Alert.model_version` (migration alerts 0012), `decode_snapshot` + `CameraEventView` (base64 JPEG ≤ 512 KB, stored once per `event_id`), `/api/alerts/{id}/snapshot/`, `ALERT_SNAPSHOTS_ENABLED`, `purge_alert_snapshots`; `AlertSnapshot.jsx`, `mobile/components/AlertSnapshot.tsx` | `alerts/test_evidence.py` (19), `test_evidence.py` (8), `test_event_outbox.py` snapshot cases (3), `mobile/__tests__/api.test.ts` image fetch (3); e2e 20 Oct on a throwaway database: synthetic frame → outbox → API (201, one 11 KB file), replay of the same `event_id` → 200 and no second file; frame, confidence and model version shown to a Viewer on web and on the mobile web build; `purge_alert_snapshots --days 0` removed the file and kept the alert | Integrated (**synthetic frame; not yet from a live camera run**) |
| FR-30 | Live camera grid for monitoring (all cameras, including a test webcam) | S | Every running camera appears live within seconds to Safety Officers and Admins, configured cameras that are not running show as offline, and Viewers cannot see video | `ai-module/live_feed.py`, `--no-live` / `SITESAFE_LIVE`, `--live-fps`; `alerts/live.py`, `CameraFrameView` (`/api/v1/camera-frames/`), `CameraListView` (`/api/v1/cameras/`), `CameraFeedConsumer` (`/ws/cameras/`), `LIVE_VIEW_ENABLED`; `pages/CamerasPage.jsx`, `hooks/useCameraFeed.js` | `test_live_feed.py` (7), `alerts/test_live.py` (11); e2e 27 Oct on a throwaway database: real pipeline (all detectors) on a test video as CAM-01 plus synthetic test frames as WEBCAM-TEST, both live in the grid at 5.0 frames/s in the browser with detections drawn; CAM-GATE (zone, not running) offline; enlarged view; pipeline 17.6 FPS while streaming; Viewer had no Cameras tab and saw the role notice | Integrated (**test video and synthetic frames; no physical camera or second machine yet**) |
| FR-31 | Worker location and zone head counts without a vest (camera-based, zones with several cameras) | S | A badge read by a camera places the worker in that camera's zone within seconds and as last seen after a minute; zone head counts never double-count overlapping cameras; one over-capacity alert per sustained crossing; a restricted-zone entry by an unassigned badge holder raises one breach | `workers/location.py` (place, zone_occupancy, check_capacity with hysteresis, sweeps), `Worker.location_*`, `Zone.camera_views_overlap`, `sitemap.Camera`, `CameraCountView` (`/api/v1/camera-counts/`), sightings every 15 s and people counts (`ai-module/latest_sender.py`); Workers page and mobile location, Zones page counts and overlap setting, live map labels (`zone_updated`) | `workers/test_location.py` (28), `test_activity_events.py` people counts (3); e2e 27 Oct (see ledger) | Integrated (**test videos with a printed test badge; no physical camera or real badge yet**) |
| FR-32 | Danger areas drawn on the live camera picture | S | An Admin draws an area on a camera's live view and it takes effect within 15 s without a restart; a person whose feet stay inside an active area for 1 s raises one alert with a snapshot (named if badged); walking past raises nothing; the area shows red in the live view while occupied; Safety Officers see areas but cannot change them | `sitemap.CameraArea`, `CameraAreaSerializer`, `CameraAreaViewSet` (`/api/v1/camera-areas/`), areas in `CameraConfigView`; `AlertType.DANGER_AREA` and its seeded rule; `ai-module/danger_areas.py` (foot point, `DangerAreaTracker`), `inference.py` (rules refresh 15 s, `draw_danger_areas`, banner); `components/cameras/DangerAreas.jsx` on the Cameras page; incident filter, simulate button, report-service type list, mobile label | `sitemap/test_camera_areas.py` (7), `test_danger_areas.py` (14), mobile label (1 assertion); e2e 27 Oct (see ledger) | Integrated (**test video; no physical camera yet**) |
| FR-33 | Cameras on the site map | S | An Admin places a camera (position, facing, view angle, range) and its view cone appears at once; every user sees cameras live, offline, or red for a minute after an alert; Safety Officers and Admins get a live thumbnail and a link to the camera's live view, Viewers no picture | `sitemap.Camera` placement fields, `CameraPlacementSerializer`, `sitemap/camera_map.py`, `CameraMapView` (`/api/v1/camera-map/`), `CameraPlacementView` (`PUT/DELETE /api/v1/camera-map/{id}/`), `camera_updated` event (placement, changed people count), `CameraLatestFrameView` (`/api/v1/camera-frames/latest/`); `components/map/CameraLayer.jsx`, `CameraPlacementPanel.jsx`, `hooks/useCameraMap.js`, `lib/geo.js`, dashboard `SiteMapCard.jsx`, Cameras page `?camera=` | `sitemap/test_camera_map.py` (11); e2e 27 Oct (see ledger) | Integrated (**test video; real camera positions pending, C13**) |
| FR-34 | Evidence snapshots in the incident and safety reports | S | Reports show the camera frames of the most severe incidents, each captioned with type, severity, time, camera, zone, worker, description and model version, and the incident log points to them; missing or unloadable snapshots are stated; the user can leave snapshots out, and the report history records which reports contain them | `report-service/lib/evidence.js` (selection, captions, loading), `lib/jpeg.js`, `fetchSnapshot` (user's token, API host only), `figures` blocks in `render-docx.js` / `render-pdf.js`, Evidence (incident) and Evidence by Zone (safety) sections, log Figure column; `include_evidence` on `/api/v1/reports/generate/`, `Report.includes_evidence`; Reports page option and history | `report-service/test/evidence.test.js` (9), `app.test.js` (2 new), `reports/tests.py` (3 new); e2e 27 Oct (see ledger) | Integrated (**test video frames**) |

## Non-functional requirements

| ID | Requirement | Target (proposed) | Evidence | Status |
|---|---|---|---|---|
| NFR-01 | Event-to-dashboard latency | p95 ≤ 2 s from commit on a local network | `tools/measure/latency.py`, 20 Oct: 100/100 delivered, p50 32 ms, p95 42 ms (PostgreSQL, single host) | **Met** (local host; LAN not yet measured) |
| NFR-02 | Outage tolerance | No lost or duplicated events across a 5-minute API outage and sender restart | `tools/measure/recovery.py`: first run 60.3 s (FAIL, 60 s ceiling) → ceiling lowered to 30 s → 30.0 s and 30.2 s, 100/100 stored once, 0 lost, 0 duplicated | **Met** |
| NFR-03 | Security of producers | No anonymous write endpoints; no credentials in source | `alerts/test_ingest.py`, `test_inference_config.py` | Tested |
| NFR-04 | Inference throughput | ≥ 10 FPS with all detectors on the demo machine | `tools/measure/fps.py`, Apple M4 at 1280×720: mps 13.4 and 15.7 FPS; cpu 9.8 and 10.1 FPS. Pipeline now defaults to mps. With the fire model (27 Oct, commit `fae1367`, clean tree): mps 15.8 and 16.1 FPS, cpu 10.4 and 10.2 FPS; fire stage p50 18 ms (mps) every 5th frame | **Met on mps with all detectors** (cpu marginal) |
| NFR-05 | Soak | 2-hour full-stack run with controlled disconnect | `tools/measure/soak.py` 5-min validation: 146 probes, 0 missed, reconnect 1.2 s; API memory 64→92 MB in 5 min (warm-up; needs the 2 h run) | **Not met yet** (2 h run pending on demo setup) |
| NFR-06 | Reproducible setup | Fresh machine reaches a working demo from the README | README updated 16 Oct | Not verified |
| NFR-07 | Code quality gate | Backend, AI and report-service tests pass; frontend build passes, lint clean | backend 237 (SQLite and PostgreSQL), ai-module 144, fire tools 7, report-service 23, mobile 25, vest simulator 8, measurement and clip scoring 21 = 465 pass (27 Oct); frontend lint clean, build OK; mobile lint and tsc clean | Met |

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

```text
Phase / task IDs: Stage 2 (honest dashboard, worker forms, map zone editor, ZONE_BREACH,
  vest offline timeout, lint)
Status: tested; browser-checked on a throwaway SQLite database; not run against PostgreSQL
Requirement IDs covered: FR-03, FR-18, FR-19, FR-20, FR-23, FR-25, FR-26, NFR-07
Commit / working-tree reference: uncommitted, branch stage-0-1-security-events, 16 Oct 2026
Files changed and migration notes:
  backend: workers (Worker.vest_id removed, SmartVest.worker is the only link; presence.py;
  run_presence_monitor; zone breach logic; telemetry fields read-only in the registry),
  sitemap (risk-ordered overlap, observed occupancy), alerts (DashboardStatsView rewritten)
  migrations: workers 0004 (moves each Worker.vest_id into a SmartVest; a vest already
  assigned to someone else keeps its assignment and the conflict is printed), 0005
  (SmartVest.battery_level nullable, "unknown" until reported). Not applied to dev PostgreSQL.
  API change: workers now take `vest` (SmartVest id) instead of a `vest_id` string; `vest_id`
  stays as a read-only field. Zone `current_occupancy` now means observed by GPS;
  `worker_count` means assigned.
  frontend: fabricated vitals/last-seen/charts/sparklines/compliance %/site list removed;
  KPIs and charts from /dashboard/stats/; Workers page drawer; Leaflet site map + boundary
  editor (leaflet 1.9.4, react-leaflet 5.0.0; OpenStreetMap tiles need internet); role gating;
  FALL filter and simulator button; lint fixes
Tests run (16 Oct 2026):
  backend → 120 OK; ai-module → 22 OK; frontend lint → clean; build → OK
  browser: dashboard figures, worker registration, map render, zone drawn and saved,
  automatic restricted-zone breach from telemetry, occupancy expiring with vest timeout
Known defects / limitations:
  - Map tiles come from tile.openstreetmap.org; offline demos show polygons on a blank map.
  - Reversing workers 0004 fails if more than one worker exists (re-added unique column).
  - Report service still uses the old compliance % (Stage 4 / FR-27).
  - Camera alerts have no worker identity, so camera-only zones cannot raise ZONE_BREACH.
Human inputs still needed: real site coordinates for zones; supervisor view on the
  "mean time to resolve" KPI replacing the unsupported compliance %
Next independent task: Stage 3 (dataset remediation / retraining) or Stage 4 (QR, PDF reports)
```

```text
Phase / task IDs: Stage 4 part 1 (QR worker identification; PDF reports with defined metrics)
Status: tested; integration-checked on a throwaway SQLite database; QR not tested with a physical camera
Requirement IDs covered: FR-10, FR-27 (and zone attribution for FR-20 alerts)
Commit / working-tree reference: uncommitted, branch stage-0-1-security-events, 16 Oct 2026
Files changed and migration notes:
  backend: Worker.badge_code (migration workers 0006 gives each existing worker its own
  random code), badge endpoint, camera events accept badge_code, alert zone_name falls back
  to the zone containing the alert's GPS location, alert/activity ?start_date/?end_date/?tz
  local-day filtering, reports: file_format (migration reports 0002), report stored before
  being returned, upstream errors relayed, content type verified; reports/__init__.py
  added (its tests were not being discovered); dead docx_builder.py removed
  ai-module: identity.py (OpenCV QR decoding, person association, ambiguity rules),
  per-person PPE grouping and cooldown, badge on fall/inactivity events, --no-qr
  report-service: metrics.js (no compliance %), shared document model rendered by
  render-docx.js and render-pdf.js (pdfkit 0.20.2), server-side period filtering, pagination
  following, CORS removed (service is called only by the backend), node:test suite
  frontend: Print / Reissue badge (qrcode 1.5.4), report format selector, local-date defaults
Tests run (16 Oct 2026): backend 134 OK; ai-module 35 OK; report-service 12 OK; frontend lint
  clean, build OK; e2e: real QR decode → outbox → API attribution; reports in both formats
Known defects / limitations:
  - QR reading range, angle and lighting are not yet measured; small or distant badges will
    not decode at the default detector input size.
  - Identity uses box overlap between samples; crossing people can swap tracks.
  - The incident log is capped at 1000 rows per report (the report states this).
Human inputs still needed: print badges and record a physical QR test (distance and lighting);
  supervisor sign-off on replacing the compliance % with the defined metrics
Next independent task: Stage 4 part 2 — mobile app (React Native) — or Stage 3 dataset work
```

```text
Phase / task IDs: Stage 4 part 2 (React Native mobile app)
Status: tested; web target integration-checked against a throwaway backend; not yet run on a
  physical phone; push not verified (needs Firebase project and an Android development build)
Requirement IDs covered: FR-28, FR-16 (client side)
Commit / working-tree reference: uncommitted, branch stage-0-1-security-events, 16 Oct 2026
Files changed:
  mobile/: Expo SDK 58 tabs template; template LICENSE, plugin-enabling .claude/settings.json,
  sample screens and unused font removed; AGENTS.md/CLAUDE.md kept (Expo's agent guidance)
  lib/api.ts (JWT + single-flight refresh, sign-out on failure), lib/storage.ts (SecureStore,
  localStorage on web), context/Live.tsx (socket, 4401 renewal, backoff, resync, background
  close), lib/push.ts (Android FCM token registration, channel, tap-to-open), screens:
  login, alerts (open/all, live), alert detail + resolve (role-gated), workers, settings
  backend: websocket allows clients without an Origin header (native apps; JWT still
  required); FCM messages use the high-importance Android channel
Tests run (16 Oct 2026): mobile jest 13 OK, eslint clean, tsc clean; backend 135 OK
Known defects / limitations:
  - iOS gets no remote push (backend sends FCM only); web/iOS rely on the live socket.
  - The server address is entered by hand; no discovery.
  - Reports, zones and worker editing remain web-only by design.
Human inputs still needed: Firebase project (google-services.json + service account),
  an Android phone for a development build, and a recorded push/resolve test
Next independent task: Stage 4 part 3 (smart vest firmware) or Stage 3 (dataset/retraining)
```

```text
Phase / task IDs: Stage 5 part 1 (PostgreSQL verification, Docker, CI) and fire/smoke (FR-09)
Status: tested on PostgreSQL 18 and SQLite; dev database backed up (backups/) and migrated;
  docker-compose and CI written but not run (Docker not installed; CI not pushed)
Requirement IDs covered: FR-09; NFR-06 (setup) partially
Commit / working-tree reference: branch stage-0-1-security-events, 20 Oct 2026
Fixes found by PostgreSQL: vest row lock across a nullable join failed on every telemetry
  message; inline notification test reset the connection; migration left 100% battery on
  vests that never reported
Tests run (20 Oct 2026): backend 146 OK on PostgreSQL and SQLite; ai-module 43 OK;
  fire prep 4 OK; report-service 12 OK; frontend lint clean, build OK
Known defects / limitations:
  - No trained fire/smoke weights yet; image-level metrics from the notebook are not alert
    quality — evaluate on recorded licensed clips including hard negatives.
  - Camera-only zones need camera_ids for permits to apply; an unzoned camera is never covered.
Human inputs still needed: choose and licence-check a fire/smoke dataset, run the notebook,
  install Docker Desktop to try the compose stack, push the branch to run CI
Next independent task: workforce activity automation (FR-24), then measurement tooling (NFR-01..05)
```

```text
Phase / task IDs: workforce activity automation (FR-24)
Status: tested on PostgreSQL and SQLite; e2e on throwaway database; dev database backed up
  and migrated (workers 0007)
Changes: Worker.last_seen_at/source; ActivityLog.timestamp now settable (event time);
  check-in on first evidence, automatic check-out dated to last sighting, late-event
  merging, isolated late sightings as their own closed session; idle start/end from camera
  inactivity for identified people; timeline/daily APIs; summary endpoint rebuilt on them;
  web timeline drawer; report attendance per worker and per day; zero durations shown as 0
Tests (20 Oct 2026): backend 164 OK (PostgreSQL and SQLite); ai-module 48 OK; report-service
  13 OK; frontend lint clean, build OK
Known limitations: timelines look back 2 days for open intervals; vest GPS is not used to
  detect idleness; track identity can swap when identified people cross
Human inputs still needed: record a short annotated scenario (badge visible, idle, leave)
  to validate against the timeline
Next independent task: measurement tooling for Chapter 5 (NFR-01..05)
```

```text
Phase / task IDs: Stage 5 part 2 — measurement tooling for Chapter 5 (NFR-01, 02, 04, 05)
Status: tools tested and run; evidence in docs/evidence/CHAPTER5_MEASUREMENTS.md
Measured on: Apple M4, 16 GB, PostgreSQL 18, single host, separate database sitesafe_measure
Findings acted on: outbox retry ceiling 60 → 30 s (recovery 60.3 s → 30 s); inference now
  defaults to the GPU (CPU default gave 9.8 FPS)
Not yet measured: LAN latency to a second device; the 2-hour soak with camera, MQTT consumer and
  presence monitor running; FPS with the fire model; FPS on the actual demo laptop if different
Human inputs still needed: run soak.py for 2 h on the demo setup; repeat fps.py once
  models/fire_smoke.pt exists; regenerate the tables with make_tables.py
Note: earlier result files record "uncommitted changes"; for the c79cc95 runs the only
  modified tracked file was the local .claude/launch.json. Results now list modified files.
```

```text
Phase / task IDs: Stage 6 — report V8 (corrections to Chapters 1–3, design diagrams, Chapters 4–6 rebuilt)
Status: V8 .docx built from V7 (V7 unchanged); rendered with LibreOffice 26.8 (69 pages), measured page
  numbers written (120 contents/list entries checked against the render, 0 mismatches), pages checked visually;
  .docx validates against the OOXML schema
Requirement IDs covered: report deliverable (M15); Chapter 5 cites FR-01..FR-29 and NFR-01..NFR-05 from this matrix
Files: docs/build_report_v8.py, docs/report_v8_content.py, docs/figures/make_figures.py (component,
  deployment, ERD, camera classes, two sequences, training pipeline; names checked against the code),
  docs/figures/screenshots/, docs/REPORT_V8_CHANGES.md (change list and items the team must check)
Counts used in the report (re-run 20 Oct 2026): backend 164, ai-module 50, fire prep 4, report-service 13,
  mobile 13, tools 16 = 260, all passing; audit_dataset.py: 573 cross-split source groups,
  30 cross-split exact duplicates, 69 conflicting duplicate groups (strict FAIL)
Body length: 10,093 words (guideline 8,500–10,500); tables add 2,426
Human inputs still needed: supervisor sign-off on the vest scope change; verify the Chapter 2 citations
  and the Labour Force Survey figure; title-page date; approval/declaration/Turnitin pages
Next independent task: open V8 in Microsoft Word to confirm pagination there; add the department's
  approval, declaration and Turnitin pages
```

```text
Phase / task IDs: FR-05 — per-person PPE violation episodes
Status: tested; full pipeline exercised headless on a synthetic clip; not scored on annotated video
Requirement IDs covered: FR-05
Changes: ai-module/ppe_episodes.py (EpisodeTracker: per-class box tracks matched by centre distance
  relative to box size, or by QR badge; confirmed after 1 s and >= 3 frames with gaps <= 0.5 s; one alert
  per episode; closed after 10 s unseen); inference.py: group_violations (merged unidentified people per
  class) replaced by badged_violations, the 15 s PPE cooldown replaced by the tracker, new CLI flags
  --ppe-persistence and --ppe-clear-seconds; COOLDOWN_SECONDS now applies to VEHICLE_PROXIMITY only;
  CI runs test_ppe_episodes; report V8 text and Tables 5.1, 5.2 and 6.1 updated (275 tests)
Tests (20 Oct 2026): ai-module 65 OK (was 50); backend 164 OK
Known limitations: episodes are camera-local; an unidentified person who leaves and returns after
  clear_seconds raises a new alert; very fast motion (> one box size per frame) splits an episode
Human inputs still needed: an annotated clip with known episodes to measure duplicate and missed alerts
```

```text
Phase / task IDs: FR-29 — alert evidence (snapshot, confidence, model version)
Status: integrated on a throwaway SQLite database with a synthetic frame; not yet exercised from a live
  camera run; dev PostgreSQL database NOT migrated (alerts 0012 adds Alert.model_version)
Requirement IDs covered: FR-29
Changes: ai-module/evidence.py (model_version: weights file name + first 12 hex of SHA-256; encode_snapshot:
  raw frame scaled to <= 640 px, JPEG q80; FrameSnapshot encodes at most once per frame and only after the
  rule check); event_outbox.py stores the JPEG as a BLOB beside the event (existing queue files upgraded in
  place) and sends it base64 in the payload's snapshot field; inference.py adds model_version per detector
  (PPE, COCO for proximity/inactivity, pose, fire) and --no-snapshots / SITESAFE_SNAPSHOTS=0
  backend: Alert.model_version; CameraEventSerializer accepts model_version and a base64 JPEG snapshot
  (JSON chosen over multipart so the outbox replays one document): strict base64, <= ALERT_SNAPSHOT_MAX_BYTES
  (512 KB), Pillow-verified JPEG, <= 4096 px per side; file written once for a new event, deleted if the
  insert loses a race, never written for duplicates or suppressed events; ALERT_SNAPSHOTS_ENABLED=False
  discards images; AlertSerializer.snapshot is the API path, not the media URL; GET /api/alerts/{id}/snapshot/
  serves the JPEG with the alert's read permission (Viewer and up); purge_alert_snapshots (default
  ALERT_SNAPSHOT_RETENTION_DAYS=30, --days, --dry-run); deleting an alert deletes its image
  clients: web incident detail and mobile alert detail show the evidence frame, confidence and model
  report: Tables 4.7, 4.8, 4.9, 5.1, 5.2, 5.7, 5.8, Sections 4.6.2, 4.10, 6.4 and totals updated (308
  tests); table rows no longer split across pages (cantSplit); rebuilt, 69 pages, 120 contents/list entries
  checked against the render, 0 mismatches; .docx validates against the OOXML schema
Defect found end to end: DRF answered 406 to the mobile client's Accept: image/* before the view ran; the
  snapshot action now ignores the Accept header (errors still JSON); regression test added
Tests (20 Oct 2026): backend 183 OK (SQLite and PostgreSQL); ai-module 76 OK; mobile jest 16 OK, eslint and
  tsc clean; frontend lint clean, build OK
Known limitations: the snapshot is the whole frame, not a crop, so it can show bystanders; the camera outbox
  can hold up to ~800 MB of snapshots at its 10,000-event cap; retention needs a scheduled job (cron) — none
  is defined in docker-compose; DEBUG=True serves media/ publicly (random file names, not authenticated)
Human inputs still needed: agree a retention period and whether snapshots are allowed on site; run
  migrate on the dev database; one live camera run to confirm a real alert carries its frame
```

```text
Phase / task IDs: FR-05 tuning from the first live webcam run (21 Oct 2026)
Status: tested; tuned against box positions recorded in that run; not re-run live yet
Finding: one person, 55 s, 13 alerts (9 AI, 4 forced test). The detector reported the same body part
  as two same-class boxes overlapping by IoU 0.50-0.63 (Ultralytics NMS keeps boxes below 0.7), so one
  person became two episodes per item, and the weaker box (conf 0.22-0.45, near the 0.15 candidate
  threshold) kept reopening episodes after the 10 s close time
Changes: ppe_episodes.merge_duplicates (same-class boxes with IoU >= 0.4 merged per frame, never across
  different badges); DEFAULT_CLEAR_SECONDS 10 -> 30; 7 new tests built from the recorded boxes
  (old settings: 4 alerts in a 60 s replay, new: 2, one per missing item)
Also fixed: workers.test_activity timeline test depended on the time of day (failed before 12:00 PKT)
Tests (21 Oct 2026): backend 183, ai-module 83, fire prep 4, report-service 13, mobile 16, tools 16 = 315 OK
Human inputs still needed: repeat the webcam run to confirm, then record an annotated clip
```

```text
Phase / task IDs: FR-05 second live webcam run (21 Oct 2026)
Status: tested on the recorded boxes; third live run still to confirm
Finding: 25 s, 5 alerts. One was a real second person at the frame edge (correct). One helmet alert
  repeated: the head came as three boxes; when the strongest dropped out the other two overlapped at
  IoU 0.26 and became two tracks
Change: same-class boxes also merge when one centre lies inside the other and IoU >= 0.2
  (DEFAULT_NESTED_IOU); 3 new tests from the recorded boxes (head pattern: 2 alerts -> 1; edge person
  still separate; side-by-side heads stay separate)
Tests (21 Oct 2026): ai-module 86 OK; total 318
```

```text
Phase / task IDs: FR-03 viewer path, FR-25 incident log
Status: both Integrated; browser checks on a throwaway SQLite database (worktree at stage tip d1bb33f),
  dev database untouched
Fixture: admin, safety officer and viewer test accounts; 1 zone, 1 worker with a vest; 9 simulated alerts,
  one per type plus a resolved FALL
FR-03 (Viewer, every page): no resolve, register, edit, generate, permit or alert-rule controls; Alert
  Configuration read-only; vest assignment disabled; Reports shows the role notice; Zones labelled
  read-only; own notification preferences and password remain editable by design; API: Viewer resolve 403,
  report generation 403. As Safety Officer the same pages show Resolve, Generate Report, Register
  worker/vest, Edit and Issue permit (zone editing stays Admin-only)
FR-25: 8 type and 4 severity filters each matched the seeded rows exactly (no LOW alert seeded); vest
  search; row detail; resolve broadcast to the Viewer's open list in < 1.5 s without reload; UI resolve
  as Safety Officer (open badge 7 -> 6); CSV export respects filters (captured in the page)
Known limitation: at a 1024 px window the incident table (875 px) overflows its 734 px area, so Status
  and Resolve need a sideways scroll
Not done: report V8 Tables 5.2 and 6.1 still show the older FR-03/FR-25 wording; update them after the
  report branch (claude/competent-moore-5fa363) is merged
```

```text
Phase / task IDs: FR-09 fire/smoke model; NFR-04 re-measure with fire
Status: model trained and installed; FR-09 stays Integrated, now with a trained model (image-level metrics only)
Training: ai-module/fire/train_fire_smoke_kaggle.ipynb (same recipe as the Colab notebook: YOLO11s from yolo11s.pt,
  640 px, batch 16, AdamW lr 0.001, seed 42, deterministic, patience 20; workers 4). Ran unattended as Kaggle
  version v1, Tesla T4, 26-27 Oct: 96 epochs in 7.0 h (early stop; best epoch 76), time guard (10 h) not
  triggered. Split identical to the 22 Oct local and Colab runs (15,469 / 1,738 / 4,294 images, 26 skipped for
  invalid labels). Earlier attempts: local mps run 22 Oct stopped in epoch 1 (process ended); Colab free tier
  disconnected around epoch 46 (no checkpoint saved); neither produced weights.
Notebook fixes found by local dry runs and the first Kaggle attempt: Path.rglob does not follow Kaggle's
  symlinked inputs on Python < 3.13 (now os.walk followlinks); copied images kept read-only mode so truncated
  JPEGs were dropped instead of repaired; reading ~43k files serially from Kaggle's input storage was too slow
  (now a parallel copy to local disk first)
Model: models/fire_smoke.pt, sha256 4bdbf70218da49dac240720a4c9928f2853b954262d2a4ef12c3b0eee2e38d10;
  models/fire_smoke_v1_export/ holds args.yaml, results.csv, dataset manifest, run manifest, held-out metrics.
  The 22 Oct aborted local run's manifest was kept as models/fire_smoke_v1_local_aborted_export/
Held-out test (once): P 0.775, R 0.720, mAP50 0.787, mAP50-95 0.459; fire P 0.720 R 0.651 mAP50 0.726;
  smoke P 0.831 R 0.789 mAP50 0.848. Re-evaluated on the Mac (mps): identical to 3 decimals
Alert path: real detections through FireTracker at the pipeline's sampling (every 5th frame at 30 FPS) on
  still images: fire image -> FIRE CRITICAL and SMOKE HIGH once each after 2.0 s; negative image -> none
NFR-04 (27 Oct, all detectors incl. fire, 1280x720, 517 PPE test images): mps 15.8 / 16.1 FPS, cpu 10.4 /
  10.2 FPS; docs/evidence/CHAPTER5_MEASUREMENTS.md regenerated (throughput section only)
Known limitations: fire recall 0.651 at image level; D-Fire is not construction footage; no video, hard-negative
  (sunset, orange vest, welding sparks, dust) or alert-level evaluation yet
Human inputs still needed: confirm D-Fire's licence and cite it; record or collect licensed clips including
  hard negatives to evaluate alerts; report V8 Chapters 4-6 still describe fire as untrained
Not included: the 22 Oct 2 h soak result in tools/measure/results/ (soak_20261022T144721Z.json, PASS) was run
  with uncommitted soak.py changes in the main checkout; its tables and NFR-05 status are left to that work
```

```text
Phase / task IDs: FR-30 live camera grid (new requirement, requested 27 Oct)
Status: Integrated on a throwaway database with a test video and synthetic frames
Decisions (user, 27 Oct): Safety Officers and Admins only; the feed shows the annotated view (detections drawn)
Design: each camera running inference.py sends its display frame as a 640 px JPEG (q70) at up to 5 FPS from a
  background thread (live_feed.LiveFeed: newest frame wins, never queued, 5 s backoff on errors, no outbox).
  POST /api/v1/camera-frames/ (camera token, image/jpeg <= 256 KB, header-checked JPEG <= 1920 px, server
  limit 15 FPS -> 202 dropped) keeps the latest frame per camera in the cache for 30 s (Redis when REDIS_URL
  is set) and relays it to /ws/cameras/ (JWT; Viewer 4403, anonymous 4401); nothing is stored on disk.
  GET /api/v1/cameras/ lists zone cameras, camera-token cameras and cameras seen live (offline after 5 s).
  Web: Cameras tab (hidden for Viewers), responsive grid, click to enlarge, Esc to close
Switches: --no-live / SITESAFE_LIVE=0 on a camera; LIVE_VIEW_ENABLED=False on the server
Tests (27 Oct 2026): ai-module 93 OK (7 new); backend 194 OK on SQLite and PostgreSQL (11 new); frontend lint
  clean, build OK
E2E: inference.py with all detectors (fire included) on a 40 s test video built from PPE test images, display
  stubbed, as CAM-01, 5 runs: 400 frames each, 123-145 live frames sent per run, 0 failed, 7 alerts queued per
  run, 0 rejected; synthetic labelled test frames as WEBCAM-TEST; browser as Safety Officer: both tiles live at
  5.0 frames/s, CAM-GATE (zone camera, not running) offline; enlarged view shows boxes and banner; pipeline
  17.6 FPS while streaming. As Viewer: no Cameras tab, role notice at /cameras, no frames fetched
Known limitations: every frame goes through the API process (about 5 x 30-60 KB/s per camera per viewer), fine
  for a few cameras on a LAN, not a replacement for an NVR; no recording or playback; the main checkout has
  uncommitted inference.py changes (video source, --no-display) that will need merging with this change
Human inputs still needed: run with the real webcam and, ideally, a second machine as a camera
```

```text
Phase / task IDs: Phase 0 — one clean codebase (27 Oct)
Status: all work merged on stage-0-1-security-events; every suite passes on the merged branch
What was consolidated:
  - main checkout's uncommitted work from 22 Oct, reviewed and committed in five commits: clip evaluation
    (inference --video-clock/--events-out/--loop/--no-display, tools/measure/evaluate_clip.py), soak --pids
    and MEDIA_ROOT, fire dataset tools (Parquet unpacker, local trainer), model evidence folders now tracked
    (weights ignored), and the 22 Oct completion plan
  - claude/beautiful-mclaren-ab41fd (fire model and Kaggle notebook, live camera grid FR-30, FR-03/FR-25
    checks) and claude/competent-moore-5fa363 (V8 report: requirements, workflow, front matter, appendices)
Found and fixed during review: with --video-clock, worker activity events were dated about a day in the past
  (rejected by the API); wall_clock() now takes the pipeline's current time. The Parquet unpacker needed
  pyarrow, which was not declared; it is now in ai-module/requirements-vision.txt and its test runs in CI,
  as does the clip-scoring test. Clip evaluation runs with --no-live.
Conflict resolution: show() presents the operator's view in the preview window (unless --no-display) and
  the dashboard live view, so a headless camera still streams
Tests (27 Oct 2026, merged branch): backend 194 OK on SQLite and PostgreSQL; ai-module 98; fire tools 7;
  vest simulator 8; measurement and clip scoring 19; report-service 13; mobile 16 (lint, tsc clean);
  frontend lint clean, build OK — 355 in total
Housekeeping: 14 alert snapshots written while the stack ran from a worktree were moved to the main
  checkout's backend/media; all 37 snapshots referenced by the dev database are present
Not done in Phase 0: docs/SiteSafe_FYP_Report_V8.docx/.pdf are the build from commit f1d917f; the merged
  report_v8_content.py also carries the reworded FR-05 evidence line. The report is rebuilt (in Word) in
  Phase 4 together with the fire, evidence, live-grid and zoning updates.
```

```text
Phase / task IDs: Phase 1 — PPE over-alerting (FR-05) and the incident table (FR-25)
Status: FR-05 fix tested (unit tests, pipeline run); not yet scored on a recorded webcam clip (skipped by the
  owner, 27 Oct); FR-25 Integrated
Finding: on the live webcam (27 Oct) one person raised no-helmet three times and no-goggles twice within
  seconds. Episodes were tracked per box by centre distance; a head box moving more than its own size (leaning
  towards the camera) started a new episode, which alerted after the 1 s persistence.
Fix: identity.IdentityTracker now gives every followed person a stable track_id, badge or not, and runs whenever
  the person detector runs (QR decoding stays optional). Each violation carries the containing person's id
  (person_at, ambiguous -> None). EpisodeTracker matches by badge, then person, then distance; same-class boxes
  on one person in a frame are one violation; a track of another person still in view is never taken by
  distance; a re-found person (new id) near a lost person's open episode continues it. Without a person
  detector, distance alone decides, as before.
Tests: test_ppe_episodes 31 (6 new), test_identity 21 (4 new); ai-module 108 OK. Pipeline main() run headless on
  the 40-scene test video, with and without --no-qr: no errors; before/after on the same settings give the same
  8 alerts at the same times (no change where people are separate and still)
FR-25: incident table responsive: vest ID under the worker name, Camera column from 1280 px (always in the row
  detail and CSV); DataTable takes a minimum width per table. Browser 27 Oct: at 1024x768 the table is 734 px in a
  734 px area with all 25 Resolve buttons visible; at 1440 px the Camera column returns, no overflow
Also: tools/measure/record_clip.py records evaluation clips at the camera's measured frame rate (2 tests)
Human inputs still needed: a recorded webcam clip with annotations to score FR-05 on real video
```

```text
Phase / task IDs: Phase 2 item 1 — FR-31 worker location without a vest; zones with several cameras
Status: Integrated on a throwaway database with test videos (a dataset image with a printed test badge, a
  crowd clip); not yet with a physical camera and a real printed badge
Design: a camera badge sighting places the worker in that camera's zone (a camera belongs to one zone, enforced
  by the zone API); sightings every 15 s; current for CAMERA_PRESENCE_SECONDS (60), then "last seen" and a
  ZONE_EXIT dated to the last sighting (presence monitor). Vest GPS uses the same location model; a current
  camera sighting takes precedence over GPS. Zone head count = max(identified workers placed there, camera
  people counts combined by largest count when views overlap, else sum); counts older than 30 s drop out.
  Over capacity uses hysteresis: alert after 10 s over the limit, re-armed after 60 s back within it.
  Restricted-zone breach from cameras for unassigned badge holders. Unidentified people in restricted zones
  are counted but raise nothing until decision B1 (docs/PENDING_FOR_YOU.md).
Visible: worker cards and mobile Workers tab show "In Bay 1 · CAM-02" / "Last seen in ...", Workers page and
  dashboard "on site" count camera-seen workers (split by camera/vest), Zones page shows each head count with
  its basis ("cameras 2 (largest of 2) · 1 identified") and an Over capacity badge, zone form gains "These
  cameras can see the same people", map keeps live head-count labels; all update over the zone_updated event
Found and fixed during the live run:
  - worker location time was a raw datetime in socket payloads: every worker update closed dashboard sockets
    (1011). Now ISO text; a test checks worker and zone payloads encode as plain JSON
  - over-capacity alerted once per crossing, which on a noisy count gave 5 alerts in 4 minutes; replaced by
    hysteresis, and capacity is now evaluated on every count report, not only on changes (a steady crowd never
    reached its confirm time between monitor sweeps)
E2E (27 Oct, throwaway SQLite database, real pipeline, all detectors): Bay 1 with CAM-01 (badge clip) and
  CAM-02 (40-scene clip, then crowd clip), Crane (restricted) with CAM-09. Badge holder placed in Bay 1 by
  CAM-01 ("ON SITE · In Bay 1 · CAM-01" on the Workers page, no vest; dashboard "1 seen by camera, 0 by vest");
  head counts followed the cameras live on the Zones page and map. Crowd clip (9 people for 25 s of every 100 s)
  over 250 s: 3 crowd periods, 3 over-capacity alerts, each 10-15 s into the period, re-armed between them. Badge
  clip as CAM-09: Bay 1 exit + Crane entry, one HIGH breach naming CAM-09; after 60 s without a sighting the
  monitor recorded the Crane exit dated 11:41:28 (last sighting), API location current=false
Tests (27 Oct): backend 223 OK on SQLite and PostgreSQL (29 new); ai-module 111 (people counts 3, shared
  LatestSender); mobile 17 (location); frontend lint clean, build OK — 400 in total
Known limitations: zone-level only (no position inside a camera view; Phase 2 item 2); counting relies on the
  person detector, which misses occluded people; identity needs a readable badge (physical range test pending,
  C1); throwaway SQLite reported "database is locked" under concurrent camera writes (PostgreSQL in real use)
Migrations: sitemap 0004 (Camera, zone overlap and capacity state), workers 0008 (location fields), workers 0009
  (fills location from each worker's latest vest zone log); the dev database still needs `migrate`
```

```text
Phase / task IDs: Phase 2 item 2 — FR-32 danger areas drawn on the live camera picture
Status: Integrated on a throwaway database with a test video (dataset image with a printed test badge); not yet
  with a physical camera
Design: an area is a polygon of 3-24 corners in picture fractions (0-1), per camera, with a name (unique per
  camera), a severity and an on/off switch. Admins draw them by clicking on the enlarged live view; everyone
  signed in can read them (API: Admin write). The camera gets its active areas with its alert rules, refreshed
  every 15 s. A person is inside when the bottom-centre of their box (their feet) is inside the polygon. One
  DANGER_AREA alert per person per entry: 1 s inside with at least 2 samples and no gap over 1 s; again only
  after 10 s outside; a person lost and re-found nearby under a new track continues their entry. Alerts carry
  the snapshot, model version and badge holder like other camera alerts, and apply to anyone (badge or not),
  independent of decision B1. The live view outlines areas in amber, fills an occupied area red and shows a
  "DANGER AREA - name" banner (ranked after a fall, before vehicle proximity). A global rule (seeded on,
  push and email) can switch the type off.
E2E (27 Oct, throwaway SQLite database, real pipeline with all detectors, badge clip as CAM-01): as the test
  Admin, drew "Loading bay edge" (4 corners, CRITICAL) on CAM-01's enlarged view; it appeared at once on the
  page. Within the 15 s refresh the camera filled the area red and showed "DANGER AREA - Loading bay edge".
  Two CRITICAL DANGER_AREA alerts, each with a snapshot: the badge holder, identified by QR badge (inside
  1.0 s), and a second person in the area without a readable badge (inside 1.1 s); no repeats while both
  stayed inside. Incident log filter "Danger area" listed both. As the test Safety Officer the area and the
  red overlay showed, with no draw, switch or delete controls. No console errors after a reload.
Tests (27 Oct): backend 230 OK on SQLite and PostgreSQL (7 new); ai-module 125 (14 new); mobile 17 (label
  assertion); fire tools 7, report-service 13, vest simulator 8, measurement 21; frontend lint clean, build OK
  — 421 in total
Known limitations: the foot point assumes the person stands on the ground plane the area was drawn on (a
  person on a raised platform in front of an area can count as inside); a partly hidden person's box may end
  above their feet; areas belong to one camera's view and move if the camera is moved, so they must be
  redrawn after re-aiming it
Migrations: alerts 0013 (DANGER_AREA type), alerts 0014 (seeds the global rule), sitemap 0005 (CameraArea);
  the dev database still needs `migrate`
```

```text
Phase / task IDs: FR-07 vehicle proximity over-alerting (found in the FR-32 live run)
Status: fix tested (unit tests, pipeline runs on two test videos); no live camera run yet
Finding: in the FR-32 live run (27 Oct) one worker beside a car in the test clip raised 14 proximity alerts in
  about 3 minutes. The tracker re-armed on the first sample without a breach, and the car's detection drops
  out for up to 4 s at a time, so only the camera-wide 15 s cooldown limited it. The cooldown also merged
  two workers at risk into one alert.
Fix: proximity.ProximityTracker now keeps one encounter per person (identity.IdentityTracker track ids,
  badge or not): confirmed after 3 samples near a vehicle with no gap over 1 s, one alert at its closest
  point so far, ended only after 15 s not near any vehicle. A person re-found under a new track id within
  5 s, within one person-height, continues their encounter. The camera-wide cooldown (COOLDOWN_SECONDS) is
  removed; the alert carries the badge holder like the other person alerts.
Also fixed: danger areas (FR-32) and proximity both continued an entry for "a re-found person" with no time
  limit, so a different person at the same spot 14 s later raised nothing (seen on the 40-scene video at
  28.7 s). Both now only re-find within 5 s (REFOUND_SECONDS); a test for each.
Evidence (headless pipeline, --video-clock, all detectors, same settings before and after):
  - test clip with a printed badge, 60 s looped 3 times (180 s): VEHICLE_PROXIMITY 10 -> 2 (the badge
    holder, CRITICAL, named; the second person, HIGH); PPE 2 -> 2
  - 40-scene test video (40 s): VEHICLE_PROXIMITY 2 -> 5 (13.7 s: four people beside two cars in one street
    scene, each alerted; 28.7 s: one person in a later scene); PPE 5 -> 5, smoke 1 -> 1
  Replays of the recorded detector output through old and new logic give the same counts; with a clear time
  of 5 s the looped clip re-alerts (8), from 10 s on it does not (2).
Tests (27 Oct): ai-module 144 (test_proximity 18, moved from backend/alerts and rewritten for encounters;
  danger areas 15); backend 221 (the 9 moved tests leave it) — 431 in total
Known limitations: proximity is measured in the image (person-heights), not in metres, so a worker in front of
  a distant vehicle can read as close (unchanged); a busy scene gives one alert per person near a vehicle
```

```text
Phase / task IDs: Phase 2 item 3 — FR-33 cameras on the site map
Status: Integrated on a throwaway database with a test video; real camera positions pending (C13)
Design: sitemap.Camera gains a placement (latitude, longitude, heading 0-359 from north, view angle 10-180,
  range 1-300 m); a row is created when an Admin places a camera that has not reported yet. GET
  /api/v1/camera-map/ (everyone signed in) lists every known camera (zone, token, live, or placed) with its
  placement, live status, people in view (a count older than 30 s shows as none), open alerts and latest
  alert. PUT/DELETE /api/v1/camera-map/{id}/ is Admin-only. camera_updated is broadcast on placement changes
  and changed people counts. GET /api/v1/camera-frames/latest/ returns the cached live frame to Safety
  Officers and Admins only. The map draws a cone from the entered values (nothing is measured from video).
Visible: Zones page Site Map with a Cameras list (Place / Move / Remove; three sliders with the cone
  following); dashboard Site Map card (live / offline / alerting counts, link to unplaced cameras); camera
  markers green, grey with a dashed cone, or red and pulsing for 60 s after an alert from that camera
  (alert_created); popup with zone, live picture (refreshed every second), people in view, open alerts,
  latest alert, and "Open live view" to /cameras?camera=ID
E2E (27 Oct, throwaway SQLite database, badge clip as CAM-01 with all detectors): as the test Admin, placed
  CAM-01 at Bay 1's corner facing NE (70 deg, 40 m) and CAM-09 at the Crane zone facing SW (90 deg); the
  draft cone followed the sliders; after saving CAM-01 was green, CAM-09 grey and dashed. CAM-01's popup
  showed its live frame, 2 people in view and its latest alert (danger area); "Open live view" opened the
  Cameras page on CAM-01. On the dashboard CAM-01 turned red within seconds of its next alerts after a camera
  restart (two vehicle-proximity alerts, the CRITICAL one naming the badge holder). As the test Safety
  Officer the list was read-only; as the test Viewer the map showed both cameras and the popup had status,
  count and alerts with no picture or link. Fixed during the run: the popup's dark style lost to leaflet.css
  (selector made more specific) and the popup opened under the zoom buttons (re-measured once filled).
  The same run confirmed FR-07 live: about 4 minutes of the looping clip gave 2 proximity alerts (was 14).
Tests (27 Oct): backend 232 OK on SQLite and PostgreSQL (11 new); ai-module 144; frontend lint clean, build
  OK — 442 in total
Known limitations: the cone is what the Admin enters, not the camera's real field of view; live status
  follows a 10 s refresh; a camera that sends nothing stays grey but keeps its position
Migrations: sitemap 0006 (camera placement); the dev database still needs `migrate`
```

```text
Phase / task IDs: Phase 2 item 4 — FR-34 evidence snapshots in the incident and safety reports
Status: Integrated on a throwaway database with test-video frames
Design: the report service picks the evidence (incident report: the 24 most severe incidents with a snapshot,
  critical first then newest; safety report: up to 2 per zone in zone order, Unattributed last), fetches each
  JPEG from /api/alerts/<id>/snapshot/ with the requesting user's token (4 at a time, API host only, JPEG of at
  most 1 MB, size read from its frame header), and lays them out two to a row with a caption: label, type,
  severity, status; time, camera (zone); worker or "not identified"; description; model version and
  confidence. Figures are E1, E2, ... in order and the incident log gains a Figure column pointing to them.
  The section states how many camera incidents had no snapshot (switched off or past retention) and how many
  could not be loaded; a failed image never fails the report. include_evidence (default true) lets the user
  leave snapshots out; Report.includes_evidence records it and the history shows "with/no snapshots".
Also fixed: the API did not expose Content-Disposition to the dashboard's origin (CORS), so every report was
  saved as "incident_report.pdf" / "compliance_report.docx"; it now keeps its dated name
  (CORS_EXPOSE_HEADERS), with a test.
E2E (27 Oct, throwaway SQLite database with the FR-32/33 runs' alerts; worktree report service): as the test
  Safety Officer, Incident Report PDF with snapshots, 27 Sep - 27 Oct: 14 pages, 1.2 MB; Evidence states "The
  24 most severe of 185 camera snapshots ... 5 camera incidents had no snapshot", 24 figures six to a page,
  captions with camera (Bay 1), badge holder where identified and model yolo11n.pt@0ebbc80d4a76; the log's
  Figure column points to E2, E3, ... Safety Performance Report DOCX with snapshots (213 KB): Evidence by Zone
  with E1-E2 from CAM-01 (Bay 1) and E3-E4 from CAM-09 (Crane), two to a row in LibreOffice's rendering.
  History lists both as "with snapshots"; downloads keep their dated file names. Fixed during the run: the
  log's "Evidence" header wrapped mid-word (now "Figure"); the history table overflowed with an extra column
  (format and snapshots now under the report type).
Tests (27 Oct): report-service 23 (10 new); backend 235 OK on SQLite and PostgreSQL (3 new); frontend lint
  clean, build OK — 455 in total
Known limitations: images are embedded at the camera's resolution (640 px), about 50 KB each; frames show
  people (decision B3 covers whether snapshots are allowed on site); Word itself not yet opened on the
  generated file (LibreOffice used)
Migrations: reports 0003 (includes_evidence); the dev database still needs `migrate`
```

```text
Phase / task IDs: Phase 2 item 5 — mobile parity for FR-31 to FR-34 (FR-28)
Status: Integrated on the app's web build against a throwaway database with a test video; not yet on a phone
  (C14: a new development build is needed; Expo Go already has both native modules)
Already in place: alert detail showed the evidence frame, model version and confidence (FR-29), and the
  Danger area type label (FR-32).
Added: Map tab (zones with head counts, vests, cameras with view cones, green/grey/red as on the web; tap a
  camera to open it) drawn by Leaflet 1.9.4, pinned by integrity hash, with OpenStreetMap tiles in a WebView,
  so no Google Maps key is needed on Android; the same page runs in an iframe on the web build; names are
  HTML-escaped and only well-formed messages from the page are acted on. Cameras tab (status, people in view,
  open and latest alert). Camera screen: live picture refreshed every second while open (Safety Officers and
  Admins) with the camera's danger areas outlined by react-native-svg over the frame at its true shape;
  areas with an on/off switch for Admins; the camera's 10 latest alerts. Alert detail: Open camera.
  Live events zone_updated and camera_updated; polling only while a screen is in view.
Backend: GET /api/alerts/ accepts camera_id and limit (newest N, 1-500; detail views ignore it), 2 tests.
E2E (27 Oct, app web build at phone size, throwaway SQLite database, badge clip as CAM-01): as the test Safety
  Officer, Cameras listed CAM-01 live with 2 in view and CAM-02/CAM-09 offline; CAM-01's screen showed the live
  frame with "Loading bay edge" outlined exactly over the camera's own red fill, its areas and latest alerts;
  an alert opened with its evidence frame and "Open camera CAM-01"; the Map showed Bay 1 and Crane with head
  counts, CAM-01 green with its cone and CAM-09 grey and dashed; tapping CAM-01 on the map opened its screen.
  As the test Admin, switching the area off from the phone: within the 15 s rules refresh the camera stopped
  drawing it and raising it; switched back on, it re-armed (both people in it alerted again). As the test
  Viewer: no live picture ("for Safety Officers and Admins"), area shown as On without a switch. No console
  errors after a reload. Fixed during the run: the web build's image load event has no size (crashed the
  camera screen); the picture's shape is now read once with Image.getSize on every platform.
Not done: an Android emulator could not boot here (the installed Android 37.1 preview image hung at cold boot,
  with and without the command sandbox), so the WebView map and SVG overlay have not run natively; C14 covers
  a phone check. Also seen: on the looping badge clip in real time, the unidentified person's proximity
  alerts recurred about every 2-3 minutes (5 in 11 min, against 14 in 3 min before FR-07's fix and 1 in the
  frame-exact replay); worth measuring on a real recording (A1)
Tests (27 Oct): mobile 25 (8 new), lint and tsc clean; backend 237 OK on SQLite and PostgreSQL (2 new) — 465
  in total
Dependencies: react-native-webview 14.0.1 and react-native-svg 15.16.0 (npx expo install, SDK 58 versions)
```
