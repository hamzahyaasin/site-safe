# Site-Safe AI Accuracy Remediation Roadmap

This plan separates model-box accuracy from alert-event accuracy. A phase is
complete only when its exit criteria are measured; passing unit tests alone is
not evidence of real-camera detection accuracy.

## Phase 1 — Correctness and data-quality guardrails

Status: in progress

- [x] Run PPE, person/vehicle, and pose models on an untouched raw frame.
- [x] Draw operator overlays only on a separate display frame.
- [x] Add a read-only dataset audit for split-source overlap, exact duplicate
  images, conflicting duplicate labels, malformed rows, backgrounds, and
  image/label pairing.
- [x] Treat intentional empty YOLO label files as valid background examples in
  the Colab training audit.
- [x] Correct polygon previews so polygons are not interpreted as box fields.
- [x] Expose the current global PPE candidate threshold through validated CLI
  configuration, without pretending it is a calibrated production value.
- [ ] Decouple frame capture from slow network alert delivery.
- [ ] Persist model/configuration hashes and source timestamps with events.

Exit criteria:

- Every model consumes the same unannotated source frame.
- Dataset auditing is reproducible locally and can fail CI in strict mode.
- Existing software tests and new audit tests pass.

## Phase 2 — Rebuild the dataset and sealed evaluation split

Status: in progress

- Recover original, pre-resize and pre-augmentation assets.
- Assign immutable source, site, camera, video/session, and timestamp metadata.
- [x] Generate a row-level manifest with exact hashes, label signatures, class
  counts, image dimensions, and compact perceptual fingerprints.
- [x] Conservatively connect source siblings, inferred video sessions, exact
  content duplicates, and pixel-verified visual duplicates.
- [x] Generate an HTML/CSV adjudication queue for all 69 contradictory
  exact-image label groups.
- [x] Generate a deterministic, group-constrained 70/15/15 split proposal that
  jointly balances images and all ten classes.
- Keep every source video/session/site in exactly one split; split before
  augmentation.
- Adjudicate all exact-duplicate label conflicts and audit all rare classes.
- Add real background and hard-negative frames.
- Add target-camera data for distance, angle, lighting, blur, compression,
  occlusion, weather, and crowding.
- Seal at least one complete target site/camera/time period for final testing.

Exit criteria:

- `python audit_dataset.py --strict` passes with zero blockers.
- No source group, exact duplicate, augmented sibling, or adjacent video
  sequence crosses a split boundary.
- The final test split has not influenced architecture, training, thresholds,
  persistence, or model selection.

Current generated proposal (`ai-module/dataset_v2_plan/`): 5,140 records in
2,240 indivisible groups, proposed as 3,598 train / 771 validation / 771 test.
It is intentionally blocked from materialization by 69 unresolved exact-image
annotation conflicts and the absence of authoritative site/camera/session/time
metadata. Filename-based session inference is a provisional safety net, not a
replacement for source metadata.

## Phase 3 — Person-centric PPE and robust temporal decisions

Status: not started

- Track people with stable IDs and associate head, torso, hand, and foot evidence
  with each person.
- Represent each PPE requirement as `present`, `absent`, or `not observable`.
- Resolve contradictory evidence per person/body region.
- Replace one-frame alerts with per-track K-of-N or elapsed-observed-time
  confirmation and hysteresis.
- Maintain cooldown and lifecycle per worker track rather than per class.
- Track proximity per person/vehicle pair and use per-camera ground-plane
  calibration where metric distance is required.
- Replace fixed-pixel inactivity/fall association with robust tracked,
  time-based evidence.

Exit criteria:

- Alerts identify one track and one policy violation.
- A single isolated box cannot create an automatic alert.
- Multiple workers with the same violation are handled independently.

## Phase 4 — Controlled training, calibration, and video validation

Status: not started

- Compare the current ten-class detector with person/body-region crops and
  person-centric multi-label alternatives.
- Test resolution, tiling/crops, class-balanced sampling, and domain-specific
  augmentation through controlled multi-seed experiments.
- Select checkpoints using a safety-weighted validation objective rather than
  aggregate mAP alone.
- Calibrate confidence thresholds per class together with temporal rules.
- Build independent labeled video suites for PPE, fall, proximity, and
  inactivity, including hard negatives.

Exit criteria and required reporting:

- Object-level precision, recall, F1, AP50/AP50-95, calibration, confusion
  matrix, and size/camera slices at the exact deployed settings.
- Event-level alert precision, episode recall, false alerts per camera-hour,
  missed incidents, detection delay, and duplicate-alert rate.
- Clustered confidence intervals by video/session/site.
- One final evaluation on the sealed test after all decisions are locked.

## Phase 5 — Production evidence, feedback, and drift control

Status: not started

- Save a redacted snapshot or short event clip, raw detections, boxes/keypoints,
  confidence values, track IDs, thresholds, source timestamp, model hash, and
  configuration version.
- Add reviewer outcomes: confirmed, false positive, uncertain, duplicate, and
  missed event.
- Feed reviewed errors into an active-learning queue.
- Monitor camera coverage, frame age/quality, effective FPS, per-model latency,
  confidence drift, queue lag, and delivery failures.

Exit criteria:

- Field precision and false-alert rates can be calculated from reviewed events.
- Missing camera/model coverage is shown as unknown or degraded, never as safe.
- Dataset, model, thresholds, code, and deployment configuration are traceable
  for every alert.
