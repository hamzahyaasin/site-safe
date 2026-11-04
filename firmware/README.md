# Smart Vest and gas monitor firmware

One ESP32 sketch with two roles, chosen in `config.h`:

- **Smart Vest**, worn by a worker: reads an SOS button (and a GPS module, if fitted) and every 5 s posts them over Wi-Fi to `POST /api/v1/vests/telemetry/`.
- **Gas monitor**, fixed in a zone: reads an MQ-2 gas sensor and every 5 s posts the reading to `POST /api/v1/gas-monitors/telemetry/`. Gas is a hazard of the place, so the server raises the GAS alert for the monitor's **zone**, not for a worker.

On a site these are separate boards; the bench prototype runs both roles on one board, each with its own device key. Both use the same endpoints and JSON as the simulator (`tools/vest_simulator.py`), so everything it shows (map, zone entry and breaches, SOS, GAS, offline detection) works with the real devices unchanged.

| File | What it is |
|---|---|
| `smart_vest/smart_vest.ino` | The sketch: Wi-Fi, GPS, button, gas sensor, reporting for each role |
| `smart_vest/vest_logic.h` | Logic with no hardware dependency: gas estimate, SOS button, JSON bodies |
| `smart_vest/config.example.h` | Settings template; copy to `config.h` (not committed) |
| `test/test_vest_logic.cpp` | Tests for `vest_logic.h`, run on a computer |

## Parts

Each board: an ESP32 DevKit V1 (any classic ESP32-WROOM-32 board, 30 or 38 pins; not an S3, C3 or C5), a USB data cable, a breadboard and jumper wires.

- **Vest:** a momentary push button, a NEO-6M GPS module with antenna (optional, see below) and a USB power bank.
- **Gas monitor:** an MQ-2 gas sensor module and two 22 kΩ resistors; power from a 5 V USB charger, since it stays in place.

## Wiring

Wire only the parts for the board's role(s).

| From | To | Notes |
|---|---|---|
| GPS VCC | ESP32 3V3 | |
| GPS GND | ESP32 GND | |
| GPS TX | ESP32 GPIO16 (RX2) | The GPS talks, the ESP32 listens |
| GPS RX | ESP32 GPIO17 (TX2) | Optional; not used by the firmware |
| Button, one leg | ESP32 GPIO27 | The ESP32's internal pull-up is used |
| Button, other leg | ESP32 GND | |
| MQ-2 VCC | ESP32 VIN | 5 V for the heater (VIN carries the USB 5 V) |
| MQ-2 GND | ESP32 GND | |
| MQ-2 AO | 22 kΩ resistor, then GPIO34 | |
| GPIO34 | 22 kΩ resistor, then GND | The two halve the sensor's 5 V to at most 2.5 V; the ESP32 pin must stay under 3.3 V |
| MQ-2 DO | not connected | |

The ESP32's on-board LED (GPIO2) stays on while SOS is active and flashes briefly after each report the server accepts.

GPIO34 is an ADC1 pin on purpose: the ESP32's ADC2 pins stop working while Wi-Fi is on.

Other resistors work if the pin stays under 3.3 V: set `MQ2_DIVIDER_TOP_KOHM` and `MQ2_DIVIDER_BOTTOM_KOHM` in `config.h`. The firmware switches gas off if the divider could exceed it (10 kΩ over 22 kΩ, for example, would reach 3.4 V).

A 12×12 mm push button has four legs in two internally joined pairs. Use two **diagonally opposite** legs: they are always on opposite sides of the switch.

**Without a GPS module** leave the four GPS wires out. The vest then sends no position: SOS alerts still arrive, without a place. To show the vest on the site map anyway, set `VEST_FIXED_LATITUDE` and `VEST_FIXED_LONGITUDE` in `config.h` to where it is being used. That position is configured, not measured; say so wherever it is shown.

## Set up the server side (once)

The vest joins a **2.4 GHz** Wi-Fi network (the ESP32 cannot use 5 GHz, nor a network with a sign-in page); a phone hotspot set to 2.4 GHz works, with the laptop joined to the same hotspot.


1. Register each device:
   - **Vest:** on the **Vest Management** page, register it (for example `VEST-001`) and assign it to a worker.
   - **Gas monitor:** on the **Zones** page, under **Gas Monitors**, register it (for example `GM-01`), choose the zone it is installed in and, optionally, pick its position on the map.
2. Create a device key for each role, from `backend/`:

   ```bash
   python manage.py create_service_token vest-001 --kind VEST_GATEWAY
   python manage.py create_service_token gm-01 --kind GAS_MONITOR
   ```

   Store each key it prints; it is shown only once. Do not use `--simulator`: that would label the alerts as simulated.
3. Run the API so the vest can reach it over Wi-Fi, with the laptop's IP address allowed. Find the IP with `ipconfig getifaddr en0` (macOS), then from `backend/`:

   ```bash
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10 daphne -b 0.0.0.0 -p 8000 sitesafe.asgi:application
   ```

   The router can give the laptop a different address after it restarts (a power cut, for example); the vest then reports `-1` and needs `API_BASE` updated and reflashing. To avoid that, reserve the laptop's address in the router's DHCP settings (often called "address reservation" or "static lease"). The laptop's `.local` name is not a reliable alternative: on some home routers the ESP32 cannot resolve it (tested 4 Nov on a PTCL router).

## Flash the vest

1. Install the [Arduino IDE](https://www.arduino.cc/en/software) (version 2).
2. **File > Preferences > Additional boards manager URLs:** add `https://espressif.github.io/arduino-esp32/package_esp32_index.json`. Then **Tools > Board > Boards Manager**: install **esp32 by Espressif Systems**.
3. **Tools > Manage Libraries:** install **TinyGPSPlus** by Mikal Hart.
4. Copy `smart_vest/config.example.h` to `smart_vest/config.h` and fill in the Wi-Fi name and password and `API_BASE` with the laptop's IP. For a vest set `VEST_ID` and `DEVICE_KEY`; for a gas monitor set `GAS_MONITOR_ID` and `GAS_MONITOR_KEY`. Set an ID to `""` to switch that role off.
5. Open `smart_vest/smart_vest.ino`, choose **Tools > Board > ESP32 Dev Module** and the vest's USB port, and click **Upload**. If the upload stalls at "Connecting…", hold the board's **BOOT** button until it starts.
6. Open **Tools > Serial Monitor** at 115200 baud. Each report prints the role, the HTTP status and the JSON sent, for example `[vest] 200 {"vest_id":"VEST-001","sos_active":false,"sos_presses":0}` and `[gas] 200 {"monitor_id":"GM-01","gas_ppm":4}`. `sos_presses` counts every SOS press since start-up; the server uses it to tell a new press from a repeated report. A monitor sends no `gas_ppm` during its first minute, while the sensor warms up.

## Bench test, in this order

| Step | Do | Expect |
|---|---|---|
| 1 | Power on, Serial Monitor open | `[wifi] connecting…`, then `[vest] 200` and/or `[gas] 200` every 5 s. A `404` means the ID is not registered; `401` or `403` means the key is wrong. |
| 2 | Watch the Vest Management page, and Gas Monitors on the Zones page | The vest and the monitor show Online within 5 s |
| 3 | Press the button once | `[sos] RAISED`; LED on; a critical SOS alert on the dashboard and phone within seconds |
| 4 | Press and hold the button for 3 s | `[sos] cancelled`; LED off; the vest's SOS shows Normal and the SOS alert is resolved, noted "cancelled by the wearer". Holding the first press never cancels it. |
| 4b | Press once (SOS raised), resolve the alert on the dashboard, then press briefly again | `[sos] pressed again (press 2)`; a new SOS alert, since the vest is still in SOS. A brief press while an alert is still open adds nothing. |
| 5 | Take the vest outdoors, open sky (skip without a GPS module) | Position appears on the site map once the GPS has a fix. The first fix can take several minutes; indoors there may be none. |
| 6 | Gas monitor: leave it on in clean air for 1 minute | `[gas] clean-air R0 = …`; then every gas report carries `gas_ppm` (low, under about 100 in clean air) |
| 7 | Hold an **unlit** lighter near the sensor and release a little gas for 1–2 s | The reading jumps above 2,000 ppm; one critical GAS alert for the monitor's zone, with no worker; the zone turns red on the site map. Air the room afterwards. |
| 8 | Switch the board off | The vest and the monitor show Offline after 2 minutes |

Never use a flame near the sensor, and do the gas test in a ventilated space.

## How the gas reading works, and its limits

The MQ-2's resistance falls as flammable gas rises. One minute after start-up the firmware measures the sensor in clean air (its reference, R0), then turns each reading into an estimated LPG-equivalent concentration using the two points of the datasheet's LPG curve. The server raises one GAS alert for the monitor's zone when a reading reaches `GAS_ALERT_PPM` (2,000 ppm by default, about a tenth of LPG's lower explosive limit), and another only after the level has stayed below it for a minute, or at the next rise once that alert has been resolved.

This is an indicative reading for "is there a leak here", not a certified gas detector: the sensor is not calibrated against a reference gas, it responds to several gases (LPG, methane, hydrogen, smoke) without telling them apart, and its readings drift with temperature and humidity. For the most stable readings, run a new sensor for a day before relying on it (its datasheet recommends this burn-in) and calibrate in clean air.

## Test the logic without hardware

```bash
c++ -std=c++17 -Wall -Wextra -I firmware/smart_vest firmware/test/test_vest_logic.cpp -o /tmp/vest_test && /tmp/vest_test
```
