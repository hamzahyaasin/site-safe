# Waiting on you

Everything that has been skipped or deferred, or that needs your hardware, accounts, decisions or signatures. When you are ready for one, say "do item A1" (or similar), and it is picked up from here. Items move to the **Done** list at the bottom when finished; the traceability matrix ledger records the evidence.

Kept since 27 October 2026. Update this file whenever something is skipped or deferred.

## A. Skipped or deferred in sessions

| # | Item | Skipped | What it takes | What it unblocks |
|---|---|---|---|---|
| A1 | **Record and score a webcam clip for PPE episodes** | 27 Oct (Phase 1) | 60 s of you in front of the webcam without helmet/vest/goggles: sit, lean in and out, turn, move left and right, step out of view for about 3 s and come back. Record with `python tools/measure/record_clip.py --out tools/measure/results/clips/webcam_one_person_01.mp4 --seconds 60` from your own Terminal (it has camera permission), then say which PPE items you were missing. Scoring is automatic. | FR-05 scored on real video (target: one alert per missing item), Chapter 5 evidence |
| A2 | **Record today's real-webcam run in the matrix** | 27 Oct ("not yet") | Nothing new: the 27 Oct run is already in the dev database (14 webcam alerts with snapshot and model version; live grid at 5 frames/s). Say when to write it up. | FR-29 and FR-30 move from "synthetic only" to a real camera |
| A3 | **Push the branch so CI runs** | 27 Oct (Phase 0 and 1) | Your go-ahead to push `stage-0-1-security-events` to GitHub. | CI runs every suite on GitHub; first step of NFR-06 |
| A4 | **Rebuild the V8 report in Word** | 27 Oct, deferred to Phase 4 | Word opens on your Mac and asks once for automation permission. Done together with the Phase 4 text updates (fire model, evidence, live grid, zoning, final counts). | Report matches the code; the current .docx/.pdf are the build from commit f1d917f |
| A5 | **Gas detection** | 27 Oct | Supervisor approval of a scope change. If approved: a scope-change note (offered), then software with a labelled simulator, then optional demo sensors (ESP32 + MQ-series, not certified). | A visible gas-monitoring feature |

## B. Decisions waiting on you

| # | Question | Default if you don't decide |
|---|---|---|
| B1 | An **unidentified person** (no readable badge) in a **restricted zone**: raise an alert, or only count them? Today they are counted in the zone's head count (visible on the map) but raise nothing. Since 27 Oct a danger area drawn over the restricted part of a camera's picture alerts anyone, badge or not, so this decision only concerns zones without such an area. | Counted only; no alert until decided |
| B2 | Does any camera on your site look at **two zones**? A camera id belongs to one zone only (the API refuses a second). Since 27 Oct a hazardous part of its view can be drawn as a danger area instead (FR-32). Counting people separately for two zones seen by one camera would be a further change; say if you need it. | One zone per camera; danger areas for parts of a view |
| B3 | Snapshot **retention period** and whether snapshots are allowed on site at all | 30 days, snapshots on |
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
| C11 | **Report admin** | Semester dates; title-page date; Chapter 2 citations and the Labour Force Survey figure to verify; approval, declaration and Turnitin pages; meeting log; contribution statement |
| C12 | **Smart Vest hardware** | Only if approved later: ESP32, GPS, SOS button, LoRa link (FR-21) |

## Done

| Item | Done | Evidence |
|---|---|---|
| Fire/smoke model trained (was a deferred human input) | 27 Oct | Kaggle v1, held-out mAP50 0.787; matrix FR-09 |
| Dev database migrated for FR-29 | before 27 Oct | `backups/sitesafe_db_before_fr29_20261020_1943.dump`; no migrations pending on 27 Oct |
| 2-hour soak run | 22 Oct | `tools/measure/results/soak_20261022T144721Z.json` (PASS); tables and NFR-05 status still to be updated in the matrix |
