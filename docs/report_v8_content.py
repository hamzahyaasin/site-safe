"""Text, tables and figures for report V8 (used by build_report_v8.py).

Every number here comes from the repository: test counts from running the
suites on 27 October 2026, measurements from docs/evidence/
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
    "The implemented system combines a ten-class YOLO11-medium PPE detector that raises one alert per person per violation, QR badge identification that also places workers in a camera's zone, pose-based fall detection, per-person vehicle proximity warnings, danger areas drawn on the live camera picture, inactivity tracking and a trained fire and smoke detector whose severity follows hot-work permits. Camera events, with their evidence frame and model version, are buffered in a local outbox and posted with per-camera device tokens to a Django REST and WebSocket backend on PostgreSQL, which provides role-based access control, configurable alert rules, push and e-mail notification, zone head counts, automatic attendance and idle timelines, and DOCX and PDF reports that carry the evidence. A React command centre with a live camera grid and a site map showing every camera, and a React Native (Expo) mobile application with the same map and live pictures, are the clients. The Smart Vest (an ESP32 with an SOS button) and a fixed zone gas monitor (an ESP32 with an MQ-2 sensor) were bench-tested over Wi-Fi; the vest's GPS module is not yet fitted.",
    "All 525 automated tests pass. On a single Apple M4 host, events reached the dashboard with a 95th-percentile latency of 42 ms, all 100 events queued during a five-minute outage were stored exactly once about 30 s after the API returned, a two-hour soak missed none of 1,431 probes, and the full detector set, including fire, ran at 16 frames per second on the laptop GPU. The PPE model measured mAP@0.5 of 0.562 on the held-out split, but missing-equipment classes remain weak (no-gloves 0.062, no-boots 0.130) and the published split places near-duplicate images in both training and test data, so the score is an upper bound; the fire and smoke model reached 0.787. The camera features were verified end to end with test videos; QR range tests, push delivery to a phone and footage from a real site are outstanding.",
)

# (prefix of the V7 paragraph, replacement text). The prefix must match
# exactly one paragraph.
CHAPTER_1_TO_3_EDITS = [
    # Citations are written [@key] and numbered by the builder from
    # REFERENCES (end of this section). Every factual claim from outside the
    # project cites the source that states it; V7's unverifiable claims
    # (a "7 percent" ILO share, 3.6 million workers, Sacks et al., Ramli et
    # al., a 91.2% result) are replaced with what the sources say.
    ("According to the International Labour Organization",
     "According to the International Labour Organization, at least 108,000 construction workers are killed on site every year, about 30 percent of all fatal occupational injuries, and in industrialised countries construction workers are three to four times more likely than other workers to die from accidents at work [@ilo]. In Pakistan, the Labour Force Survey 2020–21 found 9.5 percent of the 67.25 million employed, about 6.4 million people, working in construction [@lfs]. On many of these sites PPE compliance is enforced, if at all, through periodic manual checks, and initiatives like CPEC have added large projects to this workload."),
    ("The technological tools to do better than this now exist",
     "The technological tools to do better than this now exist. Deep learning models can process camera feeds and detect safety violations in real time [@lecun]. Simple printed QR codes can identify individual workers without requiring any electronics on the person. Cross-platform mobile frameworks allow supervisors to receive alerts and monitor workers from anywhere on the site through their phones. When combined, these technologies can create something that has never existed on most Pakistani construction sites: an automated, per-worker compliance record that documents who was wearing what, where, and when. What has been missing is a system that brings all of these capabilities together into a coherent, practical package designed for actual deployment. That is what Site-Safe is intended to be."),
    ("Design and train a real-time PPE detection model based on YOLOv11",
     "Design and train a real-time PPE detection model based on YOLOv11 that can identify safety equipment across ten detection classes (five items of equipment, each worn and missing) and flag violations under the varied lighting and environmental conditions of an actual construction site."),
    ("Build a lightweight IoT Smart Vest with GPS tracking",
     "Build a lightweight IoT Smart Vest with GPS tracking and an SOS panic button to provide supplementary worker location data and emergency alerts in areas outside camera coverage. The vest reports over Wi-Fi, and fixed gas monitors watch each zone; both are built and bench-tested, without the GPS module (Section 4.2.2)."),
    ("This project covers the full-stack design and prototype implementation",
     "This project covers the full-stack design and prototype implementation of Site-Safe. The primary focus is software: the YOLOv11-based vision pipeline with a QR code reader for worker identification, a pose-estimation module for camera-based fall detection, fire and smoke detection governed by hot-work permits, the Django REST backend, the React web dashboard, a cross-platform React Native mobile application for real-time alert management and worker monitoring, and automated compliance reports. The supplementary Smart Vest (an ESP32 with GPS and an SOS button) and fixed zone gas monitors are in scope, over Wi-Fi, with their firmware, telemetry APIs and a labelled simulator (Section 4.2.2)."),
    ("The software scope explicitly includes workforce activity monitoring",
     "The software scope explicitly includes workforce activity monitoring, compliance documentation, fall detection, and fire safety features. The vision pipeline records when identified workers are on site and when they are idle, producing queryable activity timelines tied to individual worker identities via QR codes. A parallel pose-estimation model monitors body keypoints to detect falls, while a dedicated fire and smoke stage provides early fire warning whose severity is lowered, but never suppressed, during permitted hot-work activities. The mobile application gives supervisors and administrators remote access to alerts and worker status. Automated compliance reports document per-worker violation histories and attendance records."),
    ("SDG 11 (Sustainable Cities and Communities)",
     "SDG 11 (Sustainable Cities and Communities): The fire and smoke detection module, with hot-work permits that distinguish scheduled flame work from uncontrolled fires, contributes to safer urban construction environments, reducing the risk of uncontrolled fires on building sites that endanger both workers and surrounding communities."),
    ("Chapter 2 reviews existing systems",
     "Chapter 2 reviews existing systems and relevant published research, identifying the specific gap that Site-Safe fills. Chapter 3 describes the proposed system design: architecture, module specifications including QR-based identification, fall detection, fire and smoke detection, workforce monitoring, mobile application design, and data flow, followed by the requirements specification, the complete system workflow and the feasibility of the system. Chapter 4 describes the implementation: the development environment, QR identification and the Smart Vest, the vision modules, the backend, web and mobile applications, workforce activity monitoring, and the component, deployment, data and interaction views of the delivered system. Chapter 5 reports testing against the requirements traceability matrix, model evaluation and measured performance and reliability. Chapter 6 compares the outcomes with the objectives and sets out limitations and future work. The appendices give a user manual, an installation guide, the API and database reference and the detailed test evidence."),
    ("The fundamental limitation of CCTV is not the camera",
     "The fundamental limitation of CCTV is not the camera; it is the human being required to watch it. Sustained attention is cognitively demanding, and detection falls as feeds are added: observers in one study caught 83 percent of incidents on four monitors but 64 percent on sixteen, while surveyed UK control rooms gave each operator between 27 and 520 cameras [@stainer]. Beyond the attention problem, CCTV gives no information about what a camera cannot see: gas concentration in a trench, temperature inside a poorly ventilated enclosure, or how long a worker has been stationary in a hazardous zone. Its role in Site-Safe is not eliminated but redefined: cameras become the front end of an AI inference and activity tracking pipeline, not passive recording devices."),
    ("The Apple Watch and comparable devices",
     "The Apple Watch and comparable devices from Samsung and Garmin have introduced genuinely impressive sensing capabilities into a wrist-worn form factor. Modern smartwatches monitor heart rate, and an Apple Watch that detects a hard fall calls emergency services if the wearer does not respond [@applefall]. For personal health use, they are excellent."),
    ("For construction deployment, they fall short",
     "For construction deployment, they fall short in several practical ways. Bluetooth and Wi-Fi connectivity work well in homes and offices; on a large outdoor site, they become unreliable as soon as a worker moves beyond router range. A battery that lasts a day or two sounds adequate but does not account for continuous sensor polling under the computational load of real-time monitoring. And devices designed for a commuter are not designed to survive the concrete dust, water exposure, and physical impact of a construction shift. At tens of thousands of rupees per unit, equipping an entire site crew is financially impractical for most Pakistani construction firms."),
    ("SmartCap Technologies produces",
     "SmartCap Technologies produces a sensor, worn inside a safety helmet or as a headband, that measures brain activity to warn vehicle drivers and plant operators of fatigue [@smartcap]. Within its target application, heavy vehicle operation in mining, it performs well. Outside that target, it offers nothing: no PPE compliance detection, no environmental gas sensing, no fall detection capability, and no location or health data beyond fatigue state."),
    ("This pattern, high accuracy within a narrow domain",
     "This pattern, high accuracy within a narrow domain and zero applicability outside it, repeats across the industrial wearables category [@awolusi]. Proximity warning tags alert workers when machinery approaches but do not monitor heat stress. Heat stress monitors do not detect falls. Fall detectors do not watch for gas. The fragmentation reflects the fact that no existing product was designed with the multi-hazard complexity of a construction site as its primary design constraint."),
    ("The academic literature on computer vision applied to construction safety",
     "The academic literature on computer vision applied to construction safety is substantial and growing [@fangreview]. The YOLO family of models, introduced by Redmon et al. in 2016 [@yolov1], refined in YOLOv3 [@yolov3] and YOLOv7 [@yolov7] and developed through successive iterations to YOLOv11 [@ultralytics], has become the standard architectural choice for real-time PPE detection. The single-pass inference design achieves detection speeds and accuracy levels that are genuinely usable in operational contexts."),
    ("Published results are encouraging",
     "Published results are encouraging. Nath, Behzadan, and Paal (2020) compared three YOLOv3-based approaches for checking hard hats and vests; the best reached 72.3% mAP at 11 frames per second on a laptop [@nath], and similar methods detect safety-harness use at height [@fangharness]. Adoption on real sites has lagged, held back by technical and managerial obstacles [@fangreview]. Most published PPE detection studies evaluate their models on recorded images or video. They do not deploy on actual edge hardware, integrate with sensor networks, generate real-time alerts, or connect to mobile applications. They are demonstrations of what is possible in software, not implementations of what works in the field."),
    ("A small number of research prototypes",
     "A small number of research prototypes and commercial platforms have attempted to combine sensing modalities for construction safety. Raghunath and Ghaffar (2025) built an IoT smart helmet that combines GPS, temperature and humidity sensing for heat stress, and an accelerometer for fall detection [@helmet]. It is a meaningful step, but it has no vision component, so it can neither check PPE nor identify a worker from a camera."),
    ("Commercial platforms like Pillar Technologies",
     "Commercial platforms take two forms. Pillar Technologies places sensor units around a site that report temperature, humidity, dust, noise and volatile organic compounds and raise real-time alerts [@pillar], and Triax's Spot-r clip, worn by each worker, reports slips, trips and falls and clocks workers in over a closed mesh network [@triax]. Neither includes computer vision or checks PPE."),
    ("A growing category of construction safety tools",
     "A growing category of construction safety tools focuses on mobile applications. Apps like SafetyCulture (formerly iAuditor) [@safetyculture] and Safesite [@safesite] provide digital checklists, inspections and incident reporting forms. These tools digitize the paperwork side of safety management and make compliance documentation more convenient."),
    # The vest as built (1 Nov 2026): Wi-Fi instead of LoRa, power bank; gas on fixed zone monitors (4 Nov).
    ("QR code identification depends on camera",
     'QR code identification depends on camera distance and angle: at ranges beyond approximately 10 metres, or when helmets are tilted away from the camera, the QR may not be readable. Strategic camera placement at key checkpoints mitigates this, but full-site individual tracking is not guaranteed. Continuous camera monitoring raises privacy concerns that require transparent worker consent processes and clear data handling policies. The Smart Vest and gas monitors cover areas outside camera zones only within Wi-Fi range, and the MQ-2 reading is an uncalibrated estimate. The workforce activity monitoring component can only track workers in areas with camera coverage.'),
    ('For areas outside camera coverage, a lig',
     'For areas outside camera coverage, a lightweight Smart Vest built around the ESP32 microcontroller provides supplementary worker tracking. The vest is deliberately minimal: a GPS module (NEO-6M) for location and a tactile SOS panic button for emergencies. Fixed ESP32 monitors with an MQ-2 sensor [@mq2] watch each zone for flammable gas.'),
    ('Power is supplied by a 3.7V 2500mAh LiPo',
     "Power comes from a USB power bank, or a 5 V charger for a gas monitor. The vest reports every 5 seconds and sends an SOS press at once; a power bank reports no charge level, so battery is shown as not reported."),
    ('By keeping the vest hardware minimal, we',
     'By keeping the vest hardware minimal, we avoid the cost, complexity, and battery-life problems that plague multi-sensor wearables in construction environments. A GPS module and a button are simple to manufacture, easy to maintain, and require no worker training beyond “press this if you need help.” Further sensors become small fixed devices on the same telemetry pattern, as the gas monitors did.'),
    ('The vest transmits GPS coordinates and S',
     'The vest reports over Wi-Fi, posting its position and SOS state as JSON every 5 seconds; an SOS press is sent at once and retried every second until confirmed. LoRa at 433 MHz [@lora], first chosen for its 2 to 15 km range, was replaced because the prototype site is within Wi-Fi range and Wi-Fi needs no receiver. LoRa remains the upgrade for large sites.'),
    ("On the site itself, the primary edge devices",
     "On the site itself, the primary edge devices are AI cameras running YOLOv11 inference for both PPE detection and QR-based worker identification. Each worker wears a helmet with a unique printed QR code, which the same camera reads to establish identity without requiring any electronics on the person. A Smart Vest with GPS and SOS covers workers outside camera view, and fixed monitors watch zones for gas (Section 4.2.2). Everything converges at the backend server, which processes incoming data, evaluates alert rules, generates compliance records, and pushes updates to both the web dashboard and the mobile app in real time."),
    ("Tier 1 (Edge):",
     "Tier 1 (Edge): IP cameras feed an edge computer that runs a multi-model inference pipeline locally. A Raspberry Pi 5 or Jetson-class unit was proposed; the prototype runs on a laptop GPU (Section 4.1). The primary YOLOv11 model handles PPE detection on every frame; a person-and-vehicle detector and QR code reading run on every third frame, a YOLOv11-Pose model runs on every third frame for fall detection, and a fire and smoke model runs on every fifth frame. Together these models push violation alerts, fall events, fire detections and worker identification data to the backend, and the same pipeline feeds workforce activity monitoring. ESP32-based Smart Vests (GPS, SOS) and zone gas monitors report over Wi-Fi."),
    ("Tier 2 (Network):",
     "Tier 2 (Network): Camera alerts and QR identification data are sent over HTTP to the backend API, authenticated with per-camera device tokens and buffered in a local outbox while the server is unreachable. The Smart Vest and gas monitors post over Wi-Fi to the same API, each with its own device token; an MQTT broker (Mosquitto) also accepts vest messages from a gateway."),
    ("The vision module uses a YOLOv11-M model",
     "The vision module uses a YOLOv11-M model to continuously inspect camera frames for ten detection classes covering helmets, high-visibility vests, boots, gloves and goggles, each in a worn and a missing state. Frames are captured from IP cameras over RTSP or HTTP streams, resized to 640×640 and passed through the model on the edge device. Detections below a candidate confidence threshold (0.15 in the prototype, pending per-class calibration) are discarded. OpenCV’s QRCodeDetector [@opencv] scans sampled frames for QR codes on worker helmets, linking a detected person to their registered identity. A worker without required PPE triggers a violation event logged with worker identity (from QR, when readable), timestamp, camera ID, zone and detection confidence, creating an auditable per-worker compliance record."),
    ("Administrators define Red Zones",
     "Administrators define Red Zones by drawing polygon boundaries directly on the site map in the dashboard, and the polygons are stored in the database. A camera that reads a worker's QR badge places the worker in that camera's zone, and vest GPS positions are checked against the zone polygons with a point-in-polygon test. An incursion into a restricted zone, by an unassigned worker or anyone a camera cannot identify, triggers an immediate dashboard alert and a push notification to the safety officer. Hazards smaller than a zone are drawn as danger areas on a camera's picture (Section 4.3.8)."),
    ("The Django REST Framework backend provides the API layer",
     "The Django REST Framework backend provides the API layer that edge devices write to and both the dashboard and mobile app read from. A separate MQTT consumer process handles incoming vest telemetry, and critical alerts are routed to WebSocket clients and to the FCM push notification service. Notifications are sent from a background thread pool after each alert is committed, and PDF and DOCX reports are produced by a separate Node.js report service, so neither blocks API response times."),
    ("The mobile application is built with React Native",
     "The mobile application is built with React Native, enabling a single JavaScript codebase to target both iOS and Android platforms. React Native was chosen specifically because the team already has React expertise from the web dashboard development, and the component model and API service patterns carry over between web and mobile."),
    ("The admin interface, accessible through both",
     "The admin interface, accessible through both the web dashboard and the mobile app, handles site configuration and worker management. Admins can register workers and assign QR codes to their profiles, draw geofence zones on the site map, configure alert and notification preferences, and generate or download PDF compliance reports for any date range. Access is role-gated: Admin, Safety Officer, and read-only Viewer roles are defined with corresponding permission sets enforced at the API level."),
]

# Table 2.1 rows replaced whole: (prefix of the V7 first cell, new cells).
# Each system cites its source; Site-Safe's long-range link and vest are
# proposals.
TABLE_21_ROWS = [
    ("Apple/Samsung Watch", ("Apple/Samsung Watch [@applefall]", "2023", "No", "Partial", "No", "Yes", "No", "Short range, expensive")),
    ("SmartCap", ("SmartCap (Mining) [@smartcap]", "2017", "No", "EEG only", "No", "Yes", "No", "Single-purpose")),
    ("YOLO Research", ("YOLO research [@nath]", "2020", "Yes", "No", "No", "No", "No", "Software-only, no deploy")),
    ("Pillar Technologies", ("Pillar Technologies [@pillar]", "2017", "No", "Environment only", "No", "Partial", "Partial", "No vision, no worker ID")),
    ("SafetyCulture App", ("SafetyCulture App [@safetyculture]", "2023", "No", "No", "N/A", "Yes", "No", "Manual, no detection")),
    ("Ramli et al.", ("Raghunath and Ghaffar [@helmet]", "2025", "No", "Yes", "Not stated", "Not stated", "Not stated", "No vision")),
    ("Site-Safe (ours)", ("Site-Safe (ours)", "2026", "Yes", "QR + GPS vest, zone gas monitors", "Wi-Fi (LoRa future)", "Yes", "Yes", "Prototype; QR range and vest not yet field-tested")),
]

ABBREVIATIONS_ADD = [
    ("ADC", "Analogue-to-Digital Converter"),
    ("ASGI", "Asynchronous Server Gateway Interface"),
    ("CI", "Continuous Integration"),
    ("FR", "Functional Requirement"),
    ("LPG", "Liquefied Petroleum Gas"),
    ("NFR", "Non-Functional Requirement"),
    ("QR", "Quick Response (code)"),
]
ABBREVIATIONS_REMOVE = ["ONNX", "LoRaWAN"]

# The reference list, in IEEE style, replaces V7's. The builder numbers the
# entries in order of first citation and fails if an entry is never cited
# or a citation has no entry. Journal and conference entries were checked
# against Crossref; software versions are the installed ones.
ACCESSED = "Accessed: Nov. 1, 2026."
REFERENCES = {
    "ilo": f'International Labour Organization, "Construction: a hazardous work," Mar. 23, 2015. [Online]. Available: https://www.ilo.org/resource/construction-hazardous-work. {ACCESSED}',
    "lfs": f'Pakistan Bureau of Statistics, "Labour Force Survey 2020-21," Islamabad, Pakistan, 2022. [Online]. Available: https://www.pbs.gov.pk/content/labour-force-survey. {ACCESSED}',
    "lecun": 'Y. LeCun, Y. Bengio, and G. Hinton, "Deep learning," Nature, vol. 521, no. 7553, pp. 436–444, 2015, doi: 10.1038/nature14539.',
    "stainer": 'M. J. Stainer, K. C. Scott-Brown, and B. W. Tatler, "Looking for trouble: a description of oculomotor search strategies during live CCTV operation," Front. Hum. Neurosci., vol. 7, art. no. 615, 2013, doi: 10.3389/fnhum.2013.00615.',
    "applefall": f'Apple Inc., "Use Fall Detection with Apple Watch," Apple Support. [Online]. Available: https://support.apple.com/en-us/108896. {ACCESSED}',
    "smartcap": f'"Smart hard hats sound alarm as workers tire," The Construction Enquirer, Feb. 15, 2017. [Online]. Available: https://www.constructionenquirer.com/2017/02/15/smart-hard-hats-sound-alarm-as-workers-tire/. {ACCESSED}',
    "awolusi": 'I. Awolusi, E. Marks, and M. Hallowell, "Wearable technology for personalized construction safety monitoring and trending: Review of applicable devices," Autom. Constr., vol. 85, pp. 96–106, 2018, doi: 10.1016/j.autcon.2017.10.010.',
    "fangreview": 'W. Fang, L. Ding, P. E. D. Love, H. Luo, H. Li, F. Peña-Mora, B. Zhong, and C. Zhou, "Computer vision applications in construction safety assurance," Autom. Constr., vol. 110, art. no. 103013, 2020, doi: 10.1016/j.autcon.2019.103013.',
    "yolov1": 'J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, "You only look once: Unified, real-time object detection," in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2016, pp. 779–788, doi: 10.1109/CVPR.2016.91.',
    "yolov3": 'J. Redmon and A. Farhadi, "YOLOv3: An incremental improvement," arXiv preprint arXiv:1804.02767, 2018.',
    "yolov7": 'C.-Y. Wang, A. Bochkovskiy, and H.-Y. M. Liao, "YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors," in Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit. (CVPR), 2023, pp. 7464–7475, doi: 10.1109/CVPR52729.2023.00721.',
    "ultralytics": 'G. Jocher, J. Qiu, and A. Chaurasia, "Ultralytics YOLO," version 8.4.41, 2026. [Online]. Available: https://github.com/ultralytics/ultralytics',
    "nath": 'N. D. Nath, A. H. Behzadan, and S. G. Paal, "Deep learning for site safety: Real-time detection of personal protective equipment," Autom. Constr., vol. 112, art. no. 103085, 2020, doi: 10.1016/j.autcon.2020.103085.',
    "fangharness": 'W. Fang, L. Ding, H. Luo, and P. E. D. Love, "Falls from heights: A computer vision-based approach for safety harness detection," Autom. Constr., vol. 91, pp. 53–61, 2018, doi: 10.1016/j.autcon.2018.02.018.',
    "helmet": 'S. Raghunath and S. H. Ghaffar, "Developing an IoT-enabled smart helmet for worker safety: Technical feasibility and business model," Safety, vol. 11, no. 3, art. no. 89, 2025, doi: 10.3390/safety11030089.',
    "pillar": f'F. Tepper, "Pillar Technologies is making construction sites safer with smart sensors," TechCrunch, Jan. 6, 2017. [Online]. Available: https://techcrunch.com/2017/01/06/pillar-technologies-is-making-construction-sites-safer-with-smart-sensors/. {ACCESSED}',
    "triax": f'"IoT-based wearable system launched by Triax Technologies," IoT Now, May 24, 2017. [Online]. Available: https://www.iot-now.com/2017/05/24/62271-iot-based-wearable-system-launched-triax-technologies/. {ACCESSED}',
    "safetyculture": f'SafetyCulture, "SafetyCulture." [Online]. Available: https://safetyculture.com/. {ACCESSED}',
    "safesite": f'Safesite, "Safesite." [Online]. Available: https://safesitehq.com/. {ACCESSED}',
    "opencv": 'G. Bradski, "The OpenCV library," Dr. Dobb\'s J. Softw. Tools, 2000.',
    "coco": 'T.-Y. Lin, M. Maire, S. Belongie, J. Hays, P. Perona, D. Ramanan, P. Dollár, and C. L. Zitnick, "Microsoft COCO: Common objects in context," in Proc. Eur. Conf. Comput. Vis. (ECCV), 2014, pp. 740–755, doi: 10.1007/978-3-319-10602-1_48.',
    "dataset": 'testcasque, "PPE Detection (ppe-detection-qlq3d)," Roboflow Universe, dataset version 1, CC BY 4.0, exported Oct. 19, 2024. [Online]. Available: https://universe.roboflow.com/testcasque/ppe-detection-qlq3d',
    "dfire": 'P. V. A. B. de Venâncio, A. C. Lisboa, and A. V. Barbosa, "An automatic fire detection system based on deep convolutional neural networks for low-power, resource-constrained devices," Neural Comput. Appl., vol. 34, no. 18, pp. 15349–15368, 2022, doi: 10.1007/s00521-022-07467-z.',
    "esp32": f'Espressif Systems, "ESP32 Technical Reference Manual." [Online]. Available: https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf. {ACCESSED}',
    "mq2": f'Hanwei Electronics, "MQ-2 Semiconductor Sensor for Combustible Gas: Technical Data." [Online]. Available: https://www.pololu.com/file/0J309/MQ2.pdf. {ACCESSED}',
    "lora": f'Semtech, "LoRa and LoRaWAN: A Technical Overview." [Online]. Available: https://lora-developers.semtech.com/. {ACCESSED}',
    "mosquitto": 'R. A. Light, "Mosquitto: server and client implementation of the MQTT protocol," J. Open Source Softw., vol. 2, no. 13, art. no. 265, 2017, doi: 10.21105/joss.00265.',
    "drf": 'Encode OSS, "Django REST framework," version 3.17.1, 2026. [Online]. Available: https://www.django-rest-framework.org/',
    "channels": 'Django Software Foundation, "Channels," version 4.3.2, 2026. [Online]. Available: https://channels.readthedocs.io/',
    "fcm": f'Google, "Firebase Cloud Messaging." [Online]. Available: https://firebase.google.com/docs/cloud-messaging. {ACCESSED}',
    "leaflet": 'Leaflet, "Leaflet: an open-source JavaScript library for interactive maps," version 1.9.4, 2023. [Online]. Available: https://leafletjs.com/',
    "reactnative": 'Meta Platforms, "React Native," version 0.88, 2026. [Online]. Available: https://reactnative.dev/',
    "expo": 'Expo, "Expo SDK 58," 2026. [Online]. Available: https://docs.expo.dev/',
}

# ---------------------------------------------------------------- Chapter 3
# 3.2.2 replaces V7's list, whose items were run together; Sections 3.8 and
# 3.9 are inserted before V7's 3.8 Limitations, which becomes 3.10. Their
# tables and figures follow Table 3.2 and Figure 3.8, so nothing earlier in
# the chapter is renumbered.

DATA_FLOW_322 = [
    ("p", "Data moves through the tiers in three flows. Camera frames are analysed on the edge, and only confirmed events, with the worker's badge and the evidence frame, are posted to the API. Vest positions and SOS presses reach the API over HTTP or MQTT. Configuration (zones, cameras, alert rules and permits) flows from the dashboard to the database, and cameras poll their rules from it. Figure 3.4 shows these flows as a Level-1 data flow diagram; Section 3.9 gives the Level-0 diagram and the complete workflow."),
]

LIMITATIONS_HEADING = ("3.8 Limitations", "3.10 Limitations")

# V7's Figures 3.1-3.8 were placed at a different aspect ratio than their
# images and printed stretched; they are redrawn by make_figures.py.
# (caption, file in docs/figures, width in inches, paragraph it follows:
# a prefix of the paragraph that refers to it, or the previous caption).
CHAPTER_3_FIGURES = [
    ("Figure 3.1: Use Case Diagram", "fig_use_case.png", 5.6, "On the site itself, the primary edge devices"),
    ("Figure 3.2: System Context Diagram", "fig_system_context.png", 6.0, "Figure 3.1: Use Case Diagram"),
    ("Figure 3.3: Three-Tier System Architecture", "fig_three_tier.png", 6.0, "Figure 3.3 shows the three tiers"),
    ("Figure 3.4: Level-1 Data Flow Diagram", "fig_dfd_level1.png", 6.0, "Data moves through the tiers in three flows"),
    ("Figure 3.5: Workforce Activity Monitoring Pipeline", "fig_activity_pipeline.png", 6.0, "All activity data is stored in PostgreSQL"),
    ("Figure 3.6: Smart Vest and Gas Monitor Block Diagram", "fig_vest_block.png", 6.0, "For areas outside camera coverage"),
    ("Figure 3.7: SOS and Location Alert Flowchart", "fig_sos_flowchart.png", 5.8, "By keeping the vest hardware minimal"),
    ("Figure 3.8: Mobile Application Screen Wireframes", "fig_mobile_wireframes.png", 6.0, "For users with Admin role privileges"),
]

# Captions that changed since V7, by new caption: V7's caption finds the picture to replace.
V7_FIGURE_CAPTIONS = {"Figure 3.6: Smart Vest and Gas Monitor Block Diagram": "Figure 3.6: Smart Vest Block Diagram"}

# Section 3.2 opened with Figure 3.3 and no text, so nothing referred to it first.
ARCHITECTURE_INTRO = ("3.2 Architecture", "Figure 3.3 shows the three tiers of the design and the components in each, described in Section 3.2.1.")

# (prefix of the paragraph, sentence appended): each figure is referred to
# before it appears.
FIGURE_REFERENCES = [
    ("On the site itself, the primary edge devices", "Figure 3.1 shows the use cases of Table 3.5, and Figure 3.2 places the system among the people and devices around it."),
    ("All activity data is stored in PostgreSQL", "Figure 3.5 shows this pipeline."),
    ("For areas outside camera coverage", "Figure 3.6 shows their block diagram."),
    ("By keeping the vest hardware minimal", "Figure 3.7 traces an SOS press or a periodic position report from the vest to an alert."),
    ("For users with Admin role privileges", "Figure 3.8 shows wireframes of the main screens."),
]

# Moved from before Section 3.4.2 to follow the block diagram it describes.
# Headings renamed in place, keeping their formatting: (old, new).
HEADING_RENAMES = [("3.4.3 LoRa Communication Layer", "3.4.3 Vest Communication Layer")]

VEST_POWER_PARAGRAPH = "Power comes from a USB power bank"

TABLE_33 = [
    ("Interface", "Type", "Requirement"),
    ("Camera to edge computer", "Hardware", "IP camera over RTSP or HTTP, or a USB camera, placed so badges (60 mm) are readable; tested at 1280×720"),
    ("Edge computer", "Hardware", "GPU able to run all detectors at 10 FPS or more (NFR-04)"),
    ("Vest to API", "Hardware", "ESP32 with GPS (UART; not yet fitted) and SOS button (GPIO), over Wi-Fi (Tables 4.2 and 4.3)"),
    ("Gas monitor to API", "Hardware", "ESP32 with an MQ-2 gas sensor (ADC), fixed in a zone, over Wi-Fi (Tables 4.2 and 4.3)"),
    ("Camera and gateway to API", "Software", "JSON over HTTP (HTTPS on a site network) with a device token, Authorization: Device <key>, one per camera or gateway"),
    ("Gateway to broker", "Software", "MQTT topics sitesafe/vest/<id>/telemetry and /sos on Mosquitto"),
    ("Clients to API", "Software", "REST with a 30-minute JWT renewed by a refresh token; WebSocket /ws/dashboard/ with the same token"),
    ("Backend to services", "Software", "PostgreSQL 14 or later; Redis channel layer; Node.js report service; Firebase Cloud Messaging and SMTP"),
    ("Users", "Software", "Current desktop browser for the command centre; Android or iOS phone (Expo) for the mobile app"),
]

TABLE_34 = [
    ("ID", "Requirement", "Pri.", "Acceptance criterion"),
    ("FR-01", "Sign in with e-mail and password; sessions renew silently", "M", "Expired access token renews; revoked refresh token returns to sign-in"),
    ("FR-02", "Admin, Safety Officer and Viewer roles enforced by the API", "M", "Every forbidden action returns 403; its permitted counterpart succeeds"),
    ("FR-03", "Interface offers only actions the role permits", "S", "Viewer sees no resolve, edit or generate controls"),
    ("FR-04", "Detect missing PPE (10 classes) from a camera", "M", "Event precision ≥ 90% and episode recall ≥ 85% on a sealed target-camera set"),
    ("FR-05", "One alert per person per violation episode", "M", "Two people give two alerts; a one-frame flicker gives none"),
    ("FR-06", "Detect falls from camera pose", "M", "Fall and hard-negative videos meet the AI event targets"),
    ("FR-07", "Warn when a worker is too close to a vehicle", "M", "One alert per person per encounter; threshold evaluated on video"),
    ("FR-08", "Detect prolonged inactivity with a dashboard-set timeout", "M", "A changed rule changes the camera timeout within 60 s"),
    ("FR-09", "Fire and smoke detection governed by hot-work permits", "M", "Fixture videos pass; a permitted fire is downgraded, never dropped"),
    ("FR-10", "Identify workers by the QR badge on the helmet", "M", "Association, unknown and wrong-person rates measured at stated distance and light"),
    ("FR-11", "Camera events reach the API reliably", "M", "100 events queued in a 5-minute outage arrive exactly once"),
    ("FR-12", "Only authorised devices submit data", "M", "Anonymous, revoked, wrong-kind or wrong-camera tokens are rejected"),
    ("FR-13", "Live updates for every alert, vest and worker change", "M", "Two sessions converge after create, resolve, SOS and reconnect"),
    ("FR-14", "WebSocket requires a valid user token and allowed origin", "M", "Missing, bad or expired token closes with code 4401"),
    ("FR-15", "Alert rules (enable, threshold, notify) change behaviour", "M", "A disabled type stores nothing; SOS, FIRE and GAS cannot be disabled"),
    ("FR-16", "Push notifications to subscribed users", "S", "An Android phone receives a push; tapping opens the alert"),
    ("FR-17", "E-mail notifications", "S", "Mail reaches opted-in users when the rule enables it"),
    ("FR-18", "Register, edit and deactivate workers in the interface", "M", "All three work in the browser; one vest per worker"),
    ("FR-19", "Zones with polygon boundaries and assigned cameras", "M", "Invalid geometry rejected; boundary drawn on a map"),
    ("FR-20", "Automatic restricted-zone breach and over-occupancy alerts", "M", "One ZONE_BREACH per unassigned or unidentified entry, or excess occupancy"),
    ("FR-21", "Smart Vest (GPS position, SOS button) and fixed zone gas monitors over Wi-Fi", "M", "A physical SOS and a gas leak reach the dashboard; delay measured; a gas alert names the zone"),
    ("FR-22", "Vest telemetry is validated", "M", "Out-of-range coordinates or battery return 400"),
    ("FR-23", "Vest offline detection", "S", "A vest silent for 120 s is shown offline"),
    ("FR-24", "Activity history: check-in, check-out, idle", "M", "Recorded automatically and reconciled with annotated scenarios"),
    ("FR-25", "Incident list, detail, resolve and CSV export", "M", "Resolution is broadcast; filters cover every alert type"),
    ("FR-26", "Dashboard shows recorded data only", "M", "Every figure reconciles to the API"),
    ("FR-27", "Incident and safety-performance reports in DOCX and PDF", "M", "Fixtures reconcile exactly; no unsupported percentages"),
    ("FR-28", "Mobile app: alerts, resolve, workers, site map, cameras, push", "M", "An Android build receives a push and resolves an alert seen on the web"),
    ("FR-29", "Alert evidence: snapshot, confidence, model version", "S", "Each AI alert is traceable to its frame and model"),
    ("FR-30", "Live camera grid for monitoring", "S", "Running cameras appear live to Safety Officers and Admins within seconds; Viewers see no video"),
    ("FR-31", "Locate workers and count people per zone by camera", "S", "A badge read places the worker in the camera's zone; overlapping cameras never double-count"),
    ("FR-32", "Danger areas drawn on the camera picture", "S", "A person inside an active area for 1 s raises one alert; walking past raises none"),
    ("FR-33", "Cameras on the site map", "S", "Placed cameras show their coverage and live, offline or alerting state"),
    ("FR-34", "Evidence snapshots in reports", "S", "Reports show captioned frames of the most severe incidents and state what is missing"),
]

TABLE_35 = [
    ("Use case (Figure 3.1)", "Actors", "Description", "FRs"),
    ("UC-1 Wear QR-tagged helmet", "Worker", "Wears the printed badge so cameras can attribute events", "FR-10"),
    ("UC-2 Trigger SOS alert", "Worker", "Presses the vest SOS button (Table 3.7)", "FR-20–23"),
    ("UC-3 Detect PPE violations", "IP Camera, Safety Officer", "Camera raises a violation; officer responds (Table 3.6)", "FR-04, 05, 29"),
    ("UC-4 Identify workers via QR", "IP Camera", "Badge decoded and linked to the person's box", "FR-10"),
    ("UC-5 Monitor zone breaches", "Safety Officer, Admin", "Restricted entry, over-occupancy or a danger-area entry raises an alert", "FR-19, 20, 31, 32"),
    ("UC-6 Track workforce activity", "Safety Officer", "Attendance, idle time and timelines per worker", "FR-08, 24"),
    ("UC-7 View dashboard and alerts", "Safety Officer, Admin", "Live alerts, cameras, site map, incidents and reports on web and mobile", "FR-13, 25–28, 30, 33, 34"),
    ("UC-8 Configure alert thresholds", "Admin", "Enable rules, set thresholds and notifications", "FR-15"),
]

TABLE_36 = [
    ("Field", "UC-3 Detect PPE Violations"),
    ("Scope and level", "Site-Safe system; user goal"),
    ("Primary actor", "IP Camera (initiates); Safety Officer (responds)"),
    ("Stakeholders", "Safety Officer: a prompt alert naming the worker. Worker: no false accusation, images kept no longer than needed. Management: an auditable record."),
    ("Preconditions", "The camera has a device token and is assigned to a zone; the PPE rule is enabled; the officer is signed in."),
    ("Success guarantee", "One alert per person per episode is stored with type, severity, camera, zone, worker if identified, confidence, model version and snapshot, shown live, and its resolution recorded."),
    ("Main success scenario", "1. The pipeline detects a missing-PPE box on a person. 2. The episode persists for 1 s in at least 3 frames. 3. The person's badge is read and the evidence attached. 4. The event is queued and posted. 5. The server checks the token and rule and stores the alert once. 6. Dashboard and app show it; push and e-mail follow the rule. 7. The officer reviews the snapshot, acts and resolves it. 8. Every session shows it resolved."),
    ("Extensions", "2a. Shorter flicker: no alert. 3a. Badge unreadable or ambiguous: the alert is stored as not identified. 4a. Server unreachable: the event stays in the outbox and is retried until stored once. 5a. Rule disabled: reply 202, nothing stored. Fall, proximity, inactivity and fire follow the same path with their own confirmation; fire severity depends on hot-work permits."),
    ("Special requirements", "NFR-01 latency, NFR-02 outage tolerance, NFR-03 security; snapshots of at most 512 KB, deleted after 30 days."),
]

TABLE_37 = [
    ("Field", "UC-2 Trigger SOS Alert"),
    ("Scope and level", "Site-Safe system; user goal"),
    ("Primary actor", "Worker; supporting actor: the Smart Vest"),
    ("Stakeholders", "Worker: help arrives quickly at the right place. Safety Officer: one clear alert with a position."),
    ("Preconditions", "The vest is registered and assigned to the worker and has a device token."),
    ("Success guarantee", "One CRITICAL SOS alert with the worker and position is stored, shown live and notified; the worker is checked in."),
    ("Main success scenario", "1. The worker presses SOS. 2. The vest sends position, SOS state and its press count through the gateway (HTTP or MQTT). 3. The server validates it, updates the position and finds the zone. 4. On a new press it raises the alert unless one is open. 5. The map and app show the alert and location; notifications are sent. 6. The officer responds and resolves it."),
    ("Extensions", "1a. Button held: no repeat alert. 1b. Held again for 3 s: the alert is resolved as cancelled by the wearer. 1c. Pressed again after the officer resolved it: a new alert. 3a. Invalid payload: rejected with 400. 3b. Restricted zone: a ZONE_BREACH is also raised. Vest silent for 120 s: shown offline. Simulator token: alert labelled SIMULATED and excluded from reports."),
    ("Special requirements", "Verified with the simulator, firmware-generated messages and a bench test of the vest without GPS (FR-21)."),
]

TABLE_38 = [
    ("ID", "Category", "Requirement", "Target (proposed)"),
    ("NFR-01", "Performance", "Event-to-dashboard latency", "95th percentile ≤ 2 s on a local network"),
    ("NFR-02", "Reliability", "Outage tolerance", "No lost or duplicated events across a 5-minute API outage and sender restart"),
    ("NFR-03", "Security", "Producer security", "No anonymous write endpoint; no credentials in source code"),
    ("NFR-04", "Performance", "Inference throughput", "≥ 10 FPS with all detectors on the demonstration machine"),
    ("NFR-05", "Reliability", "Soak", "2-hour full-stack run with a controlled disconnect"),
    ("NFR-06", "Portability", "Reproducible setup", "A fresh machine reaches a working demonstration from the README"),
    ("NFR-07", "Maintainability", "Quality gate", "All test suites pass; frontend builds and lints clean"),
]

TABLE_39 = [
    ("Resource", "Used in the prototype", "Justification"),
    ("Development and edge computer", "Apple M4 laptop, 16 GB, built-in GPU", "Runs all detectors at 15.7 FPS (NFR-04); a Jetson-class unit is the site option"),
    ("Training GPU", "Google Colab and Kaggle, Tesla T4", "Training exceeded the laptop's memory; the fire model was trained on Kaggle"),
    ("Cameras", "Webcam, phone IP-camera application and recorded test videos", "Same code path as site RTSP cameras"),
    ("Phone", "Android phone (push test pending)", "Firebase push needs a development build on a device"),
    ("Smart Vest and gas monitor parts", "Bought (4 Nov), except the GPS module", "ESP32 DevKit, SOS button, MQ-2 gas sensor, resistors, breadboard; one board runs both on the bench (Table 4.2)"),
    ("Software and data", "Open-source stack (Table 4.1); CC BY 4.0 dataset", "No licence cost; dataset licence permits reuse with attribution"),
    ("Human effort", "Three members over two semesters", "[Task division and person-months to be completed by the team]"),
]

TABLE_310 = [
    ("Aspect", "Assessment"),
    ("Technical", "Feasible. Every component uses mature open-source frameworks, the full detector set runs at 16 FPS on a laptop GPU and 525 automated tests pass. The open risk is detection of missing equipment (Section 5.5)."),
    ("Operational", "Feasible. Officers keep their role and receive alerts on their phones; workers need only a paper badge; zones are drawn on a map. Cameras must be placed so badges are readable."),
    ("Economic", "Low cost. The software is open source, existing IP cameras can be reused and badges cost a sheet of paper; the main expense is an edge GPU computer per site, plus optional vest hardware."),
    ("Legal and ethical", "Camera monitoring needs informed worker consent and signage. Badges carry a random code, not personal data; snapshots are visible only to signed-in users, deleted after 30 days and can be switched off. The system informs the officer and makes no disciplinary decision."),
    ("Health, safety and society", "Aims to prevent injuries and deaths (SDG 3 and 8). Missed detections remain possible, so it supplements supervision rather than replacing it."),
    ("Environmental", "Runs on existing hardware; the only consumables are paper badges and, later, vest batteries."),
]

CHAPTER_3_ADDITIONS = [
    ("h2", "3.8 Requirements Specification"),
    ("h3", "3.8.1 Interface Requirements"),
    ("p", "Table 3.3 lists the interfaces between the components and with external systems. Cameras and vest gateways never sign in as users; each authenticates with a device token limited to its own kind of data."),
    ("table", "Table 3.3: Interface Requirements", TABLE_33, [1.6, 0.8, 3.6], 8.5),
    ("h3", "3.8.2 Functional Requirements"),
    ("p", "Table 3.4 lists the functional requirements with their priority (M must, S should) and the acceptance criterion each is tested against in Chapter 5. The criteria are the team's proposals."),
    ("table", "Table 3.4: Functional Requirements", TABLE_34, [0.6, 2.2, 0.4, 2.8], 7.8),
    ("h3", "3.8.3 Use Cases"),
    ("p", "Table 3.5 describes the use cases of Figure 3.1. Two are written as full-dress use cases because they cross several components and have failure paths: detecting a PPE violation (Table 3.6), which every camera hazard follows, and triggering an SOS (Table 3.7)."),
    ("table", "Table 3.5: Use Case Descriptions", TABLE_35, [1.65, 1.2, 2.25, 0.9], 8),
    ("table", "Table 3.6: Full-Dress Use Case: Detect PPE Violations", TABLE_36, [1.3, 4.7], 8),
    ("table", "Table 3.7: Full-Dress Use Case: Trigger SOS Alert", TABLE_37, [1.3, 4.7], 8),
    ("h3", "3.8.4 Non-Functional Requirements"),
    ("p", "Table 3.8 lists the non-functional requirements; Section 5.6 reports their measurement."),
    ("table", "Table 3.8: Non-Functional Requirements", TABLE_38, [0.7, 1.1, 1.5, 2.7], 8.5),
    ("h3", "3.8.5 Resource Requirements"),
    ("p", "Table 3.9 lists the resources used to build and run the prototype. Costs are not tabulated: the software is open source, and quotations for the vest parts have not yet been recorded."),
    ("table", "Table 3.9: Resource Requirements", TABLE_39, [1.45, 2.05, 2.5], 8.5),
    ("h3", "3.8.6 Database Requirements"),
    ("p", "The system needs a relational database (PostgreSQL) that stores each camera event exactly once under its event identifier, keeps every alert with its worker, zone, permit, model version and snapshot, records attendance at the time of the event so that late deliveries merge into their session, and holds only a hash of each device key. Snapshots are deleted after the retention period while their alerts are kept. Figure 4.2 shows the data model and Appendix III the tables."),
    ("h3", "3.8.7 Project Feasibility"),
    ("p", "Table 3.10 assesses the feasibility of the system, including its cost, health and safety, legal, ethical, societal and environmental aspects."),
    ("table", "Table 3.10: Feasibility Assessment", TABLE_310, [1.3, 4.7], 8.5),
    ("h2", "3.9 System Workflow"),
    ("p", "Figure 3.9 shows the complete workflow as an activity diagram, from setting up a site to the compliance report. An administrator registers workers and prints their QR badges, draws zones, assigns cameras and sets alert rules, and safety officers issue hot-work permits for planned flame work. While the site runs, each camera pipeline captures frames and runs its detectors; an unconfirmed hazard returns the loop to the next frame. A confirmed hazard is tagged with the person's badge, the confidence, the model version and a snapshot, queued in the outbox and posted with the camera's device token."),
    ("p", "The backend authenticates the device, discards alert types whose rule is disabled, sets the severity, which for fire and smoke depends on any active permit, and stores the alert once. After the transaction commits, the alert appears live on the dashboard and the mobile app and notifications are sent. The officer reviews the snapshot, acts on site and resolves the alert, and the stored records feed the attendance timelines and reports. Vest telemetry joins the same path at validation (Section 4.9)."),
    ("fig", "fig_activity_workflow.png", 5.6, "Figure 3.9: System Workflow Activity Diagram"),
    ("p", "Figure 3.10 is the Level-0 data flow diagram: the whole system as one process and the data it exchanges with its external entities. Figure 3.4 decomposes it into Level-1 processes."),
    ("fig", "fig_dfd_level0.png", 6.0, "Figure 3.10: Level-0 Data Flow Diagram"),
]

# ---------------------------------------------------------------- Front matter
# Blank pages from SOP Appendix G, between the abstract and the contents.
# Blanks are left for the committee, signatures and the Turnitin result.

PROJECT_TITLE = "Site-Safe: A Digital Ecosystem for Autonomous Construction Safety"
STUDENTS = ("Muhammad Hamza", "Hamza Hussain", "Hanan Saeed")
SUPERVISOR = "Muhammad Yousif"
BLANK = "____________________"
SHORT_BLANK = "______________"

# ("title" | "heading" | "p" | "line" (left, right) | "right" | "gap", ...)
FRONT_PAGES = [
    [
        ("title", "CERTIFICATE"),
        ("right", f"Dated: {BLANK}"),
        ("heading", "Final Approval"),
        ("p", f"It is certified that the project report titled “{PROJECT_TITLE}”, submitted by {STUDENTS[0]}, {STUDENTS[1]} and {STUDENTS[2]} for the partial fulfillment of the requirement of the Bachelor’s Degree in Computer Science, is approved."),
        ("gap",),
        ("heading", "COMMITTEE"),
        ("line", f"Dean (Engineering & Computing): {SHORT_BLANK}", f"Signature: {SHORT_BLANK}"),
        ("line", f"Head of Department, Computer Science: {SHORT_BLANK}", f"Signature: {SHORT_BLANK}"),
        ("line", f"Project Coordinator: {SHORT_BLANK}", f"Signature: {SHORT_BLANK}"),
        ("line", f"Supervisor: {SUPERVISOR}", f"Signature: {SHORT_BLANK}"),
    ],
    [
        ("title", "DECLARATION"),
        ("p", "We hereby declare that our dissertation is entirely our own work and genuine and original. We understand that in case of discovery of any PLAGIARISM at any stage, our group will be assigned an F (FAIL) grade and it may result in withdrawal of our Bachelor’s degree."),
        ("gap",),
        ("p", "Group members:"),
        ("line", "Name", "Signature"),
        *[("line", name, BLANK) for name in STUDENTS],
    ],
    [
        ("title", "PLAGIARISM CERTIFICATE"),
        ("p", f"This is to certify that the project entitled “{PROJECT_TITLE}”, which is being submitted herewith for the award of the Degree of Bachelor’s in Computer Science, is the result of the original work by {STUDENTS[0]}, {STUDENTS[1]} and {STUDENTS[2]} under my supervision and guidance. The work embodied in this project has not been done earlier as the basis for the award of any degree or comparable certificate or similar title by any other diploma or examining body or university, to the best of my knowledge and belief."),
        ("gap",),
        ("line", "Turnitin similarity index:", "______ %"),
        ("line", "Internet sources:", "______ %"),
        ("line", "Publications:", "______ %"),
        ("line", "Student papers:", "______ %"),
        ("gap",),
        ("line", f"Date: {BLANK}", f"{SUPERVISOR} (Supervisor)"),
    ],
    [
        ("title", "TURNITIN ORIGINALITY REPORT"),
        ("p", f"{PROJECT_TITLE} [BSCS] by {STUDENTS[0]}, {STUDENTS[1]} and {STUDENTS[2]}, from {SUPERVISOR}."),
        ("line", f"Processed on: {BLANK}", f"ID: {BLANK}"),
        ("line", f"Word count: {BLANK}", "Similarity index: ______ %"),
        ("gap",),
        ("p", "[Insert the Turnitin originality report pages here.]"),
    ],
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
    ("react-native-webview / react-native-svg", "14.0.1 / 15.16.0", "Mobile site map (Leaflet) and danger-area outlines"),
    ("Docker Compose / GitHub Actions", "Written, not yet run", "Eight-service deployment; CI running every test suite"),
    ("Git", "2.53.0", "Version control"),
]

TABLE_42 = [
    ("Component", "Model", "Range", "Accuracy", "Interface"),
    ("Controller", "ESP32 DevKit, 30-pin (ESP32-D0WD-V3)", "Wi-Fi 2.4 GHz", "N/A", "USB, GPIO"),
    ("GPS (not yet fitted)", "NEO-6M", "Worldwide", "2.5 m CEP", "UART"),
    ("Gas sensor (gas monitor)", "MQ-2", "300–10,000 ppm", "Uncalibrated estimate", "Analogue (ADC)"),
    ("SOS Button (vest)", "Tactile Switch", "N/A", "N/A", "GPIO"),
    ("Power", "Vest: USB power bank; monitor: 5 V charger", "5 V", "N/A", "USB"),
]

TABLE_43 = [
    ("GPIO Pin", "Connected To", "Protocol", "Notes"),
    ("GPIO 16 (RX2)", "NEO-6M TX", "UART", "9600 baud; GPS not yet fitted"),
    ("GPIO 17 (TX2)", "NEO-6M RX", "UART", "9600 baud; optional"),
    ("GPIO 34", "MQ-2 AO (gas monitor)", "Analogue", "Through two 22 kΩ resistors (5 V to at most 2.5 V)"),
    ("GPIO 27", "SOS Button (vest)", "Digital", "To GND, internal pull-up"),
    ("GPIO 2", "On-board LED", "Digital", "On during SOS"),
    ("VIN", "MQ-2 VCC (gas monitor)", "Power", "5 V heater supply"),
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
    ("/api/alerts/", "GET/POST", "List or create alerts (date range, type, status, camera and newest-N filters)"),
    ("/api/alerts/{id}/, /api/alerts/{id}/resolve/", "GET/PATCH, POST", "Read, update or resolve one alert"),
    ("/api/alerts/{id}/snapshot/", "GET", "Evidence frame of a camera alert; signed-in users only"),
    ("/api/alerts/simulate/", "POST", "Create a simulated alert (labelled)"),
    ("/api/v1/camera-events/", "POST", "Camera event with event_id; device token"),
    ("/api/v1/camera-activity/", "POST", "Badge sightings and idle start/end; device token"),
    ("/api/v1/camera-config/", "GET", "Alert rules and danger areas for this camera; device token"),
    ("/api/v1/camera-frames/ (+ /latest/)", "POST, GET", "Live-view JPEG from a camera (device token); latest frame for officers"),
    ("/api/v1/camera-counts/", "POST", "People in a camera's view, for zone head counts; device token"),
    ("/api/v1/cameras/, /api/v1/camera-map/ (+ /{id}/)", "GET, GET/PUT/DELETE", "Cameras with live status; site-map rows and Admin placement"),
    ("/api/v1/camera-areas/", "GET/POST/PATCH/DELETE", "Danger areas on camera pictures; Admins write"),
    ("/api/alerts/ingest/", "POST", "Legacy edge ingest; device token"),
    ("/api/workers/, /api/workers/{id}/", "GET/POST, GET/PUT/PATCH/DELETE", "Worker registry and vest assignment"),
    ("/api/workers/{id}/badge/", "GET/POST", "Read or reissue a worker's QR badge"),
    ("/api/v1/vests/, /api/v1/vests/{id}/", "GET/POST, GET/PUT/PATCH/DELETE", "Smart Vest records"),
    ("/api/v1/vests/telemetry/", "POST", "GPS, battery and SOS telemetry; vest or gateway token"),
    ("/api/v1/gas-monitors/ (+ /{id}/)", "GET/POST, GET/PATCH/DELETE", "Gas monitor registry: zone and map position"),
    ("/api/v1/gas-monitors/telemetry/", "POST", "Gas monitor reading; gas monitor token"),
    ("/api/v1/activity/ (+ /timeline/, /daily/, /summary/)", "GET", "Activity records, per-worker timelines and daily totals"),
    ("/api/v1/detections/", "GET/POST", "Detection records"),
    ("/api/v1/alert-config/", "GET/POST/PUT/PATCH/DELETE", "Alert rules: enabled, threshold, notify"),
    ("/api/v1/zones/ (+ /{id}/workers/, /{id}/check_point/)", "GET/POST/PUT/PATCH/DELETE", "Zones, assigned workers, point-in-zone test"),
    ("/api/v1/hot-work-permits/ (+ /{id}/revoke/)", "GET/POST/PUT/PATCH/DELETE", "Hot-work permits and revocation"),
    ("/api/v1/fcm-tokens/, /api/v1/fcm-tokens/{token}/", "POST, DELETE", "Register or remove a phone's push token"),
    ("/api/v1/reports/ (+ /generate/, /{id}/download/)", "GET, POST, GET", "List, generate (DOCX or PDF) and download reports"),
    ("/ws/dashboard/?token=<JWT>", "WebSocket", "Live alert, vest, gas monitor, worker, zone and camera events"),
    ("/ws/cameras/?token=<JWT>", "WebSocket", "Live camera frames for Safety Officers and Admins"),
]

TABLE_48 = [
    ("Table", "Key fields", "Relations / notes"),
    ("users", "id, email, full_name, role, is_active", "Roles: Admin, Safety Officer, Viewer"),
    ("service_tokens", "id, name, kind, key_hash, camera_ids, is_simulator, is_active", "Device tokens; only a hash of the key is stored"),
    ("workers", "id, name, role, zone_id, badge_code, last_seen_at, location_zone_id, location_at, is_active", "FK zones; badge_code is unique (QR payload); last located zone"),
    ("smart_vests", "id, vest_id, worker_id, battery_level, latitude, longitude, sos_active, sos_presses, last_seen", "One-to-one with workers; battery unknown until reported"),
    ("gas_monitors", "id, monitor_id, name, zone_id, latitude, longitude, gas_ppm, is_online, last_seen", "FK zones; its GAS alerts name the zone"),
    ("zones", "id, name, risk_level, boundaries, camera_ids, max_occupancy, camera_views_overlap", "Polygon boundaries and camera assignment (JSON); capacity state"),
    ("cameras", "id, camera_id, people_count, counted_at, latitude, longitude, heading, field_of_view, view_range_m", "Latest people count and site-map placement"),
    ("camera_areas", "id, camera_id, name, polygon, severity, is_active", "Danger areas; corners as fractions of the picture"),
    ("hot_work_permits", "id, zone_id, description, starts_at, ends_at, issued_by_id, revoked_at", "FK zones, users"),
    ("alerts", "id, alert_type, severity, source, worker_id, zone_id, camera_id, hot_work_permit_id, confidence, model_version, snapshot, event_id, is_resolved", "FK workers, zones (zone devices), permits; event_id unique for idempotent ingest"),
    ("alert_config", "id, zone_id, alert_type, is_enabled, threshold_seconds, notify_push, notify_email", "One rule per type and zone; SOS, FIRE and GAS always enabled"),
    ("activity_logs", "id, worker_id, zone_id, action, timestamp, metadata", "Check-in/out, idle and zone events at event time"),
    ("detections", "id, camera_id, worker_id, class_name, confidence, bbox", "FK workers"),
    ("reports", "id, report_type, file_format, date_from, date_to, includes_evidence, created_by_id", "FK users; stored before download"),
    ("fcm_tokens, user_preferences", "user_id, token, device_name / notify_push, notify_email", "FK users; push targets and opt-outs"),
]

TABLE_49 = [
    ("Component", "Technology", "Purpose"),
    ("Framework", "React Native 0.88 on Expo SDK 58 [@expo], TypeScript", "Android and iOS from one codebase"),
    ("Navigation", "Expo Router (file-based tabs and stack)", "Alerts, Map, Cameras, Workers and Settings tabs; alert and camera screens"),
    ("Map and overlays", "Leaflet 1.9.4 in react-native-webview; react-native-svg", "Same site map as the web; danger areas over the live picture"),
    ("State", "React context and reducers", "Live alert and worker state"),
    ("HTTP client", "fetch wrapper with single-flight token refresh", "REST calls; sign-out when renewal fails"),
    ("Live updates", "WebSocket with 4401 renewal, back-off and resync", "Same live stream as the web dashboard"),
    ("Push notifications", "expo-notifications 58.1 (FCM on Android)", "Alert delivery; tap opens the alert"),
    ("Secure storage", "expo-secure-store 58.0", "Tokens in the device keychain/keystore"),
    ("Quality checks", "jest-expo (25 tests), ESLint, TypeScript", "Run in CI"),
]

CHAPTER_4 = [
    ("h2", "4.1 Development Environment"),
    ("p", "Site-Safe was developed and measured on one Apple M4 laptop with 16 GB of memory running macOS; the versions in Table 4.1 were read from the project environments and lock files on 20 October 2026. The PPE model was trained on a Google Colab Tesla T4 GPU and the fire model on a Kaggle T4, because training on the laptop ran out of memory. A docker-compose file and a GitHub Actions workflow are written but have not yet been run."),
    ("table", "Table 4.1: Development Environment Summary", TABLE_41, [1.9, 1.5, 2.6], 8.5),

    ("h2", "4.2 QR Identification and Smart Vest"),
    ("h3", "4.2.1 QR Worker Identification"),
    ("p", "Each worker has a random badge code, created at registration and reissued from the Workers page, which prints a QR badge with the payload SSW1:<code> for the helmet. On the camera, identity.py decodes QR codes with OpenCV on the frames sampled for the person detector and associates each badge with the person box that contains it, following that person between samples by box overlap. A badge inside two person boxes, or two badges inside one box, is treated as unknown rather than guessed, so people standing close together are not misattributed."),
    ("p", "Alerts from a person with a known badge are attributed to that worker; others are marked as not identified. Sightings, repeated every 15 seconds while a badge stays in view, feed attendance (Section 4.7) and place the worker in the camera's zone (Section 4.4); unknown or revoked codes are ignored with HTTP 202 so that they cannot block a camera's queue. Reading range, angle and lighting have not yet been measured with printed badges, so the 5–10 metre range in Section 3.4.1 remains an assumption."),
    ("h3", "4.2.2 Smart Vest and Gas Monitors"),
    ("p", 'One ESP32 DevKit [@esp32] runs both field devices on the bench (Figure 3.6, Tables 4.2 and 4.3): the vest, with an SOS button (its NEO-6M GPS is not yet fitted), and a gas monitor, with an MQ-2 sensor [@mq2]; on a site they are separate boards. The firmware (firmware/smart_vest) raises SOS on a press, cancels it on a three-second hold and counts repeated presses; the monitor warms up, calibrates in clean air and estimates LPG-equivalent ppm. On the bench, each SOS alert was stored within a second, and lighter gas raised a zone GAS alert within one report.'),
    ("p", "The vest posts its position and SOS state to /api/v1/vests/telemetry/, or through a Mosquitto broker [@mosquitto] (Figure 4.8); a monitor posts its reading to /api/v1/gas-monitors/telemetry/, each with its own device token. A reading of 2,000 ppm or more, about a tenth of LPG's lower explosive limit, raises one critical GAS alert naming the monitor's zone, re-armed after a minute below it or once resolved. A labelled simulator drives both paths, excluded from attendance and reports."),
    ("table", "Table 4.2: Smart Vest and Gas Monitor Components", TABLE_42, [1.1, 1.3, 1.1, 1.1, 1.4], 9),
    ("table", "Table 4.3: ESP32 Pin Allocation", TABLE_43, [1.4, 1.7, 1.2, 1.7], 9),

    ("h2", "4.3 PPE Detection Module"),
    ("p", "The camera pipeline runs the PPE detector models/sitesafe_v5.pt, a YOLO11-medium model trained with Ultralytics [@ultralytics], on every frame. A YOLO11-nano detector pretrained on COCO [@coco] supplies person and vehicle boxes, and a YOLO11-nano pose model keypoints, each on every third frame; all read the same unannotated frame. Each missing-PPE box is tracked as one person's episode (ppe_episodes.py): duplicate boxes for one body part are merged, and each box is matched to its wearer through the person tracker. An episode alerts once after persisting for one second in at least three frames, and again only after 30 seconds unseen, so a flicker raises nothing and two people missing helmets raise two alerts. Every camera detector follows this pattern."),
    ("h3", "4.3.1 Dataset and Classes"),
    ("p", "The training data is the Roboflow dataset ppe-detection-qlq3d (CC BY 4.0) [@dataset]: 5,140 images in ten classes, helmet, vest, boots, gloves and goggles, each with a matching no- class, so that a violation is detected directly rather than inferred. It has no person or vehicle class, hence the second detector."),
    ("p", "The published split (Table 4.4) is not independent. The repository audit (audit_dataset.py) found 573 source groups and 30 groups of exact duplicates with members in more than one split, and 69 groups of identical images with conflicting labels. Test images therefore have near-copies in training, which inflates the scores below. A group-constrained re-split (3,598 / 771 / 771 images) has been generated but is held back until the label conflicts are resolved."),
    ("table", "Table 4.4: Dataset Split Configuration", TABLE_44, [1.3, 1.1, 1.2, 2.4], 9),
    ("h3", "4.3.2 Training Configuration"),
    ("p", "The model was fine-tuned from COCO-pretrained YOLO11-medium weights with the settings in Table 4.5, recorded in the exported run manifest, replacing an earlier nano model trained at 416 pixels (mAP@0.5 0.544). The team's Colab record shows early stopping after 102 of 150 epochs, with the best weights at epoch 77. Figure 4.1, drawn from the exported run, summarises the path from data to deployed weights."),
    ("table", "Table 4.5: YOLOv11 Training Hyperparameters", TABLE_45, [1.5, 2.2, 2.3], 8.5),
    ("fig", "fig_training_pipeline.png", 6.0, "Figure 4.1: PPE Model Training and Evaluation Pipeline"),
    ("h3", "4.3.3 Model Performance"),
    ("p", "On the held-out split the model reaches mAP@0.5 of 0.562 and mAP@0.5:0.95 of 0.345, with precision 0.467 and recall 0.728 (Table 4.6). Worn equipment is recognised reliably: helmet, vest and boots exceed 0.95. Missing equipment, the condition the system exists to detect, is recognised poorly (no-gloves 0.062, no-boots 0.130, no-helmet 0.309), because absence must be inferred and the negative classes are under-represented. Better data for these classes is the most valuable improvement, and the split leakage makes every figure an upper bound."),
    ("table", "Table 4.6: Per-Class Detection Performance", TABLE_46, [1.8, 1.4, 1.4, 1.4], 9),
    ("h3", "4.3.4 Fall Detection"),
    ("p", "Fall detection (fall_detection.py) runs its own pose model on every third frame, since neither the PPE nor the COCO detector gives keypoints. A posture counts as collapsed only when both signals of Section 3.3.5 agree: the confident keypoints form a box wider than tall, and the hips are at or below the knees. If either signal cannot be measured, for example with a leg out of frame, the result is not-collapsed, so missing data does not raise an alarm."),
    ("p", "People are tracked between samples by a confidence-weighted keypoint centroid, and a fall is confirmed after three continuous seconds of collapse; it raises one FALL alert and latches until the posture clears. Twenty-four tests cover the geometry and the tracker, and standing pedestrians in real photographs were read as not collapsed. The module has not been tested on fall footage, and its pixel geometry is uncalibrated per camera."),
    ("h3", "4.3.5 Fire and Smoke Detection with Hot-Work Permits"),
    ("p", "On the camera, fire_detection.py runs on every fifth frame and confirms fire or smoke only when it persists for two seconds with gaps of at most one second, ignoring specks below 0.05 percent of the frame; after an alert it latches until the scene has been clear for 30 seconds, so a fire raises one alert, not one per frame."),
    ("p", "Severity is set by the server (alerts/fire_policy.py) from hot-work permits, which safety officers issue for a zone and time window and can revoke. Without an active permit FIRE is CRITICAL and SMOKE HIGH; within one, FIRE is MEDIUM and SMOKE LOW, and the alert is linked to the permit. Unlike the suppression proposed in Section 3.3.6, a permitted flame is still stored and broadcast, so a spreading welding fire is not hidden, and FIRE cannot be disabled."),
    ("p", "The fire model is a two-class YOLO11-small detector trained on the D-Fire dataset [@dfire] on a Kaggle T4 GPU (early stop after 96 epochs, best at 76). On 4,294 held-out images it reached precision 0.775, recall 0.720 and mAP@0.5 of 0.787 (fire 0.726, smoke 0.848). The permit policy was verified end to end: a fire in a permitted zone became MEDIUM and linked, elsewhere CRITICAL. Video and hard negatives such as welding remain to be evaluated."),
    ("h3", "4.3.6 Camera Sources and Reliable Event Delivery"),
    ("p", "The camera source is a device index or a stream URL, so an RTSP camera, an NVR or a phone running an IP-camera application uses the same code path as a webcam, and up to 30 consecutive failed reads are tolerated before a stream counts as disconnected. Each pipeline has a camera identifier, and zones list their cameras, so each alert is attributed to a zone."),
    ("p", "Every event is first written to a local SQLite outbox under a unique event identifier and delivered in the background with back-off capped at 30 seconds, also after a restart. The server stores each identifier once (201 new, 200 duplicate, 202 type disabled) and dead-letters invalid events. Cameras use device tokens scoped to their identifier and read their rules and danger areas every 15 seconds, so dashboard changes apply without a restart."),
    ("p", "Each pipeline also sends its annotated view, up to five frames a second from a background thread that drops stale frames, for the live camera grid (FR-30). The API relays frames to Safety Officers' and Admins' sockets and keeps only each camera's latest frame for 30 seconds; live video is never recorded."),
    ("h3", "4.3.7 Vehicle Proximity Detection"),
    ("p", "Proximity uses the COCO detector's person and vehicle boxes. Without depth, the gap between a person box and a vehicle box is divided by the person's box height, making the threshold roughly scale-invariant (one person-height is about 1.7 metres at similar distances). Each tracked person has one encounter, confirmed after three samples near a vehicle with no gap over one second; it raises one alert, CRITICAL if the boxes overlap and HIGH otherwise, and ends after 15 seconds away from every vehicle."),
    ("p", "The first design re-armed whenever one sample missed the vehicle, limited only by a camera-wide 15-second cooldown: one worker beside a flickering car raised 14 alerts in three minutes, and two workers at risk shared one. Replaying the same detections, encounters cut a three-loop clip from 10 alerts to 2, one per person (Table 5.8). COCO has no forklift class, so plant is reported as a truck or car, and a worker in front of a distant vehicle is over-reported."),
    ("h3", "4.3.8 Danger Areas"),
    ("p", "Hazards smaller than a zone, such as a crane's swing radius, are drawn by Admins as polygons on a camera's live picture and stored as fractions of it (danger_areas.py). A person is inside when the bottom-centre of their box, their feet, lies in the polygon, so someone standing in front of an area is not flagged. One DANGER_AREA alert is raised per person per entry after one second inside, and again only after ten seconds outside; the camera fills an occupied area red. Areas can be switched off while the hazard is absent, from the web or the phone."),

    ("h2", "4.4 Backend Implementation"),
    ("p", "The backend is a Django 6 and Django REST Framework [@drf] application on PostgreSQL 18, served by Daphne so that REST and WebSocket traffic share one ASGI process through Django Channels [@channels]. Its five applications are accounts, alerts, workers, sitemap (zones and permits) and reports. Table 4.7 lists the endpoints, Table 4.8 the schema and Figure 4.2 the data model, drawn from the Django models."),
    ("p", "Users receive a 30-minute JWT access token and a refresh token, renewed silently, and Admin, Safety Officer and Viewer permissions are enforced on every endpoint. Producers use device tokens instead: only a hash of each key is stored, each has a kind and permitted cameras, and none can sign in, so no write endpoint is anonymous. The WebSocket requires a valid user token and an allowed origin and otherwise closes with code 4401, telling clients to renew and reconnect."),
    ("p", "Changes are broadcast after the transaction commits, so clients never see a rolled-back alert, through a Redis channel layer between processes. Alert rules set, per type and optionally per zone, whether an alert is enabled, its threshold and whether it notifies; SOS, FIRE and GAS cannot be disabled. Notifications go out after commit through Firebase Cloud Messaging [@fcm] and e-mail. A presence monitor marks vests offline after 120 seconds of silence and closes attendance sessions."),
    ("p", "Cameras also locate workers who wear no vest (workers/location.py): a badge sighting places the worker in that camera's zone, current for 60 seconds and then shown as last seen. Each camera reports how many people it sees, and a zone's head count is the larger of its identified workers and its cameras' counts, combined by the largest count when their views overlap, so nobody is counted twice. Over-capacity alerts use hysteresis, ten seconds over the limit to alert and sixty within it to re-arm, because head counts are noisy."),
    ("table", "Table 4.7: Core API Endpoints", TABLE_47, [2.5, 1.7, 1.8], 7.8),
    ("table", "Table 4.8: Database Schema Summary", TABLE_48, [1.15, 2.85, 2.0], 7.8),
    ("fig", "fig_erd.png", 6.0, "Figure 4.2: Entity Relationship Diagram"),

    ("h2", "4.5 Frontend Dashboard Implementation"),
    ("p", "The web command centre is a React 19 application built with Vite and Tailwind CSS, with routes for the dashboard, workers, incidents, vests, zones, reports and settings. Every dashboard figure comes from stored records; the seeded charts, vitals and compliance percentage of the earlier prototype were removed. A WebSocket adds and removes alerts live, and the client resynchronises after a reconnect."),
    ("p", "The Cameras page shows every camera's annotated live view to Safety Officers and Admins; Admins draw danger areas on its enlarged view (Figure 4.3, top). On the Zones page's Leaflet [@leaflet] map, Admins draw zone polygons with risk level, occupancy limit and cameras, issue hot-work permits, and place each camera with its direction, view angle and range. The dashboard repeats the site map with live head counts, vests and cameras, which turn red for a minute after an alert (Figure 4.3, bottom). The Workers page registers workers, assigns vests, prints badges and shows daily timelines."),
    ("p", "Reports are generated in DOCX or PDF for a period in the user's time zone and give counts, resolution times, violation-free days and attendance, each defined, but no compliance percentage, because the system records violations and not compliant observations, so no denominator exists. They can include the evidence frames of the most severe incidents, captioned, numbered and referenced from the incident log, and state how many incidents had no frame."),
    ("fig", "fig_web_interface.jpg", 5.0, "Figure 4.3: Web Command Centre: Live Camera with a Danger Area, and the Site Map with Cameras"),

    ("h2", "4.6 Mobile Application"),
    ("p", "The mobile application uses React Native 0.88 [@reactnative] on Expo SDK 58 [@expo] in TypeScript (Section 3.6). Expo builds Android and iOS clients without Xcode or Android Studio and supplies the FCM device token; the app uses the same REST API and WebSocket as the web dashboard."),
    ("h3", "4.6.1 Technology Stack"),
    ("table", "Table 4.9: Mobile Application Technology Stack", TABLE_49, [1.35, 2.5, 2.15], 8.5),
    ("h3", "4.6.2 Core Screens"),
    ("p", "After sign-in, five tabs follow (Figure 4.4). Alerts updates live; an alert shows its evidence frame, confidence and model version, links to its camera, and can be resolved by Safety Officers and Admins. Map shows the web's Leaflet site map in a WebView, so Android needs no map key. Cameras lists each camera's status and people in view; a camera's screen shows its live picture with danger areas outlined, and Admins can switch an area off. Workers shows presence and location, and Settings controls push. Reports, zone editing and worker registration stay on the web; the activity summary, rule configuration and shift scheduling of Figure 3.8 were not built."),
    ("fig", "fig_mobile_interface.jpg", 6.0, "Figure 4.4: Mobile Application: Alerts, Site Map, Camera and Alert Detail"),
    ("h3", "4.6.3 Push Notification Flow"),
    ("p", "On Android the app registers its FCM token after sign-in and removes it on sign-out, and tapping a notification opens the alert. Both sides are tested with a mocked FCM service, but delivery to a real phone needs a Firebase configuration and a development build and has not been verified; iOS relies on the live socket. Figure 4.4 comes from the app's web build, on which every screen was exercised against a test camera; the native map and overlay modules have not yet run on a phone."),

    ("h2", "4.7 Workforce Activity Monitoring"),
    ("p", "Inactivity tracking (inactivity.py) follows people between samples by centroid; a track that stays within a movement threshold for the timeout set in the dashboard rules raises one INACTIVITY alert and re-arms only after moving, and brief occlusions do not drop it. Displacement is in uncalibrated pixels."),
    ("p", "Identified workers get attendance automatically (workers/activity.py). The first evidence of a worker, a badge sighting or a vest report, checks them in; idle start and end come from the inactivity tracker; and after 30 minutes without evidence the presence monitor checks them out at the time they were last seen. Late events, such as those replayed from an outbox, are merged into their session. A timeline API gives per-worker daily intervals of presence and idleness, shown on the Workers page and in the report attendance tables."),
    ("p", "Twenty-three tests cover check-in, check-out, idleness and late events; an end-to-end run gave 60 minutes on site and 20 idle, identical in the timeline and the PDF. Records exist only for workers with a readable badge or a vest, and identities can swap when identified people cross."),

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
    ("p", "Each AI alert carries its evidence (FR-29): the confidence, the weights that produced it (file name and the first 12 hex digits of its SHA-256) and a JPEG of the unannotated frame that confirmed it, at most 640 pixels wide, sent with the event from the outbox. The server accepts a JPEG of up to 512 KB, stores it once per event and serves it only to signed-in users; snapshots can be switched off, and a daily command deletes them after a retention period (30 days by default) while keeping the alert."),
    ("fig", "fig_seq_camera_event.png", 6.0, "Figure 4.9: Camera Event to Dashboard Sequence"),

    ("h2", "4.11 Project Timeline"),
    ("p", "The final semester followed the completion plan: securing producers and live events, replacing fabricated dashboard data, worker, zone and breach features, QR identification, reports, the mobile application and the vest simulator, then PostgreSQL verification, CI, fire and smoke with permits, attendance and the Chapter 5 measurements. The final weeks merged the codebases, made PPE and proximity alerts per person after live runs, and added the camera features of Sections 4.3.6–4.3.8, cameras on the site map and report evidence, each verified with a test video and recorded in the traceability matrix."),
]

# ---------------------------------------------------------------- Chapter 5

TABLE_51 = [
    ("Suite", "Tests", "What it covers", "Result"),
    ("Backend (Django)", "270", "Roles and permissions; camera and vest ingest, device tokens and alert rules; unidentified people in restricted zones; vest SOS and zone gas monitors; alert evidence and retention; live camera view and camera map; camera location, head counts and capacity; danger areas; WebSocket authentication and broadcasts; workers, vests, badges, presence and breaches; activity and timelines; zones and permits; reports; demo site set-up", "Pass on SQLite and PostgreSQL 18"),
    ("Camera pipeline", "153", "PPE episodes and person association, QR identity and small-badge decoding, restricted-zone watcher, event outbox, alert evidence, fire confirmation, proximity encounters, danger areas, live view and people counts, inference configuration, activity events, dataset tools", "Pass"),
    ("Fire dataset preparation", "7", "Label remapping, video-grouped split, negatives, parquet unpacking", "Pass"),
    ("Report service (Node)", "25", "Metrics, evidence selection and image loading, DOCX and PDF rendering, attendance tables, pagination", "Pass"),
    ("Mobile app", "28", "API client and token refresh, push registration, live-state reducers, camera status, view cones, site-map data and messages, gas monitors on the map", "Pass; lint and type check clean"),
    ("Tools", "33", "Vest and gas monitor simulator, measurement statistics, tables and clip scoring", "Pass"),
    ("Vest and gas monitor firmware logic", "9", "MQ-2 gas estimate from the datasheet curve, SOS press, repeat and hold-to-cancel with debounce, vest and gas monitor JSON", "Pass; runs on the ESP32 (bench test)"),
    ("Web frontend", "—", "No unit tests; ESLint and production build", "Lint clean; build OK"),
    ("Total", "525", "", "All pass (4 Nov 2026)"),
]

TABLE_52 = [
    ("ID", "Requirement", "Evidence", "Status"),
    ("FR-01", "Sign-in and silent session renewal", "Account tests; browser: corrupted token renewed, requests retried", "Integrated"),
    ("FR-02", "Roles enforced by the API", "16 permission tests", "Tested"),
    ("FR-03", "UI shows only permitted actions", "Browser check as Safety Officer and Admin; Viewer not checked in the browser", "Integrated"),
    ("FR-04", "Detect missing PPE (10 classes)", "Held-out mAP@0.5 0.562 on a leaky split; no sealed target-camera set", "Coded"),
    ("FR-05", "One alert per person per violation episode", "31 tests; clip with 2 people without helmets gives 2 alerts; live webcam runs fixed duplicate-box and moving-head repeats", "Tested"),
    ("FR-06", "Falls from camera pose", "24 tests; no fall video evaluated", "Tested"),
    ("FR-07", "Worker-vehicle proximity", "18 tests; looped test clip 10 alerts to 2, one per person", "Tested"),
    ("FR-08", "Inactivity with dashboard-set timeout", "10 tests; rule polling tests", "Tested"),
    ("FR-09", "Fire/smoke with hot-work permits", "20 tests; model trained, held-out mAP@0.5 0.787; permit downgrade end to end", "Integrated (images only)"),
    ("FR-10", "QR worker identification", "21 tests; synthetic frames and a test video with a printed badge", "Integrated (test video)"),
    ("FR-11", "Reliable camera event delivery", "8 outbox tests; 100-event outage (Table 5.4)", "Integrated"),
    ("FR-12", "Only authorised devices submit data", "Ingest tests: anonymous, revoked, wrong-kind, wrong-camera tokens", "Tested"),
    ("FR-13", "Live updates for every change", "Realtime tests; two clients converge; browser", "Integrated"),
    ("FR-14", "Authenticated WebSocket (4401)", "Realtime tests for missing, bad and expired tokens and origin", "Tested"),
    ("FR-15", "Alert rules change runtime behaviour", "Ingest tests: disabled type, notify flags, SOS always on", "Tested"),
    ("FR-16", "Push notifications", "Mocked FCM and app registration tests; no phone yet", "Coded"),
    ("FR-17", "E-mail notifications", "Tests with a local mail backend", "Tested"),
    ("FR-18", "Worker registry in the UI", "7 tests; browser registration with vest", "Integrated"),
    ("FR-19", "Zones with polygons and cameras", "Zone tests; polygon drawn and saved in the browser", "Integrated"),
    ("FR-20", "Automatic breach and over-occupancy alerts", "20 tests; simulated telemetry, and a camera test video with unbadged people, end to end", "Integrated (simulated GPS, test video)"),
    ("FR-21", "Smart Vest GPS and SOS; zone gas monitors", "9 SOS and 15 gas monitor tests; bench test over Wi-Fi: SOS alerts and a zone GAS alert end to end", "Integrated on the bench; GPS not fitted"),
    ("FR-22, 23", "Telemetry validation; vest offline", "Validation and presence tests; browser occupancy timeout", "Tested; Integrated"),
    ("FR-24", "Activity history: check-in/out, idle", "23 tests; timeline and PDF agree end to end", "Integrated"),
    ("FR-25", "Incident list, resolve, export", "Browser: every filter, resolve broadcast, CSV export, responsive table", "Integrated"),
    ("FR-26", "Dashboard shows recorded data only", "3 tests; browser reconciliation", "Integrated"),
    ("FR-27", "DOCX and PDF reports", "19 tests; both types and formats end to end", "Integrated"),
    ("FR-28", "Mobile app", "25 tests; web build: alerts, map, cameras, live picture end to end", "Integrated on web; no device"),
    ("FR-29", "Alert evidence (snapshot, model version)", "30 tests; test videos and a live webcam: frame and model on web, mobile and reports", "Integrated (webcam)"),
    ("FR-30", "Live camera grid", "18 tests; test video and a webcam live at 5 frames/s; Viewer sees none", "Integrated (webcam)"),
    ("FR-31", "Camera-based location and head counts", "31 tests; badge clip places the worker; crowd clip head counts with hysteresis", "Integrated (test videos)"),
    ("FR-32", "Danger areas on the camera picture", "22 tests; area drawn live, alert with snapshot and badge within 15 s", "Integrated (test video)"),
    ("FR-33", "Cameras on the site map", "11 tests; placement; live, offline and alerting states; role checks", "Integrated (test video)"),
    ("FR-34", "Evidence snapshots in reports", "13 tests; incident PDF with 24 figures, safety DOCX by zone", "Integrated (test video)"),
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
    ("Device", "Run (UTC)", "Fire model", "Frames", "FPS", "Frame p50 (ms)", "Frame p95 (ms)", "Result (≥ 10 FPS)"),
    ("CPU", "20 Oct 11:52", "No", "150", "9.8", "80.4", "145.5", "Fail"),
    ("CPU", "20 Oct 12:15", "No", "150", "10.1", "82.1", "147.2", "Pass (marginal)"),
    ("CPU", "27 Oct 09:31", "Yes", "150", "10.2", "75.9", "157.6", "Pass (marginal)"),
    ("GPU (mps)", "20 Oct 11:51", "No", "300", "13.4", "52.1", "116.5", "Pass"),
    ("GPU (mps)", "20 Oct 12:14", "No", "300", "15.7", "46.4", "106.1", "Pass"),
    ("GPU (mps)", "27 Oct 09:30", "Yes", "300", "15.8", "54.4", "109.1", "Pass"),
    ("GPU (mps)", "27 Oct 09:31", "Yes", "300", "16.1", "54.0", "105.9", "Pass"),
]

TABLE_56 = [
    ("Duration", "Probes", "Missed", "p50 (ms)", "p95 (ms)", "Socket drops", "Forced reconnect (s)", "API memory (MB)"),
    ("5 min (validation, 20 Oct)", "146", "0", "35.9", "41.1", "0", "1.2", "63.6 → 91.6 (max 109.8)"),
    ("2 h (22 Oct)", "1,431", "0", "24.4", "39.7", "0", "1.1", "85.2 → 67.2 (max 141.1)"),
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
    ("20 Oct", "Alert evidence", "Snapshot sent through the outbox; one image stored, a replay stored none; frame and model version shown on web and mobile; retention removed the image and kept the alert", "Synthetic frame; no live camera run"),
    ("Earlier", "Proximity, real detector", "Still image: 4 people, 1 vehicle, CRITICAL alert stored and shown", "Still image only"),
    ("27 Oct", "Live camera grid", "Test video and the webcam live at 5 frames/s; 14 webcam alerts each with frame and model version; offline camera shown; Viewer saw no video", "Webcam; no site camera"),
    ("27 Oct", "Camera location and head counts", "Badge clip placed the worker in its camera's zone; one over-capacity alert per crowd period", "Test videos"),
    ("27 Oct", "Danger area", "Area drawn on the live view; alert with snapshot and badge holder; red fill and banner; Safety Officer read-only", "Test video"),
    ("27 Oct", "Cameras on the site map", "Placement; live, offline and alerting states; live thumbnail for officers, none for Viewers", "Test video"),
    ("27 Oct", "Report evidence", "Incident PDF with 24 captioned figures referenced from the log; safety DOCX by zone", "Test-video frames"),
    ("27 Oct", "Mobile map and cameras", "Map and live picture with area outline; an area switched off on the phone stopped at the camera within 15 s", "Web build at phone size"),
    ("1 Nov", "Unidentified person in a restricted zone", "Test video with badges on half the scenes: 14 breaches with snapshots, all from unbadged people; the badge holder was placed and not alerted", "Test video"),
    ("1 Nov", "Vest gas and SOS", "Messages generated by the vest firmware's code, sent with a vest key: one SOS and one GAS alert with position; gas shown in red on Vest Management", "No board yet"),
    ("4 Nov", "Smart Vest bench test", "ESP32 with the MQ-2 and SOS button over home Wi-Fi, a vest key: reports every 5 s accepted; each SOS alert stored within about 1 s of the press; a 3 s hold resolved it; unlit lighter gas read 2,500–10,000 ppm and raised GAS in the same report", "No GPS; one board on a bench"),
    ("4 Nov", "Gas monitor in a zone", "The same board as gas monitor GM-01 in zone North, with a gas monitor key: after warm-up, clean air read 3–5 ppm; unlit lighter gas read 2,041 ppm and raised a GAS alert for North, with no worker, in the same report", "One board on a bench"),
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
    ("One person got repeat PPE alerts: duplicate same-class boxes became separate episodes", "Live webcam run (55 s)", "Overlapping or nested same-class boxes merged; episode close time 10 s to 30 s"),
    ("A timeline test failed before noon: its shift was partly in the future", "Re-running the suite in the morning", "Test uses yesterday's shift"),
    ("A wearer's SOS cancel left the alert open; presses after a resolve raised nothing", "Vest bench test", "Cancel resolves the alert; every press is counted"),
    ("A new gas leak within a minute of a resolved GAS alert raised nothing", "Vest bench test", "The one-minute wait applies only while the alert is open"),
    ("The mobile app could not load alert snapshots: the API refused Accept: image/* with 406", "End-to-end check of the mobile web build", "The snapshot endpoint ignores the Accept header"),
    ("Every worker update closed dashboard sockets: a raw date-time in the payload", "Live camera-location run", "Times sent as ISO text; payload test"),
    ("A noisy head count raised 5 over-capacity alerts in 4 minutes", "Live crowd-video run", "Hysteresis: 10 s to alert, 60 s within the limit to re-arm"),
    ("One worker beside a flickering car raised 14 proximity alerts in 3 minutes", "Live danger-area run", "One encounter per person; camera-wide cooldown removed"),
    ("A different person at the same spot 14 s later was taken for a re-found one", "Replay of the 40-scene test video", "Re-finding limited to 5 s"),
    ("Every report downloaded under a generic file name", "Live report run", "The API exposes the file-name header to the dashboard"),
]

CHAPTER_5 = [
    ("h2", "5.1 Testing Approach"),
    ("p", "Testing was organised around the requirements traceability matrix in the repository, which links each functional (FR) and non-functional (NFR) requirement to its code, tests and evidence. A requirement's status rises through five levels: Coded, Tested (automated tests cover it), Integrated (verified end to end across running services), Physical (verified with real hardware or a real camera scene) and Accepted (agreed with the supervisor). No requirement has reached Physical or Accepted yet, and the acceptance targets are the team's proposals."),
    ("p", "Four kinds of evidence are used. Automated unit and integration tests run on every change. End-to-end exercises start the real services and drive them with real payloads: camera events, vest telemetry, browser sessions and app sessions. Measurement scripts in tools/measure/ produce the performance and reliability tables; each saves its raw results together with the machine, the git commit and its settings, and a table generator turns them into the tables below, so no number is copied by hand. Model evaluation uses Ultralytics on the held-out test split."),
    ("h2", "5.2 Test Environment"),
    ("p", "All tests and measurements ran on the development machine: an Apple M4 laptop with 16 GB of memory running macOS, with Python 3.14.3, Node.js 25.8.1 and PostgreSQL 18.3. The backend suite runs on both SQLite and PostgreSQL, because several defects appeared only on PostgreSQL (Table 5.8). Measurements used simulator device tokens, so their alerts are labelled SIMULATED and never reach reports, and no measurement yet crosses a network to a second device."),
    ("h2", "5.3 Automated Test Results"),
    ("p", "Table 5.1 lists the automated suites. All 525 tests passed when they were re-run for this report on 4 November 2026, up from 59 in the previous revision. Decision logic on the camera side (PPE episodes, fall, inactivity, proximity and fire confirmation) is kept free of OpenCV and model imports, which lets it run under the backend test command without a camera, a GPU or weights. The web frontend has no unit tests; its lint check and production build are run instead, and its behaviour was checked in the browser (Table 5.7)."),
    ("table", "Table 5.1: Automated Test Suites", TABLE_51, [1.35, 0.55, 3.0, 1.1], 8),
    ("h2", "5.4 Requirement-Linked Test Cases"),
    ("p", "Table 5.2 condenses the traceability matrix: each requirement, its evidence and the status reached, not rounded up. FR-04 (PPE detection) remains Coded although the model runs, because its criterion, event precision of at least 90 percent and episode recall of at least 85 percent, needs a sealed set from the target camera, which does not exist yet. FR-05 is Tested: live webcam runs found one person alerted repeatedly, because one body part came as overlapping boxes and a head moving towards the camera outran its episode; merging boxes and matching them to the tracked person fixed both on the recorded runs, but no annotated video has been scored. FR-30 to FR-34, added last, are Integrated on test videos or a webcam, not yet on a site camera."),
    ("table", "Table 5.2: Requirements, Evidence and Status", TABLE_52, [0.6, 1.75, 2.45, 1.2], 7.5),
    ("h2", "5.5 Model Evaluation Results"),
    ("p", "Table 4.6 gives the held-out results of the deployed YOLO11-medium weights: mAP@0.5 of 0.562, mAP@0.5:0.95 of 0.345, precision 0.467 and recall 0.728. Figure 5.1 sets each item beside its missing class: worn boots, helmets and vests exceed 0.95, while no-gloves (0.062), no-boots (0.130) and no-helmet (0.309) are weak. Figure 5.2 shows why at the pipeline's 0.15 threshold: 15 of 19 missing boots were read as boots, and 20 of 31 bare hands went undetected. As a missing item is the alert condition, the aggregate overstates usefulness. The fire and smoke model (Section 4.3.5) reached 0.787 on 4,294 held-out images, but not on video or against hard negatives such as welding."),
    ("fig", "fig_ppe_per_class_map.png", 5.6, "Figure 5.1: Per-Class mAP@0.5 of the PPE Model on the Held-Out Split"),
    ("p", "These figures are an upper bound for two reasons. First, the published split is not independent (Section 4.3.1): 573 source groups and 30 exact-duplicate groups span the training and test splits, so part of the test score measures recall of near-copies. Second, image-level mAP is not alert quality: an alert also depends on the grouping of detections per person, persistence and cooldown, none evaluated on video. A defensible claim needs the group-constrained re-split and, above all, sealed target-camera footage with hard negatives, scored per event."),
    ("fig", "fig_ppe_confusion_matrix.png", 4.6, "Figure 5.2: PPE Confusion Matrix on the Held-Out Split at Confidence 0.15"),
    ("h2", "5.6 Performance and Reliability Measurements"),
    ("p", "Tables 5.3 to 5.6 report the non-functional measurements. Each table states its sample size and settings, and every run is kept, including failures, so a result can be traced to the commit and machine that produced it."),
    ("p", "Latency (NFR-01): 100 camera events were posted every 0.2 seconds with a simulator token, and each event's time to reach an authenticated dashboard socket was recorded. All 100 arrived, with a 95th percentile of 41.6 ms against a proposed target of 2 seconds (Table 5.3). The dashboard can receive an event slightly before the camera receives its HTTP response, because the server broadcasts when the alert commits. The figure is for a single host; latency to a phone or a second computer on a LAN has not been measured."),
    ("table", "Table 5.3: Event-to-Dashboard Latency (NFR-01)", TABLE_53, [1.6, 0.6, 0.95, 0.95, 0.95, 0.95], 8.5),
    ("p", "Outage recovery (NFR-02): 100 events were sent while the API was unreachable for five minutes, simulated by switching off a proxy, and the camera's sender process was restarted midway. The target is that every event is stored exactly once within 60 seconds of the API returning. The first run stored all 100 exactly once but took 60.3 seconds, a failure caused by the 60-second retry ceiling; the ceiling was lowered to 30 seconds and two further runs recovered in 30.0 and 30.2 seconds with nothing lost or duplicated (Table 5.4)."),
    ("table", "Table 5.4: Outage Recovery, 100 Events over a 5-Minute Outage (NFR-02)", TABLE_54, [0.95, 0.75, 0.75, 0.75, 0.65, 0.5, 0.75, 0.9], 8),
    ("p", "Throughput (NFR-04): the full detector set was timed on the 517 test images at 1280×720, detection and decoding only, so camera frame rates are at most these figures. On the laptop GPU the pipeline reached 13.4 and 15.7 FPS against a target of 10, and 15.8 and 16.1 FPS once the trained fire model was added on 27 October; on the CPU it managed about 10 FPS, so the GPU became the default (Table 5.5). On the GPU the PPE model takes a median of 44.8 ms per frame, and the person/vehicle, pose, QR and fire stages 15–18 ms on the frames they run."),
    ("table", "Table 5.5: Inference Throughput with All Detectors (NFR-04)", TABLE_55, [0.8, 0.9, 0.55, 0.55, 0.45, 0.85, 0.85, 1.05], 8),
    ("p", "Soak (NFR-05): the stack ran for two hours on 22 October with the API, a camera pipeline and the presence monitor, a probe every five seconds and a forced disconnect (Table 5.6). None of 1,431 probes was missed, the 95th percentile stayed at 39.7 ms (Figure 5.3), there were no unexpected socket drops, and the client reconnected 1.1 seconds after the forced disconnect. API memory ended lower than it started (85 to 67 MB, peak 141 MB), so the rise seen in the five-minute validation run was warm-up, and NFR-05 is met on a single host."),
    ("table", "Table 5.6: Soak Validation Run (NFR-05)", TABLE_56, [1.0, 0.6, 0.6, 0.6, 0.6, 0.7, 0.85, 1.05], 8),
    ("fig", "fig_soak_latency.png", 5.6, "Figure 5.3: Event-to-Dashboard Latency over the Two-Hour Soak (NFR-05)"),
    ("h2", "5.7 End-to-End Verification"),
    ("p", "Table 5.7 records the end-to-end exercises, each against real running services. They show that the parts exchange real payloads correctly, but each has a stated boundary: the camera features used test videos rather than a site camera, and none used a phone receiving push or an assembled vest."),
    ("table", "Table 5.7: End-to-End Verification Record", TABLE_57, [0.6, 1.4, 2.5, 1.5], 7.8),
    ("h2", "5.8 Defects Found by Testing"),
    ("p", "Testing and measurement found the defects in Table 5.8 before they reached a demonstration. Three of them appeared only when the backend ran on PostgreSQL instead of the SQLite test database, which is why both now run, and two came from the measurements, which is why each measurement keeps its failed runs."),
    ("table", "Table 5.8: Defects Found by Testing", TABLE_58, [2.6, 1.6, 1.8], 8),
    ("h2", "5.9 Discussion and Threats to Validity"),
    ("p", "The software results are strong within their scope. Producers can no longer write anonymously, events survive outages and restarts exactly once, live updates reach clients in tens of milliseconds, and the attendance and report figures reconcile with the stored records. The detection results are weaker. The PPE model is good at confirming that equipment is worn and poor at noticing that it is missing, and the held-out score is inflated by the dataset split, so the system's core detection claim is the least proven part of the project."),
    ("p", "Several threats limit how far the results generalise. All measurements ran on one machine, so network effects are absent. Camera behaviour was exercised with test videos, a webcam, still images and injected events, not footage of a real site; QR range and real falls have not been measured, and fire detection only on images. Push to a phone and the containerised deployment are untested, the vest was only bench-tested, and the team set the targets. The evidence supports an integrated prototype whose software reliability is measured and whose detection accuracy must still be established in the field, not a production-ready system."),
]

# ---------------------------------------------------------------- Chapter 6

TABLE_61 = [
    ("Objective (Section 1.3)", "Delivered", "Evidence reached", "Outstanding"),
    ("1. PPE detection model", "YOLO11m, 10 classes, every frame; one alert per person per episode", "Offline evaluation, upper bound (mAP@0.5 0.562); live webcam runs", "Sealed target-camera set; data for negative classes"),
    ("2. QR worker identification", "Badges, decoding, attribution, zone placement", "Integrated on test videos", "Physical range, angle and lighting test"),
    ("3. Geofencing", "Map polygons; breach and capacity from GPS and cameras; danger areas on camera pictures", "Integrated with test videos and simulated GPS", "Real GPS; site cameras"),
    ("4. Web command centre", "Live dashboard, camera grid, site map with cameras, permits, reports with evidence", "Integrated in the browser", "Use on a site network"),
    ("5. Mobile application", "Alerts, resolve, workers, site map, cameras, push registration", "Integrated on the web build", "Android build and push delivery; rule configuration"),
    ("6. Workforce activity", "Inactivity, automatic check-in/out, idle, timelines", "Integrated with synthetic events", "Annotated real-camera scenario"),
    ("7. Incident logging and reports", "DOCX and PDF with defined metrics and attendance", "Integrated", "Supervisor sign-off on the metrics"),
    ("8. Smart Vest", "ESP32 vest (SOS; GPS supported), zone gas monitors, telemetry APIs, MQTT consumer, simulator", "Bench-tested on the ESP32 over Wi-Fi; GPS not fitted", "GPS module; field and battery tests"),
    ("9. Fall detection", "Pose geometry with 3 s persistence", "Tested", "Evaluation on fall video"),
    ("10. Fire and smoke detection", "Trained model, confirmation logic and permit policy", "Integrated; image-level evaluation (mAP@0.5 0.787)", "Evaluate on video with hard negatives"),
]

CHAPTER_6 = [
    ("h2", "6.1 Conclusion"),
    ("p", "This project set out to replace intermittent manual safety oversight on construction sites with a continuous, camera-first system that identifies the workers involved and keeps an auditable record, and the prototype does this end to end in software. Cameras run PPE, person and vehicle, pose, fire and QR models, watch danger areas drawn on their picture, place identified workers in zones, and post events with their evidence through an outbox that survives outages. A Django backend applies alert rules and hot-work permits, keeps attendance, notifies supervisors and produces DOCX and PDF reports, and web and mobile clients show the results live, with every camera on the site map."),
    ("p", "The measurements support the reliability of that software on a single host: a 95th-percentile event-to-dashboard latency of 42 ms, exactly-once delivery of 100 events across a five-minute outage with recovery in about 30 seconds, 16 frames per second for the full detector set on the laptop GPU, a two-hour soak without a missed probe, and 525 passing automated tests. They do not yet support a claim about detection accuracy on a real site. The PPE model recognises missing equipment poorly, its test score is inflated by a leaking dataset split, and fall, fire and QR detection have not been evaluated on real footage. Table 6.1 compares each objective with what was delivered."),
    ("h2", "6.2 Objectives and Outcomes"),
    ("p", "All ten objectives have working software. Eight are integrated or tested end to end, one (the PPE model) is evaluated offline only, and the Smart Vest of objective 8 is bench-tested without GPS. The remaining gaps are evaluation with real cameras and devices rather than missing features."),
    ("table", "Table 6.1: Objectives and Outcomes", TABLE_61, [1.35, 1.65, 1.5, 1.5], 7.8),
    ("h2", "6.3 Limitations"),
    ("p", "The main limitations follow from the evidence. Detection quality is bounded by a public dataset that does not represent the target cameras, and its split leaks. Proximity and inactivity are measured in pixels on uncalibrated cameras, danger areas assume people stand on the ground the area was drawn on, and a camera's cone on the map is entered by hand. Worker identity depends on a readable badge and can swap when identified people cross. A crash between storing an alert and sending its notification loses the notification, though not the alert. The system serves one site, the map needs internet access for its tiles, iOS receives no remote push, and all measurements come from one machine."),
    ("h2", "6.4 Future Work"),
    ("p", "The first priority is the data behind detection. The 69 conflicting label groups should be resolved so the group-constrained split can be used, footage should be collected from the target cameras with hard negatives and the weakest classes, per-class thresholds calibrated, and alerts scored per event and episode on a sealed set, which would also measure the episode tracking of FR-05 on video. The fire and smoke model should be evaluated on recorded clips, including welding and other hard negatives."),
    ("p", "The second priority is physical verification: a QR range and lighting test with printed badges, an Android development build receiving push notifications and showing the map and camera screens, latency to a second device over a LAN, a staged fall recording, and a run of the docker-compose deployment and the CI workflow. The measurement scripts already exist, so each of these is a matter of running them on the demonstration setup."),
    ("p", "Beyond the FYP, the vest and gas monitors can gain a LoRa link for sites beyond Wi-Fi range, a battery that reports its charge and a calibrated sensor, with field tests of range, delivery delay and battery life. Other extensions are a durable queue for notifications, alert-rule configuration in the mobile app, and support for more than one site."),
]

# ---------------------------------------------------------------- Appendices
# Long reference tables move here from Chapters 4 and 5 (the old caption is
# the key). The builder drops them from the chapters, renumbers the tables
# left behind and rewrites every reference in the text.

MOVED_TABLES = {
    "Table 4.7": "Table III.1",
    "Table 4.8": "Table III.2",
    "Table 5.2": "Table IV.1",
    "Table 5.7": "Table IV.2",
    "Table 5.8": "Table IV.3",
}

TABLE_I1 = [
    ("Task", "Role", "Steps"),
    ("Sign in", "All", "Open the dashboard address; enter e-mail and password. The session renews itself while in use."),
    ("Monitor the site", "All", "Dashboard: counts and charts from recorded data, live alerts, worker status and the site map with every camera."),
    ("Watch cameras", "Safety Officer, Admin", "Cameras: live view of every camera with its detections; click a camera to enlarge it."),
    ("Draw a danger area", "Admin", "Cameras → open a camera → Draw a danger area: click the corners where people stand, name it, choose a severity, Save area. On/Off and Delete beside each area."),
    ("Register a worker and print a badge", "Safety Officer, Admin", "Workers → Add worker: full name, trade, phone, assigned zone and smart vest. Edit the worker → Print badge; print at 100% (60 mm) and fix it to the helmet front. Reissue badge revokes earlier prints."),
    ("Follow a worker's day", "All", "Workers → open a worker → timeline of time on site and idle time for a chosen day."),
    ("Manage vests", "Safety Officer, Admin", "Vest Management: register a vest, assign it to a worker, see battery and online state."),
    ("Manage gas monitors", "Safety Officer, Admin", "Zones → Gas Monitors: register a monitor in a zone, pick its position on the map, see its reading and online state."),
    ("Draw a zone", "Admin", "Zones: draw the polygon on the map, then set name, risk level, maximum occupancy, cameras and whether their views overlap."),
    ("Place a camera on the map", "Admin", "Zones → Cameras → Place: click where it is mounted; set facing, view angle and range; Save position."),
    ("Issue a hot-work permit", "Safety Officer, Admin", "Zones → select the zone → Hot-work permits: description, start and end (up to 12 hours). Revoke ends it early."),
    ("Review and resolve incidents", "Safety Officer, Admin", "Incidents: filter by type, status and date; open an alert to see snapshot, confidence and model version; Resolve. Export CSV saves the list."),
    ("Generate a report", "Safety Officer, Admin", "Reports: choose incident or safety-performance report, period and DOCX or PDF; Include evidence snapshots adds the frames of the most severe incidents; Generate, then download."),
    ("Configure alert rules", "Admin", "Settings → Alert Configuration → edit a rule: enabled, threshold in seconds, push and e-mail. SOS, FIRE and GAS stay enabled."),
    ("Notifications and password", "All", "Settings → Notifications to opt out of push or e-mail; Settings → Profile to change the password."),
]

TABLE_I2 = [
    ("Task", "Steps"),
    ("Sign in", "Enter the server's address on the site network (for example 192.168.1.20:8000), e-mail and password."),
    ("See alerts", "Alerts tab: open or all alerts, updated live."),
    ("Resolve an alert", "Tap an alert to see its snapshot, confidence and model version; Resolve (Safety Officer and Admin)."),
    ("See the site map", "Map tab: zones with head counts, vests and cameras; tap a camera to open it."),
    ("Watch a camera", "Cameras tab → a camera: live picture with its danger areas (Safety Officer and Admin); Admins can switch an area off."),
    ("Check workers", "Workers tab: role, zone, vest and presence."),
    ("Receive push", "Android: allow notifications at first sign-in; tapping a notification opens the alert."),
    ("Sign out", "Settings tab → Sign out; the phone stops receiving push."),
]

TABLE_II1 = [
    ("Step", "Action", "Commands and notes"),
    ("1", "Prerequisites", "Python 3.12 or later, Node.js 18 or later, PostgreSQL 14 or later (18 used); Redis and Mosquitto for multi-process runs; a webcam or IP camera"),
    ("2", "Database", "Create user and database sitesafe in PostgreSQL"),
    ("3", "Backend", "cd backend; python3 -m venv .venv; pip install -r requirements.txt; cp .env.example .env and set SECRET_KEY and DB_*; python manage.py migrate; python manage.py createsuperuser; daphne -b 127.0.0.1 -p 8000 sitesafe.asgi:application"),
    ("4", "Background jobs", "python manage.py run_mqtt_consumer; python manage.py run_presence_monitor; schedule python manage.py purge_alert_snapshots daily"),
    ("5", "Report service", "cd report-service; npm ci; DJANGO_API_URL=http://localhost:8000/api/ npm start (port 3001)"),
    ("6", "Web dashboard", "cd frontend; npm install; npm run dev; open http://localhost:5173 and sign in"),
    ("7", "Camera token", "python manage.py create_service_token CAM-01 --kind CAMERA --camera-id CAM-01 (the key is shown once)"),
    ("8", "Camera pipeline", "cd ai-module; pip install -r requirements-vision.txt; copy the weights to models/sitesafe_v5.pt; SITESAFE_DEVICE_KEY=<key> python inference.py --camera-id CAM-01 --source <device or stream URL>. Keys: Q quit, P pause, S test alert"),
    ("9", "Mobile app", "cd mobile; npm ci; npx expo start; sign in with the server's LAN address. Push needs a Firebase project and an Android development build"),
    ("10", "Vest and gas simulator", "python manage.py create_service_token vest-sim --kind VEST_GATEWAY --simulator; the same with gas-sim --kind GAS_MONITOR; SITESAFE_DEVICE_KEY=<vest key> SITESAFE_GAS_MONITOR_KEY=<gas key> python tools/vest_simulator.py tools/vest_scenarios/demo.json --speedup 5"),
    ("11", "Docker (alternative)", "cp .env.docker.example .env.docker; docker compose --env-file .env.docker up --build (dashboard on port 8080, API on 8000); not yet run"),
    ("12", "Demo site", "python manage.py setup_demo: demo accounts, zones, workers with badges, vests, a gas monitor, device keys and a placed camera, no alerts; docs/DEMO_SCRIPT.md walks through a demonstration"),
]

APPENDICES = [
    ("I", "User Manual", [
        ("p", "This appendix explains how each role uses Site-Safe once it is installed (Appendix II). The web command centre is used for set-up and monitoring (Table I.1) and the mobile app for responding on site (Table I.2). Controls appear only for the roles that may use them. The full manual, with screenshots, is docs/USER_MANUAL.md in the repository."),
        ("table", "Table I.1: Web Command Centre Tasks", TABLE_I1, [1.45, 1.1, 3.45], 8.5),
        ("table", "Table I.2: Mobile Application Tasks", TABLE_I2, [1.45, 4.55], 8.5),
    ]),
    ("II", "Installation and Setup Guide", [
        ("p", "Table II.1 brings up the system on one computer, as used for the measurements in Chapter 5. The repository README describes every option and environment variable."),
        ("table", "Table II.1: Setup Steps", TABLE_II1, [0.45, 1.25, 4.3], 8),
    ]),
    ("III", "API and Database Reference", [
        ("p", "Tables III.1 and III.2 list the backend's endpoints and database tables described in Section 4.4; Figure 4.2 shows their relations."),
        ("table", "Table III.1: Core API Endpoints", TABLE_47, [2.5, 1.7, 1.8], 7.8),
        ("table", "Table III.2: Database Schema Summary", TABLE_48, [1.15, 2.85, 2.0], 7.8),
    ]),
    ("IV", "Test Evidence", [
        ("p", "Tables IV.1 to IV.3 give the evidence summarised in Chapter 5: the status reached by each functional requirement, the end-to-end verification record and the defects found by testing."),
        ("table", "Table IV.1: Requirements, Evidence and Status", TABLE_52, [0.6, 1.75, 2.45, 1.2], 7.5),
        ("table", "Table IV.2: End-to-End Verification Record", TABLE_57, [0.6, 1.4, 2.5, 1.5], 7.8),
        ("table", "Table IV.3: Defects Found by Testing", TABLE_58, [2.6, 1.6, 1.8], 8),
    ]),
]
