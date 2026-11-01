# Waiting on you

Everything that has been skipped or deferred, or that needs your hardware, accounts, decisions or signatures. When you are ready for one, say "do item A1" (or similar), and it is picked up from here. Items move to the **Done** list at the bottom when finished; the traceability matrix ledger records the evidence.

Kept since 27 October 2026; last reviewed 1 November 2026, after every item that needed no input from you was done (A2, A6, A8, A9, A11, A12). Update this file whenever something is skipped or deferred.

## A. Skipped or deferred in sessions

| # | Item | Skipped | What it takes | What it unblocks |
|---|---|---|---|---|
| A1 | **Record and score a webcam clip for PPE episodes** | 27 Oct (Phase 1) | 60 s of you in front of the webcam without helmet/vest/goggles: sit, lean in and out, turn, move left and right, step out of view for about 3 s and come back. Record with `python tools/measure/record_clip.py --out tools/measure/results/clips/webcam_one_person_01.mp4 --seconds 60` from your own Terminal (it has camera permission), then say which PPE items you were missing. Scoring is automatic. | FR-05 scored on real video (target: one alert per missing item), Chapter 5 evidence |
| A3 | **Push the branch so CI runs** | 27 Oct (Phase 0 and 1) | Your go-ahead to push `stage-0-1-security-events` to GitHub. | CI runs every suite on GitHub; first step of NFR-06 |
| A5 | **Gas detection** | 27 Oct | Supervisor approval of a scope change. If approved: a scope-change note (offered), then software with a labelled simulator, then optional demo sensors (ESP32 + MQ-series, not certified). | A visible gas-monitoring feature |
| A10 | **Export the V8 PDF from Word** | 27 Oct (figures), 1 Nov (references, layout, charts; held back at your request) | Say "do item A10" when you have looked at `docs/SiteSafe_FYP_Report_V8.docx`. Word is closed now, so nothing else is needed from you. The .docx (92 pages) already carries everything; `docs/SiteSafe_FYP_Report_V8.pdf` is still the 95-page 27 Oct export with the old figures, references and blank pages. | A PDF that matches the .docx |

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
| C11 | **Report admin** | Semester dates; the title page (still LAHORE and April 2026: date and campus); approval, declaration and Turnitin pages (run Turnitin on the final PDF; the SOP allows at most 18% similarity); meeting log; contribution statement and the task-division row of Table 3.9; keep the Colab log as evidence for "102 of 150 epochs". After C10 is signed, the Smart Vest wording changes from "scope-change request" to "approved by the supervisor" (objective 8, Sections 1.4 and 4.2.2) |
| C12 | **Smart Vest hardware** | Only if approved later: ESP32, GPS, SOS button, LoRa link (FR-21) |
| C13 | **Real camera positions** | Where each camera is mounted on your site and which way it faces, to place them on the site map (Zones → Site Map → Place). The demo site from `setup_demo` places only CAM-01, at its demo zones (FR-33) |
| C14 | **New mobile development build on your phone** | The Map and camera screens (27 Oct) use two native modules that an older development build lacks. With the phone on USB: `cd mobile && npx expo run:android`, or `npx eas-cli@latest build --profile development --platform android`. Expo Go needs nothing new. Then check the Map and a camera's live picture on the phone (FR-28) |
| C15 | **Rehearse the demonstration** | Follow "The day before" in `docs/DEMO_SCRIPT.md`: a separate `sitesafe_demo` database, `python manage.py setup_demo` (store the passwords and keys it prints once), print Ali Raza's badge, draw and delete a danger area over the floor in view, record the fallback clip with `record_clip.py`, and run the 12-minute script once against the clock. Needs your webcam, a printer and your phone |
| C16 | **Vehicle proximity on real video** | 1–2 minutes from a fixed camera of a person walking past and then standing beside a parked car. It scores FR-07 on video and checks the one-alert-per-encounter rule: on the looping test clip, one unidentified person was re-alerted every 2–3 minutes |

## Done

| Item | Done | Evidence |
|---|---|---|
| Live webcam run written up in the matrix (was A2) | 1 Nov | `REQUIREMENTS_TRACEABILITY.md` FR-29/FR-30 rows and ledger: 14 WEBCAM-TEST alerts of 27 Oct, each with its frame on disk and model version `sitesafe_v5.pt@7e8e092d0603`; report Table 5.2 and Table IV.2 updated |
| Report layout: unnumbered title pages, no blank pages (was A6) | 1 Nov | `title_page_sections()` in `build_report_v8.py`; Word render checked: 92 pages, no blank page, every chapter and appendix title page unnumbered, the abstract no longer spills onto a blank page; all 150 contents and list entries match |
| Dev database migrated (was A8) | 1 Nov | Backup `backups/sitesafe_db_before_phase2_20261101_1455.dump`; the 8 migrations applied, `showmigrations` has none left |
| Mobile packages installed in the main checkout (was A9) | 1 Nov | `npm ci` (react-native-svg and react-native-webview present); typed routes regenerated; tsc and lint clean, 25 tests pass |
| Figure 4.3 screenshots at 1600 px (was A11) | 1 Nov | `docs/manual/web_area_live.jpg`, `web_sitemap.jpg` (1600×1000) from a throwaway demo database (dropped afterwards) with a test video as CAM-01 and the vest simulator |
| Chapter 5 charts (was A12) | 1 Nov | Figures 5.1–5.3 from `docs/figures/make_charts.py`; PPE confusion matrix from `ai-module/scripts/held_out_confusion.py` (reproduces mAP@0.5 0.5621); body text +4 words, still under 10,500 |
| Figures 3.1–3.8 redrawn, Figure 3.4 matches Figure 3.10 (was A7); Chapter 4 figure fixes; captions in Arial Narrow 10 pt; editable .drawio and .svg for every diagram | 27 Oct | `docs/figures/make_figures.py`, `docs/figures/editable/` (see its README); report rebuilt |
| V8 report rendered in Word (was A4) | 27 Oct | `docs/SiteSafe_FYP_Report_V8.docx/.pdf`, 95 pages, all 147 contents and list entries match the render; text covers Phases 0–2 |
| Fire/smoke model trained (was a deferred human input) | 27 Oct | Kaggle v1, held-out mAP50 0.787; matrix FR-09 |
| Dev database migrated for FR-29 | before 27 Oct | `backups/sitesafe_db_before_fr29_20261020_1943.dump`; the migrations added since are item A8 |
| 2-hour soak run | 22 Oct | `tools/measure/results/soak_20261022T144721Z.json` (PASS); Chapter 5 tables regenerated and NFR-05 marked Met on 27 Oct |
