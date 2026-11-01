// Copy this file to config.h (same folder) and fill it in. config.h is not
// committed: it holds your Wi-Fi password and the vest's device key.

#pragma once

// Wi-Fi the vest joins. The laptop running Site-Safe must be on the same network.
#define WIFI_SSID "your-wifi-name"
#define WIFI_PASSWORD "your-wifi-password"

// The Site-Safe API, as the vest reaches it: the laptop's IP address on that
// Wi-Fi, never "localhost" (that would be the vest itself). The backend must
// listen on the network, e.g. `daphne -b 0.0.0.0 -p 8000 sitesafe.asgi:application`.
#define API_BASE "http://192.168.1.10:8000/api"

// A vest gateway device key, from
//   python manage.py create_service_token vest-001 --kind VEST_GATEWAY
#define DEVICE_KEY "ss_..."

// The vest's ID as registered on the Vest Management page.
#define VEST_ID "VEST-001"

// The load resistor on your MQ-2 module, in kilo-ohms. Most modules use 1 k
// (marked "102" on the small resistor next to the sensor); some use 4.7 k
// ("472") or 10 k ("103").
#define MQ2_LOAD_KOHM 1.0

// Clean-air reference of your sensor (R0, kilo-ohms). Leave 0 to measure it at
// every start-up, which needs the vest switched on in clean air. The serial
// monitor prints the measured value; copy it here to skip the measurement.
#define MQ2_R0_KOHM 0.0
