# Site-Safe Demonstration Script

A 12-minute live demonstration for the final evaluation, with a rehearsal checklist, the order of the demonstration, what to say at each step, fallbacks, and likely questions. Everything shown comes from the running system. The camera is a real webcam, and the vests come from the vest simulator, which marks its data as simulated; say so when you show them.

How to use each screen is in the [user manual](USER_MANUAL.md). Installation is in the [README](../README.md).

## Kit

- The laptop with the project, its virtual environments installed, and the model weights in `ai-module/models/`.
- The laptop's webcam (or a USB webcam), with camera permission granted to the Terminal you start the camera from (macOS: System Settings → Privacy & Security → Camera).
- A printed QR badge for **Ali Raza (demo)**, at least 8 cm wide (Workers → Edit → Print badge).
- A hard hat and a hi-vis vest, to show a violation and then compliance. Without them, show the violation only.
- A phone with the Site-Safe app (Expo Go, or a development build for push), on the same Wi-Fi as the laptop.
- Internet access for the map's base layer. Without it the map shows zones, vests and cameras on a plain background.
- Two browser windows: the dashboard signed in as **demo-officer**, and a second as **demo-admin** for drawing.

## The day before: set up and rehearse

1. **Use a separate demo database**, so demo data never mixes with development data:

   ```bash
   createdb sitesafe_demo
   cd backend
   DB_NAME=sitesafe_demo python manage.py migrate
   DB_NAME=sitesafe_demo python manage.py setup_demo
   ```

   `setup_demo` creates three accounts (demo-admin, demo-officer, demo-viewer), the zones **Site** and **Crane**, three workers with QR badges, vests VEST-001 and VEST-002, camera **CAM-01** placed on the map, a camera key and a vest-simulator key. It creates no alerts. **Store the passwords and keys it prints**; they are shown only once. Run it again at any time: it keeps what exists. To start the demo database afresh, drop and recreate it.

2. **Start everything** (see *On the day*) and sign in on the dashboard and the phone.
3. **Print Ali Raza's badge** from the Workers page.
4. **Draw the demo danger area once to rehearse:** start the camera, open Cameras → CAM-01 as demo-admin, and draw an area over a patch of floor you can step into (for example the floor in front of the desk). Check that standing in it raises a Danger area alert. Delete it afterwards, so you can draw it live on the day.
5. **Record a fallback clip** of the rehearsal: stand without a hard hat, show the badge, step into the floor area, then put the hard hat on.

   ```bash
   python tools/measure/record_clip.py --out tools/measure/results/clips/demo_fallback.mp4 --seconds 60
   ```

6. Generate one **Incident Report** with snapshots, to check the report service. Then run the whole script once against the clock.

## On the day: start-up (15 minutes before)

Run each of these in its own terminal from the project root, with `DB_NAME=sitesafe_demo` exported in every backend terminal.

| # | What | Command |
|---|---|---|
| 1 | API (on the network, for the phone) | `cd backend && daphne -b 0.0.0.0 -p 8000 sitesafe.asgi:application` (add the laptop's IP to `ALLOWED_HOSTS`) |
| 2 | Presence monitor (exits, head counts, offline vests) | `cd backend && python manage.py run_presence_monitor` |
| 3 | Report service | `cd report-service && DJANGO_API_URL=http://localhost:8000/api/ npm start` |
| 4 | Dashboard | `cd frontend && npm run dev` |
| 5 | Camera CAM-01 (webcam) | `cd ai-module && SITESAFE_DEVICE_KEY=<demo-cam-01 key> python inference.py --camera-id CAM-01` |
| 6 | Vest and gas simulator (start it during step 6 of the demonstration) | `SITESAFE_DEVICE_KEY=<demo-vest-gateway key> SITESAFE_GAS_MONITOR_KEY=<demo-gas-monitor key> python tools/vest_simulator.py tools/vest_scenarios/demo.json --api http://127.0.0.1:8000/api` |

Then:

- Open the dashboard as demo-officer.
- Open the phone app, signed in as demo-officer with the server address `<laptop IP>:8000`.
- Check that the dashboard shows CAM-01 **Live** on the Cameras page, and that the phone shows the green **Live** dot.
- Resolve any alerts left over from setting up, so the feed starts clean.

## The demonstration (about 12 minutes)

| Time | Show | Do | Say |
|---|---|---|---|
| 0:00 | Dashboard | Point to the four figures, Worker Status and the Alert Feed. Scroll to the Site Map. | "Site-Safe turns cameras and vests into live safety alerts, for the office and for supervisors on site. This is a demo site: one real camera, and two vests from our simulator." |
| 1:00 | Cameras → CAM-01 | Stand in front of the webcam **without a hard hat**. | "Every frame goes through our PPE model. A missing item has to persist for a second on the same person before it alerts, so a flicker never does." |
| 1:30 | Alert Feed and phone | A PPE violation appears on the dashboard and the phone at once. Open it on the dashboard: evidence frame, model version, "Worker not identified". | "The alert carries the frame that caused it and the exact model version, so it can be checked later." |
| 2:30 | Badge | Hold the badge to the camera. The next alert names **Ali Raza (demo)**, and his card reads "In Site · CAM-01". Put the hard hat on; no new helmet alert follows. | "Workers are identified by a printed QR badge with a random code, no personal data. The camera also places him in its zone without any GPS." |
| 3:30 | Danger area (demo-admin window) | On Cameras → CAM-01, choose **Draw a danger area**, click four corners around the floor patch, name it "Loading bay edge", CRITICAL, **Save area**. | "Supervisors mark hazards on the picture itself: a crane swing, an excavation edge. We check where a person's feet are, not their whole body." |
| 4:30 | Step in | Wait about 15 s for the camera to pick up the area, then step into it. The area fills red, the banner reads DANGER AREA, and a Critical alert arrives on the dashboard and the phone. | "One alert per entry: standing there does not repeat it." |
| 5:30 | Site map | Scroll to the Site Map. CAM-01 is **red and pulsing** for a minute; its cone shows what it covers. Click it: live picture, people in view, latest alert. | "Every camera is on the site map with what it sees." |
| 6:30 | Phone | Cameras → CAM-01: live picture with the area outlined. Switch the area off (as demo-admin on the phone, or say an Admin can). | "On site, a supervisor can switch a hazard off when it is not there, for example while the crane is parked." |
| 7:30 | Vests and gas | Start the simulator (terminal 6). VEST-001 walks the site; VEST-002 walks into **Crane** (restricted), stops and presses **SOS**; gas monitor GM-01 in **Site** reports a leak (2,800 ppm) after 40 s and the zone turns red. Then, with the real board switched on for at least two minutes in clean air, press its SOS button and hold an unlit lighter near its gas sensor for a second. | "These are simulated, labelled Simulated and never counted in reports. This is the real prototype: one ESP32 running as a vest (SOS button) and as a gas monitor fixed in a zone (MQ-2 sensor), sending the same messages over Wi-Fi. One press raises SOS; a three-second hold cancels it. Gas is a hazard of the place, so the gas alert names the zone, not a worker." |
| 8:30 | Breach and SOS | A Zone breach, then an SOS, arrive on the dashboard and the phone. The vest dot turns red on the map. Resolve the SOS from the phone; it clears on the dashboard. | "Anyone can resolve it from where they are, and everyone sees it at once." |
| 9:30 | Reports | Reports → Incident Report, PDF, **Include evidence snapshots**, Generate. Open it: summary, Evidence pages, then the log's Figure column. | "Reports carry the evidence, and they say what is missing rather than hiding it." |
| 11:00 | Close | Open `docs/REQUIREMENTS_TRACEABILITY.md`. | "Every requirement maps to code, tests and the evidence of how far it was verified, including what still needs real hardware. Every automated test passes (NFR-07 gives the count)." |

## Fallbacks

| If… | Then |
|---|---|
| The webcam does not open | Stop terminal 5 and play the rehearsal clip: `python inference.py --camera-id CAM-01 --source ../tools/measure/results/clips/demo_fallback.mp4 --loop`. Say it is the recording from the rehearsal. |
| The badge is not read | Move closer, hold it flat towards the camera, check the light. Continue: the alert still arrives as "not identified". |
| The danger area does not trigger | Check it is switched on and drawn where your feet are, and that 15 s have passed since saving. |
| There is no internet | The map has no base layer; zones, vests and cameras still show. Explain why. |
| The phone shows Offline | Check it is on the same Wi-Fi and the API runs on `0.0.0.0`. Use the dashboard for that step. |
| A push does not arrive | Pushes need the development build and Firebase. The app still receives alerts live while open; show that. |
| Something else fails | Use the Event Simulator on the dashboard (it raises alerts marked SIMULATED) to keep going, and say so. |

## Likely questions

- **How accurate is the PPE model?** Overall mAP@0.5 is 0.562 on the held-out test set, from strong (helmet 0.958, vest 0.962) to weak (gloves 0.276, no-gloves 0.062). The weak classes and the split-leakage caveat are in Chapter 5. The fire and smoke model reached mAP@0.5 0.787.
- **How fast is it?** p95 event-to-dashboard latency was 42 ms on one machine. The pipeline runs at 13–16 FPS on the laptop GPU with all detectors. The measurements are in `docs/evidence/CHAPTER5_MEASUREMENTS.md`.
- **What if the network drops?** Camera events go into a local outbox and are delivered when the API returns, without duplicates (NFR-02).
- **How do you stop alert floods?** Each detector raises one alert per person per episode, then waits for the condition to clear; see the README table "When a camera raises an alert".
- **What about privacy?** Live frames are never stored. Evidence frames expire after the retention period. Badges carry random codes. Reports can leave snapshots out, and only Safety Officers and Admins see pictures.
- **What is not finished?** The physical vest, push on a real phone, a real-site camera recording, and a phone check of the new map screens. These are listed in `docs/PENDING_FOR_YOU.md` and marked in the traceability matrix.

## Afterwards

Stop the camera and the simulator. The demo database keeps the run's alerts; to start the next rehearsal clean, drop and recreate `sitesafe_demo` and run `setup_demo` again.
