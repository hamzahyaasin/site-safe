// Site-Safe Smart Vest: logic with no Arduino dependencies.
//
// Kept apart from smart_vest.ino so it can be compiled and tested on a
// computer (firmware/test/test_vest_logic.cpp) before any hardware exists.

#pragma once

#include <cmath>
#include <cstdint>
#include <cstdio>

namespace vest {

// ---------------------------------------------------------------- gas (MQ-2)
//
// The MQ-2's resistance Rs falls as gas rises. The module puts a load
// resistor RL in series, so Vout = Vc * RL / (Rs + RL), with the heater and
// divider on Vc = 5 V. Its output (up to 5 V) reaches the ESP32 (3.3 V max)
// through a resistor divider (top from the sensor, bottom to ground; two
// 22 k halve it to at most 2.5 V).
//
// R0 is Rs in clean air divided by 9.83 (the datasheet's clean-air ratio),
// measured once the heater has warmed up. The datasheet's LPG curve is a
// straight line on log-log axes through (200 ppm, Rs/R0 1.6) and
// (10,000 ppm, Rs/R0 0.26). The sensor is not calibrated against a reference gas, so the
// result is an estimate in LPG-equivalent ppm, good for "is there a leak",
// not for a certified concentration.

constexpr double SUPPLY_MV = 5000.0;
constexpr double CLEAN_AIR_RATIO = 9.83;
constexpr double LPG_LOG_PPM = 2.30103;    // log10(200)
constexpr double LPG_LOG_RATIO = 0.20412;  // log10(1.6)
constexpr double LPG_SLOPE = -0.46449;     // between the two datasheet points
constexpr int MAX_PPM = 10000;  // top of the MQ-2's range; higher readings saturate

struct Divider {
  double top_kohm;     // from the sensor's output to the pin
  double bottom_kohm;  // from the pin to ground
};

// Sensor output in millivolts from the voltage measured at the ESP32 pin.
inline double sensor_mv(double pin_mv, Divider d) { return pin_mv * (d.top_kohm + d.bottom_kohm) / d.bottom_kohm; }

// Pin voltage when the sensor outputs its maximum; must stay under the ESP32's 3.3 V.
inline double max_pin_mv(Divider d) { return SUPPLY_MV * d.bottom_kohm / (d.top_kohm + d.bottom_kohm); }

// Sensor resistance Rs in kilo-ohms; negative if the reading is unusable.
inline double sensor_kohm(double pin_mv, double load_kohm, Divider d) {
  double v = sensor_mv(pin_mv, d);
  if (v <= 1.0 || v >= SUPPLY_MV) return -1.0;
  return load_kohm * (SUPPLY_MV - v) / v;
}

// R0 from the average Rs measured in clean air.
inline double r0_from_clean_air(double rs_kohm) { return rs_kohm / CLEAN_AIR_RATIO; }

// Estimated LPG-equivalent ppm, clamped to 0..MAX_PPM; -1 if Rs or R0 is unusable.
inline int gas_ppm(double rs_kohm, double r0_kohm) {
  if (rs_kohm <= 0 || r0_kohm <= 0) return -1;
  double log_ppm = (std::log10(rs_kohm / r0_kohm) - LPG_LOG_RATIO) / LPG_SLOPE + LPG_LOG_PPM;
  double ppm = std::pow(10.0, log_ppm);
  if (ppm > MAX_PPM) return MAX_PPM;
  return ppm < 0 ? 0 : static_cast<int>(std::lround(ppm));
}

// ---------------------------------------------------------------- SOS button
//
// A press raises SOS at once. While SOS is active, holding the button for
// CANCEL_HOLD_MS cancels it; the press that raised it never cancels it, even
// if held, so a panicked long press cannot undo itself. A shorter press while
// SOS is active is a repeat: it counts as a new press (``presses``), so the
// server can raise SOS again after a supervisor has resolved the first alert.

constexpr uint32_t DEBOUNCE_MS = 50;
constexpr uint32_t CANCEL_HOLD_MS = 3000;

enum class SosEvent { None, Raised, Repeated, Cancelled };

struct SosButton {
  bool active = false;
  bool pressed = false;        // debounced state
  bool raw = false;            // last raw reading
  uint32_t raw_since = 0;      // when the raw reading last changed
  uint32_t pressed_since = 0;  // when the debounced press began
  bool press_may_cancel = false;
  uint32_t presses = 0;        // every SOS press since start-up, raising or repeated

  // Feed the raw button state (true = pressed) every loop; returns what happened.
  SosEvent update(bool raw_pressed, uint32_t now_ms) {
    if (raw_pressed != raw) {
      raw = raw_pressed;
      raw_since = now_ms;
    }
    if (raw != pressed && now_ms - raw_since >= DEBOUNCE_MS) {
      pressed = raw;
      if (pressed) {
        pressed_since = now_ms;
        if (!active) {
          active = true;
          press_may_cancel = false;
          ++presses;
          return SosEvent::Raised;
        }
        press_may_cancel = true;
      } else if (active && press_may_cancel) {
        // Released before the cancel hold completed: a repeated SOS press.
        press_may_cancel = false;
        ++presses;
        return SosEvent::Repeated;
      }
    }
    if (active && pressed && press_may_cancel && now_ms - pressed_since >= CANCEL_HOLD_MS) {
      active = false;
      press_may_cancel = false;
      return SosEvent::Cancelled;
    }
    return SosEvent::None;
  }
};

// ---------------------------------------------------------------- telemetry
//
// The JSON body for POST /api/v1/vests/telemetry/. Position and gas are left
// out when there is none (no GPS fix yet, sensor still warming up); SOS and
// the press count are always sent, so the vest's own state is what the server
// shows.

struct Reading {
  bool has_fix = false;
  double latitude = 0;
  double longitude = 0;
  int gas_ppm = -1;  // -1: no reading
  bool sos_active = false;
  uint32_t sos_presses = 0;
};

// Writes the body into buf; returns its length, or -1 if it did not fit.
inline int telemetry_json(char* buf, size_t size, const char* vest_id, const Reading& r) {
  int n = std::snprintf(buf, size, "{\"vest_id\":\"%s\",\"sos_active\":%s,\"sos_presses\":%lu", vest_id,
                        r.sos_active ? "true" : "false", static_cast<unsigned long>(r.sos_presses));
  if (n < 0 || static_cast<size_t>(n) >= size) return -1;
  if (r.has_fix) {
    int m = std::snprintf(buf + n, size - n, ",\"latitude\":%.7f,\"longitude\":%.7f", r.latitude, r.longitude);
    if (m < 0 || static_cast<size_t>(n + m) >= size) return -1;
    n += m;
  }
  if (r.gas_ppm >= 0) {
    int m = std::snprintf(buf + n, size - n, ",\"gas_ppm\":%d", r.gas_ppm);
    if (m < 0 || static_cast<size_t>(n + m) >= size) return -1;
    n += m;
  }
  if (static_cast<size_t>(n + 1) >= size) return -1;
  buf[n++] = '}';
  buf[n] = '\0';
  return n;
}

}  // namespace vest
