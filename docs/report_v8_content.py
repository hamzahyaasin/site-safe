"""Text, tables and figures for report V8 (used by build_report_v8.py).

Every number here comes from the repository: test counts from running the
suites on 20 October 2026, measurements from docs/evidence/
CHAPTER5_MEASUREMENTS.md, model figures from ai-module/models/
sitesafe_v5_export/, statuses from docs/REQUIREMENTS_TRACEABILITY.md and
dataset findings from ai-module/audit_dataset.py.

Chapters 1-3 keep the structure submitted in semester 7; only stale or
wrong statements are replaced. Chapters 4-6 are rebuilt from the blocks
below, keeping the semester-7 section numbering for Chapter 4.

Block kinds: ("h2", text), ("h3", text), ("p", text),
("fig", file in docs/figures, width in inches, caption),
("table", caption, rows (first row is the header), column widths, font size).
"""

ABSTRACT = (
    "Construction sites need evidence that safety controls were followed, yet manual inspections and passive CCTV provide only intermittent oversight. Site-Safe is a camera-first safety compliance system that detects hazards from site cameras, identifies the workers involved, alerts supervisors on web and mobile clients in real time and keeps an auditable per-worker record. This report describes its design, implementation and evaluation, and separates what was measured from what remains to be verified.",
    "The implemented system combines a ten-class YOLO11-medium PPE detector, QR badge identification of workers, pose-based fall detection, image-plane vehicle proximity warnings, camera inactivity tracking and a fire and smoke stage whose severity follows hot-work permits. Camera events are buffered in a local outbox and posted with per-camera device tokens to a Django REST and WebSocket backend on PostgreSQL, which provides role-based access control, configurable alert rules, push and e-mail notification, automatic attendance and idle timelines, and DOCX and PDF reports. A React command centre with a site map and a React Native (Expo) mobile application are the clients. The Smart Vest's software path is implemented and exercised with a labelled simulator; the physical vest was moved to future work.",
    "All 275 automated tests pass. On a single Apple M4 host, events reached the dashboard with a 95th-percentile latency of 42 ms, all 100 events queued during a five-minute outage were stored exactly once about 30 s after the API returned, and the full detector set ran at 15.7 frames per second on the laptop GPU. The PPE model measured mAP@0.5 of 0.562 on the held-out split, but missing-equipment classes remain weak (no-gloves 0.062, no-boots 0.130) and the published split places near-duplicate images in both training and test data, so the score is an upper bound. Fire detection awaits a trained model, and the two-hour soak test, physical QR range tests and push delivery to a phone are outstanding.",
)

# (prefix of the V7 paragraph, replacement text). The prefix must match
# exactly one paragraph.
CHAPTER_1_TO_3_EDITS = [
    # 1.1: the ILO claim cited [1] (YOLOv3) and the Labour Force Survey claim
    # cited [8] (a harness-detection paper); [16] and [17] are the sources.
    ("According to the International Labour Organization",
     "According to the International Labour Organization, construction accounts for roughly 30 to 40 percent of all fatal occupational accidents worldwide despite employing only about 7 percent of the global workforce [16]. In Pakistan, the Labour Force Survey 2020–21 recorded over 3.6 million workers employed in the construction sector, most of whom receive little to no formal safety training and work on sites where PPE compliance is enforced, if at all, through periodic manual checks [17]. Projects funded through initiatives like CPEC have dramatically increased the volume and scale of construction activity without a corresponding investment in safety infrastructure."),
    ("Design and train a real-time PPE detection model based on YOLOv11",
     "Design and train a real-time PPE detection model based on YOLOv11 that can identify safety equipment across ten detection classes (five items of equipment, each worn and missing) and flag violations under the varied lighting and environmental conditions of an actual construction site."),
    ("Build a lightweight IoT Smart Vest with GPS tracking",
     "Build a lightweight IoT Smart Vest with GPS tracking and an SOS panic button to provide supplementary worker location data and emergency alerts in areas outside camera coverage. The vest's software path is delivered and tested with a simulator; the physical hardware was moved to future work through a scope-change request to the supervisor (Section 4.2.2)."),
    ("This project covers the full-stack design and prototype implementation",
     "This project covers the full-stack design and prototype implementation of Site-Safe. The primary focus is software: the YOLOv11-based vision pipeline with a QR code reader for worker identification, a pose-estimation module for camera-based fall detection, fire and smoke detection governed by hot-work permits, the Django REST backend, the React web dashboard, a cross-platform React Native mobile application for real-time alert management and worker monitoring, and automated compliance reports. The software path of the supplementary Smart Vest (telemetry API, MQTT consumer and a labelled simulator) is in scope; the physical vest hardware was moved to future work through a scope-change request to the supervisor (Section 4.2.2)."),
    ("The software scope explicitly includes workforce activity monitoring",
     "The software scope explicitly includes workforce activity monitoring, compliance documentation, fall detection, and fire safety features. The vision pipeline records when identified workers are on site and when they are idle, producing queryable activity timelines tied to individual worker identities via QR codes. A parallel pose-estimation model monitors body keypoints to detect falls, while a dedicated fire and smoke stage provides early fire warning whose severity is lowered, but never suppressed, during permitted hot-work activities. The mobile application gives supervisors and administrators remote access to alerts and worker status. Automated compliance reports document per-worker violation histories and attendance records."),
    ("SDG 11 (Sustainable Cities and Communities)",
     "SDG 11 (Sustainable Cities and Communities): The fire and smoke detection module, with hot-work permits that distinguish scheduled flame work from uncontrolled fires, contributes to safer urban construction environments, reducing the risk of uncontrolled fires on building sites that endanger both workers and surrounding communities."),
    ("Chapter 2 reviews existing systems",
     "Chapter 2 reviews existing systems and relevant published research, identifying the specific gap that Site-Safe fills. Chapter 3 describes the proposed system design: architecture, module specifications including QR-based identification, fall detection, fire and smoke detection, workforce monitoring, mobile application design, and data flow. Chapter 4 describes the implementation: the development environment, QR identification and the Smart Vest software path, the vision modules, the backend, web and mobile applications, workforce activity monitoring, and the component, deployment, data and interaction views of the delivered system. Chapter 5 reports testing against the requirements traceability matrix, model evaluation and measured performance and reliability. Chapter 6 compares the outcomes with the objectives and sets out limitations and future work."),
    # 2.5: [1] is YOLOv3 (2018), not the 2016 paper.
    ("The academic literature on computer vision applied to construction safety",
     "The academic literature on computer vision applied to construction safety is substantial and growing. The YOLO family of models, introduced by Redmon et al. in 2016, refined in YOLOv3 [1] and developed through successive iterations to YOLOv11 [3], has become the standard architectural choice for real-time PPE detection. The single-pass inference design achieves detection speeds and accuracy levels that are genuinely usable in operational contexts."),
    ("On the site itself, the primary edge devices",
     "On the site itself, the primary edge devices are AI cameras running YOLOv11 inference for both PPE detection and QR-based worker identification. Each worker wears a helmet with a unique printed QR code, which the same camera reads to establish identity without requiring any electronics on the person. A lightweight Smart Vest with GPS and SOS capability is proposed for supplementary tracking in areas outside camera coverage (Section 4.2.2). Everything converges at the backend server, which processes incoming data, evaluates alert rules, generates compliance records, and pushes updates to both the web dashboard and the mobile app in real time."),
    ("Tier 1 (Edge):",
     "Tier 1 (Edge): IP cameras feed an edge computer that runs a multi-model inference pipeline locally. A Raspberry Pi 5 or Jetson-class unit was proposed; the prototype runs on a laptop GPU (Section 4.1). The primary YOLOv11 model handles PPE detection on every frame; a person-and-vehicle detector and QR code reading run on every third frame, a YOLOv11-Pose model runs on every third frame for fall detection, and a fire and smoke model runs on every fifth frame. Together these models push violation alerts, fall events, fire detections and worker identification data to the backend, and the same pipeline feeds workforce activity monitoring. A lightweight ESP32-based Smart Vest is proposed to provide supplementary GPS location and SOS alerts via LoRa."),
    ("Tier 2 (Network):",
     "Tier 2 (Network): Camera alerts and QR identification data are sent over HTTP to the backend API, authenticated with per-camera device tokens and buffered in a local outbox while the server is unreachable. For the supplementary Smart Vest, a LoRa receiver is proposed to forward GPS and SOS data via MQTT; an MQTT broker (Mosquitto) handles the publish-subscribe routing, and the vest gateway can also post over HTTP."),
    ("The vision module uses a YOLOv11-M model",
     "The vision module uses a YOLOv11-M model to continuously inspect camera frames for ten detection classes covering helmets, high-visibility vests, boots, gloves and goggles, each in a worn and a missing state. Frames are captured from IP cameras over RTSP or HTTP streams, resized to 640×640 and passed through the model on the edge device. Detections below a candidate confidence threshold (0.15 in the prototype, pending per-class calibration) are discarded. OpenCV’s QRCodeDetector scans sampled frames for QR codes on worker helmets, linking a detected person to their registered identity. A worker without required PPE triggers a violation event logged with worker identity (from QR, when readable), timestamp, camera ID, zone and detection confidence, creating an auditable per-worker compliance record."),
    ("Administrators define Red Zones",
     "Administrators define Red Zones by drawing polygon boundaries directly on the site map in the dashboard, and the polygons are stored in the database. Worker positions are checked against active zone polygons with a point-in-polygon test; in the prototype the positions come from vest GPS, because a single camera gives no ground coordinates. An incursion into a restricted zone triggers an immediate alert on the dashboard and a push notification to the safety officer through the mobile app."),
    ("The Django REST Framework backend provides the API layer",
     "The Django REST Framework backend provides the API layer that edge devices write to and both the dashboard and mobile app read from. A separate MQTT consumer process handles incoming vest telemetry, and critical alerts are routed to WebSocket clients and to the FCM push notification service. Notifications are sent from a background thread pool after each alert is committed, and PDF and DOCX reports are produced by a separate Node.js report service, so neither blocks API response times."),
    ("The mobile application is built with React Native",
     "The mobile application is built with React Native, enabling a single JavaScript codebase to target both iOS and Android platforms. React Native was chosen specifically because the team already has React expertise from the web dashboard development, and the component model and API service patterns carry over between web and mobile."),
    ("The admin interface, accessible through both",
     "The admin interface, accessible through both the web dashboard and the mobile app, handles site configuration and worker management. Admins can register workers and assign QR codes to their profiles, draw geofence zones on the site map, configure alert and notification preferences, and generate or download PDF compliance reports for any date range. Access is role-gated: Admin, Safety Officer, and read-only Viewer roles are defined with corresponding permission sets enforced at the API level."),
]

# Table 2.1, last row: the long-range link and vest are proposals.
TABLE_21_SITE_SAFE_ROW = ("Site-Safe (ours)", "2026", "Yes", "QR (+ GPS vest, proposed)", "LoRa (proposed)", "Yes", "Yes", "Prototype; QR range not yet measured")

ABBREVIATIONS_ADD = [
    ("ASGI", "Asynchronous Server Gateway Interface"),
    ("CI", "Continuous Integration"),
    ("FR", "Functional Requirement"),
    ("NFR", "Non-Functional Requirement"),
    ("QR", "Quick Response (code)"),
]
ABBREVIATIONS_REMOVE = ["ONNX"]

REFERENCE_EDITS = [
    ("[4] Roboflow", '[4] testcasque, "PPE Detection (ppe-detection-qlq3d)," Roboflow Universe, dataset version 1, CC BY 4.0, exported 19 Oct. 2024. [Online]. Available: https://universe.roboflow.com/testcasque/ppe-detection-qlq3d'),
    ("[11] Meta Platforms", '[11] Meta Platforms, "React Native," version 0.88, 2026. [Online]. Available: https://reactnative.dev/'),
]
REFERENCES_ADD = [
    '[21] Expo, "Expo SDK 58," 2026. [Online]. Available: https://docs.expo.dev/',
    '[22] Django Software Foundation, "Channels," version 4.3.2, 2026. [Online]. Available: https://channels.readthedocs.io/',
    '[23] Leaflet, "Leaflet: an open-source JavaScript library for interactive maps," version 1.9.4, 2023. [Online]. Available: https://leafletjs.com/',
]

# ---------------------------------------------------------------- Chapter 4

TABLE_41 = [
    ("Tool / Platform", "Version", "Purpose"),
    ("Python", "3.14.3", "Backend, camera pipeline and measurement tools"),
    ("Django / Django REST Framework", "6.0.4 / 3.17.1", "REST API, permissions and serializers"),
    ("Django Channels / Daphne", "4.3.2 / 4.2.3", "WebSocket delivery; ASGI server for REST and WebSocket"),
    ("PostgreSQL", "18.3", "Development and measurement database; backend tests also run on SQLite"),
    ("Redis", "7 (container image)", "Channel layer between backend processes in the compose deployment"),
    ("Eclipse Mosquitto / paho-mqtt", "2 (container image) / 1.6.1", "Vest gateway messages read by the MQTT consumer"),
    ("Ultralytics / PyTorch / OpenCV", "8.4.41 / 2.11.0 / 4.13.0", "Detection, pose estimation and QR decoding"),
    ("Node.js / Express", "25.8.1 / 5.2.1", "Report service runtime"),
    ("docx / pdfkit", "9.7.1 / 0.20.2", "DOCX and PDF report rendering"),
    ("React / Vite / Tailwind CSS", "19.2.8 / 8.2.2 / 4.3.3", "Web command centre"),
    ("Leaflet / react-leaflet", "1.9.4 / 5.0.0", "Site map and zone editor (OpenStreetMap tiles)"),
    ("Expo SDK / React Native", "58.0.12 / 0.88.0", "Mobile application"),
    ("Docker Compose / GitHub Actions", "Written, not yet run", "Eight-service deployment; CI running every test suite"),
    ("Git", "2.53.0", "Version control"),
]

TABLE_42 = [
    ("Component", "Model", "Range", "Accuracy", "Interface"),
    ("GPS", "NEO-6M", "Worldwide", "2.5 m CEP", "UART"),
    ("SOS Button", "Tactile Switch", "N/A", "N/A", "GPIO"),
]

TABLE_43 = [
    ("GPIO Pin", "Connected To", "Protocol", "Notes"),
    ("GPIO 16 (RX2)", "NEO-6M TX", "UART", "9600 baud"),
    ("GPIO 17 (TX2)", "NEO-6M RX", "UART", "9600 baud"),
    ("GPIO 18", "LoRa Module SCK", "SPI", "SX1276"),
    ("GPIO 23", "LoRa Module MOSI", "SPI", "SX1276"),
    ("GPIO 19", "LoRa Module MISO", "SPI", "SX1276"),
    ("GPIO 5", "LoRa Module NSS", "SPI", "Chip select"),
    ("GPIO 2", "Status LED", "Digital", "Activity indicator"),
    ("GPIO 15", "SOS Button", "Digital", "Pull-down, interrupt"),
]

TABLE_44 = [
    ("Split", "Images", "Percentage", "Purpose"),
    ("Training", "3,597", "70%", "Model weight optimization"),
    ("Validation", "1,026", "20%", "Early stopping and model selection"),
    ("Test", "517", "10%", "Final performance evaluation"),
]

TABLE_45 = [
    ("Parameter", "Value", "Rationale"),
    ("Base model", "YOLO11-m (medium), COCO-pretrained", "Larger capacity than the earlier nano baseline"),
    ("Input resolution", "640 × 640", "Standard Ultralytics training resolution"),
    ("Batch size", "16", "Fits the T4's memory at 640 px"),
    ("Epochs", "150 budget, early stopping (patience 25)", "Recorded run stopped after 102 epochs; best at epoch 77"),
    ("Optimizer", "AdamW", "Weight decay handling"),
    ("Learning rate", "0.001, linear decay to 1% (lrf 0.01)", "Cosine schedule disabled for this run"),
    ("Augmentation", "Mosaic, flip, HSV, scale (defaults)", "Mosaic disabled for the final 10 epochs"),
    ("Seed", "42, deterministic", "Repeatable run"),
    ("Confidence threshold", "0.15", "Runtime candidate threshold; not yet calibrated per class"),
    ("NMS IoU threshold", "0.7", "Ultralytics default"),
]

TABLE_46 = [
    ("Class", "Precision", "Recall", "mAP@0.5"),
    ("helmet", "0.893", "0.959", "0.958"),
    ("no-helmet", "0.249", "0.714", "0.309"),
    ("vest", "0.853", "0.954", "0.962"),
    ("no-vest", "0.578", "0.879", "0.782"),
    ("boots", "0.845", "0.998", "0.977"),
    ("no-boots", "0.127", "0.596", "0.130"),
    ("gloves", "0.222", "0.316", "0.276"),
    ("no-gloves", "0.109", "0.323", "0.062"),
    ("goggles", "0.470", "0.793", "0.635"),
    ("no-goggles", "0.321", "0.750", "0.530"),
    ("all classes", "0.467", "0.728", "0.562"),
]

TABLE_47 = [
    ("Endpoint", "Method", "Description"),
    ("/api/token/, /api/token/refresh/", "POST", "Sign in; renew the access token"),
    ("/api/v1/profile/, /api/v1/profile/change-password/", "GET/PATCH, POST", "Signed-in user's profile and password"),
    ("/api/dashboard/stats/", "GET", "Counts and charts from stored records"),
    ("/api/alerts/", "GET/POST", "List or create alerts (date range, type, status filters)"),
    ("/api/alerts/{id}/, /api/alerts/{id}/resolve/", "GET/PATCH, POST", "Read, update or resolve one alert"),
    ("/api/alerts/simulate/", "POST", "Create a simulated alert (labelled)"),
    ("/api/v1/camera-events/", "POST", "Camera event with event_id; device token"),
    ("/api/v1/camera-activity/", "POST", "Badge sightings and idle start/end; device token"),
    ("/api/v1/camera-config/", "GET", "Alert rules for this camera; device token"),
    ("/api/alerts/ingest/", "POST", "Legacy edge ingest; device token"),
    ("/api/workers/, /api/workers/{id}/", "GET/POST, GET/PUT/PATCH/DELETE", "Worker registry and vest assignment"),
    ("/api/workers/{id}/badge/", "GET/POST", "Read or reissue a worker's QR badge"),
    ("/api/v1/vests/, /api/v1/vests/{id}/", "GET/POST, GET/PUT/PATCH/DELETE", "Smart Vest records"),
    ("/api/v1/vests/telemetry/", "POST", "GPS, battery and SOS telemetry; gateway token"),
    ("/api/v1/activity/ (+ /timeline/, /daily/, /summary/)", "GET", "Activity records, per-worker timelines and daily totals"),
    ("/api/v1/detections/", "GET/POST", "Detection records"),
    ("/api/v1/alert-config/", "GET/POST/PUT/PATCH/DELETE", "Alert rules: enabled, threshold, notify"),
    ("/api/v1/zones/ (+ /{id}/workers/, /{id}/check_point/)", "GET/POST/PUT/PATCH/DELETE", "Zones, assigned workers, point-in-zone test"),
    ("/api/v1/hot-work-permits/ (+ /{id}/revoke/)", "GET/POST/PUT/PATCH/DELETE", "Hot-work permits and revocation"),
    ("/api/v1/fcm-tokens/, /api/v1/fcm-tokens/{token}/", "POST, DELETE", "Register or remove a phone's push token"),
    ("/api/v1/reports/ (+ /generate/, /{id}/download/)", "GET, POST, GET", "List, generate (DOCX or PDF) and download reports"),
    ("/ws/dashboard/?token=<JWT>", "WebSocket", "Live alert, vest and worker events"),
]

TABLE_48 = [
    ("Table", "Key fields", "Relations / notes"),
    ("users", "id, email, full_name, role, is_active", "Roles: Admin, Safety Officer, Viewer"),
    ("service_tokens", "id, name, kind, key_hash, camera_ids, is_simulator, is_active", "Device tokens; only a hash of the key is stored"),
    ("workers", "id, name, role, zone_id, badge_code, last_seen_at, is_active", "FK zones; badge_code is unique (QR payload)"),
    ("smart_vests", "id, vest_id, worker_id, battery_level, latitude, longitude, sos_active, last_seen", "One-to-one with workers; battery unknown until reported"),
    ("zones", "id, name, risk_level, boundaries, camera_ids, max_occupancy", "Polygon boundaries and camera assignment (JSON)"),
    ("hot_work_permits", "id, zone_id, description, starts_at, ends_at, issued_by_id, revoked_at", "FK zones, users"),
    ("alerts", "id, alert_type, severity, source, worker_id, camera_id, hot_work_permit_id, confidence, event_id, is_resolved", "FK workers, permits; event_id unique for idempotent ingest"),
    ("alert_config", "id, zone_id, alert_type, is_enabled, threshold_seconds, notify_push, notify_email", "One rule per type and zone; SOS and FIRE always enabled"),
    ("activity_logs", "id, worker_id, zone_id, action, timestamp, metadata", "Check-in/out, idle and zone events at event time"),
    ("detections", "id, camera_id, worker_id, class_name, confidence, bbox", "FK workers"),
    ("reports", "id, report_type, file_format, date_from, date_to, created_by_id", "FK users; stored before download"),
    ("fcm_tokens, user_preferences", "user_id, token, device_name / notify_push, notify_email", "FK users; push targets and opt-outs"),
]

TABLE_49 = [
    ("Component", "Technology", "Purpose"),
    ("Framework", "React Native 0.88 on Expo SDK 58 [21], TypeScript", "Android and iOS from one codebase"),
    ("Navigation", "Expo Router (file-based tabs and stack)", "Alerts, Workers and Settings tabs; alert detail"),
    ("State", "React context and reducers", "Live alert and worker state"),
    ("HTTP client", "fetch wrapper with single-flight token refresh", "REST calls; sign-out when renewal fails"),
    ("Live updates", "WebSocket with 4401 renewal, back-off and resync", "Same live stream as the web dashboard"),
    ("Push notifications", "expo-notifications 58.1 (FCM on Android)", "Alert delivery; tap opens the alert"),
    ("Secure storage", "expo-secure-store 58.0", "Tokens in the device keychain/keystore"),
    ("Quality checks", "jest-expo (13 tests), ESLint, TypeScript", "Run in CI"),
]

CHAPTER_4 = [
    ("h2", "4.1 Development Environment"),
    ("p", "Site-Safe was developed and measured on one Apple M4 laptop with 16 GB of memory running macOS; the versions in Table 4.1 were read from the project environments and lock files on 20 October 2026. The PPE model was trained on a Google Colab Tesla T4 GPU, because training on the laptop ran out of memory. A docker-compose file and a GitHub Actions workflow are written but have not yet been run."),
    ("table", "Table 4.1: Development Environment Summary", TABLE_41, [1.9, 1.5, 2.6], 8.5),

    ("h2", "4.2 QR Identification and Smart Vest"),
    ("h3", "4.2.1 QR Worker Identification"),
    ("p", "Each worker has a random badge code, created at registration and reissued from the Workers page, which prints a QR badge with the payload SSW1:<code> for the helmet. On the camera, identity.py decodes QR codes with OpenCV on the frames sampled for the person detector and associates each badge with the person box that contains it, following that person between samples by box overlap. A badge inside two person boxes, or two badges inside one box, is treated as unknown rather than guessed, so people standing close together are not misattributed."),
    ("p", "Alerts from a person with a known badge are attributed to that worker; others are marked as not identified. The same badges feed attendance (Section 4.7), with at most one sighting per badge per minute, and unknown or revoked codes are ignored with HTTP 202 so that they cannot block a camera's queue. Thirteen camera-side tests, including decoding of real OpenCV-encoded images, and seven backend tests cover decoding, association and attribution. Reading range, angle and lighting have not yet been measured with printed badges, so the 5–10 metre range in Section 3.4.1 remains an assumption."),
    ("h3", "4.2.2 Smart Vest"),
    ("p", "The physical Smart Vest (ESP32 [13], GPS module, SOS button and LoRa link [14]) has not been built. It was moved to future work through a scope-change request to the supervisor: the vest is supplementary by design (Section 3.4.2), parts and lab access were not available in the time left, and the camera functions carry the primary objectives. Figure 3.6 and Tables 4.2 and 4.3 remain the proposed hardware design."),
    ("p", "The software path a vest would use is implemented. A gateway posts JSON telemetry (vest, position, battery and SOS state) to /api/v1/vests/telemetry/ with a gateway token, or publishes it to sitesafe/vest/<id>/telemetry and /sos on a Mosquitto broker [15] read by the MQTT consumer. Both paths validate the payload and share one handler (Figure 4.8). A vest simulator drives this path with scripted scenarios; its token is flagged, so its alerts are labelled SIMULATED, create no attendance and are excluded from reports."),
    ("table", "Table 4.2: Proposed Smart Vest Component Specifications", TABLE_42, [1.1, 1.3, 1.1, 1.1, 1.4], 9),
    ("table", "Table 4.3: Proposed ESP32 Pin Allocation", TABLE_43, [1.4, 1.7, 1.2, 1.7], 9),

    ("h2", "4.3 PPE Detection Module"),
    ("p", "The camera pipeline runs the PPE detector models/sitesafe_v5.pt, a YOLO11-medium model trained with Ultralytics [3], on every frame. Because the PPE model has no person or vehicle class, a COCO-pretrained YOLO11-nano detector supplies person and vehicle boxes on every third frame, and a YOLO11-nano pose model runs on every third frame for fall detection. All models read the same unannotated frame; boxes are drawn only on a display copy. Each missing-PPE box is tracked as one person's episode (ppe_episodes.py): it alerts once after persisting for one second in at least three frames, and again only after it has been unseen for ten seconds, so a flicker raises nothing and two people missing helmets raise two alerts."),
    ("h3", "4.3.1 Dataset and Classes"),
    ("p", "The training data is the Roboflow dataset ppe-detection-qlq3d (CC BY 4.0) [4]: 5,140 images in ten classes, helmet, vest, boots, gloves and goggles, each with a matching no- class, so that a violation is detected directly rather than inferred. It has no person or vehicle class, hence the second detector."),
    ("p", "The published split (Table 4.4) is not independent. The repository audit (audit_dataset.py) found 573 source groups and 30 groups of exact duplicates with members in more than one split, and 69 groups of identical images with conflicting labels. Test images therefore have near-copies in training, which inflates the scores below. A group-constrained re-split (3,598 / 771 / 771 images) has been generated but is held back until the label conflicts are resolved."),
    ("table", "Table 4.4: Dataset Split Configuration", TABLE_44, [1.3, 1.1, 1.2, 2.4], 9),
    ("h3", "4.3.2 Training Configuration"),
    ("p", "The model was fine-tuned from COCO-pretrained YOLO11-medium weights with the settings in Table 4.5, recorded in the exported run manifest, replacing an earlier nano model trained at 416 pixels (mAP@0.5 0.544). The team's Colab record shows early stopping after 102 of 150 epochs, with the best weights at epoch 77. Figure 4.1, drawn from the exported run, summarises the path from data to deployed weights."),
    ("table", "Table 4.5: YOLOv11 Training Hyperparameters", TABLE_45, [1.5, 2.2, 2.3], 8.5),
    ("fig", "fig_training_pipeline.png", 6.0, "Figure 4.1: PPE Model Training and Evaluation Pipeline"),
    ("h3", "4.3.3 Model Performance"),
    ("p", "On the held-out split the model reaches mAP@0.5 of 0.562 and mAP@0.5:0.95 of 0.345, with precision 0.467 and recall 0.728 (Table 4.6). Equipment that is worn is recognised reliably: helmet, vest and boots exceed 0.95. Missing equipment, the condition the system exists to detect, is recognised poorly: no-gloves 0.062, no-boots 0.130 and no-helmet 0.309. Absence must be inferred from where equipment would be, and the negative classes are under-represented. The larger model did not fix this, so better data for the weakest classes is the most valuable improvement, and because of the split leakage every figure is an upper bound."),
    ("table", "Table 4.6: Per-Class Detection Performance", TABLE_46, [1.8, 1.4, 1.4, 1.4], 9),
    ("h3", "4.3.4 Fall Detection"),
    ("p", "Fall detection (fall_detection.py) runs its own pose model on every third frame, since neither the PPE nor the COCO detector gives keypoints. A posture counts as collapsed only when both signals of Section 3.3.5 agree: the confident keypoints form a box wider than tall, and the hips are at or below the knees. If either signal cannot be measured, for example with a leg out of frame, the result is not-collapsed, so missing data does not raise an alarm."),
    ("p", "People are tracked between samples by a confidence-weighted keypoint centroid, and a fall is confirmed only after three continuous seconds of collapse. It raises one FALL alert and latches until the posture clears; brief missed detections are tolerated. The alert names a worker only when a QR badge is associated with the track. Twenty-four tests cover the geometry and the tracker, and on real pose output from photographs, standing pedestrians were read as not collapsed. The module has not been tested on fall footage, and its pixel geometry is uncalibrated per camera."),
    ("h3", "4.3.5 Fire and Smoke Detection with Hot-Work Permits"),
    ("p", "On the camera, fire_detection.py runs on every fifth frame and confirms fire or smoke only when it persists for two seconds with gaps of at most one second, ignoring specks below 0.05 percent of the frame; after an alert it latches until the scene has been clear for 30 seconds, so a fire raises one alert, not one per frame."),
    ("p", "Severity is set by the server (alerts/fire_policy.py) from hot-work permits, which safety officers issue for a zone and time window on the Zones page and can revoke. Without an active permit FIRE is CRITICAL and SMOKE is HIGH; within one, FIRE is MEDIUM and SMOKE LOW, and the alert is linked to the permit. Unlike the suppression proposed in Section 3.3.6, a permitted flame is still stored and broadcast, so a welding fire that spreads is not hidden, and FIRE cannot be disabled. The growth heuristic was not implemented, as no labelled footage exists to set it."),
    ("p", "The fire model itself is not yet trained: a preparation script and a Colab notebook for a two-class YOLO11-small detector exist, but the dataset and licence must be confirmed first, and the pipeline runs without the stage until the weights exist. The permit policy was verified end to end on 20 October 2026 with injected events: a fire in a permitted zone became MEDIUM and was linked, the same fire elsewhere CRITICAL."),
    ("h3", "4.3.6 Camera Sources and Reliable Event Delivery"),
    ("p", "The camera source is a device index or a stream URL, so an RTSP camera, an NVR or a phone running an IP-camera application uses the same code path as a webcam, and up to 30 consecutive failed reads are tolerated before a stream counts as disconnected. Each pipeline has a camera identifier, and zones list their cameras, so each alert is attributed to a zone."),
    ("p", "Every event is first written to a local SQLite outbox with a unique event identifier and delivered in the background, retrying with exponential back-off capped at 30 seconds, also after a restart. The server stores each identifier once, answering 201 for a new event, 200 for a duplicate and 202 when the alert type is disabled; a validation error moves the event to dead letters. Cameras use device tokens scoped to their identifier, and read their alert rules every 60 seconds, so a new inactivity timeout set on the dashboard applies without a restart."),
    ("h3", "4.3.7 Vehicle Proximity Detection"),
    ("p", "Proximity uses the COCO detector's person and vehicle boxes. Without depth, the shortest gap between a person box and a vehicle box is divided by the person's box height, making the threshold roughly scale-invariant; one person-height is about 1.7 metres when both are at a similar distance from the camera. A breach must persist for three evaluated frames, latches until it clears, and is CRITICAL when the boxes overlap and HIGH otherwise."),
    ("p", "Nine unit tests cover the geometry, scale invariance and persistence, and with the real detector a still image of people beside a bus produced a CRITICAL alert shown on the dashboard. COCO has no forklift class, so plant is reported as a truck or car, and a worker standing in front of a distant vehicle is over-reported. Live site footage has not been evaluated."),

    ("h2", "4.4 Backend Implementation"),
    ("p", "The backend is a Django 6 and Django REST Framework [10] application on PostgreSQL 18, served by Daphne so that REST and WebSocket traffic share one ASGI process through Django Channels [22]. Its five applications are accounts, alerts, workers, sitemap (zones and permits) and reports. Table 4.7 lists the endpoints, Table 4.8 the schema and Figure 4.2 the data model, drawn from the Django models."),
    ("p", "Users receive a 30-minute JWT access token and a refresh token, which the clients renew silently, and Admin, Safety Officer and Viewer permissions are enforced on every endpoint. Producers use device tokens instead: only a hash of each key is stored, each has a kind (camera or vest gateway) and permitted cameras, and none can sign in. No write endpoint is anonymous and no credentials remain in the code. The WebSocket requires a valid user token and an allowed origin and closes with code 4401 otherwise, which tells clients to renew and reconnect."),
    ("p", "Alert, resolution and vest changes are broadcast after the transaction commits, so clients never see a rolled-back alert, and a Redis channel layer carries them between processes. Alert rules set, per type and optionally per zone, whether an alert is enabled, its threshold and whether it notifies; SOS and FIRE cannot be disabled. Notifications go out after commit through Firebase Cloud Messaging [12] and e-mail, respecting user preferences. A presence monitor runs every 30 seconds, marking vests offline after 120 seconds of silence and closing attendance sessions."),
    ("table", "Table 4.7: Core API Endpoints", TABLE_47, [2.5, 1.7, 1.8], 7.8),
    ("table", "Table 4.8: Database Schema Summary", TABLE_48, [1.15, 2.85, 2.0], 7.8),
    ("fig", "fig_erd.png", 6.0, "Figure 4.2: Entity Relationship Diagram"),

    ("h2", "4.5 Frontend Dashboard Implementation"),
    ("p", "The web command centre is a React 19 application built with Vite and Tailwind CSS, with routes for the dashboard, workers, incidents, vests, zones, reports and settings. Every dashboard figure comes from stored records; the seeded charts, vitals and compliance percentage of the earlier prototype were removed. A WebSocket adds and removes alerts live, and the client resynchronises after a reconnect."),
    ("p", "The Zones page (Figure 4.3, left) shows a Leaflet [23] map on which administrators draw zone polygons, set risk level, occupancy limit and cameras, and manage hot-work permits; vest positions appear coloured by status. The Workers page registers and edits workers, assigns vests, prints badges and opens each worker's daily timeline (Figure 4.3, right). Controls appear only for roles that may use them. Reports are generated in DOCX or PDF for a period in the user's time zone and give counts, resolution times, violation-free days and attendance, each defined, but no compliance percentage, because the system records violations and not compliant observations, so no denominator exists."),
    ("fig", "fig_web_interface.jpg", 6.0, "Figure 4.3: Web Command Centre: Zone Map and Worker Timeline"),

    ("h2", "4.6 Mobile Application"),
    ("p", "The mobile application uses React Native 0.88 [11] on Expo SDK 58 in TypeScript, following Section 3.6. Expo builds Android and iOS clients without a local Xcode or Android Studio installation and supplies the FCM device token the backend supports. The app uses the same REST API and WebSocket as the web dashboard."),
    ("h3", "4.6.1 Technology Stack"),
    ("table", "Table 4.9: Mobile Application Technology Stack", TABLE_49, [1.35, 2.5, 2.15], 8.5),
    ("h3", "4.6.2 Core Screens"),
    ("p", "After sign-in with the server address and credentials, the Alerts tab lists open or all alerts and updates live; the detail screen lets Safety Officers and Admins resolve an alert, which other sessions see immediately. The Workers tab shows role, zone, vest and presence, and Settings signs out (Figure 4.4). Reports, zone editing and worker registration stay on the web by design. Of the screens in Figure 3.8 and Table 3.2, the activity summary, rule configuration and shift scheduling were not built."),
    ("fig", "fig_mobile_interface.jpg", 5.4, "Figure 4.4: Mobile Application: Alerts, Alert Detail and Workers"),
    ("h3", "4.6.3 Push Notification Flow"),
    ("p", "On Android the app registers its FCM token after sign-in and removes it on sign-out; alerts arrive on a high-importance channel and a tap opens the alert. The backend side is tested with a mocked FCM service and the registration logic with unit tests, but delivery to a real phone needs a Firebase configuration and an Android development build and has not been verified. iOS gets no remote push and relies on the live socket. Figure 4.4 was captured from the app's web build, on which sign-in, live alerts, resolution, cross-session updates and sign-out were exercised end to end."),

    ("h2", "4.7 Workforce Activity Monitoring"),
    ("p", "Inactivity tracking (inactivity.py) follows people between samples by centroid; a track that stays within a movement threshold for the timeout set in the dashboard rules raises one INACTIVITY alert and re-arms only after moving, and brief occlusions do not drop it. Displacement is in uncalibrated pixels."),
    ("p", "Identified workers get attendance automatically (workers/activity.py). The first evidence of a worker, a badge sighting or a vest report, checks them in; idle start and end come from the inactivity tracker; and after 30 minutes without evidence the presence monitor checks them out at the time they were last seen. Late events, such as those replayed from an outbox, are merged into their session. A timeline API gives per-worker daily intervals of presence and idleness, shown on the Workers page and in the report attendance tables."),
    ("p", "Twenty-three tests cover check-in, check-out, idleness and late events, and an end-to-end run on 20 October 2026 gave 60 minutes on site and 20 idle with check-out at the last sighting, identical in the timeline and the PDF. Records exist only when a worker is seen with a readable badge or wears a vest, and identities can swap when identified people cross; no annotated real-camera scenario has been compared yet."),

    ("h2", "4.8 System Architecture and Deployment"),
    ("p", "Figure 4.5 shows the implemented components. The camera pipeline and the vest gateway or simulator write through authenticated HTTP or MQTT, the API is the only writer to PostgreSQL, and clients read through REST and receive changes over the WebSocket. The three tiers of Figure 3.3 remain, but notifications use an after-commit thread pool instead of Celery, documents come from a Node.js report service, and the edge runs on a laptop GPU instead of a Raspberry Pi or Jetson."),
    ("fig", "fig_component_view.png", 6.0, "Figure 4.5: Component View of the Implemented System"),
    ("p", "Figure 4.6 shows the demonstration deployment: the camera pipeline runs natively to use the GPU, and the server is defined as eight docker-compose services. The compose file has not yet been run, so Chapter 5's results come from the same services started on the host."),
    ("fig", "fig_deployment_view.png", 6.0, "Figure 4.6: Deployment View"),
    ("p", "Figure 4.7 shows the camera pipeline's structure: main() owns the capture loop and one helper per concern, each free of camera and model imports so that it can be unit-tested without OpenCV, a GPU or weights. The script that draws Figures 4.2 and 4.7 checks every name against the code, so the figures cannot drift from the implementation."),
    ("fig", "fig_camera_classes.png", 6.0, "Figure 4.7: Camera Pipeline Class Structure"),

    ("h2", "4.9 SOS and Location Telemetry Flow"),
    ("p", "Figure 4.8 replaces the proposed flow of Figure 3.7 with the implemented sequence. After validation, the handler locks the vest row, updates its position, checks the worker in if needed, finds the highest-risk zone at the position, logs zone entry and raises ZONE_BREACH for an unassigned entry into a restricted zone or for over-occupancy. SOS raises a CRITICAL alert on its rising edge only, so a held button does not repeat it. Changes are broadcast after commit, and the presence monitor later marks a silent vest offline."),
    ("fig", "fig_seq_vest_telemetry.png", 6.0, "Figure 4.8: Vest Telemetry and SOS Sequence"),

    ("h2", "4.10 End-to-End Alert Flow"),
    ("p", "Figure 4.9 traces a camera alert. The tracker confirms the event, the camera queues and posts it, and the server applies the alert rule and, for fire and smoke, the permit policy before storing it under its event identifier. After commit, the alert is broadcast to web and mobile clients and notifications are sent. The camera deletes the event only after the server replies, so a network failure leaves it queued. Section 5.6 measures this path."),
    ("fig", "fig_seq_camera_event.png", 6.0, "Figure 4.9: Camera Event to Dashboard Sequence"),

    ("h2", "4.11 Project Timeline"),
    ("p", "The final semester followed the completion plan: securing producers and live events first, then replacing fabricated dashboard data and adding worker, zone and breach features, then QR identification, PDF reports, the mobile application and the vest simulator, and finally PostgreSQL verification, containers and CI, fire and smoke with permits, attendance automation and the Chapter 5 measurements. Each stage was recorded with its tests in the requirements traceability matrix."),
]

# ---------------------------------------------------------------- Chapter 5

TABLE_51 = [
    ("Suite", "Tests", "What it covers", "Result"),
    ("Backend (Django)", "164", "Roles and permissions (16); camera and vest ingest, device tokens and alert rules (25); fall (24), inactivity (10) and proximity (9) decision logic; WebSocket authentication and broadcasts (8); workers, vests, badges, presence and breaches (33); activity and timelines (18); zones and permits (15); reports (6)", "Pass on SQLite and PostgreSQL 18"),
    ("Camera pipeline", "65", "PPE violation episodes (15), QR identity (13), event outbox (8), fire confirmation (8), inference configuration (9), activity events (5), dataset audit and split tools (7)", "Pass"),
    ("Fire dataset preparation", "4", "Label remapping, video-grouped split, negatives", "Pass"),
    ("Report service (Node)", "13", "Metrics, DOCX and PDF rendering, attendance tables, pagination", "Pass"),
    ("Mobile app", "13", "API client and token refresh (6), push registration (2), state reducers (5)", "Pass; lint and type check clean"),
    ("Tools", "16", "Vest simulator (8), measurement statistics and tables (8)", "Pass"),
    ("Web frontend", "—", "No unit tests; ESLint and production build", "Lint clean; build OK"),
    ("Total", "275", "", "All pass (20 Oct 2026)"),
]

TABLE_52 = [
    ("ID", "Requirement", "Evidence", "Status"),
    ("FR-01", "Sign-in and silent session renewal", "Account tests; browser: corrupted token renewed, requests retried", "Integrated"),
    ("FR-02", "Roles enforced by the API", "16 permission tests", "Tested"),
    ("FR-03", "UI shows only permitted actions", "Browser check as Safety Officer and Admin; Viewer not checked in the browser", "Integrated"),
    ("FR-04", "Detect missing PPE (10 classes)", "Held-out mAP@0.5 0.562 on a leaky split; no sealed target-camera set", "Coded"),
    ("FR-05", "One alert per person per violation episode", "15 tests; pipeline run on a clip: 3 people missing helmets, 3 alerts, no repeats", "Tested"),
    ("FR-06", "Falls from camera pose", "24 tests; no fall video evaluated", "Tested"),
    ("FR-07", "Worker-vehicle proximity", "9 tests; still-image trial", "Tested"),
    ("FR-08", "Inactivity with dashboard-set timeout", "10 tests; rule polling tests", "Tested"),
    ("FR-09", "Fire/smoke with hot-work permits", "20 tests; permit downgrade end to end; model not trained", "Integrated (no model)"),
    ("FR-10", "QR worker identification", "20 tests; synthetic-frame end to end", "Integrated (synthetic)"),
    ("FR-11", "Reliable camera event delivery", "8 outbox tests; 100-event outage (Table 5.4)", "Integrated"),
    ("FR-12", "Only authorised devices submit data", "Ingest tests: anonymous, revoked, wrong-kind, wrong-camera tokens", "Tested"),
    ("FR-13", "Live updates for every change", "Realtime tests; two clients converge; browser", "Integrated"),
    ("FR-14", "Authenticated WebSocket (4401)", "Realtime tests for missing, bad and expired tokens and origin", "Tested"),
    ("FR-15", "Alert rules change runtime behaviour", "Ingest tests: disabled type, notify flags, SOS always on", "Tested"),
    ("FR-16", "Push notifications", "Mocked FCM and app registration tests; no phone yet", "Coded"),
    ("FR-17", "E-mail notifications", "Tests with a local mail backend", "Tested"),
    ("FR-18", "Worker registry in the UI", "7 tests; browser registration with vest", "Integrated"),
    ("FR-19", "Zones with polygons and cameras", "Zone tests; polygon drawn and saved in the browser", "Integrated"),
    ("FR-20", "Automatic breach and over-occupancy alerts", "9 tests; telemetry into a restricted zone end to end", "Integrated (simulated GPS)"),
    ("FR-21", "Smart Vest GPS, SOS and link", "Simulator scenario end to end; hardware not built", "Software integrated; hardware deferred"),
    ("FR-22, 23", "Telemetry validation; vest offline", "Validation and presence tests; browser occupancy timeout", "Tested; Integrated"),
    ("FR-24", "Activity history: check-in/out, idle", "23 tests; timeline and PDF agree end to end", "Integrated"),
    ("FR-25", "Incident list, resolve, export", "Resolve broadcast covered by FR-13", "Coded"),
    ("FR-26", "Dashboard shows recorded data only", "3 tests; browser reconciliation", "Integrated"),
    ("FR-27", "DOCX and PDF reports", "19 tests; both types and formats end to end", "Integrated"),
    ("FR-28", "Mobile app", "13 tests; web build end to end", "Integrated on web; no device"),
    ("FR-29", "Alert evidence (snapshot, model version)", "Confidence stored; no snapshot", "Coded (partial)"),
]

TABLE_53 = [
    ("Measure", "n", "p50 (ms)", "p95 (ms)", "p99 (ms)", "Max (ms)"),
    ("API response", "100", "34.2", "44.0", "82.2", "82.3"),
    ("Event to dashboard", "100", "32.0", "41.6", "80.0", "81.1"),
]

TABLE_54 = [
    ("Run (UTC, 20 Oct)", "Retry ceiling (s)", "Queued at restore", "Recovery (s)", "Stored once", "Lost", "Duplicated", "Result"),
    ("11:51", "60", "100", "60.3", "100", "0", "0", "Fail"),
    ("12:01", "30", "100", "30.0", "100", "0", "0", "Pass"),
    ("12:13", "30", "100", "30.2", "100", "0", "0", "Pass"),
]

TABLE_55 = [
    ("Device", "Run (UTC, 20 Oct)", "Frames", "FPS", "Frame p50 (ms)", "Frame p95 (ms)", "Result (≥ 10 FPS)"),
    ("CPU", "11:52", "150", "9.8", "80.4", "145.5", "Fail"),
    ("CPU", "12:15", "150", "10.1", "82.1", "147.2", "Pass (marginal)"),
    ("GPU (mps)", "11:51", "300", "13.4", "52.1", "116.5", "Pass"),
    ("GPU (mps)", "12:14", "300", "15.7", "46.4", "106.1", "Pass"),
]

TABLE_56 = [
    ("Duration", "Probes", "Missed", "p50 (ms)", "p95 (ms)", "Socket drops", "Forced reconnect (s)", "API memory (MB)"),
    ("5 min (validation)", "146", "0", "35.9", "41.1", "0", "1.2", "63.6 → 91.6 (max 109.8)"),
]

TABLE_57 = [
    ("Date", "Scenario", "Observed result", "Boundary"),
    ("16 Oct", "Token renewal in the browser", "Corrupted access token renewed; requests retried with 200", "Single host"),
    ("16 Oct", "Two dashboard clients", "Both received create, create and resolve in order", "Single host"),
    ("16 Oct", "Outbox replay after outage", "3 events queued: 2 stored, 1 dead-lettered (wrong camera)", "Small fixture; see Table 5.4"),
    ("16 Oct", "Restricted-zone breach", "Telemetry into a restricted zone raised a live ZONE_BREACH", "GPS simulated over HTTP"),
    ("16 Oct", "QR attribution", "Badge decoded; alert attributed to its holder; second person not identified", "Synthetic frame; no physical camera"),
    ("16 Oct", "Reports", "Both report types in DOCX and PDF through the API; PDF inspected", "Test data"),
    ("16 Oct", "Mobile app (web build)", "Sign-in, live alert, detail, resolve, cross-session resolve, workers, sign-out", "No phone; no push"),
    ("16 Oct", "Vest simulator scenario", "Simulated breach and SOS shown; vest offline after silence", "Simulator, labelled"),
    ("20 Oct", "Hot-work permit", "Fire in permitted zone MEDIUM and linked; elsewhere CRITICAL", "Injected events; no fire model"),
    ("20 Oct", "Attendance", "60 min on site, 20 min idle, check-out at last sighting; timeline equals PDF", "Synthetic camera events"),
    ("Earlier", "Proximity, real detector", "Still image: 4 people, 1 vehicle, CRITICAL alert stored and shown", "Still image only"),
]

TABLE_58 = [
    ("Defect", "Found by", "Fix"),
    ("Every vest telemetry message failed on PostgreSQL (row lock across a nullable join)", "Running the backend tests on PostgreSQL", "Lock only the vest row"),
    ("Outage recovery took 60.3 s, over the 60 s target", "Outage measurement (Table 5.4)", "Retry ceiling lowered from 60 s to 30 s"),
    ("Full pipeline ran at 9.8 FPS because Ultralytics defaulted to the CPU", "Throughput measurement (Table 5.5)", "Automatic device selection uses the GPU"),
    ("A late camera event created a second check-in", "Activity tests", "Late events merged into their session"),
    ("A migration left 100% battery on vests that never reported", "Migration check on PostgreSQL", "Battery shown as unknown until reported"),
    ("Browsers saw close code 1006, not 4401, for a bad token", "WebSocket tests in the browser", "Accept, then close with 4401"),
    ("Report tests were silently not run", "Review of test counts", "Missing package file added"),
    ("Camera-to-zone lookup used a PostgreSQL-only JSON operator", "Tests on SQLite", "Portable lookup"),
    ("Fire images whose labels were all invalid became false negatives", "Dataset preparation tests", "Such images skipped and reported"),
]

CHAPTER_5 = [
    ("h2", "5.1 Testing Approach"),
    ("p", "Testing was organised around the requirements traceability matrix kept in the repository, which links each functional (FR) and non-functional (NFR) requirement to its code, tests and evidence. A requirement's status rises through five levels, each including the previous one: Coded (the code exists), Tested (automated tests cover the behaviour), Integrated (verified end to end across real running services), Physical (verified with real hardware or a real camera scene) and Accepted (agreed with the supervisor). No requirement has reached Physical or Accepted yet, and the acceptance targets in this chapter are the team's proposals, not targets set by the university."),
    ("p", "Four kinds of evidence are used. Automated unit and integration tests run on every change. End-to-end exercises start the real services and drive them with real payloads: camera events, vest telemetry, browser sessions and app sessions. Measurement scripts in tools/measure/ produce the performance and reliability tables; each saves its raw results together with the machine, the git commit and its settings, and a table generator turns them into the tables below, so no number is copied by hand. Model evaluation uses Ultralytics on the held-out test split."),
    ("h2", "5.2 Test Environment"),
    ("p", "All tests and measurements ran on the development machine: an Apple M4 laptop with 16 GB of memory running macOS (Darwin 27.0), with Python 3.14.3, Node.js 25.8.1 and PostgreSQL 18.3. The backend suite runs against both an isolated SQLite database and PostgreSQL 18, because several defects appeared only on PostgreSQL (Table 5.8). Measurements used a separate PostgreSQL database and simulator device tokens, so their alerts are labelled SIMULATED and never reach report figures. Everything ran on a single host; no measurement yet crosses a real network to a second device."),
    ("h2", "5.3 Automated Test Results"),
    ("p", "Table 5.1 lists the automated suites. All 275 tests passed when they were re-run for this report on 20 October 2026, up from 59 in the previous revision. Decision logic on the camera side (PPE episodes, fall, inactivity, proximity and fire confirmation) is kept free of OpenCV and model imports, which lets it run under the backend test command without a camera, a GPU or weights. The web frontend has no unit tests; its lint check and production build are run instead, and its behaviour was checked in the browser (Table 5.7)."),
    ("table", "Table 5.1: Automated Test Suites", TABLE_51, [1.35, 0.55, 3.0, 1.1], 8),
    ("h2", "5.4 Requirement-Linked Test Cases"),
    ("p", "Table 5.2 condenses the traceability matrix: each requirement, the evidence gathered for it and the status reached. Statuses are not rounded up. FR-04 (PPE detection) remains Coded although the model runs, because its acceptance criterion asks for event-level precision of at least 90 percent and episode recall of at least 85 percent on a sealed set from the target camera, which does not exist yet. FR-05, one alert per person per violation episode, is Tested: fifteen tests cover its criterion (two people give two alerts, a one-frame flicker gives none, a continuous violation alerts once), and the full pipeline run headless on a clip with three people missing helmets raised three alerts and no repeats. It is not Integrated, because no recorded video with annotated episodes has been scored."),
    ("table", "Table 5.2: Requirements, Evidence and Status", TABLE_52, [0.6, 1.75, 2.45, 1.2], 7.5),
    ("h2", "5.5 Model Evaluation Results"),
    ("p", "Table 4.6 gives the held-out results of the deployed YOLO11-medium weights: mAP@0.5 of 0.562, mAP@0.5:0.95 of 0.345, precision 0.467 and recall 0.728. Present-equipment classes exceed 0.95 mAP@0.5, while no-gloves (0.062), no-boots (0.130), gloves (0.276) and no-helmet (0.309) are weak. Because a missing item is the alert condition, the aggregate overstates usefulness for the core task unless the negative classes are read separately."),
    ("p", "These figures are an upper bound for two reasons. First, the published split is not independent (Section 4.3.1): 573 source groups and 30 exact-duplicate groups span the training and test splits, so part of the test score measures recall of near-copies. Second, image-level mAP is not alert quality. An alert also depends on the candidate threshold, the grouping of detections per person, persistence and cooldown, none of which has been evaluated on video. A defensible accuracy claim needs the group-constrained re-split and, above all, a sealed set of footage from the target camera, including hard negatives, scored per event."),
    ("h2", "5.6 Performance and Reliability Measurements"),
    ("p", "Tables 5.3 to 5.6 report the non-functional measurements. Each table states its sample size and settings, and every run is kept, including failures, so a result can be traced to the commit and machine that produced it."),
    ("p", "Latency (NFR-01): 100 camera events were posted every 0.2 seconds with a simulator token, and the time from sending each event to its arrival on an authenticated dashboard socket was recorded. All 100 arrived, with a 95th percentile of 41.6 ms against a proposed target of 2 seconds (Table 5.3). The dashboard can receive an event slightly before the camera receives its HTTP response, because the server broadcasts when the alert commits. The figure is for a single host; latency to a phone or a second computer on a LAN has not been measured."),
    ("table", "Table 5.3: Event-to-Dashboard Latency (NFR-01)", TABLE_53, [1.6, 0.6, 0.95, 0.95, 0.95, 0.95], 8.5),
    ("p", "Outage recovery (NFR-02): 100 events were sent while the API was unreachable for five minutes, simulated by switching off a proxy, and the camera's sender process was restarted midway. The target is that every event is stored exactly once within 60 seconds of the API returning. The first run stored all 100 exactly once but took 60.3 seconds, a failure caused by the 60-second retry ceiling; the ceiling was lowered to 30 seconds and two further runs recovered in 30.0 and 30.2 seconds with nothing lost or duplicated (Table 5.4)."),
    ("table", "Table 5.4: Outage Recovery, 100 Events over a 5-Minute Outage (NFR-02)", TABLE_54, [0.95, 0.75, 0.75, 0.75, 0.65, 0.5, 0.75, 0.9], 8),
    ("p", "Throughput (NFR-04): the full detector set (PPE every frame; person/vehicle, pose and QR every third frame) was timed on the 517 test images at 1280×720, measuring detection and decoding without capture or display, so camera frame rates are at most these figures. On the laptop GPU the pipeline reached 13.4 and 15.7 FPS against a target of 10; on the CPU it was 9.8 and 10.1 FPS, which led to the GPU becoming the default (Table 5.5). On the GPU the PPE model takes a median of 44.8 ms per frame, and the person/vehicle, pose and QR stages 15–17 ms each on the frames they run. The fire stage is not included because its model is not yet trained, so the figure must be re-measured when it is."),
    ("table", "Table 5.5: Inference Throughput with All Available Detectors (NFR-04)", TABLE_55, [0.85, 0.95, 0.65, 0.55, 0.95, 0.95, 1.1], 8),
    ("p", "Soak (NFR-05): the target is a two-hour run of the full stack with a forced disconnect. Only a five-minute validation run of the script has been made so far (Table 5.6): 146 probes with none missed, no unexpected socket drops and a 1.2-second reconnect after the forced disconnect. API memory rose from 64 to 92 MB in those five minutes, which may be warm-up but cannot be distinguished from a leak without the full run, so NFR-05 is not yet met."),
    ("table", "Table 5.6: Soak Validation Run (NFR-05)", TABLE_56, [1.0, 0.6, 0.6, 0.6, 0.6, 0.7, 0.85, 1.05], 8),
    ("h2", "5.7 End-to-End Verification"),
    ("p", "Table 5.7 records the end-to-end exercises, each against real running services. They show that the parts exchange real payloads correctly, but each has a stated boundary: none used a physical camera scene, a phone receiving push or an assembled vest."),
    ("table", "Table 5.7: End-to-End Verification Record", TABLE_57, [0.6, 1.4, 2.5, 1.5], 7.8),
    ("h2", "5.8 Defects Found by Testing"),
    ("p", "Testing and measurement found the defects in Table 5.8 before they reached a demonstration. Three of them appeared only when the backend ran on PostgreSQL instead of the SQLite test database, which is why both now run, and two came from the measurements, which is why each measurement keeps its failed runs."),
    ("table", "Table 5.8: Defects Found by Testing", TABLE_58, [2.6, 1.6, 1.8], 8),
    ("h2", "5.9 Discussion and Threats to Validity"),
    ("p", "The software results are strong within their scope. Producers can no longer write anonymously, events survive outages and restarts exactly once, live updates reach clients in tens of milliseconds, and the attendance and report figures reconcile with the stored records. The detection results are weaker. The PPE model is good at confirming that equipment is worn and poor at noticing that it is missing, and the held-out score is inflated by the dataset split, so the system's core detection claim is the least proven part of the project."),
    ("p", "Several threats limit how far the results generalise. All measurements ran on one machine, so network effects between camera, server and clients are absent. Camera behaviour was exercised with still images, synthetic frames and injected events rather than footage of a real site, and QR range, fall detection on real falls and fire detection have not been measured at all. The vest path was driven by a simulator. Push delivery to a phone, the two-hour soak and the containerised deployment are untested. The acceptance targets were set by the team. The evidence therefore supports an integrated prototype whose software reliability has been measured and whose detection accuracy still has to be established in the field; it does not support a production-readiness claim."),
]

# ---------------------------------------------------------------- Chapter 6

TABLE_61 = [
    ("Objective (Section 1.3)", "Delivered", "Evidence reached", "Outstanding"),
    ("1. PPE detection model", "YOLO11m, 10 classes, every frame; one alert per person per episode", "Offline evaluation, upper bound (mAP@0.5 0.562)", "Sealed target-camera set; data for negative classes"),
    ("2. QR worker identification", "Badges, decoding, attribution, sightings", "Integrated on synthetic frames", "Physical range, angle and lighting test"),
    ("3. Geofencing", "Map polygons; automatic breach and over-occupancy", "Integrated with simulated GPS", "Real GPS; camera-derived positions"),
    ("4. Web command centre", "Live dashboard, map, permits, reports", "Integrated in the browser", "Viewer role browser check"),
    ("5. Mobile application", "Alerts, resolve, workers, push registration", "Integrated on the web build", "Android build and push delivery; rule configuration"),
    ("6. Workforce activity", "Inactivity, automatic check-in/out, idle, timelines", "Integrated with synthetic events", "Annotated real-camera scenario"),
    ("7. Incident logging and reports", "DOCX and PDF with defined metrics and attendance", "Integrated", "Supervisor sign-off on the metrics"),
    ("8. Smart Vest", "Telemetry API, MQTT consumer, simulator", "Software integrated; hardware moved to future work", "Build and field-test the vest"),
    ("9. Fall detection", "Pose geometry with 3 s persistence", "Tested", "Evaluation on fall video"),
    ("10. Fire and smoke detection", "Confirmation logic and permit policy", "Integrated without a trained model", "Train the model; evaluate on video"),
]

CHAPTER_6 = [
    ("h2", "6.1 Conclusion"),
    ("p", "This project set out to replace intermittent manual safety oversight on construction sites with a continuous, camera-first system that identifies the workers involved and keeps an auditable record. The delivered prototype does this end to end in software. Cameras run PPE, person and vehicle, pose and QR models and post events with their own device tokens through an outbox that survives outages. A Django backend applies alert rules and hot-work permits, keeps per-worker attendance and idle time, notifies supervisors and produces DOCX and PDF reports. A React command centre and a React Native mobile application show the results live."),
    ("p", "The measurements support the reliability of that software on a single host: a 95th-percentile event-to-dashboard latency of 42 ms, exactly-once delivery of 100 events across a five-minute outage with recovery in about 30 seconds, 15.7 frames per second for the full detector set on the laptop GPU, and 275 passing automated tests. They do not yet support a claim about detection accuracy on a real site. The PPE model recognises missing equipment poorly, its test score is inflated by a leaking dataset split, and fall, fire and QR detection have not been evaluated on real footage. Table 6.1 compares each objective with what was delivered."),
    ("h2", "6.2 Objectives and Outcomes"),
    ("p", "All ten objectives have working software. Eight are integrated or tested end to end, one (the PPE model) is evaluated offline only, and the physical Smart Vest of objective 8 was moved to future work. The remaining gaps are evaluation with real cameras and devices rather than missing features."),
    ("table", "Table 6.1: Objectives and Outcomes", TABLE_61, [1.35, 1.65, 1.5, 1.5], 7.8),
    ("h2", "6.3 Limitations"),
    ("p", "The main limitations follow from the evidence. Detection quality is bounded by a public dataset that does not represent the target cameras, and its split leaks. Proximity and inactivity are measured in pixels on uncalibrated cameras. Worker identity depends on a readable badge and can swap when identified people cross. Notifications are sent from an in-process thread pool, so a crash between storing an alert and sending its notification loses that notification, although the alert itself is kept. The system serves a single site, the site map needs internet access for its tiles, and iOS receives no remote push. All measurements come from one machine."),
    ("h2", "6.4 Future Work"),
    ("p", "The first priority is the data behind detection. The 69 conflicting label groups should be resolved so the group-constrained split can be used, footage should be collected from the target cameras with hard negatives and the weakest classes, per-class thresholds calibrated, and alerts scored per event and episode on a sealed set, which would also measure the episode tracking of FR-05 on video. The fire and smoke model should be trained on a licence-checked dataset and evaluated on recorded clips, including welding and other hard negatives."),
    ("p", "The second priority is physical verification: a QR range and lighting test with printed badges, an Android development build receiving push notifications, the two-hour soak test, latency to a second device over a LAN, a staged fall recording, and a run of the docker-compose deployment and the CI workflow. The measurement scripts already exist, so each of these is a matter of running them on the demonstration setup."),
    ("p", "Beyond the FYP, the Smart Vest can be built against the existing gateway interface: an ESP32 with GPS and an SOS button, a point-to-point LoRa link to a USB receiver that bridges to MQTT, and field tests of range, delivery delay and battery life. Other extensions are a durable queue for notifications, alert snapshots and model versions as evidence (FR-29), alert-rule configuration in the mobile app, and support for more than one site."),
]
