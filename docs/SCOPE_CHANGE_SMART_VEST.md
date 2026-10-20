# Scope change request: Smart Vest hardware

**Project:** Site-Safe: AI-based construction site safety monitoring
**Students:** _[names, roll numbers]_
**Supervisor:** _[name]_
**Date submitted:** _[date]_

## 1. Request

We ask approval to move the **physical Smart Vest hardware** (ESP32, GPS module, SOS button and LoRa link) out of the FYP-II deliverables and into future work. All other objectives stay in scope.

The affected commitment is report §1.3, objective 8: *"Build a lightweight IoT Smart Vest with GPS tracking and an SOS panic button to provide supplementary worker location data and emergency alerts in areas outside camera coverage."* It is also described in §3.4.2, §3.4.3 and §4.2.

## 2. Reasons

- **The vest is supplementary by design.** Report §3.4.2 calls it a gap-filler for areas cameras cannot see. The primary safety functions are camera-based and complete: PPE detection, fall detection, vehicle proximity, inactivity and QR worker identification.
- **There is no hardware budget or lab access in the time left.** The parts must be bought in stages. The radio band for LoRa transmission in Pakistan must be confirmed with the university lab before any purchase. Assembly, power design and field range testing would take time away from evaluation and the report, which carry more marks.
- **The software side of the vest is already built and tested.** Only the physical device is missing (see §3).

## 3. What remains delivered

The full software path a vest would use is implemented, tested, and demonstrated with a clearly labelled simulator:

| Capability | Status |
|---|---|
| Authenticated vest gateway ingest (HTTP and MQTT) with payload validation | Implemented, automated tests |
| SOS → critical alert → web dashboard, mobile app and notifications in real time | Implemented, automated tests |
| GPS position → zone entry/exit history | Implemented, automated tests |
| Automatic restricted-zone and over-capacity breach alerts from GPS | Implemented, automated tests |
| Vest offline detection when reports stop | Implemented, automated tests |
| Live vest positions on the site map; vest presence in web and mobile apps | Implemented, browser-tested |
| Vest simulator that drives the real gateway API; its events are marked "Simulated" and excluded from report figures | Implemented |

A physical vest only needs to send the same JSON telemetry to the existing gateway endpoint.

## 4. What will be stated in the report

- §1.3 objective 8 and §1.4 scope will say the vest hardware was moved to future work by this approval, and keep the software support as delivered.
- §3.4 and §4.2 will describe the vest interface and the simulator, and will not claim a built device. Figure 4.1 and Tables 4.2/4.3 will be labelled as the proposed hardware design.
- Chapter 5 will report only simulator-driven tests for vest features, labelled as such. No GPS accuracy, battery life or LoRa range figures will be claimed.
- Chapter 6 future work will list: assembling the ESP32/GPS/SOS vest, a point-to-point LoRa link to a USB receiver and MQTT bridge, and field tests of range, delivery delay and battery runtime.

## 5. Approval

| | Name | Signature | Date |
|---|---|---|---|
| Supervisor | | | |
| Project coordinator (if required) | | | |

_Decision:_ ☐ Approved ☐ Approved with changes: ______ ☐ Not approved
