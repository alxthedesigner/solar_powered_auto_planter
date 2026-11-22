// Copy this file to planter_config.h (same folder) and fill it in. planter_config.h is kept out of git: it holds your Wi-Fi password.
#pragma once

// ---------------------------------------------------------------- network (optional: the planter waters without it)
// Three ways to reach the planter, any or all of them:
//   Wi-Fi bridge  - posts readings to bridge.py (on a Raspberry Pi) when the network is up
//   phone page    - press the setup button: the planter opens its own hotspot with a settings page
//   SD card       - every reading is logged to the card, and planter/settings.json on it can be edited
#define WIFI_SSID      "YourNetwork"
#define WIFI_PASSWORD  "YourPassword"
#define BRIDGE_HOST    "192.168.1.50"   // the Raspberry Pi running commune_link/bridge.py (its local IP address)
#define BRIDGE_PORT    8650
#define PLANTER_KEY    "change-me"      // the same as the bridge's --key
#define DEVICE_NAME    "Raised bed"     // shown in Commune
#define UTC_OFFSET_FALLBACK (-8 * 3600) // your time zone until Commune, the bridge or your phone sets it

// ---------------------------------------------------------------- phone setup page (the planter's own hotspot)
#define PIN_SETUP_BUTTON  15     // push button to GND: wakes the board and opens the setup hotspot
#define PIN_STATUS_LED    2      // lit while the setup hotspot is open (the DevKit's own LED)
#define SETUP_PASSWORD    "planter-setup"  // hotspot password, 8+ characters: change it
#define SETUP_MINUTES     10     // the hotspot closes after this long with no one using the page

// ---------------------------------------------------------------- SD card and clock (work with no Wi-Fi at all)
#define PIN_SD_CS         5      // microSD module CS (SCK 18, MISO 19, MOSI 23). -1 = no SD card module
#define PIN_RTC_SDA       21     // DS3231 clock module: keeps time through power cuts with its coin cell
#define PIN_RTC_SCL       22

// ---------------------------------------------------------------- zones: one valve and one soil sensor each
// A pin is an ESP32 GPIO, XPIN(chip, n) on an MCP23017 expander, or ADC_CH(chip, c) on an ADS1115 (see planter_io.h).
// Up to 8 zones. "Adding zones and tanks" at the end of this file shows a bigger build.
#define ZONE_COUNT 2
static const int PIN_MOISTURE[ZONE_COUNT]    = {35, 34};   // capacitive soil sensors, signal (ESP32 ADC1 pins or ADC_CH); zone 1 on 35 as in Plantwatery v12
static const int PIN_VALVE_A[ZONE_COUNT]     = {25, 27};   // DRV8833 AIN1, BIN1
static const int PIN_VALVE_B[ZONE_COUNT]     = {26, 14};   // DRV8833 AIN2, BIN2
#define PIN_DRV_SLEEP     17     // every DRV8833's SLP/EEP: high only while a valve is moving
#define VALVE_TRAVEL_MS   6000   // how long the motorised ball valve takes to open or close (check yours: usually 3-6 s)
#define VALVE_SWAP_DIRECTION 0   // 1 if "open" closes your valves (or just swap a valve's two wires)
#define MAX_OPEN_MS       (10UL * 60 * 1000)  // never leave a valve open longer than this

// Calibration: how long the valve must stay open per ml at your tank's height. Measure it: water a measuring jug
// for 60 s with a full tank, then MS_PER_ML = 60000 / ml collected. Gravity flow slows as the tank empties.
static const float MS_PER_ML[ZONE_COUNT]     = {130.0f, 130.0f};

// Optional flow sensor on the main line (YF-S401 style). -1 = none: watering is timed with MS_PER_ML instead.
#define PIN_FLOW            -1
#define FLOW_PULSES_PER_ML  5.88f

// Soil sensor calibration, in millivolts: hold the sensor in air (dry), then in a glass of water up to its line (wet).
static const int MOISTURE_DRY_MV[ZONE_COUNT] = {2600, 2600};
static const int MOISTURE_WET_MV[ZONE_COUNT] = {1150, 1150};

// ---------------------------------------------------------------- tanks (rain drums): a low float switch each
// Up to 4. A zone is skipped while the tank that feeds it is low.
#define TANK_COUNT 1
static const int PIN_TANK_FLOAT[TANK_COUNT]  = {13};       // float switch to GND near the tank's floor (the barrel's, with the pump add-on)
#define TANK_HAS_WATER_LEVEL LOW // LOW: the switch is closed while it floats (water above it)
static const int ZONE_TANK[ZONE_COUNT]       = {1, 1};     // which tank feeds each zone (1 = the first)

// ---------------------------------------------------------------- power and other sensors
#define PIN_SENSOR_POWER  4      // powers the soil sensors and temperature probes only while awake (more than 4 sensors:
                                 // switch their power through a small P-MOSFET or transistor instead, as a GPIO gives ~20 mA)
#define PIN_BATTERY       32     // battery through 27k (top) / 100k (bottom) divider
#define BATTERY_DIVIDER   1.27f  // (27k + 100k) / 100k
#define BATTERY_EMPTY_V   3.30f
#define BATTERY_FULL_V    4.15f
#define PIN_SOLAR         39     // solar panel + through 100k (top) / 47k (bottom) divider (VN pin; input only)
#define SOLAR_DIVIDER     3.128f // (100k + 47k) / 47k

// ---------------------------------------------------------------- optional pump add-on (off by default)
// Default build: the rain tank itself is raised and feeds the valves by gravity. No pump, fewest moving parts.
// Add-on: a pump (Plantwatery v12) lifts rain from a barrel on the ground into a small raised header tank.
// To use it, set PIN_PUMP to 33 and wire the header tank's full float to PIN_HEADER_FULL. Tank 1 is then the barrel.
#define PIN_PUMP          -1     // 33 with the add-on: logic-level MOSFET module SIG (v12's pump pin)
#define PIN_HEADER_FULL   12     // header tank float switch to GND, mounted near the top
#define HEADER_FULL_LEVEL LOW    // LOW: the switch closes when the rising water lifts its float
#define PUMP_MAX_MS       (5UL * 60 * 1000)  // stop the pump after this even if the header never says full
#define PIN_ONEWIRE       16     // DS18B20 probes, 4.7k pull-up to the sensor power pin
#define SOIL_PROBE_INDEX  0      // which probe is in the soil (swap with AIR if the readings look reversed)
#define AIR_PROBE_INDEX   1

// ---------------------------------------------------------------- defaults until Commune sends settings
#define DEFAULT_WAKE_MINUTES   60
#define DEFAULT_REPORT_EVERY   3
#define DEFAULT_MIN_BATTERY    25
static const int DEFAULT_WATERING_HOURS[] = {7, 19};
// Sized for a 2 ft x 6 ft bed (12 sq ft) in two zones of 6 sq ft: 1 L twice a day per zone is about 1 inch of
// water a week across the bed. Raise DEFAULT_ML toward 2000 in hot weather; the daily limit already allows it.
#define DEFAULT_SCHEDULE       false  // false: water when the soil is dry; true: water at every watering hour
#define DEFAULT_EVERY_DAYS     1      // schedule mode: 1 = daily, 7 = weekly
#define DEFAULT_MOISTURE_BELOW 40
#define DEFAULT_ML             1000
#define DEFAULT_MAX_ML_PER_DAY 4000

// ---------------------------------------------------------------- adding zones and tanks
// The ESP32 has no free pins left after two zones, so a bigger planter adds two small boards to the clock's I2C bus
// (SDA 21, SCL 22, 3.3 V): an MCP23017 expander (16 pins, for valves and floats) and an ADS1115 (4 analog inputs,
// for soil sensors). Each extra pair of valves needs another DRV8833: VM from the 5 V boost, SLP/EEP on PIN_DRV_SLEEP,
// its four inputs on the expander. Valves water one at a time, so the 1 A boost still copes.
// Example: 4 zones fed by 2 drums (zones 1-2 from the first drum, zones 3-4 from a second one).
//
//   #define ZONE_COUNT 4
//   static const int PIN_MOISTURE[ZONE_COUNT]    = {35, 34, ADC_CH(0, 0), ADC_CH(0, 1)};
//   static const int PIN_VALVE_A[ZONE_COUNT]     = {25, 27, XPIN(0, 0), XPIN(0, 2)};   // second DRV8833: AIN1, BIN1
//   static const int PIN_VALVE_B[ZONE_COUNT]     = {26, 14, XPIN(0, 1), XPIN(0, 3)};   //                 AIN2, BIN2
//   static const float MS_PER_ML[ZONE_COUNT]     = {130, 130, 130, 130};
//   static const int MOISTURE_DRY_MV[ZONE_COUNT] = {2600, 2600, 2600, 2600};
//   static const int MOISTURE_WET_MV[ZONE_COUNT] = {1150, 1150, 1150, 1150};
//   #define TANK_COUNT 2
//   static const int PIN_TANK_FLOAT[TANK_COUNT]  = {13, XPIN(0, 8)};
//   static const int ZONE_TANK[ZONE_COUNT]       = {1, 1, 2, 2};
//
// Then name the zones and drums on Commune's Planter page: it shows whatever the planter reports it has.
