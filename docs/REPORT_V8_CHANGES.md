# Report V8: what changed and what the team must check

`docs/SiteSafe_FYP_Report_V8.docx` is built from the submitted V7 (left unchanged) by `docs/build_report_v8.py`. The text lives in `docs/report_v8_content.py` and the figures come from `docs/figures/make_figures.py`. Edit those files and rebuild; don't hand-edit the .docx, or the next build will overwrite the edits. The build, render and page-number commands are in the docstring of `build_report_v8.py`.

The .docx (rebuilt 1 Nov 2026, 92 pages) has its contents and list page numbers measured from a Word render: all 150 entries match the final render. `docs/SiteSafe_FYP_Report_V8.pdf` is still the 27 Oct export (95 pages, old figures, references and layout); export it again from Word before submission.

Fixed on 21 Oct 2026: the shared table helper in `update_fyp_report.py` wrote widths in EMUs where Word expects twips, so 18 tables claimed to be about 3,800 inches wide. Word laid them out off the page, which made Table 4.1 look broken and pushed later chapters out of view. LibreOffice had silently clamped the widths, so this didn't show in the earlier checks. V7 already had five such tables from the same helper.

## Length

Body text of Chapters 1–6, excluding headings, captions, tables, front matter, chapter title pages, appendices and references: **about 10,495 words** (the guideline allows 8,500–10,500, so there is almost no room left). The Chapter 5 charts of 1 Nov 2026 added 4 words net (the text tightened to pay for the references to them), and the restricted-zone sentence in 3.3.2 (decision B1) 3 more. The reference fix of 1 Nov 2026 added 20 words, all of them citation numbers; the rewritten Chapter 1 and 2 paragraphs are no longer than before. Tables in the chapters add 2,969 words and the appendices 2,006.

Tables 4.7, 4.8, 5.2, 5.7 and 5.8 (1,309 words) moved to Appendices III and IV on 26 Oct 2026; the builder renumbers the tables left behind and rewrites every reference. The new requirements tables in Chapter 3 add 1,676 words, so if the examiners count table text, the chapters are over the cap either way; moving Table 3.4 (functional requirements, 580 words) to an appendix would be the next step.

## Figures redrawn on 27 Oct 2026

V7's Figures 3.1–3.8 were placed in boxes of a different shape from their images, so seven of them printed stretched (up to 1.8 times taller). They are now drawn by `make_figures.py` in the style of the Chapter 3 and 4 diagrams, and placed at their true proportions.

| Figure | Change |
|---|---|
| 3.1 | Use cases numbered and linked to actors as in Table 3.5; «include» from UC-3 to UC-4. |
| 3.2 | The system boundary holds the camera pipeline, API, web, mobile app and report service; Emergency Services (never built) removed. |
| 3.3 | Tiers named Edge, Network and Application as in Section 3.2.1, with the per-model frame rates. |
| 3.4 | Redrawn as five processes, three stores and the entities of Figure 3.10, so the two levels balance; Firebase is no longer a data store. |
| 3.5 | Same content, readable. |
| 3.6 | Battery 2500 mAh as in the text (was 2000), pins as in Table 4.3, TP4056 charger shown. |
| 3.7 | The "no fix" branch now rejoins the flow; SOS and zone breach branches end in notification. |
| 3.8 | Drawn as phone screens; no overlapping elements. |
| 4.1, 4.5, 4.6, 4.7 | Text that ran over box borders shortened. |
| 4.3 | The two screenshots are stacked, not side by side; the text says top and bottom. |

Every figure is now referred to before it appears (new sentences in 3.1, 3.2, 3.3.4, 3.4.2 and 3.6.3), Figures 3.4 and 3.6 moved next to the text that describes them, and figure and table captions use Arial Narrow 10 pt as the guideline requires. Editable copies of every diagram are in `docs/figures/editable/` (.drawio for diagrams.net, .svg for Figma, Inkscape or Illustrator).

## Updated on 27 Oct 2026 (Phase 4: final features and measurements)

The text now covers everything built in Phases 0–2, and the body stays within the length guideline. Counted with the same method before and after, Chapters 1–6 hold 9,704 words before the update and 9,705 after; new material was paid for by tightening older paragraphs.

| Where | Change |
|---|---|
| Abstract | Danger areas, camera-based location, live camera grid, site map with cameras and report evidence; 470 tests; the two-hour soak; the trained fire model (mAP@0.5 0.787). |
| 3.3.2 | Cameras place badge holders in their zone; danger areas named. |
| Table 3.4 | FR-30 to FR-34 added; FR-07 and FR-28 criteria updated. Tables 3.5, 3.9 and 3.10 follow. |
| 4.3 | PPE episodes matched to the tracked person; 4.3.5 the trained fire model; 4.3.6 rules every 15 s and the live view; 4.3.7 proximity encounters and the flood they fixed; new 4.3.8 Danger Areas. |
| 4.4 | Camera-based location and zone head counts with hysteresis. |
| 4.5, 4.6 | Cameras page, danger-area drawing, cameras on the site map, report evidence; mobile Map and Cameras tabs. Figures 4.3 and 4.4 are new screenshots from the demo site (`setup_demo`, a test video as CAM-01, the vest simulator), built by `make_figures.py` from `docs/manual/`. |
| Figure 4.2 | The ERD gains `cameras` and `camera_areas`, and `includes_evidence` on reports. |
| Chapter 5 | Table 5.1 with 470 tests (27 Oct); throughput with the fire model (Table 5.5); the two-hour soak, met (Table 5.6); FR-30 to FR-34 and updated statuses in Table IV.1; six end-to-end runs and five defects added to Tables IV.2 and IV.3. |
| Chapter 6 | Outcomes, limitations (danger-area ground plane, hand-entered camera cones) and future work updated. |
| Appendices | Table I.1/I.2 tasks for cameras, danger areas, camera placement and the mobile map; Table II.1 adds `setup_demo`; Tables III.1/III.2 add the camera endpoints and tables. The full manual is `docs/USER_MANUAL.md`. |

Rebuilt and rendered in Word on 27 Oct 2026: 95 pages; every one of the 147 contents and list entries matches the page it lands on in the final render.

## Updated on 1 Nov 2026 (the Smart Vest is built, not future work)

The owner decided to build the vest, with a gas sensor and Wi-Fi instead of LoRa. Every passage that called the vest future work or a scope-change request now describes the vest as designed and implemented, with its hardware being assembled; nothing claims a field test.

| Where | Change |
|---|---|
| Abstract, objective 8, 1.4, 1.7, 3.1, 3.2.1 | Vest with GPS, SOS and gas over Wi-Fi; firmware and server path implemented and tested; hardware being assembled |
| 3.4.2, 3.4.3, 3.10 | MQ-2 gas sensor added; power from a USB power bank; 3.4.3 renamed Vest Communication Layer, explaining why Wi-Fi replaced LoRa (LoRa stays as the upgrade for large sites); limitation now Wi-Fi range and an uncalibrated gas estimate |
| 4.2.2 | Rewritten: the parts, the firmware (SOS press and hold-to-cancel, MQ-2 warm-up, calibration and ppm estimate), the GAS alert, compiled but not yet field-tested |
| Figures 3.3, 3.4, 3.6, 3.7, 3.10, 4.5, 4.8 | Redrawn for the vest as built: no LoRa receiver, MQ-2 and power bank in the block diagram, gas in the flowchart and sequence |
| Tables 2.1, 3.3, 3.4, 3.7, 3.9, 4.2, 4.3, 5.2, 6.1, III.1, III.2, IV.2 | Vest rows updated; Tables 4.2 and 4.3 are the real parts and wiring (no longer "proposed"); two end-to-end rows added (restricted-zone camera, vest gas and SOS) |
| Table 5.1, abstract, 3.8 feasibility, 5.3, 6.1 | 503 tests (was 470), re-run 1 Nov on SQLite and PostgreSQL, with a new firmware-logic suite |
| References, abbreviations | MQ-2 datasheet added (33 entries); ADC and LPG added, unused LoRaWAN removed |

Body text stays within the limit (about 10,495 words); every rewrite replaced text rather than adding to it.

## Updated on 1 Nov 2026 (layout, Chapter 5 charts, sharper screenshots)

| Where | Change |
|---|---|
| Layout | Chapter and appendix title pages unnumbered; the four stray blank pages removed (see "Layout"). 92 pages. |
| 5.5 | Figure 5.1, per-class mAP@0.5 with each item beside its missing class, and Figure 5.2, the confusion matrix at the pipeline's 0.15 threshold; the text says what the matrix shows (15 of 19 missing boots read as boots, 20 of 31 bare hands missed). |
| 5.6 | Figure 5.3, the latency distribution of the 1,431 soak probes. |
| Table 5.2, Table IV.2 | FR-29 and FR-30 now cite the 27 Oct live webcam run (14 alerts with frame and model version). |
| Figure 4.3 | Retaken at 1600 px wide (was 800), so the dashboard text is readable in print. |
| 3.3.2, Table 3.4, Table 5.2 | Decision B1: a restricted zone's camera also raises a breach for anyone it cannot identify (FR-20). |

The charts are drawn by `docs/figures/make_charts.py` from the saved results only: `held_out_test_metrics.json`, `held_out_confusion_matrix.json` and the soak CSV. The Colab run kept no confusion matrix, so `ai-module/scripts/held_out_confusion.py` recomputed it from the same weights (`sitesafe_v5.pt@7e8e092d0603`) and test split; its reference pass reproduces mAP@0.5 0.5621, and the matrix columns match the per-class instance counts.

## Added on 26 Oct 2026 (SOP Appendix D gaps)

| Where | Change |
|---|---|
| Front matter | Blank Final Approval Certificate, Declaration, Plagiarism Certificate and Turnitin Originality Report pages after the abstract (SOP 3.9 items 3–6). Front matter numbered in roman numerals; title page unnumbered. |
| 3.2.2 Data Flow | V7's list (hidden in Google Docs content controls, items 3 and 4 run together, Cardo font) replaced with one paragraph. |
| 3.8 Requirements Specification | Interface requirements, functional requirements with priority and acceptance criteria, use case descriptions with two full-dress use cases, non-functional requirements, resources, database requirements and a feasibility assessment (Tables 3.3–3.10). |
| 3.9 System Workflow | Whole-system activity diagram (Figure 3.9) and Level-0 DFD (Figure 3.10), both drawn by `make_figures.py`, which checks the model fields they mention. |
| 3.10 Limitations | Was 3.8. |
| Appendices I–IV | User manual, installation and setup guide, API and database reference, test evidence. Each has a title page; References now starts on a new page. |

## Chapters 1–3: corrections only (semester-7 structure kept)

| Where | Change |
|---|---|
| Abstract | Rewritten (309 words, 3 paragraphs). It now reports the current system and the measured results. |
| 1.1 | The ILO claim cited [1] (YOLOv3); it now cites [16]. The Labour Force Survey claim cited [8] (a harness paper); it now cites [17]. |
| 1.3 objective 1 | "11 detection classes" corrected to ten. |
| 1.3 objective 8 | Added that the vest hardware was moved to future work through a scope-change request. |
| 1.4 | The vest is no longer described as delivered. Fire/smoke is described as governed by permits (severity lowered, never suppressed). |
| 1.6 SDG 11 | "zone-aware suppression" changed to hot-work permits. |
| 1.7 | Report organisation rewritten for the six chapters as they are now. |
| 2.5 | YOLO is now credited to Redmon et al. 2016, refined in YOLOv3 [1]; [1] is the YOLOv3 paper. |
| Table 2.1 | In the Site-Safe row, LoRa and the vest are marked as proposed. |
| 3.1 | Vest marked as proposed. |
| 3.2.1 | Tier 1: the prototype runs on a laptop GPU (the Raspberry Pi/Jetson was the proposal); per-model frame cadence corrected. |
| 3.2.1 | Tier 2: device tokens and the outbox added; the LoRa receiver marked as proposed. |
| 3.3.1 | 11 classes and harness corrected to 10 classes; ONNX and the 0.5 threshold corrected to the .pt model and 0.15; "frame screenshot" (not implemented) replaced with confidence. |
| 3.3.2 | Positions come from vest GPS in the prototype. |
| 3.5.1 | Celery replaced with the after-commit thread pool and the Node report service. |
| 3.6.1 | Redux removed (not used). |
| 3.7 | "upload floor plans" removed (zones are drawn on the map). |
| Abbreviations | Added ASGI, CI, FR, NFR and QR. Removed ONNX (no longer mentioned). |
| References | Rebuilt on 1 Nov 2026 (see "References" below): 32 IEEE entries, numbered in order of first citation, every one cited. |

## Layout

Each chapter now opens on its own title page: chapter number 18 pt bold, name 22 pt bold, with the first section starting on the next page, as the guideline requires. Headings and figures stay with the text that follows them.

Since 1 Nov 2026 each chapter and appendix is its own Word section that starts a new page and leaves its first page (the title page) without a page number; numbering runs on from the previous section. `title_page_sections()` in `build_report_v8.py` does this and removes the empty spacer paragraphs V7 used to push title pages down, which were what spilled onto extra pages: the blank pages after the Chapter 2 and 4 title pages, before Chapter 5 and after the abstract are gone.

## Chapters 4–6: rebuilt

- **Chapter 4** keeps the 4.1–4.11 numbering.
  - 4.2 now covers QR identification (implemented) and the vest (software implemented, hardware proposed).
  - 4.3.5 is now implemented fire/smoke with permits.
  - 4.6 is now the implemented mobile app.
  - 4.8–4.10 replace the "proposed" flows with the component, deployment and class views and two sequence diagrams.
  - New figures: the training pipeline, generated ERD, web and mobile screenshots, component view, deployment view, class structure, vest sequence and camera sequence.
  - Dropped figures: the old 4.1 (duplicated Figure 3.6), the old 4.2 (stated mAP 93%, RPi/Jetson FPS and an ONNX export, none of which happened), the old ERD (showed a vitals table and mac_address that don't exist), the old 4.4 (duplicated Figure 3.5), and the old 4.5–4.7 (proposed flows).
- **Chapter 5** contains:
  - the testing approach and status levels;
  - the test environment;
  - the automated suites (308 tests, re-run on 20 Oct 2026);
  - a requirement-linked table built from `REQUIREMENTS_TRACEABILITY.md`;
  - model evaluation with the split-leakage caveat;
  - the latency, recovery, FPS and soak tables from `docs/evidence/CHAPTER5_MEASUREMENTS.md`;
  - the end-to-end record;
  - the defects found by testing;
  - threats to validity.
- **Chapter 6** contains the conclusion, an objectives-versus-outcomes table, limitations and future work.

## Please check before submission

1. **Smart Vest.** Since 1 Nov 2026 the report says the vest's firmware and server path are implemented and tested and its hardware "is being assembled" (objective 8, Sections 1.4, 3.1, 3.2.1, 3.4, 4.2.2, 5.9, 6.3). That is true only while you are building it. After the bench test, replace "being assembled" with the measured results (SOS delay, GPS time to first fix, gas response); if the vest is not built before submission, the wording must change back.
2. **Labour Force Survey and Chapter 2 citations.** Fixed on 1 Nov 2026 (see "References" below).
4. **Epochs.** "Stopped after 102 of 150 epochs, best at epoch 77" comes from the team's earlier notes. The exported manifest has no per-epoch results, so keep the Colab log as evidence.
5. **Title page.** It still says LAHORE and April 2026. Update the date and confirm the campus.
6. **Screenshots** (Figures 4.3 and 4.4) were taken from the demo site with a test video as the camera and simulated vests. The mobile screens were captured from the app's web build, as the text says.
7. **Front-matter pages** are blank templates: fill in the committee names, dates, signatures and the Turnitin figures, and insert the Turnitin report. Dedication and acknowledgement (optional) are not included.
8. **Push and QR range.** These are reported as not yet done (the fire model and the two-hour soak are now reported as done). When they are measured, re-run `tools/measure/make_tables.py`, update `report_v8_content.py` and rebuild.
9. **Task division.** Table 3.9 has a placeholder for the human effort row (task division and person-months).
10. **Chapter 3 figures** were redrawn on 27 Oct (below). Check that they still show the design you proposed: the Level-1 DFD now balances Figure 3.10, and the use case diagram follows Table 3.5.
11. **Export the PDF** from Word once you have checked the .docx (`osascript docs/word_to_pdf.applescript ...`, see `build_report_v8.py`); the PDF in `docs/` predates the 1 Nov changes.

## References (1 Nov 2026)

The reference list is `REFERENCES` in `report_v8_content.py`. The text cites entries as `[@key]`, and `number_references()` in `build_report_v8.py` numbers them in order of first citation (IEEE). The build fails if a numeric citation is left from V7, a citation has no entry, or an entry is never cited. Journal and conference entries were checked against Crossref by DOI; software versions are the installed ones.

V7's list had citations that did not support their sentences, entries with wrong details, and entries that could not be found:

| Was | Now |
|---|---|
| ILO: "30 to 40 percent of fatal accidents, 7 percent of the workforce" | The ILO page says at least 108,000 deaths a year, about 30% of fatal occupational injuries, and 3 to 4 times the risk of other work; the text says that. |
| "Labour Force Survey 2020–21 … over 3.6 million", citing the 2022–23 survey | 9.5% of 67.25 million employed (about 6.4 million), citing the 2020–21 survey. |
| "Sacks et al. (2022) … 4.2 monitoring personnel", citing a Fang/Li/Ong review | No such source found; replaced by CCTV monitoring figures from Stainer et al. (2013). |
| "Nath, Behzadan, and Paal (2020) … 91.2%", citing a different 2023 review | The real 2020 paper: 72.3% mAP at 11 frames per second. The unsourced "above 92%" sentence was removed. |
| "Ramli et al. (2020) smart helmet … GSM", citing the dataset | No such paper found; replaced by Raghunath and Ghaffar (2025). Their link type is not stated, and Table 2.1 says so. |
| Pillar and Triax as "BLE worker tags" | Pillar's environmental sensors and Triax's Spot-r clip, each with its own source. |
| Fang/Li/Ong 2023, Nath/Alsharef/Nahangi 2023, Li/Luo/Gong 2023, Siddiqui et al. 2022 | Not found in Crossref or by search, so removed. |
| Awolusi et al., Fang et al. (harness): wrong volume, year or title | Corrected from Crossref and now cited. |
| YOLOv7, LeCun et al., SafetyCulture: listed but never cited | Cited where the text relies on them. |
| DRF credited to the Django Software Foundation; Mosquitto as a web page | Encode OSS; Light (2017), J. Open Source Softw. |
| No source for YOLOv1, COCO, D-Fire, OpenCV, the Apple Watch, SmartCap or Safesite | Each is cited where it is first used. |

Similarity is not something this pass can measure: run Turnitin on the final PDF (the SOP allows at most 18%).
