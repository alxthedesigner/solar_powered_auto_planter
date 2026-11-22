"""The automated planter's data in Commune: readings and watering events in, settings out.

Readings reach Commune three ways, and any of them can be missing:
  - the bridge (a Raspberry Pi mailbox): Commune collects new reports from it and sends it new settings (sync_bridge)
  - the planter's SD card: its log files are imported, and settings are written to it (import_card, write_card)
  - planter/inbox/: any planter package dropped there is imported (import_inbox)
Readings are matched on device and time, so the same reading arriving by two ways is only kept once.
Everything is kept in planter/journal.json next to the app (on this computer, not on the Commune drive), and
planter/planter.json holds the settings for the planter. The format is in docs/integrations/planter.md.

Every function takes `pdir`, the planter folder, so this module doesn't depend on offgrid.py.
"""

import datetime
import glob
import json
import os
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PLANTER_DIR = "planter"
MAX_READINGS = 20000   # about two years of hourly readings
MAX_EVENTS = 3000
MAX_PACKAGE = 20 * 1024 ** 2
EVENT_TYPES = ("watered", "skipped", "tank-low", "low-battery", "slow-flow", "valve-closed-on-boot", "pumped", "pump-timeout",
               "vent", "error", "other")
TANK_STATES = ("ok", "low", "empty")
ZONES = 8              # the most zones a planter can have (the reference build has 2: its firmware's MAX_ZONES)
TANKS = 4              # the most tanks (rain drums): its firmware's MAX_TANKS
DEFAULT_LAYOUT = {"zones": [{"zone": 1, "tank": 1}, {"zone": 2, "tank": 1}], "tanks": [{"tank": 1}], "pump": False, "flow": False}
DEFAULTS = {"wakeMinutes": 60, "reportEveryWakes": 3, "wateringHours": [7, 19], "minBattery": 25}
# Sized for a 2 ft x 6 ft bed in two zones: 1 L twice a day per zone is about 1 inch of water a week.
# mode "moisture" waters only when the soil is dry; "schedule" waters at every watering hour, every `everyDays` days.
ZONE_MODES = ("moisture", "schedule")
ZONE_DEFAULTS = {"enabled": True, "mode": "moisture", "everyDays": 1, "moistureBelow": 40, "ml": 1000, "maxMlPerDay": 4000}
NUM_FIELDS = {"battery": (0, 100), "batteryV": (0, 30), "solarV": (0, 60), "tankPercent": (0, 100), "airTemp": (-60, 80),
              "soilTemp": (-60, 80), "airHumidity": (0, 100), "light": (0, 1e6)}


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def _txt(v, n=200):
    return str(v).strip()[:n] if isinstance(v, (str, int, float)) and not isinstance(v, bool) else ""


def _num(v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
    return round(float(v), 2) if lo <= v <= hi else None


def _time(v):
    """An ISO 8601 time, stored in UTC so readings from anywhere sort in order (None if unreadable)."""
    s = _txt(v, 40)
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()
    return _utc(d)


def _utc(d):
    return d.astimezone(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _int(v, lo, hi, default):
    n = _num(v, lo, hi)
    return int(n) if n is not None else default


# ------------------------------------------------------------------ journal
def journal(pdir):
    j = _load(os.path.join(pdir, "journal.json"), {})
    return {"devices": j.get("devices") or {}, "readings": j.get("readings") or [], "events": j.get("events") or [],
            "packages": j.get("packages") or [], "errors": j.get("errors") or [],
            "settings": clean_settings(j.get("settings") or {}), "growing": j.get("growing") or {},
            "settingsChanged": j.get("settingsChanged") or "", "board": j.get("board") or {}, "bridge": j.get("bridge") or {}}


def save(pdir, j):
    _save(os.path.join(pdir, "journal.json"), j)


def clean_reading(r, device):
    if not isinstance(r, dict):
        raise ValueError("A reading isn't readable")
    t = _time(r.get("time"))
    if not t:
        raise ValueError("A reading has no time (ISO 8601, with its time zone)")
    out = {"device": device, "time": t}
    for k, (lo, hi) in NUM_FIELDS.items():
        n = _num(r.get(k), lo, hi)
        if n is not None:
            out[k] = n
    for k in ("charging", "headerFull"):
        if isinstance(r.get(k), bool):
            out[k] = r[k]
    if r.get("tank") in TANK_STATES:
        out["tank"] = r["tank"]
    tanks = []
    for t in (r.get("tanks") or [])[:TANKS] if isinstance(r.get("tanks"), list) else []:
        n = _int((t or {}).get("tank"), 1, TANKS, None) if isinstance(t, dict) else None
        if n and (t.get("level") in TANK_STATES or _num(t.get("percent"), 0, 100) is not None):
            tanks.append({k: v for k, v in (("tank", n), ("level", t.get("level") if t.get("level") in TANK_STATES else None),
                                            ("percent", _num(t.get("percent"), 0, 100))) if v is not None})
    if tanks:
        out["tanks"] = tanks
    zones = []
    for z in (r.get("zones") or [])[:16] if isinstance(r.get("zones"), list) else []:
        if isinstance(z, dict) and _int(z.get("zone"), 1, 16, None):
            zones.append({k: v for k, v in (("zone", _int(z.get("zone"), 1, 16, None)), ("moisture", _num(z.get("moisture"), 0, 100)),
                                            ("mv", _num(z.get("mv"), 0, 5000))) if v is not None})
    if zones:
        out["zones"] = zones
    return out


def clean_event(e, device):
    if not isinstance(e, dict):
        raise ValueError("An event isn't readable")
    t = _time(e.get("time"))
    if not t:
        raise ValueError("An event has no time (ISO 8601, with its time zone)")
    kind = e.get("type") if e.get("type") in EVENT_TYPES else "other"
    out = {"device": device, "time": t, "type": kind}
    for k, v in (("zone", _int(e.get("zone"), 1, 16, None)), ("tank", _int(e.get("tank"), 1, TANKS, None)),
                 ("ml", _num(e.get("ml"), 0, 1e6)), ("seconds", _num(e.get("seconds"), 0, 86400))):
        if v is not None:
            out[k] = v
    for k in ("reason", "state"):
        if _txt(e.get(k)):
            out[k] = _txt(e.get(k), 300)
    return out


def import_package(pdir, data, source):
    """Adds one planter package to the journal. Returns {"id", "readings", "events"}, or None if it was imported before."""
    if not isinstance(data, dict) or not data.get("communePlanterPackage"):
        raise ValueError("This isn't a planter package (no \"communePlanterPackage\")")
    readings, events = data.get("readings") or [], data.get("events") or []
    if not isinstance(readings, list) or not isinstance(events, list) or not (readings or events):
        raise ValueError("This package has no readings or events in it")
    dev = data.get("device") if isinstance(data.get("device"), dict) else {}
    device = _txt(dev.get("id"), 40) or "planter"
    pid = _txt(data.get("id"), 80) or f"{device}-{_txt(data.get('created'), 40) or time.time()}"
    j = journal(pdir)
    if pid in j["packages"]:
        return None
    rs = [clean_reading(r, device) for r in readings[:5000]]
    es = [clean_event(e, device) for e in events[:2000]]
    added = add_records(j, rs, es)
    j["packages"] = (j["packages"] + [pid])[-1000:]
    d = j["devices"].get(device, {})
    d.update(name=_txt(dev.get("name"), 80) or d.get("name") or "Planter", firmware=_txt(dev.get("firmware"), 40) or d.get("firmware", ""),
             lastSeen=now_iso(), lastPackage=pid, source=source)
    j["devices"][device] = d
    if isinstance(data.get("settings"), dict):
        note_board_settings(j, device, data["settings"], data.get("settingsSource"), data.get("settingsChangedOnPlanter"))
    save(pdir, j)
    return {"id": pid, "readings": added[0], "events": added[1]}


def add_records(j, rs, es):
    """Adds readings and events the journal doesn't already have (matched on device and time), in time order, so the
    same reading arriving through the bridge and from the SD card is kept once. Returns how many were new."""
    have_r = {(r["device"], r["time"]) for r in j["readings"]}
    key = lambda e: (e["device"], e["time"], e["type"], e.get("zone"), e.get("tank"))
    have_e = {key(e) for e in j["events"]}
    new_r = [r for r in rs if (r["device"], r["time"]) not in have_r]
    new_e = [e for e in es if key(e) not in have_e]
    if new_r:
        j["readings"] = sorted(j["readings"] + new_r, key=lambda r: r["time"])[-MAX_READINGS:]
    if new_e:
        j["events"] = sorted(j["events"] + new_e, key=lambda e: e["time"])[-MAX_EVENTS:]
    return len(new_r), len(new_e)


def note_board_settings(j, device, settings, source, changed):
    """Remembers the settings the planter reports it's using, to notice a change made on its phone page or SD card."""
    prev = j["board"].get(device, {})
    changed_utc = _time(changed) if changed else None
    if prev.get("changedOnPlanter") and changed_utc and changed_utc < prev["changedOnPlanter"]:
        return  # an older line from the SD card
    nums = sorted({_int(z.get("zone"), 1, ZONES, 0) for z in settings.get("zones") or [] if isinstance(z, dict)} - {0})
    layout = clean_layout(settings.get("layout")) or prev.get("layout")
    if layout:
        nums = [z["zone"] for z in layout["zones"]]
    j["board"][device] = {"settings": clean_settings(settings), "zoneNums": nums or [1, 2], "source": _txt(source, 20) or "default",
                          "changedOnPlanter": changed_utc or prev.get("changedOnPlanter"), "seen": now_iso(),
                          **({"layout": layout} if layout else {})}


def clean_layout(l):
    """What a planter reports it's built with: its zones (and the tank feeding each), its tanks, pump and flow sensor."""
    if not isinstance(l, dict) or not isinstance(l.get("zones"), list):
        return None
    tanks = sorted({_int((t or {}).get("tank"), 1, TANKS, 0) for t in l.get("tanks") or [] if isinstance(t, dict)} - {0}) or [1]
    zones, seen = [], set()
    for z in l["zones"][:ZONES]:
        n = _int((z or {}).get("zone"), 1, ZONES, None) if isinstance(z, dict) else None
        if n and n not in seen:
            seen.add(n)
            t = _int(z.get("tank"), 1, TANKS, 1)
            zones.append({"zone": n, "tank": t if t in tanks else tanks[0]})
    if not zones:
        return None
    return {"zones": sorted(zones, key=lambda z: z["zone"]), "tanks": [{"tank": t} for t in tanks],
            "pump": l.get("pump") is True, "flow": l.get("flow") is True}


def layout_of(j):
    """The zones and tanks to show: every planter's reported layout together, or the readings' zones, or the
    reference build (2 zones on one tank) before any planter has reported."""
    zones, tanks, pump, flow = {}, set(), False, False
    for b in j["board"].values():
        l = b.get("layout")
        if l:
            for z in l["zones"]:
                zones.setdefault(z["zone"], z["tank"])
            tanks.update(t["tank"] for t in l["tanks"])
            pump, flow = pump or l["pump"], flow or l["flow"]
    if not zones:
        seen = {z["zone"] for r in j["readings"][-200:] for z in r.get("zones") or []}
        zones = {n: 1 for n in seen} or {1: 1, 2: 1}
        tanks = {t["tank"] for r in j["readings"][-200:] for t in r.get("tanks") or []}
    tanks |= set(zones.values())
    return {"zones": [{"zone": n, "tank": zones[n]} for n in sorted(zones)], "tanks": [{"tank": t} for t in sorted(tanks or {1})],
            "pump": pump, "flow": flow}


def import_inbox(pdir):
    """Imports every package in planter/inbox/, then moves it to imported/ (or rejected/ if unreadable)."""
    inbox = os.path.join(pdir, "inbox")
    result = {"imported": [], "errors": []}
    if not os.path.isdir(inbox):
        return result
    for f in sorted(os.listdir(inbox)):
        p = os.path.join(inbox, f)
        if f.startswith(".") or not f.lower().endswith(".json") or not os.path.isfile(p):
            continue
        if time.time() - os.path.getmtime(p) < 3:  # the bridge may still be writing it
            continue
        try:
            if os.path.getsize(p) > MAX_PACKAGE:
                raise ValueError("The file is over 20 MB")
            data = _load(p, None)
            if data is None:
                raise ValueError("That file isn't valid JSON")
            up = import_package(pdir, data, f)
            if up:
                result["imported"].append(up)
            _move(p, os.path.join(pdir, "imported"))
        except (ValueError, OSError) as ex:
            result["errors"].append(f"{f}: {ex}")
            j = journal(pdir)
            j["errors"] = (j["errors"] + [{"file": f, "error": str(ex), "time": now_iso()}])[-10:]
            save(pdir, j)
            try:
                _move(p, os.path.join(pdir, "rejected"))
            except OSError:
                pass
    return result


def _move(src, folder):
    os.makedirs(folder, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(src))
    dest, n = os.path.join(folder, stem + ext), 2
    while os.path.exists(dest):
        dest, n = os.path.join(folder, f"{stem}-{n}{ext}"), n + 1
    os.replace(src, dest)


# ------------------------------------------------------------------ settings
def clean_settings(s):
    s = s if isinstance(s, dict) else {}
    hours = s.get("wateringHours", DEFAULTS["wateringHours"])
    hours = sorted({h for h in (_int(x, 0, 23, None) for x in hours) if h is not None})[:24] if isinstance(hours, list) else DEFAULTS["wateringHours"]
    by_zone = {_int(z.get("zone"), 1, ZONES, None): z for z in s.get("zones") or [] if isinstance(z, dict)}
    by_tank = {_int(t.get("tank"), 1, TANKS, None): t for t in s.get("tanks") or [] if isinstance(t, dict)}
    tanks = [{"tank": n, "name": _txt((by_tank.get(n) or {}).get("name"), 60) or ("Rain drum" if n == 1 else f"Drum {n}")}
             for n in range(1, TANKS + 1)]
    zones = []
    for n in range(1, ZONES + 1):
        z = by_zone.get(n) or {}
        zones.append({"zone": n, "name": _txt(z.get("name"), 60) or f"Zone {n}",
                      "enabled": z["enabled"] if isinstance(z.get("enabled"), bool) else ZONE_DEFAULTS["enabled"],
                      "mode": z["mode"] if z.get("mode") in ZONE_MODES else ZONE_DEFAULTS["mode"],
                      "everyDays": _int(z.get("everyDays"), 1, 14, ZONE_DEFAULTS["everyDays"]),
                      "moistureBelow": _int(z.get("moistureBelow"), 0, 100, ZONE_DEFAULTS["moistureBelow"]),
                      "ml": _int(z.get("ml"), 0, 20000, ZONE_DEFAULTS["ml"]),
                      "maxMlPerDay": _int(z.get("maxMlPerDay"), 0, 100000, ZONE_DEFAULTS["maxMlPerDay"])})
    return {"wakeMinutes": _int(s.get("wakeMinutes"), 5, 720, DEFAULTS["wakeMinutes"]),
            "reportEveryWakes": _int(s.get("reportEveryWakes"), 1, 24, DEFAULTS["reportEveryWakes"]),
            "wateringHours": hours or DEFAULTS["wateringHours"],
            "minBattery": _int(s.get("minBattery"), 0, 90, DEFAULTS["minBattery"]), "zones": zones, "tanks": tanks}


def set_settings(pdir, s, finds):
    j = journal(pdir)
    j["settings"] = clean_settings(s)
    # The planter takes Commune's settings only when this changes, so it must differ even for two saves in one second.
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
    if stamp <= j["settingsChanged"]:
        time.sleep(0.002)
        stamp = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
    j["settingsChanged"] = stamp
    save(pdir, j)
    write_device_file(pdir, finds)
    return j["settings"]


def set_growing(pdir, zone, links, finds):
    """Links field identifier finds ({upload, entry}) to a zone: what it's growing."""
    zone = _int(zone, 1, ZONES, None)
    if not zone:
        raise ValueError("Pick a zone")
    known = {f"{f['upload']}/{f['entry']}" for f in finds}
    clean = []
    for l in links if isinstance(links, list) else []:
        key = f"{_txt((l or {}).get('upload'), 80)}/{_txt((l or {}).get('entry'), 80)}"
        if key in known and key not in [f"{c['upload']}/{c['entry']}" for c in clean]:
            u, e = key.split("/", 1)
            clean.append({"upload": u, "entry": e})
    j = journal(pdir)
    j["growing"][str(zone)] = clean[:20]
    save(pdir, j)
    write_device_file(pdir, finds)
    return j["growing"]


def growing_view(growing, finds):
    """Each zone's linked finds, with the facts a planter (or a person) needs to look after them."""
    by_key = {f"{f['upload']}/{f['entry']}": f for f in finds}
    out = {}
    for zone, links in (growing or {}).items():
        out[zone] = []
        for l in links:
            f = by_key.get(f"{l['upload']}/{l['entry']}")
            if f:
                d = f.get("details") or {}
                out[zone].append({"name": f.get("name"), "scientific": f.get("scientific"),
                                  **{k: d[k] for k in ("watering", "sunlight", "climate", "growthTime", "pests") if d.get(k)},
                                  "find": {"upload": l["upload"], "entry": l["entry"]}})
    return out


def write_device_file(pdir, finds):
    """planter/planter.json: the settings the planter follows, and what each zone is growing."""
    _save(os.path.join(pdir, "planter.json"), settings_file(pdir, finds))


def settings_file(pdir, finds):
    """planter.json's contents: what the bridge serves and what's written to the SD card."""
    j = journal(pdir)
    return {"communePlanterSettings": 1, "updated": now_iso(), "settingsChanged": j["settingsChanged"],
            "utcOffset": time.localtime().tm_gmtoff or 0, **j["settings"], "growing": growing_view(j["growing"], finds)}


def plant_finds(field_journal):
    """Identified plants and fungi from the field identifier, which can be linked to a zone."""
    out = []
    for u in field_journal.get("uploads") or []:
        for e in u.get("entries") or []:
            if e.get("category") in ("plant", "fungus") and e.get("status") == "identified" and e.get("name"):
                out.append({"upload": u["id"], "entry": e["id"], "name": e["name"], "scientific": e.get("scientific"),
                            "category": e["category"], "captured": e.get("captured"), "details": e.get("details") or {}})
    return out


# ------------------------------------------------------------------ views
def summary(pdir):
    """Latest numbers for the home page and the header."""
    j = journal(pdir)
    if not j["readings"] and not j["events"]:
        return {"devices": len(j["devices"]), "readings": 0, "errors": len(j["errors"])}
    last = j["readings"][-1] if j["readings"] else {}
    watered = [e for e in j["events"] if e["type"] == "watered"]
    alerts = [e for e in j["events"][-20:] if e["type"] in ("tank-low", "low-battery", "slow-flow", "pump-timeout", "error")]
    names = {t["tank"]: t["name"] for t in j["settings"]["tanks"]}
    return {"devices": len(j["devices"]), "readings": len(j["readings"]), "errors": len(j["errors"]),
            "last": last.get("time"), "battery": last.get("battery"), "tank": last.get("tank"),
            "tanks": [{**t, "name": names.get(t["tank"], f"Drum {t['tank']}")} for t in last.get("tanks") or []],
            "zones": last.get("zones") or [], "lastWatered": watered[-1]["time"] if watered else None,
            "alert": alerts[-1] if alerts else None, "rev": f"{len(j['packages'])}:{j['packages'][-1] if j['packages'] else ''}"}


def view(pdir, finds, days=30):
    """What the Planter page shows: recent readings and events, settings, and finds to link."""
    j = journal(pdir)
    cutoff = _utc(datetime.datetime.now().astimezone() - datetime.timedelta(days=days))
    br = j["bridge"]
    return {"bridge": {"url": br.get("url", ""), "hasKey": bool(br.get("key")), "lastSync": br.get("lastSync"),
                       "lastTry": br.get("lastTry"), "error": br.get("lastError")},
            "cards": find_cards(), "boardChanges": board_changes(j), "settingsChanged": j["settingsChanged"], "layout": layout_of(j),
            "devices": j["devices"], "readings": [r for r in j["readings"] if r["time"] >= cutoff],
            "events": j["events"][-300:], "errors": j["errors"], "settings": j["settings"],
            "growing": growing_view(j["growing"], finds), "finds": finds, "inbox": os.path.join(pdir, "inbox"),
            "total": {"readings": len(j["readings"]), "events": len(j["events"])}}


def dismiss_errors(pdir):
    j = journal(pdir)
    j["errors"] = []
    save(pdir, j)


# ------------------------------------------------------------------ settings changed on the planter itself
SETTING_KEYS = ("wateringHours", "minBattery", "wakeMinutes", "reportEveryWakes")
ZONE_KEYS = ("enabled", "mode", "everyDays", "moistureBelow", "ml", "maxMlPerDay")


def _same_settings(a, b, zones):
    if any(a.get(k) != b.get(k) for k in SETTING_KEYS):
        return False
    za, zb = {z["zone"]: z for z in a["zones"]}, {z["zone"]: z for z in b["zones"]}
    return all(za[n].get(k) == zb[n].get(k) for n in zones for k in ZONE_KEYS)


def board_changes(j):
    """Planters using settings changed on their phone page or SD card, newer than Commune's own."""
    out = []
    for device, b in j["board"].items():
        zones = b.get("zoneNums") or [1, 2]  # only the zones the planter has: unused ones don't count
        if b.get("source") not in ("phone", "sd") or _same_settings(b["settings"], j["settings"], zones):
            continue
        if j["settingsChanged"] and b.get("changedOnPlanter") and b["changedOnPlanter"] < (_time(j["settingsChanged"]) or ""):
            continue  # Commune's settings are newer and will reach the planter
        out.append({"device": device, "name": j["devices"].get(device, {}).get("name") or device, "source": b["source"],
                    "changedOnPlanter": b.get("changedOnPlanter"), "settings": b["settings"]})
    return out


def adopt_board(pdir, device, finds):
    """Makes the planter's own settings (from its phone page or SD card) Commune's settings, keeping zone names."""
    j = journal(pdir)
    b = j["board"].get(device)
    if not b:
        raise ValueError("Commune hasn't heard from that planter")
    names = {z["zone"]: z["name"] for z in j["settings"]["zones"]}
    s = json.loads(json.dumps(b["settings"]))
    for z in s["zones"]:
        z["name"] = names.get(z["zone"], z["name"])
    s["tanks"] = j["settings"]["tanks"]  # the planter doesn't know the names you gave its tanks
    return set_settings(pdir, s, finds)


def resend_settings(pdir, finds):
    """Sends Commune's settings to the planter again, replacing a change made on the planter."""
    return set_settings(pdir, journal(pdir)["settings"], finds)


# ------------------------------------------------------------------ the planter's SD card
def card_roots():
    """Folders where removable cards show up on this computer."""
    if sys.platform == "darwin":
        pats = ["/Volumes/*"]
    elif sys.platform.startswith("win"):
        return [f"{d}:\\" for d in string.ascii_uppercase[3:] if os.path.isdir(f"{d}:\\")]
    else:
        user = os.environ.get("USER", "*")
        pats = [f"/media/{user}/*", "/media/*", f"/run/media/{user}/*", "/mnt/*"]
    return sorted({p for pat in pats for p in glob.glob(pat) if os.path.isdir(p)})


def find_cards():
    """Mounted cards the planter has written to (they have a planter/ folder with logs or settings)."""
    out = []
    for root in card_roots():
        base = os.path.join(root, PLANTER_DIR)
        logs = glob.glob(os.path.join(base, "log", "*.jsonl"))
        if logs or os.path.isfile(os.path.join(base, "settings.json")):
            out.append({"path": root, "name": os.path.basename(root.rstrip("/\\")) or root, "logs": len(logs),
                        "settings": os.path.isfile(os.path.join(base, "settings.json"))})
    return out


def _card(path):
    if not any(c["path"] == path for c in find_cards()):
        raise ValueError("That card isn't plugged in, or the planter hasn't written to it yet")
    return os.path.join(path, PLANTER_DIR)


def import_card(pdir, path):
    """Imports every log file on the card: planter/log/<device>-<month>.jsonl, one {"r"|"e"|"s": …} per line.
    Lines already in the journal are skipped, so importing the same card again is safe."""
    base = _card(path)
    j = journal(pdir)
    total, skipped = [0, 0], 0
    for f in sorted(glob.glob(os.path.join(base, "log", "*.jsonl"))):
        name = os.path.basename(f)[:-6]
        device = name.rsplit("-", 2)[0] if name.count("-") >= 2 else name
        rs, es = [], []
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except ValueError:
                    skipped += 1  # a line cut short by a power cut
                    continue
                try:
                    if isinstance(o.get("r"), dict):
                        rs.append(clean_reading(o["r"], device))
                    elif isinstance(o.get("e"), dict):
                        es.append(clean_event(o["e"], device))
                    elif isinstance(o.get("s"), dict):
                        s = o["s"]
                        note_board_settings(j, device, s, s.get("source"), s.get("changedOnPlanter"))
                except ValueError:
                    skipped += 1  # no time: logged before the clock was set
        added = add_records(j, rs, es)
        total[0] += added[0]
        total[1] += added[1]
        d = j["devices"].get(device, {})
        d.setdefault("name", "Planter")
        d.update(lastCard=now_iso())
        j["devices"][device] = d
    save(pdir, j)
    return {"readings": total[0], "events": total[1], "skipped": skipped}


def write_card(pdir, path, finds):
    """Writes Commune's settings to the card's planter/settings.json. The planter uses them at its next wake."""
    base = _card(path)
    _save(os.path.join(base, "settings.json"), settings_file(pdir, finds))
    return {"path": os.path.join(base, "settings.json")}


# ------------------------------------------------------------------ the bridge (a Raspberry Pi mailbox)
def bridge_url(url):
    url = _txt(url, 200)
    if not url:
        return ""
    if "://" not in url:
        url = "http://" + url
    u = urllib.parse.urlparse(url)
    if not u.hostname:
        raise ValueError("That isn't a bridge address. Type its name or IP address, like 192.168.1.50")
    return f"{u.scheme}://{u.hostname}:{u.port or 8650}"


def _call(url, key, path, body=None, timeout=6):
    req = urllib.request.Request(url + path, data=None if body is None else json.dumps(body).encode(),
                                 method="GET" if body is None else "POST",
                                 headers={"X-Planter-Key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as ex:
        if ex.code == 403:
            raise ValueError("The bridge refused the key. Use the same key the bridge was started with")
        raise ValueError(f"The bridge answered {ex.code}")
    except (urllib.error.URLError, OSError, ValueError) as ex:
        raise ValueError(f"Couldn't reach the bridge at {url}: {getattr(ex, 'reason', ex)}")


def set_bridge(pdir, url, key):
    """Saves the bridge's address and key, and checks the connection (an empty address turns syncing off)."""
    url = bridge_url(url)
    j = journal(pdir)
    b = j["bridge"]
    key = _txt(key, 200) if key else b.get("key", "")  # an empty key box keeps the saved key
    status = _call(url, key, "/planter/status") if url else {}  # check first, so a typo doesn't replace what works
    if url != b.get("url"):
        b.update(cursor="", pushed="")  # a different bridge: start from its oldest report
    b.update(url=url, key=key, lastError=None)
    j["bridge"] = b
    save(pdir, j)
    return status


def sync_bridge(pdir, finds):
    """Collects new reports from the bridge, and sends it Commune's settings if they changed since last time."""
    b = journal(pdir)["bridge"]
    url, key = b.get("url"), b.get("key", "")
    if not url:
        return {"imported": 0}
    cursor, imported, error = b.get("cursor", ""), 0, None
    try:
        for _ in range(50):
            got = _call(url, key, f"/planter/packages?after={urllib.parse.quote(cursor)}&limit=100", timeout=20)
            for item in got.get("packages") or []:
                try:
                    if import_package(pdir, item["package"], "bridge"):
                        imported += 1
                except ValueError:
                    pass  # an unreadable report: skip it rather than stall every sync behind it
                cursor = item["name"]
            if not got.get("more"):
                break
        j = journal(pdir)
        if j["settingsChanged"] and j["settingsChanged"] != b.get("pushed"):
            _call(url, key, "/planter/settings", settings_file(pdir, finds))
            b["pushed"] = j["settingsChanged"]
    except ValueError as ex:
        error = str(ex)
    j = journal(pdir)
    j["bridge"].update(cursor=cursor, pushed=b.get("pushed", ""), lastError=error, lastTry=now_iso(),
                       **({} if error else {"lastSync": now_iso()}))
    save(pdir, j)
    return {"imported": imported, "error": error}
