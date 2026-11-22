// The planter's rules, with no hardware in them: settings in and out of JSON, and when a zone is watered.
// main.cpp does the pins, sensors, Wi-Fi and SD card; this file only decides. Because it needs nothing but
// ArduinoJson, the same code is compiled on a computer by test/host/run.sh to check it.
#pragma once
#include <ArduinoJson.h>
#include <stdint.h>
#include <string.h>

// Limits of this firmware. A planter uses ZONE_COUNT zones and TANK_COUNT tanks (planter_config.h), up to these.
#define MAX_ZONES 8
#define MAX_TANKS 4
#define MAX_HOURS 24  // every hour of the day, for hourly watering

// Defaults until Commune, the phone page or the SD card sends settings (planter_config.h can change them).
#ifndef DEFAULT_WAKE_MINUTES
#define DEFAULT_WAKE_MINUTES 60
#endif
#ifndef DEFAULT_REPORT_EVERY
#define DEFAULT_REPORT_EVERY 3
#endif
#ifndef DEFAULT_MIN_BATTERY
#define DEFAULT_MIN_BATTERY 25
#endif
#ifndef DEFAULT_SCHEDULE
#define DEFAULT_SCHEDULE false
#endif
#ifndef DEFAULT_EVERY_DAYS
#define DEFAULT_EVERY_DAYS 1
#endif
#ifndef DEFAULT_MOISTURE_BELOW
#define DEFAULT_MOISTURE_BELOW 40
#endif
#ifndef DEFAULT_ML
#define DEFAULT_ML 1000
#endif
#ifndef DEFAULT_MAX_ML_PER_DAY
#define DEFAULT_MAX_ML_PER_DAY 4000
#endif
#ifndef UTC_OFFSET_FALLBACK
#define UTC_OFFSET_FALLBACK 0
#endif

inline int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

// ---------------------------------------------------------------- settings
// mode "moisture": water only when the soil is drier than moistureBelow (Plantwatery's way).
// mode "schedule": water ml at every watering hour, every `everyDays` days, whatever the soil says (Rainmaker's way).
struct ZoneSettings { bool enabled, schedule; int everyDays, moistureBelow, ml, maxMlPerDay; };
struct Settings {
  int wakeMinutes, reportEvery, minBattery, nHours;
  int hours[MAX_HOURS];
  int32_t utcOffset;
  ZoneSettings zones[MAX_ZONES];
};

inline void defaultSettings(Settings &c, const int *hours, int nHours) {
  c.wakeMinutes = DEFAULT_WAKE_MINUTES;
  c.reportEvery = DEFAULT_REPORT_EVERY;
  c.minBattery = DEFAULT_MIN_BATTERY;
  c.utcOffset = UTC_OFFSET_FALLBACK;
  c.nHours = 0;
  for (int i = 0; i < nHours && c.nHours < MAX_HOURS; i++)
    if (hours[i] >= 0 && hours[i] <= 23) c.hours[c.nHours++] = hours[i];
  for (int z = 0; z < MAX_ZONES; z++)
    c.zones[z] = {true, DEFAULT_SCHEDULE, DEFAULT_EVERY_DAYS, DEFAULT_MOISTURE_BELOW, DEFAULT_ML, DEFAULT_MAX_ML_PER_DAY};
}

// Reads settings in planter.json's format: from Commune (through the bridge or the SD card), the SD card edited by
// hand, or the phone page. Anything missing keeps its current value; anything out of range is pulled into range.
inline bool applySettings(Settings &c, JsonVariantConst s) {
  if (!s.is<JsonObjectConst>()) return false;
  c.wakeMinutes = clampi(s["wakeMinutes"] | c.wakeMinutes, 5, 720);
  c.reportEvery = clampi(s["reportEveryWakes"] | c.reportEvery, 1, 24);
  c.minBattery = clampi(s["minBattery"] | c.minBattery, 0, 90);
  c.utcOffset = clampi(s["utcOffset"] | (int)c.utcOffset, -14 * 3600, 14 * 3600);
  JsonArrayConst hours = s["wateringHours"];
  if (!hours.isNull()) {
    bool seen[24] = {};
    for (JsonVariantConst h : hours)
      if (h.is<int>() && h.as<int>() >= 0 && h.as<int>() <= 23) seen[h.as<int>()] = true;
    c.nHours = 0;  // sorted, each hour once
    for (int h = 0; h < 24; h++) if (seen[h]) c.hours[c.nHours++] = h;
  }
  for (JsonVariantConst z : s["zones"].as<JsonArrayConst>()) {
    int n = (z["zone"] | 0) - 1;
    if (n < 0 || n >= MAX_ZONES) continue;
    ZoneSettings &zs = c.zones[n];
    zs.enabled = z["enabled"] | zs.enabled;
    zs.moistureBelow = clampi(z["moistureBelow"] | zs.moistureBelow, 0, 100);
    zs.ml = clampi(z["ml"] | zs.ml, 0, 20000);
    zs.maxMlPerDay = clampi(z["maxMlPerDay"] | zs.maxMlPerDay, 0, 100000);
    const char *mode = z["mode"] | (zs.schedule ? "schedule" : "moisture");
    zs.schedule = strcmp(mode, "schedule") == 0;
    zs.everyDays = clampi(z["everyDays"] | zs.everyDays, 1, 14);
  }
  return true;
}

// What this planter is built with, so Commune shows exactly its zones and tanks. zoneTank[z] is the tank (1-based)
// that feeds zone z+1.
struct Layout { int zones, tanks; const int *zoneTank; bool pump, flow; };

inline void layoutToJson(const Layout &l, JsonObject o) {
  JsonArray zs = o["zones"].to<JsonArray>();
  for (int z = 0; z < l.zones; z++) {
    JsonObject zo = zs.add<JsonObject>();
    zo["zone"] = z + 1;
    zo["tank"] = l.zoneTank[z];
  }
  JsonArray ts = o["tanks"].to<JsonArray>();
  for (int t = 0; t < l.tanks; t++) {
    JsonObject to = ts.add<JsonObject>();
    to["tank"] = t + 1;
  }
  o["pump"] = l.pump;
  o["flow"] = l.flow;
}

inline void settingsToJson(const Settings &c, const Layout &l, JsonObject o) {
  o["communePlanterSettings"] = 1;
  o["wakeMinutes"] = c.wakeMinutes;
  o["reportEveryWakes"] = c.reportEvery;
  o["minBattery"] = c.minBattery;
  o["utcOffset"] = c.utcOffset;
  JsonArray hours = o["wateringHours"].to<JsonArray>();
  for (int i = 0; i < c.nHours; i++) hours.add(c.hours[i]);
  JsonArray zones = o["zones"].to<JsonArray>();
  for (int z = 0; z < l.zones; z++) {
    const ZoneSettings &zs = c.zones[z];
    JsonObject zo = zones.add<JsonObject>();
    zo["zone"] = z + 1;
    zo["enabled"] = zs.enabled;
    zo["mode"] = zs.schedule ? "schedule" : "moisture";
    zo["everyDays"] = zs.everyDays;
    zo["moistureBelow"] = zs.moistureBelow;
    zo["ml"] = zs.ml;
    zo["maxMlPerDay"] = zs.maxMlPerDay;
  }
  layoutToJson(l, o["layout"].to<JsonObject>());
}

// Commune's settings are taken only when their settingsChanged differs from the last one taken, so a change made on
// the phone page or the SD card stays until someone changes the settings in Commune.
inline bool communeSettingsAreNew(const char *changed, const char *lastTaken) {
  return changed && *changed && strcmp(changed, lastTaken ? lastTaken : "") != 0;
}

// ---------------------------------------------------------------- when to water
inline bool isWateringHour(const Settings &c, int hour) {
  for (int i = 0; i < c.nHours; i++) if (c.hours[i] == hour) return true;
  return false;
}

// The current watering slot (local hours since 1970), or -1 if this isn't a watering hour. Without the real time
// (no clock module, and nothing has set it since power-up) it allows one watering every 12 hours.
inline int32_t wateringSlot(const Settings &c, bool timeValid, uint32_t now) {
  if (!timeValid) return (int32_t)(now / 43200);
  int32_t local = (int32_t)now + c.utcOffset;
  int hour = (local % 86400) / 3600;
  return isWateringHour(c, hour) ? local / 3600 : -1;
}

// Seconds until the next watering hour starts (plus a little), or 0 if there's none.
inline uint32_t secondsToNextWateringHour(const Settings &c, uint32_t now) {
  int32_t local = (int32_t)now + c.utcOffset;
  for (int ahead = 1; ahead <= 24; ahead++)
    if (isWateringHour(c, ((local / 3600) + ahead) % 24)) return (uint32_t)(3600 - (local % 3600) + (ahead - 1) * 3600) + 20;
  return 0;
}

enum Reason : uint8_t { R_NONE, R_MOIST, R_DAILY_MAX, R_BATTERY, R_TANK, R_RESET, R_NO_WATER, R_BARREL_RAN_LOW, R_NOT_TODAY, R_BY_HAND, R_NO_SENSOR };

// What one zone needs at a watering slot.
struct ZoneInput {
  int moisture;          // %, -1 if the sensor isn't calibrated or isn't there
  bool tankLow;          // the tank that feeds this zone is low
  int battery;           // %, -1 unknown
  uint32_t mlToday;
  int32_t today;         // local day number
  int32_t lastWaterDay;  // local day of the last scheduled watering
};
struct ZoneDecision {
  bool water;
  int ml;          // when water is true
  uint8_t reason;  // when it isn't: why (R_NONE = the zone is off, nothing to report)
  int a, b;        // numbers for the reason
};

inline ZoneDecision decideZone(const Settings &c, int z, const ZoneInput &in) {
  const ZoneSettings &zs = c.zones[z];
  if (!zs.enabled || zs.ml <= 0) return {false, 0, R_NONE, 0, 0};
  if (zs.schedule) {
    // Scheduled: every watering hour of a watering day. A day counts once it has had its first watering.
    int32_t since = in.today - in.lastWaterDay;
    if (since != 0 && since < zs.everyDays) return {false, 0, R_NOT_TODAY, zs.everyDays, (int)(zs.everyDays - since)};
  } else {
    if (in.moisture < 0) return {false, 0, R_NO_SENSOR, 0, 0};
    if (in.moisture >= zs.moistureBelow) return {false, 0, R_MOIST, in.moisture, zs.moistureBelow};
  }
  if (in.tankLow) return {false, 0, R_TANK, 0, 0};
  if (in.battery >= 0 && in.battery < c.minBattery) return {false, 0, R_BATTERY, in.battery, c.minBattery};
  int ml = zs.ml;
  if ((int)in.mlToday + ml > zs.maxMlPerDay) ml = zs.maxMlPerDay - (int)in.mlToday;
  if (ml <= 0) return {false, 0, R_DAILY_MAX, zs.maxMlPerDay, 0};
  return {true, ml, R_NONE, 0, 0};
}
