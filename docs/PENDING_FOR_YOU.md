# Waiting on you

Everything that has been skipped or deferred, or that needs your hardware, accounts, decisions or signatures. When you are ready for one, say "do item A1" (or similar), and it is picked up from here. Items move to the **Done** list at the bottom when finished; the traceability matrix ledger records the evidence.

Kept since 27 October 2026; last reviewed 27 October 2026, after Phase 4. Update this file whenever something is skipped or deferred.

## A. Skipped or deferred in sessions

| # | Item | Skipped | What it takes | What it unblocks |
|---|---|---|---|---|
| A1 | **Record and score a webcam clip for PPE episodes** | 27 Oct (Phase 1) | 60 s of you in front of the webcam without helmet/vest/goggles: sit, lean in and out, turn, move left and right, step out of view for about 3 s and come back. Record with `python tools/measure/record_clip.py --out tools/measure/results/clips/webcam_one_person_01.mp4 --seconds 60` from your own Terminal (it has camera permission), then say which PPE items you were missing. Scoring is automatic. | FR-05 scored on real video (target: one alert per missing item), Chapter 5 evidence |
| A2 | **Record today's real-webcam run in the matrix** | 27 Oct ("not yet") | Nothing new: the 27 Oct run is already in the dev database (14 webcam alerts with snapshot and model version; live grid at 5 frames/s). Say when to write it up. | FR-29 and FR-30 move from "synthetic only" to a real camera |
| A3 | **Push the branch so CI runs** | 27 Oct (Phase 0 and 1) | Your go-ahead to push `stage-0-1-security-events` to GitHub. | CI runs every suite on GitHub; first step of NFR-06 |
| A5 | **Gas detection** | 27 Oct | Supervisor approval of a scope change. If approved: a scope-change note (offered), then software with a labelled simulator, then optional demo sensors (ESP32 + MQ-series, not certified). | A visible gas-monitoring feature |
| A6 | **Report layout polish** | 27 Oct (Phase 4) | The Word render has blank pages after the Chapter 2 and Chapter 4 title pages and before the Chapter 5 title page (PDF pages 20, 52 and 71), and chapter title pages still carry a page number, which the guideline says they should not. Fixable in `build_report_v8.py`; needs another Word render with you at the Mac. | A layout that follows the FYP guideline |
| A7 | **Redraw Figure 3.4 (Level-1 DFD)** | 27 Oct (Phase 4) | The diagram, kept from V7, still shows Firebase as a telemetry store; Firebase only sends push notifications. It can be drawn by `make_figures.py` to match Figure 3.10. | A Chapter 3 diagram that matches the system |
| A8 | **Migrate your development database** | 27 Oct (offered in each phase) | 8 migrations are not applied yet: alerts 0013–0014, reports 0003, sitemap 0004–0006, workers 0008–0009. Back up first, then migrate, from `backend/`: `pg_dump -Fc -U sitesafe_user sitesafe_db > ../backups/sitesafe_db_before_phase2.dump`, then `python manage.py migrate`. Or say "do item A8" and it is done with a backup. | Running the latest code against your own data |
| A9 | **Install the new mobile packages in your main checkout** | 27 Oct (Phase 2 item 5) | Before running the mobile app from `/Users/hamza/code/site-safe`: `cd mobile && npm ci` (adds react-native-webview and react-native-svg). | The mobile Map and camera screens in your own runs |

## B. Decisions waiting on you

| # | Question | Default if you don't decide |
|---|---|---|
| B1 | An **unidentified person** (no readable badge) in a **restricted zone**: raise an alert, or only count them? Today they are counted in the zone's head count (visible on the map) but raise nothing. Since 27 Oct a danger area drawn over the restricted part of a camera's picture alerts anyone, badge or not, so this decision only concerns zones without such an area. | Counted only; no alert until decided |
| B2 | Does any camera on your site look at **two zones**? A camera id belongs to one zone only (the API refuses a second). Since 27 Oct a hazardous part of its view can be drawn as a danger area instead (FR-32). Counting people separately for two zones seen by one camera would be a further change; say if you need it. | One zone per camera; danger areas for parts of a view |
| B3 | Snapshot **retention period** and whether snapshots are allowed on site at all. Since 27 Oct reports can also carry snapshots (FR-34); each report can leave them out, and the history shows which include them | 30 days, snapshots on, included in reports unless unticked |
| B4 | Revoke the **WEBCAM-TEST** device token in Django admin after testing | Left active |

## C. Needs your hardware, accounts, people or signatures

| # | Item | Notes |
|---|---|---|
| C1 | **QR badge range test** | Print badges at 5, 8 and 12 cm; test distance, 45° angle, daylight and room light (FR-10 to Physical) |
| C2 | **Android build with push** | Firebase project (`google-services.json` + service account), an Android phone, an EAS development build; record a push arriving and a resolve syncing to the web (FR-16, FR-28) |
| C3 | **LAN latency** | Run `tools/measure/latency.py` from a second device on the same Wi-Fi (NFR-01 over a network) |
| C4 | **Fresh-machine and Docker** | Install Docker Desktop, bring up `docker-compose`, follow the README on a clean machine (NFR-06) |
| C5 | **Fall clip** | A staged, safe fall on a mattress, plus licence-checked public fall clips (FR-06) |
| C6 | **Fire clips and D-Fire licence** | Confirm and cite D-Fire's licence; licensed clips with real fire/smoke and look-alikes (sunsets, orange vests, welding sparks, dust) to evaluate FR-09 alerts |
| C7 | **Annotated activity scenario** | Badge visible, idle for a minute, leave and return, to check the attendance timeline (FR-24) |
| C8 | **PPE label conflicts** | About an hour adjudicating the 69 conflicting label groups (`ai-module/dataset_v2_plan/conflict_review.html`) before a leak-free retrain (FR-04) |
| C9 | **Your own camera footage** | 150–300 labelled frames from the target camera, the biggest accuracy gain for missing-equipment classes (optional) |
| C10 | **Supervisor sign-offs** | Smart Vest hardware moved to future work; the proposed acceptance targets; the report metrics replacing a compliance percentage |
| C11 | **Report admin** | Semester dates; the title page (still LAHORE and April 2026: date and campus); Chapter 2 citations and the Labour Force Survey figure to verify (`docs/REPORT_V8_CHANGES.md`, items 2–3); approval, declaration and Turnitin pages; meeting log; contribution statement and the task-division row of Table 3.9; keep the Colab log as evidence for "102 of 150 epochs". After C10 is signed, the Smart Vest wording changes from "scope-change request" to "approved by the supervisor" (objective 8, Sections 1.4 and 4.2.2) |
| C12 | **Smart Vest hardware** | Only if approved later: ESP32, GPS, SOS button, LoRa link (FR-21) |
| C13 | **Real camera positions** | Where each camera is mounted on your site and which way it faces, to place them on the site map (Zones → Site Map → Place). The demo site from `setup_demo` places only CAM-01, at its demo zones (FR-33) |
| C14 | **New mobile development build on your phone** | The Map and camera screens (27 Oct) use two native modules that an older development build lacks. With the phone on USB: `cd mobile && npx expo run:android`, or `npx eas-cli@latest build --profile development --platform android`. Expo Go needs nothing new. Then check the Map and a camera's live picture on the phone (FR-28) |
| C15 | **Rehearse the demonstration** | Follow "The day before" in `docs/DEMO_SCRIPT.md`: a separate `sitesafe_demo` database, `python manage.py setup_demo` (store the passwords and keys it prints once), print Ali Raza's badge, draw and delete a danger area over the floor in view, record the fallback clip with `record_clip.py`, and run the 12-minute script once against the clock. Needs your webcam, a printer and your phone |
| C16 | **Vehicle proximity on real video** | 1–2 minutes from a fixed camera of a person walking past and then standing beside a parked car. It scores FR-07 on video and checks the one-alert-per-encounter rule: on the looping test clip, one unidentified person was re-alerted every 2–3 minutes |

## Done

| Item | Done | Evidence |
|---|---|---|
| V8 report rendered in Word (was A4) | 27 Oct | `docs/SiteSafe_FYP_Report_V8.docx/.pdf`, 95 pages, all 147 contents and list entries match the render; text covers Phases 0–2 |
| Fire/smoke model trained (was a deferred human input) | 27 Oct | Kaggle v1, held-out mAP50 0.787; matrix FR-09 |
| Dev database migrated for FR-29 | before 27 Oct | `backups/sitesafe_db_before_fr29_20261020_1943.dump`; the migrations added since are item A8 |
| 2-hour soak run | 22 Oct | `tools/measure/results/soak_20261022T144721Z.json` (PASS); Chapter 5 tables regenerated and NFR-05 marked Met on 27 Oct |
