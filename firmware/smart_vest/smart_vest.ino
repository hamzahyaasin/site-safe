// Site-Safe Smart Vest firmware (ESP32 DevKit V1).
//
// Every REPORT_MS the vest posts its GPS position, gas level and SOS state to
// the Site-Safe API over Wi-Fi (POST /api/v1/vests/telemetry/, the same
// endpoint and JSON as tools/vest_simulator.py). An SOS press or cancel is
// sent at once and retried every second until the server has it. Nothing in
// the loop blocks for long, so the SOS button is always read.
//
// Wiring and set-up: firmware/README.md. Logic that needs no hardware (gas
// estimate, SOS button, JSON body) is in vest_logic.h and tested on a computer.

#include <HTTPClient.h>
#include <TinyGPSPlus.h>
#include <WiFi.h>

#include "config.h"
#include "vest_logic.h"

constexpr int GPS_RX_PIN = 16;  // ESP32 RX2 <- GPS TX
constexpr int GPS_TX_PIN = 17;  // ESP32 TX2 -> GPS RX
constexpr int SOS_PIN = 27;     // button to GND; internal pull-up
constexpr int GAS_PIN = 34;     // MQ-2 AO through the 10 k / 20 k divider (ADC1: works with Wi-Fi on)
constexpr int LED_PIN = 2;      // on-board LED

constexpr uint32_t REPORT_MS = 5000;
constexpr uint32_t RETRY_MS = 1000;
constexpr uint32_t WIFI_RETRY_MS = 10000;
constexpr uint32_t GPS_MAX_AGE_MS = 5000;  // older positions are not sent
constexpr uint32_t GAS_WARMUP_MS = 60000;  // heater warm-up before any reading
constexpr int GAS_SAMPLES = 16;            // averaged per reading
constexpr int R0_SAMPLES = 50;             // clean-air calibration readings, one per R0_SAMPLE_MS
constexpr uint32_t R0_SAMPLE_MS = 100;

TinyGPSPlus gps;
vest::SosButton sos;
double r0_kohm = MQ2_R0_KOHM;  // 0: not calibrated yet; -1: calibration failed
double r0_sum = 0;
int r0_good = 0, r0_taken = 0;
uint32_t last_r0_sample = 0;
uint32_t last_report = 0;
uint32_t last_wifi_try = 0;
bool delivered = false;    // whether the last report reached the server (for the LED)
bool sos_pending = false;  // an SOS press or cancel the server has not confirmed yet

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
  double rs = vest::sensor_kohm(read_pin_mv(), MQ2_LOAD_KOHM);
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
  return vest::gas_ppm(vest::sensor_kohm(read_pin_mv(), MQ2_LOAD_KOHM), r0_kohm);
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

bool send_report() {
  vest::Reading r;
  r.sos_active = sos.active;
  r.gas_ppm = read_gas_ppm();
  if (gps.location.isValid() && gps.location.age() < GPS_MAX_AGE_MS) {
    r.has_fix = true;
    r.latitude = gps.location.lat();
    r.longitude = gps.location.lng();
  }
  char body[200];
  if (vest::telemetry_json(body, sizeof body, VEST_ID, r) < 0) return false;
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("[report] no Wi-Fi; not sent: %s\n", body);
    return false;
  }
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(String(API_BASE) + "/v1/vests/telemetry/");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Device ") + DEVICE_KEY);
  int code = http.POST(reinterpret_cast<uint8_t*>(body), strlen(body));
  http.end();
  Serial.printf("[report] %d %s\n", code, body);
  if (code == 404) Serial.println("[report] unknown vest: register " VEST_ID " on the Vest Management page");
  if (code == 401 || code == 403) Serial.println("[report] key refused: check DEVICE_KEY (a VEST_GATEWAY token)");
  return code == 200;
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  pinMode(SOS_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  analogSetPinAttenuation(GAS_PIN, ADC_11db);  // full 0-3.3 V range
  WiFi.mode(WIFI_STA);
  Serial.printf("\nSite-Safe vest %s; gas readings start after %u s of warm-up\n", VEST_ID,
                static_cast<unsigned>(GAS_WARMUP_MS / 1000));
  keep_wifi();
}

void loop() {
  while (Serial2.available()) gps.encode(Serial2.read());
  keep_wifi();

  uint32_t now = millis();
  calibrate_gas_step(now);
  vest::SosEvent event = sos.update(digitalRead(SOS_PIN) == LOW, now);
  if (event == vest::SosEvent::Raised) Serial.println("[sos] RAISED");
  if (event == vest::SosEvent::Cancelled) Serial.println("[sos] cancelled");
  if (event != vest::SosEvent::None) sos_pending = true;

  bool due = now - last_report >= REPORT_MS || (sos_pending && now - last_report >= RETRY_MS);
  if (due || event != vest::SosEvent::None) {
    last_report = now;
    delivered = send_report();
    if (delivered) sos_pending = false;
  }

  // Solid while SOS is active; otherwise a short flash after each delivered report.
  digitalWrite(LED_PIN, sos.active || (delivered && now - last_report < 100) ? HIGH : LOW);
}
