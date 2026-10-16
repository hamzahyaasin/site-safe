# Site-Safe economical hardware and purchasing plan

Prepared 13 October 2026. No dedicated project hardware is currently owned; budget is economical with no fixed demo date. Reuse access to the existing development computer, borrow test equipment where possible, and purchase in stages. No prices, local stock, exact radio band or supplier authenticity are verified by this plan.

## 1. What is actually needed

The core web/AI software can be developed with recorded videos before purchasing electronics. A physical demo needs a camera. Delivering the currently promised full hardware scope additionally needs one GPS/SOS vest transmitter and a receiver that forwards messages to the backend. The mobile objective needs access to a real test phone; it does not necessarily require buying one.

| Item | Economical starting quantity | Purpose | Purchase decision |
|---|---:|---|---|
| Existing development computer and charger | 1 | Django/PostgreSQL, dashboard, inference, reporting, broker/gateway | Reuse first; benchmark before buying compute. |
| USB camera, preferably 1080p capture, with stable mount | 1 | Physical PPE/pose/QR and camera-zone demo | First dedicated camera purchase if one cannot be borrowed. Focus/readability at the working distance matters more than headline resolution. |
| Phone with camera/network access | Borrow 1 | Physical mobile app and push tests; may also supply a second camera stream | Borrow first. A single phone cannot always conveniently serve both demo roles simultaneously. |
| Local Wi-Fi router/access point | Reuse/borrow 1 | Computer, phone and any IP camera connectivity | Buy only if existing LAN access is unsuitable. |
| Helmet, reflective vest, goggles, gloves and boots | Borrow 1 set; preferably 2 people for tracking tests | Controlled compliant/noncompliant PPE examples | Borrow real examples; do not buy only miniature props and claim real-worker validation. |
| Printed QR labels/cards and matte covers | Several | Worker identification and reassignment tests | Ordinary printing initially; test size and placement before durable labels. |
| Second video source | Borrow or recorded stream initially | Multi-camera attribution/recovery tests | Buy a second camera only if required by acceptance results. |
| External storage | Existing capacity first | Video, annotations, checkpoints and evidence | Add only after measuring dataset/storage needs. |

“1080p” is a capture starting point, not a guarantee that small gloves/goggles or distant QR codes are readable. Collect representative frames before committing to lens, mounting distance or camera quantity. An IP camera is useful later for RTSP testing; no NVR is necessary for the first prototype.

## 2. One complete LoRa vest prototype: bill of materials

Default design: ESP32 + GNSS + SOS on the vest, one matching LoRa receiver connected by USB to the development computer. The computer runs a bridge and MQTT broker. Choose either discrete boards or integrated ESP32/LoRa boards; do not purchase both sets unnecessarily.

| Component | Quantity | Notes |
|---|---:|---|
| ESP32 development board | 2 | One wearable controller and one receiver controller. ESP32-DevKitC-class boards are a practical documented option. Exact board revision determines wiring and available pins. |
| Compatible LoRa radio breakout/module | 2 | One at each end. SX1262-class radios are an example, not a finalized regional SKU. Both breakouts must support the selected band, interface/library and antenna configuration. |
| Correct-band antennas with matching connectors | 2 | Order with the radio modules; identify antenna and connector type explicitly. |
| GNSS breakout with antenna | 1 | UART output, documented logic/supply levels, fix status. A u-blox M10-based breakout is one example; choose an affordable documented equivalent if needed. Buy a breakout, not a bare surface-mount chip. |
| Momentary SOS pushbutton | 1, plus spare if inexpensive | Accessible mounting, debounce and acknowledgement indication. |
| Status LED plus resistor; buzzer if useful | 1 set | Distinguish powered, connected, event pending and acknowledged. Use appropriate driver components for the selected buzzer. |
| USB data cables | 2 | Must support data for flashing/serial reception, not charge-only cables. |
| Breadboard, jumper wires and basic passives | 1 set | Bench bring-up; later replace loose wiring for the wearable demo. |
| USB power bank | 1 | Simple first wearable power source; test that it does not shut off at low load. Avoid custom battery/charger design initially. |
| Regulated USB supply for receiver | 1 if not powered from computer | Normally the receiver is powered via its USB connection. |
| Small enclosure/pouch, mounting/strain relief | 1 set | Buy after board dimensions and working wiring are known. |
| Multimeter | Borrow 1 | Voltage, continuity and power troubleshooting. |
| Soldering tools/perfboard/connectors | Borrow tools; 1 material set | Only after the bench circuit is working. |
| Battery measurement circuit/fuel gauge | Conditional, 1 | Only if genuine percentage/voltage reporting is retained. Select around the actual battery system; a USB power bank generally does not expose cell state automatically. Otherwise report battery as unknown. |

Manufacturer references: [Espressif DevKitC guide](https://documentation.espressif.com/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html), [Semtech SX1262](https://www.semtech.com/products/wireless-rf/lora-connect/sx1262), [u-blox MAX-M10 series](https://www.u-blox.com/en/product/max-m10-series?legacy=Current). These establish component families/interfaces, not a drop-in wiring design or local availability.

An integrated ESP32/LoRa development board can replace one ESP32 plus one radio breakout per endpoint. If its total local price and documentation are better, use two matching integrated boards, one GNSS breakout, and the remaining listed parts.

## 3. Hardware decisions before ordering

- **LoRa versus LoRaWAN:** the economical plan uses a private point-to-point LoRa link and a USB receiver/bridge. A full LoRaWAN design needs the appropriate gateway/network-server architecture; one ordinary radio receiver is not a full LoRaWAN gateway. Confirm the approved project wording before choosing. See [LoRa Alliance backend architecture](https://resources.lora-alliance.org/document/lorawan-back-end-interfaces-v1-0).
- **Radio band and module variant:** this review did not verify a current applicable Pakistan operating band/power authorization from the primary regulator documents. Have the university lab/supplier confirm the current PTA/FAB requirements and exact matching module/antenna variants before buying/transmitting. Do not choose 433/868/915 MHz merely because a listing is cheap.
- **Electrical compatibility:** check breakout supply, I/O levels and current requirements against exact datasheets. A bare GNSS/radio chip and a regulated breakout can have different requirements. ESP32 GPIO wiring must match the selected board; do not reuse an unverified report pin table.
- **Power:** begin with the manufacturer's supported USB power path. Do not simultaneously feed alternative power inputs unless explicitly supported by that exact board. Add custom battery electronics only after measured power requirements justify it.
- **GNSS limits:** validate outdoors and report fix age/quality. Use sufficiently broad test zones and handle uncertainty near boundaries. Do not promise precise indoor positioning; indoor camera zones should use image coordinates.
- **Radio link:** send only small telemetry/SOS messages. Camera video remains USB/IP. Measure actual packet-loss and range conditions; there is no guaranteed kilometre-range claim in this plan.

## 4. Compute and storage

Start on the computer already used for development. As engineering planning targets, 16 GB RAM is a reasonable starting point for a modest one-camera setup, with 32 GB providing more room for concurrent services and models. These are not measured minimum requirements or throughput guarantees. Model choice, resolution, frame sampling and video decoding determine capacity.

Use available CPU or supported Apple-silicon acceleration for development and benchmark the actual inference path. The current script needs explicit device/configuration verification. Ultralytics documents CPU, CUDA and Apple MPS device options, but that does not establish this project's frame rate: [training/device documentation](https://docs.ultralytics.com/modes/train).

Do not buy a GPU just to repair the dataset or write the system. Use available university/shared/cloud GPU access for controlled training after the data gate passes. If GPU access is paid, budget it separately and obtain authorization. The existing export records a T4 training run, but new data/model settings may need a different batch size or resource budget.

If the final all-model one-camera benchmark misses acceptance targets, first profile capture, inference cadence, resolution and model size. Then evaluate borrowed GPU hardware before a purchase. A Raspberry Pi or ESP32 is not the proposed host for the complete current multi-model vision stack.

Storage planning: recorded video dominates. For one stream at a measured bitrate of B megabits/second over H hours, decimal storage is approximately `0.45 × B × H` GB, before redundancy/checkpoints. At 4 Mbps, 10 hours is approximately 18 GB. Measure the actual camera bitrate and retain only authorized evidence needed for evaluation.

## 5. Purchase in stages

### Stage A — Start software and data collection

Reuse the computer, LAN and storage; borrow a phone/PPE; acquire one mounted USB camera if needed. Start phases 00–06 using controlled recordings and explicit simulators where hardware is pending. Measure QR readability and model speed now.

**Spend gate:** representative capture works and the selected camera can see the relevant body regions/QR at the planned distance. Do not buy extra cameras to solve an unmeasured modeling problem.

### Stage B — Build the vest on the bench

Buy the two controller/radio endpoints, matched antennas, one GNSS breakout, button, cables and breadboard parts after selecting the exact variants. Use USB power. Claude prepares component tests and firmware; the team connects and verifies each device.

**Spend gate:** serial output, GNSS outdoors, SOS press and point-to-point radio reception each work independently, then together.

### Stage C — Make the prototype wearable

Add power bank, enclosure, secured wiring and genuine power measurements. Integrate broker/backend/web/mobile and test real message loss/recovery. Add a battery measurement accessory only if the selected power architecture supports it and the requirement remains.

**Spend gate:** complete actual SOS/GPS path works and repeated operation is stable. This is the first stage at which the vest can be described as physically implemented.

### Stage D — Buy only proven gaps

A second camera, dedicated receiver host, IP camera, better lens, larger storage or GPU machine is optional until testing identifies a concrete need. Use borrowed Android/iOS devices for acceptance where possible. iOS distribution/signing arrangements are separate from the electronics budget.

## 6. Items unnecessary for the current stated design

- Temperature, heart-rate and gas sensors: current dashboard values are placeholders; the agreed vest design is GPS/SOS. Remove unsupported measurements rather than adding unrelated hardware to justify them.
- Accelerometer/IMU: optional research extension; current fall detection is camera-based. It is not a substitute for finishing the pose pipeline's evaluation.
- Physical smoke/flame sensor: not required for the proposed camera fire/smoke detector. Test using appropriately licensed recordings, not an improvised live-fire demonstration.
- Custom PCB, multiple vests, NVR, dedicated server, Raspberry Pi gateway or expensive GPU: defer until the one-camera/one-vest system passes its gates.

## 7. Quotation and physical evidence checklist

Before paying, record quantity, exact part/revision, supported regional band, antenna/connector, included cables/headers, voltage/interface documentation, unit price in PKR, delivery, return policy and total delivered cost. Compare local quotations for discrete versus integrated boards. No reliable total price can be given without these choices and current quotes.

For acceptance retain a component photograph, final wiring diagram, firmware/build hash, flashing log, GNSS trace, transmitted/received sequence log, backend event ID, web/mobile screenshot, measured delay, tested range conditions and runtime. Mark borrowed equipment and simulated inputs accurately.
