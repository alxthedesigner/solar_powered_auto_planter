// Planter page: readings from the automated planter (through its bridge), its watering, and the settings it follows.
// Uses app.js's helpers ($, esc, plural, when, changed, api, notice, S). Format: docs/integrations/planter.md.

let pl = null, plLoading = false, plErr = "", plRev = null;
let plRange = (() => { try { return localStorage.getItem("commune.plRange") || "7"; } catch { return "7"; } })();
let plDirty = false;                      // the settings form has unsaved changes: don't redraw it under the person
let plBridgeShown = false;                // the bridge form was filled from the saved address
const PL_COLORS = ["var(--accent)", "#b8691f", "#6a5acd", "#b03a6b", "#2f7fb3", "#8a8a1e", "#c0563a", "#5f6b73"];
const PL_EVENT = {
  "watered": "Watered", "skipped": "Skipped", "tank-low": "Tank low", "low-battery": "Battery low", "slow-flow": "Water flowing slowly",
  "valve-closed-on-boot": "Closed valves after a restart", "pumped": "Refilled header tank", "pump-timeout": "Pump stopped: header didn't fill", "vent": "Vent", "error": "Problem", "other": "Note",
};
const PL_ALERT = new Set(["tank-low", "low-battery", "slow-flow", "pump-timeout", "error"]);
const fmtN = (v, d = 0) => v == null ? "–" : Number(v).toFixed(d);
const ago = s => {
  if (!s) return "never";
  const m = Math.round((Date.now() - new Date(s)) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  if (m < 48 * 60) return `${Math.round(m / 60)} h ago`;
  return `${Math.round(m / 1440)} days ago`;
};

async function loadPlanter() {
  plLoading = true;
  try { pl = await api("/api/planter"); plErr = ""; plRev = S.planter?.rev ?? null; }
  catch (e) { plErr = e.message; }
  plLoading = false;
  render();
}

function renderPlanterHeader(st) {
  const P = S.planter;
  const alert = P?.alert && (Date.now() - new Date(P.alert.time)) < 2 * 86400000;
  $("#planter-alert").hidden = !alert;
  $("#planter-btn").setAttribute("aria-label", "Planter" + (alert ? `: ${PL_EVENT[P.alert.type] || "alert"}` : ""));
  if (st === "planter") $("#planter-btn").setAttribute("aria-current", "page"); else $("#planter-btn").removeAttribute("aria-current");
}

function renderPlanterHome() {
  const P = S.planter;
  const zones = (P?.zones || []).map(z => `zone ${z.zone} ${fmtN(z.moisture)}% moist`).join(" · ");
  const tanks = P?.tanks?.length > 1 ? P.tanks.map(t => `${t.name} ${t.level}`).join(" · ") : P?.tank ? `tank ${P.tank}` : "";
  const t = !P?.readings ? "No readings from the planter yet. Start its bridge (see automated_planter_system/README.md)."
    : `Last report ${ago(P.last)}${zones ? " · " + zones : ""}${P.battery != null ? ` · battery ${fmtN(P.battery)}%` : ""}${tanks ? " · " + tanks : ""}${P.lastWatered ? ` · watered ${ago(P.lastWatered)}` : ""}`;
  $("#pl-stats").textContent = t;
}

function renderPlanterStep() {
  if ((!pl || (S.planter?.rev ?? null) !== plRev) && !plLoading && !plErr) loadPlanter();
  if (!pl) {
    if (changed("plMsg", "loading:" + plErr)) $("#pl-msg").innerHTML = plErr ? `<div class="notice error">${esc(plErr)}</div>` : `<p class="empty">Loading the planter…</p>`;
    return;
  }
  const msgs = [];
  // Settings changed on the planter itself (its phone page or SD card), newer than Commune's.
  (pl.boardChanges || []).forEach(c => msgs.push(`<div class="notice warn"><b>${esc(c.name)}'s settings were changed on the planter</b>
    (${c.source === "phone" ? "its phone page" : "its SD card"}${c.changedOnPlanter ? `, ${esc(when(c.changedOnPlanter))}` : ""}), so it isn't using the settings below.
    <div class="row-actions" style="margin-top:8px"><button type="button" class="btn small primary" data-pl="adopt" data-device="${esc(c.device)}">Keep the planter's settings</button>
    <button type="button" class="btn small" data-pl="resend">Send Commune's settings to it</button></div></div>`));
  if (pl.errors.length) msgs.push(`<div class="notice warn"><b>${plural(pl.errors.length, "file", "files")} from the planter couldn't be read</b>
    <ul>${pl.errors.map(x => `<li><code>${esc(x.file)}</code>: ${esc(x.error)}</li>`).join("")}</ul>
    <button type="button" class="btn small" data-pl="dismiss">Dismiss</button></div>`);
  if (!pl.total.readings && !pl.total.events) msgs.push(`<div class="notice">No readings yet. Connect the Wi-Fi bridge below, or plug in the planter's SD card and import it.</div>`);
  if (changed("plMsg", msgs.join(""))) $("#pl-msg").innerHTML = msgs.join("");

  // The zones and tanks the planter reports it has (2 zones on one tank until it reports), with your settings for each.
  const zones = pl.layout.zones.map(l => ({ ...(pl.settings.zones.find(z => z.zone === l.zone) || { zone: l.zone, name: `Zone ${l.zone}` }), tank: l.tank }));
  renderPlNow(zones);
  renderPlLinks();
  renderPlChart(zones);
  renderPlEvents(zones);
  renderPlSettings(zones);
}

function renderPlNow(zones) {
  const last = pl.readings[pl.readings.length - 1] || {};
  const lastWater = z => pl.events.filter(e => e.type === "watered" && e.zone === z).pop();
  const lastAll = pl.events.filter(e => e.type === "watered").pop();
  const tile = (label, value, sub = "", cls = "") => `<div class="card pl-tile ${cls}"><span class="eyebrow">${label}</span><b>${value}</b><small class="muted">${sub}</small></div>`;
  const tz = zones.map((s, i) => {
    const z = (last.zones || []).find(x => x.zone === s.zone);
    const w = lastWater(s.zone);
    const sched = s.mode === "schedule";
    const dry = !sched && z?.moisture != null && z.moisture < s.moistureBelow;
    const how = sched ? `On a schedule: ${fmtN(s.ml)} ml at each watering hour${s.everyDays > 1 ? `, every ${s.everyDays} days` : ""}`
      : dry ? "Dry: waters at the next watering hour" : `Waters below ${s.moistureBelow}%`;
    const from = pl.layout.tanks.length > 1 ? `From ${esc(plTankName(s.tank))} · ` : "";
    return tile(`<span class="pl-dot" style="background:${PL_COLORS[i % PL_COLORS.length]}"></span>${esc(s.name)}`, z ? `${fmtN(z.moisture)}%` : "–",
      `${from}${how}<br>${w ? `Last watered ${ago(w.time)} (${fmtN(w.ml)} ml)` : "Not watered yet"}`, dry ? "warn" : "");
  }).join("");
  const header = last.headerFull == null ? "" : last.headerFull ? "Header tank full" : "Header tank refilling";
  const lastPump = pl.events.filter(e => e.type === "pumped").pop();
  const sun = last.solarV == null ? "" : last.solarV > 4.5 ? "Solar charging" : last.solarV > 1 ? "Weak sun" : "No sun (night?)";
  const tt = pl.layout.tanks.map(({ tank: n }) => {
    const lv = (last.tanks || []).find(t => t.tank === n)?.level || (n === 1 && !last.tanks ? last.tank : null);
    const fed = zones.filter(z => z.tank === n);
    const lastUse = pl.events.filter(e => e.type === "watered" && fed.some(z => z.zone === e.zone)).pop();
    const pumped = header && n === 1;  // with the pump add-on, tank 1 is the barrel
    const sub = [pumped ? header : "", pumped && lastPump ? `pumped ${ago(lastPump.time)}` : "",
      lv && lv !== "ok" ? (pumped ? "The pump waits for rain" : "Its valves stay shut until it refills") : lastUse && !pumped ? `Last used ${ago(lastUse.time)}` : "",
      pl.layout.tanks.length > 1 && fed.length ? `Feeds ${fed.map(z => esc(z.name)).join(", ")}` : ""].filter(Boolean).join(" · ");
    return tile(esc(pumped && pl.layout.tanks.length === 1 ? "Rain barrel" : plTankName(n)), lv ? { ok: "Has water", low: "Low", empty: "Empty" }[lv] : "–", sub, lv && lv !== "ok" ? "warn" : "");
  }).join("");
  const html = tz + tt
    + tile("Battery", last.battery != null ? `${fmtN(last.battery)}%` : "–", [last.batteryV != null ? `${fmtN(last.batteryV, 2)} V` : "", sun].filter(Boolean).join(" · "),
      last.battery != null && last.battery < pl.settings.minBattery ? "warn" : "")
    + tile("Temperature", last.airTemp != null ? `${fmtN(last.airTemp, 1)}°C` : "–", last.soilTemp != null ? `Soil ${fmtN(last.soilTemp, 1)}°C` : "Air")
    + tile("Last report", last.time ? ago(last.time) : "never", last.time ? esc(when(last.time)) : "");
  if (changed("plNow", html)) $("#pl-now").innerHTML = html;
}

function plTankName(n) { return pl.settings.tanks.find(t => t.tank === n)?.name || `Drum ${n}`; }

function renderPlLinks() {
  const b = pl.bridge || {};
  if (!plBridgeShown) {  // fill the form once, so a refresh doesn't wipe what the person is typing
    $("#pl-bridge-url").value = b.url ? b.url.replace(/^http:\/\//, "").replace(/:8650$/, "") : "";
    $("#pl-bridge-key").placeholder = b.hasKey ? "saved (leave empty to keep it)" : "the bridge's --key";
    plBridgeShown = true;
  }
  const st = !b.url ? `<span class="muted">Not set up.</span>`
    : b.error ? `<span class="warn-text">${esc(b.error)}</span>${b.lastSync ? ` <span class="muted">Last synced ${ago(b.lastSync)}.</span>` : ""}`
    : b.lastSync ? `Connected. Last synced ${ago(b.lastSync)}.` : `<span class="muted">Not synced yet.</span>`;
  if (changed("plBridgeSt", st)) $("#pl-bridge-status").innerHTML = st;
  const cards = (pl.cards || []).map(c => `<div class="pl-card"><div><b>${esc(c.name)}</b><small class="muted">${plural(c.logs, "log file", "log files")}${c.settings ? " · has settings" : ""}</small></div>
      <div class="row-actions"><button type="button" class="btn small primary" data-pl="card-import" data-path="${esc(c.path)}">Import readings</button>
      <button type="button" class="btn small" data-pl="card-write" data-path="${esc(c.path)}">Write settings to card</button></div></div>`).join("")
    || `<p class="muted small">No planter card found. Plug it in and click <b>Check for new readings</b>.</p>`;
  if (changed("plCards", cards)) $("#pl-cards").innerHTML = cards;
}

function renderPlChart(zones) {
  const ranges = [["1", "24 hours"], ["7", "7 days"], ["30", "30 days"]];
  const seg = ranges.map(([v, l]) => `<button type="button" data-pl="range" data-v="${v}" aria-pressed="${plRange === v}"><b>${l}</b></button>`).join("");
  if (changed("plRange", seg)) $("#pl-range").innerHTML = seg;
  const end = Date.now(), start = end - Number(plRange) * 86400000;
  const rs = pl.readings.filter(r => new Date(r.time) >= start);
  // Drawn at the box's real width, so the labels stay readable on a phone.
  const W = Math.max(300, Math.min(1400, Math.round($("#pl-chart").clientWidth || 720))), H = W < 500 ? 200 : 240, L = 36, R = 8, T = 10, B = 26;
  const x = t => L + (W - L - R) * (t - start) / (end - start), y = v => T + (H - T - B) * (1 - v / 100);
  let svg = "";
  [0, 25, 50, 75, 100].forEach(v => { svg += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" class="pl-grid"/><text x="${L - 6}" y="${y(v) + 4}" class="pl-axis" text-anchor="end">${v}%</text>`; });
  const fmtX = t => new Date(t).toLocaleString([], plRange === "1" ? { hour: "numeric" } : { month: "short", day: "numeric" });
  for (let i = 0; i <= 4; i++) { const t = start + (end - start) * i / 4; svg += `<text x="${x(t)}" y="${H - 6}" class="pl-axis" text-anchor="${i === 0 ? "start" : i === 4 ? "end" : "middle"}">${esc(fmtX(t))}</text>`; }
  zones.forEach((s, i) => {
    i %= PL_COLORS.length;
    const pts = rs.map(r => [new Date(r.time).getTime(), (r.zones || []).find(z => z.zone === s.zone)?.moisture]).filter(p => p[1] != null);
    if (s.mode !== "schedule") svg += `<line x1="${L}" x2="${W - R}" y1="${y(s.moistureBelow)}" y2="${y(s.moistureBelow)}" class="pl-threshold" style="stroke:${PL_COLORS[i]}"/>`;
    if (pts.length) svg += `<polyline fill="none" stroke-width="2" style="stroke:${PL_COLORS[i]}" points="${pts.map(([t, v]) => `${x(t).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`;
    pl.events.filter(e => e.type === "watered" && e.zone === s.zone && new Date(e.time) >= start)
      .forEach(e => { svg += `<circle cx="${x(new Date(e.time).getTime()).toFixed(1)}" cy="${H - B - 4}" r="4" style="fill:${PL_COLORS[i]}"><title>${esc(s.name)} watered ${esc(when(e.time))}: ${fmtN(e.ml)} ml</title></circle>`; });
  });
  const legend = zones.map((s, i) => `<span><span class="pl-dot" style="background:${PL_COLORS[i % PL_COLORS.length]}"></span>${esc(s.name)}</span>`).join("")
    + `<span class="muted">Dashed line: waters below this (soil-moisture zones) · dots: watered</span>`;
  const html = rs.length
    ? `<svg class="pl-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Soil moisture for each zone">${svg}</svg><div class="pl-legend small">${legend}</div>`
    : `<p class="empty">No readings in this time.</p>`;
  if (changed("plChart", html)) $("#pl-chart").innerHTML = html;
}

function renderPlEvents(zones) {
  const name = z => zones.find(s => s.zone === z)?.name || (z ? `Zone ${z}` : "");
  const evs = pl.events.slice(-60).reverse();
  const html = evs.length ? `<ul class="pl-events">${evs.map(e => `<li class="${PL_ALERT.has(e.type) ? "warn" : ""}">
      <b>${esc(PL_EVENT[e.type] || e.type)}${e.zone ? ` · ${esc(name(e.zone))}` : ""}${e.tank && !e.zone ? ` · ${esc(plTankName(e.tank))}` : ""}${e.type === "watered" && e.ml != null ? ` · ${fmtN(e.ml)} ml` : ""}${e.state ? ` · ${esc(e.state)}` : ""}</b>
      <small class="muted">${esc(when(e.time))}${e.reason ? ` · ${esc(e.reason)}` : ""}</small></li>`).join("")}</ul>`
    : `<p class="empty">Nothing yet.</p>`;
  if (changed("plEvents", html)) $("#pl-events").innerHTML = html;
}

function renderPlSettings(zones) {
  if (plDirty && $("#pl-settings").childElementCount) return;
  const s = pl.settings;
  const opts = pl.finds.map(f => `<option value="${esc(f.upload + "/" + f.entry)}">${esc(f.name)}${f.scientific ? ` (${esc(f.scientific)})` : ""}</option>`).join("");
  const grow = z => (pl.growing[String(z.zone)] || []).map(g => `<li><div><b>${esc(g.name)}</b>${g.scientific ? ` <i class="muted">${esc(g.scientific)}</i>` : ""}
      ${["watering", "sunlight", "climate"].filter(k => g[k]).map(k => `<small class="muted"><b>${k[0].toUpperCase() + k.slice(1)}:</b> ${esc(g[k])}</small>`).join("")}</div>
      <button type="button" class="btn small ghost" data-pl="ungrow" data-zone="${z.zone}" data-key="${esc(g.find.upload + "/" + g.find.entry)}" aria-label="Remove ${esc(g.name)}">Remove</button></li>`).join("");
  const many = pl.layout.tanks.length > 1;
  const zoneHtml = zones.map((z, i) => `<fieldset class="pl-zone">
    <legend><span class="pl-dot" style="background:${PL_COLORS[i % PL_COLORS.length]}"></span>Zone ${z.zone}${many ? ` <span class="muted small">· from ${esc(plTankName(z.tank))}</span>` : ""}</legend>
    <div class="pl-grid">
      <label>Name<input name="z${z.zone}-name" value="${esc(z.name)}" maxlength="60"></label>
      <label class="pl-check"><input type="checkbox" name="z${z.zone}-enabled" ${z.enabled ? "checked" : ""}> Water this zone</label>
      <label>When to water<select name="z${z.zone}-mode">
        <option value="moisture" ${z.mode !== "schedule" ? "selected" : ""}>When the soil is dry</option>
        <option value="schedule" ${z.mode === "schedule" ? "selected" : ""}>On a schedule</option></select></label>
      <label class="pl-moist" ${z.mode === "schedule" ? "hidden" : ""}>Water when moisture is below (%)<input type="number" name="z${z.zone}-moistureBelow" min="0" max="100" value="${z.moistureBelow}"></label>
      <label class="pl-sched" ${z.mode === "schedule" ? "" : "hidden"}>Every how many days (1 = daily, 7 = weekly)<input type="number" name="z${z.zone}-everyDays" min="1" max="14" value="${z.everyDays}"></label>
      <label>Water per watering (ml)<input type="number" name="z${z.zone}-ml" min="0" max="20000" step="10" value="${z.ml}"></label>
      <label>Most per day (ml)<input type="number" name="z${z.zone}-maxMlPerDay" min="0" max="100000" step="50" value="${z.maxMlPerDay}"></label>
    </div>
    <div class="pl-growing"><span class="small"><b>Growing here</b> (from your field identification finds)</span>
      <ul>${grow(z) || `<li class="muted small">Nothing linked yet.</li>`}</ul>
      ${pl.finds.length ? `<div class="row-actions"><select data-zone="${z.zone}" aria-label="Add a plant to zone ${z.zone}"><option value="">Add a plant you identified…</option>${opts}</select>
        <button type="button" class="btn small" data-pl="grow" data-zone="${z.zone}">Add</button></div>`
        : `<small class="muted">Identify plants with the field identifier to link them here.</small>`}
    </div></fieldset>`).join("");
  const html = `<div class="pl-grid">
      <label>Watering hours (0–23: "7, 19", or "6-20" for every hour)<input name="wateringHours" value="${esc(plHoursText(s.wateringHours))}"></label>
      <label>Don't water below battery (%)<input type="number" name="minBattery" min="0" max="90" value="${s.minBattery}"></label>
      <label>Take a reading every (minutes)<input type="number" name="wakeMinutes" min="5" max="720" value="${s.wakeMinutes}"></label>
      <label>Report after this many readings<input type="number" name="reportEveryWakes" min="1" max="24" value="${s.reportEveryWakes}"></label>
      ${pl.layout.tanks.map(({ tank: n }) => `<label>${many ? `Name of tank ${n}` : "Name of the rain tank"}<input name="t${n}-name" value="${esc(plTankName(n))}" maxlength="60"></label>`).join("")}
    </div>${zoneHtml}
    <div class="row-actions"><button type="submit" class="btn primary">Save settings</button><span class="small muted" id="pl-saved"></span></div>`;
  if (changed("plSettings", html)) $("#pl-settings").innerHTML = html;
}

// Shows watering hours compactly: runs of 3 or more consecutive hours as "6-20".
function plHoursText(hours) {
  const out = [];
  for (let i = 0; i < hours.length;) {
    let j = i;
    while (j + 1 < hours.length && hours[j + 1] === hours[j] + 1) j++;
    out.push(j - i >= 2 ? `${hours[i]}-${hours[j]}` : hours.slice(i, j + 1).join(", "));
    i = j + 1;
  }
  return out.join(", ");
}

function plFormSettings() {
  const f = $("#pl-settings"), v = n => f.elements[n]?.value;
  // "7, 19" or ranges like "6-20" (every hour from 6:00 to 20:00).
  const hours = [];
  String(v("wateringHours") || "").split(/[,;\s]+/).filter(Boolean).forEach(part => {
    const m = part.match(/^(\d{1,2})(?:-(\d{1,2}))?$/);
    if (!m) return;
    const a = Number(m[1]), b = m[2] != null ? Number(m[2]) : a;
    for (let h = Math.min(a, b); h <= Math.max(a, b) && h <= 23; h++) hours.push(h);
  });
  return {
    wateringHours: hours, minBattery: Number(v("minBattery")), wakeMinutes: Number(v("wakeMinutes")), reportEveryWakes: Number(v("reportEveryWakes")),
    tanks: pl.settings.tanks.map(t => f.elements[`t${t.tank}-name`] ? { tank: t.tank, name: v(`t${t.tank}-name`) } : t),
    zones: pl.settings.zones.map(z => f.elements[`z${z.zone}-name`] ? {
      zone: z.zone, name: v(`z${z.zone}-name`), enabled: f.elements[`z${z.zone}-enabled`].checked,
      mode: v(`z${z.zone}-mode`), everyDays: Number(v(`z${z.zone}-everyDays`)),
      moistureBelow: Number(v(`z${z.zone}-moistureBelow`)), ml: Number(v(`z${z.zone}-ml`)), maxMlPerDay: Number(v(`z${z.zone}-maxMlPerDay`)),
    } : z),
  };
}

async function plGrow(zone, keys) {
  const links = keys.map(k => { const [upload, ...rest] = k.split("/"); return { upload, entry: rest.join("/") }; });
  try {
    const r = await api("/api/planter/grow", { zone, links });
    if (plDirty) pl.settings = { ...pl.settings, ...plFormSettings() };  // keep unsaved edits on screen while redrawing
    const dirty = plDirty;
    pl.growing = r.growing; plDirty = false; sigs.plSettings = null; render(); plDirty = dirty;
    if (dirty) $("#pl-saved").textContent = "Unsaved changes";
  }
  catch (e) { notice(esc(e.message), "error"); }
}

$("#pl-settings").addEventListener("input", e => {
  plDirty = true; $("#pl-saved").textContent = "Unsaved changes";
  const sel = e.target.closest('select[name$="-mode"]');
  if (sel) {  // soil-moisture zones need a threshold; scheduled zones need how often
    const box = sel.closest(".pl-zone");
    box.querySelector(".pl-moist").hidden = sel.value === "schedule";
    box.querySelector(".pl-sched").hidden = sel.value !== "schedule";
  }
});
$("#pl-settings").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const r = await api("/api/planter/settings", { settings: plFormSettings() });
    pl.settings = r.settings; plDirty = false; sigs.plSettings = null; render();
    $("#pl-saved").textContent = "Saved. The planter picks these up the next time it reports in.";
  } catch (ex) { notice(esc(ex.message), "error"); }
});
$("#pl-check").addEventListener("click", async () => {
  try {
    const r = await api("/api/planter/import", {});
    let n = r.imported.length;
    if (pl?.bridge?.url) { const sy = await api("/api/planter/sync", {}); n += sy.imported; }
    notice(n ? `Imported ${plural(n, "report", "reports")} from the planter.` : r.errors.length ? esc(r.errors.join("; ")) : "Nothing new from the planter.", r.errors.length ? "warn" : "");
  } catch (e) { notice(esc(e.message), "error"); }
  plRev = null; pl = null; await refresh();
});
$("#pl-bridge").addEventListener("submit", async e => {
  e.preventDefault();
  const f = e.target;
  try {
    const r = await api("/api/planter/bridge", { url: f.url.value, key: f.key.value });
    f.key.value = "";
    notice(f.url.value ? `Connected to the bridge${r.imported ? `: imported ${plural(r.imported, "report", "reports")}` : ""}.` : "The bridge is turned off.");
  } catch (ex) { notice(esc(ex.message), "error"); }
  plBridgeShown = false; plRev = null; pl = null; await refresh();
});
$("#pl-sync").addEventListener("click", async () => {
  try { const r = await api("/api/planter/sync", {}); notice(r.imported ? `Imported ${plural(r.imported, "report", "reports")} from the bridge.` : "Synced: nothing new from the bridge."); }
  catch (e) { notice(esc(e.message), "error"); }
  plRev = null; pl = null; await refresh();
});
$("#step-planter").addEventListener("click", async e => {
  const b = e.target.closest("[data-pl]");
  if (!b) return;
  const act = b.dataset.pl, zone = Number(b.dataset.zone);
  const current = () => (pl.growing[String(zone)] || []).map(g => g.find.upload + "/" + g.find.entry);
  if (act === "range") { plRange = b.dataset.v; try { localStorage.setItem("commune.plRange", plRange); } catch {} render(); }
  else if (act === "grow") {
    const key = $(`#pl-settings select[data-zone="${zone}"]`).value;
    if (key && !current().includes(key)) await plGrow(zone, [...current(), key]);
  }
  else if (act === "ungrow") await plGrow(zone, current().filter(k => k !== b.dataset.key));
  else if (act === "card-import") {
    try { const r = await api("/api/planter/card/import", { path: b.dataset.path });
      notice(`Imported ${plural(r.readings, "reading", "readings")} and ${plural(r.events, "event", "events")} from the card${r.skipped ? ` (${r.skipped} lines without a time were skipped)` : ""}.`); }
    catch (ex) { notice(esc(ex.message), "error"); }
    plRev = null; pl = null; await refresh();
  }
  else if (act === "card-write") {
    try { await api("/api/planter/card/write", { path: b.dataset.path }); notice("Settings written to the card. Put it back in the planter: it uses them at its next wake."); }
    catch (ex) { notice(esc(ex.message), "error"); }
  }
  else if (act === "adopt" || act === "resend") {
    try { await api("/api/planter/board", { action: act, device: b.dataset.device }); notice(act === "adopt" ? "Commune now uses the planter's settings." : "Commune's settings will reach the planter at its next report, or write them to its SD card."); }
    catch (ex) { notice(esc(ex.message), "error"); }
    plDirty = false; sigs.plSettings = null; plRev = null; pl = null; await refresh();
  }
  else if (act === "dismiss") { try { await api("/api/planter/dismiss", {}); pl.errors = []; render(); } catch (ex) { notice(esc(ex.message), "error"); } }
});
