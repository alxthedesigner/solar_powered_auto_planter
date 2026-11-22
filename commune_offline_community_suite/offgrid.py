#!/usr/bin/env python3
"""Off-Grid Library: build a plug-in survival library drive from Kiwix ZIMs.

Run:  .venv/bin/python offgrid.py   then open http://localhost:8642

Drive layout written by this tool:
    <drive>/OfflineLibrary/   (or the name of the package you downloaded)
        zim/                    downloaded, crawled and generated .zim files
        kiwix-tools/<platform>/ kiwix-serve binaries for each OS you install
        library.xml             Kiwix library index of zim/
        START-Mac.command, START-Linux.sh, START-Windows.bat
        custom.json             websites crawled with zimit
"""
import base64
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import build_guide
import planter

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
SETTINGS_FILE = os.path.join(HERE, "settings.json")
CACHE_FILE = os.path.join(HERE, "catalog_cache.json")
UI_PORT = int(os.environ.get("OFFGRID_PORT", "8642"))
KIWIX_PORT = 8090
OPDS = "https://library.kiwix.org/catalog/v2/entries"
TOOLS_URL = "https://download.kiwix.org/release/kiwix-tools/kiwix-tools_{}.{}"
TOOL_PLATFORMS = {
    "macos-arm64": "Mac (Apple Silicon)",
    "macos-x86_64": "Mac (Intel)",
    "linux-x86_64": "Linux (x86-64)",
    "linux-aarch64": "Linux (ARM64 / Raspberry Pi 4+)",
    "win-x86_64": "Windows (64-bit)",
}
ZIMIT_IMAGE = "ghcr.io/openzim/zimit"
BUILD_STATE = "build-state.json"  # ZIM files present at the last build, to tell when a rebuild is due
PACKAGES_FILE = os.path.join(HERE, "packages.json")
# Bump when /api/state changes shape. The page checks it, because web/ files are re-read from disk on
# every request while this module only loads at startup, so an old builder can end up serving a new page.
API_VERSION = 11
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
UA = {"User-Agent": "OffGridLibrary/1.0"}

with open(os.path.join(HERE, "catalog.json")) as f:
    CATALOG = json.load(f)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


settings = load_json(SETTINGS_FILE, {"drive": "", "flavours": {}})
settings.setdefault("flavours", {})
settings.setdefault("scanAlways", False)    # look for removable drives without asking first
settings.setdefault("autoConnect", False)   # reconnect to the saved drive without asking first
settings.setdefault("topicEdits", {})        # your changes to topics: {topic id: {"title": ..., "kiwix": [library names]}}
settings.setdefault("folders", {})         # drive path -> name of the library folder on it
settings.setdefault("favorites", None)      # starred package ids for the landing page; None = Commune's starter packs
remote = load_json(CACHE_FILE, {})  # library name -> [options]
packages = load_json(PACKAGES_FILE, [])  # saved carts, oldest first


def _rename_offie_ids():
    """The app used to be called Offie; its starter packs were "offie-…". Rename saved ids to "commune-…"."""
    new = lambda i: "commune-" + i[6:] if isinstance(i, str) and i.startswith("offie-") else i
    if any(str(p.get("id", "")).startswith("offie-") for p in packages):
        for p in packages:
            p["id"] = new(p.get("id"))
        save_json(PACKAGES_FILE, packages)
    favs = settings.get("favorites")
    if favs and any(str(f).startswith("offie-") for f in favs):
        settings["favorites"] = [new(f) for f in favs]
        save_json(SETTINGS_FILE, settings)


_rename_offie_ids()
lock = threading.RLock()
# The saved drive is only touched once the person says so (this session), unless they chose "don't ask again".
session = {"connected": False}


# ------------------------------------------------------------------ paths

DEFAULT_FOLDER = "OfflineLibrary"
LEGACY_FOLDERS = ("OfflineLibrary", "OffGridLibrary")
MARKER = ".commune-library"  # dropped in every library folder Commune creates, so it can find it again
OLD_MARKERS = (".offie-library",)  # from when the app was called Offie


def find_library(p):
    """Name of the folder holding a Commune library on drive p, or None."""
    names = [settings["folders"].get(p)] if settings["folders"].get(p) else []
    try:
        names += sorted(e for e in os.listdir(p) if not e.startswith("."))
    except OSError:
        pass
    for n in names:
        d = os.path.join(p, n)
        if os.path.isdir(os.path.join(d, "zim")) and (n in LEGACY_FOLDERS or any(os.path.exists(os.path.join(d, m)) for m in (MARKER, *OLD_MARKERS))):
            return n
    return None


def folder_name(name):
    """A safe folder name from a package name (falls back to OfflineLibrary)."""
    n = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name or "").strip(" .")[:60]
    return n or DEFAULT_FOLDER


def adopt_library(p):
    """Remember the library already on drive p (if any), so root() points at it."""
    n = find_library(p)
    if n and settings["folders"].get(p) != n:
        settings["folders"][p] = n
        save_json(SETTINGS_FILE, settings)


def name_library(package):
    """Before the first download to an empty drive, name the library folder after the package (or OfflineLibrary)."""
    p = settings.get("drive")
    if not p or find_library(p) or os.path.isdir(root()):
        return
    with lock:
        settings["folders"][p] = folder_name(package)
        save_json(SETTINGS_FILE, settings)


def root():
    if not settings.get("drive") or not (session["connected"] or settings.get("autoConnect")):
        return ""
    return os.path.join(settings["drive"], settings["folders"].get(settings["drive"]) or DEFAULT_FOLDER)


def ensure_root():
    os.makedirs(zim_dir(), exist_ok=True)
    m = os.path.join(root(), MARKER)
    if not os.path.exists(m):
        open(m, "w").close()


def zim_dir():
    return os.path.join(root(), "zim")


def host_platform():
    m = platform.machine().lower()
    arm = m in ("arm64", "aarch64")
    if sys.platform == "darwin":
        return "macos-arm64" if arm else "macos-x86_64"
    if sys.platform.startswith("win"):
        return "win-x86_64"
    return "linux-aarch64" if arm else "linux-x86_64"


def tool_path(name, plat=None):
    plat = plat or host_platform()
    exe = name + (".exe" if plat.startswith("win") else "")
    p = os.path.join(root(), "kiwix-tools", plat, exe)
    if root() and os.path.exists(p):
        return p
    return shutil.which(name) if plat == host_platform() else None


def fs_type(path):
    """Filesystem type of the mount holding path ('msdos'/'vfat' = FAT32, 4 GB file limit)."""
    try:
        out = subprocess.run(["mount"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    best, kind = "", ""
    real = os.path.realpath(path)
    for line in out.splitlines():
        m = re.match(r".+? on (.+?) (?:\((\w+)|type (\w+))", line)
        if m and (real == m.group(1) or real.startswith(m.group(1).rstrip("/") + "/")) and len(m.group(1)) > len(best):
            best, kind = m.group(1), m.group(2) or m.group(3)
    return kind


def is_removable(p):
    """True for USB sticks, SD cards and external drives; False for internal disks, disk images and network shares."""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["diskutil", "info", "-plist", p], capture_output=True, timeout=8).stdout
            info = plistlib.loads(out)
        except (OSError, subprocess.SubprocessError, ValueError):
            return False
        if info.get("BusProtocol") == "Disk Image" or info.get("VirtualOrPhysical") == "Virtual":
            return False
        return bool(info.get("RemovableMedia") or info.get("Removable") or info.get("Ejectable") or info.get("Internal") is False)
    if sys.platform.startswith("win"):
        import ctypes
        return ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(p)) == 2  # DRIVE_REMOVABLE
    return True  # Linux: only /media and /run/media are scanned, where desktops mount removable drives


def list_drives():
    """Removable drives only. Internal disks and folders are added by typing a path."""
    cands = []
    if sys.platform == "darwin":
        cands = [os.path.join("/Volumes", d) for d in os.listdir("/Volumes")]
    elif sys.platform.startswith("win"):
        cands = [f"{c}:\\" for c in "DEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{c}:\\")]
    else:
        for base in ("/media", "/run/media"):
            if os.path.isdir(base):
                for d in os.listdir(base):
                    p = os.path.join(base, d)
                    subs = [os.path.join(p, s) for s in os.listdir(p)] if not os.path.ismount(p) and os.path.isdir(p) else []
                    cands += subs or [p]
    cands = [p for p in cands if os.path.isdir(p) and os.path.realpath(p) != "/"]
    # Each check talks to the disk; run them side by side so one slow drive can't stall the list.
    with ThreadPoolExecutor(8) as pool:
        checked = list(pool.map(lambda p: drive_info(p, "removable") if is_removable(p) else None, cands))
    return [d for d in checked if d]


def drive_info(p, kind):
    """Size, filesystem and any existing library for one drive or folder (None if unreadable)."""
    try:
        u = shutil.disk_usage(p)
    except OSError:
        return None
    lib = find_library(p)
    lib_zim = os.path.join(p, lib, "zim") if lib else ""
    zims = []
    if os.path.isdir(lib_zim):
        try:
            zims = [f for f in os.listdir(lib_zim) if f.endswith(".zim") and not f.startswith(build_guide.GUIDE_NAME)]
        except OSError:
            pass
    lib_size = sum(os.path.getsize(os.path.join(lib_zim, f)) for f in zims) if zims else 0
    return {"path": p, "name": os.path.basename(p.rstrip("/\\")) or p, "kind": kind,
            "free": u.free, "total": u.total, "fstype": fs_type(p),
            "library": {"count": len(zims), "size": lib_size, "folder": lib} if lib else None}


def frameable(url):
    """Whether a site lets this app show it in an embedded preview (X-Frame-Options / CSP frame-ancestors)."""
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError("Enter a full web address starting with http:// or https://")
    blocked = {"ok": False, "reason": "This website doesn't allow previews inside other apps."}
    # Ask the way a browser would, so the site sends the same headers the preview would get.
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=BROWSER_UA), timeout=10) as r:
            headers = r.headers
    except urllib.error.HTTPError:
        # The site refused us; a preview would most likely come up blank too, so say so up front.
        return {"ok": False, "reason": "This website blocked the preview."}
    except Exception:  # DNS failure, TLS error, timeout…
        return {"ok": False, "reason": "This website couldn't be reached for a preview."}
    xfo = (headers.get("X-Frame-Options") or "").strip().lower()
    csp = " ".join(headers.get_all("Content-Security-Policy") or []).lower()
    if xfo:
        return blocked
    m = re.search(r"frame-ancestors([^;]*)", csp)
    if m and not any(s in m.group(1) for s in ("*", "http://localhost")):
        return blocked
    return {"ok": True}


# ------------------------------------------------------------------ catalog

def fetch_remote(name):
    url = OPDS + "?" + urllib.parse.urlencode({"name": name, "count": 50})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        tree = ET.fromstring(r.read())
    ns = {"a": "http://www.w3.org/2005/Atom"}
    opts = []
    for e in tree.findall("a:entry", ns):
        acq = [l for l in e.findall("a:link", ns) if l.get("type") == "application/x-zim"]
        if not acq:
            continue
        href = acq[0].get("href")
        opts.append({
            "flavour": (e.findtext("a:flavour", "", ns) or ""),
            "size": int(acq[0].get("length") or 0),
            "url": href[:-len(".meta4")] if href.endswith(".meta4") else href,
            "date": (e.findtext("a:updated", "", ns) or "")[:10],
            "summary": e.findtext("a:summary", "", ns) or "",
        })
    opts.sort(key=lambda o: o["size"])
    return opts


def refresh_catalog():
    names = list(CATALOG["libraries"])
    errors = []

    def one(n):
        try:
            return n, fetch_remote(n)
        except Exception as ex:  # network down, etc.
            errors.append(f"{n}: {ex}")
            return n, None

    with ThreadPoolExecutor(8) as pool:
        for n, opts in pool.map(one, names):
            if opts:
                remote[n] = opts
    save_json(CACHE_FILE, remote)
    if errors and len(errors) == len(names):
        raise RuntimeError("Could not reach library.kiwix.org: " + errors[0])
    return len(names) - len(errors)


def chosen_option(name):
    opts = remote.get(name) or []
    if not opts:
        return None
    want = settings["flavours"].get(name, CATALOG["libraries"][name].get("flavour", ""))
    for o in opts:
        if o["flavour"] == want:
            return o
    return opts[0]


def on_drive():
    return build_guide.scan(zim_dir(), CATALOG) if root() else {}


def custom_sites():
    return load_json(os.path.join(root(), "custom.json"), []) if root() else []


# Files people add to a topic (PDFs, Word documents, PNGs). They're kept in <library>/files/ and packed into
# the guide ZIM at build time, so each topic page links to them and they open offline in the reader.
FILE_TYPES = {
    ".pdf": ("application/pdf", "PDF"),
    ".doc": ("application/msword", "Word document"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Word document"),
    ".png": ("image/png", "PNG image"),
}


def files_dir():
    return os.path.join(root(), "files")


def custom_files():
    return load_json(os.path.join(root(), "files.json"), []) if root() else []


def save_upload(name, topic, length, stream):
    """Copies an uploaded file onto the drive in chunks and records which topic it belongs to."""
    base = os.path.basename(name or "").strip()
    stem, ext = os.path.splitext(base)
    ext = ext.lower()
    if ext not in FILE_TYPES:
        raise ValueError("Only PDF, Word (.doc, .docx) and PNG files can be added")
    topics = {t["id"] for c in CATALOG["categories"] for t in c["topics"]}
    if topic not in topics:
        raise ValueError("Pick a topic for this file")
    if length <= 0:
        raise ValueError("That file is empty")
    safe = re.sub(r"[^A-Za-z0-9._ -]+", "-", stem).strip(" .-")[:60] or "file"
    ensure_root()
    os.makedirs(files_dir(), exist_ok=True)
    if length > shutil.disk_usage(files_dir()).free:
        raise ValueError("Not enough free space on the drive for this file")
    fname, n = safe + ext, 2
    while os.path.exists(os.path.join(files_dir(), fname)):
        fname, n = f"{safe}-{n}{ext}", n + 1
    dest = os.path.join(files_dir(), fname)
    copy_stream(stream, length, dest)
    entry = {"title": stem.strip() or fname, "name": fname, "topic": topic, "size": length, "kind": FILE_TYPES[ext][1]}
    with lock:
        files = [f for f in custom_files() if f["name"] != fname] + [entry]
        save_json(os.path.join(root(), "files.json"), files)
    return entry


def copy_stream(stream, length, dest):
    """Writes exactly length bytes from an upload to dest, via dest.part so a cut-off upload never looks complete."""
    left = length
    try:
        with open(dest + ".part", "wb") as out:
            while left > 0:
                chunk = stream.read(min(1 << 20, left))
                if not chunk:
                    raise ValueError("The upload stopped before the whole file arrived")
                out.write(chunk)
                left -= len(chunk)
        os.replace(dest + ".part", dest)
    except BaseException:
        if os.path.exists(dest + ".part"):
            os.remove(dest + ".part")
        raise


# ------------------------------------------------------------------ field identification
# The Commune field identifier is a handheld scanner for plants, animals, writing (languages) and electrical or
# mechanical parts. It identifies what it scans against this library, and keeps everything scanned since its last
# upload as one "field package": a .json file, or a .zip holding that JSON (manifest.json) plus the photos and sound
# clips it names. The device drops packages in <library>/field-id/inbox/ (or you import one on the Field
# identification page). Each becomes one upload in field-id/journal.json, with its finds split into "identified" and
# "needs identification" (the device wasn't sure enough). field-id/device.json tells the device which libraries and
# dictionaries are on the drive and when its last upload arrived. The package format is in docs/integrations/field-identifier.md.
FIELD_DIR = "field-id"
# The five identifiers: plants and fungi, animals and bugs, languages, tech (hardware and software), and first aid.
# Fungi are their own category (not plants) but share the plant and fungus identifier and its facts.
FIELD_CATEGORIES = ("plant", "fungus", "animal", "language", "hardware", "software", "firstaid", "other")
FIELD_ALIASES = {"plants": "plant", "fungi": "fungus", "mushroom": "fungus", "mushrooms": "fungus", "animals": "animal",
                 "wildlife": "animal", "bird": "animal", "insect": "animal", "bug": "animal", "bugs": "animal",
                 "text": "language", "writing": "language", "languages": "language",
                 "tech": "hardware", "component": "hardware", "components": "hardware", "electrical": "hardware",
                 "electronic": "hardware", "mechanical": "hardware", "part": "hardware", "device": "hardware",
                 "app": "software", "program": "software", "first-aid": "firstaid", "first_aid": "firstaid",
                 "medical": "firstaid", "injury": "firstaid", "medicine": "firstaid"}
FIELD_SOURCE_KINDS = ("article", "dictionary", "video", "lesson", "manual", "image", "knowledge")
# A find you identify yourself needs a source. "knowledge" sources are your own past identifications (knowledge.json).
CITE_TYPES = {"website": "Website", "book": "Book", "field-guide": "Field guide", "expert": "Expert or person",
              "library": "Library on this drive", "other": "Other"}
# A person you asked may have no website; every other kind of source must give the website it came from.
CITE_NO_URL = ("expert",)
# The website each library was made from, so every source can name where its information really comes from.
WIKI_FAMILIES = {"wikipedia": "wikipedia.org", "wiktionary": "wiktionary.org", "wikivoyage": "wikivoyage.org", "wikibooks": "wikibooks.org"}
WIKI_SITES = {"wikispecies": "https://species.wikimedia.org/wiki/", "gardenology": "https://www.gardenology.org/wiki/",
              "energypedia": "https://energypedia.info/wiki/", "mdwiki": "https://mdwiki.org/wiki/", "appropedia": "https://www.appropedia.org/",
              "ifixit": "https://www.ifixit.com/", "scoutwiki.org": "https://en.scoutwiki.org/", "canadian-prepper": "https://www.youtube.com/@CanadianPrepper"}


def _url(v):
    v = _txt(v, 500)
    return v if re.match(r"https?://[^\s/]+\.\S*$", v) else ""


def source_url(library, path=""):
    """The web address of the page a library article was made from ("" if it can't be worked out). Libraries with no
    website of their own (the zimgit collections, for example) point at their page in the Kiwix library."""
    lib = _txt(library, 80)
    if not lib:
        return ""
    base, _, rest = lib.partition("_")
    lang = rest.split("_")[0] or "en"
    path = _txt(path, 300).lstrip("/")
    if base in WIKI_FAMILIES or base in WIKI_SITES:
        path = path.replace(" ", "_")  # wiki page names use underscores
    path = urllib.parse.quote(path, safe="/:#?=&%()_-.,'!~")
    if base in WIKI_FAMILIES:
        return f"https://{lang}.{WIKI_FAMILIES[base]}/wiki/{path}" if path else f"https://{lang}.{WIKI_FAMILIES[base]}/"
    if base in WIKI_SITES:
        return WIKI_SITES[base] + path
    if "." in base:  # named after its website: outdoors.stackexchange.com, ready.gov, irp.fas.org…
        return f"https://{base}/{path}"
    return "https://library.kiwix.org/#q=" + urllib.parse.quote(lib)
FIELD_SURE = 0.8  # confidence at or above which a find counts as identified, unless the device says otherwise
FIELD_MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
               ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav", ".ogg": "audio/ogg"}
FIELD_MAX_UPLOAD = 1024 ** 3      # one package, photos included
FIELD_MAX_MEDIA = 50 * 1024 ** 2  # one photo or sound clip
# Topics whose libraries the device searches for each kind of find (see device.json).
FIELD_TOPICS = {
    "plant": ["plant-id", "spice-plants", "poison", "natural-medicine", "finding-spices", "tea"],
    "fungus": ["plant-id", "poison", "natural-medicine"],
    "animal": ["animal-id", "tracking", "hunting", "butchering", "predators"],
    "language": ["dict-es", "dict-fr", "dict-zh", "translator", "encyclopedia"],
    "hardware": ["electrical", "mechanic", "walkie", "radio", "irrigation"],
    "software": ["electrical", "radio", "encyclopedia"],
    "firstaid": ["first-aid", "cpr", "choking", "wounds", "burns", "poison", "natural-medicine"],
}


LOCAL_FIELD = os.path.join(HERE, FIELD_DIR)  # where finds are kept while no drive is connected


def field_dir(*parts):
    """The connected drive's field-id folder, or one next to the app when no drive is connected."""
    return os.path.join(root(), FIELD_DIR, *parts) if root() else os.path.join(LOCAL_FIELD, *parts)


def planter_dir(*parts):
    """The planter's readings and settings, kept on this computer (next to the app), not on the Commune drive:
    the drive goes out with the field identifier, while the planter stays home."""
    return os.path.join(HERE, planter.PLANTER_DIR, *parts)


planter_lock = threading.RLock()  # its own lock: a bridge sync waits on the network, and shouldn't hold up the rest


def planter_sync():
    """Collects new reports from the bridge (a Raspberry Pi) and sends it changed settings. Safe to call any time."""
    with planter_lock:
        return planter.sync_bridge(planter_dir(), planter_finds())


def planter_sync_soon():
    threading.Thread(target=lambda: _try(planter_sync), daemon=True).start()


def planter_sync_loop():
    while True:
        time.sleep(120)
        _try(planter_sync)


def planter_finds():
    return planter.plant_finds(field_journal())


def planter_import():
    """Picks up anything the planter's bridge left in planter/inbox/, and tells the planter the latest settings."""
    with planter_lock:
        result = planter.import_inbox(planter_dir())
        if result["imported"] or not os.path.exists(planter_dir("planter.json")):
            planter.write_device_file(planter_dir(), planter_finds())
    return result


_planter_cache = {"key": None, "summary": None}


def planter_summary():
    """The planter's latest numbers for the home page, re-read only when its journal changes."""
    p = planter_dir("journal.json")
    try:
        key = (p, os.path.getmtime(p))
    except OSError:
        key = (p, 0)
    if _planter_cache["key"] != key:
        _planter_cache.update(key=key, summary=planter.summary(planter_dir()))
    return _planter_cache["summary"]


def field_journal():
    j = load_json(field_dir("journal.json"), {})
    return {"uploads": j.get("uploads") or [], "errors": j.get("errors") or []}


def save_field(j):
    if root():
        ensure_root()  # a drive whose first content is a field upload still becomes a Commune library
    os.makedirs(field_dir(), exist_ok=True)
    save_json(field_dir("journal.json"), j)
    write_knowledge(j)


def user_identified(e):
    return e.get("identifiedBy") == "user" or (bool(e.get("confirmed")) and e.get("status") == "identified")


def write_knowledge(j):
    """field-id/knowledge.json: every find you identified yourself, with your source. The field identifier searches it
    alongside the drive's libraries when it scans, so what you've learned helps identify what you find next."""
    known = []
    j = with_source_urls(json.loads(json.dumps(j)))  # a copy, with every source's website
    for u in j["uploads"]:
        for e in u["entries"]:
            if e.get("status") == "identified" and user_identified(e):
                known.append({
                    "name": e.get("name"), "scientific": e.get("scientific"), "category": e.get("category"),
                    "identified": e.get("confirmed"), "captured": e.get("captured"), "location": e.get("location"),
                    "citation": e.get("citation"), "details": e.get("details") or {}, "notes": e.get("notes") or "",
                    "sources": e.get("sources") or [], "quotes": e.get("quotes") or [],
                    "photo": f"media/{u['id']}/{e['photo']}" if e.get("photo") else None,
                    "deviceGuess": (e.get("deviceGuess") or {}).get("name") or None,
                    "find": {"upload": u["id"], "entry": e["id"]}})
    save_json(field_dir("knowledge.json"), {"communeFieldKnowledge": 1, "updated": now_iso(), "count": len(known), "entries": known})


def load_sample():
    """Test finds for every category, from docs/field-package.example.json. Returns the upload (None if already there)."""
    data = load_json(os.path.join(HERE, "docs", "field-package.example.json"), None)
    if not data:
        raise ValueError("The sample upload (docs/field-package.example.json) is missing")
    data.update(id="commune-sample", device={"name": "Sample finds (Commune)"})
    photos = os.path.join(HERE, "docs", "sample-photos")

    def read_media(ref):  # the sample's test pictures, kept in docs/sample-photos/
        p = os.path.join(photos, os.path.basename(ref))
        return open(p, "rb").read() if os.path.isfile(p) else None

    return import_package(data, read_media, "Sample upload")


def seed_field():
    """The first time the Field identification page opens on a drive (or this computer), it starts with the sample
    finds so there's something to look at. Deleting them doesn't bring them back: the journal exists from then on."""
    if not os.path.exists(field_dir("journal.json")):
        try:
            load_sample()
        except (ValueError, OSError):
            pass


def now_iso():
    import datetime
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _txt(v, n=300, lines=False):
    """A clean string from whatever the device sent ("" for missing values, objects and lists)."""
    if v is None or isinstance(v, (dict, list)):
        return ""
    s = str(v).replace("\r\n", "\n")
    s = re.sub(r"[ \t]+", " ", s) if lines else re.sub(r"\s+", " ", s)
    return s.strip()[:n]


def _slug(v, n=40):
    return re.sub(r"[^A-Za-z0-9_-]+", "-", _txt(v, 200)).strip("-")[:n]


def _conf(v):
    """Confidence as 0–1 (devices may send 0–100); None if missing."""
    try:
        c = float(v)
    except (TypeError, ValueError):
        return None
    if c > 1:
        c /= 100
    return max(0.0, min(c, 1.0))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clean_details(d):
    """The category-specific facts (edibility, danger level, translation, specs…): values, lists of values, and
    one-level maps of values (such as {"Mexico": 98, "United States": 13} for who speaks a language)."""
    out = {}
    for k, v in (d.items() if isinstance(d, dict) else []):
        key = re.sub(r"[^A-Za-z0-9_]", "", str(k))[:40]
        if not key or len(out) >= 40:
            continue
        if isinstance(v, bool) or (isinstance(v, (int, float)) and v == v):
            out[key] = v
        elif isinstance(v, list):
            items = [_txt(x, 300) for x in v[:30] if not isinstance(x, (dict, list))]
            if any(items):
                out[key] = [x for x in items if x]
        elif isinstance(v, dict):
            m = {_txt(a, 80): (b if isinstance(b, (int, float)) and not isinstance(b, bool) else _txt(b, 300))
                 for a, b in list(v.items())[:300] if _txt(a) and not isinstance(b, (dict, list))}
            if m:
                out[key] = m
        elif _txt(v):
            out[key] = _txt(v, 2000, lines=True)
    return out


def clean_entry(e, i, taken):
    if not isinstance(e, dict):
        raise ValueError(f"Find {i + 1} isn't readable")
    cat = _txt(e.get("category"), 40).lower()
    cat = FIELD_ALIASES.get(cat, cat)
    if cat not in FIELD_CATEGORIES:
        cat = "other"
    eid = _slug(e.get("id")) or f"find-{i + 1}"
    while eid in taken:
        eid += "-2"
    taken.add(eid)
    conf = _conf(e.get("confidence"))
    name = _txt(e.get("name"), 160)
    status = _txt(e.get("status"), 20).lower().replace("_", "-")
    if status not in ("identified", "needs-id"):
        status = "identified" if name and conf is not None and conf >= FIELD_SURE else "needs-id"
    cands = []
    for c in e.get("candidates") or []:
        if isinstance(c, dict) and _txt(c.get("name")):
            cands.append({"name": _txt(c.get("name"), 160), "scientific": _txt(c.get("scientific"), 160),
                          "confidence": _conf(c.get("confidence"))})
    loc = e.get("location") if isinstance(e.get("location"), dict) else {}
    location = {k: v for k, v in {"lat": _num(loc.get("lat")), "lon": _num(loc.get("lon")), "label": _txt(loc.get("label"), 160)}.items() if v not in (None, "")}
    sources = []
    for s in e.get("sources") or []:
        # Every source says which website its information is from: the device's "url", or worked out from the library.
        if isinstance(s, dict) and (_txt(s.get("library")) or _url(s.get("url"))):
            kind = _txt(s.get("kind"), 20).lower()
            sources.append({"library": _txt(s.get("library"), 80), "title": _txt(s.get("title"), 160), "path": _txt(s.get("path"), 300),
                            "kind": kind if kind in FIELD_SOURCE_KINDS else "article", "url": _url(s.get("url"))})
    # Summaries are quotes only: word for word from a library on the drive, each with where it came from.
    # The device never writes its own summary. An old-style "summary" string is kept as a quote with no source.
    quotes = []
    for q in e.get("quotes") or []:
        if isinstance(q, dict) and _txt(q.get("text")):
            quotes.append({"text": _txt(q.get("text"), 1500, lines=True), "library": _txt(q.get("library"), 80),
                           "title": _txt(q.get("title"), 160), "path": _txt(q.get("path"), 300), "url": _url(q.get("url"))})
    if not quotes and _txt(e.get("summary")):
        quotes.append({"text": _txt(e.get("summary"), 1500, lines=True), "library": "", "title": "", "path": ""})
    return {"id": eid, "category": cat, "status": status, "name": name, "scientific": _txt(e.get("scientific"), 160),
            "confidence": conf, "captured": _txt(e.get("captured"), 40), "location": location or None,
            "quotes": quotes[:10], "details": clean_details(e.get("details")),
            "candidates": cands[:8], "sources": sources[:20], "notes": _txt(e.get("notes"), 5000, lines=True),
            "photo": "", "audio": "", "translationAudio": ""}


def import_package(data, read_media, source):
    """Adds one field package to the journal. read_media(name) returns a photo or clip's bytes (or None).
    Returns the new upload, or None if this package was imported before."""
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError("This isn't a field identifier upload: it has no list of finds (\"entries\")")
    if not data["entries"]:
        raise ValueError("This upload has no finds in it")
    raw = json.dumps(data, sort_keys=True).encode()
    uid = _slug(data.get("id")) or hashlib.sha1(raw).hexdigest()[:12]
    with lock:
        journal = field_journal()
        if any(u["id"] == uid for u in journal["uploads"]):
            return None
        taken, entries = set(), []
        for i, e in enumerate(data["entries"][:5000]):
            entry = clean_entry(e, i, taken)
            for kind in ("photo", "audio", "translationAudio"):
                ref = e.get(kind) if isinstance(e, dict) else None
                if not isinstance(ref, str) or not ref:
                    continue
                ext, blob = os.path.splitext(ref.split("?")[0])[1].lower(), None
                m = re.match(r"data:([\w/+.-]+);base64,(.*)$", ref, re.S)
                if m:  # small packages may carry the photo inline
                    ext = next((x for x, t in FIELD_MEDIA.items() if t == m.group(1)), "")
                    try:
                        blob = base64.b64decode(m.group(2), validate=False)
                    except ValueError:
                        blob = None
                elif ext in FIELD_MEDIA:
                    blob = read_media(ref)
                if ext in FIELD_MEDIA and blob and len(blob) <= FIELD_MAX_MEDIA:
                    os.makedirs(field_dir("media", uid), exist_ok=True)
                    fname = f"{entry['id']}-{kind}{ext}"
                    with open(field_dir("media", uid, fname), "wb") as out:
                        out.write(blob)
                    entry[kind] = fname
            entries.append(entry)
        dev = data.get("device") if isinstance(data.get("device"), dict) else {}
        upload = {"id": uid, "device": {"id": _txt(dev.get("id"), 80), "name": _txt(dev.get("name"), 80) or "Field identifier",
                                        "firmware": _txt(dev.get("firmware"), 40)},
                  "since": _txt(data.get("since"), 40), "created": _txt(data.get("created"), 40),
                  "received": now_iso(), "source": _txt(source, 120), "entries": entries}
        journal["uploads"].append(upload)
        save_field(journal)
    write_device_file()
    return upload


def import_file(path, source):
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/") and "__MACOSX" not in n]
            jsons = [n for n in names if n.lower().endswith(".json")]
            manifest = next((n for n in jsons if os.path.basename(n).lower() == "manifest.json"), None) or (jsons[0] if len(jsons) == 1 else None)
            if not manifest:
                raise ValueError("The .zip has no manifest.json listing the finds")
            try:
                data = json.loads(z.read(manifest))
            except ValueError:
                raise ValueError("manifest.json in the .zip isn't valid JSON")
            base = os.path.dirname(manifest)
            by_base = {os.path.basename(n): n for n in names}

            def read_media(ref):
                ref = ref.lstrip("/")
                n = next((x for x in (ref, os.path.join(base, ref).replace(os.sep, "/")) if x in names), None) or by_base.get(os.path.basename(ref))
                if not n or z.getinfo(n).file_size > FIELD_MAX_MEDIA:
                    return None
                return z.read(n)

            return import_package(data, read_media, source)
    with open(path, "rb") as f:
        try:
            data = json.loads(f.read())
        except ValueError:
            raise ValueError("That file isn't valid JSON")
    return import_package(data, lambda ref: None, source)


def _move(src, folder):
    os.makedirs(folder, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(src))
    dest, n = os.path.join(folder, stem + ext), 2
    while os.path.exists(dest):
        dest, n = os.path.join(folder, f"{stem}-{n}{ext}"), n + 1
    os.replace(src, dest)


def import_inbox():
    """Imports every package the device left in field-id/inbox/, then moves it to imported/ (or rejected/ if unreadable)."""
    inbox = field_dir("inbox")
    if not os.path.isdir(inbox):
        return {"imported": [], "errors": []}
    result = {"imported": [], "errors": []}
    for f in sorted(os.listdir(inbox)):
        p = os.path.join(inbox, f)
        if f.startswith(".") or not f.lower().endswith((".json", ".zip")) or not os.path.isfile(p):
            continue
        if time.time() - os.path.getmtime(p) < 3:  # the device may still be writing it
            continue
        try:
            up = import_file(p, f)
            if up:
                result["imported"].append({"id": up["id"], "count": len(up["entries"])})
            _move(p, field_dir("imported"))
        except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as ex:  # RuntimeError: encrypted zip
            result["errors"].append(f"{f}: {ex}")
            with lock:
                j = field_journal()
                j["errors"] = (j["errors"] + [{"file": f, "error": str(ex), "time": now_iso()}])[-10:]
                save_field(j)
            try:
                _move(p, field_dir("rejected"))
            except OSError:
                pass
    return result


def write_device_file():
    """field-id/device.json: what the device can look things up in on this drive, and when its last upload arrived."""
    if not root():
        return
    os.makedirs(field_dir("inbox"), exist_ok=True)
    have = on_drive()
    topics = {t["id"]: t for c in catalog_view()["categories"] for t in c["topics"]}
    sources = {}
    for cat, tids in FIELD_TOPICS.items():
        libs = []
        for n in [n for tid in tids for n in topics.get(tid, {}).get("kiwix", [])]:
            if n in have and all(x["library"] != n for x in libs):
                libs.append({"library": n, "title": CATALOG["libraries"][n]["title"], "file": "zim/" + have[n]})
        sources[cat] = libs
    dictionaries = {n.split("_")[1]: {"library": n, "file": "zim/" + have[n]} for n in sorted(have) if n.startswith("wiktionary_")}
    ups = field_journal()["uploads"]
    last = ups[-1] if ups else {}
    save_json(field_dir("device.json"), {
        "communeFieldDevice": 1, "inbox": FIELD_DIR + "/inbox", "confidenceToIdentify": FIELD_SURE,
        "lastUpload": {"id": last.get("id"), "received": last.get("received"), "created": last.get("created")} if last else None,
        "sources": sources, "dictionaries": dictionaries,
        "knowledge": FIELD_DIR + "/knowledge.json",  # your own identifications: search these too when scanning
        "knowledgeCount": len(load_json(field_dir("knowledge.json"), {}).get("entries") or []),
        "updated": now_iso()})


_field_cache = {"key": None, "summary": None}


def field_summary():
    """Counts for the home page and the header, re-read only when the journal changes."""
    p = field_dir("journal.json")
    inbox = field_dir("inbox")
    try:
        mtime = os.path.getmtime(p)
    except OSError:
        mtime = 0
    waiting = len([f for f in os.listdir(inbox) if f.lower().endswith((".json", ".zip"))]) if os.path.isdir(inbox) else 0
    if _field_cache["key"] != (p, mtime):
        j = field_journal()
        finds = [e for u in j["uploads"] for e in u["entries"]]
        _field_cache.update(key=(p, mtime), summary={
            "rev": f"{p}:{mtime}", "onDrive": bool(root()), "uploads": len(j["uploads"]), "errors": len(j["errors"]),
            "identified": sum(e["status"] == "identified" for e in finds),
            "needs": sum(e["status"] != "identified" for e in finds),
            "last": j["uploads"][-1]["received"] if j["uploads"] else None})
    return {**_field_cache["summary"], "inbox": waiting}


def with_source_urls(j):
    """Fills in the website for every source and quote that doesn't name one (older uploads, or a device that
    only gave the library), and for sources that point at your own earlier finds, the website you cited there."""
    finds = {f"{u['id']}/{e['id']}": e for u in j["uploads"] for e in u["entries"]}
    for e in finds.values():
        for s in (e.get("sources") or []) + (e.get("quotes") or []):
            if s.get("url"):
                continue
            if s.get("kind") == "knowledge":
                s["url"] = ((finds.get(s.get("path")) or {}).get("citation") or {}).get("url") or ""
            else:
                s["url"] = source_url(s.get("library"), s.get("path"))
        c = e.get("citation")
        if c and not c.get("url"):  # identified before citations had their own website field
            c["url"] = _url(c.get("detail")) or _url(c.get("title"))
    return j


def find_entry(j, uid, eid):
    u = next((x for x in j["uploads"] if x["id"] == uid), None)
    e = next((x for x in u["entries"] if x["id"] == eid), None) if u else None
    if not e:
        raise ValueError("That find isn't in the journal any more")
    return e


# ------------------------------------------------------------------ jobs

jobs = []  # newest last
queue_cv = threading.Condition(lock)


class Cancelled(Exception):
    pass


def new_job(kind, label, run, **extra):
    job = {"id": uuid.uuid4().hex[:8], "kind": kind, "label": label, "status": "queued",
           "progress": 0.0, "message": "Waiting…", "done": 0, "total": 0, "speed": 0,
           "cancel": False, "run": run, "started": None, **extra}
    with queue_cv:
        jobs.append(job)
        queue_cv.notify_all()
    return job


def public(job):
    return {k: v for k, v in job.items() if k not in ("run", "cancel", "proc")}


def worker(kinds):
    """One worker per lane: downloads run one at a time; crawls/builds run in their own lane."""
    while True:
        with queue_cv:
            job = None
            while job is None:
                job = next((j for j in jobs if j["status"] == "queued" and j["kind"] in kinds), None)
                if job is None:
                    queue_cv.wait()
            job["status"], job["started"] = "running", time.time()
        try:
            job["run"](job)
            job["status"], job["progress"] = "done", 1.0
            job["message"] = job.get("message") if job["message"] != "Waiting…" else "Done"
        except Cancelled:
            job["status"], job["message"] = "cancelled", "Cancelled"
        except Exception as ex:
            job["status"], job["message"] = "error", str(ex)


def check_cancel(job):
    if job["cancel"]:
        raise Cancelled()


def download(url, dest, job):
    """Resumable HTTP download into dest (.part until complete)."""
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={have}-"} if have else UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        if have and r.status != 206:
            have = 0  # server ignored Range; start over
        total = have + int(r.headers.get("Content-Length") or 0)
        job["total"], job["done"] = total, have
        t0, d0 = time.time(), have
        with open(part, "ab" if have else "wb") as f:
            while True:
                check_cancel(job)
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                job["done"] += len(chunk)
                dt = time.time() - t0
                if dt > 1:
                    job["speed"] = (job["done"] - d0) / dt
                job["progress"] = job["done"] / total if total else 0
                job["message"] = f"{human(job['done'])} of {human(total)}"
    if total and os.path.getsize(part) < total:
        raise RuntimeError("Download incomplete; start it again to resume")
    os.replace(part, dest)


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def queue_download(name):
    opt = chosen_option(name)
    if not opt:
        raise ValueError(f"No catalog info for {name}; refresh the catalog first")
    fname = os.path.basename(urllib.parse.urlparse(opt["url"]).path)
    dest = os.path.join(zim_dir(), fname)
    if os.path.exists(dest):
        raise ValueError(f"{fname} is already on the drive")
    for j in jobs:
        if j.get("library") == name and j["status"] in ("queued", "running"):
            raise ValueError(f"{name} is already queued")
    ensure_root()
    free = shutil.disk_usage(zim_dir()).free
    queued = sum(j["total"] - j["done"] for j in jobs if j["kind"] == "download" and j["status"] in ("queued", "running"))
    if opt["size"] > free - queued:
        raise ValueError(f"Not enough space for {name} ({human(opt['size'])}, {human(free - queued)} free after queue)")
    fat = fs_type(zim_dir()) in ("msdos", "vfat", "fat32")
    if fat and opt["size"] >= 4 * 1024 ** 3:
        raise ValueError(f"{name} is over 4 GB and the drive is FAT32. Reformat as exFAT or pick a smaller flavour.")

    def run(job):
        # Drop older versions of the same library once the new one lands.
        old = on_drive().get(name)
        download(opt["url"], dest, job)
        if old and old != fname:
            os.remove(os.path.join(zim_dir(), old))
        job["message"] = f"Saved {fname}"

    return new_job("download", CATALOG["libraries"][name]["title"], run, library=name, total=opt["size"])


def queue_crawl(url, title, topic, page_limit):
    if not shutil.which("docker"):
        raise ValueError("Docker is not installed; zimit needs it to crawl websites")
    host = urllib.parse.urlparse(url).netloc
    if not host:
        raise ValueError("Enter a full URL, e.g. https://example.org/")
    name = re.sub(r"[^a-z0-9]+", "-", (title or host).lower()).strip("-")[:40] or "site"
    stem = f"crawl-{name}_{time.strftime('%Y-%m')}"
    ensure_root()

    def run(job):
        # No volume mount: Docker Desktop only shares some host folders, and FAT/exFAT drives
        # mount poorly. The ZIM is copied out of the container with `docker cp` instead.
        container = f"offgrid-crawl-{job['id']}"
        cmd = ["docker", "run", "--name", container, ZIMIT_IMAGE, "zimit",
               "--seeds", url, "--name", f"crawl-{name}", "--zim-file", stem + ".zim",
               "--title", (title or host)[:30], "--description", f"Offline copy of {host}"[:80],
               "--workers", "2", "--waitUntil", "domcontentloaded"]
        if page_limit:
            cmd += ["--pageLimit", str(int(page_limit))]
        job["message"] = "Starting crawler (first run pulls the Docker image, about 1 GB)…"
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            tail = []
            for line in proc.stdout:
                if job["cancel"]:
                    subprocess.run(["docker", "stop", container], capture_output=True)
                    raise Cancelled()
                line = line.strip()
                if not line:
                    continue
                tail = (tail + [line])[-40:]
                m = re.search(r'"crawled":(\d+).*?"total":(\d+)', line)
                if m:
                    done, total = int(m.group(1)), int(m.group(2))
                    job["done"], job["total"] = done, total
                    job["progress"] = 0.9 * done / max(total, 1)
                    job["message"] = f"Crawled {done} of {total} pages"
                elif "warc2zim" in line.lower():
                    job["message"] = "Packaging pages into a ZIM…"
            if proc.wait() != 0:
                raise RuntimeError("zimit failed: " + (tail[-1] if tail else "no output"))
            job["message"] = "Copying ZIM to the drive…"
            dest = os.path.join(zim_dir(), stem + ".zim")
            cp = subprocess.run(["docker", "cp", f"{container}:/output/{stem}.zim", dest + ".part"],
                                capture_output=True, text=True)
            if cp.returncode != 0:
                raise RuntimeError("zimit finished but no ZIM was written: " + cp.stderr.strip())
            os.replace(dest + ".part", dest)
        finally:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)
        sites = [c for c in custom_sites() if c["file"] != stem + ".zim"]
        sites.append({"title": title or host, "url": url, "topic": topic, "file": stem + ".zim"})
        save_json(os.path.join(root(), "custom.json"), sites)
        job["message"] = f"Saved {stem}.zim"

    return new_job("crawl", f"Copy website: {title or host}", run,
                   url=url, title=title, topic=topic, pageLimit=page_limit)


def tools_url(plat, ext):
    """Newest kiwix-tools build for a platform, read from the release directory listing."""
    base = TOOLS_URL.rsplit("/", 1)[0] + "/"
    with urllib.request.urlopen(urllib.request.Request(base, headers=UA), timeout=30) as r:
        listing = r.read().decode(errors="replace")
    pat = re.compile(r'href="(kiwix-tools_' + re.escape(plat) + r'-(\d+)\.(\d+)\.(\d+)(?:-(\d+))?\.' + re.escape(ext) + ')"')
    builds = [(tuple(int(g or 0) for g in m.groups()[1:]), m.group(1)) for m in pat.finditer(listing)]
    if not builds:
        raise RuntimeError(f"No kiwix-tools build found for {plat}")
    return base + max(builds)[1]


def queue_tools(platforms):
    def run(job):
        for i, plat in enumerate(platforms):
            check_cancel(job)
            ext = "zip" if plat.startswith("win") else "tar.gz"
            dest_dir = os.path.join(root(), "kiwix-tools", plat)
            os.makedirs(dest_dir, exist_ok=True)
            archive = os.path.join(root(), "kiwix-tools", f"{plat}.{ext}")
            job["message"] = f"Downloading {TOOL_PLATFORMS[plat]}"
            download(tools_url(plat, ext), archive, job)
            job["message"] = f"Unpacking {TOOL_PLATFORMS[plat]}"
            if ext == "zip":
                with zipfile.ZipFile(archive) as z:
                    members = [(m, os.path.basename(m.filename)) for m in z.infolist() if not m.is_dir()]
                    for m, base in members:
                        with z.open(m) as src, open(os.path.join(dest_dir, base), "wb") as out:
                            shutil.copyfileobj(src, out)
            else:
                with tarfile.open(archive) as t:
                    for m in t.getmembers():
                        if m.isfile():
                            with t.extractfile(m) as src, open(os.path.join(dest_dir, os.path.basename(m.name)), "wb") as out:
                                shutil.copyfileobj(src, out)
                            os.chmod(os.path.join(dest_dir, os.path.basename(m.name)), 0o755)
            os.remove(archive)
            job["progress"] = (i + 1) / len(platforms)
        job["message"] = "Installed " + ", ".join(TOOL_PLATFORMS[p] for p in platforms)

    return new_job("build", "Install Kiwix reader", run)


LAUNCH_MAC = """#!/bin/bash
# Double-click to open the Off-Grid Library.
cd "$(dirname "$0")"
ARCH=$(uname -m); [ "$ARCH" = "arm64" ] && P=macos-arm64 || P=macos-x86_64
BIN="kiwix-tools/$P/kiwix-serve"
[ -x "$BIN" ] || { echo "No Kiwix reader for $P on this drive."; read -r; exit 1; }
xattr -dr com.apple.quarantine kiwix-tools 2>/dev/null
"$BIN" --port {port} --library library.xml &
PID=$!; sleep 2; open "http://localhost:{port}/content/{guide}/"
echo "Off-Grid Library running at http://localhost:{port}  (close this window to stop)"
wait $PID
"""
LAUNCH_LINUX = """#!/bin/sh
# Run: sh START-Linux.sh
cd "$(dirname "$0")"
case "$(uname -m)" in aarch64|arm64) P=linux-aarch64;; *) P=linux-x86_64;; esac
BIN="kiwix-tools/$P/kiwix-serve"
[ -x "$BIN" ] || chmod +x "$BIN" 2>/dev/null
"$BIN" --port {port} --library library.xml &
PID=$!; sleep 2; (xdg-open "http://localhost:{port}/content/{guide}/" >/dev/null 2>&1 &)
echo "Off-Grid Library running at http://localhost:{port}  (Ctrl+C to stop)"
wait $PID
"""
LAUNCH_WIN = """@echo off
rem Double-click to open the Off-Grid Library.
cd /d "%~dp0"
start "" /b "kiwix-tools\\win-x86_64\\kiwix-serve.exe" --port {port} --library library.xml
timeout /t 2 >nul
start "" "http://localhost:{port}/content/{guide}/"
echo Off-Grid Library running at http://localhost:{port}  - close this window to stop.
pause >nul
"""
README = """OFF-GRID LIBRARY
================

Plug this drive into any computer, then:

  Mac      double-click  START-Mac.command   (first time: right-click > Open)
  Windows  double-click  START-Windows.bat
  Linux    run           sh START-Linux.sh

Your web browser opens the Off-Grid Field Guide. It works with no internet.
Every topic page links into the full libraries stored in the zim/ folder.

Readers available on this drive: {plats}

Phones/tablets: install the free Kiwix app and open the .zim files in zim/.
Other computers on the same network can browse to http://<this-computer-ip>:{port}
"""


def write_library_xml(files):
    """library.xml via kiwix-manage when available; otherwise a minimal index we write ourselves."""
    lib = os.path.join(root(), "library.xml")
    if os.path.exists(lib):
        os.remove(lib)
    manage = tool_path("kiwix-manage")
    if manage:
        subprocess.run([manage, "library.xml", "add"] + [os.path.join("zim", f) for f in files],
                       cwd=root(), check=True, capture_output=True, timeout=600)
        return "kiwix-manage"
    books = []
    for f in files:
        with open(os.path.join(zim_dir(), f), "rb") as z:
            head = z.read(24)
        book_id = str(uuid.UUID(bytes=head[8:24]))
        books.append(f'  <book id="{book_id}" path="zim/{f}" title="{f[:-4]}"/>')
    with open(lib, "w") as out:
        out.write('<?xml version="1.0" encoding="UTF-8" ?>\n<library version="20110515">\n' + "\n".join(books) + "\n</library>\n")
    return "built-in writer"


def queue_build():
    def run(job):
        ensure_root()
        job["message"] = "Building Off-Grid Field Guide ZIM…"
        guide = os.path.join(zim_dir(), build_guide.GUIDE_NAME + ".zim")
        docs = [{**f, "path": os.path.join(files_dir(), f["name"]), "mimetype": FILE_TYPES.get(os.path.splitext(f["name"])[1].lower(), ("application/octet-stream",))[0]}
                for f in custom_files() if os.path.isfile(os.path.join(files_dir(), f["name"]))]
        build_guide.build(guide, catalog_view(), on_drive(), custom_sites(), docs)
        job["progress"] = 0.5
        check_cancel(job)
        job["message"] = "Writing library.xml…"
        files = sorted(f for f in os.listdir(zim_dir()) if f.endswith(".zim"))
        how = write_library_xml(files)
        save_json(os.path.join(root(), BUILD_STATE), {"files": files, "docs": sorted(d["name"] for d in docs), "time": time.time()})
        write_device_file()  # the field identifier's list of what's on the drive
        job["progress"] = 0.8
        for fname, tpl in (("START-Mac.command", LAUNCH_MAC), ("START-Linux.sh", LAUNCH_LINUX), ("START-Windows.bat", LAUNCH_WIN)):
            p = os.path.join(root(), fname)
            text = tpl.replace("{port}", str(KIWIX_PORT)).replace("{guide}", build_guide.GUIDE_NAME)
            with open(p, "w", newline="\r\n" if fname.endswith(".bat") else "\n") as out:
                out.write(text)
            os.chmod(p, 0o755)
        plats = [TOOL_PLATFORMS[p] for p in TOOL_PLATFORMS if os.path.isdir(os.path.join(root(), "kiwix-tools", p))]
        with open(os.path.join(root(), "README-FIRST.txt"), "w") as out:
            out.write(README.format(plats=", ".join(plats) or "none yet (add them in step 3 of the builder)", port=KIWIX_PORT))
        job["message"] = f"Indexed {len(files)} ZIM files ({how}); launchers written"

    return new_job("build", "Build drive index & launchers", run)


# ------------------------------------------------------------------ kiwix-serve

serve = {"proc": None}


def serve_start():
    serve_stop()
    binp = tool_path("kiwix-serve")
    lib = os.path.join(root(), "library.xml")
    if not binp:
        raise ValueError("This computer's reader isn't on the drive yet. Tick it under 'Which computers should open this drive?' and build again.")
    if not os.path.exists(lib):
        raise ValueError("Build the drive index first")
    serve["proc"] = subprocess.Popen([binp, "--port", str(KIWIX_PORT), "--library", lib],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1.0)
    if serve["proc"].poll() is not None:
        err = serve["proc"].stderr.read().decode(errors="replace")[-300:]
        serve["proc"] = None
        raise RuntimeError("kiwix-serve exited: " + err)


def serve_stop():
    if serve["proc"] and serve["proc"].poll() is None:
        serve["proc"].terminate()
        serve["proc"].wait(5)
    serve["proc"] = None


# ------------------------------------------------------------------ packages

def catalog_view():
    """The catalog with your topic edits applied (new names, libraries added or removed). Topic ids never change."""
    edits = settings.get("topicEdits") or {}
    cats = []
    for c in CATALOG["categories"]:
        topics = []
        for t in c["topics"]:
            e = edits.get(t["id"]) or {}
            topics.append({**t, "title": e.get("title") or t["title"],
                           "kiwix": [n for n in e["kiwix"] if n in CATALOG["libraries"]] if "kiwix" in e else t["kiwix"],
                           "edited": bool(e), "originalTitle": t["title"]})
        cats.append({**c, "topics": topics})
    return {**CATALOG, "categories": cats}


def clean_package(b):
    """A saved cart: libraries from the catalog plus websites to copy. Also used for imported package files."""
    name = str(b.get("name") or "").strip()[:80]
    if not name:
        raise ValueError("Give the package a name")
    libs = []
    for n in b.get("libraries") or []:
        if n in CATALOG["libraries"] and n not in libs:
            libs.append(n)
    topics = {t["id"] for c in CATALOG["categories"] for t in c["topics"]}
    sites, seen = [], set()
    for s in b.get("sites") or []:
        url = str(s.get("url") or "").strip()
        if urllib.parse.urlparse(url).scheme not in ("http", "https") or url in seen:
            continue
        seen.add(url)
        sites.append({"url": url, "title": str(s.get("title") or urllib.parse.urlparse(url).netloc)[:80],
                      "topic": s.get("topic") if s.get("topic") in topics else None,
                      "pageLimit": max(0, min(int(s.get("pageLimit") or 200), 100000))})
    if not libs and not sites:
        raise ValueError("This package has nothing in it")
    return {"id": uuid.uuid4().hex[:10], "name": name, "description": str(b.get("description") or "").strip()[:500],
            "libraries": libs, "sites": sites, "created": time.strftime("%Y-%m-%d")}


# ------------------------------------------------------------------ state

def docker_ok():
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=8).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


_docker = {"ok": None, "t": 0}


def state():
    if time.time() - _docker["t"] > 30:
        _docker.update(ok=docker_ok(), t=time.time())
    drive = None
    if root():
        try:
            u = shutil.disk_usage(settings["drive"])
            drive = {"path": settings["drive"], "name": os.path.basename(settings["drive"].rstrip("/\\")) or settings["drive"],
                     "root": root(), "folder": os.path.basename(root()), "folderExists": os.path.isdir(root()), "free": u.free, "total": u.total, "fstype": fs_type(settings["drive"]),
                     "home": os.path.realpath(settings["drive"]) == os.path.realpath(os.path.expanduser("~"))}
        except OSError:
            drive = {"path": settings["drive"], "missing": True}
    have = on_drive() if drive and not drive.get("missing") else {}
    libs = {}
    for name, meta in CATALOG["libraries"].items():
        opt = chosen_option(name)
        f = have.get(name)
        libs[name] = {
            "title": meta["title"], "options": remote.get(name) or [],
            "flavour": opt["flavour"] if opt else meta.get("flavour", ""),
            "size": opt["size"] if opt else 0, "summary": opt["summary"] if opt else "",
            "file": f, "fileSize": os.path.getsize(os.path.join(zim_dir(), f)) if f else 0,
            "outdated": bool(f and opt and os.path.basename(opt["url"]) != f),
        }
    guide = os.path.join(zim_dir(), build_guide.GUIDE_NAME + ".zim") if root() else ""
    zims, needs_rebuild = [], False
    if drive and not drive.get("missing") and os.path.isdir(zim_dir()):
        zims = sorted(f for f in os.listdir(zim_dir()) if f.endswith(".zim"))
        lib = os.path.join(root(), "library.xml")
        last = load_json(os.path.join(root(), BUILD_STATE), None)
        if last is not None:
            needs_rebuild = sorted(last.get("files", [])) != zims or sorted(last.get("docs", [])) != sorted(f["name"] for f in custom_files())
        elif os.path.exists(lib):  # built by an older version of this app
            needs_rebuild = any(os.path.getmtime(os.path.join(zim_dir(), f)) > os.path.getmtime(lib) for f in zims)
    try:
        import libzim  # noqa: F401
        has_libzim = True
    except ImportError:
        has_libzim = False
    saved = None
    if settings.get("drive") and not root():  # a drive from last time, waiting for permission to reconnect
        p = settings["drive"]
        saved = {"path": p, "name": os.path.basename(p.rstrip("/\\")) or p, "available": os.path.isdir(p)}
    field = None
    if not (drive and drive.get("missing")):
        try:
            import_inbox()  # pick up anything the field identifier dropped on the drive
            field = field_summary()
        except OSError:
            pass
    plant = None
    if not (drive and drive.get("missing")):
        try:
            planter_import()
            plant = planter_summary()
        except OSError:
            pass
    return {
        "apiVersion": API_VERSION,
        "drive": drive,
        "savedDrive": saved,
        "permissions": {"scanAlways": bool(settings.get("scanAlways")), "autoConnect": bool(settings.get("autoConnect"))},
        "packages": packages,
        "favorites": settings.get("favorites"),
        "categories": catalog_view()["categories"],
        "suggestions": CATALOG["crawl_suggestions"],
        "libraries": libs,
        "catalogLoaded": bool(remote),
        "custom": custom_sites(),
        "files": custom_files(),
        "field": field,
        "planter": plant,
        "jobs": [public(j) for j in jobs[-40:]],
        "tools": {
            "docker": _docker["ok"], "libzim": has_libzim, "host": host_platform(),
            "platforms": [{"id": p, "label": l, "installed": bool(root()) and os.path.isdir(os.path.join(root(), "kiwix-tools", p))}
                          for p, l in TOOL_PLATFORMS.items()],
            "kiwixServe": bool(root()) and bool(tool_path("kiwix-serve")),
        },
        "guideBuilt": bool(guide) and os.path.exists(guide),
        "indexBuilt": bool(root()) and os.path.exists(os.path.join(root(), "library.xml")),
        "needsRebuild": needs_rebuild,
        "zimCount": len([f for f in zims if not f.startswith(build_guide.GUIDE_NAME)]),
        "serving": bool(serve["proc"] and serve["proc"].poll() is None),
        "kiwixUrl": f"http://localhost:{KIWIX_PORT}/content/{build_guide.GUIDE_NAME}/",
        "kiwixHome": f"http://localhost:{KIWIX_PORT}/",
    }


# ------------------------------------------------------------------ http

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/state":
            return self.send(200, state())
        if path == "/api/drives":
            return self.send(200, list_drives())
        if path == "/api/frameable":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            try:
                return self.send(200, frameable((q.get("url") or [""])[0]))
            except ValueError as ex:
                return self.send(400, {"error": str(ex)})
        if path == "/api/field":
            with lock:
                seed_field()
            if root() and not os.path.exists(field_dir("device.json")):
                write_device_file()
            return self.send(200, {**with_source_urls(field_journal()), "sure": FIELD_SURE, "inbox": field_dir("inbox"), "onDrive": bool(root())})
        if path == "/api/planter":
            planter_import()
            with planter_lock:
                return self.send(200, planter.view(planter_dir(), planter_finds()))
        if path == "/api/field/media":
            # A photo or sound clip that came with a find.
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            uid, name = _slug((q.get("upload") or [""])[0]), os.path.basename((q.get("name") or [""])[0])
            p = field_dir("media", uid, name) if uid and name else ""
            ext = os.path.splitext(name)[1].lower()
            if not p or ext not in FIELD_MEDIA or not os.path.isfile(p):
                return self.send(404, {"error": "not found"})
            with open(p, "rb") as f:
                return self.send(200, f.read(), FIELD_MEDIA[ext])
        if path == "/api/file":
            # Opens a file you added to a topic, straight from the drive.
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            name = os.path.basename((q.get("name") or [""])[0])
            p = os.path.join(files_dir(), name) if root() and name else ""
            if not p or not any(f["name"] == name for f in custom_files()) or not os.path.isfile(p):
                return self.send(404, {"error": "not found"})
            with open(p, "rb") as f:
                return self.send(200, f.read(), FILE_TYPES.get(os.path.splitext(name)[1].lower(), ("application/octet-stream",))[0])
        fname = "index.html" if path == "/" else path.lstrip("/")
        full = os.path.realpath(os.path.join(WEB, fname))
        if not full.startswith(WEB + os.sep) or not os.path.isfile(full):
            return self.send(404, {"error": "not found"})
        ctype = {"html": "text/html", "js": "text/javascript", "css": "text/css", "svg": "image/svg+xml"}.get(full.rsplit(".", 1)[-1], "application/octet-stream")
        with open(full, "rb") as f:
            self.send(200, f.read(), ctype + "; charset=utf-8")

    def do_POST(self):
        # Only accept requests from this app's own page.
        origin = self.headers.get("Origin", "")
        if origin and urllib.parse.urlparse(origin).netloc not in (f"localhost:{UI_PORT}", f"127.0.0.1:{UI_PORT}"):
            return self.send(403, {"error": "forbidden"})
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/upload":
            # Raw file body (not JSON), so big PDFs stream to the drive instead of sitting in memory.
            q = urllib.parse.parse_qs(url.query)
            try:
                if not root():
                    raise ValueError("Choose a drive first")
                entry = save_upload((q.get("name") or [""])[0], (q.get("topic") or [""])[0],
                                    int(self.headers.get("Content-Length") or 0), self.rfile)
                return self.send(200, entry)
            except (ValueError, OSError) as ex:
                self.close_connection = True  # the rest of the body may be unread
                return self.send(400, {"error": str(ex)})
        if url.path == "/api/field/upload":
            # A field package (.json or .zip) picked on the Field identification page: it goes through the inbox
            # like one the device left on the drive, so both are imported the same way.
            q = urllib.parse.parse_qs(url.query)
            try:
                name = os.path.basename((q.get("name") or [""])[0]).strip()
                if not name.lower().endswith((".json", ".zip")):
                    raise ValueError("Pick the .json or .zip file the field identifier made")
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > FIELD_MAX_UPLOAD:
                    raise ValueError("That file is empty" if length <= 0 else "That file is too big (over 1 GB)")
                os.makedirs(field_dir("inbox"), exist_ok=True)
                safe = re.sub(r"[^A-Za-z0-9._ -]+", "-", name)
                tmp = field_dir(f"upload-{uuid.uuid4().hex[:8]}-{safe}")
                copy_stream(self.rfile, length, tmp)
                try:
                    up = import_file(tmp, name)
                except (ValueError, RuntimeError, zipfile.BadZipFile) as ex:
                    raise ValueError(f"Couldn't read {name}: {ex}")
                finally:
                    if os.path.exists(tmp):
                        _move(tmp, field_dir("imported"))
                if not up:
                    return self.send(200, {"duplicate": True})
                return self.send(200, {"id": up["id"], "count": len(up["entries"]),
                                       "needs": sum(e["status"] != "identified" for e in up["entries"])})
            except (ValueError, OSError) as ex:
                self.close_connection = True
                return self.send(400, {"error": str(ex)})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            result = self.route(urllib.parse.urlparse(self.path).path, body)
            self.send(200, result if result is not None else {"ok": True})
        except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as ex:
            self.send(400, {"error": str(ex)})

    def route(self, path, b):
        needs_drive = not (path in ("/api/settings", "/api/resolve", "/api/flavour", "/api/connect", "/api/permissions", "/api/favorite", "/api/topic")
                           or path.startswith("/api/packages/") or path.startswith("/api/field/") or path.startswith("/api/planter/"))
        if needs_drive and not root():
            raise ValueError("Choose a drive first")
        if path == "/api/settings":
            d = os.path.expanduser(b.get("drive", "").strip())
            if not os.path.isdir(d):
                raise ValueError(f"Folder not found: {d}")
            with lock:
                settings["drive"] = d
                save_json(SETTINGS_FILE, settings)
                session["connected"] = True  # the person just picked it
                adopt_library(d)
        elif path == "/api/connect":
            d = settings.get("drive")
            if not d:
                raise ValueError("No drive saved yet")
            if not os.path.isdir(d):
                raise ValueError(f"{os.path.basename(d.rstrip('/')) or d} isn't connected. Plug it in, or pick another drive.")
            with lock:
                session["connected"] = True
                adopt_library(d)
                if b.get("remember"):
                    settings["autoConnect"] = True
                    save_json(SETTINGS_FILE, settings)
        elif path == "/api/permissions":
            with lock:
                for k in ("scanAlways", "autoConnect"):
                    if k in b:
                        settings[k] = bool(b[k])
                save_json(SETTINGS_FILE, settings)
        elif path == "/api/favorite":
            pid = str(b.get("id") or "")[:40]
            if not pid:
                raise ValueError("No package given")
            with lock:
                favs = list(b["defaults"] if settings.get("favorites") is None and isinstance(b.get("defaults"), list) else settings.get("favorites") or [])
                favs = [str(x)[:40] for x in favs if x != pid][:200]
                if b.get("favorite"):
                    favs.append(pid)
                settings["favorites"] = favs
                save_json(SETTINGS_FILE, settings)
        elif path == "/api/packages/save":
            pkg = clean_package(b)
            with lock:
                packages.append(pkg)
                save_json(PACKAGES_FILE, packages)
            return pkg
        elif path == "/api/packages/update":
            # Edits a saved package in place. Editing one of Commune's starter packs (id "commune-…") saves your own copy under
            # the same id, which the page shows instead of the original; deleting that copy brings the original back.
            pid = str(b.get("id") or "")[:40]
            pkg = clean_package(b)
            with lock:
                old = next((x for x in packages if x["id"] == pid), None)
                if old:
                    pkg.update(id=pid, created=old.get("created", pkg["created"]))
                    packages[packages.index(old)] = pkg
                elif re.fullmatch(r"commune-[a-z0-9-]{1,30}", pid):
                    pkg.update(id=pid, edited=True)
                    packages.append(pkg)
                else:
                    raise ValueError("That package no longer exists")
                save_json(PACKAGES_FILE, packages)
            return pkg
        elif path == "/api/packages/import":
            pkg = clean_package(b.get("package") or {})
            with lock:
                packages.append(pkg)
                save_json(PACKAGES_FILE, packages)
            return pkg
        elif path == "/api/packages/delete":
            with lock:
                packages[:] = [p for p in packages if p["id"] != b.get("id")]
                save_json(PACKAGES_FILE, packages)
                # Resetting an edited Commune pack keeps it starred; deleting your own package unstars it.
                if settings.get("favorites") and b.get("id") in settings["favorites"] and not str(b.get("id")).startswith("commune-"):
                    settings["favorites"] = [x for x in settings["favorites"] if x != b.get("id")]
                    save_json(SETTINGS_FILE, settings)
        elif path == "/api/resolve":
            return {"resolved": refresh_catalog()}
        elif path == "/api/flavour":
            if b["name"] not in CATALOG["libraries"]:
                raise ValueError("unknown library")
            with lock:
                settings["flavours"][b["name"]] = b["flavour"]
                save_json(SETTINGS_FILE, settings)
        elif path == "/api/download":
            name_library(b.get("folder"))
            errors, queued = [], 0
            for n in b.get("names", []):
                try:
                    queue_download(n)
                    queued += 1
                except ValueError as ex:
                    errors.append(str(ex))
            return {"queued": queued, "errors": errors}
        elif path == "/api/topic":
            # Rename a topic or change which libraries it lists; {"reset": true} goes back to Commune's version.
            tid = b.get("id")
            if tid not in {t["id"] for c in CATALOG["categories"] for t in c["topics"]}:
                raise ValueError("Unknown topic")
            with lock:
                edits = settings.setdefault("topicEdits", {})
                if b.get("reset"):
                    edits.pop(tid, None)
                else:
                    title = str(b.get("title") or "").strip()[:80]
                    if not title:
                        raise ValueError("Give the topic a name")
                    kiwix = []
                    for n in b.get("kiwix") or []:
                        if n in CATALOG["libraries"] and n not in kiwix:
                            kiwix.append(n)
                    edits[tid] = {"title": title, "kiwix": kiwix}
                save_json(SETTINGS_FILE, settings)
        elif path == "/api/custom/update":
            # Moves a website already copied to the drive to another topic (the copy itself doesn't change).
            topics = {t["id"] for c in CATALOG["categories"] for t in c["topics"]}
            topic = b.get("topic") or None
            if topic is not None and topic not in topics:
                raise ValueError("Unknown topic")
            with lock:
                sites = custom_sites()
                site = next((c for c in sites if c.get("file") == b.get("file")), None)
                if not site:
                    raise ValueError("That website isn't on the drive any more")
                site["topic"] = topic
                save_json(os.path.join(root(), "custom.json"), sites)
        elif path == "/api/delete":
            f = os.path.basename(b["file"])
            os.remove(os.path.join(zim_dir(), f))
            sites = [c for c in custom_sites() if c.get("file") != f]
            save_json(os.path.join(root(), "custom.json"), sites)
        elif path == "/api/files/delete":
            name = os.path.basename(str(b.get("name") or ""))
            with lock:
                files = custom_files()
                if not any(f["name"] == name for f in files):
                    raise ValueError("That file isn't on the drive any more")
                p = os.path.join(files_dir(), name)
                if os.path.exists(p):
                    os.remove(p)
                save_json(os.path.join(root(), "files.json"), [f for f in files if f["name"] != name])
        elif path.startswith("/api/field/"):
            return self.field_route(path, b)
        elif path == "/api/planter/import":
            return planter_import()
        elif path == "/api/planter/sync":
            r = planter_sync()
            if r.get("error"):
                raise ValueError(r["error"])
            return r
        elif path == "/api/planter/bridge":
            with planter_lock:
                status = planter.set_bridge(planter_dir(), b.get("url"), b.get("key"))
            return {"status": status, **(planter_sync() if status else {})}
        elif path in ("/api/planter/card/import", "/api/planter/card/write"):
            # The planter's SD card, plugged into this computer.
            with planter_lock:
                if path.endswith("import"):
                    return planter.import_card(planter_dir(), b.get("path"))
                return planter.write_card(planter_dir(), b.get("path"), planter_finds())
        elif path == "/api/planter/board":
            # Settings changed on the planter itself: keep them, or send Commune's again.
            with planter_lock:
                if b.get("action") == "adopt":
                    planter.adopt_board(planter_dir(), b.get("device"), planter_finds())
                else:
                    planter.resend_settings(planter_dir(), planter_finds())
            planter_sync_soon()
        elif path in ("/api/planter/settings", "/api/planter/grow", "/api/planter/dismiss"):
            # The Planter page: watering settings, what each zone is growing, and clearing read errors.
            with planter_lock:
                if path == "/api/planter/settings":
                    saved = planter.set_settings(planter_dir(), b.get("settings"), planter_finds())
                    planter_sync_soon()  # reach the bridge now, so the planter gets them at its next report
                    return {"settings": saved}
                if path == "/api/planter/grow":
                    planter.set_growing(planter_dir(), b.get("zone"), b.get("links"), planter_finds())
                    return {"growing": planter.view(planter_dir(), planter_finds())["growing"]}
                planter.dismiss_errors(planter_dir())
        elif path == "/api/cancel":
            for j in jobs:
                if j["id"] == b["id"]:
                    j["cancel"] = True
                    if j["status"] == "queued":
                        j["status"], j["message"] = "cancelled", "Cancelled"
        elif path == "/api/clear":
            with lock:
                jobs[:] = [j for j in jobs if j["status"] in ("queued", "running")]
        elif path == "/api/crawl":
            name_library(b.get("folder"))
            queue_crawl(b.get("url", "").strip(), b.get("title", "").strip(), b.get("topic") or None, b.get("pageLimit") or 0)
        elif path == "/api/tools":
            plats = [p for p in b.get("platforms", []) if p in TOOL_PLATFORMS]
            if not plats:
                raise ValueError("Pick at least one platform")
            queue_tools(plats)
        elif path == "/api/build":
            queue_build()
        elif path == "/api/serve":
            serve_start() if b.get("action") == "start" else serve_stop()
        else:
            raise ValueError("unknown endpoint")

    def field_route(self, path, b):
        """Notes, confirmations and clean-up on the Field identification page."""
        if path == "/api/field/import":
            return import_inbox()
        if path == "/api/field/sample":
            up = load_sample()  # remove them again with Delete upload
            return {"id": "commune-sample", "duplicate": up is None, "count": len(up["entries"]) if up else 0}
        uid, eid = str(b.get("upload") or ""), str(b.get("entry") or "")
        with lock:
            j = field_journal()
            if path == "/api/field/note":
                e = find_entry(j, uid, eid)
                e["notes"] = _txt(b.get("notes"), 5000, lines=True)
                e["notesUpdated"] = now_iso()
            elif path == "/api/field/confirm":
                # You identify it yourself: one of the device's guesses, or your own answer, always with a source.
                # It's marked identifiedBy "user", kept apart from the device's own guess, and added to knowledge.json.
                e = find_entry(j, uid, eid)
                name = _txt(b.get("name"), 160)
                if not name:
                    raise ValueError("Type what it is first")
                c = b.get("citation") if isinstance(b.get("citation"), dict) else {}
                ctype, ctitle, cdetail = _txt(c.get("type"), 20), _txt(c.get("title"), 200), _txt(c.get("detail"), 500)
                curl = _url(c.get("url")) or _url(cdetail) or _url(ctitle)
                if ctype not in CITE_TYPES:
                    raise ValueError("Say what kind of source you used: a website, book, field guide, person…")
                if not ctitle:
                    raise ValueError("Add your source: the website, book or person you identified it with")
                if ctype not in CITE_NO_URL and not curl:
                    raise ValueError("Add the source's website (starting with http:// or https://): where the information can be found")
                if cdetail == curl:
                    cdetail = ""
                if "deviceGuess" not in e:
                    e["deviceGuess"] = {"name": e.get("name"), "scientific": e.get("scientific"), "confidence": e.get("confidence"), "status": e["status"]}
                e.update(name=name, scientific=_txt(b.get("scientific"), 160), status="identified", confirmed=now_iso(),
                         identifiedBy="user", citation={"type": ctype, "title": ctitle, "detail": cdetail, "url": curl})
            elif path == "/api/field/unconfirm":
                e = find_entry(j, uid, eid)
                e.update(status="needs-id", confirmed=None, identifiedBy=None, citation=None)
            elif path == "/api/field/delete":
                if not any(u["id"] == uid for u in j["uploads"]):
                    raise ValueError("That upload isn't in the journal any more")
                j["uploads"] = [u for u in j["uploads"] if u["id"] != uid]
                media = field_dir("media", _slug(uid))
                if _slug(uid) and os.path.isdir(media):
                    shutil.rmtree(media)
            elif path == "/api/field/dismiss":
                j["errors"] = []
            else:
                raise ValueError("unknown endpoint")
            save_field(j)
        if path in ("/api/field/delete", "/api/field/confirm", "/api/field/unconfirm"):
            write_device_file()  # its knowledge count and last upload


def main():
    for lane in ({"download"}, {"crawl"}, {"build"}):
        threading.Thread(target=worker, args=(lane,), daemon=True).start()
    if not remote:
        threading.Thread(target=lambda: _try(refresh_catalog), daemon=True).start()
    threading.Thread(target=planter_sync_loop, daemon=True).start()  # the planter's bridge, every 2 minutes
    if settings.get("drive") and settings.get("autoConnect") and os.path.isdir(settings["drive"]):
        adopt_library(settings["drive"])  # pick up a library made before folders were named (OffGridLibrary)
    srv = ThreadingHTTPServer(("127.0.0.1", UI_PORT), Handler)
    url = f"http://localhost:{UI_PORT}"
    print(f"Off-Grid Library builder running at {url}  (Ctrl+C to quit)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serve_stop()


def _try(fn):
    try:
        fn()
    except Exception as ex:
        print("Background task failed (offline?):", ex)


if __name__ == "__main__":
    main()
