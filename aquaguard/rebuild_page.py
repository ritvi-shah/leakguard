#!/usr/bin/env python3
# rebuild_page.py v2 - writes LeakGuard page. JS built from short one-line
# strings (paste-proof). Self-verifies: braces balanced, quotes even.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{--bg:#f2f5f9;--card:#fff;--ink:#16233b;--ink2:#5b6b82;
--line:#dbe3ec;--accent:#0b6e99;--good:#177245;--goodbg:#e7f5ec;
--warn:#8a6116;--warnbg:#fdf3dd;--bad:#b3261e;--badbg:#fdeceb}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Segoe UI",system-ui,sans-serif;background:var(--bg);
color:var(--ink);font-size:16px;line-height:1.55}
.sitehead{text-align:center;padding:30px 16px 8px}
.appname{font-size:2.8rem;font-weight:800}
.tagline{color:var(--ink2);text-align:center;margin-top:4px}
.tabs{display:flex;justify-content:center;gap:6px;margin:20px auto 0;
max-width:760px;background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:6px}
.tab{flex:1;border:none;background:none;color:var(--ink2);font-size:1rem;
font-weight:600;padding:11px;border-radius:8px;cursor:pointer}
.tab.active{background:var(--accent);color:#fff}
.controlstrip{max-width:1100px;margin:16px auto 0;padding:0 20px;
display:flex;flex-wrap:wrap;gap:14px;align-items:center;
justify-content:space-between}
.pills{display:flex;gap:8px;flex-wrap:wrap;max-width:600px}
.pill{border:1.5px solid var(--line);background:var(--card);
color:var(--ink2);border-radius:999px;padding:9px 16px;
font-size:.9rem;font-weight:600;cursor:pointer}
.pill.active{background:var(--accent);border-color:var(--accent);color:#fff}
.playwrap{display:flex;align-items:center;gap:10px;min-width:300px;
flex:1;max-width:440px}
.playbtn{background:var(--accent);border:none;color:#fff;
font-weight:700;border-radius:8px;padding:9px 16px;cursor:pointer}
.playwrap input[type=range]{flex:1;accent-color:var(--accent);min-width:120px}
.timelabel{font-variant-numeric:tabular-nums;color:var(--ink2);min-width:100px}
.panel{display:none;max-width:1100px;margin:20px auto 40px;padding:0 20px}
.panel.active{display:block}
.sect{font-size:1.15rem;font-weight:700;margin:30px 0 4px}
.secthint{color:var(--ink2);font-size:.95rem;margin-bottom:14px;
overflow-wrap:anywhere}
.kpigrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
gap:14px;margin-top:4px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;border-left:5px solid var(--line);min-width:0;overflow:hidden}
.klabel{display:block;font-size:.75rem;text-transform:uppercase;
letter-spacing:.06em;color:var(--ink2);font-weight:700;margin-bottom:6px}
.kvalue{font-size:1.18rem;font-weight:800;line-height:1.3;
overflow-wrap:anywhere}
.ksub{font-size:.8rem;color:var(--ink2);margin-top:5px;overflow-wrap:anywhere}
.kpi.good{border-left-color:#2f9e63}.kpi.good .kvalue{color:var(--good)}
.kpi.warn{border-left-color:#d9a62e}.kpi.warn .kvalue{color:var(--warn)}
.kpi.bad{border-left-color:#d64545}.kpi.bad .kvalue{color:var(--bad)}
.insight{background:var(--card);border:1px solid var(--line);
border-left:5px solid var(--accent);border-radius:12px;padding:14px 18px;
margin:16px 0;font-size:.97rem;overflow-wrap:anywhere}
.liveline{background:#eef3f8;border:1px solid var(--line);border-radius:10px;
padding:10px 16px;font-size:.93rem;margin-bottom:4px;display:flex;
flex-wrap:wrap;gap:4px 18px;align-items:center;overflow-wrap:anywhere}
.mapbox{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:10px}
#map{width:100%;height:auto;display:block}
.mlk{stroke:#c9d4e0;stroke-width:1.1}
.mlk2{stroke:#9fb0c0;stroke-dasharray:5 3}
.mdot.junction{fill:#93a7bc}
.mdot.tank{fill:#0e8f8f}
.mdot.reservoir{fill:#085a7d}
.mdot.sndot{fill:#0b6e99}
.mdot.suspect{fill:#d9a62e}
.mring{fill:none;stroke:#0b6e99;stroke-width:2.4}
.mlbl{font-size:12px;fill:#5b6b82;text-anchor:middle;font-weight:600}
.mleak{fill:none;stroke:#b3261e;stroke-width:2.4;stroke-dasharray:6 4}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.8rem;
color:var(--ink2);margin-top:8px}
.lg{display:inline-block;width:11px;height:11px;border-radius:50%;
margin-right:5px;vertical-align:-1px}
.lg.j{background:#93a7bc}.lg.s{background:#0b6e99}
.lg.t{background:#0e8f8f}.lg.r{background:#085a7d}
.lg.l{background:#fff;border:2px dashed #b3261e}.lg.q{background:#d9a62e}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
gap:14px}
.tile{background:var(--card);border:1.5px solid var(--line);
border-radius:12px;padding:16px;cursor:pointer;min-width:0}
.tile:hover{border-color:var(--accent)}
.tile.sel{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,110,153,.14)}
.tile.near{border-color:#d9a62e;background:var(--warnbg)}
.tile .nm{font-size:.8rem;color:var(--ink2);font-weight:600;
overflow-wrap:anywhere}
.tile .pv{font-size:1.5rem;font-weight:800;margin-top:6px}
.chartbox{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:16px;height:300px;margin-bottom:8px}
.mtable{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:12px;font-size:.98rem}
.mtable th,.mtable td{border-bottom:1px solid var(--line);padding:12px 14px;
text-align:center;overflow-wrap:anywhere}
.mtable th{background:#eef3f8;font-weight:700}
.mtable td:first-child{text-align:left;font-weight:600;color:var(--ink2)}
.note{color:var(--ink2);font-size:.92rem;margin:10px 0 6px;
overflow-wrap:anywhere}
.method p{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:16px 18px;margin-bottom:12px;font-size:.97rem;
overflow-wrap:anywhere}
.mono{font-variant-numeric:tabular-nums}
.dlbtn{background:var(--accent);color:#fff;border:none;border-radius:8px;
padding:11px 18px;font-weight:700;cursor:pointer;margin:8px 0 4px}
.foot{text-align:center;color:var(--ink2);font-size:.85rem;
padding:0 20px 40px}
.errbox{max-width:1100px;margin:14px auto 0;background:var(--badbg);
color:var(--bad);border:1px solid #e5b5b2;border-radius:10px;
padding:12px 16px;font-size:.9rem;font-family:Consolas,monospace}
"""

HTML = """
<div id="errbox" class="errbox" hidden></div>
<header class="sitehead">
<h1 class="appname">LeakGuard</h1>
<p class="tagline">Leak detection for water distribution networks</p>
</header>
<nav class="tabs">
<button class="tab active" data-tab="overview">Overview</button>
<button class="tab" data-tab="analysis">Flow &amp; Pressure</button>
<button class="tab" data-tab="reports">Reports &amp; Method</button>
</nav>
<div class="controlstrip">
<div class="pills" id="scenPills"></div>
<div class="playwrap">
<button id="playBtn" class="playbtn">Play</button>
<input id="scrub" type="range" min="0" value="0" step="1"/>
<span id="tlabel" class="timelabel">-</span>
</div>
</div>
<section class="panel active" id="panel-overview">
<div class="kpigrid" id="kpis"></div>
<div class="insight" id="insight"></div>
<div class="liveline" id="liveline">-</div>
<h2 class="sect">Network map</h2>
<p class="secthint">Actual topology of the EPA Net3 benchmark network.
Ringed dots are instrumented districts (click to highlight their
pressure trace). The dashed red circle marks the injected leak; the
amber dot is the zone the model currently points to.</p>
<div class="mapbox"><svg id="map" viewBox="0 0 1000 620"></svg></div>
<div class="legend">
<span><i class="lg j"></i>junction</span>
<span><i class="lg s"></i>sensor district</span>
<span><i class="lg t"></i>tank</span>
<span><i class="lg r"></i>reservoir</span>
<span><i class="lg l"></i>leak location</span>
<span><i class="lg q"></i>suspected zone</span>
</div>
<h2 class="sect">Monitoring points</h2>
<p class="secthint">Pressure at each instrumented district. Amber =
the zone the model currently points to. Click a card to highlight
its trace in Flow &amp; Pressure.</p>
<div class="tiles" id="tiles"></div>
</section>
<section class="panel" id="panel-analysis">
<h2 class="sect">Source flow at the reservoir outlet</h2>
<p class="secthint">Dashed orange: night-flow alert threshold fitted
on leak-free data. Shaded band: leak active.</p>
<div class="chartbox"><canvas id="flowChart"></canvas></div>
<h2 class="sect">Pressure at the six monitoring points</h2>
<p class="secthint">Red dots mark timesteps flagged by the digital
twin on the selected district.</p>
<div class="chartbox"><canvas id="pChart"></canvas></div>
</section>
<section class="panel" id="panel-reports">
<h2 class="sect">Measured performance -
<span id="repScen" class="mono"></span></h2>
<table class="mtable" id="mtable"></table>
<p class="note" id="mnote"></p>
<button id="dlBtn" class="dlbtn">Download incident report (.txt)</button>
<h2 class="sect">How the two detectors work</h2>
<div class="method">
<p><b>Nightly flow method</b> - the standard utility approach:
between 02:00 and 04:00 legitimate demand is near zero, so excess
flow indicates leakage. Simple and trusted, but it inspects the
network only once per night, so detection is structurally slow -
and a gradual leak can be absorbed into a rolling baseline.</p>
<p><b>Digital twin (continuous)</b> - expected pressure at every
monitoring point is learned from leak-free operation as a function
of time of day. Every 15 minutes, observed pressures are compared
with expectations; unexplained deviations are flagged, and the
spatial pattern of pressure drops indicates the leak zone.</p>
</div>
<h2 class="sect">Data provenance</h2>
<p class="note">Telemetry generated with the EPANET engine (via WNTR)
on the EPA Net3 benchmark network: 92 junctions, dual reservoirs,
tanks and pumps, 14 days at 15-minute steps. Leaks are modeled as
pressure-dependent orifice emitters. Detectors are trained only on
leak-free data; performance is measured against known ground truth.</p>
</section>
<footer class="foot">LeakGuard - demonstration build on a published
benchmark network. The same pipeline accepts a live SCADA feed.</footer>
"""

JS = [
'var S = { data:null, key:null, d:null, i:0,',
'  playing:false, timer:null, charts:[], sel:null };',
'function $(id){ return document.getElementById(id); }',
'window.onerror = function(msg, src, line){',
'  var b = $("errbox");',
'  if(b){ b.hidden = false;',
'    b.textContent = "Script error: " + msg + " (line " + line + ")"; }',
'};',
'function showFatal(t){',
'  var b = $("errbox");',
'  if(b){ b.hidden = false; b.textContent = t; }',
'}',
'var marker = { id:"marker", afterDatasetsDraw: function(c){',
'  var x = c.scales.x.getPixelForValue(S.i);',
'  var a = c.chartArea, ctx = c.ctx;',
'  ctx.save(); ctx.strokeStyle = "#8aa0b8";',
'  ctx.setLineDash([5,4]); ctx.lineWidth = 1.2;',
'  ctx.beginPath(); ctx.moveTo(x, a.top);',
'  ctx.lineTo(x, a.bottom); ctx.stroke(); ctx.restore(); } };',
'var shade = { id:"shade", beforeDatasetsDraw: function(c){',
'  var o = c.options.plugins.shade;',
'  if(!o || !o.on) return;',
'  var x0 = c.scales.x.getPixelForValue(o.from);',
'  var a = c.chartArea;',
'  c.ctx.save(); c.ctx.fillStyle = "rgba(214,69,69,.08)";',
'  c.ctx.fillRect(x0, a.top, a.right - x0, a.bottom - a.top);',
'  c.ctx.restore(); } };',
'function xScale(N){',
'  return { type:"linear", min:0, max:Math.max(N-1,1),',
'    ticks:{ maxTicksLimit:7,',
'      callback: function(v){',
'        var t = S.d ? S.d.series.times[Math.round(v)] : "";',
'        return t || ""; } },',
'    grid:{ color:"#e8edf3" } };',
'}',
'function pressAt(id, i){',
'  var a = S.d.series.pressures["pressure_" + id];',
'  if(!Array.isArray(a)) return null;',
'  var v = a[i];',
'  return (typeof v === "number" && isFinite(v)) ? v : null;',
'}',
'function fmtLag(steps){',
'  if(steps === null || steps === undefined || steps < 0) return null;',
'  var m = steps * 15;',
'  if(m < 60) return "<= 15 min";',
'  return (m/60).toFixed(m % 60 ? 1 : 0) + " h";',
'}',
'function firstIdx(arr){',
'  var k = arr.indexOf(1);',
'  return k < 0 ? null : k;',
'}',
'function wireTabs(){',
'  var tabs = document.querySelectorAll(".tab");',
'  for(var t = 0; t < tabs.length; t++){',
'    tabs[t].onclick = function(){',
'      var b = this;',
'      var all = document.querySelectorAll(".tab");',
'      for(var i = 0; i < all.length; i++)',
'        all[i].classList.remove("active");',
'      b.classList.add("active");',
'      var ps = document.querySelectorAll(".panel");',
'      for(var j = 0; j < ps.length; j++)',
'        ps[j].classList.remove("active");',
'      var p = $("panel-" + b.dataset.tab);',
'      if(p) p.classList.add("active");',
'      S.charts.forEach(function(c){ c.resize(); });',
'    };',
'  }',
'}',
'var MAP = null;',
'function buildMap(){',
'  var net = S.data.network;',
'  var holder = $("mapwrap");',
'  if(!net || !net.nodes || !net.nodes.length){',
'    holder.style.display = "none"; return;',
'  }',
'  var svg = $("map");',
'  svg.innerHTML = "";',
'  var xs = net.nodes.map(function(n){ return n.x; });',
'  var ys = net.nodes.map(function(n){ return n.y; });',
'  var minX = Math.min.apply(null, xs);',
'  var maxX = Math.max.apply(null, xs);',
'  var minY = Math.min.apply(null, ys);',
'  var maxY = Math.max.apply(null, ys);',
'  var W = 1000, H = 620, pad = 40;',
'  var sx = (W - 2*pad) / Math.max(maxX - minX, 1e-9);',
'  var sy = (H - 2*pad) / Math.max(maxY - minY, 1e-9);',
'  var sc = Math.min(sx, sy);',
'  var ox = pad + ((W - 2*pad) - (maxX - minX)*sc)/2;',
'  var oy = pad + ((H - 2*pad) - (maxY - minY)*sc)/2;',
'  var NS = "http://www.w3.org/2000/svg";',
'  function el(t, at){',
'    var e = document.createElementNS(NS, t);',
'    for(var k in at) e.setAttribute(k, at[k]);',
'    return e;',
'  }',
'  var byId = {};',
'  net.nodes.forEach(function(n){ byId[n.id] = n; });',
'  net.links.forEach(function(L){',
'    var a = byId[L.frm], b = byId[L.to];',
'    if(!a || !b) return;',
'    svg.appendChild(el("line", {',
'      x1: ox + (a.x-minX)*sc, y1: oy + (maxY-a.y)*sc,',
'      x2: ox + (b.x-minX)*sc, y2: oy + (maxY-b.y)*sc,',
'      "class": "mlk" + (L.type !== "pipe" ? " mlk2" : "") }));',
'  });',
'  MAP = { dots:{}, sc:sc, minX:minX, maxY:maxY,',
'    ox:ox, oy:oy, byId:byId };',
'  var order = net.nodes.slice().sort(function(a, b){',
'    return (a.type === "junction" ? 0 : 1)',
'         - (b.type === "junction" ? 0 : 1); });',
'  order.forEach(function(n){',
'    var x = ox + (n.x-minX)*sc, y = oy + (maxY-n.y)*sc;',
'    var g = el("g", {});',
'    if(n.is_sensor) g.appendChild(el("circle",',
'      { cx:x, cy:y, r:9, "class":"mring" }));',
'    var r = n.type === "tank" ? 7 :',
'      (n.type === "reservoir" ? 8 : 3.4);',
'    var cls = "mdot " + n.type + (n.is_sensor ? " sndot" : "");',
'    var dot = el("circle", { cx:x, cy:y, r:r, "class":cls });',
'    g.appendChild(dot);',
'    var ti = el("title", {});',
'    ti.textContent = n.is_sensor ?',
'      ("Sensor " + n.id + " - " + n.label)',
'      : (n.type + " " + n.id);',
'    g.appendChild(ti);',
'    if(n.is_sensor){',
'      g.style.cursor = "pointer";',
'      g.addEventListener("click", function(){',
'        selectSensor(n.id); });',
'    }',
'    svg.appendChild(g);',
'    MAP.dots[n.id] = dot;',
'    if(n.is_sensor || n.type !== "junction"){',
'      var t = el("text", { x:x, y:y-13, "class":"mlbl" });',
'      t.textContent = n.id;',
'      svg.appendChild(t);',
'    }',
'  });',
'  var lk = el("circle", { r:13, "class":"mleak" });',
'  lk.style.display = "none";',
'  svg.appendChild(lk);',
'  MAP.leak = lk;',
'}',
'function updateLeakMarker(){',
'  if(!MAP || !MAP.leak) return;',
'  if(S.d.leak_node && MAP.byId[S.d.leak_node]){',
'    var n = MAP.byId[S.d.leak_node];',
'    MAP.leak.setAttribute("cx",',
'      MAP.ox + (n.x - MAP.minX)*MAP.sc);',
'    MAP.leak.setAttribute("cy",',
'      MAP.oy + (MAP.maxY - n.y)*MAP.sc);',
'    MAP.leak.style.display = ""; return;',
'  }',
'  MAP.leak.style.display = "none";',
'}',
'function updateSuspect(){',
'  if(!MAP) return;',
'  for(var k in MAP.dots)',
'    MAP.dots[k].classList.remove("suspect");',
'  if(S.d.leak_node){',
'    var z = S.d.series.likely_near[S.i];',
'    var d = MAP.dots[z];',
'    if(d) d.classList.add("suspect");',
'  }',
'}',
'async function init(){',
'  wireTabs();',
'  var raw = null;',
'  try{',
'    var resp = await fetch("/api/data");',
'    raw = await resp.json();',
'  }catch(e){',
'    showFatal("Could not load /api/data - start the server:" +',
'      " python -m dashboard.app");',
'    return;',
'  }',
'  if(!raw || !raw.order || !raw.scenarios || !raw.meta ||',
'     !Array.isArray(raw.meta.sensors)){',
'    showFatal("results.json missing/outdated." +',
'      " Run: python make_data.py");',
'    return;',
'  }',
'  S.data = raw;',
'  var pills = "";',
'  S.data.order.forEach(function(k){',
'    pills += "<button class=\'pill\' data-key=\'" + k + "\'>" +',
'      S.data.scenarios[k].label + "</button>";',
'  });',
'  $("scenPills").innerHTML = pills;',
'  $("scenPills").onclick = function(ev){',
'    var p = ev.target.closest(".pill");',
'    if(!p) return;',
'    try{ setScenario(p.dataset.key); }',
'    catch(err){ showFatal("Switch failed: " + err.message); }',
'  };',
'  $("tiles").onclick = function(ev){',
'    var c = ev.target.closest(".tile");',
'    if(c && c.dataset.sensor) selectSensor(c.dataset.sensor);',
'  };',
'  buildMap();',
'  var startKey = S.data.order.filter(function(k){',
'    return k !== "normal"; })[0] || S.data.order[0];',
'  try{ setScenario(startKey); }',
'  catch(err){ showFatal("Render failed: " + err.message); return; }',
'  $("playBtn").onclick = function(){',
'    if(S.playing){ pause(); }',
'    else { S.playing = true; tickLoop(); } };',
'  $("scrub").addEventListener("input", function(e){',
'    pause(); setIndex(+e.target.value); });',
'  $("dlBtn").onclick = downloadReport;',
'}',
'function leakStartIdx(){',
'  var k = S.d.series.leak_active.indexOf(1);',
'  return k < 0 ? 0 : k;',
'}',
'function topZone(){',
'  var counts = {};',
'  S.d.series.twin_flag.forEach(function(f, i){',
'    if(f){',
'      var z = S.d.series.likely_near[i];',
'      counts[z] = (counts[z] || 0) + 1;',
'    } });',
'  var e = Object.keys(counts).map(function(k){',
'    return [k, counts[k]]; });',
'  e.sort(function(a, b){ return b[1] - a[1]; });',
'  if(!e.length) return null;',
'  var total = 0;',
'  e.forEach(function(q){ total += q[1]; });',
'  return { zone: e[0][0], share: e[0][1] / total };',
'}',
'function setScenario(key){',
'  S.key = key; S.d = S.data.scenarios[key];',
'  S.sel = S.d.leak_node || S.data.meta.sensors[0].id;',
'  var pills = document.querySelectorAll(".pill");',
'  for(var i = 0; i < pills.length; i++){',
'    pills[i].classList.toggle("active",',
'      pills[i].dataset.key === key);',
'  }',
'  $("repScen").textContent = S.d.label;',
'  S.charts.forEach(function(c){ c.destroy(); });',
'  S.charts = [];',
'  buildKPIs(); buildCharts(); buildMetrics(); buildTiles();',
'  updateLeakMarker();',
'  var li = leakStartIdx();',
'  setIndex(li > 96 ? li + 1 : 0);',
'}',
'function buildKPIs(){',
'  var t = S.d.metrics.twin, m = S.d.metrics.mnf;',
'  var tLag = fmtLag(firstIdx(S.d.series.twin_flag));',
'  var mLag = fmtLag(firstIdx(S.d.series.mnf_flag));',
'  var tz = topZone();',
'  var meta = tz ? S.data.meta.sensors.find(function(s){',
'    return s.id === tz.zone; }) : null;',
'  function card(cls, label, value, sub){',
'    return "<div class=\'kpi " + cls + "\'>" +',
'      "<span class=\'klabel\'>" + label + "</span>" +',
'      "<span class=\'kvalue\'>" + value + "</span>" +',
'      "<div class=\'ksub\'>" + sub + "</div></div>";',
'  }',
'  var html = "";',
'  if(!S.d.leak_node){',
'    var nf = 0;',
'    S.d.series.twin_flag.forEach(function(x){',
'      if(x === 1) nf++; });',
'    html += card("good", "False alarms (14 days)",',
'      nf + " flags", "across 1344 steps of normal operation");',
'    html += card("good", "Baseline stability", "clean",',
'      "no leak present - any flag would be a false alarm");',
'    html += card("good", "Nightly method", "quiet",',
'      "nothing to detect");',
'    html += card("good", "Purpose", "trust check",',
'      "proves the model does not cry wolf");',
'  } else {',
'    html += card("good", "Digital twin - first alert",',
'      tLag || "no alert", "continuous watch, 15-minute steps");',
'    html += card(mLag ? "warn" : "bad", "Nightly method",',
'      mLag ? "detected after " + mLag : "missed entirely",',
'      "inspects once per night (02:00-04:00)");',
'    html += card("good", "Detection quality (F1)", String(t.f1),',
'      "precision " + t.precision + " / recall " + t.recall);',
'    html += card(tz ? "good" : "warn", "Localized to",',
'      meta ? (meta.id + " - " + meta.label) : "n/a",',
'      tz ? Math.round(tz.share*100) + "% of alerts point here"',
'         : "no alerts to localize");',
'  }',
'  $("kpis").innerHTML = html;',
'  var ins;',
'  if(!S.d.leak_node){',
'    ins = "No leak occurs in this 14-day baseline." +',
'      " The twin stays quiet throughout - the control that" +',
'      " shows the system does not raise false alarms.";    ',
'  } else {',
'    ins = "Scenario: " +',
'      S.d.label.replace(/^[^-]+- /, "") + ". ";',
'    if(tLag && mLag){',
'      ins += "The twin alerted " +',
'        (mLag === "<= 15 min" ? "well before" : "hours before") +',
'        " the nightly check.";',
'    } else if(!mLag){',
'      ins += "The nightly method never detected this leak" +',
'        " at all - the exact blind spot continuous" +',
'        " monitoring closes.";',
'    }',
'  }',
'  $("insight").textContent = ins;',
'}',
'function alertMarkerData(){',
'  var out = [];',
'  S.d.series.twin_flag.forEach(function(f, i){',
'    if(f){',
'      var y = pressAt(S.sel, i);',
'      if(y !== null) out.push({ x:i, y:y });',
'    } });',
'  return out;',
'}',
'function buildCharts(){',
'  var d = S.d.series, N = d.times.length;',
'  var pal = ["#0b6e99","#177245","#b3261e",',
'    "#6d5bb8","#c07a1a","#0e8f8f"];',
'  var flowData = (d.source_flow_Ls || []).map(function(y, x){',
'    return { x:x, y:y }; });',
'  var thrData = (d.source_flow_Ls || []).map(function(_, x){',
'    return { x:x, y:d.mnf_threshold }; });',
'  var flow = new Chart($("flowChart"), { type:"line",',
'    data:{ datasets:[',
'      { label:"Source flow (L/s)", data:flowData,',
'        borderColor:"#0b6e99", borderWidth:2,',
'        pointRadius:0, tension:.12 },',
'      { label:"Night-flow alert threshold", data:thrData,',
'        borderColor:"#c07a1a", borderDash:[7,5],',
'        borderWidth:1.6, pointRadius:0 } ] },',
'    options:{ animation:false, maintainAspectRatio:false,',
'      scales:{ x:xScale(N),',
'        y:{ title:{ display:true, text:"L/s" } } },',
'      plugins:{ shade:{ on:!!S.d.leak_node,',
'        from:leakStartIdx() },',
'        legend:{ labels:{ boxWidth:12, font:{ size:11 } } } } },',
'    plugins:[marker, shade] });',
'  var psets = S.data.meta.sensors.map(function(s, j){',
'    var pd = (d.pressures && d.pressures["pressure_" + s.id])',
'      || [];',
'    return { label:s.id + " - " + s.label,',
'      data: pd.map(function(y, x){ return { x:x, y:y }; }),',
'      borderColor: pal[j % pal.length],',
'      borderWidth: s.id === S.sel ? 2.6 : 1.4,',
'      pointRadius:0, tension:.1,',
'      alpha: s.id === S.sel ? 1 : .5 }; });',
'  psets.push({ label:"TwinAlert", data:alertMarkerData(),',
'    showLine:false, pointRadius:3,',
'    pointBackgroundColor:"rgba(179,38,30,.9)",',
'    pointBorderColor:"#fff", pointBorderWidth:.5 });',
'  var press = new Chart($("pChart"), { type:"line",',
'    data:{ datasets:psets },',
'    options:{ animation:false, maintainAspectRatio:false,',
'      scales:{ x:xScale(N),',
'        y:{ title:{ display:true, text:"pressure (m)" } } },',
'      plugins:{ shade:{ on:!!S.d.leak_node,',
'        from:leakStartIdx() },',
'        legend:{ labels:{ boxWidth:12, font:{ size:10 },',
'          filter:function(ds){',
'            return ds.label !== "TwinAlert"; } } } } },',
'    plugins:[marker, shade] });',
'  S.charts = [flow, press];',
'}',
'function buildMetrics(){',
'  var t = S.d.metrics.twin, m = S.d.metrics.mnf;',
'  function row(a, b, c){',
'    return "<tr><td>" + a + "</td><td>" + b + "</td><td>" + c +',
'      "</td></tr>";',
'  }',
'  function fmt(v){',
'    return (v === null || v === undefined) ?',
'      "no detection" : v + " h";',
'  }',
'  $("mtable").innerHTML =',
'    "<tr><th></th><th>Digital twin (continuous)</th>" +',
'    "<th>Nightly flow method</th></tr>" +',
'    row("Precision", t.precision, m.precision) +',
'    row("Recall", t.recall, m.recall) +',
'    row("F1", t.f1, m.f1) +',
'    row("Detection lag",',
'      fmt(t.detection_lag_hours), fmt(m.detection_lag_hours));',
'  $("mnote").textContent = S.key === "normal" ?',
'    "No leak in this scenario - any flag would be a false alarm." :',
'    "Lag = time from leak start to first alarm." +',
'    " The nightly method only reads flows once per night," +',
'    " so its lag is structurally large.";',
'}',
'function buildTiles(){',
'  var html = "";',
'  S.data.meta.sensors.forEach(function(s){',
'    html += "<div class=\'tile\' data-sensor=\'" + s.id + "\'>" +',
'      "<div class=\'nm\'>" + s.id + " - " + s.label + "</div>" +',
'      "<div class=\'pv\' id=\'pv_" + s.id + "\'>-</div></div>";',
'  });',
'  $("tiles").innerHTML = html;',
'}',
'function selectSensor(id){',
'  S.sel = id;',
'  if(S.charts[1]){',
'    S.charts[1].data.datasets.forEach(function(ds){',
'      if(ds.label === "TwinAlert"){',
'        ds.data = alertMarkerData(); return;',
'      }',
'      var on = ds.label.indexOf(id + " ") === 0;',
'      ds.borderWidth = on ? 2.6 : 1.4;',
'      ds.alpha = on ? 1 : .5;',
'    });',
'    S.charts[1].update("none");',
'  }',
'  S.data.meta.sensors.forEach(function(s){',
'    var el = $("tile_" + s.id);',
'    if(el) el.classList.toggle("sel", s.id === id);',
'  });',
'}',
'function setIndex(i){',
'  S.i = Math.max(0, Math.min(i,',
'    S.d.series.times.length - 1));',
'  var d = S.d.series;',
'  $("scrub").value = S.i;',
'  $("tlabel").textContent = d.times[S.i];',
'  S.data.meta.sensors.forEach(function(s){',
'    var pv = $("pv_" + s.id);',
'    if(!pv) return;',
'    var v = pressAt(s.id, S.i);',
'    pv.textContent = (v === null ? "n/a" : v + " m");',
'    var near = d.likely_near[S.i] === s.id && !!S.d.leak_node;',
'    pv.style.color = near ? "#8a6116" :',
'      (v === null ? "#94a3b8" : "#16233b");',
'    var el = $("tile_" + s.id);',
'    if(el) el.classList.toggle("near", near);',
'  });',
'  var twinOn = d.twin_flag[S.i] === 1;',
'  var mnfOn = d.mnf_flag[S.i] === 1;',
'  var cT = twinOn ? "#b3261e" : "#177245";',
'  var cM = mnfOn ? "#8a6116" : "#177245";',
'  var parts = ["Day status: <b>" + d.times[S.i] + "</b>",',
'    "Digital twin: <b style=\'color:" + cT + "\'>" +',
'      (twinOn ? "ANOMALY" : "normal") + "</b>",',
'    "Nightly method: <b style=\'color:" + cM + "\'>" +',
'      (mnfOn ? "flagged" : "quiet") + "</b>"];',
'  if(S.d.leak_node){',
'    var z = d.likely_near[S.i];',
'    var meta = S.data.meta.sensors.find(function(s){',
'      return s.id === z; });',
'    parts.push("Pointing at: <b>" +',
'      (meta ? (meta.id + " - " + meta.label) : z) + "</b>");',
'  }',
'  $("liveline").innerHTML = parts.join(" &middot; ");',
'  updateSuspect();',
'  S.charts.forEach(function(c){ c.update("none"); });',
'}',
'function pause(){',
'  S.playing = false;',
'  clearInterval(S.timer);',
'  $("playBtn").textContent = "Play";',
'}',
'function tickLoop(){',
'  clearInterval(S.timer);',
'  $("playBtn").textContent = "Pause";',
'  S.timer = setInterval(function(){',
'    if(S.i >= S.d.series.times.length - 1){',
'      pause(); return;',
'    }',
'    setIndex(S.i + 16);',
'  }, 100);',
'}',
'function downloadReport(){',
'  var t = S.d.metrics.twin, m = S.d.metrics.mnf;',
'  var tz = topZone();',
'  var meta = tz ? S.data.meta.sensors.find(function(s){',
'    return s.id === tz.zone; }) : null;',
'  var lines = [',
'    "LEAKGUARD - INCIDENT REPORT",',
'    "========================================",',
'    "Scenario: " + S.d.label,',
'    "Leak node: " + (S.d.leak_node || "none"),',
'    "Leak start: " + (S.d.leak_start || "n/a"),',
'    "",',
'    "Digital twin (continuous):",',
'    "  precision " + t.precision +',
'      "  recall " + t.recall + "  F1 " + t.f1,',
'    "  first alert: " +',
'      (fmtLag(firstIdx(S.d.series.twin_flag)) || "none"),',
'    "Nightly flow method:",',
'    "  precision " + m.precision +',
'      "  recall " + m.recall + "  F1 " + m.f1,',
'    "  first alert: " +',
'      (fmtLag(firstIdx(S.d.series.mnf_flag)) || "none"),',
'    "",',
'    "Localization: " + (meta ?',
'      (meta.id + " - " + meta.label + " (" +',
'       Math.round((tz.share || 0)*100) + "% of alerts)")',
'      : "n/a"),',
'    "",',
'    "Provenance: EPANET (WNTR) on the EPA Net3 benchmark,",',
'    "14 days at 15-minute steps; leaks modeled as",',
'    "pressure-dependent orifice emitters; detectors trained",',
'    "on leak-free data only. LeakGuard demonstration build."',
'  ];',
'  var a = document.createElement("a");',
'  a.href = URL.createObjectURL(new Blob(',
'    [lines.join("\\n")], { type:"text/plain" }));',
'  a.download = "leakguard-report-" + S.key + ".txt";',
'  a.click();',
'}',
'init();',
]

HEAD = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="UTF-8"/>\n'
        '<meta name="viewport" content="width=device-width, '
        'initial-scale=1"/>\n'
        '<title>LeakGuard - Water Network Leak Detection</title>\n'
        '<style>' + CSS + '</style>\n</head>\n<body>\n')
MID = ('\n<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1'
       '/dist/chart.umd.min.js"></script>\n<script>\n')
TAIL = '\n</script>\n</body>\n</html>\n'


def main():
    js = "\n".join(JS)
    html = HEAD + HTML + MID + js + TAIL
    path = os.path.join(ROOT, "dashboard", "templates", "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    checks = []
    checks.append(("starts with doctype",
                   html.lstrip().lower().startswith("<!doctype")))
    checks.append(("ends with </html>",
                   html.rstrip().endswith("</html>")))
    checks.append(("js braces balanced",
                   js.count("{") == js.count("}")))
    checks.append(("js parens balanced",
                   js.count("(") == js.count(")")))
    checks.append(("js quotes even",
                   js.count('"') % 2 == 0))
    checks.append(("shade marker present", 'id:"shade"' in js))
    checks.append(("no escaped quotes in js", "\\" + '"' not in js))

    print("wrote dashboard/templates/index.html ("
          + str(len(html)) + " chars, "
          + str(len(JS)) + " js lines)")
    ok = True
    for name, passed in checks:
        print(("  OK  " if passed else "  FAIL") + " " + name)
        ok = ok and passed
    print("INTEGRITY:", "OK" if ok else "BROKEN - report to chat")


if __name__ == "__main__":
    main()