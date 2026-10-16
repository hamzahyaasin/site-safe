# Site-Safe: module status and completion plan

Prepared 16 October 2026 from three sources: the NUML FYP report guideline, the Revised FYP SOP (FYP-II rubric and Appendix D outline), and a fresh audit of the code in this repository. It builds on `FYP_READINESS_REVIEW_2026-10-13.md` and `CLAUDE_PHASED_IMPLEMENTATION_PLAN.md`, and re-checks their claims against today's code.

## 1. What the university actually grades

| Gate / component | Source | What it means for Site-Safe |
|---|---|---|
| Completion certificate ≥ 80% | SOP 3.6.2 | Below 80% of the approved scope, the group is **not allowed to present**. The timeline targets 100%. |
| Similarity ≤ 18% | SOP 3.6.4 | Turnitin is run on the final report, and you get at most two attempts. |
| Supervisor score: 20 marks | FYP-II rubric | Meeting log with at least 13 weekly entries, task progress, recent references. No log means a 50% deduction. |
| Presentation / demo: 40 marks | FYP-II rubric | A working system, methodology, results and analysis, communication. |
| Report: 40 marks | FYP-II rubric | Abstract, Ch.1–6, hardware/software design, algorithm/source code, testing results, references (50% from the last 5 years), writing, organization. |
| Report format | Guideline p.3–4, SOP 3.8–3.9 | 8,500–10,500 words; A4; margins 1/1/1/1.25"; Times New Roman 12 pt at 1.5 spacing, justified; chapter separator pages; no bullets in body text; IEEE references. |
| Final package | SOP 3.7 | Three hardbound copies (black for CS) and a CD with the proposal, report, presentations, source code, setup, and user manual. |

**Required report sequence (guideline):** Title, Abstract, Final Approval Certificate, Declaration, Plagiarism Certificate, Turnitin report, (Dedication, Acknowledgement), TOC, List of Figures, List of Tables, then the chapters:

- **Ch.1** Introduction
- **Ch.2** Background/Existing Work
- **Ch.3** System Requirement Specification
- **Ch.4** System Modeling & Design
- **Ch.5** Testing & Validation
- **Ch.6** Conclusion

After the chapters come the Appendices (including the user manual) and the References.

## 2. Module status (verified 16 Oct 2026)

"Status" describes the code itself. Nothing below has been field-validated.

| # | Module (from report objectives) | Status | What exists | What is missing |
|---|---|---|---|---|
| M1 | Accounts and roles | **Complete (API)** / Partial (UI) | Email/JWT login, roles Admin / Safety Officer / Viewer, permission classes, profile and preferences; 16 tests | Token refresh is never used by the frontend. There is no user-management UI. Viewers see buttons the API will reject. The websocket is unauthenticated. |
| M2 | PPE detection (vision) | **Partial** | YOLO11m `sitesafe_v5.pt` with 10 classes, live overlay, posts alerts. Held-out mAP50 is 0.562. | Violation classes are weak: no-gloves 0.06, no-boots 0.13, no-helmet 0.31. The dataset split leaks across splits (the v2 split is planned but not materialized). No per-person association. **Admin credentials are hardcoded in `inference.py:37-38`.** No snapshots are attached. |
| M3 | Fall detection | **Partial** | Pose-keypoint heuristic with a persistence tracker, FALL alert type; 21 tests | Not validated on real fall and hard-negative videos. FALL is missing from the incident filter. |
| M4 | Vehicle proximity | **Partial** | Person/vehicle detection and image-plane distance logic; 9 tests | No calibration, so distances can't be claimed in metres. No per-pair tracking. |
| M5 | Inactivity / workforce activity | **Partial** | Camera-local inactivity tracker; 10 tests; ActivityLog model and summary API | No check-in/out, idle or shift logs are generated automatically. Inactivity isn't linked to a worker. |
| M6 | Geofencing / zones | **Partial** | Zone polygons, point-in-polygon, camera-to-zone mapping, ZONE_ENTER/EXIT logs from GPS | **No automatic ZONE_BREACH** for restricted zones. `max_occupancy` is never enforced. Polygons are edited as raw JSON with no map. No tests. |
| M7 | QR worker identification | **Missing** | Documentation only | Issue/print QR codes, decode them from the camera, link the decoded worker to alerts. |
| M8 | Smart vest (ESP32 + GPS + SOS + LoRa) | **Missing (hardware)** / Partial (server) | Vest model, HTTP telemetry endpoint, MQTT handlers, SOS rising-edge alert, simulator UI | No firmware anywhere in the repo. The MQTT listener is never started. No offline timeout. Vest SOS is not broadcast live. Telemetry ingest is AllowAny. |
| M9 | Fire/smoke detection and hot-work suppression | **Missing** | Report section marked "not implemented" | Model/dataset, inference integration, hot-work permit policy. |
| M10 | Command centre (React dashboard) | **Partial** | 8 pages on the real API, live alerts over websocket with a polling fallback | **Fabricated data:** vitals (Temp/HR/Gas), last-seen, hourly/compliance charts, sparklines, site list. No worker create/edit UI. No site map. Zone ID shown instead of zone name. Build/lint not verified because `node_modules` is empty. |
| M11 | Real-time alerts and notifications | **Partial** | Websocket broadcast on create/simulate/ingest; FCM send hook | Resolve and vest SOS are not broadcast. In-memory channel layer. `AlertConfig` settings are enforced nowhere. FCM pushes to all users and is unconfigured. No email or SMS. |
| M12 | Mobile app (React Native) | **Missing** | Report design only | The whole app: login, alerts list/resolve, push reception. |
| M13 | Reports (incident/compliance) | **Partial** | Node docx service, Django proxy, history/download | **No PDF** (the objective promises PDF). Compliance % is arbitrary. The service URL default only works in Docker. `docx_builder.py` is dead code. No tests. |
| M14 | Delivery / ops | **Missing** | Report-service Dockerfile only | docker-compose, setup guide, CI, model download instructions, user manual. |
| M15 | FYP report (V7 docx) | **Partial** | 6 chapters, ~12,500 extracted words, references | Ch.3 is "System Overview", not an **SRS** (no FR/NFR, use cases or feasibility). Ch.4 is implementation, not **Modeling & Design** (no class, sequence, activity or deployment views). Missing approval, declaration, plagiarism and Turnitin pages and appendices/user manual. Over the 10,500-word cap. Contains stale claims (11 classes, "training unfinished", fall detection marked as future work). |

**Rough position:** about 60–70% of a narrowed camera-first web prototype, and about 35–45% of the full scope promised in report §1.3–1.4. Four whole modules are missing (M7, M8 hardware, M9, M12), so the 80% presentation gate is **not met under the full scope** today.

## 3. Decision needed first: scope

The fastest path to the 80% gate depends on what the supervisor accepts:

- **Option A: keep the full scope.** All of M7–M12 must be built, including a physical vest. This is the longest path and needs hardware purchases (BOM in `HARDWARE_AND_PURCHASE_PLAN.md`).
- **Option B: documented scope amendment.** Keep the camera-first core plus QR, PDF reports and the mobile app. Move the physical vest/LoRa and fire/smoke detection to future work with a written supervisor sign-off.

Do not silently move features to "future work" in the conclusion. The SOP measures completion against the approved proposal.

## 4. Completion plan

Work is ordered by grading value and dependency. Each step names its "done" evidence. "Claude" means the work can be done in this repo. "Team" means a human must supply it.

### Stage 0: Baseline and traceability (Claude)
1. Commit the current untracked work (`audit_dataset.py`, `prepare_dataset_v2.py`, AI tests) and add model files to a documented download location instead of git.
2. Install frontend and report-service dependencies, then run build and lint. Record the results.
3. Build a **requirements traceability matrix** (FR/NFR IDs → module → code → test → evidence). It feeds Ch.3 and Ch.5 directly and lets you state the completion % honestly.

*Done when* all suites run from documented commands and every objective has a matrix row.

### Stage 1: Security and correctness blockers (Claude)
1. Remove the hardcoded credentials from `inference.py`. Add a scoped service/device token for the AI and vest ingest endpoints. Authenticate the websocket with JWT. Add token refresh in the frontend.
2. Validate ingest payloads (confidence, boxes, GPS, battery).
3. Broadcast every alert event (create, resolve, vest SOS) after commit. Send `worker_status_update`. Use the Redis channel layer.
4. Make `AlertConfig` effective (enabled flag, thresholds, notify flags) and seed default rules. Respect user preferences for push.
5. Add an outbox to the inference process (local queue with retry) so an API outage doesn't lose events.

*Done when* there are tests for rejected anonymous producers and subscribers, and a rule change visibly changes behaviour.

### Stage 2: Honest, complete dashboard (Claude)
1. Delete the fabricated vitals/last-seen/chart data. Add backend aggregation endpoints (hourly incidents, per-type, per-zone) and drive the charts from them. Show "not measured" where there's no data.
2. Add worker create/edit/deactivate forms. Unify the vest-assignment source of truth (drop `Worker.vest_id` and keep the FK).
3. Add a map-based zone editor (Leaflet polygon drawing) and show live vest positions.
4. Generate ZONE_BREACH automatically for restricted zones and over-occupancy. Add a vest offline timeout.
5. Add role-aware UI, the FALL filter, zone names, alert snapshot display, and remove the fake site selector.

*Done when* the frontend builds and lints, and every visible control works.

### Stage 3: AI quality (Claude prepares, team runs the GPU and adjudicates labels)
1. Materialize the v2 group-aware split and resolve the 139 conflict-review rows (the team adjudicates). Add rare negative examples (no-gloves, no-boots).
2. Retrain on Colab with the existing notebook and calibrate per-class thresholds on validation only.
3. Associate PPE detections with person tracks and add temporal confirmation, so one person yields one alert.
4. Record short test videos with real PPE (the team does this) and measure event precision, recall and false alerts per hour for PPE, fall, proximity and inactivity.
5. Upload snapshots as alert evidence.

*Done when* Ch.5 can report per-class and event-level results on an untouched test set.

### Stage 4: Missing modules (Claude codes; team supplies hardware and devices)
1. **M7 QR identification:** issue a QR per worker (printable from the Workers page), decode with `pyzbar`/OpenCV in the inference loop, link the decoded worker to the nearest person track, and attach `worker` to alerts. Measure readable distance and angle physically.
2. **M13 PDF reports:** add PDF output to the report service (e.g. render via LibreOffice/Gotenberg or a pdfkit template). Replace the compliance % with defined metrics: incidents per type/zone and resolution time. Add fixture tests.
3. **M12 Mobile app:** React Native (Expo) with login/refresh, alert list/detail/resolve, worker status and FCM push. Test on a borrowed Android phone (the team needs a Firebase project).
4. **M8 Smart vest:** ESP32 firmware (GPS over UART, SOS button with debounce and ack LED, LoRa TX), receiver firmware, a serial→MQTT bridge, and start the MQTT consumer as a management command. The team buys about two ESP32+LoRa boards, a GNSS module and a button, then assembles and measures range and latency.
5. **M9 Fire/smoke:** a fine-tuned YOLO on a licensed fire/smoke dataset, a FIRE alert type, and hot-work permit zones/times that downgrade rather than drop the alert. Evaluate on recorded licensed videos only.

*Done when* each module has an end-to-end demo plus an evidence entry in the matrix.

### Stage 5: Release and validation (Claude)
1. Add a docker-compose with Postgres, Redis, backend (daphne), report-service and frontend. Inference stays native on the Mac for camera access.
2. Add GitHub Actions CI covering backend tests, AI unit tests, frontend lint/build and report-service tests.
3. Add backend tests for workers, sitemap, reports, websocket and ingest (those suites are empty today).
4. Measure the NFRs on the demo machine: event-to-dashboard latency, FPS with all models running, recovery after an API restart, and a 2-hour soak.
5. Write a fresh-machine setup guide and a user manual.

### Stage 6: Report, demo and submission (Claude drafts; team approves and signs)
1. **Restructure the report to the guideline outline.**
   - **Ch.3 SRS:** interface requirements, FR list with IDs, use-case diagram and descriptions, measurable NFRs, resources, database requirements, feasibility.
   - **Ch.4 Modeling & Design:** design approach, UI screenshots, 4+1 views (class, sequence/activity, component, deployment), ERD, and algorithm/module details.
   - **Ch.5 Testing:** requirement-linked test cases with expected and actual results, plus model and event metrics with sample sizes and limitations.
2. Fix the stale claims: 10 classes, v5 metrics, fall detection implemented, actual module status.
3. Trim to ≤10,500 words by moving long tables to appendices. Abstract ≥250 words in 3–4 paragraphs.
4. Add front-matter pages as blank templates (the team fills in signatures and the Turnitin score), Appendices (user manual, API, dataset details), and IEEE references with ≥50% from the last 5 years.
5. Apply the formatting (Times New Roman, margins, captions, Roman/Arabic numbering) and regenerate the TOC and lists with `docs/update_fyp_report.py`.
6. Prepare the defence slides, a timed demo script, a fallback demo recording, and the CD contents.

**Team-only items throughout:**
- Biweekly supervisor meetings and the meeting log (13+ weekly entries).
- The scope decision.
- Hardware purchase and assembly.
- Recording PPE and fall videos.
- Label adjudication.
- Firebase/Colab accounts.
- Signatures and Turnitin.

## 5. Suggested order of execution

| Order | Work | Why first |
|---|---|---|
| 1 | Scope decision with supervisor; Stage 0 | Sets the denominator for the 80% gate |
| 2 | Stage 1 and Stage 2 | Visible demo quality; removes the fake data an examiner would catch |
| 3 | Stage 3 (start dataset fixes in parallel) | Needs GPU time and human labeling, so it has a long lead time |
| 4 | Stage 4: QR → PDF → mobile → vest → fire | Cheapest/no-hardware items first; order vest parts early |
| 5 | Stage 5 | Produces the test evidence for Ch.5 |
| 6 | Stage 6 (draft Ch.3/Ch.4 now, finalize last) | Worth 40 marks; the SRS/design restructure doesn't depend on code |
