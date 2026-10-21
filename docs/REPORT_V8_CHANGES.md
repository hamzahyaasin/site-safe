# Report V8: what changed and what the team must check

`docs/SiteSafe_FYP_Report_V8.docx` is built from the submitted V7 (left unchanged) by `docs/build_report_v8.py`. The text lives in `docs/report_v8_content.py` and the figures come from `docs/figures/make_figures.py`. Edit those files and rebuild; don't hand-edit the .docx, or the next build will overwrite the edits. The build, render and page-number commands are in the docstring of `build_report_v8.py`.

The rendered PDF (`docs/SiteSafe_FYP_Report_V8.pdf`, 73 pages) is exported from Microsoft Word, and the contents and list page numbers were measured from that Word render (all 120 entries match).

Fixed on 21 Oct 2026: the shared table helper in `update_fyp_report.py` wrote widths in EMUs where Word expects twips, so 18 tables claimed to be about 3,800 inches wide. Word laid them out off the page, which made Table 4.1 look broken and pushed later chapters out of view. LibreOffice had silently clamped the widths, so this didn't show in the earlier checks. V7 already had five such tables from the same helper.

## Length

Body text, excluding front matter, chapter title pages and references: **10,093 words** (the guideline allows 8,500–10,500). Tables add 2,426 words. If the examiners count table text, move Tables 4.7, 4.8 and 5.2 to an appendix.

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
| References | [4] now names the dataset actually used (ppe-detection-qlq3d). [11] updated to React Native 0.88. Added [21] Expo, [22] Channels and [23] Leaflet. |

## Layout

Each chapter now opens on its own title page: chapter number 18 pt bold, name 22 pt bold, with the first section starting on the next page, as the guideline requires. Headings and figures stay with the text that follows them. The guideline also says title pages carry no page number; that is not done yet.

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

1. **Smart Vest approval.** The report says the hardware "was moved to future work through a scope-change request to the supervisor". Once `docs/SCOPE_CHANGE_SMART_VEST.md` is signed, change this to "approved by the supervisor" (in objective 8, Section 1.4 and Section 4.2.2).
2. **Labour Force Survey.** The text says "2020–21 … over 3.6 million workers", but reference [17] is the 2022–23 survey. Check the figure against the survey you cite, and fix the year or the number.
3. **Unverified Chapter 2 citations** (not changed, because the correct sources could not be confirmed here):
   - "Sacks et al. (2022) … 4.2 full-time monitoring personnel [6]": [6] is a Fang/Li/Ong review.
   - "Nath, Behzadan, and Paal (2020) … 91.2% … YOLOv3 [5]": [5] lists different authors (Nath, Alsharef, Nahangi, 2023). The 2020 paper is in Automation in Construction, vol. 112.
   - "Ramli et al. (2020) … smart helmet [4]": [4] is the dataset.

   References [2], [7], [9], [13], [14], [18], [19] and [20] were already uncited or are cited only in tables; check that each exists as written.
4. **Epochs.** "Stopped after 102 of 150 epochs, best at epoch 77" comes from the team's earlier notes. The exported manifest has no per-epoch results, so keep the Colab log as evidence.
5. **Title page.** It still says LAHORE and April 2026. Update the date and confirm the campus.
6. **Screenshots** (Figures 4.3 and 4.4) were taken from test data. The mobile screens were captured from the app's web build, as the text says.
7. **Missing front-matter pages** required by the guideline (approval certificate, declaration, Turnitin report, acknowledgement) are not in V7 or V8 and must be added from the department templates.
8. **Fire model, soak, push and QR range.** These are reported as not yet done. When they are measured, re-run `tools/measure/make_tables.py`, update `report_v8_content.py` and rebuild.
