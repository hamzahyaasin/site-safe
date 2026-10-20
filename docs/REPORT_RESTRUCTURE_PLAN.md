# FYP report restructure plan

> **Status, 20 Oct 2026: partly superseded.** Chapters 1–4 were submitted for the semester-7 progress evaluation. They will keep their structure. The FYP-II rubric's own labels ("Ch.3 System Model/Proposed System", "Ch.4 Hardware/Software Design") match it. The work is now:
>
> - correct the stale claims in Chapters 1–4;
> - add the design diagrams of §2 inside Chapter 4;
> - expand Chapters 5–6 as planned below;
> - add the front matter and appendices, and meet the word cap.
>
> The new SRS chapter in §2 is not planned unless the supervisor asks for it.

Prepared 16 October 2026 for `docs/SiteSafe_FYP_Report_V7.docx`, against the general report guideline (chapter outline, p.3) and the FYP-II rubric (SOP Appendix C). No report text has been changed yet.

## 1. Why a restructure, not more edits

| Rubric line | Guideline expects | Report has now |
|---|---|---|
| Ch.3 System Model / Proposed System | **System Requirement Specification**: interfaces, FRs, use cases, measurable NFRs, resources, database requirements, feasibility | "System Overview": a module-by-module narrative with no FR/NFR list, use-case descriptions or feasibility |
| Ch.4 Hardware/Software Design; Algorithm/Source Code | **System Modeling & Design**: design approach, interface design, 4+1 views (class, sequence/activity, component, deployment), ERD | "Implementation": a mix of done and "proposed / not implemented" sections. ERD only; no class, sequence, component or deployment views |
| Ch.5 Testing results & discussion | Requirement-linked test cases with expected vs actual results | 59-test summary and an end-to-end table; most implemented work since then is missing |
| Abstract, Ch.1, Ch.6 | Consistent with what was delivered | Describe the October-2026 state as unimplemented: QR, mobile, fall and fire marked future work; the 0.544 metric; 11 classes |

There are 19 figures and 16 tables, and about 11,000 body words, so the 10,500 cap is already exceeded before any SRS content is added.

## 2. Target outline

Old sections marked → are moved and condensed; **new** marks content to write.

**Front matter:** Title · Abstract (≥250 words, 3–4 paragraphs, **rewritten**) · Final Approval · Declaration · Plagiarism Certificate · Turnitin report (**new blank templates**; the team fills in signatures and scores) · Acknowledgement · TOC · List of Figures · List of Tables · List of Abbreviations (**new**).

**Chapter 1 Introduction:** keep 1.1–1.6, updated. 1.3 objectives reflect delivered scope (vest per the scope-change approval). 1.7 process model (**new**, short). 1.8 report organization (**rewritten**).

**Chapter 2 Background and Existing Work:** keep. Fix mismatched citations (the ILO claim cites YOLOv3; the labour-survey claim cites a harness paper). Add 3–5 papers from the last five years so at least half the references are recent.

**Chapter 3 System Requirement Specification (new chapter):**

| Section | Source |
|---|---|
| 3.1 Introduction | new |
| 3.2 Interface requirements: hardware (cameras, phone, compute); software (REST, WebSocket, MQTT/HTTP gateway, FCM) | new, from the code's API contracts |
| 3.3 Functional requirements: FR-01…FR-29 table | `docs/REQUIREMENTS_TRACEABILITY.md` |
| 3.4 Use case model | existing Figure 3.1, redrawn if actors changed |
| 3.5 Use case descriptions: about 8 key cases (sign in, monitor live alerts, resolve alert, register worker and print badge, define zone, configure alert rule, generate report, camera raises event) | new |
| 3.6 Non-functional requirements: performance, reliability, security, usability, each with a measurable target | matrix NFR-01…07 plus the acceptance targets |
| 3.7 Resource requirements: hardware/software with justification; human effort | existing Table 4.1 → plus new text |
| 3.8 Database requirements | existing Table 4.8 → |
| 3.9 Feasibility: technical, operational, legal/ethical (worker privacy, camera footage, badges carrying no personal data) | new |

**Chapter 4 System Modeling and Design (rebuilt):**

| Section | Source |
|---|---|
| 4.1 Design approach: modular, service-oriented, bottom-up | new |
| 4.2 Architecture | existing 3.2, Figures 3.2/3.3 |
| 4.3 Logical view: class diagram of core models | **new diagram** |
| 4.4 Process view: sequence diagrams (camera event → outbox → API → socket → dashboard/mobile; report generation); activity diagram for alert lifecycle | **new diagrams**; Figure 4.7 replaced |
| 4.5 Development view: component diagram (backend apps, vision worker, report service, web, mobile) | **new diagram** |
| 4.6 Physical view: deployment diagram | **new diagram** |
| 4.7 Data design | ERD (Figure 4.3, updated: worker–vest link, badge, service token, report format) |
| 4.8 Module design and algorithms: PPE model and training (Tables 4.4–4.6, v5 figures); QR identity association; fall, proximity, inactivity; geofencing and breaches; event outbox; reporting metrics | existing Ch.4 condensed, plus new algorithm text |
| 4.9 Interface design: real screenshots of web dashboard, map editor, mobile app | **new** (replaces the mobile wireframes, Figure 3.8) |
| 4.10 Smart Vest (proposed design) | existing 4.2 and Figure 4.1, clearly labelled, assuming the scope change is approved |

**Chapter 5 Testing and Validation (expanded):** test strategy and environment. Automated suites: backend 138, AI 35, report service 12, mobile 13, simulator 8. A requirement-linked test-case table (ID, FR, steps, expected, actual, pass/fail). End-to-end scenarios already run: outage replay, socket auth, live updates, QR attribution, reports, browser and mobile-web checks, vest simulator. Model evaluation, stated as from a leaky split. NFR measurements (**pending Stage 5**). Threats to validity.

**Chapter 6 Conclusion and Future Work:** objectives vs outcome table; honest limitations; specific future work (vest hardware, fire/smoke if deferred, clean-split retraining, iOS push).

**Appendices:** A installation and setup; B user manual (web and mobile); C API summary; D dataset and evaluation details. Long tables move here to save word count.

**Word budget (body, excluding front matter and references):** Ch.1 1,200 · Ch.2 1,100 · Ch.3 2,100 · Ch.4 2,900 · Ch.5 1,700 · Ch.6 600 ≈ **9,600**. That leaves room within 8,500–10,500 if the existing Ch.3/Ch.4 narrative is cut heavily.

## 3. How to produce it

**Recommended: regenerate the report from structured source.** A new builder holds the content (Markdown-like files per chapter) and applies the guideline formatting:

- Times New Roman; A4 with 1/1/1/1.25-inch margins.
- Chapter separator pages, with chapter number in 18 pt bold and name in 22 pt bold.
- Numbered headings at 16/14/12 pt; body 12 pt, 1.5 spacing, justified.
- Captions numbered by chapter: tables above, figures below.
- Roman-numbered front matter and an auto-generated TOC and lists.

It reuses the existing figure images. It also checks that every figure and table is cited in the text before it appears, and counts body words against the cap.

The current patch script edits the original paragraph by paragraph. It is not idempotent and breaks on moved content, so it suits small corrections only.

## 4. Decisions needed before writing

1. **Template conventions.** The general guide and the SOP conflict (`FYP_READINESS_REVIEW_2026-10-13.md` §2): separator page numbers hidden or shown, and caption font Arial Narrow or Times New Roman. Default: follow the general report guideline (hidden numbers, Arial Narrow 10), since it is the document specifically about report format. Confirm with the coordinator.
2. **Smart vest wording** depends on the scope-change approval (`docs/SCOPE_CHANGE_SMART_VEST.md`).
3. **Fire/smoke detection** is still an objective and not implemented. It needs to be built, or covered by the same scope change, before the report can be truthful about it.
4. **Authorship.** Claude can draft every section from the code and evidence. The team must read, correct and own the final wording, and must check whether the department's academic-integrity policy covers AI-assisted writing. Turnitin is run on the report.
