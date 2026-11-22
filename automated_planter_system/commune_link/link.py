"""The bridge's mailbox: planter packages waiting for Commune, and the settings Commune left for the planter.

The bridge runs on an always-on computer (a Raspberry Pi). The planter posts readings to it; Commune, running on
your Mac or PC, collects them whenever it's open and leaves new settings here. Nothing needs the other side to be
awake at the same time. Standard library only.

    <mailbox>/packages/   one planter package per report, named <UTC time>-<id>.json so names sort by time
    <mailbox>/planter.json  the latest settings from Commune (the planter gets them in its next reply)
"""

import datetime
import json
import os
import time

PACKAGE_VERSION = 1
KEEP_DAYS = 365  # packages older than this are deleted; Commune has long since collected them
# Used until Commune sends settings: the same defaults Commune starts with.
DEFAULT_SETTINGS = {"communePlanterSettings": 1, "wakeMinutes": 60, "reportEveryWakes": 3, "wateringHours": [7, 19],
                    "minBattery": 25, "zones": [{"zone": n, "name": f"Zone {n}", "enabled": True, "mode": "moisture", "everyDays": 1,
                                                 "moistureBelow": 40, "ml": 1000, "maxMlPerDay": 4000} for n in (1, 2)],
                    "growing": {}, "settingsChanged": ""}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, data):
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def iso(t):
    """Unix seconds as ISO 8601 in this computer's time zone."""
    return datetime.datetime.fromtimestamp(t).astimezone().isoformat(timespec="seconds")


def package_from_report(report, now=None):
    """Turns what the board posted (Unix times, see the bridge protocol) into a planter package."""
    if not isinstance(report, dict):
        raise ValueError("The report isn't a JSON object")
    now = now or time.time()
    dev = report.get("device") if isinstance(report.get("device"), dict) else {}
    device_id = str(dev.get("id") or "planter")[:40]
    readings, events = report.get("readings") or [], report.get("events") or []
    if not isinstance(readings, list) or not isinstance(events, list):
        raise ValueError("readings and events must be lists")
    # A board whose clock was never set counts from when it powered on: shift its times to real ones.
    shift = 0
    sent = report.get("sentAt")
    if isinstance(sent, (int, float)) and (not report.get("timeValid") or abs(now - sent) > 120):
        shift = now - sent

    def fix(items):
        out = []
        for x in items:
            if isinstance(x, dict) and isinstance(x.get("t"), (int, float)):
                y = {k: v for k, v in x.items() if k != "t"}
                y["time"] = iso(x["t"] + shift)
                out.append(y)
        return out

    stamp = datetime.datetime.fromtimestamp(now).strftime("%Y%m%dT%H%M%S")
    pkg = {"communePlanterPackage": PACKAGE_VERSION, "id": f"{device_id}-{stamp}-{int(now * 1000) % 1000:03d}",
           "device": {"id": device_id, "name": str(dev.get("name") or "Planter")[:80], "firmware": str(dev.get("firmware") or "")[:40]},
           "created": iso(now), "readings": fix(readings), "events": fix(events)}
    # The settings the planter is using, so Commune can see a change made on its phone page or SD card.
    if isinstance(report.get("settings"), dict):
        pkg["settings"] = report["settings"]
        pkg["settingsSource"] = str(report.get("settingsSource") or "")[:20]
        pkg["settingsChangedOnPlanter"] = str(report.get("settingsChangedOnPlanter") or "")[:40]
    return pkg


class Mailbox:
    def __init__(self, folder):
        self.folder = os.path.abspath(os.path.expanduser(folder))
        self.packages = os.path.join(self.folder, "packages")
        os.makedirs(self.packages, exist_ok=True)

    # ---- settings: Commune writes them, the planter reads them
    def settings(self):
        s = _load(os.path.join(self.folder, "planter.json"), None)
        return s if isinstance(s, dict) and s.get("communePlanterSettings") else dict(DEFAULT_SETTINGS)

    def save_settings(self, s):
        if not isinstance(s, dict) or not s.get("communePlanterSettings"):
            raise ValueError("Those aren't planter settings (no \"communePlanterSettings\")")
        _write(os.path.join(self.folder, "planter.json"), s)

    # ---- packages: the planter (or a LoRa receiver, later) adds them, Commune collects them
    def store(self, package):
        if not (package.get("readings") or package.get("events")):
            return None
        utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        name = utc + "-" + "".join(c if c.isalnum() or c in "-_" else "-" for c in package["id"]) + ".json"
        _write(os.path.join(self.packages, name), package)
        return name

    def names(self):
        return sorted(f for f in os.listdir(self.packages) if f.endswith(".json"))

    def after(self, cursor="", limit=100):
        """Packages whose names sort after `cursor` (the last one Commune collected), oldest first."""
        names = [n for n in self.names() if n > (cursor or "")]
        out = []
        for n in names[:limit]:
            p = _load(os.path.join(self.packages, n), None)
            if p:
                out.append({"name": n, "package": p})
        return out, len(names) > limit

    def prune(self):
        cutoff = time.time() - KEEP_DAYS * 86400
        for n in self.names():
            p = os.path.join(self.packages, n)
            if os.path.getmtime(p) < cutoff:
                os.remove(p)

    def status(self):
        names = self.names()
        return {"packages": len(names), "latest": names[-1] if names else None,
                "settingsChanged": self.settings().get("settingsChanged", "")}
