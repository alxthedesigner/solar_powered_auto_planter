// Tests planter_logic.h (settings and the watering rules) on a computer, with no ESP32. Run ./run.sh.
//
//   planter_test                run the tests
//   planter_test apply ZONES    read settings JSON on stdin (planter.json from Commune, the SD card's settings.json, or
//                               what the phone page posts), apply it the way the planter does, and print the
//                               settings the planter would then use (and report back), for a planter with ZONES zones
#include <stdio.h>
#include <iostream>
#include <iterator>
#include <string>

#include "../../src/planter_logic.h"

static int failures = 0, checks = 0;
#define CHECK(cond)                                                     \
  do {                                                                  \
    checks++;                                                           \
    if (!(cond)) { failures++; printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); } \
  } while (0)

static const int HOURS[] = {7, 19};
static const int ZONE_TANK_2[] = {1, 1};
static const int ZONE_TANK_8[] = {1, 1, 2, 2, 3, 3, 4, 4};

static Settings fresh() {
  Settings c;
  defaultSettings(c, HOURS, 2);
  return c;
}
static bool apply(Settings &c, const char *json) {
  JsonDocument d;
  if (deserializeJson(d, json)) return false;
  return applySettings(c, d.as<JsonVariantConst>());
}
static ZoneInput dry(int moisture = 20) { return {moisture, false, 80, 0, 100, -1000}; }

static void testDefaults() {
  Settings c = fresh();
  CHECK(c.nHours == 2 && c.hours[0] == 7 && c.hours[1] == 19);
  CHECK(c.wakeMinutes == 60 && c.reportEvery == 3 && c.minBattery == 25);
  for (int z = 0; z < MAX_ZONES; z++) {
    CHECK(c.zones[z].enabled && !c.zones[z].schedule);
    CHECK(c.zones[z].moistureBelow == 40 && c.zones[z].ml == 1000 && c.zones[z].maxMlPerDay == 4000);
  }
}

// What Commune writes (planter.json): extra keys like names, tanks and growing are ignored by the planter.
static void testCommuneSettings() {
  Settings c = fresh();
  CHECK(apply(c, R"({"communePlanterSettings":1,"settingsChanged":"2026-11-22T09:00:00-08:00","utcOffset":-28800,
    "wakeMinutes":30,"reportEveryWakes":2,"wateringHours":[19,6,7,7,30,-1],"minBattery":35,
    "tanks":[{"tank":1,"name":"Rain drum"}],
    "zones":[{"zone":1,"name":"Tomatoes","enabled":true,"mode":"moisture","everyDays":1,"moistureBelow":35,"ml":1500,"maxMlPerDay":3000},
             {"zone":2,"name":"Herbs","enabled":false,"mode":"schedule","everyDays":3,"moistureBelow":30,"ml":500,"maxMlPerDay":1000},
             {"zone":9,"ml":1},{"zone":0,"ml":1}],
    "growing":{"1":[{"name":"Tomato"}]}})"));
  CHECK(c.wakeMinutes == 30 && c.reportEvery == 2 && c.minBattery == 35 && c.utcOffset == -28800);
  CHECK(c.nHours == 3 && c.hours[0] == 6 && c.hours[1] == 7 && c.hours[2] == 19);  // sorted, once each, 0-23 only
  CHECK(c.zones[0].moistureBelow == 35 && c.zones[0].ml == 1500 && c.zones[0].maxMlPerDay == 3000 && !c.zones[0].schedule);
  CHECK(!c.zones[1].enabled && c.zones[1].schedule && c.zones[1].everyDays == 3 && c.zones[1].ml == 500);
  CHECK(c.zones[2].ml == 1000);  // zones not sent keep theirs
}

// The phone page sends only what's on it; the rest stays.
static void testPartialAndRanges() {
  Settings c = fresh();
  CHECK(apply(c, R"({"wateringHours":[8],"zones":[{"zone":2,"ml":250}]})"));
  CHECK(c.nHours == 1 && c.hours[0] == 8 && c.wakeMinutes == 60);
  CHECK(c.zones[1].ml == 250 && c.zones[1].moistureBelow == 40 && c.zones[0].ml == 1000);
  CHECK(apply(c, R"({"wakeMinutes":1,"minBattery":200,"zones":[{"zone":1,"ml":999999,"everyDays":0,"moistureBelow":-5}]})"));
  CHECK(c.wakeMinutes == 5 && c.minBattery == 90);
  CHECK(c.zones[0].ml == 20000 && c.zones[0].everyDays == 1 && c.zones[0].moistureBelow == 0);
  CHECK(apply(c, R"({"wateringHours":[]})") && c.nHours == 0);  // no watering hours: never waters
  CHECK(!apply(c, "[1,2]") && !apply(c, "not json"));
}

static void testRoundTrip(int zones, const int *zoneTank, int tanks) {
  Settings a = fresh();
  CHECK(apply(a, R"({"wateringHours":[5,6,7,8],"zones":[{"zone":1,"mode":"schedule","everyDays":7,"ml":300},{"zone":8,"enabled":false}]})"));
  Layout l = {zones, tanks, zoneTank, false, false};
  JsonDocument d;
  settingsToJson(a, l, d.to<JsonObject>());
  CHECK(d["zones"].size() == (size_t)zones);
  CHECK(d["layout"]["zones"].size() == (size_t)zones && d["layout"]["tanks"].size() == (size_t)tanks);
  CHECK(d["layout"]["zones"][zones - 1]["tank"] == zoneTank[zones - 1]);
  Settings b = fresh();
  CHECK(applySettings(b, d.as<JsonVariantConst>()));
  CHECK(b.nHours == 4 && b.hours[3] == 8 && b.zones[0].schedule && b.zones[0].everyDays == 7 && b.zones[0].ml == 300);
  CHECK(b.zones[zones - 1].enabled == a.zones[zones - 1].enabled);
}

static void testCommuneOnlyWhenChanged() {
  CHECK(communeSettingsAreNew("2026-11-22T09:00:00Z", ""));
  CHECK(!communeSettingsAreNew("2026-11-22T09:00:00Z", "2026-11-22T09:00:00Z"));  // a phone change stays
  CHECK(communeSettingsAreNew("2026-11-23T10:00:00Z", "2026-11-22T09:00:00Z"));
  CHECK(!communeSettingsAreNew("", "x") && !communeSettingsAreNew(nullptr, ""));
}

static void testSlots() {
  Settings c = fresh();  // 7 and 19, UTC
  uint32_t day = 1763769600;  // 2025-11-22 00:00 UTC
  CHECK(wateringSlot(c, true, day + 7 * 3600 + 30) >= 0);
  CHECK(wateringSlot(c, true, day + 8 * 3600) == -1);
  CHECK(wateringSlot(c, true, day + 7 * 3600) == wateringSlot(c, true, day + 7 * 3600 + 3599));  // once per hour
  CHECK(secondsToNextWateringHour(c, day + 8 * 3600) == 11 * 3600 + 20);
  c.utcOffset = -8 * 3600;  // 7:00 local is 15:00 UTC
  CHECK(wateringSlot(c, true, day + 15 * 3600) >= 0 && wateringSlot(c, true, day + 7 * 3600) == -1);
  CHECK(wateringSlot(c, false, 1000) == 0 && wateringSlot(c, false, 50000) == 1);  // no clock: every 12 hours
  apply(c, R"({"wateringHours":[]})");
  CHECK(secondsToNextWateringHour(c, day) == 0);
}

static void testDecisions() {
  Settings c = fresh();
  ZoneDecision d = decideZone(c, 0, dry());
  CHECK(d.water && d.ml == 1000);
  d = decideZone(c, 0, dry(55));
  CHECK(!d.water && d.reason == R_MOIST && d.a == 55 && d.b == 40);
  ZoneInput in = dry();
  in.tankLow = true;
  CHECK(decideZone(c, 0, in).reason == R_TANK);
  in = dry(); in.battery = 10;
  d = decideZone(c, 0, in);
  CHECK(!d.water && d.reason == R_BATTERY && d.a == 10 && d.b == 25);
  in = dry(); in.battery = -1;  // unknown battery doesn't block watering
  CHECK(decideZone(c, 0, in).water);
  in = dry(); in.mlToday = 3500;
  d = decideZone(c, 0, in);
  CHECK(d.water && d.ml == 500);  // tops up to the daily limit
  in.mlToday = 4000;
  CHECK(decideZone(c, 0, in).reason == R_DAILY_MAX);
  CHECK(decideZone(c, 0, dry(-1)).reason == R_NO_SENSOR);
  apply(c, R"({"zones":[{"zone":1,"enabled":false},{"zone":2,"ml":0}]})");
  CHECK(!decideZone(c, 0, dry()).water && decideZone(c, 0, dry()).reason == R_NONE);
  CHECK(!decideZone(c, 1, dry()).water && decideZone(c, 1, dry()).reason == R_NONE);

  // Schedule: waters whatever the soil says, every N days.
  Settings s = fresh();
  apply(s, R"({"zones":[{"zone":1,"mode":"schedule","everyDays":3,"ml":400}]})");
  in = dry(90);  // soaking wet, still waters
  in.today = 100; in.lastWaterDay = -1000;
  d = decideZone(s, 0, in);
  CHECK(d.water && d.ml == 400);
  in.lastWaterDay = 100;  // already watered today: the evening hour waters too
  CHECK(decideZone(s, 0, in).water);
  in.today = 101;
  d = decideZone(s, 0, in);
  CHECK(!d.water && d.reason == R_NOT_TODAY && d.b == 2);
  in.today = 103;
  CHECK(decideZone(s, 0, in).water);
  in.tankLow = true;
  CHECK(decideZone(s, 0, in).reason == R_TANK);  // a schedule still stops for an empty tank
}

int main(int argc, char **argv) {
  if (argc >= 2 && std::string(argv[1]) == "apply") {
    int zones = argc >= 3 ? atoi(argv[2]) : 2;
    if (zones < 1 || zones > MAX_ZONES) zones = 2;
    std::string in((std::istreambuf_iterator<char>(std::cin)), std::istreambuf_iterator<char>());
    Settings c = fresh();
    if (!apply(c, in.c_str())) { fprintf(stderr, "not settings\n"); return 2; }
    Layout l = {zones, 1, ZONE_TANK_8, false, false};
    JsonDocument out;
    settingsToJson(c, l, out.to<JsonObject>());
    serializeJson(out, std::cout);
    std::cout << "\n";
    return 0;
  }
  testDefaults();
  testCommuneSettings();
  testPartialAndRanges();
  testRoundTrip(2, ZONE_TANK_2, 1);
  testRoundTrip(8, ZONE_TANK_8, 4);
  testCommuneOnlyWhenChanged();
  testSlots();
  testDecisions();
  printf("%d checks, %d failed\n", checks, failures);
  return failures ? 1 : 0;
}
