"""The planter's bridge: an always-on mailbox between the planter and Commune. Run it on a Raspberry Pi.

    python3 -m commune_link.bridge --key some-shared-secret            (from automated_planter_system/)

The planter posts its readings here over Wi-Fi (no internet needed) and gets back the time and its settings.
Commune, on your Mac or PC, collects the readings and leaves new settings whenever it's open. Readings wait here
(in ~/planter-bridge by default) until it does. Standard library only.

  Planter:  POST /planter/report      readings and events in, {now, utcOffset, settings} back
            GET  /planter/settings    the latest settings
  Commune:  GET  /planter/packages?after=<name>   reports since the last one Commune collected
            POST /planter/settings    new settings from Commune
            GET  /planter/status      a connection check
Every request needs the header X-Planter-Key when the bridge was started with --key.
"""

import argparse
import hmac
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if __package__ in (None, ""):  # run as a plain script: python3 commune_link/bridge.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from commune_link.link import Mailbox, package_from_report
else:
    from .link import Mailbox, package_from_report

MAX_BODY = 512 * 1024


def utc_offset(now):
    lt = time.localtime(now)
    return lt.tm_gmtoff if lt.tm_gmtoff is not None else -time.timezone


class Bridge(BaseHTTPRequestHandler):
    mailbox = None
    key = ""
    lock = threading.Lock()
    server_version = "CommunePlanterBridge/2"

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} {self.client_address[0]} {fmt % args}\n")

    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def allowed(self):
        if self.key and not hmac.compare_digest(self.headers.get("X-Planter-Key", ""), self.key):
            self.reply(403, {"error": "wrong key"})
            return False
        return True

    def body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            raise ValueError("empty or too big")
        return json.loads(self.rfile.read(length))

    def for_planter(self):
        now = time.time()
        return {"ok": True, "now": int(now), "utcOffset": utc_offset(now), "settings": self.mailbox.settings()}

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if not self.allowed():
            return
        if url.path == "/planter/settings":
            return self.reply(200, self.for_planter())
        if url.path == "/planter/status":
            return self.reply(200, {"ok": True, **self.mailbox.status()})
        if url.path == "/planter/packages":
            q = urllib.parse.parse_qs(url.query)
            after = (q.get("after") or [""])[0]
            limit = max(1, min(500, int((q.get("limit") or ["100"])[0] or 100)))
            items, more = self.mailbox.after(after, limit)
            return self.reply(200, {"packages": items, "more": more})
        return self.reply(404, {"error": "not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path not in ("/planter/report", "/planter/settings"):
            return self.reply(404, {"error": "not found"})
        if not self.allowed():
            return
        try:
            data = self.body()
            with self.lock:
                if path == "/planter/report":
                    pkg = package_from_report(data)
                    name = self.mailbox.store(pkg)
                    if name:
                        self.log_message("saved %d readings, %d events as %s", len(pkg["readings"]), len(pkg["events"]), name)
                    return self.reply(200, self.for_planter())
                self.mailbox.save_settings(data)
                self.log_message("new settings from Commune (%s)", data.get("settingsChanged", ""))
                return self.reply(200, {"ok": True})
        except ValueError as ex:
            return self.reply(400, {"error": str(ex)})
        except OSError as ex:
            return self.reply(503, {"error": f"couldn't save: {ex}"})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mailbox between the planter and Commune.")
    ap.add_argument("--data", default=os.path.expanduser("~/planter-bridge"), help="where readings and settings are kept")
    ap.add_argument("--port", type=int, default=8650)
    ap.add_argument("--host", default="0.0.0.0", help="address to listen on (0.0.0.0: every network on this computer)")
    ap.add_argument("--key", default=os.environ.get("PLANTER_KEY", ""), help="shared key: PLANTER_KEY in planter_config.h, and the key in Commune")
    a = ap.parse_args(argv)
    Bridge.mailbox, Bridge.key = Mailbox(a.data), a.key
    Bridge.mailbox.prune()
    if not a.key:
        print("Warning: no --key set, so anyone on this network can post readings or change settings.")
    srv = ThreadingHTTPServer((a.host, a.port), Bridge)
    print(f"Planter bridge on port {a.port}, keeping data in {Bridge.mailbox.folder}")
    print("Point BRIDGE_HOST in planter_config.h, and the bridge address in Commune, at this computer.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
