"""Build the "Off-Grid Field Guide" pseudosite as a ZIM file with python-libzim.

The guide is the drive's home page: one page per topic from catalog.json, each
linking to whichever real libraries (Kiwix ZIMs or crawled sites) are on the
drive. Links use kiwix-serve's /content/<book>/ URLs, so they work when the
drive is opened through the bundled launchers.

    python build_guide.py OUTPUT.zim [--zim-dir DIR]
"""
import argparse
import datetime
import html
import json
import os
import re
import struct
import zlib
from urllib.parse import quote

from guide_content import PAGES

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE_NAME = "offgrid-field-guide"

CSS = """
:root{color-scheme:light;--bg:#f0f3f2;--fg:#363c3a;--muted:#65706c;--card:#ffffff;--line:#d7dfdc;--accent:#2e7a64;--green:#256a56;--warn:#8a4a2b;--warnbg:#f8ebe3}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 64px}a{color:var(--accent)}
header.top{border-bottom:2px solid var(--green);margin-bottom:24px;padding-bottom:12px}
header.top .crumb{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
h1{font-size:30px;line-height:1.15;margin:4px 0}h2{font-size:19px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:15px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--card)}
.warn{background:var(--warnbg);border-left:4px solid var(--warn);padding:10px 12px;border-radius:4px}
.libs{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin-top:32px}
.libs h2{margin-top:4px;border:0}.libs li{margin:4px 0}.off{color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.cat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px}
.cat h2{margin-top:0;font-size:17px}.cat ul{padding-left:18px;margin:0}.cat li{margin:3px 0}
.emerg{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 24px}.emerg a{background:var(--warn);color:var(--bg);padding:8px 12px;border-radius:6px;text-decoration:none;font-weight:600}
footer{margin-top:40px;font-size:13px;color:var(--muted)}
"""


def png_icon(size=48):
    """A tiny green-on-cream tent glyph, written as a PNG without dependencies."""
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            cx = abs(x - size / 2)
            inside = y > size * 0.2 and cx < (y - size * 0.2) * 0.75 and y < size * 0.85
            door = y > size * 0.55 and cx < (y - size * 0.55) * 0.5 and y < size * 0.85
            if door:
                row += bytes((244, 241, 232))
            elif inside:
                row += bytes((61, 107, 53))
            else:
                row += bytes((244, 241, 232))
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def page(title, body, crumb="Off-Grid Field Guide", home=False):
    back = "" if home else '<p><a href="index.html">← All topics</a></p>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<link rel="stylesheet" href="style.css"></head><body><main>
<header class="top"><div class="crumb">{html.escape(crumb)}</div><h1>{html.escape(title)}</h1></header>
{back}{body}
<footer>Off-Grid Field Guide · quick reference only. Get hands-on training where you can.</footer>
</main></body></html>"""


def book_stem(filename):
    return os.path.splitext(os.path.basename(filename))[0]


def library_links(topic, catalog, on_drive, custom, files=()):
    """HTML list of libraries for a topic; on_drive maps library name -> zim filename."""
    items = []
    for name in topic.get("kiwix", []):
        title = catalog["libraries"].get(name, {}).get("title", name)
        if name in on_drive:
            items.append(f'<li><a href="/content/{html.escape(book_stem(on_drive[name]))}/">{html.escape(title)}</a></li>')
        else:
            items.append(f'<li class="off">{html.escape(title)} (not on this drive)</li>')
    for c in custom:
        if c.get("topic") == topic["id"] and c.get("file"):
            items.append(f'<li><a href="/content/{html.escape(book_stem(c["file"]))}/">{html.escape(c["title"])}</a> (crawled website)</li>')
    for f in files:
        if f.get("topic") == topic["id"]:
            items.append(f'<li><a href="files/{html.escape(quote(f["name"]))}">{html.escape(f["title"])}</a> ({html.escape(f.get("kind", "file"))})</li>')
    return ('<section class="libs"><h2>Full libraries on this drive</h2><ul>' + "".join(items) +
            '</ul><p class="off">Links open in the Kiwix reader started by the drive\'s START launcher.</p></section>')


def build(output, catalog, on_drive=None, custom=None, files=None):
    """files: documents added to topics, each {"name", "title", "topic", "path", "mimetype"}; packed in under files/."""
    from libzim.writer import Creator, FileProvider, Hint, Item, StringProvider

    on_drive = on_drive or {}
    custom = custom or []
    files = files or []

    class Entry(Item):
        def __init__(self, path, title, content, mimetype="text/html", front=True):
            super().__init__()
            self.path, self.title, self.content = path, title, content
            self.mimetype, self.front = mimetype, front

        def get_path(self):
            return self.path

        def get_title(self):
            return self.title

        def get_mimetype(self):
            return self.mimetype

        def get_contentprovider(self):
            return StringProvider(self.content)

        def get_hints(self):
            return {Hint.FRONT_ARTICLE: self.front}

    class FileEntry(Entry):
        def get_contentprovider(self):
            return FileProvider(self.content)  # content is the file's path on disk

    entries = [Entry("style.css", "style", CSS, "text/css", front=False)]
    entries += [FileEntry("files/" + f["name"], f["title"], f["path"], f["mimetype"], front=False) for f in files]

    cards = []
    for cat in catalog["categories"]:
        lis = []
        for t in cat["topics"]:
            body = PAGES.get(t["id"], "<p>No quick guide yet; see the libraries below.</p>")
            body += library_links(t, catalog, on_drive, custom, files)
            entries.append(Entry(f'{t["id"]}.html', t["title"], page(t["title"], body, cat["title"])))
            lis.append(f'<li><a href="{t["id"]}.html">{html.escape(t["title"])}</a></li>')
        cards.append(f'<div class="cat"><h2>{html.escape(cat["title"])}</h2><ul>{"".join(lis)}</ul></div>')

    extra = [c for c in custom if c.get("file") and not c.get("topic")]
    if extra:
        lis = "".join(f'<li><a href="/content/{html.escape(book_stem(c["file"]))}/">{html.escape(c["title"])}</a></li>' for c in extra)
        cards.append(f'<div class="cat"><h2>Crawled websites</h2><ul>{lis}</ul></div>')

    emergency = "".join(f'<a href="{i}.html">{l}</a>' for i, l in
                        [("cpr", "CPR"), ("choking", "Choking"), ("wounds", "Bleeding"), ("burns", "Burns"),
                         ("poison", "Poisoning"), ("water", "Safe water"), ("shelter", "Shelter")])
    home = (f'<p>Quick references for living off-grid, with links into the full offline libraries on this drive '
            f'({len(on_drive) + sum(1 for c in custom if c.get("file"))} installed).</p>'
            f'<div class="emerg">{emergency}</div><div class="grid">{"".join(cards)}</div>')
    entries.append(Entry("index.html", "Off-Grid Field Guide", page("Off-Grid Field Guide", home, "Home", home=True)))

    tmp = output + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    with Creator(tmp).config_indexing(True, "eng") as creator:
        creator.set_mainpath("index.html")
        creator.add_illustration(48, png_icon())
        for k, v in {
            "Name": GUIDE_NAME,
            "Title": "Off-Grid Field Guide",
            "Description": "Survival quick references with links to the drive's offline libraries",
            "Language": "eng",
            "Creator": "Off-Grid Library",
            "Publisher": "Off-Grid Library",
            "Date": datetime.date.today().isoformat(),
            "Tags": "survival;preppers;_ftindex:yes",
        }.items():
            creator.add_metadata(k, v)
        for e in entries:
            creator.add_item(e)
    os.replace(tmp, output)
    return output


def scan(zim_dir, catalog):
    """Map library name -> zim filename for the Kiwix libraries found in zim_dir."""
    found = {}
    files = sorted(os.listdir(zim_dir)) if os.path.isdir(zim_dir) else []
    for name in catalog["libraries"]:
        pat = re.compile(r"^" + re.escape(name) + r"(_[a-z]+)?_\d{4}-\d{2}\.zim$")
        hits = [f for f in files if pat.match(f)]
        if hits:
            found[name] = hits[-1]  # newest date sorts last
    return found


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--zim-dir", help="folder of downloaded ZIMs to link to")
    args = ap.parse_args()
    with open(os.path.join(HERE, "catalog.json")) as f:
        cat = json.load(f)
    print(build(args.output, cat, scan(args.zim_dir, cat) if args.zim_dir else {}))
