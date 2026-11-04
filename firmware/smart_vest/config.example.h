// Copy this file to config.h (same folder) and fill it in. config.h is not
// committed: it holds your Wi-Fi password and the device keys.
//
// The board runs as a Smart Vest (VEST_ID set), a fixed gas monitor
// (GAS_MONITOR_ID set) or, on the bench prototype, both. Leave an ID as ""
// to switch that role off.

#pragma once

// Wi-Fi the vest joins. The laptop running Site-Safe must be on the same network.
#define WIFI_SSID "your-wifi-name"
#define WIFI_PASSWORD "your-wifi-password"

// The Site-Safe API, as the vest reaches it: the laptop's IP address on that
// Wi-Fi, never "localhost" (that would be the vest itself). The backend must
// listen on the network, e.g. `daphne -b 0.0.0.0 -p 8000 sitesafe.asgi:application`.
#define API_BASE "http://192.168.1.10:8000/api"

// --- Smart Vest role (SOS button, optional GPS) ---
// The vest's ID as registered on the Vest Management page; "" if this board is not a vest.
#define VEST_ID "VEST-001"
// A vest gateway device key, from
//   python manage.py create_service_token vest-001 --kind VEST_GATEWAY
#define DEVICE_KEY "ss_..."

// --- Gas monitor role (MQ-2 sensor, fixed in a zone) ---
// The monitor's ID as registered under Gas Monitors on the Zones page (which
// also says which zone it is in); "" if this board is not a gas monitor.
#define GAS_MONITOR_ID "GM-01"
// A gas monitor device key, from
//   python manage.py create_service_token gm-01 --kind GAS_MONITOR
#define GAS_MONITOR_KEY "ss_..."

// The load resistor on your MQ-2 module, in kilo-ohms. Most modules use 1 k
// (marked "102" on the small resistor next to the sensor); some use 4.7 k
// ("472") or 10 k ("103").
#define MQ2_LOAD_KOHM 1.0

// The two resistors between the MQ-2's AO pin and GPIO34: top from AO to the
// pin, bottom from the pin to GND. Two 22 k resistors halve the sensor's 5 V to
// at most 2.5 V. The firmware refuses gas readings if the pin could exceed 3.3 V.
#define MQ2_DIVIDER_TOP_KOHM 22.0
#define MQ2_DIVIDER_BOTTOM_KOHM 22.0

// Clean-air reference of your sensor (R0, kilo-ohms). Leave 0 to measure it at
// every start-up, which needs the vest switched on in clean air. The serial
// monitor prints the measured value; copy it here to skip the measurement.
#define MQ2_R0_KOHM 0.0

// Without a GPS module (or before it has a fix) the vest sends no position.
// To place it on the site map anyway, set where it is being used, e.g. a
// bench inside a zone. This position is configured, not measured: say so
// wherever it is shown. Leave both 0 to send no position.
#define VEST_FIXED_LATITUDE 0.0
#define VEST_FIXED_LONGITUDE 0.0
