# Automated planter system

The Solar Rain Planter waters a 2 × 6 ft bed from collected rain and runs on sunlight, with as few moving parts as possible. Rain fills a 55-gallon drum raised on a stand, and gravity carries it through one valve per zone to the plants, with no pump. It combines the gravity feed, water rail and per-zone valves of [Rainmaker 9000](https://github.com/AlexanderPinkerton/rainmaker9000) with the solar power (v12: TP4056, 18650 and TPS61023 5 V boost), deep sleep and moisture-triggered watering of [Plantwatery](https://github.com/Lumics/Plantwatery). Rainmaker's 12 V solenoids, relays and CYD touchscreen are swapped for 5 V motorised ball valves, a DRV8833 and an ESP32 DevKit. The code here is written fresh for this project and borrows ideas from those two, not code.

**Build guide:** [docs/build-guide.html](docs/build-guide.html) has the infrastructure drawing, parts list, ESP32 pins, build order, calibration and safety notes.

```
automated_planter_system/
  firmware/
    src/main.cpp            every wake: sensors, watering, SD card log, bridge report, deep sleep
    src/planter_logic.h     the rules: settings in and out, when each zone is watered (no hardware in it)
    src/planter_io.h        pins on the ESP32, or on I2C expanders for more zones and tanks
    src/phone_page.h        the setup hotspot's page
    src/config_example.h    copy to planter_config.h: Wi-Fi, pins, zones, tanks, calibration
    test/host/run.sh        tests the rules on a computer, no ESP32 needed
  commune_link/    the bridge: a mailbox between the planter and Commune (Python, standard library)
  docs/            build guide
```

## How it reaches Commune

It runs entirely on solar power, and keeps watering with no network at all. Readings and settings can travel three ways:

```
                       ┌── Wi-Fi ──▶ Raspberry Pi (bridge.py, mailbox) ◀── home Wi-Fi ──▶ Commune (Mac/PC)
Planter (ESP32) ───────┼── SD card: carry it to the Commune computer ─────────────────────▶ Commune
  clock module,        └── phone: press the setup button, join "Planter-XXXXXX", change settings there
  SD card log
```

| Way | For | How |
|---|---|---|
| Wi-Fi bridge | everyday use | The planter posts to the Pi; Commune syncs with it every 2 minutes while it's open. |
| SD card | no power or network anywhere | Every reading is logged to the card. In Commune: **Import readings** and **Write settings to card**. |
| Phone page | Wi-Fi is down | The planter's own hotspot and settings page. It also sets the clock from the phone. |

A change made on the phone page or the SD card stays until someone changes the settings in Commune, and Commune shows it with a choice to keep it. The format is in [docs/integrations/planter.md](../commune_offline_community_suite/docs/integrations/planter.md).

## Firmware

```bash
cd firmware
cp src/config_example.h src/planter_config.h   # Wi-Fi, bridge address and key, setup password, pins, calibration
pio run -t upload && pio device monitor
```

- **Every wake** (hourly by default) it closes the valves if the last start wasn't a planned wake, sets its clock from the DS3231 module, checks the SD card for edited settings, then reads soil moisture per zone, soil and air temperature, battery, solar voltage and the drum's float.
- **Watering modes, per zone:** *when the soil is dry* (the default) waters at a watering hour only if the soil is below its threshold. *On a schedule* waters the set ml at every watering hour, every N days. For hourly watering, set the hours to a range such as `6-20`. Defaults for a 12 sq ft bed are 7:00 and 19:00, below 40%, 1000 ml, at most 4000 ml a day per zone.
- **Safety:** a zone is skipped when the drum is low, the battery is below its minimum, or it has had its daily limit. Valves close after any unplanned reset, and valve pins are held low while the board sleeps.
- **Logging:** every reading and event goes to `planter/log/` on the SD card, and to the bridge every third wake (and straight after watering). Up to 48 readings wait in memory while the bridge can't be reached.
- **Phone page:** the setup button (GPIO 15) wakes the board and opens the hotspot `Planter-XXXXXX` (password `SETUP_PASSWORD`). It closes after `SETUP_MINUTES` with no one using it.
- **Pump add-on (off by default):** set `PIN_PUMP` to `33` to keep the drum on the ground and refill a small raised header tank instead.
- **Tests:** `test/host/run.sh` checks the settings and watering rules on your computer (72 checks). Run `pio run` once first so ArduinoJson is downloaded.

## Adding zones and tanks

Zones (up to 8) and tanks (up to 4) are lists in `planter_config.h`: each zone has a soil sensor pin, two valve pins and the tank that feeds it, and each tank has a float pin. The ESP32 has no pins left after two zones, so a bigger planter adds two small boards to the clock's I2C bus: an **MCP23017** (16 pins for valves and floats, `XPIN(chip, n)`) and an **ADS1115** (4 soil sensor inputs, `ADC_CH(chip, c)`). Each extra pair of valves needs another DRV8833, sharing the sleep pin. The end of `config_example.h` has a worked 4-zone, 2-drum example.

The planter reports its zones and tanks to Commune, so the Planter page shows the right number of zone settings and a tile for each drum. Name them there. A zone is skipped while its own drum is low; the others keep watering.

## Bridge (on a Raspberry Pi)

```bash
python3 -m commune_link.bridge --key change-me   # run from automated_planter_system/; data goes in ~/planter-bridge
```

It listens on port 8650 and needs Python 3 only. Use the same key as `PLANTER_KEY` in `planter_config.h`, and set `BRIDGE_HOST` there to the Pi's address. In Commune, open the **Planter** page and enter the Pi's address and key under **How the planter reaches Commune**. To start it when the Pi boots, add a systemd service or a `@reboot` line to `crontab -e`:

```
@reboot cd /home/pi/automated_planter_system && python3 -m commune_link.bridge --key change-me
```
