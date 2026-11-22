// Solar rain planter: waters each zone by gravity from a raised rain tank, running on a solar-charged 18650 battery.
// Combines the gravity feed and valve zones of Rainmaker 9000 (github.com/AlexanderPinkerton/rainmaker9000) with the
// solar power, deep sleep and moisture-triggered watering of Plantwatery (github.com/Lumics/Plantwatery).
// Written fresh for this project; no code is copied from either.
//
// Every wake: read the sensors, water any zone that needs it (only at a watering hour), log the reading to the SD
// card, post saved readings to the Wi-Fi bridge when it's time, then deep sleep. Nothing here needs Wi-Fi: the
// clock module keeps time, the SD card keeps every reading and a settings file, and the setup button opens the
// planter's own hotspot with a settings page for a phone. Format: commune_offline_community_suite/docs/integrations/planter.md.
//
// Files: planter_logic.h decides (settings and when to water; tested on a computer by test/host/run.sh),
// planter_io.h reaches pins on the ESP32 or on I2C expanders, phone_page.h is the hotspot page, and this file
// does the rest. Zones and tanks are lists in planter_config.h, so a bigger planter only changes the config.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <DallasTemperature.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <Preferences.h>
#include <RTClib.h>
#include <SD.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>
#include <driver/gpio.h>
#include <driver/rtc_io.h>
#include <esp_sleep.h>
#include <esp_wifi.h>
#include <sys/time.h>

#include "planter_io.h"  // XPIN() and ADC_CH(), which planter_config.h may use
#if __has_include("planter_config.h")
#include "planter_config.h"
#else
#warning "No src/planter_config.h: building with config_example.h. Copy it to planter_config.h and fill in your Wi-Fi and bridge."
#include "config_example.h"
#endif
#include "planter_logic.h"

#define FIRMWARE "1.2.0"
#define MAX_READINGS 48
#define MAX_EVENTS 32
#define STATE_MAGIC 0x504C4E33  // "PLN3"
static_assert(ZONE_COUNT >= 1 && ZONE_COUNT <= MAX_ZONES, "ZONE_COUNT must be 1-8");
static_assert(TANK_COUNT >= 1 && TANK_COUNT <= MAX_TANKS, "TANK_COUNT must be 1-4");

// ---------------------------------------------------------------- kept in RTC memory through deep sleep
enum EventType : uint8_t { EV_WATERED, EV_SKIPPED, EV_TANK_LOW, EV_LOW_BATTERY, EV_SLOW_FLOW, EV_VALVES_CLOSED, EV_ERROR, EV_PUMPED, EV_PUMP_TIMEOUT };
static const char *EVENT_NAMES[] = {"watered", "skipped", "tank-low", "low-battery", "slow-flow", "valve-closed-on-boot", "error", "pumped", "pump-timeout"};
#define HAS_PUMP (PIN_PUMP >= 0)
bool headerIsFull();
bool tankHasWater(int t);

struct Reading {
  uint32_t t;
  int8_t battery;           // %, -1 unknown
  uint16_t batteryMv, solarMv;
  uint8_t tankLow;          // one bit per tank: set while that tank's float says low
  uint8_t headerFull;       // header tank float: 1 full, 0 not full, 2 no header tank
  int16_t airTemp, soilTemp; // tenths of °C, INT16_MIN unknown
  int8_t moisture[MAX_ZONES];
  uint16_t mv[MAX_ZONES];
};
struct Event {
  uint32_t t;
  uint8_t type, zone, reason, tank;
  uint16_t ml, deciSeconds;
  int16_t a, b;             // numbers for the reason (moisture and threshold, battery and minimum…)
};
struct State {
  uint32_t magic;
  uint32_t boots, wakesSinceReport;
  bool timeValid, valveMaybeOpen, batteryWarned;
  uint8_t tankWasLow;                // one bit per tank
  int32_t day;                       // local day number, to reset mlToday
  uint32_t mlToday[MAX_ZONES];
  int32_t lastSlot[MAX_ZONES];       // watering slot (day*24+hour) last checked, so each slot runs once
  uint32_t lastWatered[MAX_ZONES];
  int32_t lastWaterDay[MAX_ZONES];   // local day of the last scheduled watering (for "every N days")
  uint8_t nReadings, nEvents;
  Reading readings[MAX_READINGS];
  Event events[MAX_EVENTS];
};
RTC_DATA_ATTR State st;

// Events from this wake, for the SD card log (the RTC buffer above is cleared whenever the bridge takes it).
Event wakeEvents[24];
int nWakeEvents = 0;

// ---------------------------------------------------------------- settings (one copy in flash, mirrored to the SD card)
Settings cfg;  // the rules are in planter_logic.h
const Layout LAYOUT = {ZONE_COUNT, TANK_COUNT, ZONE_TANK, HAS_PUMP, PIN_FLOW >= 0};
// Where the settings in use came from, and when they were last changed on the planter itself.
String settingsSource = "default", settingsChangedAt = "", communeChanged = "";

Preferences prefs;
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature probes(&oneWire);
RTC_DS3231 rtc;
bool rtcOk = false, sdOk = false;
volatile uint32_t flowPulses = 0;

void IRAM_ATTR onFlowPulse() { flowPulses++; }

uint32_t nowSec() { return (uint32_t)time(nullptr); }
int32_t localSec() { return (int32_t)nowSec() + cfg.utcOffset; }

// ISO 8601 in local time, with the offset: what Commune reads.
String isoTime(uint32_t t) {
  time_t lt = (time_t)t + cfg.utcOffset;
  struct tm tmv;
  gmtime_r(&lt, &tmv);
  char b[40];
  strftime(b, sizeof b, "%Y-%m-%dT%H:%M:%S", &tmv);
  int off = cfg.utcOffset / 60;
  char z[10];
  snprintf(z, sizeof z, "%c%02d:%02d", off < 0 ? '-' : '+', abs(off) / 60, abs(off) % 60);
  return String(b) + z;
}

String deviceId() {
  uint64_t mac = ESP.getEfuseMac();
  char id[16];
  snprintf(id, sizeof id, "PL-%02X%02X%02X", (uint8_t)(mac >> 24), (uint8_t)(mac >> 32), (uint8_t)(mac >> 40));
  return String(id);
}

// Sets the clock from the bridge or a phone, and the clock module too, so it survives the next power cut.
void setClock(uint32_t epoch) {
  if (epoch < 1700000000) return;
  struct timeval tv = {(time_t)epoch, 0};
  settimeofday(&tv, nullptr);
  st.timeValid = true;
  if (rtcOk) rtc.adjust(DateTime(epoch));
}

void defaultSettings() { defaultSettings(cfg, DEFAULT_WATERING_HOURS, sizeof(DEFAULT_WATERING_HOURS) / sizeof(int)); }
bool applySettings(JsonVariantConst s) { return applySettings(cfg, s); }
void settingsToJson(JsonObject o) { settingsToJson(cfg, LAYOUT, o); }

uint32_t fnv(const String &s) {
  uint32_t h = 2166136261u;
  for (size_t i = 0; i < s.length(); i++) { h ^= (uint8_t)s[i]; h *= 16777619u; }
  return h;
}

#define SD_DIR "/planter"
#define SD_SETTINGS SD_DIR "/settings.json"
#define SD_LOGS SD_DIR "/log"
void sdLogSettings();

// Saves the settings in use to flash and to the SD card's planter/settings.json. `source` says who changed them:
// "commune" (through the bridge or written to the card by Commune), "phone", "sd" (the file edited by hand).
void commitSettings(const char *source) {
  JsonDocument d;
  settingsToJson(d.to<JsonObject>());
  d["source"] = source;
  String compact;
  serializeJson(d, compact);
  prefs.begin("planter", false);
  bool changed = prefs.getString("settings", "") != compact;
  if (changed) prefs.putString("settings", compact);  // spare the flash when nothing changed
  if (strcmp(source, "commune") != 0 && changed) {
    settingsChangedAt = st.timeValid ? isoTime(nowSec()) : "";
    prefs.putString("changedAt", settingsChangedAt);
  }
  settingsSource = source;
  prefs.putString("source", settingsSource);
  prefs.putString("commune", communeChanged);
  prefs.end();
  if (sdOk) {
    String pretty;
    d["changedOnPlanter"] = settingsChangedAt;
    serializeJsonPretty(d, pretty);
    File f = SD.open(SD_SETTINGS, FILE_WRITE);
    if (f) {
      f.print(pretty);
      f.close();
      prefs.begin("planter", false);
      prefs.putUInt("sdHash", fnv(pretty));  // so a hand edit on a computer is noticed next wake
      prefs.end();
    }
  }
  if (changed) sdLogSettings();
}

void loadSettings() {
  defaultSettings();
  prefs.begin("planter", true);
  String saved = prefs.getString("settings", "");
  settingsSource = prefs.getString("source", "default");
  settingsChangedAt = prefs.getString("changedAt", "");
  communeChanged = prefs.getString("commune", "");
  prefs.end();
  if (saved.length()) {
    JsonDocument doc;
    if (!deserializeJson(doc, saved)) applySettings(doc.as<JsonVariantConst>());
  }
}

// ---------------------------------------------------------------- SD card: a log of everything, and a settings file
bool sdBegin() {
  if (PIN_SD_CS < 0) return false;
  if (!SD.begin(PIN_SD_CS)) { log_w("No SD card"); return false; }
  SD.mkdir(SD_DIR);
  SD.mkdir(SD_LOGS);
  return true;
}

// The settings file was changed on a computer (by hand, or by Commune's "Write settings to card"): use it.
void sdCheckSettings() {
  if (!sdOk || !SD.exists(SD_SETTINGS)) { if (sdOk) commitSettings(String(settingsSource).c_str()); return; }
  File f = SD.open(SD_SETTINGS, FILE_READ);
  if (!f || f.size() > 16384) { if (f) f.close(); return; }
  String text = f.readString();
  f.close();
  prefs.begin("planter", true);
  uint32_t known = prefs.getUInt("sdHash", 0);
  prefs.end();
  if (fnv(text) == known) return;
  JsonDocument d;
  if (deserializeJson(d, text) || !applySettings(d.as<JsonVariantConst>())) {
    log_w("planter/settings.json on the SD card isn't valid JSON; keeping the current settings");
    return;
  }
  const char *changed = d["settingsChanged"] | "";
  bool fromCommune = strlen(changed) > 0 && String(changed) != communeChanged;
  if (fromCommune) communeChanged = changed;
  log_i("Using the settings from the SD card");
  commitSettings(fromCommune ? "commune" : "sd");
}

void fillReading(JsonObject o, const Reading &r) {
  if (r.battery >= 0) o["battery"] = r.battery;
  o["batteryV"] = r.batteryMv / 1000.0f;
  o["solarV"] = r.solarMv / 1000.0f;
  o["charging"] = r.solarMv > 4600;  // the TP4056 charges from about 4.5 V
  o["tank"] = r.tankLow ? "low" : "ok";  // any tank low (older Commune versions read only this)
  JsonArray ts = o["tanks"].to<JsonArray>();
  for (int t = 0; t < TANK_COUNT; t++) {
    JsonObject to = ts.add<JsonObject>();
    to["tank"] = t + 1;
    to["level"] = (r.tankLow >> t) & 1 ? "low" : "ok";
  }
  if (r.headerFull != 2) o["headerFull"] = r.headerFull == 1;
  if (r.airTemp != INT16_MIN) o["airTemp"] = r.airTemp / 10.0f;
  if (r.soilTemp != INT16_MIN) o["soilTemp"] = r.soilTemp / 10.0f;
  JsonArray zs = o["zones"].to<JsonArray>();
  for (int z = 0; z < ZONE_COUNT; z++) {
    JsonObject zo = zs.add<JsonObject>();
    zo["zone"] = z + 1;
    if (r.moisture[z] >= 0) zo["moisture"] = r.moisture[z];
    zo["mv"] = r.mv[z];
  }
}

String reasonText(const Event &e);
void fillEvent(JsonObject o, const Event &e) {
  o["type"] = EVENT_NAMES[e.type];
  if (e.zone) o["zone"] = e.zone;
  if (e.tank) o["tank"] = e.tank;
  if (e.type == EV_WATERED) { o["ml"] = e.ml; o["seconds"] = e.deciSeconds / 10.0f; }
  if (e.type == EV_PUMPED || e.type == EV_PUMP_TIMEOUT) o["seconds"] = e.deciSeconds / 10.0f;
  String why = reasonText(e);
  if (why.length()) o["reason"] = why;
}

// One file per device and month: planter/log/PL-XXXXXX-2026-11.jsonl, one JSON object per line:
// {"r": reading} or {"e": event} or {"s": settings}. Commune imports it ("Import from SD card").
void sdAppend(JsonDocument &line) {
  if (!sdOk) return;
  char month[12] = "no-clock";
  if (st.timeValid) {
    time_t lt = (time_t)nowSec() + cfg.utcOffset;
    struct tm tmv;
    gmtime_r(&lt, &tmv);
    strftime(month, sizeof month, "%Y-%m", &tmv);
  }
  File f = SD.open(String(SD_LOGS "/") + deviceId() + "-" + month + ".jsonl", FILE_APPEND);
  if (!f) return;
  serializeJson(line, f);
  f.print('\n');
  f.close();
}

void sdLogSettings() {
  JsonDocument line;
  JsonObject s = line["s"].to<JsonObject>();
  settingsToJson(s);
  s["source"] = settingsSource;
  if (st.timeValid) s["time"] = isoTime(nowSec());
  if (settingsChangedAt.length()) s["changedOnPlanter"] = settingsChangedAt;
  sdAppend(line);
}

void sdLogWake(const Reading &r) {
  if (!sdOk) return;
  for (int i = 0; i < nWakeEvents; i++) {
    JsonDocument line;
    JsonObject o = line["e"].to<JsonObject>();
    fillEvent(o, wakeEvents[i]);
    if (st.timeValid) o["time"] = isoTime(wakeEvents[i].t);
    sdAppend(line);
  }
  JsonDocument line;
  JsonObject o = line["r"].to<JsonObject>();
  fillReading(o, r);
  if (st.timeValid) o["time"] = isoTime(r.t);  // without a clock, Commune can't place it in time and skips it
  sdAppend(line);
}

// ---------------------------------------------------------------- log in RTC memory (for the bridge)
void addEvent(uint8_t type, int zone = 0, uint8_t reason = R_NONE, int a = 0, int b = 0, uint16_t ml = 0, float seconds = 0, int tank = 0) {
  Event e = {nowSec(), type, (uint8_t)zone, reason, (uint8_t)tank, ml, (uint16_t)min(seconds * 10, 65535.0f), (int16_t)a, (int16_t)b};
  if (st.nEvents == MAX_EVENTS) {  // full: drop the oldest
    memmove(&st.events[0], &st.events[1], sizeof(Event) * (MAX_EVENTS - 1));
    st.nEvents--;
  }
  st.events[st.nEvents++] = e;
  if (nWakeEvents < (int)(sizeof wakeEvents / sizeof wakeEvents[0])) wakeEvents[nWakeEvents++] = e;
  log_i("event %s zone %d", EVENT_NAMES[type], zone);
}

void addReading(const Reading &r) {
  if (st.nReadings == MAX_READINGS) {
    memmove(&st.readings[0], &st.readings[1], sizeof(Reading) * (MAX_READINGS - 1));
    st.nReadings--;
  }
  st.readings[st.nReadings++] = r;
}

// ---------------------------------------------------------------- valves (motorised ball valves on DRV8833s)
const int HELD_PINS[] = {PIN_DRV_SLEEP, PIN_SENSOR_POWER, PIN_STATUS_LED, PIN_PUMP};

// The ESP32's own valve, pump and power pins are held low through deep sleep. Expander pins keep their (low) state
// by themselves, and the DRV8833s' shared sleep pin is held low, so nothing can drive a valve or the pump asleep.
void forEachHeldPin(void (*f)(int)) {
  for (int z = 0; z < ZONE_COUNT; z++) { f(PIN_VALVE_A[z]); f(PIN_VALVE_B[z]); }
  for (int p : HELD_PINS) f(p);
}
void releasePins() { forEachHeldPin([](int p) { if (p >= 0 && p < 100) gpio_hold_dis((gpio_num_t)p); }); }
void holdPinsLow() {
  forEachHeldPin([](int p) {
    ioWrite(p, LOW);
    if (p >= 0 && p < 100) gpio_hold_en((gpio_num_t)p);
  });
  gpio_deep_sleep_hold_en();
}

// Drives the valve motor one way for its travel time, then lets it coast: the valve stays where it is with no power.
void moveValve(int z, bool open) {
  bool forward = open != (bool)VALVE_SWAP_DIRECTION;
  digitalWrite(PIN_DRV_SLEEP, HIGH);
  delay(2);
  ioWrite(PIN_VALVE_A[z], forward ? HIGH : LOW);
  ioWrite(PIN_VALVE_B[z], forward ? LOW : HIGH);
  delay(VALVE_TRAVEL_MS);
  ioWrite(PIN_VALVE_A[z], LOW);
  ioWrite(PIN_VALVE_B[z], LOW);
  digitalWrite(PIN_DRV_SLEEP, LOW);
}

void closeAllValves() {
  for (int z = 0; z < ZONE_COUNT; z++) moveValve(z, false);
  st.valveMaybeOpen = false;
}

// Opens zone z's valve until `ml` has flowed (flow sensor) or for the calibrated time. Returns the ml given.
float water(int z, int ml, float &seconds) {
  uint32_t expectMs = (uint32_t)(ml * MS_PER_ML[z]);
  uint32_t limitMs = min((uint32_t)MAX_OPEN_MS, PIN_FLOW >= 0 ? expectMs * 3 + VALVE_TRAVEL_MS : expectMs);
  flowPulses = 0;
  st.valveMaybeOpen = true;  // if the board resets now, the next boot closes every valve
  uint32_t start = millis();
  moveValve(z, true);        // travel time counts: water starts flowing as the ball turns
  if (PIN_FLOW >= 0) {
    uint32_t target = (uint32_t)(ml * FLOW_PULSES_PER_ML);
    while (flowPulses < target && millis() - start < limitMs) delay(50);
  } else {
    while (millis() - start < limitMs) delay(50);
  }
  moveValve(z, false);
  st.valveMaybeOpen = false;
  seconds = (millis() - start) / 1000.0f;
  if (PIN_FLOW < 0) return ml;
  float given = flowPulses / FLOW_PULSES_PER_ML;
  if (given < ml * 0.8f) addEvent(EV_SLOW_FLOW, z + 1, R_NONE, (int)given, ml);
  return given;
}

// ---------------------------------------------------------------- sensors
bool readFloat(int pin, int level) {
  ioMode(pin, INPUT_PULLUP);
  delay(5);
  bool on = ioRead(pin) == level;
  ioMode(pin, INPUT);  // no pull-up current while asleep
  return on;
}
bool headerIsFull() { return PIN_HEADER_FULL >= 0 && readFloat(PIN_HEADER_FULL, HEADER_FULL_LEVEL); }
bool tankHasWater(int t) { return readFloat(PIN_TANK_FLOAT[t], TANK_HAS_WATER_LEVEL); }  // t: 0 = the first tank
uint8_t readTanks() {
  uint8_t low = 0;
  for (int t = 0; t < TANK_COUNT; t++) if (!tankHasWater(t)) low |= 1 << t;
  return low;
}

Reading measure() {
  Reading r = {};
  r.t = nowSec();
  digitalWrite(PIN_SENSOR_POWER, HIGH);
  delay(300);  // let the soil sensors settle
  for (int z = 0; z < ZONE_COUNT; z++) {
    int mv = ioReadMv(PIN_MOISTURE[z]);
    r.mv[z] = mv < 0 ? 0 : mv;
    int span = MOISTURE_DRY_MV[z] - MOISTURE_WET_MV[z];
    // Below 100 mV the sensor is unplugged (a bare input reads near 0): unknown, not soaking wet.
    r.moisture[z] = span > 0 && mv >= 100 ? constrain((MOISTURE_DRY_MV[z] - mv) * 100 / span, 0, 100) : -1;
  }
  probes.begin();
  probes.setResolution(10);
  probes.requestTemperatures();
  float soil = probes.getTempCByIndex(SOIL_PROBE_INDEX), air = probes.getTempCByIndex(AIR_PROBE_INDEX);
  r.soilTemp = soil > -100 ? (int16_t)(soil * 10) : INT16_MIN;
  r.airTemp = air > -100 ? (int16_t)(air * 10) : INT16_MIN;
  digitalWrite(PIN_SENSOR_POWER, LOW);

  float bv = ioReadMv(PIN_BATTERY) * BATTERY_DIVIDER / 1000.0f;
  r.batteryMv = (uint16_t)(bv * 1000);
  r.battery = bv < 1.0f ? -1 : (int8_t)constrain((bv - BATTERY_EMPTY_V) * 100 / (BATTERY_FULL_V - BATTERY_EMPTY_V), 0, 100);
  r.solarMv = (uint16_t)(max(ioReadMv(PIN_SOLAR), 0) * SOLAR_DIVIDER);
  r.tankLow = readTanks();
  r.headerFull = HAS_PUMP ? (headerIsFull() ? 1 : 0) : 2;
  return r;
}

// ---------------------------------------------------------------- optional pump add-on: refills the header tank
// Runs the pump until the header's float says full. It stops early if the barrel runs low (a pump running dry
// wears out fast) and after PUMP_MAX_MS whatever happens. The overflow back to the barrel covers a stuck float.
// The barrel is tank 1.
void refillHeader(Reading &r) {
  if (!HAS_PUMP || r.headerFull != 0 || (r.tankLow & 1)) return;
  if (r.battery >= 0 && r.battery < cfg.minBattery) return;  // the low-battery event already says why
  uint32_t start = millis();
  bool full = false, barrelLow = false;
  digitalWrite(PIN_PUMP, HIGH);
  while (millis() - start < PUMP_MAX_MS) {
    delay(250);
    if (headerIsFull()) { full = true; break; }
    if (!tankHasWater(0)) { barrelLow = true; break; }
  }
  digitalWrite(PIN_PUMP, LOW);
  float seconds = (millis() - start) / 1000.0f;
  if (full) { addEvent(EV_PUMPED, 0, R_NONE, 0, 0, 0, seconds); r.headerFull = 1; }
  else if (barrelLow) { addEvent(EV_PUMPED, 0, R_BARREL_RAN_LOW, 0, 0, 0, seconds, 1); r.tankLow |= 1; }
  else addEvent(EV_PUMP_TIMEOUT, 0, R_NONE, PUMP_MAX_MS / 1000, 0, 0, seconds);
}

// ---------------------------------------------------------------- deciding when to water (rules in planter_logic.h)
void decideWatering(Reading &r, bool &watered) {
  int32_t slot = wateringSlot(cfg, st.timeValid, nowSec());
  if (slot < 0) return;
  int32_t today = localSec() / 86400;
  for (int z = 0; z < ZONE_COUNT; z++) {
    if (st.lastSlot[z] == slot) continue;  // each slot runs once, however often the board wakes in that hour
    st.lastSlot[z] = slot;
    int tank = ZONE_TANK[z];
    // With the pump add-on, zones on tank 1 drink from the header tank, which still holds water when the barrel is low.
    bool tankLow = (r.tankLow >> (tank - 1)) & 1 && !(HAS_PUMP && tank == 1);
    ZoneInput in = {r.moisture[z], tankLow, r.battery, st.mlToday[z], today, st.lastWaterDay[z]};
    ZoneDecision d = decideZone(cfg, z, in);
    if (!d.water) {
      if (d.reason == R_NO_SENSOR) addEvent(EV_ERROR, z + 1, R_NO_SENSOR);
      else if (d.reason == R_TANK) addEvent(EV_SKIPPED, z + 1, R_TANK, tank, 0, 0, 0, tank);
      else if (d.reason != R_NONE) addEvent(EV_SKIPPED, z + 1, d.reason, d.a, d.b);
      continue;
    }
    float seconds = 0;
    float given = water(z, d.ml, seconds);
    st.mlToday[z] += (uint32_t)given;
    st.lastWatered[z] = nowSec();
    st.lastWaterDay[z] = today;
    addEvent(EV_WATERED, z + 1, R_NONE, 0, 0, (uint16_t)given, seconds);
    watered = true;
  }
}

String reasonText(const Event &e) {
  char b[80];
  switch (e.reason) {
    case R_MOIST: snprintf(b, sizeof b, "moist enough (%d%% >= %d%%)", e.a, e.b); break;
    case R_DAILY_MAX: snprintf(b, sizeof b, "had its most for today (%d ml)", e.a); break;
    case R_NOT_TODAY: snprintf(b, sizeof b, "scheduled every %d days; next in %d", e.a, e.b); break;
    case R_BATTERY: snprintf(b, sizeof b, "battery low (%d%% < %d%%)", e.a, e.b); break;
    case R_TANK:
      if (TANK_COUNT == 1) return "rain tank low";
      snprintf(b, sizeof b, "tank %d low", e.a);
      break;
    case R_NO_SENSOR: return "soil sensor not answering or not calibrated (see planter_config.h)";
    case R_BARREL_RAN_LOW: return "stopped: the rain barrel ran low before the header tank filled";
    case R_RESET: return "the board restarted, so every valve was closed";
    case R_BY_HAND: return "watered by hand from the setup page";
    default:
      if (e.type == EV_SLOW_FLOW) { snprintf(b, sizeof b, "only %d of %d ml flowed: tank empty or line blocked?", e.a, e.b); break; }
      if (e.type == EV_PUMP_TIMEOUT) { snprintf(b, sizeof b, "header not full after %d s: pump dry, a leak, or a stuck float?", e.a); break; }
      return "";
  }
  return String(b);
}

// ---------------------------------------------------------------- the Wi-Fi bridge (optional)
String buildReport() {
  JsonDocument doc;
  JsonObject dev = doc["device"].to<JsonObject>();
  dev["id"] = deviceId();
  dev["name"] = DEVICE_NAME;
  dev["firmware"] = FIRMWARE;
  doc["sentAt"] = nowSec();
  doc["timeValid"] = st.timeValid;
  JsonObject s = doc["settings"].to<JsonObject>();  // so Commune can see settings changed on the planter itself
  settingsToJson(s);
  doc["settingsSource"] = settingsSource;
  doc["settingsChangedOnPlanter"] = settingsChangedAt;
  JsonArray rs = doc["readings"].to<JsonArray>();
  for (int i = 0; i < st.nReadings; i++) {
    JsonObject o = rs.add<JsonObject>();
    o["t"] = st.readings[i].t;
    fillReading(o, st.readings[i]);
  }
  JsonArray es = doc["events"].to<JsonArray>();
  for (int i = 0; i < st.nEvents; i++) {
    JsonObject o = es.add<JsonObject>();
    o["t"] = st.events[i].t;
    fillEvent(o, st.events[i]);
  }
  String out;
  serializeJson(doc, out);
  return out;
}

bool connectWifi() {
  if (strlen(WIFI_SSID) == 0) return false;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) delay(100);
  return WiFi.status() == WL_CONNECTED;
}

void wifiOff() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
}

bool report() {
  if (!connectWifi()) { log_w("Wi-Fi not reachable; keeping %d readings", st.nReadings); wifiOff(); return false; }
  HTTPClient http;
  http.setTimeout(8000);
  http.begin(String("http://") + BRIDGE_HOST + ":" + BRIDGE_PORT + "/planter/report");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Planter-Key", PLANTER_KEY);
  int code = http.POST(buildReport());
  bool ok = false;
  if (code == 200) {
    JsonDocument reply;
    if (!deserializeJson(reply, http.getString())) {
      setClock(reply["now"] | 0);
      JsonVariantConst s = reply["settings"];
      // Commune's settings are used only when they changed in Commune since the planter last took them, so a
      // change made on the phone page or the SD card stays until someone changes the settings in Commune.
      String changed = s["settingsChanged"] | "";
      if (communeSettingsAreNew(changed.c_str(), communeChanged.c_str()) && applySettings(s)) {
        communeChanged = changed;
        commitSettings("commune");
      } else if (reply["utcOffset"].is<int>() && (int32_t)reply["utcOffset"] != cfg.utcOffset) {
        cfg.utcOffset = reply["utcOffset"];  // daylight saving changed
        commitSettings(String(settingsSource).c_str());
      }
    }
    st.nReadings = st.nEvents = 0;
    st.wakesSinceReport = 0;
    ok = true;
  } else {
    log_w("Bridge answered %d; keeping %d readings", code, st.nReadings);
  }
  http.end();
  wifiOff();
  return ok;
}

// ---------------------------------------------------------------- the phone setup page (the planter's own hotspot)
#include "phone_page.h"

// ---------------------------------------------------------------- sleep
uint64_t secondsToSleep() {
  uint32_t sleep = cfg.wakeMinutes * 60;
  if (st.timeValid) {  // wake right at the next watering hour if it comes before the next regular reading
    uint32_t until = secondsToNextWateringHour(cfg, nowSec());
    if (until) sleep = min(sleep, until);
  }
  return max(sleep, (uint32_t)60);
}

void goToSleep() {
  uint64_t s = secondsToSleep();
  log_i("sleeping %llu s", s);
  if (sdOk) SD.end();
  Serial.flush();
  holdPinsLow();
  esp_sleep_enable_timer_wakeup(s * 1000000ULL);
  if (PIN_SETUP_BUTTON >= 0) {  // the setup button wakes the board too
    rtc_gpio_pullup_en((gpio_num_t)PIN_SETUP_BUTTON);
    rtc_gpio_pulldown_dis((gpio_num_t)PIN_SETUP_BUTTON);
    esp_sleep_enable_ext0_wakeup((gpio_num_t)PIN_SETUP_BUTTON, 0);
  }
  esp_deep_sleep_start();
}

void setup() {
  Serial.begin(115200);
  releasePins();
  Wire.begin(PIN_RTC_SDA, PIN_RTC_SCL);  // the clock module, and any expanders for more zones and tanks
  for (int z = 0; z < ZONE_COUNT; z++) {
    ioMode(PIN_VALVE_A[z], OUTPUT); ioWrite(PIN_VALVE_A[z], LOW);
    ioMode(PIN_VALVE_B[z], OUTPUT); ioWrite(PIN_VALVE_B[z], LOW);
  }
  pinMode(PIN_DRV_SLEEP, OUTPUT);
  digitalWrite(PIN_DRV_SLEEP, LOW);
  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);
  if (HAS_PUMP) { pinMode(PIN_PUMP, OUTPUT); digitalWrite(PIN_PUMP, LOW); }
  pinMode(PIN_SENSOR_POWER, OUTPUT);
  digitalWrite(PIN_SENSOR_POWER, LOW);
  if (PIN_SETUP_BUTTON >= 0) { rtc_gpio_deinit((gpio_num_t)PIN_SETUP_BUTTON); pinMode(PIN_SETUP_BUTTON, INPUT_PULLUP); }
  analogSetAttenuation(ADC_11db);
  if (PIN_FLOW >= 0) { pinMode(PIN_FLOW, INPUT_PULLUP); attachInterrupt(PIN_FLOW, onFlowPulse, FALLING); }

  esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  bool buttonWake = cause == ESP_SLEEP_WAKEUP_EXT0;
  bool fromSleep = (cause == ESP_SLEEP_WAKEUP_TIMER || buttonWake) && st.magic == STATE_MAGIC;
  if (!fromSleep) {  // power-up, reset or brownout: start fresh, and make sure no valve was left open
    memset(&st, 0, sizeof st);
    st.magic = STATE_MAGIC;
    for (int z = 0; z < MAX_ZONES; z++) { st.lastSlot[z] = -1; st.lastWaterDay[z] = -1000; }
    closeAllValves();
    addEvent(EV_VALVES_CLOSED, 0, R_RESET);
  } else if (st.valveMaybeOpen) {
    closeAllValves();
    addEvent(EV_VALVES_CLOSED, 0, R_RESET);
  }
  st.boots++;

  // The clock module keeps real time through power cuts and long sleeps (the ESP32's own clock drifts).
  rtcOk = rtc.begin();
  if (rtcOk && !rtc.lostPower()) {
    struct timeval tv = {(time_t)rtc.now().unixtime(), 0};
    settimeofday(&tv, nullptr);
    st.timeValid = true;
  }

  loadSettings();
  sdOk = sdBegin();
  sdCheckSettings();  // settings edited on the SD card take over
  if (!fromSleep) sdLogSettings();  // after a power-up or new firmware, so the card records the zones and tanks too

  Reading r = measure();
  if (buttonWake || (PIN_SETUP_BUTTON >= 0 && digitalRead(PIN_SETUP_BUTTON) == LOW)) runPhonePage(r);

  int32_t day = localSec() / 86400;
  if (day != st.day) { st.day = day; memset(st.mlToday, 0, sizeof st.mlToday); st.batteryWarned = false; }
  for (int t = 0; t < TANK_COUNT; t++)
    if ((r.tankLow >> t) & 1 && !((st.tankWasLow >> t) & 1)) addEvent(EV_TANK_LOW, 0, R_NONE, 0, 0, 0, 0, t + 1);
  st.tankWasLow = r.tankLow;
  if (r.battery >= 0 && r.battery < cfg.minBattery && !st.batteryWarned) { addEvent(EV_LOW_BATTERY, 0, R_BATTERY, r.battery, cfg.minBattery); st.batteryWarned = true; }

  bool watered = false;
  refillHeader(r);                // pump add-on only: top up the header tank first
  decideWatering(r, watered);
  if (watered && HAS_PUMP) { r.headerFull = headerIsFull() ? 1 : 0; refillHeader(r); }
  addReading(r);
  sdLogWake(r);
  log_i("boot %u: battery %d%%, solar %u mV, tanks low 0x%x, zone 1 %d%%, sd %d, clock %d", st.boots, r.battery, r.solarMv,
        r.tankLow, r.moisture[0], sdOk, rtcOk);

  st.wakesSinceReport++;
  bool firstContact = !st.timeValid && st.boots <= 3;  // with no clock module, the first wakes try to set the time
  if (watered || firstContact || st.wakesSinceReport >= (uint32_t)cfg.reportEvery || st.nReadings >= MAX_READINGS - 2) report();
  goToSleep();
}

void loop() {}  // never reached: every wake runs setup() and goes back to sleep
