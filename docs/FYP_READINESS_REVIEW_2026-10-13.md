# Site-Safe: FYP readiness and completion plan

Reviewed 13 October 2026 against the current working tree and the newly supplied FYP guide folder. This is an engineering and documentation assessment, not a university completion certificate. Application code, the original report and guides were not modified.

## 1. Current position

Site-Safe has a substantial integrated prototype, but it is not ready for a defensible claim that the full proposed project is complete. The strongest work is the Django API, React command centre, camera inference pipeline, incident management and automated decision-logic tests. The largest gaps are reliable AI evaluation, complete worker-level workflows, missing original-scope modules, truthful analytics, operational reliability and academic submission evidence.

The September planning estimates remain reasonable for the areas rechecked: **60–70% of a narrowed camera-first web prototype**, and **35–45% of the full scope stated in report sections 1.3–1.4**. These are rough planning ranges, not computed coverage or an official score. There is no approved weighted requirements/acceptance matrix in the reviewed materials from which to calculate an authoritative percentage. Do not use the narrower denominator unless the supervisor accepts that scope.

Three readiness questions have different answers:

| Question | Assessment |
|---|---|
| Does meaningful working software exist? | Yes. Core modules and selected integration paths exist. |
| Is the full stated FYP scope implemented and evidenced? | No. Several entire modules and connecting workflows are missing. |
| Is it ready for final submission or real construction-site reliance? | No. Submission evidence, validation and material correctness/security work remain. |

## 2. Sources and interpretation

Reviewed sources:

- [General report guide, 47 pages](</Users/hamza/Downloads/fyp guide/FYP-Report-General-Guidlines.pdf>).
- [Revised SOP, 69 pages](</Users/hamza/Downloads/fyp guide/Revised_FYP_SOP.pdf>).
- [Current FYP report](</Users/hamza/code/site-safe/docs/SiteSafe_FYP_Report_V7.docx>), extracted completely and rendered to 64 pages; selected front matter and chapter openings inspected visually.
- Current backend, frontend, AI and report-service code; model export metadata; [September audit](/Users/hamza/code/site-safe/docs/PROJECT_AUDIT_2026-09-20.md) and [AI roadmap](/Users/hamza/code/site-safe/docs/AI_ACCURACY_ROADMAP.md).

Page references below use PDF file page positions, not a sample report's internal numbering. The newly supplied SOP is byte-identical to `docs/Revised_FYP_SOP (1).pdf`. The separate general report guide adds useful detail that was not covered by the existing SOP copy alone.

### Resolve these document conflicts before reformatting

The general guide identifies Rawalpindi, the SOP identifies Islamabad, and the current report identifies Lahore. That does not establish which departmental template applies to this group.

| Topic | General guide | Revised SOP | Required decision |
|---|---|---|---|
| Chapter structure | Six chapters: introduction, background, SRS, modeling/design, testing, conclusion; p.3 | Six-chapter rubric matches much of the current outline, pp.35–40; a separate *possible* organization has seven chapters including standalone implementation, pp.66–68 | Supervisor/coordinator selects the applicable outline. Seven chapters are not automatically mandatory. |
| Separator-page number | Hidden but counted, p.4 | Displayed, p.10 | Confirm which convention governs. |
| Caption font | Arial Narrow 10, p.4 | Times New Roman 10, p.10 | Confirm applicable template. |
| Roman front numbering | Approval certificate through list of tables, p.4 | Dedication through TOC, p.11 | Confirm the front-matter sequence and numbering boundaries. |
| Bullets | Objectives exception, p.4 | No body bullets, p.10 | Use prose and numbered sections outside objectives; confirm objective formatting. |

These conflicts do not block fixing missing requirements, unreliable results, code defects or contradictory claims. Do not copy sample dates, officeholders, signatures or Turnitin scores as real submission information.

### Explicit academic gates

- SOP p.8: a supervisor-countersigned completion certificate is required; below 80% completion or above 18% similarity prevents presentation. This is an eligibility threshold, not a substitute for finishing the approved scope. The timeline on p.6 targets 100% implementation.
- SOP p.8: final report countersignature and meeting log are required; the stated missing-log penalty is severe. Their absence from the repository does not prove the students have not maintained them elsewhere.
- SOP pp.33–34: FYP-II assessment is 20 marks supervisor, 40 presentation/demo and 40 report. Coding alone cannot complete the assessment.
- SOP pp.39–40: the rubric assesses functioning hardware/software, clear code, accurate results, objective alignment, organization and references; its highest-mark reference criterion includes at least half the references from the last five years.
- SOP p.9: three hardbound copies, black for CS/green for SE, silver embossing, spine details and a CD containing proposal, final report, presentations, source, setup and user manual; supporting tutorials where applicable. Confirm local submission instructions and actual semester dates with the department.
- General guide p.4: 8,500–10,500 report words, excluding specified preliminary material, title pages and references. It does not explicitly exclude tables.

## 3. Fresh verification and its limits

| Check repeated on 13 October | Outcome | Meaning |
|---|---|---|
| Django isolated test suite | 59 tests pass | Selected role/API contracts and camera decision logic pass; not 59 complete user workflows. |
| AI utility unit suite | 10 tests pass | Audit/split-plan/configuration fixtures pass. |
| Strict local dataset audit | Fails | 573 inferred source groups cross splits; 30 exact-image duplicate groups cross splits; 69 exact-image groups have conflicting labels. |
| Dataset pairing/annotation shape checks | No reported pairing/row errors | Well-formed labels do not establish correct labels or independent splits. |
| Frontend build and lint | Could not execute: Vite/ESLint missing | Dependency installation is needed before either can be verified; this is not a demonstrated compilation failure. |
| Source reinspection | Major September gaps remain | Ingestion/socket authorization, synthetic measurements, disconnected settings, report calculations and delivery flaws remain visible. |
| Report content/layout | 64 rendered pages | Missing front matter, inconsistent chapter openings and outdated claims confirmed. This was not a certification of every page. |

No new live-camera, PostgreSQL integration, hardware, mobile, browser acceptance, report-service integration or model-accuracy pass is claimed. The September audit contains additional isolated defect reproductions; those were not all rerun this time. Existing user changes were preserved.

Reproducible checks from the repository root, using the existing root virtual environment:

```bash
(cd backend && ../.venv/bin/python manage.py test --settings=sitesafe.test_settings --verbosity 1)
(cd ai-module && ../.venv/bin/python -m unittest discover -p 'test_*.py' -v)
(cd ai-module && ../.venv/bin/python audit_dataset.py --strict)
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend run lint
```

The dependency-install command is a recommended next step, not a successful installation performed in this review.

## 4. Implementation inventory

“Present” below means code exists, not that the entire feature is accepted or field-validated.

| Area | Present now | Still required |
|---|---|---|
| Accounts and roles | Email/JWT login, roles, protected management endpoints, preferences | Device/socket authentication; token refresh; role-aware UI; stronger account validation; broader authorization checks. |
| Workers | CRUD API, cards, zone/vest links | Worker create/edit/deactivate UI; real presence; consistent vest assignment; identification workflow. |
| Incident management | List/detail/resolve, types, simulation, camera IDs, CSV | Reliable delivery; all-producer updates; evidence; reviewer outcomes; durable resolution history. |
| PPE | Ten-class model, overlays, threshold option, alert posting | Clean splits/labels; person-to-PPE association; temporal confirmation; class calibration; independent video evaluation. |
| Fall detection | Pose heuristic, persistence/latch, API type/migration, tests | Real fall/hard-negative videos; uncertain/occluded posture behavior; reliable event delivery. Do not list all fall work as unimplemented. |
| Proximity | Person/vehicle detector and tested image-plane distance logic | Per-pair tracking; camera calibration; industrial-vehicle coverage and field validation. |
| Inactivity | Camera-local tracks and timeout logic | Robust association, observation-gap handling and worker-linked activity records. |
| Cameras | Webcam/file/network sources, camera IDs, zone association | Persistent reconnect/supervision, API recovery, health/coverage state and capacity testing. Current repeated-read tolerance eventually exits. |
| Zones | CRUD, polygons, camera assignment, point-in-polygon and GPS transition logs | Map editor; meaningful live occupancy; automatic restricted-entry events; camera-space geofencing and validation. |
| Vests | Registry, assignment, HTTP telemetry/SOS and MQTT handlers | Staleness/offline rules; validated authenticated device messages; running MQTT service; physical vest/firmware/LoRa if retained. |
| Notifications | FCM registration and send hook | Receiving client, preference/rule enforcement, targeted recipients, queue/retry isolation; email implementation if retained. |
| Reports | DOCX generation service, proxy, saved-file/download flow | Correct compliance definition/data inclusion; service error handling; complete exports/date boundaries; PDF if retained. |
| Dashboard | Seven screens and socket/polling mechanisms | Genuine history/vitals/presence, worker forms, FALL filters, accurate role/site display, tested reconnect reconciliation. |
| QR/mobile/fire | Proposed documentation | No complete implementation found. |
| Delivery | Dependency manifests, backend environment example, report Dockerfile | Reproducible full setup, model distribution, clean install, CI, operations/user manuals and submission package. |

## 5. Prioritized engineering backlog

P0 means a blocker to credible demonstration/results; P1 means needed to complete the accepted prototype; P2 means an original-scope feature requiring implementation unless formally deferred. Production-only expansion should not obscure the FYP's agreed acceptance criteria.

### P0: Correctness, security and reliable events

1. **Replace fabricated dashboard measurements.** `frontend/src/lib/utils.js` derives last-seen/vitals from worker IDs and compliance from worker/alert counts; `DashboardCharts.jsx` uses fixed series. Add real historical aggregations and timestamps. Remove unavailable sensor values or show “not measured”; keep simulation explicitly labeled and separable from real reports. Do not build new temperature/heart-rate/gas hardware merely to justify placeholders if it is outside agreed scope.
   - Done when displayed values reconcile to recorded observations; empty/no-observation states cannot imply 100% safety.
2. **Authenticate all ingest and socket paths.** `backend/alerts/views.py` allows anonymous ingest/detection creation; vest telemetry does likewise; `DashboardConsumer.connect` accepts without checking the user. Remove embedded AI credentials, use scoped device/service authentication, enforce socket access and origin rules, and implement client token renewal.
   - Done when anonymous/unauthorized producers and subscribers are rejected and long-running authorized clients recover after expiration.
3. **Validate external data.** Check confidence ranges, box coordinates/schema, timestamps, camera IDs, GPS/battery/SOS values, zone polygon geometry and camera assignment lists. Decide overlapping-zone behavior.
   - Done when invalid input produces clear 4xx responses without corrupting state; accepted boundary cases have tests.
4. **Make alert settings effective.** Connect saved enabled/threshold/notification rules to runtime decisions; define configuration refresh/versioning; create usable default rules. Enforce user notification preferences and recipient scope. Queue push/email work so delivery failure does not break incident persistence.
   - Done when changing a rule changes observed behavior and disabled notifications produce no sends.
5. **Separate inference from network delivery.** Replace blocking posts with a durable bounded delivery queue, retries/backoff, idempotency keys and recovery when the API starts late or tokens expire. Advance delivery state only after successful handling; preserve events across process restarts. The current cooldown/latch can consume an event before it reaches the API.
   - Done when API outages do not freeze capture or silently lose/duplicate confirmed events after recovery.
6. **Unify live updates.** Publish created, updated and resolved alerts plus worker/vest state from every producer after successful database commit. Telemetry SOS currently creates an alert without the view-layer broadcast; resolve/update also lack broadcast. Reconcile full state on socket reconnect. Use a shared channel layer for multiple processes.
   - Done when two browser sessions converge after AI events, SOS, resolution, disconnect and reconnect.
7. **Repair report correctness.** Read upstream error content before closing the streamed response in `backend/reports/proxy.py`. Replace arbitrary compliance scoring in `report-service/templates/compliance-report.js`, which excludes worker-less camera alerts and treats empty zones as 100%. Define an observation denominator or report incident counts instead. Handle pagination, truncation disclosure, date/timezone boundaries, simulated sources and interrupted downloads.
   - Done when known fixtures reconcile exactly between API, dashboard and generated report, including empty data and service failure.

### P0: AI data and evaluation

8. **Finish dataset remediation before more model tuning.** Review all 69 conflicting duplicate-label groups; recover trustworthy source/session metadata; keep source siblings and duplicates within one split; implement the reviewed split materialization workflow. Existing `prepare_dataset_v2.py` output is a plan, not a repaired training set. Add rare absence-class examples, real backgrounds and difficult negatives; retain provenance/license records.
   - Done when the materialized dataset passes strict checks and manual label/source review. Zero inferred overlap alone does not prove independence when source metadata is missing.
9. **Seal an independent evaluation set.** Reserve complete source sessions/cameras/site periods before augmentation. Tune using validation only. Prior test results have already informed development, so use a new untouched final set for final generalization claims.
   - Done when the split manifest, provenance and locked evaluation protocol are reproducible.
10. **Make PPE alerts person-specific.** Associate equipment/body regions to stable person tracks, handle present/absent/not-observable states and conflicting boxes, use observed-time persistence and per-track cooldowns. Unknown visibility must not become a confident violation or compliance claim.
    - Done when multiple people with the same violation are handled independently and isolated detections do not create incidents.
11. **Evaluate models and events separately.** Train on the repaired data; compare controlled baselines; calibrate per-class thresholds. Record precision/recall/AP, per-class sample sizes, confusion/error examples and target-camera slices. Evaluate event precision, missed episodes, duplicate rate, false alerts per camera-hour, detection delay and inference throughput. Include confidence intervals appropriate to clustered video/session samples.
    - Done when the exact deployed weights/configuration are tied to a reproducible evaluation and supervisor-agreed acceptance targets. Passing geometry unit tests is insufficient.
12. **Validate fall, inactivity and proximity on videos.** Include normal bending, kneeling, partial bodies, crowds, dropped frames, camera angles, lawful breaks and different vehicles. Use per-person/per-pair continuity; limit stale observations. Do not claim metres from image-plane distance without calibration or industrial coverage from generic COCO classes.
    - Done when each enabled alert class has recorded positive and difficult-negative outcomes and known operating limits.
13. **Persist reviewable evidence.** Store source timestamp, camera/track, confidence, model/configuration hashes and appropriate snapshot/clip or detection evidence; capture confirmed/false-positive/uncertain review outcomes. Define access and retention for worker images.
    - Done when a report incident can be traced to the event and model/configuration that generated it.

### P1: Complete the accepted user workflows

14. Implement worker create/edit/deactivate forms and repair the duplicate vest identifier/assignment sources of truth.
15. Replace assigned-worker counts with observed occupancy/presence, distinguish assigned zone from observed zone, and expire stale vest/camera status.
16. Finish map/polygon interaction and restricted-entry alert logic; camera-to-zone assignment alone does not detect a worker crossing a boundary.
17. Link identity to ActivityLog generation; implement defined check-in/out, zone transitions, inactivity/break states, shift/overnight handling and historical views if worker-level monitoring remains in scope.
18. Correct FALL filters/simulation controls, role-dependent actions, logged-in identity, and the site selector. Implement actual site scoping only if required; otherwise remove unsupported multi-site behavior.
19. Add camera/service health, source reopen/backoff, supervised/headless inference and recovery tests. Distinguish file end-of-stream from network failure.
20. Complete and test report downloads/history, evidence access and receiving notification clients. Add PDF output if the PDF objective is retained; DOCX alone does not satisfy it.

### P2: Original commitments still missing

| Commitment | Minimum implementation and evidence if retained |
|---|---|
| QR worker identification | Identifier issuance/revocation, printable QR, camera decoding, safe track-to-worker association, unreadable/duplicate-code handling, worker-linked events and measured reading limits. |
| React Native app | Auth/refresh/roles, alert list/detail/resolve, worker status, configuration where authorized, FCM reception and navigation, device build and delivery tests. Backend FCM code is not a mobile app. |
| Physical Smart Vest / LoRa | Assembled ESP32/GPS/SOS prototype, firmware, battery/power design, gateway/MQTT lifecycle, device provisioning, loss/reconnect handling and physical verification. Simulator remains a simulator. |
| Fire/smoke and hot-work suppression | Dataset/model, inference integration, hot-work zone/time authorization, policy for fire outside allowed work, audit trail and false-negative/false-positive tests. Do not silently suppress real emergency evidence. |
| Worker-level workforce monitoring | Reliable identity, zones, activity state transitions, shifts/breaks, reports and acceptance demonstrations. Camera inactivity alone is insufficient. |
| PDF compliance documentation | Defined compliance semantics, worker/zone/shift evidence, PDF export and reproducible output tests. |

Moving a promised feature to “future work” in the conclusion does not by itself amend an approved proposal. Obtain a documented scope amendment or complete it.

## 6. Academic report backlog

| Requirement | Current assessment | Action |
|---|---|---|
| Approved scope and traceability | Broad commitments conflict with delivered subset | Assign FR/NFR IDs, priority, owner, acceptance criterion, code location, test/evidence and status. Reconcile with the approved proposal. |
| SRS | Module descriptions exist; no explicit complete SRS/measurable-NFR structure | Add functional/interface/data requirements, measurable nonfunctional targets, resources, feasibility and rationale. General guide pp.25–26; SOP pp.66–67. |
| Design | Use-case, context, architecture, DFD and ERD figures exist | Check DFD levels 0/1 semantics; add relevant detailed use cases, activity/sequence models and design class diagram. ERD is not a substitute for a class diagram. Add component/deployment views where they explain this multi-service system. General guide pp.28–35 explicitly allows relevance-based selection. |
| Test documentation | Summary tables and 59-test narrative exist | Add requirement-linked cases with setup, environment, steps, expected/actual result, date/tester, pass/fail and screenshot/log evidence; include failures and remediation. General guide pp.39–42. |
| NFR results | No complete measured acceptance table | Measure latency, throughput, recovery, authorization and usability against declared targets on named hardware/data. Avoid “efficient/accurate” without a metric. |
| Implementation/results consistency | Model and fall sections contradict other sections | Update the report as a whole from current evidence, including abstract, objectives, organization, tables, testing, conclusion and future work. |
| Front matter | Title, abstract, TOC and lists exist; approval/declaration/plagiarism/Turnitin pages absent | Add genuine required pages and obtain actual approvals/results. Keep signatures and scores unfilled until supplied. |
| Abstract | Three paragraphs, approximately 240 extracted words | General guide p.7 requires at least 250 words and 3–4 paragraphs. Add evaluation hardware, actual testing outcomes and concise limitations; do not inflate claims. |
| Word count | About 11,700 extracted body words including tables/captions/headings; prose-only about 9,020 | General guide ceiling is 10,500 excluding listed front/title/reference material. Confirm counting convention; likely trim/move long tables to appendices if tables count. These are extraction counts, not Microsoft Word's official submission count. |
| Layout | A4 and required margins present; inconsistent separators and styles | Chapters 1 and 4 share title and body content; chapter 5/6 openings differ. Use consistent section breaks, hierarchy, spacing, captions and selected numbering convention. Front matter currently shows Arabic numbers. |
| Citations/literature | Numbered list exists, some in-text references mismatch claims | Repair mappings: introductory ILO claim points to YOLOv3, labour-survey claim to harness detection. Verify each source and dataset provenance, include recent literature and cite every listed reference. This review did not independently validate every bibliography entry. |
| Appendices/manuals | No final appendix section found | Add installation, user/admin guide, API/schema/evaluation details where useful, contribution/accountability record and supporting evidence. General guide p.45. |
| Administrative detail | Title page says April 2026 | Confirm actual submission date, degree/campus, supervisor details and template. Use authentic student/supervisor records. |

Specific contradictions to repair:

- Objective 1 says eleven PPE classes; actual training/runtime use ten.
- Section 1.7 describes QR/mobile implementation even though later sections correctly mark it absent, and does not describe the full final chapter sequence.
- Sections 4.1, 4.3.3, 5.3 and 6.2 describe medium-model training as unfinished. The saved export manifest records a completed YOLO11m run and inference defaults to the newer weights.
- The old report metric is AP50 0.544. The saved newer test result is AP50 **0.562**, AP50–95 **0.345**, precision **0.467**, recall **0.728**. These are historical results from a compromised split, not a clean independent accuracy claim.
- Newer absence-class AP50 remains weak: no-boots **0.130**, no-gloves **0.062**, no-helmet **0.309**. Aggregate improvement does not establish reliable violation detection.
- Section 4.3.4 describes implemented fall detection, while 4.10, 4.11 and chapter 6 call it future/unimplemented. Correct status: implemented prototype logic, pending real-video validation and reliable integration.
- Bind results to actual weights by checksum and retained run artifacts; requested epochs are not necessarily completed epochs when early stopping is enabled.

The report updater is not a safe substitute for editorial review. Before regenerating, pin its true source document/revision and make the transformation reproducible/idempotent; it currently mixes content from different project states.

## 7. Completion sequence and acceptance gates

| Order | Work package | Exit gate |
|---|---|---|
| 1 | Agree scope/template and build FR/NFR matrix | Every original objective has an accepted implementation or documented deferral; selected outline and formatting are confirmed. |
| 2 | Repair truthful data, authentication, validation, rules, delivery and reports | Reproducible core workflow with no fabricated measurements; outage/reconnect and unauthorized-client cases pass. |
| 3 | Repair dataset and event logic | Audited materialized data, independent sealed test, person-level alert decisions and traceable evidence. Run alongside package 2 where possible. |
| 4 | Complete worker/zone/activity/client workflows and retained missing modules | Every retained requirement has working end-to-end behavior and recorded acceptance evidence. Identity precedes worker-linked activity/report claims. |
| 5 | Evaluate on target setup | PostgreSQL integration, frontend build/lint/browser tests, report integration, video metrics and NFR measurements pass agreed criteria. |
| 6 | Reconcile and format report | No contradictory claims; all results traceable; correct front matter, SRS/design/tests, citations, word count and page layout. Draft continuously, finalize after results. |
| 7 | Package and rehearse | Fresh-machine setup succeeds; reproducible model/data access; user manual, presentation, demo recording, contribution/log records and submission materials ready. |

This is several work packages, not a final cosmetic pass. A calendar estimate should follow the scope decision and availability of real datasets/hardware; mobile and physical vest work materially change the schedule. Do not promise a completion date from passing unit tests alone.

Minimum final demonstration: start from documented setup; sign in as each role; register/assign a worker and camera/zone; produce a real accepted camera event; show evidence and live notification; resolve it; show consistent state in another session; recover after an API/socket outage; export a reconciled report. Demonstrate QR/mobile/hardware/fire separately if they remain approved commitments. Preserve recordings and logs as evidence, labeling simulated inputs explicitly.

## 8. Definition of ready

- [ ] Approved scope, template and weighted requirement/acceptance matrix exist.
- [ ] Every retained functional requirement works through its complete user/device path.
- [ ] Critical security, false-data, lost-event and incorrect-report defects are resolved.
- [ ] Clean dataset/evaluation and event-level results support each AI claim at the deployed configuration.
- [ ] Required automated, integration, browser and target-environment acceptance checks pass.
- [ ] Fresh installation, model retrieval, configuration, operation and recovery are documented and verified.
- [ ] Report claims agree across abstract, scope, implementation, results and conclusion.
- [ ] Report meets the selected structure, word count, formatting, references and evidence requirements.
- [ ] Actual supervisor approval, meeting records and acceptable Turnitin output are obtained.
- [ ] Presentation, demo evidence, contribution records, manuals and required final submission media are complete.

Maintain this checklist against evidence. A working screen, stored enum, proposed diagram or simulated event should not be counted as a completed real-world feature.
