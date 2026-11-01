// Host tests for firmware/smart_vest/vest_logic.h (no hardware needed).
//
//   c++ -std=c++17 -Wall -Wextra -I firmware/smart_vest firmware/test/test_vest_logic.cpp -o /tmp/vest_test && /tmp/vest_test

#include <cmath>
#include <cstdio>
#include <cstring>

#include "vest_logic.h"

static int failures = 0;

#define CHECK(cond)                                                    \
  do {                                                                 \
    if (!(cond)) {                                                     \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);      \
      ++failures;                                                      \
    }                                                                  \
  } while (0)

static bool near(double a, double b, double tolerance) { return std::fabs(a - b) <= tolerance; }

static void test_divider_and_resistance() {
  // 2.0 V at the pin is 3.0 V from the sensor; with RL 1 k, Rs = 1 * (5 - 3) / 3.
  CHECK(near(vest::sensor_mv(2000), 3000, 1e-9));
  CHECK(near(vest::sensor_kohm(2000, 1.0), 2.0 / 3.0, 1e-9));
  CHECK(vest::sensor_kohm(0, 1.0) < 0);  // no signal: unusable, not infinite resistance
  CHECK(vest::sensor_kohm(3400, 1.0) < 0);  // 5.1 V: above the supply, unusable
}

static void test_ppm_follows_the_datasheet_curve() {
  const double r0 = 10.0;
  CHECK(near(vest::gas_ppm(1.6 * r0, r0), 200, 2));   // the curve's anchor point
  CHECK(near(vest::gas_ppm(0.26 * r0, r0), 10000, 250));  // datasheet: about 0.26 at 10,000 ppm
  CHECK(vest::gas_ppm(vest::CLEAN_AIR_RATIO * r0, r0) < 10);  // clean air reads near zero
  CHECK(vest::gas_ppm(0.05 * r0, r0) == vest::MAX_PPM);  // saturates
  CHECK(vest::gas_ppm(-1, r0) == -1);
  CHECK(vest::gas_ppm(5, 0) == -1);  // not calibrated
}

static void test_more_gas_reads_higher() {
  const double r0 = vest::r0_from_clean_air(vest::sensor_kohm(800, 1.0));  // clean air: 1.2 V from the sensor
  int clean = vest::gas_ppm(vest::sensor_kohm(800, 1.0), r0);
  int some = vest::gas_ppm(vest::sensor_kohm(1600, 1.0), r0);
  int lots = vest::gas_ppm(vest::sensor_kohm(2600, 1.0), r0);
  CHECK(clean < some && some < lots);
  CHECK(clean < 10);
}

static void test_sos_press_raises_and_hold_cancels() {
  vest::SosButton b;
  uint32_t t = 0;
  CHECK(b.update(true, t) == vest::SosEvent::None);  // bounce: not yet debounced
  t += 60;
  CHECK(b.update(true, t) == vest::SosEvent::Raised);
  CHECK(b.active);
  // Holding the press that raised it never cancels it.
  for (t += 100; t < 10000; t += 100) CHECK(b.update(true, t) == vest::SosEvent::None);
  CHECK(b.active);
  b.update(false, t);
  t += 60;
  b.update(false, t);
  // A second press held for 3 s cancels.
  b.update(true, t);
  t += 60;
  CHECK(b.update(true, t) == vest::SosEvent::None);
  t += 2000;
  CHECK(b.update(true, t) == vest::SosEvent::None);
  t += 1000;
  CHECK(b.update(true, t) == vest::SosEvent::Cancelled);
  CHECK(!b.active);
}

static void test_short_press_while_active_does_not_cancel() {
  vest::SosButton b;
  b.update(true, 0);
  b.update(true, 60);
  b.update(false, 200);
  b.update(false, 260);
  b.update(true, 300);
  b.update(true, 360);
  b.update(false, 1000);
  CHECK(b.update(false, 1060) == vest::SosEvent::None);
  CHECK(b.active);
}

static void test_bounces_shorter_than_debounce_are_ignored() {
  vest::SosButton b;
  CHECK(b.update(true, 0) == vest::SosEvent::None);
  CHECK(b.update(false, 20) == vest::SosEvent::None);
  CHECK(b.update(false, 200) == vest::SosEvent::None);
  CHECK(!b.active);
}

static void test_telemetry_json() {
  char buf[200];
  vest::Reading r;
  CHECK(vest::telemetry_json(buf, sizeof buf, "VEST-001", r) > 0);
  CHECK(std::strcmp(buf, "{\"vest_id\":\"VEST-001\",\"sos_active\":false}") == 0);

  r.has_fix = true;
  r.latitude = 33.6844;
  r.longitude = 73.0479;
  r.gas_ppm = 2400;
  r.sos_active = true;
  vest::telemetry_json(buf, sizeof buf, "VEST-001", r);
  CHECK(std::strcmp(buf,
                    "{\"vest_id\":\"VEST-001\",\"sos_active\":true,\"latitude\":33.6844000,"
                    "\"longitude\":73.0479000,\"gas_ppm\":2400}") == 0);

  char small[30];
  CHECK(vest::telemetry_json(small, sizeof small, "VEST-001", r) == -1);  // never a truncated body
}

int main() {
  test_divider_and_resistance();
  test_ppm_follows_the_datasheet_curve();
  test_more_gas_reads_higher();
  test_sos_press_raises_and_hold_cancels();
  test_short_press_while_active_does_not_cancel();
  test_bounces_shorter_than_debounce_are_ignored();
  test_telemetry_json();
  if (failures) {
    std::printf("%d check(s) failed\n", failures);
    return 1;
  }
  std::printf("vest logic: all checks passed\n");
  return 0;
}
