"use strict";
// Commune builder UI: a landing page, then three steps (choose topics → choose a drive → build & test), driven by /api/state.

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = n => {
  if (!n) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return (i < 2 ? Math.round(n) : n.toFixed(n < 10 ? 1 : 0)) + " " + u[i];
};
const MB = 1024 ** 2, GB = 1024 ** 3;
const host = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

const ICON = {
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>',
  warn: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 21h20L12 3zM12 10v5M12 18h.01"/></svg>',
  eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"/></svg>',
  ext: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/></svg>',
  link: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>',
};
const ON_DRIVE = `<span class="on-drive">${ICON.check}On drive</span>`;
const FLAVOURS = { maxi: "With images", nopic: "Text only", mini: "Short version", "": "Standard" };
// Small, high-value libraries (about 6 GB together): medicine, water, food, knots, outdoors, radio, mechanics.
const ESSENTIALS = ["zimgit-medicine_en", "irp.fas.org_en_military-medicine", "wikipedia_en_medicine", "zimgit-water_en",
  "zimgit-food-preparation_en", "zimgit-knots_en", "zimgit-post-disaster_en", "outdoors.stackexchange.com_en_all",
  "ham.stackexchange.com_en_all", "mechanics.stackexchange.com_en_all", "ifixit_en_all"];
const STEPS = ["home", "pick", "drive", "build", "field", "planter"];

// Commune's own starter packages. They show on the landing page until the person stars their own favorites.
const COMMUNE_PACKS = [
  { id: "commune-outage", builtin: true, name: "Outage kit", sites: [],
    description: "For power, internet and phone outages: first aid, safe water, food storage, disaster recovery, ham radio and off-grid power.",
    libraries: ["zimgit-medicine_en", "wikipedia_en_medicine", "zimgit-water_en", "zimgit-food-preparation_en", "zimgit-post-disaster_en", "ready.gov_en_all", "ham.stackexchange.com_en_all", "energypedia_en_all"] },
  { id: "commune-camping", builtin: true, name: "Camping trip", sites: [],
    description: "Outdoor skills, knots, water purification, field medicine, and plant and animal identification.",
    libraries: ["outdoors.stackexchange.com_en_all", "scoutwiki.org_en_all", "zimgit-knots_en", "zimgit-water_en", "irp.fas.org_en_military-medicine", "gardenology_en_all", "wikispecies_en_all"] },
  { id: "commune-fixit", builtin: true, name: "Fix it yourself", sites: [],
    description: "Repair guides, home improvement, electronics, car mechanics and low-tech builds, so you can mend what breaks.",
    libraries: ["ifixit_en_all", "diy.stackexchange.com_en_all", "electronics.stackexchange.com_en_all", "mechanics.stackexchange.com_en_all", "appropedia_en_all", "solar.lowtechmagazine.com_mul_all"] },
  { id: "commune-essentials", builtin: true, name: "Survival essentials", sites: [],
    description: "The small, high-value core: medicine, water, food, knots, outdoors, radio and mechanics.",
    libraries: ESSENTIALS },
];

// Per-browser conveniences only; the server holds everything that matters.
const store = {
  // Falls back to the "offie.…" key from when the app was called Offie.
  get(k, d) { try { return JSON.parse(localStorage.getItem(k) ?? localStorage.getItem(k.replace(/^commune\./, "commune."))) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } },
};

let S = null;                                        // last /api/state
let drives = null;                                   // last /api/drives
const picked = new Set(store.get("commune.picked", [])); // library names waiting for "Download & continue"
let pending = store.get("commune.pending", []);         // websites waiting to be copied: {url,title,topic,pageLimit}
let cat = store.get("commune.cat", null);              // selected category in step 1
let plats = null, platsDrive = null;                 // reader platforms ticked in step 3
let qaCat = null;                                    // quick-add dialog
let pv = null;                                       // item shown in the preview pop-up
let lostConnection = false, missingWarned = false;
let scanAllowed = false;                             // the person said yes to looking for drives (this visit)
let driveError = "";                                 // last drive-scan failure, shown in the list
let connectDismissed = false;                        // "Not now" on the reconnect banner (this visit)
const sigs = {};
const changed = (key, val) => { const s = JSON.stringify(val); if (sigs[key] === s) return false; sigs[key] = s; return true; };
let qPkgs = store.get("commune.qpkgs", []).map(id => id.replace(/^offie-/, "commune-"));             // ids of packages added to the queue as a whole
const save = () => {
  // Forget packages once none of their items are left in the queue.
  if (S) qPkgs = qPkgs.filter(id => { const p = findPkg(id); return p && (p.libraries.some(n => picked.has(n)) || p.sites.some(x => pending.some(y => y.url === x.url))); });
  store.set("commune.picked", [...picked]); store.set("commune.pending", pending); store.set("commune.qpkgs", qPkgs);
};

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}
function notice(msg, kind = "") {
  const n = $("#notice");
  n.className = "notice " + kind; n.innerHTML = msg; n.hidden = !msg;
  if (msg && !kind) setTimeout(() => { if (n.innerHTML === msg) n.hidden = true; }, 6000);
}
async function act(fn, ok) {
  try { const r = await fn(); if (ok) notice(typeof ok === "function" ? ok(r) : ok); }
  catch (e) { notice(esc(e.message), "error"); }
  await refresh();
}

// ------------------------------------------------------------------ catalog helpers
const hasDrive = () => !!(S?.drive && !S.drive.missing);
const sameTopic = (a, b) => (a || "") === (b || "");
const isVideo = n => /\(video\)/i.test(S.libraries[n]?.title || "");
const libSize = n => S.libraries[n]?.size || 0;
const isFat = fs => /^(msdos|vfat|fat|fat32)$/i.test(fs || "");
const liveJob = j => j.status === "running" || j.status === "queued";
const activeJob = name => S.jobs.find(j => j.library === name && liveJob(j));
const canPick = n => { const L = S.libraries[n]; return !!(L && L.options.length && (!L.file || L.outdated) && !activeJob(n)); };

function allCats() {
  const cats = S.categories.slice();
  if (S.custom.some(c => !c.topic) || pending.some(p => !p.topic))
    cats.push({ id: "__other", title: "Other websites", topics: [{ id: "", title: "Websites without a topic", kiwix: [] }] });
  return cats;
}
function topicIndex() {
  const m = {};
  allCats().forEach(c => c.topics.forEach(t => { m[t.id] = { ...t, cat: c }; }));
  return m;
}
function usage() {
  const u = {};
  S.categories.forEach(c => c.topics.forEach(t => t.kiwix.forEach(n => { u[n] = (u[n] || 0) + 1; })));
  return u;
}
const topicOnDrive = t => t.kiwix.some(n => S.libraries[n]?.file) || S.custom.some(c => sameTopic(c.topic, t.id) && c.file) || (S.files || []).some(f => sameTopic(f.topic, t.id));
const topicPicked = t => t.kiwix.some(n => picked.has(n)) || pending.some(p => sameTopic(p.topic, t.id));

// ------------------------------------------------------------------ routing
function step() {
  const h = location.hash.slice(1);
  return STEPS.includes(h) ? h : "home";
}
// Back arrow: each in-app page change is numbered in history.state, so "back" only leaves pages this visit opened.
const navDepth = () => history.state?.depth || 0;
if (!history.state) history.replaceState({ depth: 0 }, "");
let lastDepth = navDepth();
window.addEventListener("hashchange", () => {
  if (history.state?.depth == null) history.replaceState({ depth: lastDepth + 1 }, "");
  lastDepth = navDepth();
  render(); window.scrollTo(0, 0);
});
const PARENT = { pick: "home", drive: "pick", build: "drive", field: "home", planter: "home" };
$("#back-btn").onclick = () => { if (navDepth() > 0) history.back(); else location.hash = "#" + (PARENT[step()] || "home"); };

function render() {
  if (!S) return;
  let st = step();
  if (st === "build" && !hasDrive()) {
    history.replaceState(history.state, "", "#drive"); st = "drive";
  }
  STEPS.forEach(s => { $("#step-" + s).hidden = s !== st; });
  document.body.classList.toggle("on-home", st === "home");
  document.body.classList.toggle("green", st === "home" || st === "planter");  // the landing page's colours
  $("#steps").hidden = !["pick", "drive", "build"].includes(st);  // the three steps show only while you're on one of them
  renderHeader(st);
  renderConnectBanner();
  $$(".lib-folder").forEach(x => { x.textContent = hasDrive() ? S.drive.folder : DEFAULT_FOLDER; });
  if (st === "home") renderHomeStep();
  else if (st === "drive") renderDriveStep();
  else if (st === "pick") renderPickStep();
  else if (st === "field") renderFieldStep();
  else if (st === "planter") renderPlanterStep();  // planter.js
  else renderBuildStep();
  renderPlanterHeader(st);
  $("#bar").hidden = st !== "home";  // the queue bar is only on the landing page; other steps use the Queue button
  if (st === "home") renderBar(st);
  if ($("#downloads").open) renderAllJobs();
  if ($("#drives-pop").open) renderDrivesPop();
  if ($("#preview").open) renderPreviewAction();
  if ($("#qa").open) renderQA();
  if ($("#packages").open) renderPackages();
  if ($("#queue").open) renderQueue();
  updateProgress();
}

// Top-bar Drive pop-up: switch between plugged-in drives quickly; "More" opens step 2.
function renderDrivesPop() {
  if (scanOk() && drives === null && !scanning) loadDrives();
  const cur = (step() === "home" && homeTarget()?.path) || (hasDrive() && S.drive.path);
  const rows = homeDrives().map(d => {
    const on = d.path === cur;
    const info = [d.free != null && fmt(d.free) + " free", d.fstype, d.lastUsed && !d.connected && "last used"].filter(Boolean).join(" · ");
    return `<button type="button" class="drive-opt" data-act="pop-drive" data-path="${esc(d.path)}" aria-pressed="${on}">
      <span class="radio" aria-hidden="true"></span><span class="grow"><b>${esc(d.name)}</b><small class="muted">${esc(info)}</small></span></button>`;
  }).join("");
  let html = rows;
  if (!scanOk()) html += `<div class="pop-consent"><p class="muted small">Commune asks before it looks for USB sticks, SD cards and external drives.</p>
    <button type="button" class="btn small primary" data-act="scan-once">Look for drives</button></div>`;
  else if (scanning) html += `<p class="muted small">Looking for removable drives…</p>`;
  else if (!rows) html = `<p class="muted small">No removable drives found. Plug one in and click Look again, or choose More to use a folder.</p>`;
  if (changed("drivesPop", html)) $("#drives-pop-list").innerHTML = html;
  $("[data-act=pop-rescan]").hidden = !scanOk();
}
// Quick drive switch, opened under the Queue button when a download needs a drive first.
function openDrivesPop() { delete sigs.drivesPop; renderDrivesPop(); openPopup("#drives-pop", $("#queue-btn")); }

function renderHeader(st) {
  const d = S.drive;
  $("#back-btn").hidden = st === "home" && !navDepth();
  const q = cartCount();
  $("#queue-count").textContent = q;
  $("#queue-btn").classList.toggle("has", q > 0);
  $("#queue-btn").setAttribute("aria-label", `Download queue, ${plural(q, "item", "items")}`);
  const need = S.field?.needs || 0;
  $("#field-count").hidden = !need;
  $("#field-count").textContent = need;
  $("#field-btn").setAttribute("aria-label", "Field identification" + (need ? `, ${plural(need, "find needs", "finds need")} identifying` : ""));
  if (st === "field") $("#field-btn").setAttribute("aria-current", "page"); else $("#field-btn").removeAttribute("aria-current");
  if (st === "pick") $("#topics-btn").setAttribute("aria-current", "page"); else $("#topics-btn").removeAttribute("aria-current");
  const done = { home: false, drive: hasDrive(), pick: picked.size + pending.length > 0 || Object.values(S.libraries).some(l => l.file) || S.custom.length > 0, build: false };
  const at = ["pick", "drive", "build"].indexOf(st);
  document.querySelectorAll(".step-arrow").forEach(el => el.classList.toggle("lit", at > ["pick", "drive", "build"].indexOf(el.dataset.after)));
  document.querySelectorAll(".steps a").forEach(a => {
    const s = a.dataset.step;
    if (s === st) a.setAttribute("aria-current", "step"); else a.removeAttribute("aria-current");
    a.classList.toggle("done", s !== st && done[s]);
  });
}

// ------------------------------------------------------------------ step 2: choose a drive
function verdict(d) {
  if (d.kind === "computer") return { warn: true, title: "Not portable", text: "Fine for trying things out, but you can't unplug it and take it with you." };
  if (isFat(d.fstype)) return { warn: true, title: "Can't hold files over 4 GB", text: "Big libraries like Wikipedia and the videos would be blocked. Reformat it as exFAT to use them (this erases the drive)." };
  if (d.free < 2 * GB) return { warn: true, title: "Almost full", text: `Only ${fmt(d.free)} free: room for a few small libraries.` };
  if (d.free < 60 * GB) return { warn: false, title: "Fine for the essentials", text: "Room for the medicine, water, food and skills libraries, but not all of Wikipedia." };
  return { warn: false, title: "Good choice", text: "Works on every computer and has room for big libraries like Wikipedia." };
}

function driveCard(d) {
  const v = verdict(d), sel = d.path === S.drive?.path;
  const used = d.total ? (100 * (1 - d.free / d.total)).toFixed(0) : 0;
  const kind = { external: "External drive", computer: "Your home folder", folder: "Folder" }[d.kind] || "Drive";
  const lib = d.library?.count
    ? `<div class="has-lib">Already has a library on it (${plural(d.library.count, "library", "libraries")}, ${fmt(d.library.size)}). Picking it lets you continue where you left off.</div>` : "";
  return `<button type="button" class="drive-card" data-act="drive" data-path="${esc(d.path)}" aria-pressed="${sel}">
    <div class="top"><span class="radio"></span><div class="grow">
      <span class="name">${esc(d.name)}</span><span class="pill">${esc(d.fstype || "Folder")}</span>
      <div class="sub">${kind} · ${esc(d.path)}</div></div></div>
    <div><div class="meter"><span class="used" style="width:${used}%"></span></div>
      <small class="muted"><b>${fmt(d.free)} free</b> of ${fmt(d.total)}</small></div>
    <div class="verdict ${v.warn ? "warn" : ""}">${v.warn ? ICON.warn : ICON.check}<div><b>${esc(v.title)}</b><small>${esc(v.text)}</small></div></div>
    ${lib}</button>`;
}

const scanOk = () => scanAllowed || S.permissions.scanAlways;
let scanning = false;

function renderConnectBanner() {
  const b = $("#connect-banner"), sd = S.savedDrive;
  b.hidden = !sd || connectDismissed;
  if (b.hidden) return;
  const h = sd.available
    ? `<div class="grow"><b>Connect to “${esc(sd.name)}” again?</b><p class="muted small">Your library was saved there last time. Commune won't open the drive until you say so.</p></div>
       <div class="row-actions"><button type="button" class="btn primary" data-act="connect">Connect</button>
       <button type="button" class="btn" data-act="connect-always">Connect, and don't ask again</button>
       <button type="button" class="btn ghost" data-act="connect-later">Not now</button></div>`
    : `<div class="grow"><b>“${esc(sd.name)}” isn't plugged in</b><p class="muted small">Plug it in to keep working on the library saved there, or choose another drive in step 2.</p></div>
       <div class="row-actions"><button type="button" class="btn" data-act="connect">Try again</button>
       <button type="button" class="btn ghost" data-act="connect-later">Not now</button></div>`;
  if (changed("banner", h)) b.innerHTML = h;
}

const CONSENT = `<div class="consent"><h3>Can Commune look for removable drives?</h3>
  <p class="muted small">Commune checks for external hard drives, USBs, and SD cards that are plugged in. Commune only reads these drives' names, sizes, and free space; your computer's disks are not shown by default; use “Use a folder or another disk”.</p>
  <div class="row-actions"><button type="button" class="btn primary" data-act="scan-once">Yes, look for drives</button>
  <button type="button" class="btn" data-act="scan-always">Yes, and don't ask again</button></div></div>`;

// Step 2 offers two ways to pick where the library goes. The chosen one is highlighted; the other is greyed out but still usable.
let driveMode = store.get("commune.driveMode", null);
function currentMode() {
  if (driveMode) return driveMode;
  if (hasDrive()) return drives?.some(x => x.path === S.drive.path) || (drives === null && scanOk()) ? "scan" : "folder";
  return scanOk() ? "scan" : null;
}
function setDriveMode(m) {
  if (m === currentMode()) return;
  driveMode = m; store.set("commune.driveMode", m); render();
}

// The library folder's name: the one already on the drive, else the package being downloaded, else OfflineLibrary.
const DEFAULT_FOLDER = "OfflineLibrary";
const folderName = n => (n || "").replace(/[<>:"/\\|?*\x00-\x1f]/g, "").trim().replace(/^[.\s]+|[.\s]+$/g, "").slice(0, 60) || DEFAULT_FOLDER;
function queuePackage() {
  if (qPkgs.length !== 1) return null;
  const p = findPkg(qPkgs[0]);
  if (!p) return null;
  const all = [...picked].every(n => p.libraries.includes(n)) && pending.every(x => p.sites.some(y => y.url === x.url));
  return all ? p : null;
}
const libFolder = () => hasDrive() && S.drive.folderExists ? S.drive.folder : folderName(queuePackage()?.name);

function renderDriveStep() {
  if (scanOk() && drives === null && !scanning) loadDrives();
  const d = S.drive, mode = currentMode();
  const onList = hasDrive() && (drives || []).some(x => x.path === d.path);
  const cards = (drives || []).map(driveCard).join("");
  let html = "";
  if (!scanOk()) html = "";
  else if (scanning && drives === null) html = `<p class="empty">Looking for removable drives…</p>`;
  else if (driveError) html = `<p class="empty">${esc(driveError)}</p>` + cards;
  else html = cards || `<p class="empty">No removable drives found. Plug in a USB stick or external drive, then click Look for drives again. To use your computer's own disk, choose “Use a folder or another disk”.</p>`;
  if (changed("drives", html)) $("#drive-list").innerHTML = html;
  const acts = scanOk()
    ? `<button class="btn small" type="button" data-act="rescan" ${scanning ? "disabled" : ""}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></svg><span>${scanning ? "Looking…" : "Look for drives again"}</span></button>`
    : `<button type="button" class="btn primary" data-act="scan-once">Yes, look for drives</button>
       <button type="button" class="btn" data-act="scan-always">Yes, and don't ask again</button>`;
  if (changed("scanActs", acts)) $("#scan-actions").innerHTML = acts;
  const folder = hasDrive() && !onList ? driveCard({ ...d, kind: d.home ? "computer" : "folder", name: d.home ? "This computer" : d.name, library: null }) : "";
  if (changed("folderCard", folder)) $("#folder-card").innerHTML = folder;
  $$(".drive-choose .choice").forEach(c => {
    c.classList.toggle("on", c.dataset.mode === mode);
    c.classList.toggle("off", !!mode && c.dataset.mode !== mode);
    $("input[type=radio]", c).checked = c.dataset.mode === mode;
  });
  const name = libFolder();
  const fnote = hasDrive() && S.drive.folderExists
    ? `Your library goes in the <b>${esc(name)}</b> folder already on this drive. Nothing else on the drive is changed or deleted.`
    : name === DEFAULT_FOLDER
      ? `We add one folder, <b>${DEFAULT_FOLDER}</b> (named after your package instead, if you download one). Nothing else on the drive is changed or deleted.`
      : `We add one folder, <b>${esc(name)}</b>, named after your package. Nothing else on the drive is changed or deleted.`;
  if (changed("folderNote", fnote)) $("#folder-note").innerHTML = fnote;
  const p = S.permissions, auto = [p.scanAlways && "looks for drives", p.autoConnect && "reconnects to your saved drive"].filter(Boolean);
  const note = auto.length ? `Commune ${auto.join(" and ")} without asking. <button type="button" class="link-btn" data-act="reset-perms">Ask me again</button>` : "";
  $("#perm-note").hidden = !note;
  if (changed("permNote", note)) $("#perm-note").innerHTML = note;
  // What to do next, now that the bottom bar is only on the landing page.
  let next = "";
  if (hasDrive()) {
    const n = cartCount();
    if (n) {
      const { sub, over } = cartFit(d);
      next = `<div class="grow"><b>${esc(cartTitle())} → ${esc(d.home ? "this computer" : d.name)}</b><small class="${over ? "over" : "muted"}">${esc(sub)}</small></div>
        <button type="button" class="btn primary big" data-act="go">Download &amp; continue</button>`;
    } else next = `<div class="grow"><b>${esc(d.home ? "This computer" : d.name)} · ${fmt(d.free)} free</b><small class="muted">Your queue is empty. Add topics in step 1, or go on to build the drive.</small></div>
        <a class="btn primary big" href="#build">Next: build &amp; test →</a>`;
  }
  if (changed("driveNext", next)) $("#drive-next").innerHTML = next;
  renderSpace();
}
document.addEventListener("change", e => { if (e.target.name === "drive-mode") setDriveMode(e.target.value); });
document.addEventListener("focusin", e => { const c = e.target.closest?.(".drive-choose .choice.off"); if (c && e.target.type !== "radio") setDriveMode(c.dataset.mode); });

function spaceRow(r, d) {
  const libs = S.libraries;
  const total = r.names.reduce((a, n) => a + libSize(n), 0);
  const need = r.names.filter(n => !libs[n].file);
  const needSize = need.reduce((a, n) => a + libSize(n), 0);
  let mark = "·", cls = "";
  if (d && (total || r.sites)) {
    const ok = needSize <= d.free && !(isFat(d.fstype) && need.some(n => libSize(n) >= 4 * GB));
    mark = ok ? "✓" : "✕"; cls = ok ? "yes" : "no";
  }
  const sites = r.sites ? ` + ${plural(r.sites, "website", "websites")}` : "";
  const size = total ? (r.names.length > 1 ? "about " : "") + fmt(total) + sites : r.sites ? plural(r.sites, "website", "websites") + ", size known after copying" : "size shown once the catalog loads";
  return `<div><span class="mark ${cls}" aria-label="${cls === "yes" ? "Fits" : cls === "no" ? "Doesn't fit" : ""}">${mark}</span>
    <div class="grow">${r.pkg ? `<div class="pkg-tag">Your package</div>` : ""}<b class="small">${esc(r.label)}</b> <span class="muted small">· ${size}</span>
    <div class="muted small">${esc(r.note)}</div>
    ${r.pkg ? (q => `<button type="button" class="btn small add" data-act="pkg-toggle" data-id="${esc(r.pkg)}" aria-pressed="${q}">${q ? "✓ In your queue" : "+ Add"}</button>`)(pkgQueued(r.pkgObj)) : ""}</div></div>`;
}
function renderSpace() {
  const libs = S.libraries, d = hasDrive() ? S.drive : null;
  const recent = S.packages.filter(p => !p.edited).slice(-2).reverse().map(p => ({
    label: p.name, names: p.libraries.filter(n => libs[n]), sites: p.sites.length, pkg: p.id, pkgObj: p,
    note: p.description || `Saved ${p.created}`,
  }));
  const rows = [
    { label: "Essentials", names: ESSENTIALS.filter(n => libs[n]), note: "Medicine, water, food, knots, outdoors, radio, mechanics" },
    ...recent,
    { label: "Everything in the app", names: Object.keys(libs), note: "Every library at its chosen size" },
  ].filter(r => r.names.length || r.sites);
  const html = rows.map(r => spaceRow(r, d)).join("");
  if (changed("space", html)) $("#space-list").innerHTML = html;
  $("#fit-note").textContent = d ? `Checked against ${d.home ? "this computer" : d.name}.` : "Pick a drive to see what fits.";
}

async function loadDrives() {
  if (scanning) return;
  scanning = true; driveError = "";
  render();
  const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 20000);
  try {
    const r = await fetch("/api/drives", { signal: ctl.signal });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    drives = data;
  } catch (e) {
    driveError = e.name === "AbortError"
      ? "Looking for drives took too long. A drive may be busy or failing; unplug it, plug it back in, and try again."
      : `Couldn't look for drives: ${e.message}. Is the builder still running?`;
    drives = drives || [];
  } finally {
    clearTimeout(timer); scanning = false;
  }
  render();
}
$("#drive-form").onsubmit = e => {
  e.preventDefault();
  const p = $("#drive-path").value.trim();
  if (p) { driveMode = "folder"; store.set("commune.driveMode", driveMode); act(() => api("/api/settings", { drive: p }), "Folder selected."); }
};

// ------------------------------------------------------------------ step 1: choose topics
function libRow(n, use) {
  const L = S.libraries[n];
  if (!L) return "";
  const job = activeJob(n), added = picked.has(n), have = L.file && !L.outdated;
  const opt = L.options.find(o => o.flavour === L.flavour);
  const meta = [fmt(have ? L.fileSize : L.size)];
  if (isVideo(n)) meta.push("video");
  if (use[n] > 1) meta.push(`also covers ${plural(use[n] - 1, "other topic", "other topics")}, downloaded once`);
  if (opt?.date) meta.push("updated " + opt.date.slice(0, 7));
  const flav = L.options.length > 1 && !have && !job
    ? `<select data-act="flavour" data-name="${esc(n)}" aria-label="Version of ${esc(L.title)}">${L.options.map(o =>
      `<option value="${esc(o.flavour)}" ${o.flavour === L.flavour ? "selected" : ""}>${esc(FLAVOURS[o.flavour] ?? o.flavour)} · ${fmt(o.size)}</option>`).join("")}</select>` : "";
  let actions;
  if (job) actions = `<span class="pill busy" data-jobtag="${esc(n)}">${job.status === "queued" ? "Waiting" : Math.round(job.progress * 100) + "%"}</span>`;
  else if (have) actions = `${ON_DRIVE}<button type="button" class="btn small ghost danger" data-act="del" data-file="${esc(L.file)}" aria-label="Remove ${esc(L.title)} from the drive">Remove</button>`;
  else if (!L.options.length) actions = `<span class="pill">Not in catalog yet</span>`;
  else {
    // Just a + (add to the queue) or a ✓ (in the queue; click to take it out). "Update" keeps its word.
    const label = added ? ICON.check : L.outdated ? "Update" : ICON.plus;
    const tip = added ? `Remove ${L.title} from the queue` : `Add ${L.title} to the queue`;
    actions = `${L.outdated ? `${ON_DRIVE}<span class="pill warn">Update available</span>` : ""}
    <button type="button" class="btn add ${added || !L.outdated ? "icon-add" : ""}" data-act="pick" data-name="${esc(n)}" aria-pressed="${added}" aria-label="${esc(tip)}" title="${esc(tip)}">${label}</button>`;
  }
  return `<div class="lib ${added ? "added" : ""}">
    <div class="info"><b>${titleLink(siteFor(n), L.title)}</b>${L.summary ? `<div class="desc">${esc(L.summary)}</div>` : ""}
      <div class="meta"><span>${meta.map(esc).join(" · ")}</span>${flav}</div></div>
    <div class="actions">${actions}${L.options.length ? `<button type="button" class="icon-btn eye-btn" data-act="preview-lib" data-name="${esc(n)}" aria-label="Preview ${esc(L.title)}" title="Preview">${ICON.eye}</button>` : ""}</div>
    ${job ? `<div class="bar-line"><span data-jobbar="${esc(n)}" style="width:${job.progress * 100}%"></span></div>` : ""}</div>`;
}

const siteAttrs = s => `data-url="${esc(s.url)}" data-title="${esc(s.title)}" data-topic="${esc(s.topic || "")}" data-pages="${esc(s.pageLimit || "")}"`;
const previewSiteBtn = s => `<button type="button" class="icon-btn eye-btn" data-act="preview-site" ${siteAttrs(s)} aria-label="Preview ${esc(s.title)}" title="Preview">${ICON.eye}</button>`;
const editSiteBtn = (kind, key, title) => `<button type="button" class="icon-btn eye-btn" data-act="edit-site" data-kind="${kind}" data-key="${esc(key)}" aria-label="Edit ${esc(title)}" title="Edit topic or address">${ICON.edit}</button>`;
const titleLink = (url, title) => url ? `<a class="title-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer" title="Open the full website">${esc(title)}</a>` : esc(title);

// The original website a library was made from, so "open the full website" goes somewhere real.
// Libraries with no public website of their own (the zimgit collections) fall back to their online Kiwix copy.
function siteFor(n) {
  const [base, lang] = n.split("_");
  const wm = { wikipedia: "wikipedia.org", wiktionary: "wiktionary.org", wikivoyage: "wikivoyage.org", wikibooks: "wikibooks.org" };
  const known = { wikispecies: "https://species.wikimedia.org", ifixit: "https://www.ifixit.com", appropedia: "https://www.appropedia.org",
    energypedia: "https://energypedia.info", gardenology: "https://www.gardenology.org", mdwiki: "https://mdwiki.org",
    "canadian-prepper": "https://www.youtube.com/@CanadianPrepper" };
  if (wm[base]) return `https://${lang}.${wm[base]}`;
  if (known[base]) return known[base];
  if (base.includes(".")) return "https://" + base;
  return kiwixUrl(n);
}
function kiwixUrl(n) {
  const L = S.libraries[n], opt = L?.options.find(o => o.flavour === L.flavour) || L?.options[0];
  return opt ? "https://browse.library.kiwix.org/viewer#" + opt.url.split("/").pop().replace(/\.zim$/, "") : "";
}

function siteOnDriveRow(c) {
  return `<div class="lib"><div class="info"><b>${titleLink(c.url, c.title)}</b><div class="desc">${esc(host(c.url))}</div><div class="meta">Website you copied</div></div>
    <div class="actions">${ON_DRIVE}<button type="button" class="btn small ghost danger" data-act="del" data-file="${esc(c.file)}" aria-label="Remove ${esc(c.title)} from the drive">Remove</button>${editSiteBtn("drive", c.file, c.title)}${previewSiteBtn(c)}</div></div>`;
}
function crawlRow(j) {
  return `<div class="lib"><div class="info"><b>${esc(j.title || host(j.url))}</b><div class="desc">${esc(host(j.url))}</div>
    <div class="meta" data-jobmsg="${j.id}">${esc(jobDetail(j))}</div></div>
    <div class="actions"><span class="pill busy">${j.status === "queued" ? "Waiting" : "Copying"}</span></div></div>`;
}
function pendingRow(p) {
  return `<div class="lib added"><div class="info"><b>${titleLink(p.url, p.title)}</b><div class="desc">${esc(host(p.url))}</div>
    <div class="meta">Website · copied when you click Download &amp; continue</div></div>
    <div class="actions"><button type="button" class="btn add icon-add" data-act="unpend" data-url="${esc(p.url)}" aria-pressed="true" aria-label="Remove ${esc(p.title)} from the queue" title="Remove from the queue">${ICON.check}</button>${editSiteBtn("pending", p.url, p.title)}${previewSiteBtn(p)}</div></div>`;
}
// A file (PDF, Word, PNG) added to a topic. It's already on the drive; the next build links it from the topic's page.
function fileRow(f) {
  return `<div class="lib"><div class="info"><b><a class="title-link" href="/api/file?name=${encodeURIComponent(f.name)}" target="_blank" rel="noopener" title="Open the file">${esc(f.title)}</a></b>
    <div class="desc">${esc(f.kind || "File")} · ${fmt(f.size)}</div><div class="meta">File you added · on the topic's page after you build</div></div>
    <div class="actions">${ON_DRIVE}<button type="button" class="btn small ghost danger" data-act="del-doc" data-name="${esc(f.name)}" aria-label="Remove ${esc(f.title)} from the drive">Remove</button></div></div>`;
}
const topicFiles = t => (S.files || []).filter(f => sameTopic(f.topic, t.id));

function topicCard(t, use) {
  const pill = topicOnDrive(t) ? `<span class="pill on">On drive</span>` : "";
  const crawls = S.jobs.filter(j => j.kind === "crawl" && liveJob(j) && sameTopic(j.topic, t.id));
  const rows = t.kiwix.map(n => libRow(n, use)).join("")
    + S.custom.filter(c => sameTopic(c.topic, t.id)).map(siteOnDriveRow).join("")
    + topicFiles(t).map(fileRow).join("")
    + crawls.map(crawlRow).join("")
    + pending.filter(p => sameTopic(p.topic, t.id)).map(pendingRow).join("");
  const edit = t.id ? `<button type="button" class="icon-btn eye-btn" data-act="edit-topic" data-id="${esc(t.id)}" aria-label="Edit ${esc(t.title)}" title="Edit this topic">${ICON.edit}</button>` : "";
  return `<article class="topic"><div class="topic-head"><h3>${esc(t.title)}</h3>${pill}${edit}</div>
    ${rows ? `<div class="libs">${rows}</div>` : ""}
    ${t.id ? `<button type="button" class="add-site" data-act="add-site" data-topic="${esc(t.id)}" title="Add a website, PDF, Word document or PNG">${ICON.plus}Add to Topic</button>` : ""}</article>`;
}

// Sidebar: your top 3 packages (favorites first), with Add to queue, and See more for the Packages pop-up.
function renderSidePkgs() {
  const all = allPackages(), favs = favIds();
  const ranked = [...favs.map(findPkg).filter(Boolean), ...all.filter(p => !favs.includes(p.id))];
  const rows = ranked.slice(0, 3).map(p => {
    const inQ = pkgQueued(p);
    return `<div class="side-pkg"><div class="grow"><b>${esc(p.name)}</b><small>${esc(pkgItems(p).split(" plus ")[0])}</small></div>
      ${starBtn(p)}<button type="button" class="btn small" data-act="pkg-toggle" data-id="${esc(p.id)}" aria-pressed="${inQ}">${inQ ? "✓ Added" : "+ Add"}</button></div>`;
  }).join("");
  const html = rows ? `<div class="eyebrow">Packages</div>${rows}${ranked.length > 3 ? `<button type="button" class="link-btn see-more" data-act="side-pkgs-more">See more (${ranked.length - 3})</button>` : ""}` : "";
  if (changed("sidePkgs", html)) $("#side-pkgs").innerHTML = html;
}

function renderPickStep() {
  renderSidePkgs();
  const cats = allCats();
  if (!cats.some(c => c.id === cat)) cat = cats[0]?.id;
  const q = $("#filter").value.trim().toLowerCase();
  const sig = [cat, q, [...picked], pending, S.drive?.path, S.custom, S.catalogLoaded, S.categories,
    Object.entries(S.libraries).map(([k, v]) => [k, v.file, v.flavour, v.options.length, v.outdated]),
    S.jobs.filter(j => (j.library || j.kind === "crawl") && liveJob(j)).map(j => [j.id, j.status]), S.files];
  if (!changed("pick", sig)) return;
  $("#catalog-status").textContent = S.catalogLoaded ? "" : "Catalog not loaded (offline?)";
  $("#cat-list").innerHTML = cats.map(c => {
    const covered = c.topics.filter(topicOnDrive).length;
    return `<button type="button" class="cat-btn" data-act="cat" data-id="${esc(c.id)}" aria-current="${!q && c.id === cat}">
      <b>${esc(c.title)}</b><small>${covered} of ${plural(c.topics.length, "topic", "topics")} on drive</small></button>`;
  }).join("");
  const use = usage();
  if (q) {
    const match = (c, t) => (c.title + " " + t.title + " " + t.kiwix.map(n => S.libraries[n]?.title || "").join(" ")).toLowerCase().includes(q);
    const groups = cats.map(c => ({ c, ts: c.topics.filter(t => match(c, t)) })).filter(g => g.ts.length);
    $("#cat-title").textContent = "Search results";
    $("#topics").innerHTML = groups.map(g => `<h3 class="group-title">${esc(g.c.title)}</h3>` + g.ts.map(t => topicCard(t, use)).join("")).join("")
      || `<p class="empty">No topics or libraries match “${esc(q)}”.</p>`;
  } else {
    const c = cats.find(x => x.id === cat);
    $("#cat-title").textContent = c.title;
    $("#topics").innerHTML = c.topics.map(t => topicCard(t, use)).join("");
  }
}
$("#filter").oninput = () => render();
$("#refresh").onclick = async e => {
  e.target.disabled = true; $("#catalog-status").textContent = "Contacting library.kiwix.org…";
  await act(() => api("/api/resolve", {}), r => `Catalog updated: ${r.resolved} libraries.`);
  e.target.disabled = false;
};

// ------------------------------------------------------------------ quick add
let qaEdit = null;  // null = adding a website; otherwise { kind: "pending" | "drive", url, file } being edited
function fillTopics(selected) {
  $("#qa-topic").innerHTML = S.categories.map(c => `<optgroup label="${esc(c.title)}">${c.topics.map(t =>
    `<option value="${esc(t.id)}">${esc(t.title)}</option>`).join("")}</optgroup>`).join("");
  $("#qa-topic").value = selected;
}
function openQA(topic) {
  const idx = topicIndex();
  qaEdit = null;
  qaCat = topic && idx[topic] ? idx[topic].cat : allCats().find(c => c.id === cat) || S.categories[0];
  fillTopics(topic || qaCat.topics[0]?.id || S.categories[0].topics[0].id);
  const f = $("#qa-form");
  f.url.value = ""; f.url.readOnly = false; f.file.value = "";
  $("#qa-kind").textContent = ""; $("#qa-kind").hidden = true;
  $("#qa-mode-field").hidden = false;
  setQAMode("site");
  $("#qa-close").textContent = "Done";
  $("#qa-status").textContent = "";
  delete sigs.qa;
  renderQA();
  $("#qa").showModal();
}
// Edit a website after adding it: a queued one can change topic and address; one already copied can change topic.
function openEditSite(kind, key) {
  const site = kind === "pending" ? pending.find(p => p.url === key) : S.custom.find(c => c.file === key);
  if (!site) return;
  qaEdit = { kind, url: site.url, file: site.file };
  const idx = topicIndex();
  qaCat = idx[site.topic]?.cat || S.categories[0];
  fillTopics(site.topic || S.categories[0].topics[0].id);
  const f = $("#qa-form");
  f.url.value = site.url; f.url.readOnly = kind === "drive";
  setQAMode("site");
  $("#qa-mode-field").hidden = true;
  $("#qa-url-label").textContent = "2. Website address";
  $("#qa-kind").textContent = "Edit website"; $("#qa-kind").hidden = false;
  $("#qa-submit").textContent = "Save changes";
  $("#qa-close").textContent = "Cancel";
  $("#qa-note").textContent = kind === "drive"
    ? "This website is already copied, so only its topic can change. To use a different address, remove it and add the new one."
    : "Changes apply before the website is copied.";
  $("#qa-status").textContent = "";
  delete sigs.qa;
  renderQA();
  $("#qa").showModal();
}
function renderQA() {
  const topic = $("#qa-topic").value, idx = topicIndex();
  if (!changed("qa", [topic, S.tools.docker, qaEdit])) return;
  $("#qa-title").textContent = qaEdit ? (idx[topic]?.title || "Website") : "New Resource";
  $("#qa-docker").hidden = S.tools.docker !== false || qaEdit?.kind === "drive" || qaMode === "file";
}
// The dialog adds either a website (queued, copied with Docker on download) or a file (copied to the drive now).
let qaMode = "site";
function setQAMode(m) {
  qaMode = m;
  const f = $("#qa-form"), file = m === "file";
  $$("#qa-mode button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mode === m)));
  $("#qa-site-field").hidden = file; $("#qa-file-field").hidden = !file;
  f.url.required = !file; f.file.required = file;
  $("#qa-url-label").textContent = "3. Website address";
  $("#qa-submit").textContent = file ? "+ Add to Topic" : "+ Add to Queue";
  $("#qa-note").textContent = file
    ? "PDF, Word (.doc, .docx) or PNG. It's copied to your drive now, and shows on the topic's page the next time you build the drive."
    : "Copied with Docker when you download. Only copy sites you're allowed to.";
  $("#qa-status").textContent = "";
  delete sigs.qa; if (S) renderQA();
}
$("#qa-mode").onclick = e => { const b = e.target.closest("[data-mode]"); if (b) setQAMode(b.dataset.mode); };
async function uploadFile(form) {
  const file = form.file.files[0], status = $("#qa-status");
  if (!file) { form.reportValidity(); return; }
  if (!/\.(pdf|docx?|png)$/i.test(file.name)) { status.textContent = "Only PDF, Word (.doc, .docx) and PNG files can be added."; return; }
  if (!hasDrive()) { status.textContent = "Choose a drive first (step 2): files are copied straight onto it."; return; }
  const topicName = topicIndex()[form.topic.value]?.title, btn = $("#qa-submit");
  btn.disabled = true; status.textContent = `Copying ${file.name} to the drive…`;
  try {
    const r = await fetch(`/api/upload?topic=${encodeURIComponent(form.topic.value)}&name=${encodeURIComponent(file.name)}`, { method: "POST", body: file });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    status.textContent = `Added ${data.title} to “${topicName}”. Build the drive again to put it on the topic's page.`;
    form.file.value = "";
  } catch (err) { status.textContent = `Couldn't add the file: ${err.message}`; }
  finally { btn.disabled = false; }
  await refresh();
}
function typedSite() {
  const f = $("#qa-form");
  if (!f.reportValidity()) return null;
  const url = f.url.value.trim();
  return { url, title: host(url), topic: f.topic.value, pageLimit: 200 };
}
function togglePending(item) {
  if (pending.some(p => p.url === item.url)) pending = pending.filter(p => p.url !== item.url);
  else pending.push(item);
  save(); render();
}
$("#quick-add").onclick = () => openQA(null);
$("#qa-topic").onchange = () => renderQA();
$("#qa-preview").onclick = () => { const s = typedSite(); if (s) openPreview({ type: "site", ...s }); };
$("#qa-form").onsubmit = async e => {
  e.preventDefault();
  if (qaMode === "file" && !qaEdit) { await uploadFile(e.target); return; }
  const s = typedSite(); if (!s) return;
  const topicName = topicIndex()[s.topic]?.title;
  if (qaEdit?.kind === "drive") {
    try {
      await api("/api/custom/update", { file: qaEdit.file, topic: s.topic });
      notice(`Moved it to “${esc(topicName)}”. Build the drive again to update its home page.`);
      $("#qa").close();
    } catch (err) { $("#qa-status").textContent = err.message; }
    await refresh();
    return;
  }
  if (qaEdit?.kind === "pending") {
    const item = pending.find(p => p.url === qaEdit.url);
    if (!item) { $("#qa").close(); return; }
    if (s.url !== item.url && pending.some(p => p.url === s.url)) { $("#qa-status").textContent = `${s.title} is already in your queue.`; return; }
    const keepTitle = item.title && item.title !== host(item.url) && s.url === item.url;
    Object.assign(item, { url: s.url, topic: s.topic, title: keepTitle ? item.title : s.title });
    save(); render(); $("#qa").close();
    notice(`Saved changes to ${esc(item.title)}.`);
    return;
  }
  if (pending.some(p => p.url === s.url)) { $("#qa-status").textContent = `${s.title} is already added.`; return; }
  pending.push(s); save();
  $("#qa-status").textContent = `Added ${s.title} to “${topicName}”. It's copied when you click Download & continue.`;
  e.target.url.value = "";
  render();
};

// ------------------------------------------------------------------ preview pop-up
// Swaps in a fresh iframe instead of changing its src: navigating an iframe adds browser history entries,
// which would make the Back arrow (and the browser's back button) step through previews instead of pages.
function setPvFrame(url) {
  const old = $("#pv-frame"), f = old.cloneNode(false);
  f.removeAttribute("src");
  if (url) f.src = url;
  old.replaceWith(f);
}
async function openPreview(item) {
  pv = item;
  const msg = $("#pv-msg");
  setPvFrame(""); msg.hidden = true;
  if (item.type === "lib") {
    const L = S.libraries[item.name];
    const opt = L.options.find(o => o.flavour === L.flavour) || L.options[0];
    const book = opt.url.split("/").pop().replace(/\.zim$/, "");
    const url = "https://browse.library.kiwix.org/viewer#" + book;
    $("#pv-kind").textContent = "Offline library preview";
    $("#pv-title").textContent = L.title;
    $("#pv-meta").textContent = `${fmt(opt.size)} download · ${FLAVOURS[opt.flavour] ?? opt.flavour}${opt.date ? " · updated " + opt.date : ""}`;
    $("#pv-url").textContent = "library.kiwix.org · " + book;
    $("#pv-open").href = siteFor(item.name);
    setPvFrame(url);
  } else {
    $("#pv-kind").textContent = "Website preview";
    $("#pv-title").textContent = item.title;
    $("#pv-meta").textContent = [item.pageLimit ? `Copies about ${item.pageLimit} pages` : "", topicIndex()[item.topic]?.title].filter(Boolean).join(" · ");
    $("#pv-url").textContent = item.url;
    $("#pv-open").href = item.url;
    msg.hidden = false; msg.textContent = "Checking whether this site can be shown here…";
  }
  renderPreviewAction();
  if (!$("#preview").open) $("#preview").showModal();
  if (item.type !== "site") return;
  try {
    const r = await api("/api/frameable?url=" + encodeURIComponent(item.url));
    if (pv !== item) return;
    if (r.ok) { msg.hidden = true; setPvFrame(item.url); }
    else msg.innerHTML = `${ICON.warn}<b>This website can't be previewed here</b>
      <p>${esc(r.reason)} You can still look at it in a new tab, and you can still add it to your drive.</p>
      <a class="btn primary big" href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">Open in new tab ↗</a>`;
  } catch (e) { if (pv === item) msg.textContent = e.message; }
}
function renderPreviewAction() {
  if (!pv) return;
  let h;
  if (pv.type === "lib") {
    const n = pv.name, L = S.libraries[n], job = activeJob(n);
    if (job) h = `<span class="pill busy">${job.status === "queued" ? "Waiting to download" : "Downloading"}</span>`;
    else if (L.file && !L.outdated) h = ON_DRIVE;
    else { const a = picked.has(n); h = `<button type="button" class="btn add big" data-act="pick" data-name="${esc(n)}" aria-pressed="${a}">${a ? "✓ Added (click to remove)" : "Add to my drive"}</button>`; }
  } else if (S.custom.some(c => c.url === pv.url)) h = ON_DRIVE;
  else if (!pv.topic) h = `<span class="muted small">Add it from New Topic to pick a topic.</span>`;
  else { const a = pending.some(p => p.url === pv.url); h = `<button type="button" class="btn add big" data-act="pv-site" aria-pressed="${a}">${a ? "✓ Added (click to remove)" : "Add to my drive"}</button>`; }
  if ($("#pv-action").innerHTML !== h) $("#pv-action").innerHTML = h;
}
$("#preview").addEventListener("close", () => { pv = null; setPvFrame(""); });

// ------------------------------------------------------------------ step 3: build & test
function jobDetail(j) {
  if (j.status === "queued") return "Starts when the one above finishes";
  if (j.status === "running") {
    const eta = j.kind === "download" && j.speed > 0 && j.total ? ` · about ${Math.max(1, Math.ceil((j.total - j.done) / j.speed / 60))} min left` : "";
    return j.message + eta;
  }
  if (j.status === "error") return j.message + (j.library ? ". Try again picks up where it stopped." : "");
  if (j.status === "cancelled") return "Not saved";
  return j.message;
}
function jobRow(j) {
  const pill = {
    done: '<span class="pill on">Done</span>', running: `<span class="pill busy" data-jobpct="${j.id}">${Math.round(j.progress * 100)}%</span>`,
    queued: '<span class="pill">Waiting</span>', error: '<span class="pill warn">Stopped</span>', cancelled: '<span class="pill">Cancelled</span>',
  }[j.status] || "";
  const retry = (j.status === "error" || j.status === "cancelled") && (j.library || j.url)
    ? `<button type="button" class="btn small primary" data-act="retry" data-id="${j.id}">Try again</button>` : "";
  const cancel = liveJob(j) ? `<button type="button" class="btn small" data-act="cancel" data-id="${j.id}">Cancel</button>` : "";
  return `<div class="job"><div class="info"><b>${esc(j.label)}</b><small data-jobmsg="${j.id}">${esc(jobDetail(j))}</small></div>${pill}${retry}${cancel}
    ${j.status === "running" ? `<div class="bar-line"><span data-jobbarid="${j.id}" style="width:${j.progress * 100}%"></span></div>` : ""}</div>`;
}
const fileJobs = () => S.jobs.filter(j => j.kind === "download" || j.kind === "crawl");
const buildBusy = () => S.jobs.find(j => j.kind === "build" && liveJob(j));
const isBuilt = () => S.guideBuilt && S.indexBuilt;

function renderBuildStep() {
  const jobs = fileJobs();
  const done = jobs.filter(j => j.status === "done").length;
  $("#dl-summary").textContent = jobs.length ? `${done} of ${jobs.length} finished` : "";
  if (changed("buildJobs", jobs.map(j => [j.id, j.status])))
    $("#build-jobs").innerHTML = jobs.map(jobRow).join("") || `<p class="empty">Nothing downloading. Libraries and websites you add in step 1 show up here.</p>`;

  if (platsDrive !== S.drive.path) {
    plats = new Set(S.tools.platforms.filter(p => p.installed || p.id === S.tools.host).map(p => p.id));
    platsDrive = S.drive.path;
  }
  const platHtml = S.tools.platforms.map(p => {
    const on = p.installed || plats.has(p.id);
    const status = (p.installed ? "Reader on drive" : on ? "Added when you build" : "Not included") + (p.id === S.tools.host ? " · this computer" : "");
    return `<button type="button" class="plat" data-act="plat" data-id="${esc(p.id)}" aria-pressed="${on}" ${p.installed ? "disabled" : ""}>
      <span class="box"></span><span><b>${esc(p.label)}</b><small>${status}</small></span></button>`;
  }).join("");
  if (changed("plats", platHtml)) $("#platforms").innerHTML = platHtml;

  const busy = buildBusy();
  const lastBuild = S.jobs.filter(j => j.kind === "build").pop();
  const libs = plural(S.zimCount, "library or website", "libraries and websites");
  let cls = "", t, s;
  if (busy) { cls = "busy"; t = busy.label.startsWith("Install") ? "Adding reader apps…" : "Building…"; s = `${busy.message}. Don't unplug the drive.`; }
  else if (lastBuild?.status === "error") { cls = "warn"; t = "The last build stopped"; s = lastBuild.message; }
  else if (!isBuilt()) { t = "Not built yet"; s = S.zimCount ? `${libs} on the drive will be included.` : "Nothing is downloaded yet. You can build now to try it out, then build again later."; }
  else if (!S.zimCount && !S.needsRebuild) { t = "Built, but nothing is downloaded yet"; s = "The drive has the quick-reference pages only. Add libraries in step 1, then build again."; }
  else if (S.needsRebuild) { cls = "warn"; t = "Build again to include new downloads"; s = "Something was added or removed since the last build."; }
  else { cls = "ok"; t = "Built and up to date"; s = `${libs} on the home page.`; }
  const box = $("#build-box");
  box.className = "status-box " + cls;
  box.innerHTML = `<b>${esc(t)}</b><small>${esc(s)}</small>`;
  const warn = $("#build-warn");
  warn.hidden = false;
  if (!S.tools.libzim) warn.innerHTML = "The home page can't be built because python-libzim is missing. Run <code>.venv/bin/pip install libzim</code>, then restart.";
  else if (jobs.some(liveJob)) warn.textContent = "Some downloads are still going. You can build now and build again when they finish.";
  else warn.hidden = true;
  const btn = $("#build");
  btn.textContent = busy ? "Building…" : isBuilt() ? "Build again" : "Build drive";
  btn.disabled = !!busy || !S.tools.libzim;

  let h;
  if (!S.indexBuilt) h = `<p class="empty">Build the drive first, then you can test it here.</p>`;
  else if (!S.tools.kiwixServe && !S.serving) h = `<p class="note">This computer's reader isn't on the drive yet. Tick it in part 2, then build again.</p>`;
  else h = `<div class="row-actions"><button type="button" class="btn big ${S.serving ? "" : "primary"}" data-act="serve">${S.serving ? "Stop reader" : "Start reader"}</button>
    ${S.serving ? `<a class="btn big" href="${esc(S.kiwixUrl)}" target="_blank" rel="noopener">Open home page ↗</a><a class="btn big" href="${esc(S.kiwixHome)}" target="_blank" rel="noopener">See all libraries ↗</a>` : ""}</div>
    ${S.serving ? `<p class="serve-ok">The reader is running. Click around and check your libraries open. Stop it before you unplug the drive.</p>` : ""}`;
  if (changed("test", h)) $("#test-area").innerHTML = h;
}
$("#build").onclick = () => {
  const need = S.tools.platforms.filter(p => !p.installed && plats.has(p.id)).map(p => p.id);
  act(async () => {
    if (need.length) await api("/api/tools", { platforms: need });
    return api("/api/build", {});
  }, need.length ? "Adding reader apps, then building the drive…" : "Building the drive…");
};

function renderAllJobs() {
  const jobs = S.jobs.slice().reverse();
  if (changed("allJobs", jobs.map(j => [j.id, j.status])))
    $("#all-jobs").innerHTML = jobs.map(jobRow).join("") || `<p class="empty">No activity yet.</p>`;
}
$("#clear-jobs").onclick = () => act(() => api("/api/clear", {}));

function updateProgress() {
  S.jobs.forEach(j => {
    if (j.status !== "running") return;
    const pct = Math.round(j.progress * 100) + "%";
    if (j.library) {
      document.querySelectorAll(`[data-jobbar="${CSS.escape(j.library)}"]`).forEach(b => { b.style.width = j.progress * 100 + "%"; });
      document.querySelectorAll(`[data-jobtag="${CSS.escape(j.library)}"]`).forEach(b => { b.textContent = pct; });
    }
    document.querySelectorAll(`[data-jobbarid="${j.id}"]`).forEach(b => { b.style.width = j.progress * 100 + "%"; });
    document.querySelectorAll(`[data-jobpct="${j.id}"]`).forEach(b => { b.textContent = pct; });
    document.querySelectorAll(`[data-jobmsg="${j.id}"]`).forEach(b => { b.textContent = jobDetail(j); });
  });
}

// ------------------------------------------------------------------ bottom bar
const cartSize = () => [...picked].reduce((a, n) => a + libSize(n), 0);
const cartCount = () => picked.size + pending.length;
const cartTitle = () => `${plural(cartCount(), "item", "items")} in your queue · ${[picked.size && fmt(cartSize()), pending.length && plural(pending.length, "website", "websites")].filter(Boolean).join(" + ")}`;
// Whether the queue fits on the connected drive, in words.
function cartFit(d) {
  const size = cartSize();
  if (isFat(d.fstype) && [...picked].some(x => libSize(x) >= 4 * GB))
    return { over: true, sub: "This drive can't hold files over 4 GB. Remove the big libraries or pick their Text only version." };
  if (size > d.free) return { over: true, sub: `Too big for this drive. Remove ${fmt(size - d.free)}.` };
  return { over: false, sub: `Fits on this drive. ${fmt(d.free - size)} will be left.${pending.length ? " Website sizes are known after copying." : ""}` };
}

function renderBar(st) {
  let title, sub, acts, over = false;
  const d = S.drive, n = cartCount();
  $("#bar-meter").hidden = !((st === "pick" || st === "home") && hasDrive());
  if (st === "pick" || st === "home") {
    title = n ? cartTitle() : "Your queue is empty";
    if (!n) sub = "Click Add on anything you want to keep, or use New Topic. You choose where to save it next.";
    else if (hasDrive()) ({ sub, over } = cartFit(d));
    else sub = "Next, choose where to save it. You can also create a package from this queue to reuse or share.";
    if (hasDrive()) {
      const usedPct = d.total ? 100 * (1 - d.free / d.total) : 0;
      $("#bar-meter .used").style.width = usedPct.toFixed(1) + "%";
      $("#bar-meter .pick").style.width = Math.min(100 - usedPct, d.total ? 100 * cartSize() / d.total : 0).toFixed(1) + "%";
    }
    acts = n ? `<button type="button" class="btn" data-act="clear">Clear</button><button type="button" class="btn" data-act="save-pkg">+ Create package</button><a class="btn primary big" href="#drive">Choose a drive</a>`
      : `<button type="button" class="btn primary big" disabled title="Add something to your queue first">Choose a drive</button>`;
  } else if (st === "drive") {
    if (!hasDrive()) {
      title = "No drive picked yet";
      sub = n ? `${cartTitle()}. Choose where to save it.` : "Choose where the library will be saved.";
      acts = `<a class="btn big" href="#pick">← Back</a><button type="button" class="btn big" disabled>Pick a drive first</button>`;
    } else if (n) {
      title = `${cartTitle()} → ${d.home ? "this computer" : d.name}`;
      ({ sub, over } = cartFit(d));
      acts = `<a class="btn big" href="#pick">← Back</a><button type="button" class="btn primary big" data-act="go">Download &amp; continue</button>`;
    } else {
      title = `${d.home ? "This computer" : d.name} · ${fmt(d.free)} free`;
      const v = verdict({ ...d, kind: d.home ? "computer" : "external" });
      sub = v.warn ? `Heads up: ${v.title.toLowerCase()}. You can still continue.` : S.zimCount ? "We'll keep the library that's already there." : `We'll add a ${libFolder()} folder to it.`;
      acts = `<a class="btn big" href="#pick">← Back</a><a class="btn primary big" href="#build">Next: build &amp; test →</a>`;
    }
  } else {
    const active = fileJobs().filter(liveJob).length;
    if (!isBuilt()) { title = "Your drive isn't ready yet"; sub = "Build the drive (part 3) to make it usable without internet."; }
    else if (S.needsRebuild) { title = "Almost there: build again"; sub = "New downloads aren't on the home page yet."; }
    else if (!S.zimCount && !active) { title = "Built with the quick-reference pages only"; sub = "Add libraries in step 1 for the full details."; }
    else if (active) { title = "Ready to use, still downloading more"; sub = `${plural(active, "download", "downloads")} still going. Build again when they finish.`; }
    else { title = "Your drive is ready to use"; sub = "Test it, then unplug it safely."; }
    acts = `<a class="btn big" href="#pick">← Back to topics</a>`;
  }
  $("#bar-title").textContent = title;
  $("#bar-sub").textContent = sub;
  $("#bar-sub").classList.toggle("over", over);
  if (changed("barActs", acts)) $("#bar-actions").innerHTML = acts;
}

// Starts downloads for libraries and website copies. Calls done(site) for each website that was queued.
async function queueItems(names, sites, done = () => {}, folder = "") {
  const errors = []; let queued = 0;
  try {
    if (names.length) {
      const r = await api("/api/download", { names, folder });
      queued += r.queued; errors.push(...r.errors);
    }
    for (const p of sites) {
      try {
        await api("/api/crawl", { url: p.url, title: p.title, topic: p.topic, pageLimit: p.pageLimit, folder });
        queued++; done(p);
      } catch (e) { errors.push(`${p.title}: ${e.message}`); }
    }
  } catch (e) { errors.push(e.message); }
  return { queued, errors };
}

async function downloadAndContinue(btn) {
  btn.disabled = true;
  const names = [...picked];
  const folder = queuePackage()?.name || "";
  const { queued, errors } = await queueItems(names, pending.slice(), p => { pending = pending.filter(x => x !== p); }, folder);
  if (names.length) picked.clear();
  save();
  notice(`Started ${plural(queued, "download", "downloads")}.` + (errors.length ? "<br>" + errors.map(esc).join("<br>") : ""), errors.length ? "warn" : "");
  location.hash = "#build";
  await refresh();
}

async function retry(id) {
  const j = S.jobs.find(x => x.id === id); if (!j) return;
  await act(async () => {
    if (j.library) { const r = await api("/api/download", { names: [j.library] }); if (r.errors.length) throw new Error(r.errors[0]); }
    else await api("/api/crawl", { url: j.url, title: j.title, topic: j.topic, pageLimit: j.pageLimit });
  }, "Trying again…");
}

// ------------------------------------------------------------------ packages (saved queues)
let pkgStatus = "";
const pkgSize = p => p.libraries.reduce((a, n) => a + libSize(n), 0);
// Your saved packages plus Commune's starter packs. An edited starter pack is saved under its own id and replaces the original.
function allPackages() {
  const edited = new Map(S.packages.filter(p => p.edited).map(p => [p.id, { ...p, builtin: true }]));
  const builtins = COMMUNE_PACKS.map(p => edited.get(p.id) || { ...p, libraries: p.libraries.filter(n => S.libraries[n]) });
  return [...S.packages.filter(p => !p.edited), ...builtins];
}
const findPkg = id => allPackages().find(p => p.id === id);
const favIds = () => S.favorites ?? COMMUNE_PACKS.map(p => p.id);
const isFav = id => favIds().includes(id);
const starBtn = p => `<button type="button" class="star" data-act="fav" data-id="${esc(p.id)}" aria-pressed="${isFav(p.id)}" aria-label="${isFav(p.id) ? "Remove" : "Add"} “${esc(p.name)}” ${isFav(p.id) ? "from" : "to"} favorites" title="${isFav(p.id) ? "Favorite: shown on the home page" : "Show on the home page"}">${isFav(p.id) ? "★" : "☆"}</button>`;
const pkgInCart = p => p.libraries.every(n => picked.has(n) || !canPick(n)) && p.sites.every(s => pending.some(x => x.url === s.url) || S.custom.some(c => c.url === s.url));
// Whether a package's toggle button shows as on: everything still needed is in the queue (and something is still needed).
const pkgQueued = p => pkgItemsLeft(p) && pkgInCart(p);
function pkgItems(p) {
  const parts = [];
  if (p.libraries.length) parts.push(plural(p.libraries.length, "topic", "topics"));  // a package's libraries are shown as topics
  if (p.sites.length) parts.push(plural(p.sites.length, "website", "websites"));
  return parts.join(" + ") + (p.libraries.length ? ` · ${fmt(pkgSize(p))}` : "") + (p.sites.length ? (p.libraries.length ? " plus website copies" : " · size known after copying") : "");
}
// Whether a package still has anything that could go in the queue (not already on the drive).
const pkgItemsLeft = p => p.libraries.some(n => canPick(n) || picked.has(n)) || p.sites.some(s => !S.custom.some(c => c.url === s.url));
function removePackageFromCart(p) {
  qPkgs = qPkgs.filter(x => x !== p.id);
  // Keep anything another queued package also includes (packages often share libraries).
  const others = qPkgs.map(findPkg).filter(Boolean);
  const keepLib = n => others.some(o => o.libraries.includes(n));
  const keepSite = u => others.some(o => o.sites.some(x => x.url === u));
  p.libraries.forEach(n => { if (!keepLib(n)) picked.delete(n); });
  pending = pending.filter(x => keepSite(x.url) || !p.sites.some(s => s.url === x.url));
  save(); render();
}
async function copyLink(url, btn) {
  try { await navigator.clipboard.writeText(url); }
  catch {
    const t = document.createElement("textarea"); t.value = url; document.body.append(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  const label = $("span", btn); const old = label.textContent;
  label.textContent = "Copied"; setTimeout(() => { label.textContent = old; }, 1600);
}
function addPackageToCart(p) {
  if (!qPkgs.includes(p.id)) qPkgs.push(p.id);
  p.libraries.filter(canPick).forEach(n => picked.add(n));
  p.sites.forEach(s => {
    if (!pending.some(x => x.url === s.url) && !S.custom.some(c => c.url === s.url)) pending.push({ ...s });
  });
  save(); render();
}
function renderPackages() {
  const q = $("#pkg-search").value.trim().toLowerCase();
  const list = [...S.packages.filter(p => !p.edited).reverse(), ...allPackages().filter(p => p.builtin)].filter(p => !q || [p.name, p.description, ...p.libraries.map(n => S.libraries[n]?.title), ...p.sites.map(s => s.title + " " + s.url)]
    .join(" ").toLowerCase().includes(q));
  const html = (pkgStatus ? `<p class="small ok-text">${esc(pkgStatus)}</p>` : "") + (list.map(p => {
    const inQ = pkgQueued(p);
    return `<article class="pkg"><div class="pkg-head"><div class="grow"><span class="kind pkg-kind">Package</span><b>${esc(p.name)}</b>
        <small class="muted">${esc(pkgItems(p).split(" plus ")[0])}${p.builtin ? ` · Commune${p.edited ? ", edited" : ""}` : ""}</small></div>${starBtn(p)}</div>
      ${p.description ? `<p class="desc">${esc(p.description)}</p>` : ""}
      ${insideList("f:" + p.id, p.libraries.filter(n => S.libraries[n]), p.sites, false)}
      <div class="pkg-acts"><button type="button" class="btn small add" data-act="pkg-toggle" data-id="${esc(p.id)}" aria-pressed="${inQ}">${inQ ? "✓ In your queue" : "+ Add to queue"}</button>
      <button type="button" class="btn small" data-act="pkg-edit" data-id="${esc(p.id)}">Edit</button>
      <button type="button" class="btn small" data-act="pkg-export" data-id="${esc(p.id)}">Export</button>
      ${p.builtin ? "" : `<button type="button" class="btn small ghost danger" data-act="pkg-del" data-id="${esc(p.id)}">Delete</button>`}</div></article>`;
  }).join("") || `<p class="empty">${S.packages.length ? `No packages match “${esc(q)}”.` : "No packages yet."}</p>`);
  if (changed("pkgs", html)) $("#pkg-list").innerHTML = html;
}
$("#packages-btn").onclick = () => { pkgStatus = ""; delete sigs.pkgs; renderPackages(); openPopup("#packages", $("#packages-btn")); $("#packages-btn").setAttribute("aria-expanded", "true"); };
$("#packages").addEventListener("close", () => $("#packages-btn").setAttribute("aria-expanded", "false"));
$("#pkg-search").oninput = () => renderPackages();
$("#pkg-import").onclick = () => $("#pkg-file").click();
$("#pkg-file").onchange = async e => {
  const f = e.target.files[0]; e.target.value = "";
  if (!f) return;
  try {
    const data = JSON.parse(await f.text());
    const p = await api("/api/packages/import", { package: data });
    pkgStatus = `Imported “${p.name}”.`;
  } catch (err) { pkgStatus = `Couldn't import that file: ${err instanceof SyntaxError ? "it isn't a package file" : err.message}.`; }
  await refresh(); renderPackages();
};
function exportPackage(p) {
  const data = { communePackage: 1, name: p.name, description: p.description, libraries: p.libraries, sites: p.sites };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  a.download = (p.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "package") + ".commune-package.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function openSavePackage() {
  if (!cartCount()) { notice("Your queue is empty. Add libraries or websites first.", "warn"); return; }
  const f = $("#save-pkg-form");
  f.reset();
  const parts = [];
  if (picked.size) parts.push(`${plural(picked.size, "library", "libraries")} (${fmt(cartSize())})`);
  if (pending.length) parts.push(plural(pending.length, "website", "websites"));
  $("#save-pkg-summary").textContent = `Makes a package of the ${parts.join(" and ")} in your queue. It stays in your queue as one package.`;
  $("#save-pkg").showModal();
  f.elements.name.focus();
}
$("#save-pkg-form").onsubmit = async e => {
  e.preventDefault();
  const f = e.target;
  try {
    const fav = f.elements.favorite.checked;
    const p = await api("/api/packages/save", { name: f.elements.name.value, description: f.elements.description.value, libraries: [...picked], sites: pending });
    // The package is made from the queue, so it goes in the queue as one package.
    if (!qPkgs.includes(p.id)) qPkgs.push(p.id);
    store.set("commune.qpkgs", qPkgs);
    if (fav) await api("/api/favorite", { id: p.id, favorite: true, defaults: COMMUNE_PACKS.map(x => x.id) });
    $("#save-pkg").close();
    notice(`Created “${esc(p.name)}” and added it to your queue.${fav ? " It's in Favorites on the home page." : ""} Find it under Packages (the box icon at the top).`);
  } catch (err) { notice(esc(err.message), "error"); $("#save-pkg").close(); }
  await refresh();
};

// ------------------------------------------------------------------ landing page
let homeDrive = null;     // path picked in the Drive pop-up; landing-page downloads go there

// Drives the Drive pop-up can offer: the connected drive, the last-used drive, and any removable drives found.
function homeDrives() {
  const out = [];
  const add = d => { if (d && !out.some(x => x.path === d.path)) out.push(d); };
  if (hasDrive()) add({ ...S.drive, name: S.drive.home ? "This computer" : S.drive.name, connected: true });
  if (S.savedDrive?.available) add({ path: S.savedDrive.path, name: S.savedDrive.name, lastUsed: true });
  (drives || []).forEach(add);
  return out;
}
const homeTarget = () => homeDrives().find(d => d.path === homeDrive) || null;

// What a package still needs on the chosen drive, and whether it fits.
function homeFit(p, d) {
  const onThis = d && S.drive && d.path === S.drive.path && !S.drive.missing;
  const libs = p.libraries.filter(n => S.libraries[n]);
  const need = onThis ? libs.filter(canPick) : libs;
  const sites = onThis ? p.sites.filter(s => !S.custom.some(c => c.url === s.url)) : p.sites;
  const busy = onThis && libs.some(n => activeJob(n));
  const size = need.reduce((a, n) => a + libSize(n), 0);
  let fit = null;
  if (d && d.free != null && need.length) {
    if (isFat(d.fstype) && need.some(n => libSize(n) >= 4 * GB)) fit = { ok: false, text: "Has files over 4 GB, which this drive can't hold" };
    else if (size > d.free) fit = { ok: false, text: `Needs ${fmt(size - d.free)} more space on this drive` };
    else fit = { ok: true, text: `Fits · ${fmt(d.free - size)} left after` };
  }
  return { need, sites, busy, done: onThis && !need.length && !sites.length && !busy, fit, size };
}

function favCard(p, d) {
  const f = homeFit(p, d);
  const names = [...p.libraries.map(n => S.libraries[n]?.title || n), ...p.sites.map(s => s.title)];
  let action;
  if (f.done) action = ON_DRIVE;
  else if (f.busy && !f.need.length && !f.sites.length) action = `<a class="btn" href="#build">Downloading… see progress</a>`;
  else action = `<button type="button" class="btn primary big" data-act="home-dl" data-id="${esc(p.id)}" ${f.fit && !f.fit.ok ? "disabled" : ""}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>Download${d ? ` to ${esc(d.name)}` : ""}</button>`;
  const inQ = pkgQueued(p);
  const addBtn = f.done ? "" : `<button type="button" class="btn add" data-act="pkg-toggle" data-id="${esc(p.id)}" aria-pressed="${inQ}">${inQ ? "✓ Added" : "+ Add to queue"}</button>`;
  return `<article class="fav-card">${starBtn(p)}
    <h3>${esc(p.name)}</h3>
    <p class="meta">${esc(pkgItems(p).split(" plus ")[0])}${f.fit && !f.done ? ` · <span class="fit ${f.fit.ok ? "" : "no"}">${esc(f.fit.text)}</span>` : ""}</p>
    ${p.description ? `<p class="desc">${esc(p.description)}</p>` : ""}
    <ul class="items">${names.map(n => `<li>${esc(n)}</li>`).join("")}</ul>
    <div class="fav-actions">${action}<button type="button" class="icon-btn" data-act="pkg-edit" data-id="${esc(p.id)}" aria-label="Edit ${esc(p.name)}" title="Edit">${ICON.edit}</button></div>
    ${addBtn}</article>`;
}

function renderHomeStep() {
  if (scanOk() && drives === null && !scanning) loadDrives();
  const list = homeDrives();
  if (homeDrive && !list.some(d => d.path === homeDrive)) homeDrive = null;
  if (!homeDrive && hasDrive()) homeDrive = S.drive.path;
  const d = homeTarget();
  let note = "";
  if (scanning) note = "Looking for removable drives…";
  else if (driveError) note = driveError;
  else if (!d) note = "No drive chosen yet. Click Choose Drive… above to pick one.";
  else if (d && d.free != null) {
    const v = verdict({ ...d, kind: d.home ? "computer" : "external" });
    if (v.warn) note = `Heads up: ${v.title.toLowerCase()}. ${v.text}`;
  }
  $("#home-drive-note").textContent = note;
  $("#fav-hint").textContent = d ? `Download in one click to ${d.name}.` : "Download in one click once you've chosen a drive.";

  const favs = favIds().map(findPkg).filter(Boolean);
  const html = favs.map(p => favCard(p, d)).join("")
    || `<p class="empty">No favorites yet. Open <b>See all packages</b> and tap ☆ on the ones you want here.</p>`;
  if (changed("favs", html)) $("#fav-list").innerHTML = html;

  const idCat = S.categories.find(x => /identif/i.test(x.title));
  const F = S.field;
  const stats = !F?.uploads ? "No uploads from the field identifier yet."
    : `${plural(F.identified, "find", "finds")} identified · ${F.needs} need identifying · last upload ${when(F.last)}`;
  $("#fid-stats").textContent = stats;
  const fid = `<a class="btn primary big" href="#field">Open field identification${F?.needs ? ` (${F.needs} to check)` : ""}</a>`
    + (idCat ? `<button type="button" class="btn big" data-act="goto-cat" data-id="${esc(idCat.id)}">Browse identification libraries</button>` : "");
  if (changed("fid", fid)) $("#fid-actions").innerHTML = fid;
  renderPlanterHome();  // planter.js
}

async function homeDownload(id, btn) {
  const p = findPkg(id);
  const d = homeTarget();
  if (!p) return;
  if (!d) {
    notice("Choose a drive first.", "warn");
    openDrivesPop();
    return;
  }
  btn.disabled = true;
  try {
    if (!hasDrive() || S.drive.path !== d.path) await api("/api/settings", { drive: d.path });
    await refresh();
    const f = homeFit(p, homeTarget() || d);
    if (f.fit && !f.fit.ok) { notice(esc(f.fit.text) + ".", "warn"); return; }
    if (!f.need.length && !f.sites.length) { notice(`Everything in “${esc(p.name)}” is already on ${esc(d.name)}.`); return; }
    const { queued, errors } = await queueItems(f.need, f.sites, undefined, p.name);
    notice(`Downloading “${esc(p.name)}” to ${esc(d.name)}: started ${plural(queued, "download", "downloads")}. When they finish, build the drive below.`
      + (errors.length ? "<br>" + errors.map(esc).join("<br>") : ""), errors.length ? "warn" : "");
    location.hash = "#build";
  } catch (e) { notice(esc(e.message), "error"); }
  finally { btn.disabled = false; }
  await refresh();
}

// ------------------------------------------------------------------ field identification
// Finds from the Commune field identifier. Each upload (everything scanned since the last one) is listed on its own,
// split into Identified and Needs identification (the device wasn't sure enough). The journal lives on the drive.
//
// What each identifier records, in the order shown: [key in the find's "details", label]. Anything else the device
// sends is shown after these under its own name. "badges" are short facts shown up top as coloured tags; "purposes" are
// what a find can be good for (the device lists them in details.purposes and the card shows them as "Good for").
const FIELD_CATS = {
  plant: { label: "Plant", plural: "Plants and fungi", badges: ["edibility", "edibleAs", "poisonous", "compost"], purposes: [], fields: [
    ["edibility", "Edible?"], ["edibleAs", "Eat it as (spice, fruit, veggie, leaf, foliage, tree)"], ["poisonous", "Poisonous properties"],
    ["lookalikes", "Dangerous look-alikes"],
    ["medicinal", "Medicinal properties"], ["nutrition", "Nutritional value"], ["watering", "Watering"], ["sunlight", "Sunlight"],
    ["sunDirection", "Sun direction"], ["climate", "Best climate and time of year"], ["fertilizers", "Natural fertilizers"],
    ["pests", "Pests"], ["compost", "Compost friendly?"], ["planting", "How to plant and grow it abundantly"],
    ["growthTime", "Expected growth time"], ["seeds", "How to extract seeds"]] },
  animal: { label: "Animal or bug", plural: "Animals and bugs", badges: ["danger", "touch", "feed", "pestToPlants"],
    purposes: ["Eating", "Medicinal", "Building material", "Pest control", "Learning", "Survival", "Useful resource", "Clothing"], fields: [
    ["danger", "Danger level to humans"], ["description", "Description"], ["defenses", "Attack and defense mechanisms"],
    ["touch", "Should you touch it?"], ["feed", "Should you feed it?"], ["pestToPlants", "Pest to your plants?"], ["pestOf", "Plants it's a pest to"],
    ["deterrents", "Deterrents"], ["attractants", "Food it likes (to bring more)"], ["edibility", "Edible?"],
    ["pros", "Pros of it being around"], ["cons", "Cons of it being around"], ["cause", "Why it's around"], ["conditions", "Conditions it's found in"]] },
  language: { label: "Language", plural: "Languages", badges: ["language", "worldShare"], purposes: ["Understanding", "Communication"], fields: [
    ["language", "Language"], ["script", "Script"], ["historyOfText", "History behind the text"], ["historyOfLanguage", "History of the language"],
    ["cultures", "Cultures that speak it"], ["countries", "Countries that speak it"], ["worldShare", "Share of the world who speaks it"],
    ["context", "Where it was seen"]] },
  hardware: { label: "Hardware", plural: "Hardware", badges: ["version", "released"], purposes: ["Plumbing", "Electrical", "Comfort", "Communications"], fields: [
    ["whatIsIt", "What it is"], ["function", "What it does"], ["released", "Released"], ["version", "Version"], ["commonUses", "Common uses"],
    ["specs", "Specs"], ["connectors", "Connectors"], ["lifespan", "Average lifespan"], ["components", "Components (hardware dictionary)"],
    ["pairedSoftware", "Commonly paired software"], ["softwareRequired", "Software required"], ["hardwareRequired", "Other hardware required"],
    ["maintenance", "Maintenance suggestions"], ["hazards", "Hazards"]] },
  software: { label: "Software", plural: "Software", badges: ["genre", "version", "subscription"], purposes: [], fields: [
    ["genre", "Type or genre"], ["creator", "Creator"], ["released", "Release date"], ["version", "Version"], ["commonUses", "Common uses"],
    ["history", "History"], ["pros", "Pros"], ["cons", "Cons"], ["hardwareRequired", "Hardware required"], ["pairedHardware", "Commonly paired hardware"],
    ["subscription", "Subscription required?"], ["security", "Security recommendations"], ["github", "GitHub"]] },
  firstaid: { label: "First aid", plural: "First aid", badges: ["type", "otc"],
    purposes: ["Mitigating further damage", "Preventing ailments", "Wound healing", "First response", "Emergency response"], fields: [
    ["type", "Item or injury"], ["description", "What it is"], ["howToApply", "How to apply"],
    ["otc", "Over the counter, or a medical professional?"], ["naturalRemedies", "Natural remedies"], ["related", "Related items and injuries"],
    ["manualYear", "First aid manual used (release year)"]],
    caution: "A quick reference, not a medical professional. In an emergency, get help first." },
  other: { label: "Other", plural: "Other finds", badges: [], purposes: [], fields: [] },
};
// The plant and fungus identifier: a fungus is labelled as one, with the same facts as a plant.
FIELD_CATS.fungus = { ...FIELD_CATS.plant, label: "Fungus" };
FIELD_CATS.hardware.badges.push("hazards");
const CAT_ALIAS = { component: "hardware" };  // finds imported before Tech was split into hardware and software
const FILTER_OF = { fungus: "plant" };         // plants and fungi share one filter
// Shown in their own boxes instead of the facts list.
const LANG_KEYS = ["text", "translation", "pronunciation", "languageCode", "translationLanguage", "countryShare"];
const KEEP_KEYS = [["preserveFrozen", "Frozen"], ["preserveFridge", "In the fridge"], ["preserveOut", "Left out"]];
const BOX_KEYS = ["purposes", ...KEEP_KEYS.map(k => k[0])];
// Where a find was looked up, grouped by the kind of source.
const SOURCE_KINDS = { knowledge: "Your knowledge base", article: "Looked up in", dictionary: "Dictionary entries", image: "Pictures", manual: "First aid manual",
  video: "Beginner videos", lesson: "Beginner lessons" };
const LANG_CODES = { english: "en", spanish: "es", french: "fr", chinese: "zh", mandarin: "zh", german: "de", italian: "it", portuguese: "pt",
  russian: "ru", arabic: "ar", japanese: "ja", korean: "ko", hindi: "hi", vietnamese: "vi", tagalog: "tl", dutch: "nl", polish: "pl", turkish: "tr" };
// Tag colours: "not poisonous" is safe, then any danger word wins ("Low; can be aggressive" warns), then safe words.
const NOT_BAD = /^(not|non-?)\s*(poisonous|toxic|venomous|aggressive|dangerous|invasive)\b|^no hazards?\b|^none\b/i;
const DANGER = /deadly|fatal|lethal|poison|toxic|venom|aggressive|dangerous|danger|invasive|high voltage|not edible|inedible|do not|don't|hazard|charged|asbestos|unknown|professional|doctor|prescription|emergency/i;
const SAFE = /^(yes\b|edible|safe|friendly|docile|harmless|gentle|shy|native|low\b|over the counter|otc\b)/i;
const YES_IS_BAD = new Set(["subscription", "pestToPlants"]), NO_IS_BAD = new Set(["touch", "feed", "compost", "edibility"]);
const ICON_SOUND = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zM16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/></svg>';
const ICON_BOOK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M8 7h7"/></svg>';
const canSpeak = "speechSynthesis" in window;

let field = null, fieldRev = null, fieldLoading = false, fieldErr = "", fieldLocal = 0;
let fieldUpload = store.get("commune.fieldUpload", "all");  // which upload is shown ("all" for every one)
let fieldTab = store.get("commune.fieldTab", "identified");  // "identified" or "needs"
let fieldCat = "all", fieldQuery = "";
const fieldOpen = new Set();  // finds shown in full, by "upload/find" (the rest are condensed)
const noteDrafts = new Map(), noteTimers = {};               // notes typed but not saved yet, by "upload/find"

const when = s => { if (!s) return ""; const d = new Date(s); return isNaN(d) ? String(s) : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" }); };
const place = l => !l ? "" : l.label || (l.lat != null && l.lon != null ? `${(+l.lat).toFixed(4)}, ${(+l.lon).toFixed(4)}` : "");
const hasVal = v => v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && !v.length) && !(typeof v === "object" && !Array.isArray(v) && !Object.keys(v).length);
const valText = (v, k = "") => Array.isArray(v) ? v.join(", ") : v === true ? "Yes" : v === false ? "No"
  : typeof v === "object" ? Object.entries(v).map(([a, b]) => `${a}: ${valText(b, k)}`).join(", ")
  : typeof v === "number" && /share|percent/i.test(k) ? `${+v.toFixed(2)}%` : String(v);
const humanize = k => k.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
function tone(v, key) {
  const t = valText(v);
  if (YES_IS_BAD.has(key)) return /^(yes|true|required)\b/i.test(t) ? "danger" : /^(no|none|free)\b/i.test(t) ? "ok" : "";
  if (NO_IS_BAD.has(key) && /^no\b/i.test(t)) return "danger";
  return NOT_BAD.test(t) ? "ok" : DANGER.test(t) || key === "hazards" ? "danger" : SAFE.test(t) ? "ok" : "";
}
const catOf = e => CAT_ALIAS[e.category] || e.category;
let fieldCountry = store.get("commune.fieldCountry", "");  // the country picked for "who speaks it" (same on every card)
const isNeeds = e => e.status !== "identified";
const fieldMedia = (u, name) => `/api/field/media?upload=${encodeURIComponent(u.id)}&name=${encodeURIComponent(name)}`;
const findLocal = (uid, eid) => field?.uploads.find(u => u.id === uid)?.entries.find(e => e.id === eid);

async function loadField() {
  fieldLoading = true;
  const rev = S.field?.rev;
  try { field = await api("/api/field"); fieldErr = ""; field.uploads.forEach(u => u.entries.forEach(e => { e.category = catOf(e); })); }
  catch (e) { fieldErr = e.message; }
  finally { fieldLoading = false; fieldRev = rev; }
  render();
}

function langCode(d) {
  const raw = String(d.languageCode || "").trim().toLowerCase();
  if (raw) return raw;
  const name = String(d.language || "").trim().toLowerCase();
  return LANG_CODES[name] || (/^[a-z]{2,3}(-[a-z0-9]+)?$/.test(name) ? name : "");
}
// The dictionary for a language: a link if it's on the drive, else a button to add it to the queue.
function dictionaryLink(code, word) {
  const base = code.split("-")[0], n = `wiktionary_${base}_all`, L = S.libraries[n];
  if (!base) return "";
  if (!L) return `<p class="muted small">Commune doesn't have a dictionary for this language yet.</p>`;
  if (L.file) {
    const book = L.file.replace(/\.zim$/, "");
    const open = `<a class="btn small" href="${esc(S.kiwixHome + "content/" + encodeURIComponent(book) + "/")}" target="_blank" rel="noopener">${ICON_BOOK}Open the ${esc(L.title)}</a>`;
    const look = word && word.split(/\s+/).length <= 3
      ? `<a class="btn small" href="${esc(S.kiwixHome + "search?content=" + encodeURIComponent(book) + "&pattern=" + encodeURIComponent(word))}" target="_blank" rel="noopener">Look up “${esc(word)}”</a>` : "";
    return `<div class="row-actions">${open}${look}</div>` + (S.serving ? "" : `<p class="muted small">The dictionary is on your drive. Start the reader in <a href="#build">step 3</a> to open it.</p>`);
  }
  const q = picked.has(n);
  return `<div class="row-actions"><span class="muted small">The ${esc(L.title)} isn't on this drive.</span>
    <button type="button" class="btn small add" data-act="pick" data-name="${esc(n)}" aria-pressed="${q}">${q ? "✓ In your queue" : "+ Add dictionary to queue"}</button></div>`;
}
// A link into a library on the drive (opens in the reader started in step 3), or null if it isn't on the drive.
function libHref(lib, path) {
  const L = S.libraries[lib];
  if (!L?.file) return null;
  return S.kiwixHome + "content/" + encodeURIComponent(L.file.replace(/\.zim$/, "")) + "/" + (path || "").split("/").map(encodeURIComponent).join("/");
}
const readerNote = () => S.serving ? "" : `<p class="muted small">Start the reader in <a href="#build">step 3</a> to open these.</p>`;
function langBlock(u, e) {
  const d = e.details || {}, code = langCode(d), to = String(d.translationLanguage || "en"), key = u.id + "/" + e.id;
  const say = (text, lang, label) => text && canSpeak
    ? `<button type="button" class="btn small" data-act="field-say" data-text="${esc(text)}" data-lang="${esc(lang)}">${ICON_SOUND}${label}</button>` : "";
  const clip = (name, label) => name ? `<span class="clip"><small class="muted">${label}</small><audio controls preload="none" src="${esc(fieldMedia(u, name))}"></audio></span>` : "";
  // Share of a chosen country who speaks it: the device sends {country: percent}; the picked country is remembered.
  const share = d.countryShare && typeof d.countryShare === "object" && !Array.isArray(d.countryShare) ? Object.entries(d.countryShare) : [];
  const pick = share.find(([c]) => c === fieldCountry) || share[0];
  const countries = share.length ? `<div class="country-share"><label class="inline-label">Who speaks it in
      <select data-country="${esc(key)}">${share.map(([c]) => `<option value="${esc(c)}" ${pick && c === pick[0] ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
      <b data-country-out="${esc(key)}">${esc(valText(pick[1], "share"))}</b></div>` : "";
  return `<div class="lang-box">
    ${hasVal(d.text) ? `<div><small class="muted">What it says</small><blockquote lang="${esc(code)}">${esc(valText(d.text))}</blockquote></div>` : ""}
    ${hasVal(d.pronunciation) ? `<div><small class="muted">Say it like</small><p>${esc(valText(d.pronunciation))}</p></div>` : ""}
    ${hasVal(d.translation) ? `<div><small class="muted">Translation</small><p class="translation">${esc(valText(d.translation))}</p></div>` : ""}
    <div class="row-actions">${say(valText(d.text || ""), code, "Hear it")}${e.translationAudio ? "" : say(valText(d.translation || ""), to, "Hear translation")}
      ${clip(e.audio, "Recording")}${clip(e.translationAudio, "Spoken translation")}</div>
    ${countries}
    ${dictionaryLink(code, hasVal(d.text) ? valText(d.text).trim() : "")}</div>`;
}
// "Source: <website>" for every resource: the web page its information comes from (filled in by Commune when the
// device only named a library). Opens on the internet, unlike the library links, which open offline in the reader.
function siteText(url) {
  try { const x = new URL(url); const t = x.hostname.replace(/^www\./, "") + decodeURIComponent(x.pathname).replace(/\/$/, "");
    return t.length > 70 ? t.slice(0, 67) + "…" : t; } catch { return url; }
}
const sourceSite = url => url
  ? `<span class="source-site">Source: <a href="${esc(url)}" target="_blank" rel="noopener noreferrer" title="${esc(url)}">${esc(siteText(url))}</a></span>`
  : `<span class="source-site muted">Source website not given</span>`;
// Summaries are quotes only: word for word from the drive's libraries, each with where it came from.
function quotesBlock(e) {
  if (!e.quotes?.length) return "";
  return `<div class="find-quotes">${e.quotes.map(q => {
    const L = S.libraries[q.library], href = q.library && libHref(q.library, q.path);
    const name = esc(q.title || L?.title || q.library);
    const cite = !q.library ? `<span class="muted">Source not given</span>`
      : href ? `<a href="${esc(href)}" target="_blank" rel="noopener">${name}</a>${L && q.title ? ` · ${esc(L.title)}` : ""}`
      : `${name} <span class="muted">· ${esc(L ? L.title + ", not on this drive" : q.library)}</span>`;
    return `<figure><blockquote>${esc(q.text)}</blockquote><figcaption>— ${cite}${sourceSite(q.url)}</figcaption></figure>`;
  }).join("")}</div>`;
}
function sourcesBlock(e) {
  if (!e.sources?.length) return "";
  const groups = Object.keys(SOURCE_KINDS).map(kind => [kind, e.sources.filter(s => (s.kind || "article") === kind)]).filter(([, l]) => l.length);
  const item = s => {
    if (s.kind === "knowledge") {  // one of your own earlier identifications; path is "upload/find"
      const [ku, ke] = String(s.path || "").split("/"), k = findLocal(ku, ke);
      return `<li>${k ? `<button type="button" class="link-btn" data-act="field-goto" data-key="${esc(s.path)}">${esc(s.title || k.name)}</button>` : esc(s.title || "Your earlier find")} <small class="muted">Your earlier find</small>${sourceSite(s.url)}</li>`;
    }
    const L = S.libraries[s.library], label = esc(s.title || L?.title || s.library), href = libHref(s.library, s.path);
    if (!s.library) return `<li>${label || esc(siteText(s.url))}${sourceSite(s.url)}</li>`;  // a website not in any library
    return href ? `<li><a href="${esc(href)}" target="_blank" rel="noopener" title="Open on this drive">${label}</a> <small class="muted">${esc(L.title)}</small>${sourceSite(s.url)}</li>`
      : `<li>${label} <small class="muted">${esc(L ? L.title + " · not on this drive" : s.library)}</small>${sourceSite(s.url)}</li>`;
  };
  return `<div class="find-sources">${groups.map(([kind, l]) => `<div><small class="muted">${SOURCE_KINDS[kind]}</small><ul>${l.map(item).join("")}</ul></div>`).join("")}
    ${e.sources.some(s => libHref(s.library)) ? readerNote() : ""}</div>`;
}
// How long an edible animal keeps: frozen, in the fridge, left out.
function keepsBlock(d) {
  const rows = KEEP_KEYS.filter(([k]) => hasVal(d[k]));
  if (!rows.length) return "";
  return `<div class="keeps"><small class="muted">If you eat it, it keeps</small><div>${rows.map(([k, l]) => `<span><small>${l}</small>${esc(valText(d[k]))}</span>`).join("")}</div></div>`;
}
function purposesBlock(d) {
  const p = Array.isArray(d.purposes) ? d.purposes : hasVal(d.purposes) ? [valText(d.purposes)] : [];
  return p.length ? `<div class="purposes"><small class="muted">Good for</small>${p.map(x => `<span class="purpose">${esc(x)}</span>`).join("")}</div>` : "";
}
function factsList(C, d, cat) {
  const known = new Set(C.fields.map(f => f[0]));
  // Short facts are already tags at the top; only long ones are repeated here in full.
  const skip = new Set([...(cat === "language" ? LANG_KEYS : []), ...BOX_KEYS, ...C.badges.filter(k => valText(d[k] ?? "", k).length <= 60)]);
  const rows = [...C.fields.filter(([k]) => hasVal(d[k]) && !skip.has(k)), ...Object.keys(d).filter(k => !known.has(k) && !skip.has(k) && hasVal(d[k])).map(k => [k, humanize(k)])];
  if (!rows.length) return "";
  return `<dl class="find-facts">${rows.map(([k, label]) => {
    const v = d[k], t = C.badges.includes(k) || k === "hazards" ? tone(v, k) : "";
    const link = typeof v === "string" && /^https?:\/\/\S+$/.test(v.trim());
    const val = link ? `<a href="${esc(v.trim())}" target="_blank" rel="noopener noreferrer">${esc(v.trim())}</a>`
      : Array.isArray(v) && v.length > 1 ? `<ul>${v.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : esc(valText(v, k));
    return `<div class="${t}"><dt>${esc(label)}</dt><dd>${val}</dd></div>`;
  }).join("")}</dl>`;
}
// ---- your own identifications: marked identifiedBy "user", always with a source, and kept in the knowledge base
const CITE_TYPES = [["website", "Website"], ["book", "Book"], ["field-guide", "Field guide"], ["expert", "Expert or person"],
  ["library", "Library on this drive"], ["other", "Other"]];
const isMine = e => e.identifiedBy === "user" || (!!e.confirmed && e.status === "identified");
const confirmDrafts = new Map();  // what's typed in a find's "Identify it" form, kept across redraws, by "upload/find"
let KNOWN = new Map();            // lower-case name -> finds you identified yourself (rebuilt on each redraw)
function knownIndex() {
  const m = new Map();
  field.uploads.forEach(u => u.entries.forEach(e => {
    if (!isNeeds(e) && isMine(e) && e.name) { const k = e.name.toLowerCase(); if (!m.has(k)) m.set(k, []); m.get(k).push({ u, e }); }
  }));
  return m;
}
const gotoBtn = (u, e, label) => `<button type="button" class="link-btn" data-act="field-goto" data-key="${esc(u.id + "/" + e.id)}">${label}</button>`;
function citeText(c) {
  if (!c) return "";
  const kind = (CITE_TYPES.find(t => t[0] === c.type) || [, "Source"])[1];
  const url = c.url || [c.detail, c.title].find(x => /^https?:\/\/\S+$/.test(x || "")) || "";
  const detail = c.detail && c.detail !== url ? ` · ${esc(c.detail)}` : "";
  return `<span class="kind">${esc(kind)}</span> ${esc(c.title === url ? siteText(url) : c.title)}${detail}${c.type === "expert" && !url ? "" : sourceSite(url)}`;
}
function confirmBlock(u, e) {
  const key = u.id + "/" + e.id, ids = `data-upload="${esc(u.id)}" data-entry="${esc(e.id)}" data-key="${esc(key)}"`;
  const g = e.deviceGuess;
  const guess = g && g.name && g.name !== e.name ? `<span class="muted small">The device guessed ${esc(g.name)}${g.confidence != null ? ` (${Math.round(g.confidence * 100)}% sure)` : ""}.</span>` : "";
  if (!isNeeds(e)) {
    const back = `<button type="button" class="link-btn" data-act="field-unconfirm" ${ids}>Not right? Move it back to Needs identification</button>`;
    if (!isMine(e)) return `<div class="find-confirmed">${back}</div>`;
    return `<div class="find-mine"><div><span class="pill mine">Identified by you</span> <span class="muted small">${esc(when(e.confirmed))} · in your knowledge base</span></div>
      ${e.citation ? `<p class="small">Your source: ${citeText(e.citation)}</p>` : `<p class="small warn-text">No source was saved for this one.</p>`}
      <div class="find-confirmed">${guess}${back}</div></div>`;
  }
  const draft = confirmDrafts.get(key) || {};
  // A find moved back here keeps its name as the first choice.
  const list = (e.candidates || []).slice();
  if (e.name && !list.some(c => c.name === e.name)) list.unshift({ name: e.name, scientific: e.scientific, confidence: null });
  const cands = list.map(c => {
    const known = KNOWN.get(c.name.toLowerCase());
    return `<button type="button" class="cand" data-act="field-pick" data-key="${esc(key)}" data-name="${esc(c.name)}" data-sci="${esc(c.scientific || "")}" aria-pressed="${draft.name === c.name}">
      <span class="grow"><b>${esc(c.name)}</b>${c.scientific ? ` <i>${esc(c.scientific)}</i>` : ""}${known ? `<span class="known">You've identified this before</span>` : ""}</span>
      ${c.confidence != null ? `<small class="muted">${Math.round(c.confidence * 100)}%</small>` : ""}<span class="cand-go">${draft.name === c.name ? "✓ Picked" : "This is it"}</span></button>`;
  }).join("");
  // Finds you identified before that match one of the device's guesses: open them to compare.
  const seen = list.flatMap(c => (KNOWN.get(c.name.toLowerCase()) || []).map(k => ({ ...k, c })));
  const compare = seen.length ? `<div class="known-list small">Compare with your earlier finds: ${seen.slice(0, 4).map(k => gotoBtn(k.u, k.e, `${esc(k.e.name)} (${esc(when(k.e.captured || k.e.confirmed))})`)).join(", ")}</div>` : "";
  const opt = CITE_TYPES.map(([v, l]) => `<option value="${v}" ${(draft.ctype || "website") === v ? "selected" : ""}>${l}</option>`).join("");
  return `<div class="find-needs">
    ${cands ? `<small class="muted">The device thinks it might be one of these. Pick the right one, or type your own answer:</small><div class="cands">${cands}</div>${compare}`
      : `<small class="muted">The device couldn't tell what this is. Type what it is:</small>`}
    <form class="find-confirm" ${ids} novalidate>
      <label>What is it?<input name="name" maxlength="160" value="${esc(draft.name || "")}" placeholder="${cands ? "Pick a guess above, or type what it is" : "Type what it is"}" autocomplete="off"></label>
      <fieldset class="cite"><legend>Your source <span class="req">Required</span></legend>
        <p class="muted small">Where did you check what it is? It's saved with the find, and the field identifier uses it in future scans.</p>
        <div class="cite-row"><label>Kind<select name="ctype">${opt}</select></label>
          <label class="grow">Title or name<input name="ctitle" maxlength="200" value="${esc(draft.ctitle || "")}" placeholder="Website name, book title, or who you asked" autocomplete="off"></label></div>
        <label>Source website <span class="muted small" data-cite-optional="${esc(key)}" ${draft.ctype === "expert" ? "" : "hidden"}>(optional for a person)</span>
          <input name="curl" type="url" maxlength="500" value="${esc(draft.curl || "")}" placeholder="https://… where this information can be found" autocomplete="off"></label>
        <label>Page or details <span class="muted small">(optional)</span><input name="cdetail" maxlength="500" value="${esc(draft.cdetail || "")}" placeholder="Page 211, edition, or when you asked" autocomplete="off"></label>
      </fieldset>
      <p class="small warn-text" data-confirm-msg="${esc(key)}" role="alert"></p>
      <button type="submit" class="btn primary">Identify it</button>
    </form></div>`;
}
// ---- search: every word must appear somewhere in the find
function findText(u, e) {
  const C = FIELD_CATS[e.category] || FIELD_CATS.other, key = u.id + "/" + e.id;
  return [e.name, e.scientific, C.label, C.plural, place(e.location), when(e.captured), noteDrafts.get(key) ?? e.notes,
    ...(e.quotes || []).map(q => q.text + " " + (q.title || "")), ...Object.entries(e.details || {}).map(([k, v]) => valText(v, k)),
    ...(e.candidates || []).map(c => c.name + " " + (c.scientific || "")), ...(e.sources || []).map(x => x.title || ""),
    e.citation?.title, e.citation?.detail, isMine(e) && !isNeeds(e) ? "identified by you mine" : "", isNeeds(e) ? "needs identification unknown" : ""]
    .filter(Boolean).join(" ").toLowerCase();
}
const matchQ = (u, e, q) => !q || q.toLowerCase().split(/\s+/).filter(Boolean).every(w => findText(u, e).includes(w));

// ---- cards: condensed by default (photo, name, key facts); click to open the full card
function cardParts(u, e) {
  const C = FIELD_CATS[e.category] || FIELD_CATS.other, d = e.details || {};
  const unknown = e.category === "firstaid" && /^(item|injury)$/i.test(valText(d.type || "")) ? valText(d.type).toLowerCase() : C.label.toLowerCase();
  const title = e.name || (isNeeds(e) ? `Unknown ${unknown}` : C.label);
  const sure = e.confidence != null && !isMine(e) ? `<span class="pill ${e.confidence >= (field.sure || 0.8) ? "" : "warn"}">${Math.round(e.confidence * 100)}% sure</span>` : "";
  const mine = isMine(e) && !isNeeds(e) ? `<span class="pill mine">Identified by you</span>` : "";
  const meta = [when(e.captured), place(e.location)].filter(Boolean).join(" · ");
  const tags = C.badges.filter(k => hasVal(d[k])).map(k => `<span class="tag ${tone(d[k], k)}"><small>${esc((C.fields.find(f => f[0] === k) || [k, humanize(k)])[1])}</small>${esc(valText(d[k], k))}</span>`);
  const img = e.photo ? `<img src="${esc(fieldMedia(u, e.photo))}" alt="Photo of ${esc(title)}" loading="lazy">` : "";
  return { C, d, title, sure, mine, meta, tags, img };
}
function compactCard(u, e) {
  const { C, d, title, sure, mine, meta, img } = cardParts(u, e), key = u.id + "/" + e.id;
  // Just the values here (the label shows on hover); the full card has the labels.
  const tags = C.badges.filter(k => hasVal(d[k])).map(k => `<span class="tag ${tone(d[k], k)}" title="${esc((C.fields.find(f => f[0] === k) || [k, humanize(k)])[1])}">${esc(valText(d[k], k))}</span>`);
  const guesses = isNeeds(e) && e.candidates?.length ? `<span class="find-guess">Might be ${e.candidates.slice(0, 2).map(c => esc(c.name)).join(" or ")}</span>` : "";
  const noted = (noteDrafts.get(key) ?? e.notes) ? `<span class="find-noted">Has your notes</span>` : "";
  return `<article class="find compact ${isNeeds(e) ? "needs" : ""}" data-key="${esc(key)}">
    <button type="button" class="find-open" data-act="field-open" data-key="${esc(key)}" aria-expanded="false">
      <span class="find-photo ${img ? "" : "none"}">${img || esc(C.label)}</span>
      <span class="grow find-head">
        <span class="find-kicker"><span class="kind">${esc(C.label)}</span>${sure}${mine}</span>
        <b class="find-title">${esc(title)}</b>${e.scientific ? `<span class="sci">${esc(e.scientific)}</span>` : ""}
        ${meta ? `<span class="muted small">${esc(meta)}</span>` : ""}
        ${tags.length ? `<span class="tags">${tags.slice(0, 2).join("")}</span>` : ""}
        ${guesses}${noted}
      </span>
      <span class="find-more">${isNeeds(e) ? "Identify" : "Details"} <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg></span>
    </button></article>`;
}
function findCard(u, e) {
  const key = u.id + "/" + e.id;
  if (!fieldOpen.has(key)) return compactCard(u, e);
  const { C, d, title, sure, mine, meta, tags, img } = cardParts(u, e);
  const photo = img ? `<a class="find-photo" href="${esc(fieldMedia(u, e.photo))}" target="_blank" rel="noopener" title="Open the full photo">${img}</a>`
    : `<div class="find-photo none" aria-hidden="true">${esc(C.label)}</div>`;
  const cautionText = (e.category === "plant" || e.category === "fungus") && hasVal(d.edibility) && tone(d.edibility, "edibility") !== "danger"
    ? `Never eat a wild ${e.category === "fungus" ? "mushroom" : "plant"} on a scan alone. Check it against a second source${e.category === "fungus" ? ", and if in doubt, don't eat it" : ", and test a small amount first"}.` : C.caution;
  const caution = cautionText ? `<p class="find-caution">${esc(cautionText)}</p>` : "";
  const note = noteDrafts.has(key) ? noteDrafts.get(key) : e.notes || "";
  return `<article class="find open ${isNeeds(e) ? "needs" : ""}" data-key="${esc(key)}">
    <div class="find-top">${photo}
      <div class="grow find-head">
        <div class="find-kicker"><span class="kind">${esc(C.label)}</span>${sure}${mine}</div>
        <h3>${esc(title)}</h3>${e.scientific ? `<p class="sci">${esc(e.scientific)}</p>` : ""}
        ${meta ? `<p class="muted small">${esc(meta)}</p>` : ""}
        ${tags.length ? `<div class="tags">${tags.join("")}</div>` : ""}
      </div>
      <button type="button" class="btn small find-close" data-act="field-open" data-key="${esc(key)}" aria-expanded="true">Show less</button></div>
    ${quotesBlock(e)}
    ${e.category === "language" ? langBlock(u, e) : ""}
    ${purposesBlock(d)}
    ${factsList(C, d, e.category)}${keepsBlock(d)}${caution}
    ${sourcesBlock(e)}${!isNeeds(e) && !e.citation?.url && !(e.sources || []).some(x => x.url) && !(e.quotes || []).some(x => x.url) && Object.keys(d).length
      ? `<p class="small warn-text">No source website was given for this information.</p>` : ""}
    ${confirmBlock(u, e)}
    <label class="find-notes"><span>Your notes <small class="muted" data-note-status="${esc(key)}">${e.notesUpdated && !noteDrafts.has(key) ? "Saved " + esc(when(e.notesUpdated)) : ""}</small></span>
      <textarea rows="3" maxlength="5000" data-note="${esc(key)}" data-upload="${esc(u.id)}" data-entry="${esc(e.id)}"
        placeholder="Where you found it, what you used it for, what to check next…">${esc(note)}</textarea></label>
  </article>`;
}

function renderFieldStep() {
  const msg = $("#field-errors"), body = $("#field-body");
  // Finds are kept on the connected drive; with no drive they're kept on this computer until you connect one.
  if (!S.field && !fieldLoading && !field && !fieldErr) loadField();
  if (S.field && S.field.rev !== fieldRev && !fieldLoading) loadField();
  body.hidden = false;
  if (!field) {
    msg.hidden = !fieldErr;
    if (fieldErr) msg.innerHTML = `<div class="notice error">${esc(fieldErr)}</div>`;
    if (changed("fieldList", "loading")) $("#field-list").innerHTML = `<p class="empty">Loading your finds…</p>`;
    return;
  }
  // Files the device left that couldn't be read.
  const errs = field.errors || [];
  const eh = errs.length ? `<div class="notice warn field-errs"><b>${plural(errs.length, "file", "files")} from the device couldn't be read</b>
    <ul>${errs.map(x => `<li><code>${esc(x.file)}</code>: ${esc(x.error)}</li>`).join("")}</ul>
    <p class="small">They were moved to the drive's <code>field-id/rejected</code> folder.</p><button type="button" class="btn small" data-act="field-dismiss">Dismiss</button></div>` : "";
  const local = !field.onDrive ? `<div class="notice">No drive is connected, so these finds are kept on this computer. <a href="#drive">Choose a drive</a> to keep finds on it; the field identifier reads and writes the drive.</div>` : "";
  msg.hidden = !(eh || local);
  if (changed("fieldMsg", local + eh)) msg.innerHTML = local + eh;

  const ups = field.uploads.slice().reverse();  // newest first
  if (fieldUpload !== "all" && !ups.some(u => u.id === fieldUpload)) fieldUpload = "all";
  const shown = fieldUpload === "all" ? ups : ups.filter(u => u.id === fieldUpload);
  const counts = es => ({ n: es.length, need: es.filter(isNeeds).length });
  const all = counts(ups.flatMap(u => u.entries));
  const side = `<button type="button" class="cat-btn" data-act="field-upload" data-id="all" aria-current="${fieldUpload === "all"}">
      <b>All uploads</b><small>${plural(all.n, "find", "finds")}${all.need ? ` · ${all.need} to identify` : ""}</small></button>`
    + ups.map((u, i) => { const c = counts(u.entries);
      return `<button type="button" class="cat-btn" data-act="field-upload" data-id="${esc(u.id)}" aria-current="${fieldUpload === u.id}">
        <b>${i === 0 ? "Latest · " : ""}${esc(when(u.received))}</b><small>${esc(u.device?.name || "Field identifier")} · ${plural(c.n, "find", "finds")}${c.need ? ` · ${c.need} to identify` : ""}</small></button>`; }).join("");
  if (changed("fieldSide", side)) $("#field-uploads").innerHTML = side;
  $("#field-inbox").textContent = `The device saves uploads to ${field.inbox}. Commune imports them on its own.`;
  const sampleBtn = ups.some(u => u.id === "commune-sample") ? "" : `<button type="button" class="btn small" data-act="field-sample">Load sample finds</button>`;
  if (changed("fieldSample", sampleBtn)) $("#field-sample").innerHTML = sampleBtn;

  const inUpload = shown.flatMap(u => u.entries);
  const filterOf = e => FILTER_OF[e.category] || e.category;
  const cats = Object.keys(FIELD_CATS).filter(c => !FILTER_OF[c] && inUpload.some(e => filterOf(e) === c));
  if (fieldCat !== "all" && !cats.includes(fieldCat)) fieldCat = "all";
  const q = fieldQuery.trim(), upOf = new Map(shown.flatMap(u => u.entries.map(e => [e, u])));
  const inCat = inUpload.filter(e => (fieldCat === "all" || filterOf(e) === fieldCat) && matchQ(upOf.get(e), e, q));
  const nId = inCat.filter(e => !isNeeds(e)).length, nNeed = inCat.length - nId;
  const tabs = `<button type="button" data-act="field-tab" data-tab="identified" aria-pressed="${fieldTab === "identified"}"><b>Identified (${nId})</b><small>Found and identified</small></button>
    <button type="button" data-act="field-tab" data-tab="needs" aria-pressed="${fieldTab === "needs"}"><b>Needs identification (${nNeed})</b><small>The device wasn't sure: you identify it</small></button>`;
  if (changed("fieldTabs", tabs)) $("#field-tabs").innerHTML = tabs;
  const chips = cats.length > 1 ? [["all", "Everything"], ...cats.map(c => [c, FIELD_CATS[c].plural])].map(([c, l]) =>
    `<button type="button" class="chip" data-act="field-cat" data-cat="${c}" aria-pressed="${fieldCat === c}">${esc(l)}</button>`).join("") : "";
  if (changed("fieldCats", chips)) $("#field-cats").innerHTML = chips;

  const u1 = fieldUpload !== "all" ? shown[0] : null;
  const head = u1 ? `<div class="upload-head"><div class="grow"><b>Upload from ${esc(u1.device?.name || "the field identifier")}</b>
      <small class="muted">${esc(["Received " + when(u1.received), u1.since && "scanned since " + when(u1.since), u1.source].filter(Boolean).join(" · "))}</small></div>
      <button type="button" class="btn small ghost danger" data-act="field-del-upload" data-id="${esc(u1.id)}">Delete upload</button></div>` : "";
  if (changed("fieldHead", head)) $("#field-upload-head").innerHTML = head;

  // Don't redraw the finds while someone is typing in one (a note, or what a find is).
  const ae = document.activeElement;
  if (ae && $("#field-list").contains(ae) && /^(TEXTAREA|INPUT)$/.test(ae.tagName)) return;
  const wiki = Object.entries(S.libraries).filter(([n]) => n.startsWith("wiktionary_")).map(([n, L]) => [n, L.file, picked.has(n)]);
  if (!changed("fieldList", [fieldRev, fieldLocal, fieldUpload, fieldTab, fieldCat, q, [...fieldOpen], S.serving, wiki, S.kiwixHome, Object.values(S.libraries).map(L => L.file)])) return;
  KNOWN = knownIndex();
  const want = (u, e) => (fieldTab === "needs") === isNeeds(e) && (fieldCat === "all" || filterOf(e) === fieldCat) && matchQ(u, e, q);
  const cards = shown.flatMap(u => u.entries.filter(e => want(u, e)).map(e => findCard(u, e))).join("");
  let empty;
  if (q && ups.length) empty = `<p class="empty">No ${fieldTab === "needs" ? "finds that need identifying" : "identified finds"} match “${esc(q)}”.${(fieldTab === "needs" ? nId : nNeed) ? ` <button type="button" class="link-btn" data-act="field-tab" data-tab="${fieldTab === "needs" ? "identified" : "needs"}">See ${plural(fieldTab === "needs" ? nId : nNeed, "match", "matches")} in ${fieldTab === "needs" ? "Identified" : "Needs identification"}</button>` : ""}</p>`;
  else if (!ups.length) empty = `<div class="empty"><b>No uploads yet.</b><br>Plug the field identifier into this drive and it saves its finds to the <code>field-id/inbox</code> folder, or click <b>Import upload</b> and pick the file it made.
    <p><button type="button" class="btn small" data-act="field-sample">Load sample finds</button> <span class="muted small">One test find for each kind; delete them any time.</span></p></div>`;
  else if (fieldTab === "needs") empty = `<p class="empty">Nothing here needs identifying.${nId ? " Everything was identified." : ""}</p>`;
  else empty = `<p class="empty">Nothing identified here yet.${nNeed ? ` Check <button type="button" class="link-btn" data-act="field-tab" data-tab="needs">${plural(nNeed, "find", "finds")} that need identifying</button>.` : ""}</p>`;
  $("#field-list").innerHTML = cards || empty;
}

// Notes save on their own a moment after you stop typing, and when you leave the box.
async function saveNote(uid, eid, key) {
  clearTimeout(noteTimers[key]); delete noteTimers[key];
  const text = noteDrafts.get(key);
  if (text == null) return;
  const st = () => document.querySelector(`[data-note-status="${CSS.escape(key)}"]`);
  if (st()) st().textContent = "Saving…";
  try {
    await api("/api/field/note", { upload: uid, entry: eid, notes: text });
    const e = findLocal(uid, eid); if (e) { e.notes = text; e.notesUpdated = new Date().toISOString(); }
    if (noteDrafts.get(key) === text) noteDrafts.delete(key);
    if (st()) st().textContent = "Saved";
  } catch (err) { if (st()) st().textContent = "Couldn't save: " + err.message; }
}
document.addEventListener("input", e => {
  const t = e.target, key = t.dataset?.note;
  if (!key) return;
  noteDrafts.set(key, t.value);
  const st = document.querySelector(`[data-note-status="${CSS.escape(key)}"]`);
  if (st) st.textContent = "Not saved yet…";
  clearTimeout(noteTimers[key]);
  noteTimers[key] = setTimeout(() => saveNote(t.dataset.upload, t.dataset.entry, key), 800);
});
document.addEventListener("focusout", e => {
  const t = e.target;
  if (t.dataset?.note && noteDrafts.has(t.dataset.note)) saveNote(t.dataset.upload, t.dataset.entry, t.dataset.note);
  if (t.closest?.("#field-list")) setTimeout(() => { if (step() === "field") render(); }, 0);  // catch up on redraws held back while typing
});
// "Who speaks it in …": picking a country shows its share, and the same country is picked on every language card.
document.addEventListener("change", e => {
  const key = e.target.dataset?.country;
  if (!key) return;
  fieldCountry = e.target.value; store.set("commune.fieldCountry", fieldCountry);
  const [uid, eid] = key.split("/"), find = findLocal(uid, eid);
  const out = document.querySelector(`[data-country-out="${CSS.escape(key)}"]`);
  if (out && find) out.textContent = valText(find.details.countryShare[fieldCountry], "share");
  fieldLocal++;
});
// "Identify it": what it is, plus a source (required), kept as a draft across redraws until it's sent.
function confirmDraft(f) {
  const key = f.dataset.key, old = confirmDrafts.get(key) || {}, name = f.elements.name.value;
  confirmDrafts.set(key, { name, sci: name === old.name ? old.sci || "" : "", ctype: f.elements.ctype.value,
    ctitle: f.elements.ctitle.value, curl: f.elements.curl.value, cdetail: f.elements.cdetail.value });
  const opt = f.querySelector("[data-cite-optional]"); if (opt) opt.hidden = f.elements.ctype.value !== "expert";
}
document.addEventListener("input", e => { const f = e.target.closest?.(".find-confirm"); if (f) confirmDraft(f); });
document.addEventListener("change", e => { const f = e.target.closest?.(".find-confirm"); if (f) confirmDraft(f); });
document.addEventListener("submit", async e => {
  const f = e.target.closest?.(".find-confirm");
  if (!f) return;
  e.preventDefault();
  confirmDraft(f);
  const key = f.dataset.key, dr = confirmDrafts.get(key), say = m => { const el = f.querySelector("[data-confirm-msg]"); if (el) el.textContent = m; };
  const name = dr.name.trim(), title = dr.ctitle.trim(), detail = dr.cdetail.trim(), url = dr.curl.trim();
  if (!name) { say("Say what it is first: pick one of the guesses or type it."); f.elements.name.focus(); return; }
  if (!title) { say("Add your source: the website, book or person you identified it with."); f.elements.ctitle.focus(); return; }
  if ((url || dr.ctype !== "expert") && !/^https?:\/\/[^\s/]+\.\S*$/.test(url)) { say("Add the source's website, starting with http:// or https://: where this information can be found."); f.elements.curl.focus(); return; }
  say("");
  const btn = f.querySelector("[type=submit]"); btn.disabled = true;
  try {
    await api("/api/field/confirm", { upload: f.dataset.upload, entry: f.dataset.entry, name, scientific: dr.sci || "",
      citation: { type: dr.ctype, title, detail, url } });
    confirmDrafts.delete(key);
    document.activeElement?.blur();
    notice(`Identified “${esc(name)}” and added it to your knowledge base. The field identifier will use it in future scans. It's in the Identified tab.`);
  } catch (err) { say(err.message); btn.disabled = false; return; }
  await refresh();
});
function fieldSay(text, lang) {
  if (!canSpeak || !text) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const base = (lang || "").toLowerCase().split("-")[0];
  const voice = speechSynthesis.getVoices().find(v => v.lang.toLowerCase().split(/[-_]/)[0] === base);
  if (lang) u.lang = lang;
  if (voice) u.voice = voice;
  else if (base) notice("This computer has no voice for that language installed, so it may read it with the wrong accent. Add one in your system's speech settings.", "warn");
  speechSynthesis.speak(u);
}
$("#field-search").oninput = e => { fieldQuery = e.target.value; render(); };
$("#field-import").onclick = () => $("#field-file").click();
$("#field-file").onchange = async e => {
  const f = e.target.files[0]; e.target.value = "";
  if (!f) return;
  notice(`Importing ${esc(f.name)}…`);
  try {
    const r = await fetch(`/api/field/upload?name=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    if (data.duplicate) notice("That upload was already imported.");
    else {
      fieldUpload = data.id; fieldTab = data.needs ? "needs" : "identified";
      store.set("commune.fieldUpload", fieldUpload); store.set("commune.fieldTab", fieldTab);
      notice(`Imported ${plural(data.count, "find", "finds")}${data.needs ? `. ${data.needs} need identifying` : ""}.`);
    }
  } catch (err) { notice(esc(err.message), "error"); }
  await refresh();
};

// ------------------------------------------------------------------ pop-up menus
// Opens a toolbar menu just under the button that opened it (a sheet at the bottom on small screens).
function openPopup(sel, btn) {
  const dlg = $(sel), r = btn.getBoundingClientRect();
  // Open below the button, or above it when there isn't room below (e.g. "See more" low in the sidebar).
  const below = innerHeight - r.bottom - 16, above = r.top - 16;
  if (below < 360 && above > below) { dlg.style.top = "auto"; dlg.style.bottom = Math.round(innerHeight - r.top + 8) + "px"; dlg.style.maxHeight = Math.round(Math.min(above - 8, 620)) + "px"; }
  else { dlg.style.bottom = "auto"; dlg.style.top = Math.max(16, Math.round(r.bottom + 8)) + "px"; dlg.style.maxHeight = ""; }  // the header scrolls away, so keep the menu on screen
  // Open toward the middle of the screen: right-aligned for top-bar buttons, left-aligned for ones on the left (the sidebar).
  if (r.left < innerWidth / 2) { dlg.style.left = Math.max(16, Math.round(r.left)) + "px"; dlg.style.right = "auto"; }
  else { dlg.style.right = Math.max(16, Math.round(innerWidth - r.right)) + "px"; dlg.style.left = "auto"; }
  if (!dlg.open) dlg.showModal();
}

// ------------------------------------------------------------------ queue
const X_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
// What's inside a package, as a drop-down list of single resources and websites.
const detailsOpen = new Set();  // drop-downs the person opened, kept open across re-renders
document.addEventListener("toggle", e => {
  const k = e.target.dataset?.key; if (!k) return;
  e.target.open ? detailsOpen.add(k) : detailsOpen.delete(k);
}, true);
function insideList(key, libs, sites, removable) {
  const n = libs.length + sites.length;
  if (!n) return "";
  const x = (act, label) => removable ? `<button type="button" class="icon-btn xs" ${act} aria-label="Remove ${esc(label)} from the queue" title="Remove">${X_ICON}</button>` : "";
  const rows = libs.map(k => { const L = S.libraries[k];
      return `<li><div class="grow"><span class="kind">Single resource</span><b>${esc(L?.title || k)}</b>${L?.summary ? `<p class="desc">${esc(L.summary)}</p>` : ""}<small class="muted">${fmt(libSize(k))}</small></div>${x(`data-act="pick" data-name="${esc(k)}"`, L?.title || k)}</li>`; })
    .concat(sites.map(w => `<li><div class="grow"><span class="kind">Single website</span><b>${esc(w.title)}</b><small class="muted">${esc(host(w.url))}</small></div>${x(`data-act="unpend" data-url="${esc(w.url)}"`, w.title)}</li>`));
  return `<details class="inside" data-key="${esc(key)}" ${detailsOpen.has(key) ? "open" : ""}><summary>What's inside (${n})</summary><ul>${rows.join("")}</ul></details>`;
}
function queueRow(kind, key, title, desc, sub) {
  const act = kind === "lib" ? `data-act="pick" data-name="${esc(key)}"` : `data-act="unpend" data-url="${esc(key)}"`;
  return `<div class="q-row"><div class="grow"><span class="kind">${kind === "lib" ? "Single resource" : "Single website"}</span>
    <b>${esc(title)}</b>${desc ? `<p class="desc">${esc(desc)}</p>` : ""}<small class="muted">${esc(sub)}</small></div>
    ${kind === "site" ? `<button type="button" class="icon-btn sm" data-act="edit-site" data-kind="pending" data-key="${esc(key)}" aria-label="Edit ${esc(title)}" title="Edit topic or address">${ICON.edit}</button>` : ""}
    <button type="button" class="icon-btn sm" ${act} aria-label="Remove ${esc(title)} from the queue" title="Remove">${X_ICON}</button></div>`;
}
function renderQueue() {
  const n = cartCount();
  $("#queue-summary").textContent = n ? `${plural(n, "item", "items")} · ${fmt(cartSize())}` : "";
  // Packages added as a whole show as one row; anything else shows on its own.
  const shownLibs = new Set(), shownSites = new Set(), rows = [];
  qPkgs.map(findPkg).filter(Boolean).forEach(p => {
    const libs = p.libraries.filter(k => picked.has(k) && !shownLibs.has(k));
    const sites = p.sites.filter(x => pending.some(y => y.url === x.url) && !shownSites.has(x.url));
    if (!libs.length && !sites.length) return;
    libs.forEach(k => shownLibs.add(k)); sites.forEach(x => shownSites.add(x.url));
    const size = libs.reduce((a, k) => a + libSize(k), 0);
    const parts = [libs.length && plural(libs.length, "library", "libraries"), sites.length && plural(sites.length, "website", "websites")].filter(Boolean).join(" + ");
    rows.push(`<div class="q-row"><div class="grow"><span class="kind pkg-kind">Package</span>
      <b>${esc(p.name)}</b>${p.description ? `<p class="desc">${esc(p.description)}</p>` : ""}
      <small class="muted">${esc(parts)}${size ? " · " + fmt(size) : ""}</small>${insideList("q:" + p.id, libs, sites, true)}</div>
      <button type="button" class="icon-btn sm" data-act="q-pkg-del" data-id="${esc(p.id)}" aria-label="Remove the ${esc(p.name)} package from the queue" title="Remove">${X_ICON}</button></div>`);
  });
  [...picked].filter(k => !shownLibs.has(k)).forEach(k => rows.push(queueRow("lib", k, S.libraries[k]?.title || k, S.libraries[k]?.summary, fmt(libSize(k)))));
  pending.filter(x => !shownSites.has(x.url)).forEach(x => rows.push(queueRow("site", x.url, x.title, "", host(x.url))));
  const html = rows.join("") || `<p class="empty">Your queue is empty.</p>`;
  if (changed("queue", html)) $("#queue-list").innerHTML = html;
  let fit = "";
  if (n && hasDrive()) { const f = cartFit(S.drive); fit = `<span class="small ${f.over ? "warn-text" : "muted"}">${esc(f.sub)}</span>`; }
  const foot = n
    ? `${fit ? `<div class="q-fit">${fit}</div>` : ""}<button type="button" class="btn small ghost" data-act="clear">Clear</button><button type="button" class="btn small" data-act="save-pkg">+ Create package</button>
       <span class="grow"></span>
       ${hasDrive() ? `<button type="button" class="btn small primary" data-act="go">Download &amp; continue</button>` : `<a class="btn small primary" href="#drive">Choose drive →</a>`}`
    : `<span class="grow"></span><a class="btn small" href="#pick">Choose topics</a>`;
  if (changed("queueFoot", foot)) $("#queue-foot").innerHTML = foot;
}
$("#queue-btn").onclick = e => { delete sigs.queue; delete sigs.queueFoot; renderQueue(); openPopup("#queue", e.currentTarget); e.currentTarget.setAttribute("aria-expanded", "true"); };
$("#queue").addEventListener("close", () => $("#queue-btn").setAttribute("aria-expanded", "false"));

// ------------------------------------------------------------------ edit a topic
let editingTopic = null, topicLibs = [], topicOff = new Set();  // libraries listed in the dialog, and the unticked ones
function topicLibRow(n) {
  const L = S.libraries[n];
  return `<label class="check-row"><input type="checkbox" ${topicOff.has(n) ? "" : "checked"} value="${esc(n)}">
    <span class="grow"><b>${esc(L?.title || n)}</b><small class="muted">${esc([L?.summary, fmt(libSize(n))].filter(Boolean).join(" · "))}</small></span></label>`;
}
function renderTopicLibs() {
  $("#edit-topic-libs").innerHTML = topicLibs.map(topicLibRow).join("") || `<p class="muted small">No libraries yet. Add one below.</p>`;
  const others = Object.keys(S.libraries).filter(n => !topicLibs.includes(n))
    .sort((a, b) => S.libraries[a].title.localeCompare(S.libraries[b].title));
  $("#edit-topic-add").innerHTML = `<option value="">Choose a library…</option>` + others.map(n => `<option value="${esc(n)}">${esc(S.libraries[n].title)} · ${fmt(libSize(n))}</option>`).join("");
}
function openEditTopic(id) {
  const t = topicIndex()[id];
  if (!t) return;
  editingTopic = t; topicLibs = t.kiwix.slice(); topicOff = new Set();
  const f = $("#edit-topic-form");
  f.reset();
  f.elements.title.value = t.title;
  $("#edit-topic-title").textContent = t.title;
  renderTopicLibs();
  $("#edit-topic-note").textContent = "Changes show here and on the drive's home page the next time you build it. Websites in this topic have their own pencil.";
  $("#edit-topic-reset").hidden = !t.edited;
  $("#edit-topic").showModal();
  f.elements.title.focus();
}
$("#edit-topic-add-btn").onclick = () => {
  const n = $("#edit-topic-add").value;
  if (!n || topicLibs.includes(n)) return;
  topicLibs.push(n);
  renderTopicLibs();
};
$("#edit-topic-libs").onchange = e => { if (e.target.checked) topicOff.delete(e.target.value); else topicOff.add(e.target.value); };
$("#edit-topic-form").onsubmit = async e => {
  e.preventDefault();
  const f = e.target, t = editingTopic;
  const kiwix = [...f.querySelectorAll("#edit-topic-libs input:checked")].map(i => i.value);
  try {
    await api("/api/topic", { id: t.id, title: f.elements.title.value, kiwix });
    $("#edit-topic").close();
    notice(`Saved changes to “${esc(f.elements.title.value.trim())}”.${S.guideBuilt ? " Build the drive again to update its home page." : ""}`);
  } catch (err) { notice(esc(err.message), "error"); }
  await refresh();
};
$("#edit-topic-reset").onclick = async () => {
  const t = editingTopic;
  if (!t || !confirm(`Reset “${t.title}” to Commune's version (“${t.originalTitle}” with its original libraries)?`)) return;
  $("#edit-topic").close();
  await act(() => api("/api/topic", { id: t.id, reset: true }), `Reset “${esc(t.originalTitle)}” to Commune's version.`);
};

// ------------------------------------------------------------------ edit a package
let editing = null;
function openEditPackage(id) {
  const p = findPkg(id);
  if (!p) return;
  editing = p;
  const f = $("#edit-pkg-form");
  f.reset();
  f.elements.name.value = p.name;
  f.elements.description.value = p.description || "";
  $("#edit-pkg-kind").textContent = p.builtin ? "Commune package" : "Your package";
  const item = (kind, key, title, sub) => `<label class="check-row"><input type="checkbox" checked data-kind="${kind}" value="${esc(key)}">
    <span class="grow"><b>${esc(title)}</b><small class="muted">${esc(sub)}</small></span></label>`;
  $("#edit-pkg-items").innerHTML = p.libraries.map(n => item("lib", n, S.libraries[n]?.title || n, fmt(libSize(n)))).join("")
    + p.sites.map(x => item("site", x.url, x.title, "Website copy · " + host(x.url))).join("")
    || `<p class="muted small">Nothing in it yet.</p>`;
  const n = cartCount();
  $("#edit-pkg-addq").hidden = !n;
  $("#edit-pkg-addq-text").textContent = `Also add what's in your queue (${plural(n, "item", "items")})`;
  $("#edit-pkg-note").textContent = p.builtin && !p.edited
    ? "This is one of Commune's packages. Your changes are saved as your own version, and you can reset it at any time."
    : "To add more, put things in your queue first, then come back and tick “Also add what's in your queue”.";
  $("#edit-pkg-reset").hidden = !p.edited;
  $("#edit-pkg").showModal();
  f.elements.name.focus();
}
$("#edit-pkg-form").onsubmit = async e => {
  e.preventDefault();
  const f = e.target, p = editing;
  const keep = kind => [...f.querySelectorAll(`#edit-pkg-items input[data-kind=${kind}]:checked`)].map(i => i.value);
  const libraries = keep("lib"), urls = new Set(keep("site"));
  const sites = p.sites.filter(x => urls.has(x.url));
  if (f.elements.addQueue.checked) {
    picked.forEach(n => { if (!libraries.includes(n)) libraries.push(n); });
    pending.forEach(x => { if (!sites.some(y => y.url === x.url)) sites.push(x); });
  }
  try {
    const r = await api("/api/packages/update", { id: p.id, name: f.elements.name.value, description: f.elements.description.value, libraries, sites });
    $("#edit-pkg").close();
    pkgStatus = `Saved changes to “${r.name}”.`;
    notice(`Saved changes to “${esc(r.name)}”.`);
  } catch (err) { notice(esc(err.message), "error"); $("#edit-pkg").close(); }
  delete sigs.pkgs; delete sigs.favs;
  await refresh();
};
$("#edit-pkg-reset").onclick = async () => {
  const p = editing;
  if (!p || !confirm(`Reset “${p.name}” to Commune's original version? Your changes to it are removed.`)) return;
  $("#edit-pkg").close();
  await act(() => api("/api/packages/delete", { id: p.id }), "Reset to Commune's version.");
  pkgStatus = ""; delete sigs.pkgs;
};

// ------------------------------------------------------------------ events
document.addEventListener("click", e => {
  if (e.target.tagName === "DIALOG") {  // click on the backdrop
    const r = e.target.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close();
    return;
  }
  const close = e.target.closest("[data-close]");
  if (close) { close.closest("dialog").close(); return; }
  const link = e.target.closest('dialog a[href^="#"]');  // a step link inside a pop-up: go there and close the pop-up
  if (link) link.closest("dialog").close();
  const el = e.target.closest("[data-act]");
  const choice = e.target.closest(".drive-choose .choice.off");
  if (choice) setDriveMode(choice.dataset.mode);
  if (!el || el.tagName === "SELECT" || el.disabled) return;
  const d = el.dataset;
  switch (d.act) {
    case "drive":
      if (d.path !== S.drive?.path) act(() => api("/api/settings", { drive: d.path }), "Drive selected.");
      break;
    case "connect":
    case "connect-always":
      act(() => api("/api/connect", { remember: d.act === "connect-always" }),
        `Connected to “${esc(S.savedDrive?.name)}”.` + (d.act === "connect-always" ? " Commune will reconnect to it without asking from now on." : ""));
      break;
    case "connect-later": connectDismissed = true; render(); break;
    case "rescan": case "pop-rescan": loadDrives(); break;
    case "pop-drive":
      homeDrive = d.path; delete sigs.homeDrive;
      if (d.path !== S.drive?.path) act(() => api("/api/settings", { drive: d.path }), "Drive selected.");
      else render();
      $("#drives-pop").close();
      break;
    case "scan-once": scanAllowed = true; loadDrives(); break;
    case "scan-always": scanAllowed = true; act(() => api("/api/permissions", { scanAlways: true })).then(loadDrives); break;
    case "reset-perms":
      scanAllowed = false;
      act(() => api("/api/permissions", { scanAlways: false, autoConnect: false }), "Commune will ask before looking for drives, and before reconnecting to your drive.");
      break;
    case "save-pkg": openSavePackage(); break;
    case "pkg-export": { const p = findPkg(d.id); if (p) exportPackage(p); break; }
    case "fav": act(() => api("/api/favorite", { id: d.id, favorite: !isFav(d.id), defaults: COMMUNE_PACKS.map(p => p.id) })); break;
    case "home-dl": homeDownload(d.id, el); break;
    case "open-packages": $("#packages-btn").click(); break;
    case "goto-cat": cat = d.id; store.set("commune.cat", cat); location.hash = "#pick"; break;
    case "pkg-del": {
      const p = S.packages.find(x => x.id === d.id);
      if (p && confirm(`Delete the package “${p.name}”? Nothing on your drive is removed.`))
        act(() => api("/api/packages/delete", { id: p.id })).then(() => { pkgStatus = `Deleted “${p.name}”.`; renderPackages(); });
      break;
    }
    case "cat":
      cat = d.id; store.set("commune.cat", cat); $("#filter").value = ""; render();
      $("#step-pick").scrollIntoView({ block: "start" });
      break;
    case "pick":
      picked.has(d.name) ? picked.delete(d.name) : picked.add(d.name); save(); render();
      break;
    case "pack":
      d.names.split(",").filter(n => n && canPick(n)).forEach(n => picked.add(n)); save(); render();
      break;
    case "del":
      if (confirm(`Delete ${d.file} from the drive?`)) act(() => api("/api/delete", { file: d.file }), "Removed from the drive. Build again to update the home page.");
      break;
    case "preview-lib": openPreview({ type: "lib", name: d.name }); break;
    case "preview-site": openPreview({ type: "site", url: d.url, title: d.title, topic: d.topic, pageLimit: +d.pages || 0 }); break;
    case "pv-site": togglePending({ url: pv.url, title: pv.title, topic: pv.topic, pageLimit: pv.pageLimit || 200 }); break;
    case "add-site": openQA(d.topic); break;
    case "del-doc": {
      const f = (S.files || []).find(x => x.name === d.name);
      if (f && confirm(`Remove “${f.title}” from the drive?`)) act(() => api("/api/files/delete", { name: f.name }), "Removed from the drive. Build again to update the topic's page.");
      break;
    }
    case "unpend": pending = pending.filter(p => p.url !== d.url); save(); render(); break;
    case "edit-site": openEditSite(d.kind, d.key); break;
    case "edit-topic": openEditTopic(d.id); break;
    case "sugg": { const s = S.suggestions[+d.i]; togglePending({ url: s.url, title: s.title, topic: s.topic, pageLimit: s.pageLimit }); break; }
    case "clear": picked.clear(); pending = []; qPkgs = []; save(); render(); break;
    case "q-pkg-del": { const p = findPkg(d.id); if (p) removePackageFromCart(p); else { qPkgs = qPkgs.filter(x => x !== d.id); save(); render(); } break; }
    case "go": if (el.closest("dialog")) el.closest("dialog").close(); downloadAndContinue(el); break;
    case "pkg-edit": openEditPackage(d.id); break;
    case "side-pkgs-more": pkgStatus = ""; delete sigs.pkgs; renderPackages(); openPopup("#packages", el); break;
    case "pkg-toggle": { const p = findPkg(d.id); if (p) (pkgQueued(p) ? removePackageFromCart(p) : addPackageToCart(p)); break; }
    case "pv-copy": copyLink($("#pv-open").href, el); break;
    case "field-upload": fieldUpload = d.id; store.set("commune.fieldUpload", fieldUpload); render(); break;
    case "field-tab": fieldTab = d.tab; store.set("commune.fieldTab", fieldTab); render(); break;
    case "field-cat": fieldCat = d.cat; render(); break;
    case "field-open":
      fieldOpen.has(d.key) ? fieldOpen.delete(d.key) : fieldOpen.add(d.key);
      fieldLocal++; render();
      if (fieldOpen.has(d.key)) document.querySelector(`.find[data-key="${CSS.escape(d.key)}"]`)?.scrollIntoView({ block: "nearest" });
      break;
    case "field-pick": {  // one of the device's guesses: fill it in, then ask for the source
      const old = confirmDrafts.get(d.key) || { ctype: "website", ctitle: "", curl: "", cdetail: "" };
      confirmDrafts.set(d.key, { ...old, name: d.name, sci: d.sci });
      fieldLocal++; render();
      document.querySelector(`.find-confirm[data-key="${CSS.escape(d.key)}"] [name=ctitle]`)?.focus();
      break;
    }
    case "field-goto": {  // show one find, opened, wherever it is
      const [uid, eid] = d.key.split("/"), f = findLocal(uid, eid);
      if (!f) break;
      fieldUpload = "all"; fieldCat = "all"; fieldQuery = ""; $("#field-search").value = "";
      fieldTab = isNeeds(f) ? "needs" : "identified"; fieldOpen.add(d.key);
      fieldLocal++; render();
      document.querySelector(`.find[data-key="${CSS.escape(d.key)}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" });
      break;
    }
    case "field-unconfirm": act(() => api("/api/field/unconfirm", { upload: d.upload, entry: d.entry }), "Moved it to Needs identification."); break;
    case "field-say": fieldSay(d.text, d.lang); break;
    case "field-sample":
      act(() => api("/api/field/sample", {}), r => {
        if (!r.duplicate) { fieldUpload = r.id; fieldTab = "identified"; fieldCat = "all"; store.set("commune.fieldUpload", r.id); store.set("commune.fieldTab", "identified"); }
        return r.duplicate ? "The sample finds are already here." : `Loaded ${plural(r.count, "sample find", "sample finds")}. Delete them any time with Delete upload.`;
      });
      break;
    case "field-dismiss": act(() => api("/api/field/dismiss", {})); break;
    case "field-check":
      act(() => api("/api/field/import", {}), r => r.imported.length
        ? `Imported ${plural(r.imported.length, "upload", "uploads")} from the drive.`
        : r.errors.length ? "Some files on the drive couldn't be read. See the list above." : "No new uploads on the drive.");
      break;
    case "field-del-upload": {
      const u = field?.uploads.find(x => x.id === d.id);
      if (u && confirm(`Delete this upload (${plural(u.entries.length, "find", "finds")}, with their photos and your notes)? This can't be undone.`))
        act(() => api("/api/field/delete", { upload: u.id }), "Deleted the upload.");
      break;
    }
    case "cancel": act(() => api("/api/cancel", { id: d.id })); break;
    case "retry": retry(d.id); break;
    case "plat": plats.has(d.id) ? plats.delete(d.id) : plats.add(d.id); render(); break;
    case "serve": {
      const was = S.serving;
      act(() => api("/api/serve", { action: was ? "stop" : "start" }), was ? "Reader stopped." : "Reader started.");
      break;
    }
  }
});
document.addEventListener("change", e => {
  const d = e.target.dataset;
  if (d.act === "flavour") act(() => api("/api/flavour", { name: d.name, flavour: e.target.value }));
});

// ------------------------------------------------------------------ loop
const API_VERSION = 11;  // must match API_VERSION in offgrid.py
let staleServer = false;

async function refresh() {
  let next;
  try { next = await api("/api/state"); }
  catch { lostConnection = true; notice("Lost connection to the builder. Is it still running? Start it again with <code>./start.command</code>.", "error"); return; }
  if (next.apiVersion !== API_VERSION) {
    // An older builder is still running from before an update: its data doesn't match this page.
    if (!staleServer) notice("The builder running in Terminal is an older version than this page. Close it (press <b>Ctrl+C</b> in its Terminal window), run <code>./start.command</code> again, then reload this page.", "error");
    staleServer = true;
    return;
  }
  if (staleServer) { staleServer = false; notice(""); }
  S = next;
  if (lostConnection) { lostConnection = false; notice(""); }
  let dirty = false;
  for (const n of [...picked]) if (!canPick(n)) { picked.delete(n); dirty = true; }
  if (dirty) save();
  if (S.drive?.missing && !missingWarned) { missingWarned = true; notice(`The drive <code>${esc(S.drive.path)}</code> isn't connected. Plug it in or pick another.`, "warn"); }
  if (!S.drive?.missing) missingWarned = false;
  render();
}
// Drives are only scanned once the person allows it (renderDriveStep asks first).
(async () => { await refresh(); setInterval(refresh, 1500); })();
