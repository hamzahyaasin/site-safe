# Site-Safe project completion audit

Reviewed on 20 September 2026 against the current working tree, including existing uncommitted work.

Site-Safe has a substantial camera-first prototype: a Django API, seven React pages, three loaded vision models, camera-level safety decision logic, and document-report integration. The main remaining work is connecting incomplete workflows, correcting misleading data, securing ingestion, repairing the dataset, and collecting end-to-end evidence. More model training alone will not finish the project.

## Completion assessment

These are engineering planning estimates, not measured percentages, test coverage, or a university completion certificate. The repository does not contain an approved, weighted acceptance checklist.

| Scope being assessed | Estimated completion | Interpretation |
|---|---:|---|
| Narrow camera-first web prototype | 60–70% | Core code exists; several operational workflows, analytics, reliability measures, and acceptance tests remain incomplete. |
| Full scope in report sections 1.3–1.4 | 35–45% | QR identity, mobile app, physical vest/LoRa, fire/smoke, map-based intrusion, and worker-level attendance are major unfinished commitments. |
| Readiness for use on an operating site | Not ready | There is no clean independent evaluation or measured field alert reliability; security and delivery defects also remain. |

The narrower estimate assumes an explicitly accepted scope covering camera-level PPE, proximity, inactivity and possible-fall alerts, web incident management, worker/zone records, and DOCX reports. It does not silently count mobile, QR, hardware or fire detection as completed or remove them from the original proposal. Confirm any scope reduction with the supervisor before using it in a completion claim.

The estimates reflect usable workflows and their evidence, rather than the number of files or screens. API/model code contributes real progress, but a saved setting that has no runtime effect, a synthetic chart, or an untested hardware design does not count as a finished feature.

## Verification performed

| Check | Result | What it establishes |
|---|---|---|
| Django test suite with isolated SQLite | **59/59 passed** | Role tests and proximity/inactivity/fall decision logic plus selected alert API contracts. |
| AI utility unit suite | **10/10 passed** | Dataset-audit fixtures, split-planning fixtures, raw/display frame separation, confidence CLI validation. |
| Migration drift check | **Passed: no changes detected** | Current Django models have corresponding migration definitions. |
| Local PostgreSQL migration inspection | **All listed migrations applied** | Development database schema is current. This was read-only. |
| Strict audit of the local PPE dataset | **Failed** | 573 source groups cross splits; 30 exact-image duplicate groups cross splits; 69 exact-image groups have conflicting annotations. |
| Three-model CPU smoke check on one existing test image | **Passed** | PPE and COCO detection models return boxes; pose returns a `[2,17,3]` tensor. This is neither a performance benchmark nor a new accuracy evaluation. |
| Django deployment check | **6 warnings** | Current configuration warns about DEBUG, secret-key quality, HTTPS redirection/HSTS and secure session/CSRF cookies. |
| Focused isolated API/WebSocket probes | **Defects reproduced** | See the results below. Tests used an in-memory database and disabled real push delivery. |
| Report-service JavaScript syntax | **Passed** | All service/lib/template JavaScript files parse; behavior and generated output are not thereby verified. |
| Frontend production build and ESLint | **Not verified** | Initially missing Vite/ESLint. Locked dependency installation failed due DNS/network timeouts; offline cache also lacked the locked Recharts package. |
| Report-service installation/integration | **Not verified end to end** | Offline installation lacked `xml-js`; no service integration pass is claimed. |
| FYP report inspection | **Content reviewed; rendered to 64 pages** | Extracted paragraphs/tables and visually inspected model, test and conclusion pages. This was not a complete page-by-page formatting certification. |

The test totals are **69 tests across two commands**, not 69 complete product workflows. The backend's `workers/tests.py`, `sitemap/tests.py` and `alerts/tests.py` remain empty templates. There are no frontend test scripts, no substantive report-service test script, and no checked-in CI workflow.

Commands run from the repository root, except where a subshell changes directory:

```bash
(cd backend && ../.venv/bin/python manage.py test --settings=sitesafe.test_settings --verbosity 2)
(cd ai-module && ../.venv/bin/python -m unittest discover -p 'test_*.py' -v)
(cd backend && ../.venv/bin/python manage.py makemigrations --check --dry-run --settings=sitesafe.test_settings)
.venv/bin/python backend/manage.py showmigrations --plan
.venv/bin/python backend/manage.py check --deploy
(cd ai-module && ../.venv/bin/python audit_dataset.py --strict)
npm --prefix frontend run build
npm --prefix frontend run lint
```

No live camera, physical vest, LoRa link, mobile client, field fall footage, production deployment, full browser workflow or fresh model accuracy evaluation was verified in this audit. Existing development data was not changed.

## Module inventory

| Area | Implemented | Remaining |
|---|---|---|
| Accounts and roles | Email JWT login; Admin/Safety Officer/Viewer hierarchy; server-side permissions; profile preferences; password change; Django admin | Authentication for devices and sockets; token refresh/recovery; frontend role gating; broader permission tests; stronger password-change validation. |
| Workers | Worker model, zone link, serializer, CRUD API, frontend fetching and status cards | Actual create/edit/delete worker forms; truthful presence; QR identity; consistency between Worker.vest_id and assigned SmartVest. |
| Alerts and incidents | Create/list/update/resolve; six alert types; camera identifier; CSV export; incident filters/detail UI; simulated alerts | Config enforcement; consistent publication from all producers; resolution events; evidence media; structured track/model metadata; immutable resolution history. |
| Camera sources | Webcam, file and network-source support; configurable camera ID; camera-to-zone lookup; multiple processes can run separate cameras | Camera registry/health dashboard, supervised workers, reconnect/recovery, headless operation, capacity and real-stream verification. |
| PPE model | Ten-class model, inference overlays, API posts, configurable global threshold, per-class cooldown | Clean data; trustworthy evaluation; per-person association; observable/unknown states; temporal confirmation; per-class calibration. |
| Vehicle proximity | Separate COCO detector; normalized box gap; persistence and latch; tested geometry | Per-pair tracking, scene calibration, industrial-vehicle validation; current COCO labels do not establish forklift/crane detection capability. |
| Inactivity | Multi-person camera-local centroid tracker, elapsed timeout, movement reset/latch, tests | Robust identities, occlusion handling and observation-gap limits; worker ActivityLog integration; break/shift semantics. |
| Fall | Pose model plus span/hip/knee heuristic; persistence/re-arm; tests; API enum and migration | Real fall and hard-negative video evaluation; multiple camera directions/occlusions; unknown posture handling; reliable delivery. |
| Zones and geofencing | Zone CRUD, JSON polygons, camera assignments, point-in-polygon helper, telemetry zone-enter/exit logs | Site map/polygon editor; automatic restricted-zone alerts; camera-space intrusion; live occupancy; overlap and malformed-polygon handling. |
| Vests and IoT | SmartVest model/UI, assignment, GPS/battery/SOS HTTP telemetry, MQTT callbacks | Assembled hardware/firmware/LoRa/gateway; started/supervised MQTT listener; device auth; input validation; stale-device offline handling. |
| Activity | Append/list API and daily summary calculation; GPS zone transition logs | Camera-to-worker identity; automatic check-in/out, breaks, shifts, overnight handling and historical analytics UI. |
| Notifications | FCM token endpoints and synchronous alert-created push hook | Working receiving client; preference/rule enforcement; recipient scoping; email delivery; background retries and failure isolation. |
| Reports | Incident/compliance DOCX templates; Django proxy, saved reports and authenticated downloads; React generation UI | Fix proxy errors; valid compliance definition; camera-level inclusion; truncation disclosure; integration tests; PDF if original objective remains. |
| Dashboard | Seven pages, routing, cards/tables/forms, socket reconnect/poll fallback | Replace fabricated metrics; finish worker workflows; correct role display/actions, site selector and FALL filtering; browser verification. |
| Mobile, QR, fire/smoke | Design text only | No implemented mobile app, QR identity flow, fire/smoke model or hot-work permit system found. |
| Deployment and operations | Python requirements, npm lockfiles, example backend env, report-service Dockerfile | Complete startup/deployment procedure; shared channel layer; health monitoring; backups/restore; media serving; CI; reproducible Python environment and model distribution. |

## Highest-priority defects

### 1. The UI presents invented measurements as live observations

[DashboardCharts.jsx](/Users/hamza/code/site-safe/frontend/src/components/dashboard/DashboardCharts.jsx:15) contains fixed hourly data and a fixed seven-day compliance series. Scaling a predefined hourly pattern by today's total does not produce actual hourly measurements. The zero-alert branch still displays the predefined violations.

[utils.js](/Users/hamza/code/site-safe/frontend/src/lib/utils.js:121) generates last-seen times from worker IDs and generates temperature, heart rate and gas values from deterministic arithmetic. [WorkerStatusGrid.jsx](/Users/hamza/code/site-safe/frontend/src/components/dashboard/WorkerStatusGrid.jsx:38) displays them under a description claiming live vest telemetry. The SmartVest schema does not even contain those vital-sign fields.

[KpiStrip.jsx](/Users/hamza/code/site-safe/frontend/src/components/dashboard/KpiStrip.jsx:1) adds fixed deltas and synthetic sparklines. Its compliance calculation subtracts open alerts from active workers; multiple alerts per person, unassigned camera alerts, non-PPE alerts and unknown camera coverage make that an invalid compliance denominator. With zero workers it returns 100%.

**Completion requirement:** remove these values or clearly restrict them to a labeled demo mode. Compute historical counts from timestamps and use actual telemetry freshness. Show unavailable/unknown when there is no observation. Define any compliance metric before implementing it; do not substitute absence of alerts for evidence of compliance.

### 2. Ingestion and the live dashboard lack complete authentication

[alerts/views.py](/Users/hamza/code/site-safe/backend/alerts/views.py:118) allows unauthenticated alert ingestion and detection creation. [workers/views.py](/Users/hamza/code/site-safe/backend/workers/views.py:135) allows unauthenticated vest telemetry. [consumers.py](/Users/hamza/code/site-safe/backend/alerts/consumers.py:6) joins and accepts WebSocket connections without checking the user. Session middleware alone does not authorize a connection, and the frontend socket supplies no JWT.

Isolated probes reproduced anonymous alert creation (`201`), detection creation (`201`), telemetry updates (`200`) and accepted anonymous dashboard sockets.

[inference.py](/Users/hamza/code/site-safe/ai-module/inference.py:37) contains hard-coded administrative credentials. Their values are intentionally not repeated here.

**Completion requirement:** use revocable device credentials with limited permissions, authenticated sockets with origin checks, environment-provided secrets, and appropriate abuse limits. Rotate embedded credentials if reused. Keep authenticated dashboard-user permissions distinct from machine ingestion permissions.

### 3. Alert and notification settings are saved but do not govern behavior

`AlertConfig` is exposed through CRUD, but the detector and ingestion paths do not use it to apply `is_enabled`, thresholds or zone-specific rules. A probe created a PPE alert successfully after disabling the global PPE rule.

[signals.py](/Users/hamza/code/site-safe/backend/alerts/signals.py:16) targets all active users for every newly created alert without consulting `UserPreferences`, per-zone rules or notification flags. Email preferences have no email-sending implementation. Push delivery is synchronous and its exceptions are not isolated from alert creation.

**Completion requirement:** establish one alert-policy layer, define global-versus-zone precedence, synchronize versioned detector settings, honor recipient preferences, and queue notifications. Verify a settings change actually changes behavior. Provide defaults or creation UI for a fresh database; the settings screen currently only edits existing rows.

### 4. Alert delivery can block inference and lose incidents

[inference.py](/Users/hamza/code/site-safe/ai-module/inference.py:122) authenticates once. It does not refresh tokens, reauthenticate on expiry or recover from offline startup. Each alert POST can block the same loop that captures and processes frames for up to ten seconds; multiple calls can compound the delay.

PPE cooldown is advanced even after a failed POST. Fall and inactivity trackers latch before successful delivery; without an outbox, a failed event can be lost until a later re-arm. There is no durable retry queue or event idempotency key.

**Completion requirement:** separate capture/inference from HTTP delivery; add a bounded durable outbox, retry/backoff, idempotency, token renewal and observable queue failures. Preserve event capture time separately from server receipt time. Test unavailable API, expired token, slow requests and process restart.

### 5. Live updates omit important write paths

REST alert create/ingest/simulate calls broadcast explicitly. [mqtt_handlers.py](/Users/hamza/code/site-safe/backend/workers/mqtt_handlers.py:69) creates SOS alerts directly without that broadcast. The isolated telemetry probe produced no call to the broadcast helper. Alert resolve/update does not broadcast changes either. There is no backend producer for the frontend's `worker_status_update` event.

The frontend stops polling when a socket is live. A successfully connected dashboard can therefore remain stale for telemetry SOS, worker changes or resolutions from another client. The polling fallback mostly discovers new alert IDs and is not a complete state-reconciliation mechanism.

**Completion requirement:** publish committed state changes from a common service or transaction-on-commit hook, support created/updated/resolved events and worker/vest updates, and reconcile state after reconnect. Move the channel layer out of process memory before running multiple server processes.

### 6. Data validation allows invalid records

Focused probes showed that a detection with confidence `3.5` and a nonnumeric bounding-box member was accepted, telemetry stored battery level `900`, and zone creation accepted malformed polygon vertices plus a string in `camera_ids`.

**Completion requirement:** typed serializers for telemetry; numeric finite/range validation for confidence, coordinates and battery; ordered numeric bounding boxes; valid polygon vertices; lists of camera IDs; positive threshold constraints. Return controlled `400` errors before any partial write. Treat malformed MQTT payloads as recoverable input errors too.

### 7. Reports can be wrong even when generation succeeds

[compliance-report.js](/Users/hamza/code/site-safe/report-service/templates/compliance-report.js:37) associates violations only through worker IDs, while camera AI alerts deliberately leave worker unset. Those alerts therefore do not contribute to its zone compliance calculation. The arbitrary multiplier of 25 is not a measured compliance definition, and zero workers yields 100%.

[proxy.py](/Users/hamza/code/site-safe/backend/reports/proxy.py:55) closes an unsuccessful streaming upstream response before reading its JSON/text body. A simulated `503` streaming response reproduced `ValueError: I/O operation on closed file` rather than a controlled service error.

The incident table silently keeps only the first 500 alerts while its text says all incidents are listed. Compliance detail caps response rows at 200 and workers at 50. Simulated data is not excluded from normal analytics/reports by default. Alert source/zone attribution is not an immutable observation: camera zone names are resolved from current zone configuration.

**Completion requirement:** fix response handling; define honest report metrics; include camera-level incidents and observation coverage; disclose or remove truncation; explicitly separate test data; retain zone/config attribution at incident time. Add report integration tests including empty data, camera-only alerts, service failure, large periods and download persistence. Decide DOCX versus the original PDF commitment explicitly.

### 8. Worker and zone workflows stop partway through

[WorkersPage.jsx](/Users/hamza/code/site-safe/frontend/src/pages/WorkersPage.jsx:1) only renders status cards. Worker create/update/delete methods exist in `useWorkers` but are not used by a form. The “Register new worker” link goes to vest registration, which only assigns existing workers. Registration currently requires the API or Django admin.

Telemetry does produce zone-enter/exit ActivityLogs, so the old handoff's blanket “zone entry/exit not built” claim is too broad. However, an isolated restricted-zone entry produced one entry log, **zero breach alerts**, and no update to `Worker.zone`. Zone occupancy counts assigned active workers, not live occupancy.

There are two potentially conflicting identifiers: `Worker.vest_id` and `SmartVest.vest_id` with a worker relationship. Vest assignment does not synchronize the worker string, while ingestion can look up the worker by that string.

**Completion requirement:** finish worker forms and consistent assignment semantics; distinguish assigned zone from observed zone; emit policy-driven zone breaches; compute occupancy from fresh observations; decide how overlapping zones are handled.

### 9. Roles and site selection are incomplete in the frontend

Zones hides admin controls correctly, but other pages still offer restricted actions to viewers/officers. Backend permissions often reject these actions, so this is not a claim that those protected REST endpoints are bypassable. The top bar always labels the user “Safety Officer”. FALL exists in the backend but is absent from incident type-filter buttons and the dashboard simulator options.

The site selector has two hard-coded sites and only changes local UI state; no Site model or API scoping implements that choice. WebSocket broadcasting defaults to one global group.

**Completion requirement:** use the returned role throughout the UI, remove or implement site selection, add FALL controls, and cover all roles in browser tests. Show useful errors for failed data loads and unauthorized actions.

### 10. Release and observability work remains

[settings.py](/Users/hamza/code/site-safe/backend/sitesafe/settings.py:135) uses `InMemoryChannelLayer`. REST/login URLs are hard-coded to localhost; only the WebSocket URL has an environment override. Backend CORS is fixed to the local Vite origin. Default report-service addressing assumes a service hostname, but the README's three-terminal startup does not start the report service or explain its configuration.

There is no checked-in whole-stack deployment, CI, camera heartbeat, model-health API, stale-vest expiry, durable alert queue, backup/restore procedure or packaged model download with integrity verification. Media is served by Django only under DEBUG. List APIs have no pagination; the browser and report service fetch full lists. Adding pagination will also require report code to follow every page.

**Completion requirement:** document and automate all required processes, pin a supported runtime/dependency set, configure deployment URLs/TLS/media, add shared messaging and health checks, and prove a clean-clone startup and restore procedure. Missing camera/model coverage must appear as unknown/degraded rather than safe.

## AI status and the path to acceptable results

### What is actually present

The current inference default is `models/sitesafe_v5.pt`, not `sitesafe_final.pt`. The exported manifest records a completed YOLO11m training/test run on a Colab T4, with a 150-epoch budget, 640-pixel images and batch 16. The local current PPE weights loaded successfully as a ten-class detector with 20,037,742 parameters. The separate COCO and pose weights also loaded and ran.

The artifact records completion, but its weights path points to Colab and it does not record the deployed file's SHA-256. This audit has not cryptographically proven that the exported metric JSON belongs to the exact local bytes. The local PPE file SHA-256 measured during this audit is:

```text
7e8e092d0603846512a8b54e4e5d31e3c260f3bdf1f45366cc82d25b489f30f3
```

The report-update script mentions 102 completed epochs and best epoch 77; retain the original training log/checkpoint evidence before publishing those details as verified run history. The exported manifest records requested settings and completion, not those two epoch counts.

### Recorded model metrics

Source: [held_out_test_metrics.json](/Users/hamza/code/site-safe/ai-module/models/sitesafe_v5_export/held_out_test_metrics.json). These are saved artifact values, not a fresh evaluation in this audit, not field alert precision and not “accuracy percent”.

| Metric | Recorded result |
|---|---:|
| mAP@0.5 | 0.5621 |
| mAP@0.5:0.95 | 0.3447 |
| Mean precision | 0.4666 |
| Mean recall | 0.7281 |

| Violation class | Test instances | AP@0.5 |
|---|---:|---:|
| no-helmet | 42 | 0.3095 |
| no-vest | 116 | 0.7819 |
| no-boots | 19 | 0.1297 |
| no-gloves | 31 | 0.0618 |
| no-goggles | 88 | 0.5305 |

The older report records overall AP50 of 0.544. Relative to that recorded baseline, the headline improvement is only about **1.8 percentage points**; no-boots and no-gloves are worse than the older reported values. A larger model has not solved the central missing-equipment problem.

### Data quality blocks a trustworthy completion claim

The live strict audit covered 5,140 images: 3,597 train, 1,026 validation and 517 test. It found no malformed rows or image/label pairing errors, but did find:

- 573 filename-derived source groups crossing split boundaries.
- 30 exact-image duplicate groups crossing split boundaries.
- 69 exact-image groups with conflicting labels.
- Zero background images in all three splits.

The group counts describe groups, not percentages of images. Source identity inference is provisional; exact duplicates are stronger direct leakage evidence. The current test split should not be described as independent evidence of generalization.

The v2 planner is real progress: a manifest, grouped sources/duplicates, conflict review pack and 3,598/771/771 proposed split exist. It is only a proposal. There is no finished, adjudicated v2 dataset or reviewed source/site/camera/session metadata. The planner does not apply human conflict decisions into a materialized training dataset. The Colab notebook's built-in audit is less strict than the local leakage audit; a malformed-label check does not protect against split leakage.

### Runtime decisions need improvement independently of training

- PPE currently reduces boxes to the maximum score for each violation class and applies a class-level cooldown. Two people missing the same equipment are not independent alert subjects. One frame can trigger an alert.
- PPE detections are not associated with a person/body region; conflicting equipment/absence boxes are not reconciled.
- Proximity has a camera-wide streak/latch, not a tracked person/vehicle-pair lifecycle.
- Inactivity and fall associate people by fixed-pixel centroid distance. They can swap identities or fragment tracks during occlusion/crossing.
- Time since the last frame is not explicitly bounded as observed time. A long capture/network gap can contribute to temporal persistence; the explicit pause path resets some trackers, but outages need equivalent treatment.
- Pose uncertainty is currently converted to non-collapsed behavior, which can re-arm a previous event. There is no persistent “not observable” state for the operator.
- Events do not save snapshots/clips, full detections, model/config hashes or structured tracking evidence. The Detection and snapshot schemas exist but are not populated by the main vision pipeline.

### Recommended AI sequence

1. Preserve the present dataset/model as a named baseline with checksums and the failed audit attached.
2. Recover source metadata and original assets where available. Review every conflicting-label group, with particular attention to negative classes and annotation policy.
3. Implement an auditable dataset-v2 materializer that consumes approved decisions. Keep videos/sites/sessions and derived duplicates in one split. Require strict checks before training.
4. Collect fresh target-camera footage, rare violations, background scenes and hard negatives. Reserve genuinely unseen camera/session/site footage for final evaluation; do not reuse a repeatedly inspected test set as sealed evidence.
5. Add stable person tracking, person/body-region PPE association, present/absent/not-observable states, and per-track elapsed-observation confirmation with hysteresis.
6. Train controlled experiments on clean data. Calibrate per-class thresholds and temporal settings on validation only; do not try to fix the system by lowering one global threshold.
7. Evaluate full video events: alert precision, missed episodes, false alerts per camera-hour, delay, duplicate rate and camera/lighting/distance slices. Agree numeric acceptance thresholds before examining final-test results.
8. Validate fall/inactivity/proximity separately, using positive cases and ordinary bending, sitting, occlusion, parked vehicles and camera perspective hard negatives. Record throughput and end-to-end latency on the actual deployment hardware.
9. Release only a versioned combination of code, weights, thresholds, camera configuration and evaluation evidence. Preserve degraded/unknown states for missing coverage.

## Documentation and academic completion

The current DOCX has a useful implementation/results/future-work structure, but it is not ready to submit unchanged.

| Document | Required correction |
|---|---|
| README | Describes YOLOv10 and older weight/setup paths; misses the report-service process and several runtime dependencies/features. Update the actual architecture, model and clean-start instructions. |
| HANDOFF_NEXT_STEPS | Says retraining is not run and five commits are unpushed. Local v5 artifacts show completed training; local HEAD and the cached origin/main ref are equal. No remote fetch was performed, so actual remote freshness is not asserted. Its claim that all listed features are covered by 59 tests is too broad. |
| AI_ACCURACY_ROADMAP | Best current description of the AI work. Preserve its separation of object metrics from event metrics, and turn phases into tracked acceptance tasks. |
| FYP report | Still describes the nano model/54.4% and says medium training has not completed; current inference points to v5. Update every affected section and table consistently, with the leakage caveat. |
| FYP report fall status | Section 4.3.4 correctly describes implementation, but sections 4.10, 4.11 and Chapter 6 still call it unimplemented/future work. |
| FYP report scope | Section 1.3 says 11 PPE classes, while the implemented dataset has 10. Section 1.7 claims QR/mobile implementation that later sections correctly defer. Chapter 1 still commits to PDF, mobile, QR, hardware and fire/smoke. Resolve scope explicitly. |
| FYP report references | Internal citation mappings are broken: the ILO statistic cites [1], which is a YOLOv3 paper; the Pakistan labour-survey statement cites [8], a harness-detection paper. Recheck claim-to-reference mappings and the dataset citation. This audit did not independently verify every external reference. |
| Report build script | Existing uncommitted edits update part of model performance while other generated text still uses the old model and results. Finish the source-of-truth update before rebuilding. |
| generated-file-contents.md | Historical copied source snapshot, not current implementation. Mark as archival or regenerate deliberately. |
| Frontend README | Still a generic Vite template. Replace with application-specific instructions. |

The report's A4 dimensions and 1.25-inch left / 1-inch other margins match the supplied SOP. Visual spot checks found readable tables/body text, but Chapter 5 styling differs from Chapter 6 and the SOP's separate chapter-page requirement needs a full final-format review. No blanket formatting pass is claimed.

The supplied SOP, sections 3.6–3.9, says a project below 80% completion or above 18% similarity cannot be presented, and requires supervisor-signed documentation and meeting records. That is **at most 18% similarity**, rather than the handoff's stricter “less than 18%” wording. These conditions are quoted from the local supplied SOP; current department applicability still rests with the supervisor.

Approval/declaration/plagiarism/Turnitin certificates are not present in the extracted report text; no completed originality report or meeting-log evidence was found in this repository. Their existence elsewhere cannot be inferred. A user manual, reproducible installation package and final presentation material also need to be assembled if they have not been prepared outside the repo.

Use the existing report build script for future edits. The handoff documents that the script cannot safely rebuild from its own already-transformed output. Pin an exact original input version/checksum, consolidate all measured results, rebuild, render, validate XML and verify every final page and index before submission. Do not simply replace 54.4 with 56.2 throughout the report.

## Completion plan

The order below keeps dependencies explicit. Effort ranges are rough focused developer-days for someone familiar with this code, not calendar promises. They exclude waiting for supervisor decisions, field access, annotation, GPU availability and hardware procurement.

| Milestone | Work | Exit condition | Rough effort |
|---|---|---|---:|
| 1. Freeze acceptance scope | Trace original objectives to code/tests; decide which deferred modules remain mandatory; list exact demonstration scenarios and acceptance thresholds. | Supervisor/team accepts a versioned scope and no screen/report misstates what exists. | 1–2 days |
| 2. Make the prototype truthful and secure | Remove synthetic live values; fix roles/FALL controls; device/socket auth; remove embedded credentials; validate inputs; fix report proxy errors and invalid compliance claims. | Anonymous access is rejected; invalid payloads return 400; unobserved metrics are unknown; service failures are controlled. | 4–7 days |
| 3. Complete operational workflows | Worker forms/vest identity; settings enforcement; common alert lifecycle/broadcasting; queue/retry/token recovery; evidence metadata; real chart aggregation; zone breach if retained. | Freshly registered worker/zone/camera can produce, display, review, resolve and report an incident across two clients, including outage/reconnect. | 7–12 days |
| 4. Repair AI evidence | Adjudicate labels, materialize v2, acquire fresh evaluation footage, track people and confirm events, run controlled training/calibration/video evaluation. | Strict data checks pass and locked event-level targets pass on independent footage; results reproducible. | 10–20+ days plus data collection/review |
| 5. Package and test release | PostgreSQL and service integration tests, browser role flows, report tests, shared channel layer, startup/configuration, health checks and backup/restore. | A clean clone starts from documented steps and the acceptance suite passes with no manual DB repair. | 4–7 days |
| 6. Finish academic evidence | Rebuild consistent report, citations, screenshots and measured results; final visual review; demo recording, manual, certificates, meeting records and similarity check. | Submission materials match the demonstrated build and departmental requirements. | 3–5 days plus institutional turnaround |

For the narrowed prototype, this is approximately **6–11 focused developer-weeks**, with substantial uncertainty concentrated in dataset work and field validation. Some tasks can overlap if the team divides frontend/backend/data work. This estimate is for finishing credibly, not merely getting a local demo running.

The original broader scope additionally requires distinct workstreams:

- **QR identity:** worker identifier schema, QR generation/printing, camera decoding, identity-to-track association, expiry/reacquisition and distance/occlusion validation. This is a dependency for credible per-worker camera compliance and attendance.
- **Map and intrusion:** define GPS polygons separately from camera-image polygons; map editing, observed location, restricted-zone policy, deduplicated breach events and live occupancy.
- **Worker activity:** identity-based entry/exit, shift boundaries, check-in/out, break policies and reviewed summaries rather than raw event counts.
- **Mobile:** actual React Native project, authenticated sessions, alert/status views, permissions and background push, tested on target devices.
- **Hardware:** ESP32 firmware, GPS/SOS, LoRa transport/gateway, MQTT worker, authentication, offline behavior and measured field/battery tests.
- **Fire/smoke:** suitable labeled data/model, temporal validation, alert enums/UI, hot-work permit schema and tested suppression/escalation policy.
- **PDF reporting:** add export support if it remains an accepted requirement; DOCX generation alone does not meet it.

Do not promise a reliable total for those workstreams without hardware access, scope confirmation and data availability. They are not a final-week polish task.

## Concrete definition of done

- A new machine can install the exact dependencies, obtain verified model artifacts, start all required services, migrate and create the initial user using documented steps.
- An admin can configure a zone/camera and register/edit/assign workers through the intended UI; each role sees and can perform only its permitted actions.
- A genuine observed event is saved once with timestamp, camera/zone/track attribution and evidence, reaches authorized dashboards, and survives API/socket/process interruptions.
- Resolution propagates to another client and preserves who resolved it, when and why.
- Settings alter runtime decisions and notification delivery as specified, including disabled rules and per-zone overrides.
- Data gaps, offline devices and unavailable models are shown explicitly. No synthetic health or compliance values appear as live facts.
- Reports match their underlying events and declared metric definitions, include camera-level incidents, and disclose incomplete/truncated information.
- Dataset integrity checks and event-level evaluation meet predefined acceptance criteria, with results tied to the deployed weights/configuration.
- Tests cover PostgreSQL behavior, ingestion, device validation, notifications, sockets/reconnect, report failures, browser roles and multi-person AI events.
- Documentation, approved scope, demo, report, references and measured results describe the same release.

The immediate next implementation batch should cover authentication, truthful UI values, input validation, report proxy/compliance correctness and regression tests. Dataset adjudication/source collection should start alongside that work because it is likely to determine the critical path.
