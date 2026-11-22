// The phone setup page. Press the setup button: the planter opens its own Wi-Fi hotspot ("Planter-XXXXXX"), with
// no router or internet involved. Join it from a phone and the settings page opens (or browse to 192.168.4.1).
// It shows the latest reading, sets the clock from the phone, changes the watering settings and can water a zone
// by hand. The hotspot closes when you tap Done, or after SETUP_MINUTES with no one using it.
// Included by main.cpp, which defines everything used here.
#pragma once
#include <DNSServer.h>
#include <WebServer.h>

static const char PHONE_PAGE[] PROGMEM = R"HTML(<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Planter setup</title>
<style>
:root{--bg:#f3f5f1;--card:#fff;--ink:#1f2a26;--muted:#5b6a64;--line:#d5ddd7;--accent:#2e7a64;--on:#fff;--warn:#8a4a2b}
@media(prefers-color-scheme:dark){:root{--bg:#121815;--card:#1b231f;--ink:#e3ebe6;--muted:#9db0a7;--line:#2d3a34;--accent:#5cc78a;--on:#0d1a14;--warn:#ef8a6f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif;padding:16px}
main{max-width:560px;margin:0 auto;display:flex;flex-direction:column;gap:14px}h1{font-size:24px;margin:0}h2{font-size:17px;margin:0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;flex-direction:column;gap:10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}label{display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:600}
input,select,button{font:inherit;padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink);min-height:44px;width:100%}
button{background:var(--accent);color:var(--on);border:0;font-weight:600}button.ghost{background:none;color:var(--ink);border:1px solid var(--line)}
.muted{color:var(--muted);font-size:14px}.warn{color:var(--warn)}.row{display:flex;gap:10px}.row>*{flex:1}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.tile{background:var(--bg);border-radius:10px;padding:8px}.tile b{display:block;font-size:20px}
[hidden]{display:none!important}
</style></head><body><main>
<h1>Planter setup</h1><p class="muted" id="who">Connecting…</p>
<div class="card"><h2>Now</h2><div class="tiles" id="now"></div><p class="muted" id="clock"></p></div>
<form class="card" id="f"><h2>Watering</h2>
<div class="grid"><label>Watering hours<input name="hours" placeholder="7, 19 or 6-20"></label>
<label>Don't water below battery (%)<input name="minBattery" type="number" min="0" max="90"></label></div>
<div id="zones"></div>
<button type="submit">Save settings</button><p class="muted" id="saved"></p></form>
<div class="card"><h2>Water by hand</h2><div class="row"><select id="wz"></select><input id="wml" type="number" value="500" min="50" max="5000" step="50"></div>
<button type="button" class="ghost" id="wbtn">Water now (ml)</button><p class="muted" id="wmsg"></p></div>
<button type="button" class="ghost" id="done">Done: close the hotspot</button>
<p class="muted">Changes made here stay until the settings are changed in Commune. The SD card's settings file is updated too.</p>
</main><script>
const $=s=>document.querySelector(s),f=$("#f");let S;
const hoursText=h=>{const o=[];for(let i=0;i<h.length;){let j=i;while(j+1<h.length&&h[j+1]===h[j]+1)j++;o.push(j-i>=2?h[i]+"-"+h[j]:h.slice(i,j+1).join(", "));i=j+1}return o.join(", ")};
const parseHours=t=>{const o=[];t.split(/[,;\s]+/).forEach(p=>{const m=p.match(/^(\d{1,2})(?:-(\d{1,2}))?$/);if(!m)return;const a=+m[1],b=m[2]!=null?+m[2]:a;for(let h=Math.min(a,b);h<=Math.max(a,b)&&h<24;h++)o.push(h)});return o};
async function post(u,b){const r=await fetch(u,{method:"POST",body:JSON.stringify(b||{})});if(!r.ok)throw new Error(await r.text());return r.json()}
function show(d){S=d;const r=d.reading,z=r.zones||[];
$("#who").textContent=d.name+" · "+d.device+" · SD card "+(d.sd?"in":"missing")+" · clock module "+(d.rtc?"found":"missing");
const L=d.settings.layout||{},tanks=r.tanks||[{tank:1,level:r.tank}],one=tanks.length<2,tn=t=>one?"Tank":"Tank "+t,feed=n=>((L.zones||[]).find(x=>x.zone===n)||{}).tank;
$("#now").innerHTML=z.map(x=>`<div class="tile">Zone ${x.zone}<b>${x.moisture!=null?x.moisture+"%":"–"}</b></div>`).join("")+
tanks.map(t=>`<div class="tile">${tn(t.tank)}<b class="${t.level==="ok"?"":"warn"}">${t.level==="ok"?"OK":"Low"}</b></div>`).join("")+`<div class="tile">Battery<b>${r.battery!=null?r.battery+"%":"–"}</b></div>`+
(r.airTemp!=null?`<div class="tile">Air<b>${r.airTemp.toFixed(1)}°C</b></div>`:"");
$("#clock").textContent="Planter clock: "+new Date(d.now*1000).toLocaleString();
const s=d.settings;f.hours.value=hoursText(s.wateringHours);f.minBattery.value=s.minBattery;
$("#zones").innerHTML=s.zones.map(x=>`<div class="card"><h2>Zone ${x.zone}${!one&&feed(x.zone)?` <span class="muted">· from tank ${feed(x.zone)}</span>`:""}</h2><div class="grid">
<label>When to water<select name="mode${x.zone}"><option value="moisture">Soil is dry</option><option value="schedule">Schedule</option></select></label>
<label>Water this zone<select name="en${x.zone}"><option value="1">Yes</option><option value="0">No</option></select></label>
<label data-m="${x.zone}">Water below moisture (%)<input name="below${x.zone}" type="number" min="0" max="100" value="${x.moistureBelow}"></label>
<label data-s="${x.zone}">Every how many days<input name="days${x.zone}" type="number" min="1" max="14" value="${x.everyDays}"></label>
<label>Water each time (ml)<input name="ml${x.zone}" type="number" min="0" max="20000" step="50" value="${x.ml}"></label>
<label>Most per day (ml)<input name="max${x.zone}" type="number" min="0" max="100000" step="50" value="${x.maxMlPerDay}"></label></div></div>`).join("");
s.zones.forEach(x=>{f["mode"+x.zone].value=x.mode;f["en"+x.zone].value=x.enabled?"1":"0"});toggle();
$("#wz").innerHTML=s.zones.map(x=>`<option value="${x.zone}">Zone ${x.zone}</option>`).join("")}
function toggle(){S.settings.zones.forEach(x=>{const sch=f["mode"+x.zone].value==="schedule";document.querySelector(`[data-m="${x.zone}"]`).hidden=sch;document.querySelector(`[data-s="${x.zone}"]`).hidden=!sch})}
f.addEventListener("change",e=>{if(e.target.name&&e.target.name.startsWith("mode"))toggle()});
f.addEventListener("submit",async e=>{e.preventDefault();const s={wateringHours:parseHours(f.hours.value),minBattery:+f.minBattery.value,
zones:S.settings.zones.map(x=>({zone:x.zone,enabled:f["en"+x.zone].value==="1",mode:f["mode"+x.zone].value,everyDays:+f["days"+x.zone].value,
moistureBelow:+f["below"+x.zone].value,ml:+f["ml"+x.zone].value,maxMlPerDay:+f["max"+x.zone].value}))};
try{show(await post("/api/settings",s));$("#saved").textContent="Saved on the planter."}catch(x){$("#saved").textContent="Couldn't save: "+x.message}});
$("#wbtn").onclick=async()=>{$("#wmsg").textContent="Watering… the valve takes a few seconds to open and close.";$("#wbtn").disabled=true;
try{const d=await post("/api/water",{zone:+$("#wz").value,ml:+$("#wml").value});$("#wmsg").textContent=`Done: ${d.ml} ml in ${d.seconds} s.`}catch(x){$("#wmsg").textContent=x.message}$("#wbtn").disabled=false};
$("#done").onclick=async()=>{await post("/api/done");document.body.innerHTML='<main><h1>Hotspot closed</h1><p class="muted">The planter is back to its normal schedule. You can reconnect your phone to your usual Wi-Fi.</p></main>'};
(async()=>{try{show(await post("/api/time",{now:Math.floor(Date.now()/1000),utcOffset:-new Date().getTimezoneOffset()*60}))}catch(x){$("#who").textContent="Couldn't reach the planter: "+x.message}})();
</script></body></html>)HTML";

WebServer web(80);
DNSServer dns;
bool phoneDone = false;
uint32_t phoneLastUse = 0;
Reading *phoneReading = nullptr;

void phoneSendStatus() {
  JsonDocument d;
  d["device"] = deviceId();
  d["name"] = DEVICE_NAME;
  d["firmware"] = FIRMWARE;
  d["now"] = nowSec();
  d["timeValid"] = st.timeValid;
  d["sd"] = sdOk;
  d["rtc"] = rtcOk;
  fillReading(d["reading"].to<JsonObject>(), *phoneReading);
  settingsToJson(d["settings"].to<JsonObject>());
  String out;
  serializeJson(d, out);
  web.send(200, "application/json", out);
}

bool phoneBody(JsonDocument &d) {
  phoneLastUse = millis();
  if (deserializeJson(d, web.arg("plain"))) { web.send(400, "text/plain", "That request wasn't valid JSON"); return false; }
  return true;
}

void runPhonePage(Reading &r) {
  phoneReading = &r;
  char ssid[24];
  snprintf(ssid, sizeof ssid, "Planter-%s", deviceId().substring(3).c_str());
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, SETUP_PASSWORD);
  IPAddress ip = WiFi.softAPIP();
  dns.start(53, "*", ip);  // every name points at the planter, so the phone opens the page by itself
  digitalWrite(PIN_STATUS_LED, HIGH);
  log_i("Setup hotspot %s open at %s", ssid, ip.toString().c_str());

  web.on("/", HTTP_GET, [] { phoneLastUse = millis(); web.send_P(200, "text/html", PHONE_PAGE); });
  web.on("/api/status", HTTP_GET, [] { phoneLastUse = millis(); phoneSendStatus(); });
  web.on("/api/time", HTTP_POST, [] {
    JsonDocument d;
    if (!phoneBody(d)) return;
    setClock(d["now"] | 0);  // the phone's clock is right, and the clock module keeps it from now on
    int32_t off = d["utcOffset"] | cfg.utcOffset;
    if (off != cfg.utcOffset) { cfg.utcOffset = off; commitSettings(String(settingsSource).c_str()); }
    phoneSendStatus();
  });
  web.on("/api/settings", HTTP_POST, [] {
    JsonDocument d;
    if (!phoneBody(d)) return;
    if (!applySettings(d.as<JsonVariantConst>())) { web.send(400, "text/plain", "No settings in the request"); return; }
    commitSettings("phone");
    phoneSendStatus();
  });
  web.on("/api/water", HTTP_POST, [] {
    JsonDocument d;
    if (!phoneBody(d)) return;
    int z = (d["zone"] | 0) - 1, ml = constrain(d["ml"] | 0, 0, 5000);
    if (z < 0 || z >= ZONE_COUNT || ml <= 0) { web.send(400, "text/plain", "Pick a zone and an amount"); return; }
    float seconds = 0, given = water(z, ml, seconds);
    st.mlToday[z] += (uint32_t)given;
    addEvent(EV_WATERED, z + 1, R_BY_HAND, 0, 0, (uint16_t)given, seconds);
    phoneLastUse = millis();
    web.send(200, "application/json", String("{\"ml\":") + (int)given + ",\"seconds\":" + (int)seconds + "}");
  });
  web.on("/api/done", HTTP_POST, [] { phoneDone = true; web.send(200, "application/json", "{}"); });
  web.onNotFound([] { web.sendHeader("Location", "http://192.168.4.1/", true); web.send(302, "text/plain", ""); });
  web.begin();

  phoneLastUse = millis();
  while (!phoneDone && millis() - phoneLastUse < SETUP_MINUTES * 60000UL) {
    dns.processNextRequest();
    web.handleClient();
    delay(2);
  }
  delay(300);  // let the last reply reach the phone
  web.stop();
  dns.stop();
  WiFi.softAPdisconnect(true);
  wifiOff();
  digitalWrite(PIN_STATUS_LED, LOW);
}
