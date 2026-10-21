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
| FR-03 | UI offers only actions the user's role permits | S | Viewer sees no resolve/edit/generate controls | `AuthContext.jsx` (`canOperate`, `isAdmin`) across Dashboard, Incidents, Workers, Vests, Zones, Settings, Reports | Browser check 16 Oct (officer: zones read-only; admin: zone editor) | Integrated (viewer path not browser-checked) |
| FR-04 | Detect missing PPE (10 classes) from a camera | M | Event precision ≥90% and episode recall ≥85% per retained class, on a sealed target-camera set | `ai-module/inference.py`, `models/sitesafe_v5.pt` | Held-out mAP50 0.562 on a leaky split (not a valid claim) | Coded |
| FR-05 | One alert per person per violation episode | M | Two people with the same violation give two alerts; a single-frame flicker gives none | `ai-module/ppe_episodes.py`, `badged_violations` + episode loop in `inference.py`, `--ppe-persistence`, `--ppe-clear-seconds` | `test_ppe_episodes.py` (22); headless pipeline run 20 Oct on a still-image clip: 3 people missing helmets + 1 missing goggles → 4 alerts, no repeats over 40 frames; live webcam run 21 Oct (55 s, one person) found duplicate-box episodes → fixed, replay of its recorded boxes gives one alert per item | Tested (**no annotated video scored yet**) |
| FR-06 | Detect falls from camera pose | M | Positive and hard-negative videos meet the AI event targets | `ai-module/fall_detection.py` | `alerts/test_fall.py` (21) | Tested |
| FR-07 | Warn when a worker is too close to a vehicle | M | Calibrated distance threshold; video evaluation | `ai-module/proximity.py` | `alerts/test_proximity.py` (9) | Tested |
| FR-08 | Detect prolonged inactivity; timeout configurable from the dashboard | M | Changing the INACTIVITY rule changes the camera timeout within 60 s | `ai-module/inactivity.py`, `CameraRules` | `alerts/test_inactivity.py` (10), `test_inference_config.py` | Tested |
| FR-09 | Fire/smoke detection with hot-work permit suppression | M | Licensed fixture videos pass; a permitted hot-work fire is downgraded, not dropped | `ai-module/fire_detection.py`, `ai-module/fire/` (prep script, Colab notebook), `alerts/fire_policy.py`, `sitemap.HotWorkPermit`, `components/zones/HotWorkPermits.jsx` | `test_fire_detection.py` (8), `fire/test_prepare_fire_dataset.py` (4), `sitemap/tests.py` permit + policy (8); e2e 20 Oct: permit issued in UI → fire in permitted zone MEDIUM + linked, elsewhere CRITICAL | Integrated (**model not yet trained; no video evaluation**) |
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
| FR-25 | Incident list, detail, resolve, CSV export | M | Resolve is broadcast; filters include every type | `frontend/src/components/incidents/` | FALL filter added 16 Oct; resolve broadcast covered by FR-13 | Coded |
| FR-26 | Dashboard KPIs and charts reflect recorded data only | M | Every displayed number reconciles to the API; nothing fabricated | `DashboardStatsView`, `KpiStrip.jsx`, `DashboardCharts.jsx`, `WorkerStatusGrid.jsx` | `workers/tests.py` DashboardStatsTests (3); browser check 16 Oct | Integrated |
| FR-27 | Incident and safety-performance reports in DOCX and PDF | M | Fixtures reconcile exactly; PDF produced; no unsupported percentages; period in the user's time zone | `report-service/lib/*`, `templates/*`, `backend/reports/` | `report-service/test` (12); `reports/tests.py` (6); e2e 16 Oct (both types, both formats via API → service; PDF inspected) | Integrated |
| FR-28 | Mobile app: login, alerts, resolve, worker status, push | M | Android build receives a push and resolves an incident visible on web | `mobile/` (Expo SDK 58) | `mobile/__tests__` (13); web build checked 16 Oct: sign-in, live alert arrival, detail, resolve, resolve from another session removed live, workers presence, sign-out | Integrated on web target (**device + push pending**) |
| FR-29 | Alert evidence (snapshot, confidence, model version) | S | Each AI incident is traceable to its frame and model | `ai-module/evidence.py` (model id = weights name + SHA-256 prefix; JPEG of the raw frame ≤ 640 px), snapshot BLOB in `event_outbox.py`, `--no-snapshots` / `SITESAFE_SNAPSHOTS`; `Alert.model_version` (migration alerts 0012), `decode_snapshot` + `CameraEventView` (base64 JPEG ≤ 512 KB, stored once per `event_id`), `/api/alerts/{id}/snapshot/`, `ALERT_SNAPSHOTS_ENABLED`, `purge_alert_snapshots`; `AlertSnapshot.jsx`, `mobile/components/AlertSnapshot.tsx` | `alerts/test_evidence.py` (19), `test_evidence.py` (8), `test_event_outbox.py` snapshot cases (3), `mobile/__tests__/api.test.ts` image fetch (3); e2e 20 Oct on a throwaway database: synthetic frame → outbox → API (201, one 11 KB file), replay of the same `event_id` → 200 and no second file; frame, confidence and model version shown to a Viewer on web and on the mobile web build; `purge_alert_snapshots --days 0` removed the file and kept the alert | Integrated (**synthetic frame; not yet from a live camera run**) |

## Non-functional requirements

| ID | Requirement | Target (proposed) | Evidence | Status |
|---|---|---|---|---|
| NFR-01 | Event-to-dashboard latency | p95 ≤ 2 s from commit on a local network | `tools/measure/latency.py`, 20 Oct: 100/100 delivered, p50 32 ms, p95 42 ms (PostgreSQL, single host) | **Met** (local host; LAN not yet measured) |
| NFR-02 | Outage tolerance | No lost or duplicated events across a 5-minute API outage and sender restart | `tools/measure/recovery.py`: first run 60.3 s (FAIL, 60 s ceiling) → ceiling lowered to 30 s → 30.0 s and 30.2 s, 100/100 stored once, 0 lost, 0 duplicated | **Met** |
| NFR-03 | Security of producers | No anonymous write endpoints; no credentials in source | `alerts/test_ingest.py`, `test_inference_config.py` | Tested |
| NFR-04 | Inference throughput | ≥ 10 FPS with all detectors on the demo machine | `tools/measure/fps.py`, Apple M4 at 1280×720: mps 13.4 and 15.7 FPS; cpu 9.8 and 10.1 FPS. Pipeline now defaults to mps. Fire model not yet included | **Met on mps** (re-measure once fire weights exist) |
| NFR-05 | Soak | 2-hour full-stack run with controlled disconnect | `tools/measure/soak.py` 5-min validation: 146 probes, 0 missed, reconnect 1.2 s; API memory 64→92 MB in 5 min (warm-up; needs the 2 h run) | **Not met yet** (2 h run pending on demo setup) |
| NFR-06 | Reproducible setup | Fresh machine reaches a working demo from the README | README updated 16 Oct | Not verified |
| NFR-07 | Code quality gate | Backend, AI and report-service tests pass; frontend build passes, lint clean | backend 183, ai-module 76, report-service 13, mobile 16, tools 16 pass (20 Oct); build OK; lint clean | Met |

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
