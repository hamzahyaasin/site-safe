# Copy this instruction into Claude

You are implementing Site-Safe in `/Users/hamza/code/site-safe`. Complete the existing project according to `docs/CLAUDE_PHASED_IMPLEMENTATION_PLAN.md`, using `docs/FYP_READINESS_REVIEW_2026-10-13.md`, `docs/AI_ACCURACY_ROADMAP.md` and `docs/HARDWARE_AND_PURCHASE_PLAN.md` as supporting evidence. Read applicable repository instructions first.

The user has no dedicated project hardware, wants an economical build, has no fixed demo deadline, and wants completion as soon as feasible. Reuse the current stack and development computer; start with one camera and one GPS/SOS LoRa vest. Retain the full original scope unless the user/supervisor explicitly approves a reduction. Do not treat proposed or simulated features as completed physical implementations.

Start with phase 00: inspect/preserve all existing edits, reproduce the baseline, establish runtime/setup instructions and create the requirement/evidence matrix. Then implement the next unblocked phase in dependency order. Work in focused batches with meaningful tests, migration notes and evidence. Do not perform a whole-project rewrite or remove difficult requirements merely to claim completion.

Known baseline: 59 backend tests and 10 AI utility tests passed in the October audit; frontend build/lint could not run because dependencies were missing. The dataset audit failed with 573 cross-split source groups, 30 cross-split exact-duplicate groups and 69 conflicting annotation groups. Reproduce these facts before relying on them. Newer model artifacts exist; older README/handoff/report statements that medium-model training never ran are stale. Fall detection already exists and needs reliable integration and real-video validation, not another duplicate implementation.

Prioritize real data, secure ingestion/socket access, durable delivery, effective rules, correct reports and repaired datasets. Respect shared contracts, separate camera/GPS coordinate systems, keep unknown worker identity honest, and make event processing idempotent. Do not tune against the final evaluation set.

You can write firmware, training tools and app builds, but the team must obtain hardware, provide authorized data, adjudicate labels, physically assemble/test devices, and obtain academic approvals/signatures. Request these inputs when needed and continue independent work. Do not invent physical measurements, credentials, signatures or evaluation results. Do not purchase services, publish externally or send third-party notifications without authorization.

After each batch update the plan's progress ledger with task/requirement IDs, changed files, commands/tests actually run, evidence paths, unresolved issues and next task. Keep coded, tested, physically verified and accepted statuses distinct. When a phase's gate fails, fix it or record the precise blocker; do not mark it done.

Your first response should briefly state the baseline you found and then begin phase 00. Routine implementation choices do not need repeated confirmation. Ask only for an essential missing input, genuine scope decision, or action requiring human authorization.
