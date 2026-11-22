# Automated planter ↔ Commune

The automated planter waters its zones (up to 8) by gravity from raised rain tanks (up to 4) (or, with the pump add-on, from a header tank refilled from a barrel). It runs on solar power and measures soil moisture, temperature, battery, solar and tank level. Commune keeps every reading and watering event, shows them on the **Planter** page, and sends back the settings you choose there.

Planter data is kept **on the computer running Commune**, in `planter/` next to the app. It isn't kept on the Commune drive, which goes out into the field with the field identifier.

## Three ways in, any of them optional

| Way | Works when | Readings | Settings |
|---|---|---|---|
| **Wi-Fi bridge** | the planter's Wi-Fi reaches the bridge | The planter posts them to the bridge, a mailbox on an always-on computer (a Raspberry Pi). Commune collects them every 2 minutes while it's open. | Commune sends them to the bridge; the planter gets them in its next reply. |
| **SD card** | nothing else is working: no power or network needed beyond the planter's own | The planter logs every reading to its card. Plug the card into the Commune computer and click **Import readings**. | **Write settings to card**, then put the card back. The planter uses them at its next wake. |
| **Phone page** | Wi-Fi or the internet is down | Shown on the page | Press the planter's setup button, join its own hotspot (`Planter-XXXXXX`), and change them on the page that opens. |

The planter keeps watering with none of them. Readings are matched on device and time, so one that arrives by two ways is only kept once.

## Folders (on the Commune computer)

```
planter/
  journal.json   Commune's record: devices, readings, events, your settings, the bridge's address and key
  planter.json   the settings for the planter (what the bridge serves, and what's written to the SD card)
  inbox/         any planter package dropped here is imported (used by other planters, or a LoRa receiver)
  imported/  rejected/
```

## A planter package

What the bridge collects, and what can be dropped in `inbox/`:

```json
{
  "communePlanterPackage": 1,
  "id": "PL-3A9F21-20261121T070512-482",
  "device": { "id": "PL-3A9F21", "name": "Raised bed", "firmware": "1.2.0" },
  "created": "2026-11-21T07:05:12-08:00",
  "readings": [{
    "time": "2026-11-21T07:00:03-08:00",
    "battery": 78, "batteryV": 3.98, "solarV": 5.6, "charging": true,
    "tank": "ok", "tanks": [{ "tank": 1, "level": "ok" }], "airTemp": 11.5, "soilTemp": 9.8,
    "zones": [{ "zone": 1, "moisture": 31, "mv": 2210 }, { "zone": 2, "moisture": 55, "mv": 1690 }]
  }],
  "events": [
    { "time": "2026-11-21T07:00:05-08:00", "type": "watered", "zone": 1, "ml": 1000, "seconds": 130 },
    { "time": "2026-11-21T07:00:05-08:00", "type": "skipped", "zone": 2, "reason": "moist enough (55% >= 40%)" }
  ],
  "settings": { "...": "the settings the planter is using (same format as planter.json), plus its layout",
                "layout": { "zones": [{ "zone": 1, "tank": 1 }, { "zone": 2, "tank": 1 }], "tanks": [{ "tank": 1 }], "pump": false, "flow": false } },
  "settingsSource": "phone",
  "settingsChangedOnPlanter": "2026-11-20T18:02:00-08:00"
}
```

**Readings:** `time` is required. Everything else is optional: `battery` (%), `batteryV`, `solarV`, `charging`, `tank` (`ok`, `low` or `empty`: `low` if any tank is), `tanks` (`{ "tank", "level", "percent" }` for each tank), `tankPercent`, `headerFull` (pump add-on), `airTemp`, `soilTemp` (°C), `airHumidity`, `light`, and `zones`: `{ "zone", "moisture" (%), "mv" }`.

**Events:** `time` and `type` are required. The types are `watered` (`zone`, `ml`, `seconds`; a `reason` when watered by hand), `skipped` (`zone`, `reason`), `tank-low` (`tank`), `low-battery`, `slow-flow`, `valve-closed-on-boot`, `pumped`, `pump-timeout`, `vent`, `error` and `other`.

**Layout:** `settings.layout` says what the planter is built with: its zones and the tank feeding each, its tanks, and whether it has the pump add-on or a flow sensor. The Planter page shows exactly those zones and tanks (2 zones on one tank until a planter reports). The planter sends it in every report and logs it to its SD card after each power-up.

**Settings:** `settings`, `settingsSource` (`commune`, `phone`, `sd` or `default`) and `settingsChangedOnPlanter` are optional. They tell Commune what the planter is actually using. If it's using settings changed on its phone page or SD card, newer than Commune's, the Planter page says so and offers **Keep the planter's settings** or **Send Commune's settings to it**.

## Settings: `planter.json`

```json
{
  "communePlanterSettings": 1,
  "settingsChanged": "2026-11-21T09:12:00-08:00",
  "utcOffset": -28800,
  "wakeMinutes": 60, "reportEveryWakes": 3, "wateringHours": [7, 19], "minBattery": 25,
  "tanks": [{ "tank": 1, "name": "Rain drum" }],
  "zones": [
    { "zone": 1, "name": "Tomatoes", "enabled": true, "mode": "moisture", "everyDays": 1, "moistureBelow": 40, "ml": 1000, "maxMlPerDay": 4000 },
    { "zone": 2, "name": "Herbs",    "enabled": true, "mode": "schedule", "everyDays": 2, "moistureBelow": 30, "ml": 500, "maxMlPerDay": 1000 }
  ],
  "growing": { "1": [{ "name": "Tomato", "scientific": "Solanum lycopersicum", "watering": "…", "find": { "upload": "…", "entry": "p-004" } }] }
}
```

- A zone can only be watered at one of the `wateringHours` (local time, 0–23; all 24 for hourly watering), and only when it's `enabled`, the tank feeding it isn't low, the battery is at least `minBattery` (%), and it hasn't had `maxMlPerDay` yet today. Each watering gives `ml`.
- `mode` is `moisture` (water only when the zone is below `moistureBelow` %) or `schedule` (water at every watering hour, every `everyDays` days, whatever the soil says).
- `settingsChanged` changes only when someone changes the settings in Commune (it has milliseconds, so two saves in one second still differ). The planter takes Commune's settings only when it differs from the last one it took. So a change made on the phone page or the SD card stays until someone changes the settings in Commune.
- `utcOffset` is the Commune computer's time zone in seconds, so the planter's watering hours are local time.
- `growing` lists the field identifier finds linked to each zone, and `tanks` the names you gave the tanks, for reference. The planter ignores both, and any zones it doesn't have.

## The SD card

The planter writes, at the root of its card:

```
planter/settings.json                 the settings it's using (edit it, or let Commune write it)
planter/log/PL-3A9F21-2026-11.jsonl   one JSON object per line: {"r": reading}, {"e": event} or {"s": settings}
```

Each line carries its own `time`. Lines logged before the clock was ever set have no time and are skipped on import. A clock module (DS3231) keeps the time through power cuts. Commune finds a planter card on any mounted drive with a `planter/` folder (`/Volumes/*` on a Mac, `/media/…` on Linux, drive letters on Windows).

When the planter wakes and finds `settings.json` changed since it last wrote the file, it uses the new settings. It treats them as Commune's if their `settingsChanged` is new to it, and as a hand edit (`sd`) otherwise.

## The bridge protocol

The bridge (`automated_planter_system/commune_link/bridge.py`, port 8650) keeps everything in a folder on the computer it runs on. Every request carries `X-Planter-Key` when the bridge was started with `--key`.

| From | Request | Does |
|---|---|---|
| Planter | `POST /planter/report` | Stores the report as a package. Replies `{ "now", "utcOffset", "settings" }`. |
| Planter | `GET /planter/settings` | The same reply, without sending anything |
| Commune | `GET /planter/packages?after=<name>&limit=100` | `{ "packages": [{ "name", "package" }], "more" }`: everything stored since the last one Commune collected |
| Commune | `POST /planter/settings` | Saves Commune's `planter.json` for the planter |
| Commune | `GET /planter/status` | `{ "packages", "latest", "settingsChanged" }`: a connection check |

The planter's report uses Unix seconds (`t`) instead of ISO times, plus `sentAt` and `timeValid`. If its clock was never set, the bridge shifts every time by `now − sentAt`. A future LoRa receiver would store packages in the same mailbox.
