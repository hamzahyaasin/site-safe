// Site-Safe field device firmware (ESP32 DevKit): Smart Vest and/or gas monitor.
//
// One sketch, two roles, chosen in config.h:
//  - Smart Vest (VEST_ID set): every REPORT_MS posts its GPS position and SOS
//    state (POST /api/v1/vests/telemetry/). An SOS press, repeat or cancel is
//    sent at once and retried every second until the server has it.
//  - Gas monitor (GAS_MONITOR_ID set): fixed in a zone, every REPORT_MS posts
//    its MQ-2 reading (POST /api/v1/gas-monitors/telemetry/); the server
//    raises GAS alerts for the monitor's zone.
// A deployed vest and monitor are separate boards; the bench prototype can
// run both roles at once. Both use the same endpoints and JSON as
// tools/vest_simulator.py. Nothing in the loop blocks for long, so the SOS
// button is always read.
//
// Wiring and set-up: firmware/README.md. Logic that needs no hardware (gas
// estimate, SOS button, JSON bodies) is in vest_logic.h and tested on a computer.

#include <HTTPClient.h>
#include <TinyGPSPlus.h>
#include <WiFi.h>

#include "config.h"
#include "vest_logic.h"

constexpr int GPS_RX_PIN = 16;  // ESP32 RX2 <- GPS TX
constexpr int GPS_TX_PIN = 17;  // ESP32 TX2 -> GPS RX
constexpr int SOS_PIN = 27;     // button to GND; internal pull-up
constexpr int GAS_PIN = 34;     // MQ-2 AO through the divider in config.h (ADC1: works with Wi-Fi on)
constexpr int LED_PIN = 2;      // on-board LED

// A role is on when its ID in config.h is not empty.
constexpr bool IS_VEST = sizeof(VEST_ID) > 1;
constexpr bool IS_GAS_MONITOR = sizeof(GAS_MONITOR_ID) > 1;

constexpr uint32_t REPORT_MS = 5000;
constexpr uint32_t RETRY_MS = 1000;
constexpr uint32_t WIFI_RETRY_MS = 10000;
constexpr uint32_t GPS_MAX_AGE_MS = 5000;  // older positions are not sent
constexpr uint32_t GAS_WARMUP_MS = 60000;  // heater warm-up before any reading
constexpr int GAS_SAMPLES = 16;            // averaged per reading
constexpr int R0_SAMPLES = 50;             // clean-air calibration readings, one per R0_SAMPLE_MS
constexpr uint32_t R0_SAMPLE_MS = 100;

const vest::Divider GAS_DIVIDER{MQ2_DIVIDER_TOP_KOHM, MQ2_DIVIDER_BOTTOM_KOHM};
constexpr double PIN_MAX_MV = 3300.0;

TinyGPSPlus gps;
vest::SosButton sos;
double r0_kohm = MQ2_R0_KOHM;  // 0: not calibrated yet; -1: calibration failed
double r0_sum = 0;
int r0_good = 0, r0_taken = 0;
uint32_t last_r0_sample = 0;
uint32_t last_vest_report = 0;
uint32_t last_gas_report = 0;
uint32_t last_delivery = 0;  // when a report last reached the server (for the LED)
uint32_t last_wifi_try = 0;
bool sos_pending = false;  // an SOS press, repeat or cancel the server has not confirmed yet

double read_pin_mv() {
  uint32_t total = 0;
  for (int i = 0; i < GAS_SAMPLES; ++i) total += analogReadMilliVolts(GAS_PIN);
  return static_cast<double>(total) / GAS_SAMPLES;
}

// After warm-up, average Rs over R0_SAMPLES readings (about 5 s), one per
// loop pass so the SOS button keeps being read. The air must be clean.
void calibrate_gas_step(uint32_t now) {
  if (r0_kohm != 0 || now < GAS_WARMUP_MS || now - last_r0_sample < R0_SAMPLE_MS) return;
  if (r0_taken == 0) Serial.println("[gas] warmed up; calibrating in clean air");
  last_r0_sample = now;
  double rs = vest::sensor_kohm(read_pin_mv(), MQ2_LOAD_KOHM, GAS_DIVIDER);
  if (rs > 0) {
    r0_sum += rs;
    ++r0_good;
  }
  if (++r0_taken < R0_SAMPLES) return;
  if (r0_good == 0) {
    r0_kohm = -1;
    Serial.println("[gas] no usable reading: check the MQ-2 wiring; gas will not be reported");
    return;
  }
  r0_kohm = vest::r0_from_clean_air(r0_sum / r0_good);
  Serial.printf("[gas] clean-air R0 = %.3f kOhm (set MQ2_R0_KOHM to this to skip calibration)\n", r0_kohm);
}

// -1 until the sensor is warmed up and calibrated.
int read_gas_ppm() {
  if (r0_kohm <= 0 || millis() < GAS_WARMUP_MS) return -1;
  return vest::gas_ppm(vest::sensor_kohm(read_pin_mv(), MQ2_LOAD_KOHM, GAS_DIVIDER), r0_kohm);
}

void keep_wifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  uint32_t now = millis();
  if (now - last_wifi_try < WIFI_RETRY_MS && last_wifi_try != 0) return;
  last_wifi_try = now;
  Serial.printf("[wifi] connecting to %s\n", WIFI_SSID);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// POSTs a JSON body with a device key; returns the HTTP status (negative if
// the request failed) and logs it under ``tag``.
int post_json(const char* tag, const char* path, const char* key, const char* body) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("[%s] no Wi-Fi; not sent: %s\n", tag, body);
    return -1;
  }
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(String(API_BASE) + path);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Device ") + key);
  int code = http.POST(reinterpret_cast<uint8_t*>(const_cast<char*>(body)), strlen(body));
  http.end();
  Serial.printf("[%s] %d %s\n", tag, code, body);
  if (code == 200) last_delivery = millis();
  return code;
}

bool send_vest_report() {
  vest::Reading r;
  r.sos_active = sos.active;
  r.sos_presses = sos.presses;
  if (gps.location.isValid() && gps.location.age() < GPS_MAX_AGE_MS) {
    r.has_fix = true;
    r.latitude = gps.location.lat();
    r.longitude = gps.location.lng();
  } else if (VEST_FIXED_LATITUDE != 0.0 || VEST_FIXED_LONGITUDE != 0.0) {
    r.has_fix = true;  // configured in config.h, not measured
    r.latitude = VEST_FIXED_LATITUDE;
    r.longitude = VEST_FIXED_LONGITUDE;
  }
  char body[200];
  if (vest::telemetry_json(body, sizeof body, VEST_ID, r) < 0) return false;
  int code = post_json("vest", "/v1/vests/telemetry/", DEVICE_KEY, body);
  if (code == 404) Serial.println("[vest] unknown vest: register " VEST_ID " on the Vest Management page");
  if (code == 401 || code == 403) Serial.println("[vest] key refused: check DEVICE_KEY (a VEST_GATEWAY token)");
  return code == 200;
}

void send_gas_report() {
  char body[100];
  if (vest::gas_monitor_json(body, sizeof body, GAS_MONITOR_ID, read_gas_ppm()) < 0) return;
  int code = post_json("gas", "/v1/gas-monitors/telemetry/", GAS_MONITOR_KEY, body);
  if (code == 404) Serial.println("[gas] unknown monitor: register " GAS_MONITOR_ID " under Gas Monitors on the Zones page");
  if (code == 401 || code == 403) Serial.println("[gas] key refused: check GAS_MONITOR_KEY (a GAS_MONITOR token)");
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  WiFi.mode(WIFI_STA);
  if (IS_VEST) {
    Serial2.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
    pinMode(SOS_PIN, INPUT_PULLUP);
    if (VEST_FIXED_LATITUDE != 0.0 || VEST_FIXED_LONGITUDE != 0.0) {
      Serial.printf("[gps] no fix: reporting the configured position %.6f, %.6f\n", VEST_FIXED_LATITUDE,
                    VEST_FIXED_LONGITUDE);
    }
    Serial.printf("\nSite-Safe vest %s\n", VEST_ID);
  }
  if (IS_GAS_MONITOR) {
    analogSetPinAttenuation(GAS_PIN, ADC_11db);  // full 0-3.3 V range
    if (vest::max_pin_mv(GAS_DIVIDER) > PIN_MAX_MV) {
      // A wrong divider could push GPIO34 over 3.3 V: never read it.
      r0_kohm = -1;
      Serial.printf("[gas] divider %.0f k / %.0f k would put %.0f mV on GPIO34 (max 3300); gas disabled\n",
                    MQ2_DIVIDER_TOP_KOHM, MQ2_DIVIDER_BOTTOM_KOHM, vest::max_pin_mv(GAS_DIVIDER));
    }
    Serial.printf("\nSite-Safe gas monitor %s; readings start after %u s of warm-up\n", GAS_MONITOR_ID,
                  static_cast<unsigned>(GAS_WARMUP_MS / 1000));
  }
  if (!IS_VEST && !IS_GAS_MONITOR) Serial.println("\nNeither VEST_ID nor GAS_MONITOR_ID is set in config.h: nothing to do");
  keep_wifi();
}

void loop() {
  keep_wifi();
  uint32_t now = millis();

  if (IS_VEST) {
    while (Serial2.available()) gps.encode(Serial2.read());
    vest::SosEvent event = sos.update(digitalRead(SOS_PIN) == LOW, now);
    if (event == vest::SosEvent::Raised) Serial.println("[sos] RAISED");
    if (event == vest::SosEvent::Repeated) Serial.printf("[sos] pressed again (press %lu)\n", static_cast<unsigned long>(sos.presses));
    if (event == vest::SosEvent::Cancelled) Serial.println("[sos] cancelled");
    if (event != vest::SosEvent::None) sos_pending = true;

    bool due = now - last_vest_report >= REPORT_MS || (sos_pending && now - last_vest_report >= RETRY_MS);
    if (due || event != vest::SosEvent::None) {
      last_vest_report = now;
      if (send_vest_report()) sos_pending = false;
    }
  }

  if (IS_GAS_MONITOR) {
    calibrate_gas_step(now);
    if (now - last_gas_report >= REPORT_MS) {
      last_gas_report = now;
      send_gas_report();
    }
  }

  // Solid while SOS is active; otherwise a short flash after each delivered report.
  digitalWrite(LED_PIN, sos.active || (last_delivery != 0 && millis() - last_delivery < 100) ? HIGH : LOW);
}
