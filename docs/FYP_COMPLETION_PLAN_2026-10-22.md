# Site-Safe: plan to finish the FYP (project, report and submission)

Prepared 22 October 2026, after the supervisor approved the implementation plan. It replaces `FYP_COMPLETION_PLAN_2026-10-16.md`. Sources: the NUML FYP Report Guidelines, the Revised FYP SOP (sections 3.6–3.9, the FYP-II rubric and Appendix D), `REQUIREMENTS_TRACEABILITY.md` (requirement status) and the code on branch `stage-0-1-security-events` at commit `d1bb33f`.

## 1. What the approval is taken to mean

Two things in the repository were waiting on the supervisor. The plan assumes both are now approved; if either is not, say so and the affected rows below change.

1. **Smart Vest hardware moved to future work** (`SCOPE_CHANGE_SMART_VEST.md`). The vest's software path (telemetry API, MQTT consumer, simulator, breach alerts, offline detection) stays delivered. Once the form is signed, the report wording changes from "scope-change request" to "approved by the supervisor" in objective 8, Section 1.4 and Section 4.2.2.
2. **The proposed acceptance targets** in the traceability matrix (NFR-01 latency ≤ 2 s, NFR-02 exactly-once over a 5-minute outage, NFR-04 ≥ 10 FPS, NFR-05 2-hour soak, and the per-requirement criteria). With these agreed, "Accepted" becomes a reachable status and the completion percentage in Section 3 is defensible.

## 2. What the university grades (from the SOP)

| Component | Marks | What it needs from us |
|---|---|---|
| Supervisor score | 20 | A meeting log with weekly entries (understanding, explanation, supporting references). No log at the presentation = 50% deducted. |
| Presentation and demo | 40 | Topic knowledge, methodology, problem-solving, **results and analysis**, communication, and **accountability** (what each member did). |
| Report | 40 | Abstract; Ch.1 background, problem, objectives/scope, significance; Ch.2 existing work; Ch.3 proposed system; Ch.4 hardware/software design and algorithms/source; Ch.5 testing results and discussion; Ch.6 conclusion; references; writing; organisation. |

Gates before anyone presents: a **completion certificate ≥ 80%** countersigned by the supervisor, **Turnitin similarity ≤ 18%** (two attempts), and the meeting log. After the demo: three hard-bound copies (black, silver text, spine with degree, batch, title and year) and a CD with the proposal, final report, all presentations, source code, setup instructions and a user manual.

Schedule in the SOP's final semester: report submission week 10, plagiarism check week 11, evaluation week 13, hard binding week 16. **The actual dates for this semester are needed to put weeks on the tasks below.**

**Chapter structure.** The rubric grades the report by exactly the chapters V8 already has (proposed system, hardware/software design with algorithms, testing results and discussion, conclusion). The guideline's sequence (SRS, System Modelling and Design) and Appendix D are a "possible organisation". Recommendation: keep the semester-7 structure, which the rubric matches, and add the cheap Appendix D elements graders look for: a short feasibility paragraph and a use-case description for the three main actors in Chapter 3, and an appendix with the FR/NFR table. Only restructure if the supervisor asks.

## 3. Where the project stands (22 Oct 2026)

All ten objectives have working software. 318 automated tests pass. The code is committed on `stage-0-1-security-events` (16 commits since `main`, nothing pushed). Measured on one laptop: event-to-dashboard p95 42 ms, 100 events exactly once across a 5-minute outage with ~30 s recovery, 15.7 FPS for all detectors on the GPU. Two live webcam runs this week found and fixed duplicate PPE alerts.

Requirement status from the matrix (29 FR, 7 NFR):

| Status | Count | Requirements |
|---|---|---|
| Integrated (end to end on real services) | 17 | FR-01, 03, 09, 10, 11, 13, 18–21, 23, 24, 26–29; NFR-01, 02, 04 met |
| Tested (automated tests only) | 11 | FR-02, 05, 06, 07, 08, 12, 14, 15, 17, 22; NFR-03 |
| Coded only | 3 | FR-04 (PPE accuracy criterion unmet), FR-16 (push, no phone yet), FR-25 (CSV export untested) |
| Not met / not verified | 2 | NFR-05 (2-hour soak), NFR-06 (fresh-machine setup) |

Counting Integrated and Tested as complete against the approved scope gives **28 of 36 (78%)** before the work below, and the gaps are evaluation work, not missing features. Completing Phase A below takes it past the 80% gate with evidence, and the certificate should quote this table rather than a round number.

What is weakest, in the order it will cost marks:

1. **Detection accuracy has no field evidence.** The PPE model's held-out score (mAP@0.5 0.562) is an upper bound on a leaking split, and missing-equipment classes are poor (no-gloves 0.06, no-boots 0.13). Nothing has been scored on video from a real camera. This is the "results and analysis" criterion of the demo and Chapter 5.
2. **Fire/smoke has no trained model.** The policy and tests exist; the detector does not.
3. **Three measurements are still pending:** the 2-hour soak, push to a real phone, QR reading range.
4. **The report lacks the required front-matter pages** (approval certificate, declaration, plagiarism certificate, Turnitin report), roman page numbers, appendices and a user manual, and three Chapter 2 citations point to the wrong papers.
5. **Nothing exists yet for the presentation**: no slides, demo script, meeting log file or contribution statement.

## 4. Plan

"Me" = done in this session on request. "You" = needs your hardware, accounts, people or signatures. Weeks are relative to now until the semester dates are known.

### Phase A: evidence that the system works (weeks 1–2)

This phase moves requirements from Tested to Integrated/Physical and gives Chapter 5 real results. Each item ends with the matrix updated and the report rebuilt.

| # | Task | Who | Done when |
|---|---|---|---|
| A1 | **Annotated evaluation clip.** Record 3–5 minutes on the webcam or a phone: two or three people with and without helmets/vests, one wearing a printed badge, one idle for a minute, people crossing, someone leaving and returning after 30 s. Note the true episodes (who, what, start, end) in a simple CSV. I write `tools/evaluate_clip.py` that runs the pipeline on the clip, matches alerts to the annotations and reports per-person precision, recall, duplicates and delay. | You record and annotate; me the tool and scoring | FR-04 has an event-level score, FR-05/FR-10/FR-24 reach Integrated on real video; Chapter 5 gains a table |
| A2 | **QR range and lighting test.** Print three badge sizes (5, 8, 12 cm). For each: distance at which decoding first succeeds, straight-on and at 45°, in daylight and under room light. A short script logs decode success per frame. | You; me the logging script | A table of range by size, angle and light in Section 4.2.1 and Chapter 5 |
| A3 | **Fire/smoke model.** Download D-Fire (or another licence-checked dataset), run `fire/prepare_fire_dataset.py`, then train with the Colab notebook (T4, 2–3 h) or overnight on the laptop GPU. Then re-run `tools/measure/fps.py` with the fire stage and evaluate on a handful of recorded clips with welding/sunset negatives. | You run Colab (needs your Google account); me the preparation, local-training fallback, evaluation and FPS re-measure | `models/fire_smoke.pt` exists; FR-09 shows a video result; NFR-04 re-measured with all five stages |
| A4 | **Fall detection on real falls.** Evaluate on a public fall dataset clip set (UR Fall or Le2i, licence checked) plus a staged, safe fall on a mattress by the team. | Me the evaluation script and public-clip run; you the staged clip | FR-06 reaches Integrated with a hit/miss table |
| A5 | **2-hour soak.** Run `tools/measure/soak.py` for 2 h with the full stack (API, presence monitor, MQTT consumer, camera on a looped clip). | Me, during a session | NFR-05 met or a memory finding recorded |
| A6 | **Push to a real phone.** Create a Firebase project, add `google-services.json` and the service-account file, build an Android development build with EAS, install on a phone, record a push arriving and a resolve syncing to the web. | You (Firebase account, phone); me the config and the test script | FR-16 and FR-28 reach Integrated on a device |
| A7 | **LAN latency.** Run `tools/measure/latency.py` from the phone or a second laptop on the same Wi-Fi. | You (second device); me the run | NFR-01 measured over a network |
| A8 | **Fresh-machine setup and CI.** Push the branch so GitHub Actions runs every suite; install Docker Desktop and bring the compose stack up once. | You (push, Docker install); me the fixes if CI or compose fails | NFR-06 verified; CI green in the README |
| A9 | **Small gaps.** Tests for incident CSV export (FR-25); browser check of the Viewer role (FR-03); mark FR-29 Integrated from the live runs (snapshots were stored). | Me | Matrix rows updated |

### Phase B: improve what the evidence shows (weeks 2–4)

| # | Task | Who | Done when |
|---|---|---|---|
| B1 | **Resolve the 69 PPE label conflicts** using the adjudication queue in `ai-module/dataset_v2_plan/conflict_review.html`, then materialise the group-constrained split and retrain on Colab. Report both the old and the new score. | You adjudicate (about an hour); me the split, training setup and tables | Chapter 5 reports a leak-free score; Section 4.3.1 no longer needs the caveat |
| B2 | **Per-class thresholds** calibrated on the A1 clip and the new validation split, replacing the single 0.15 candidate threshold. | Me | FR-04 criterion measurable per class |
| B3 | **Target-camera data.** Label 150–300 frames from your own camera (with the team) and add them to training; this is the single biggest accuracy lever for missing-equipment classes. Optional if time is short. | You label; me the extraction and tooling | Re-evaluation on A1 shows the gain |
| B4 | Fixes that A1–A7 reveal (the two live runs each found one). | Me | Each fix has a test and a Table 5.8 row |

### Phase C: the report (weeks 1–3, in parallel)

| # | Task | Who | Done when |
|---|---|---|---|
| C1 | **Front matter from the SOP templates (Appendix G):** Final Approval Certificate, Declaration, Plagiarism Certificate, Turnitin Originality placeholder page, Acknowledgement; roman numerals on those pages; no page numbers on chapter title pages; title-page date and campus. | Me the pages; you the names, roll numbers and the actual Turnitin report | Sequence matches the guideline page 3 |
| C2 | **Vest wording** from "request" to "approved" once the form is signed. | Me, after you confirm | Three places updated |
| C3 | **Citation fixes:** Labour Force Survey year/figure against [17]; the Sacks, Nath/Behzadan/Paal and Ramli citations in Chapter 2 replaced with the correct papers; check every reference exists as written. 19 of 23 references are from 2022 or later, so the recency rule is met. | You find the right sources (or confirm the ones I propose); me the edits | No citation points to the wrong paper |
| C4 | **Chapter 3 additions from Appendix D** without restructuring: a feasibility paragraph (technical, operational, legal/ethical, including camera privacy), use-case descriptions for Admin, Safety Officer and the camera, and a pointer to the FR/NFR appendix. Trim elsewhere to stay under 10,500 words. | Me | Word count 9,500–10,500 |
| C5 | **Chapter 5 and 6 from Phase A/B results:** clip evaluation table, QR range table, fire results, soak, push, LAN latency; conclusion and objectives table updated. | Me, as each result lands | No "not yet measured" row that could have been measured |
| C6 | **Appendices:** I user manual (web, mobile, camera), II setup guide (from the README), III API summary, IV data dictionary, V requirements matrix. Appendices do not count towards the word limit. | Me | Present in the TOC with page numbers |
| C7 | **Final render in Word**, page numbers measured, PDF exported; then your Turnitin run (≤ 18%). | Me the render; you Turnitin | V9 signed off by the supervisor |

### Phase D: presentation and submission package (weeks 3–4)

| # | Task | Who | Done when |
|---|---|---|---|
| D1 | **Meeting log.** I draft weekly entries from the git history (what was done, what was learned, references used); you correct them against the meetings that actually happened and get them signed. | Both | A log with weekly entries since the start of the semester |
| D2 | **Contribution statement** (CLO-8, "accountability"): who did what, by module, agreed by the three of you. | You | One table, also used in the slides |
| D3 | **Slides** (15–20): problem, objectives, architecture (the Chapter 4 figures), demo, results tables, limitations, future work, contributions. | Me the deck; you the rehearsal | Deck in the CD folder |
| D4 | **Demo script** with a fallback: the live webcam path, and a recorded clip plus the vest simulator in case the room has no usable camera. Rehearse once end to end, timed. | Me the script and the clip; you the rehearsal | Under 12 minutes, every step tried once |
| D5 | **Completion certificate** text with the percentage from Section 3, updated after Phase A. | Me the draft; you the signatures | Signed before the presentation |
| D6 | **CD folder:** proposal, final report (docx and PDF), all presentations, source archive (`git archive`, without weights), model weights, setup guide, user manual. | Me | One folder that opens on another machine |
| D7 | Three hard-bound copies and the spine text. | You | After the report is approved |

### Housekeeping (this week)

- Branch `claude/competent-moore-5fa363` ("Fix report table widths") was started by another session and duplicates commit `9f79303`; it can be deleted. The FR-29 session's worktree branch `claude/beautiful-mclaren-ab41fd` is merged and can be deleted too.
- Rotate the old admin password that was once committed (noted since Stage 1).
- `docs/Revised_FYP_SOP (1).pdf` is a duplicate of the SOP; remove it.

## 5. Order of work

Week 1: A1 (record the clip first; everything downstream uses it), A3 (start the fire download and training early, it runs unattended), A5, A9, C1, C2, D1 draft. Week 2: A2, A4, A6, A7, A8, C3, C4, B1 adjudication. Week 3: B1 retrain, B2, C5, C6, D3, D4. Week 4: B3 if time allows, C7, D2, D5, D6, rehearsal.

## 6. Execution split (revised 22 Oct: priority is a complete project and a complete report)

Meeting log, completion certificate and Turnitin are deferred; they are done last, from templates, once the report is final. Everything below is ordered by how much it adds to the demo and to Chapter 5.

### 6.1 Done by Claude in this repository, no input needed

| Order | Task | Output |
|---|---|---|
| 1 | 2-hour soak (NFR-05) with the full stack on a looped clip | Table 5.6 with a real result |
| 2 | `tools/evaluate_clip.py`: runs the pipeline on a video, matches alerts to an annotation CSV, reports per-person precision, recall, duplicates and delay | Ready for the clip in 6.2 |
| 3 | Fire/smoke: download and licence-check D-Fire, prepare it, train YOLO11-small overnight on this laptop's GPU, evaluate, re-measure FPS with five stages | `models/fire_smoke.pt`; FR-09 and NFR-04 rows; Chapter 4.3.5 and 5 updated |
| 4 | Fall detection on a public fall dataset (UR Fall / Le2i, licence checked) | FR-06 hit/miss table |
| 5 | Adjudicate the 69 PPE label conflicts (decision recorded per group), materialise the group-constrained split, retrain overnight, report old and new scores | Leak-free Table 4.6; Section 4.3.1 caveat resolved |
| 6 | Per-class candidate thresholds from the new validation split | FR-04 measurable per class |
| 7 | Small gaps: CSV export tests (FR-25), Viewer role browser check (FR-03), FR-29 marked Integrated from the live runs, MQTT path verified live with a local Mosquitto | Matrix rows updated |
| 8 | Fresh-clone setup check: clone into a temporary folder and follow the README from scratch (NFR-06) | README corrected; setup script if needed |
| 9 | Report: roman numerals on front matter, no numbers on chapter title pages, vest wording to "approved", Chapter 2 citations verified or rewritten against real sources, feasibility and use-case descriptions in Chapter 3, Chapters 5–6 updated after each result, appendices (user manual, setup, API, data dictionary, requirements matrix), final Word render | Report V9 |
| 10 | Later, from templates: approval certificate, declaration, plagiarism and Turnitin pages; slides and demo script; meeting-log draft from git history | Submission package |

### 6.2 Needs you (hardware, accounts, people)

| # | What | Why Claude cannot do it | What to hand over |
|---|---|---|---|
| Y1 | Record the evaluation clip: 3–5 min, 2–3 people with and without helmet/vest/gloves, one with a printed badge, one idle for a minute, people crossing, someone leaving and returning after 30 s; note the true episodes (person, item, start, end) | Needs people, PPE and a camera | The video file and the CSV (template provided with the tool) |
| Y2 | QR range test: print badges at 5, 8 and 12 cm; for each, note the distance at which decoding starts, straight-on and at 45°, daylight and room light | Needs printed badges and the room | The filled table (the logging script prints decode success) |
| Y3 | Every live webcam run of the pipeline | macOS camera permission is granted to Terminal, not to this session | Paste the Terminal output after each run |
| Y4 | A staged fall on a mattress, filmed, with two "not a fall" clips (crouch, sit) | Safety and people | Three short clips |
| Y5 | Push notifications: Firebase project, `google-services.json` and service-account file, Expo account, an Android development build installed on a phone | Google and Expo accounts, a phone | The two config files; then one push and one resolve from the phone, screenshots |
| Y6 | LAN latency: run the latency script from a second device on the same Wi-Fi | A second device | The result JSON |
| Y7 | Docker Desktop install; push the branch to GitHub so CI runs | Administrator install; pushing is your call | Say when installed; say "push" |
| Y8 | Keep the laptop awake and plugged in overnight twice (fire training, PPE retraining) | Training runs for hours | Nothing else |
| Y9 | Feature acceptance pass in the browser and the mobile web build: sign in as each role, register a worker and print a badge, draw a zone, issue and revoke a permit, resolve an alert from the phone and watch it leave the web, generate both reports in both formats | Your judgement of what looks wrong to a user | A list of anything wrong or confusing |
| Y10 | Month and year of submission for the title page; confirm the campus name | Not in the repository | Two words |
| Y11 | Optional, biggest accuracy lever: 150–300 frames from your own camera with PPE on and off, labelled by the team with the provided tool | Needs your site and people | The labelled folder |

## 7. Order

Week 1: 1, 2, 3 (training overnight), 9 (front matter, vest wording, citations), with Y1, Y3 and Y10 from you. Week 2: 4, 5 (retraining overnight), 7, 8, Chapter 3 additions, with Y2, Y4, Y5, Y9. Week 3: 6, Chapters 5–6 and appendices from all results, final render; Y6, Y7, Y11 if available. Week 4: item 10.
