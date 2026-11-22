"""Reads what Commune left for the device, and writes field packages into the drive's inbox (standard library only)."""

import datetime
import json
import os
import zipfile

FIELD_DIR = "field-id"
PACKAGE_VERSION = 1
# Categories Commune understands (it also accepts mushroom, bug, tech, component and first-aid).
CATEGORIES = ("plant", "fungus", "animal", "language", "hardware", "software", "firstaid", "other")
MEDIA_KINDS = ("photo", "audio", "translationAudio")
MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".m4a", ".mp3", ".wav", ".ogg")
MAX_MEDIA = 50 * 1024 ** 2  # Commune drops any single photo or clip larger than this


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def find_library(path):
    """The Commune library folder at or directly under `path` (a drive or folder), or None.
    A library folder is one that holds field-id/device.json, or a library.xml with a zim/ folder."""
    path = os.path.abspath(path)
    candidates = [path] + sorted(os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))) \
        if os.path.isdir(path) else []
    for c in candidates:
        if os.path.isfile(os.path.join(c, FIELD_DIR, "device.json")):
            return c
    for c in candidates:
        if os.path.isfile(os.path.join(c, "library.xml")) and os.path.isdir(os.path.join(c, "zim")):
            return c
    return None


class CommuneDrive:
    """One Commune library folder, as seen by the field identifier."""

    def __init__(self, library):
        self.library = os.path.abspath(library)
        self.field = os.path.join(self.library, FIELD_DIR)

    @classmethod
    def find(cls, path):
        lib = find_library(path)
        if not lib:
            raise FileNotFoundError(f"No Commune library found at {path}")
        return cls(lib)

    # ---- what Commune wrote for the device
    def device(self):
        """device.json: libraries to search for each category, confidenceToIdentify, lastUpload. {} before the first build."""
        return _load(os.path.join(self.field, "device.json"), {})

    def sources(self, category):
        """ZIM files on the drive worth searching for this category, as absolute paths with their library names."""
        return [{**s, "file": os.path.join(self.library, s["file"])}
                for s in self.device().get("sources", {}).get(category, []) if s.get("file")]

    def confidence_to_identify(self):
        return float(self.device().get("confidenceToIdentify") or 0.8)

    def last_upload_created(self):
        """The `created` time of the last package Commune received: finds up to then can be cleared on the device."""
        return (self.device().get("lastUpload") or {}).get("created")

    def knowledge(self):
        """The person's own identifications. Search these with the libraries on every scan; photos are relative to field-id/."""
        rel = self.device().get("knowledge") or FIELD_DIR + "/knowledge.json"
        return _load(os.path.join(self.library, rel), {}).get("entries") or []

    def media_path(self, rel):
        return os.path.join(self.field, rel)

    # ---- what the device writes
    def inbox(self):
        rel = self.device().get("inbox") or FIELD_DIR + "/inbox"
        path = os.path.join(self.library, rel)
        os.makedirs(path, exist_ok=True)
        return path

    def send(self, package):
        """Writes a FieldPackage into the inbox (written as .part, then renamed, so Commune never reads half a file)."""
        return package.write(self.inbox())


class FieldPackage:
    """Everything scanned since the last upload. Add finds with add(), then CommuneDrive.send() it."""

    def __init__(self, device_id, device_name="Field identifier", firmware="", since=None, package_id=None):
        self.device = {"id": device_id, "name": device_name, "firmware": firmware}
        self.since = since
        self.id = package_id
        self.entries = []
        self._media = {}  # name inside the zip -> local file path

    def add(self, category, *, id=None, name=None, scientific=None, confidence=None, captured=None, location=None,
            photo=None, audio=None, translationAudio=None, candidates=None, quotes=None, details=None, sources=None,
            status=None):
        """One find. photo/audio/translationAudio are local file paths. quotes must be copied word for word from a
        library on the drive ({text, library, title, path, url}): the device never writes its own summary."""
        category = category.lower()
        if category not in CATEGORIES and category not in ("mushroom", "bug", "tech", "component", "first-aid"):
            raise ValueError(f"Unknown category {category!r}; use one of {', '.join(CATEGORIES)}")
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence is 0-1")
        if status not in (None, "identified", "needs-id"):
            raise ValueError("status is 'identified', 'needs-id' or None")
        entry = {"id": id or f"{category[:1]}-{len(self.entries) + 1:03d}", "category": category,
                 "captured": captured or now_iso()}
        for k, v in (("name", name), ("scientific", scientific), ("confidence", confidence), ("location", location),
                     ("candidates", candidates), ("quotes", quotes), ("details", details), ("sources", sources),
                     ("status", status)):
            if v is not None:
                entry[k] = v
        for kind, path in (("photo", photo), ("audio", audio), ("translationAudio", translationAudio)):
            if path:
                ext = os.path.splitext(path)[1].lower()
                if ext not in MEDIA_EXT:
                    raise ValueError(f"{path}: Commune reads {', '.join(MEDIA_EXT)}")
                if os.path.getsize(path) > MAX_MEDIA:
                    raise ValueError(f"{path} is over 50 MB")
                ref = f"media/{entry['id']}-{kind}{ext}"
                self._media[ref] = path
                entry[kind] = ref
        self.entries.append(entry)
        return entry

    def manifest(self):
        created = now_iso()
        return {"communeFieldPackage": PACKAGE_VERSION,
                "id": self.id or f"{self.device['id'] or 'device'}-{created.replace(':', '')}",
                "device": self.device, "since": self.since, "created": created, "entries": self.entries}

    def write(self, folder):
        if not self.entries:
            raise ValueError("A package needs at least one find")
        data = self.manifest()
        name = "".join(c if c.isalnum() or c in "-_" else "-" for c in data["id"])
        if self._media:
            final = os.path.join(folder, name + ".zip")
            with zipfile.ZipFile(final + ".part", "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("manifest.json", json.dumps(data, indent=2, ensure_ascii=False))
                for ref, path in self._media.items():
                    z.write(path, ref)
        else:
            final = os.path.join(folder, name + ".json")
            with open(final + ".part", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(final + ".part", final)
        return final
