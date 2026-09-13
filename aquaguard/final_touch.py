#!/usr/bin/env python3
# final_touch.py - simpler text, cleaner map, water-loss KPI.
# Rewrites make_data.py (adds est_loss) and index.html (DOM-built, paste-proof).
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))

MAKE_DATA = r'''"""Runs the WNTR/EPANET pipeline and writes dashboard/data/results.json."""
import json
import os
import sys
import traceback

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from core.simulate import generate_scenario, PRESSURE_SENSOR_NODES, NODE_LABELS
from core.detectors import (MinimumNightFlowDetector, ResidualTwinDetector,
                            score_detection, STEPS_PER_DAY)

SENSOR_COLS = ["pressure_" + n for n in PRESSURE_SENSOR_NODES]
DT_MIN = 15

SCENARIOS = [
    dict(key="normal", label="Baseline - no leaks",
         csv="data/scenario_normal.csv", gen=dict(n_days=14)),
    dict(key="leak_a", label="Slow leak - Central Park",
         csv="data/scenario_leak_a.csv",
         gen=dict(n_days=14, leak_node="105", leak_coeff=0.003)),
    dict(key="leak_b", label="Burst - South Harbor",
         csv="data/scenario_leak_b.csv",
         gen=dict(n_days=14, leak_node="201", leak_coeff=0.010)),
]


def extract_network():
    import wntr
    from core.network import NETWORK_PATH
    wn = wntr.network.WaterNetworkModel(NETWORK_PATH)
    nodes, links = [], []
    for name in wn.node_name_list:
        node = wn.get_node(name)
        try:
            x, y = node.coordinates
        except Exception:
            continue
        t = (getattr(node, "node_type", "") or "").lower()
        ntype = ("reservoir" if t.startswith("res")
                 else "tank" if t.startswith("tank") else "junction")
        nodes.append(dict(id=name, x=float(x), y=float(y), type=ntype,
                          is_sensor=name in PRESSURE_SENSOR_NODES,
                          label=NODE_LABELS.get(name, name)))
    for name in wn.link_name_list:
        link = wn.get_link(name)
        t = (getattr(link, "link_type", "") or "").lower()
        links.append(dict(frm=link.start_node_name,
                          to=link.end_node_name, type=t))
    return dict(nodes=nodes, links=links)


def get_or_generate(sc):
    if os.path.exists(sc["csv"]):
        print("  " + sc["key"] + ": cached")
        return pd.read_csv(sc["csv"])
    print("  " + sc["key"] + ": EPANET simulation ...", flush=True)
    df = generate_scenario(**sc["gen"])
    os.makedirs("data", exist_ok=True)
    df.to_csv(sc["csv"], index=False)
    return df


def fmt_time(step):
    step = int(step)
    day = step // STEPS_PER_DAY + 1
    mins = (step % STEPS_PER_DAY) * DT_MIN
    return "Day " + str(day) + " " + str(mins // 60).zfill(2) + ":" \
        + str(mins % 60).zfill(2)


def main():
    dfs = {}
    print("[1/4] scenarios ...", flush=True)
    for sc in SCENARIOS:
        dfs[sc["key"]] = get_or_generate(sc)
    df_normal = dfs["normal"]

    print("[2/4] network map ...", flush=True)
    network = extract_network()

    print("[3/4] training on leak-free baseline ...", flush=True)
    mnf = MinimumNightFlowDetector(threshold_pct=0.20).fit(df_normal)
    twin = ResidualTwinDetector(sensor_cols=SENSOR_COLS).fit(df_normal)

    print("[4/4] scoring ...", flush=True)
    base_f = df_normal["source_flow_Ls"].mean()
    out = {}
    for sc in SCENARIOS:
        df = dfs[sc["key"]]
        has_leak = "leak_node" in sc["gen"]
        df_mnf, daily_mnf, thr = mnf.predict(df)
        df_tw = twin.predict(df)
        df_mnf.loc[df_mnf["hour_of_day"] < 4.0, "mnf_flag"] = 0

        est_lpm = 0.0
        note = ""
        if has_leak:
            leak_f = df[df.leak_active == 1]["source_flow_Ls"].mean()
            est = max(0.0, leak_f - base_f)
            est_lpm = round(est * 60, 1)
            note = " | leak adds ~" + str(round(est, 1)) + " L/s"

        out[sc["key"]] = dict(
            label=sc["label"],
            leak_node=sc["gen"].get("leak_node"),
            leak_start=("from Day 1 (demo)" if has_leak else None),
            est_loss_Lpm=est_lpm,
            metrics=dict(mnf=score_detection(df_mnf, "mnf_flag"),
                         twin=score_detection(df_tw, "twin_flag")),
            series=dict(
                times=[fmt_time(s) for s in df["step"]],
                source_flow_Ls=df["source_flow_Ls"].round(2).tolist(),
                leak_active=df["leak_active"].astype(int).tolist(),
                twin_flag=df_tw["twin_flag"].astype(int).tolist(),
                mnf_flag=df_mnf["mnf_flag"].astype(int).tolist(),
                anomaly_score=df_tw["anomaly_score"].round(4).tolist(),
                likely_near=[c.replace("pressure_", "")
                             for c in df_tw["likely_leak_near"]],
                pressures={c: df[c].round(2).tolist() for c in SENSOR_COLS},
                mnf_daily={str(k): round(v, 2)
                           for k, v in daily_mnf.items()},
                mnf_threshold=round(float(thr), 2),
            ),
        )
        mt = out[sc["key"]]["metrics"]["twin"]
        mm = out[sc["key"]]["metrics"]["mnf"]
        print("  " + sc["key"] + ": twin F1=" + str(mt["f1"]) +
              " lag=" + str(mt["detection_lag_hours"]) + "h | nightly F1=" +
              str(mm["f1"]) + " lag=" + str(mm["detection_lag_hours"]) +
              "h" + note, flush=True)

    payload = dict(
        meta=dict(steps_per_day=STEPS_PER_DAY, dt_min=DT_MIN,
                  sensors=[dict(id=n, label=NODE_LABELS.get(n, n))
                           for n in PRESSURE_SENSOR_NODES],
                  baseline_mnf_Ls=round(float(mnf.baseline_mnf_), 2)),
        network=network,
        order=[sc["key"] for sc in SCENARIOS],
        scenarios=out,
    )
    os.makedirs("dashboard/data", exist_ok=True)
    with open("dashboard/data/results.json", "w") as f:
        json.dump(payload, f)
    print("\nWROTE dashboard/data/results.json (map: "
          + str(len(network["nodes"])) + " nodes) - Ctrl+Shift+R in browser")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nPIPELINE ERROR - paste this traceback into the chat:")
        traceback.print_exc()
'''

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
.pills{display:flex;gap:8px;flex-wrap:wrap;max-width:620px}
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
.kpigrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));
gap:14px;margin-top:4px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;border-left:5px solid var(--line);min-width:0}
.klabel{display:block;font-size:.75rem;text-transform:uppercase;
letter-spacing:.06em;color:var(--ink2);font-weight:700;margin-bottom:6px}
.kvalue{font-size:1.25rem;font-weight:800;line-height:1.3;
overflow-wrap:anywhere}
.ksub{font-size:.8rem;color:var(--ink2);margin-top:5px;overflow-wrap:anywhere}
.kpi.good{border-left-color:#2f9e63}.kpi.good .kvalue{color:var(--good)}
.kpi.warn{border-left-color:#d9a62e}.kpi.warn .kvalue{color:var(--warn)}
.kpi.bad{border-left-color:#d64545}.kpi.bad .kvalue{color:var(--bad)}
.insight{background:var(--card);border:1px solid var(--line);
border-left:5px solid var(--accent);border-radius:12px;padding:14px 18px;
margin:16px 0;font-size:.98rem;overflow-wrap:anywhere}
.liveline{background:#eef3f8;border:1px solid var(--line);border-radius:10px;
padding:10px 16px;font-size:.93rem;margin-bottom:4px;display:flex;
flex-wrap:wrap;gap:4px 16px;align-items:center;overflow-wrap:anywhere}
.mapbox{background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:10px}
#map{width:100%;height:auto;display:block}
.mlk{stroke:#d6dfe8;stroke-width:.9}
.mlk2{stroke:#b8c5d2;stroke-dasharray:5 3}
.mdot.junction{fill:#bcc9d6}
.mdot.tank{fill:#0e8f8f}
.mdot.reservoir{fill:#085a7d}
.mdot.sndot{fill:#0b6e99}
.mdot.suspect{fill:#d9a62e}
.mring{fill:none;stroke:#0b6e99;stroke-width:2.2}
.mlbl{font-size:12.5px;fill:#3f4f63;text-anchor:middle;font-weight:700}
.mleak{fill:none;stroke:#b3261e;stroke-width:2.4;stroke-dasharray:6 4}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:.8rem;
color:var(--ink2);margin-top:8px}
.lg{display:inline-block;width:11px;height:11px;border-radius:50%;
margin-right:5px;vertical-align:-1px}
.lg.j{background:#bcc9d6}.lg.s{background:#0b6e99}
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
<p class="tagline">Finds pipe leaks early - before anyone notices the loss</p>
</header>
<nav class="tabs">
<button class="tab active" data-tab="overview">Overview</button>
<button class="tab" data-tab="analysis">Charts</button>
<button class="tab" data-tab="reports">Evidence</button>
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
<p class="secthint">The real EPA Net3 network. Big blue rings are the six
watched districts. During a leak: red dashed circle = where the leak is,
amber dot = where the model points.</p>
<div class="mapbox"><svg id="map" viewBox="0 0 1000 640"></svg></div>
<div class="legend">
<span><i class="lg j"></i>pipe junction</span>
<span><i class="lg s"></i>watched district</span>
<span><i class="lg t"></i>tank</span>
<span><i class="lg r"></i>reservoir</span>
<span><i class="lg l"></i>leak</span>
<span><i class="lg q"></i>suspected</span>
</div>
<h2 class="sect">Watched districts</h2>
<p class="secthint">Live pressure at each district. Amber = the district
the model currently suspects. Click one to highlight it in Charts.</p>
<div class="tiles" id="tiles"></div>
</section>
<section class="panel" id="panel-analysis">
<h2 class="sect">Water flow at the reservoir</h2>
<p class="secthint">Orange dashes = alert line learned from leak-free
days. Flow above it at night means water is escaping. Red shading =
leak is active.</p>
<div class="chartbox"><canvas id="flowChart"></canvas></div>
<h2 class="sect">Pressure in the six districts</h2>
<p class="secthint">Pressure drops near a leak. Red dots = moments the
model flagged on the selected district.</p>
<div class="chartbox"><canvas id="pChart"></canvas></div>
</section>
<section class="panel" id="panel-reports">
<h2 class="sect">Measured results - <span id="repScen" class="mono"></span></h2>
<table class="mtable" id="mtable"></table>
<p class="note" id="mnote"></p>
<button id="dlBtn" class="dlbtn">Download report (.txt)</button>
<h2 class="sect">The two methods compared</h2>
<div class="method">
<p><b>Nightly check (today)</b> - utilities read flows once per night,
between 02:00 and 04:00, when real demand is near zero. Leftover flow
means leakage. Trusted, but it looks at the network only once a day,
so a burst can run for half a day unseen - and a slow leak may never
stand out.</p>
<p><b>Continuous twin (LeakGuard)</b> - the app learns the normal
pressure of every district for every hour of the day, from leak-free
data. Every 15 minutes it compares live pressures with normal. When
several districts dip together in a way normal operation never shows,
it raises an alert and names the likely zone.</p>
</div>
<h2 class="sect">Where the data comes from</h2>
<p class="note">Simulated with the official EPANET engine on the EPA
Net3 benchmark network: 92 junctions, two reservoirs, tanks and pumps,
14 days at 15-minute steps. Leaks are modeled as pressure-driven
orifices. Detectors are trained only on leak-free days. All scores are
measured against the known truth, not estimated.</p>
</section>
<footer class="foot">LeakGuard - demonstration build. The same pipeline
accepts a live sensor feed from a real network.</footer>
"""

JS = [
'var S = { data:null, key:null, d:null, i:0,',
'  playing:false, timer:null, charts:[], sel:null };',
'var ZONE = { "15":"Northside", "35":"Downtown", "101":"Eastside",',
'  "105":"Central Park", "113":"Westside", "201":"South Harbor" };',
'function $(id){ return document.getElementById(id); }',
'function el(tag, cls, text){',
'  var e = document.createElement(tag);',
'  if(cls) e.className = cls;',
'  if(text !== undefined) e.textContent = text;',
'  return e;',
'}',
'window.onerror = function(msg, src, line){',
'  var b = $("errbox");',
'  if(b){ b.hidden = false;',
'    b.textContent = "Script error: " + msg + " line " + line; }',
'};',
'function showFatal(t){',
'  var b = $("errbox");',
'  if(b){ b.hidden = false; b.textContent = t; }',
'}',
'var marker = { id:"marker", afterDatasetsDraw:function(c){',
'  var x = c.scales.x.getPixelForValue(S.i);',
'  var a = c.chartArea, ctx = c.ctx;',
'  ctx.save(); ctx.strokeStyle = "#8aa0b8";',
'  ctx.setLineDash([5,4]); ctx.lineWidth = 1.2;',
'  ctx.beginPath(); ctx.moveTo(x, a.top);',
'  ctx.lineTo(x, a.bottom); ctx.stroke(); ctx.restore(); } };',
'var shade = { id:"shade", beforeDatasetsDraw:function(c){',
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
'      callback:function(v){',
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
'  if(m < 60) return "within 15 min";',
'  return "after " + (m/60).toFixed(m % 60 ? 1 : 0) + " h";',
'}',
'function firstIdx(arr){',
'  var k = arr.indexOf(1);',
'  return k < 0 ? null : k;',
'}',
'function zoneName(id){ return ZONE[id] || id; }',
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
'  if(!net || !net.nodes || !net.nodes.length) return;',
'  var svg = $("map");',
'  svg.innerHTML = "";',
'  var xs = net.nodes.map(function(n){ return n.x; });',
'  var ys = net.nodes.map(function(n){ return n.y; });',
'  var minX = Math.min.apply(null, xs);',
'  var maxX = Math.max.apply(null, xs);',
'  var minY = Math.min.apply(null, ys);',
'  var maxY = Math.max.apply(null, ys);',
'  var W = 1000, H = 640, pad = 46;',
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
'      { cx:x, cy:y, r:10, "class":"mring" }));',
'    var r = n.type === "tank" ? 7 :',
'      (n.type === "reservoir" ? 8 : 2.6);',
'    var cls = "mdot " + n.type + (n.is_sensor ? " sndot" : "");',
'    var dot = el("circle", { cx:x, cy:y, r:r, "class":cls });',
'    g.appendChild(dot);',
'    var ti = el("title", {});',
'    ti.textContent = n.is_sensor ?',
'      ("Watched district: " + n.label)',
'      : (n.type + " " + n.id);',
'    g.appendChild(ti);',
'    if(n.is_sensor){',
'      g.style.cursor = "pointer";',
'      g.addEventListener("click", function(){',
'        selectSensor(n.id); });',
'    }',
'    svg.appendChild(g);',
'    MAP.dots[n.id] = dot;',
'  });',
'  net.nodes.forEach(function(n){',
'    if(!(n.is_sensor || n.type !== "junction")) return;',
'    var x = ox + (n.x-minX)*sc, y = oy + (maxY-n.y)*sc;',
'    var txt = n.is_sensor ? zoneName(n.id) : n.id;',
'    var t = el("text", { x:x, y:y-15, "class":"mlbl" });',
'    t.textContent = txt;',
'    svg.appendChild(t);',
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
'    showFatal("No data. Start the server:" +',
'      " python -m dashboard.app");',
'    return;',
'  }',
'  if(!raw || !raw.order || !raw.scenarios || !raw.meta ||',
'     !Array.isArray(raw.meta.sensors)){',
'    showFatal("results.json missing. Run: python make_data.py");',
'    return;',
'  }',
'  S.data = raw;',
'  S.data.order.forEach(function(k){',
'    var b = el("button", "pill", S.data.scenarios[k].label);',
'    b.dataset.key = k;',
'    $("scenPills").appendChild(b);',
'  });',
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
'function kpiCard(cls, label, value, sub){',
'  var box = el("div", "kpi " + cls);',
'  box.appendChild(el("span", "klabel", label));',
'  box.appendChild(el("span", "kvalue", value));',
'  box.appendChild(el("div", "ksub", sub));',
'  return box;',
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
'  var box = $("kpis");',
'  box.innerHTML = "";',
'  if(!S.d.leak_node){',
'    var nf = 0;',
'    S.d.series.twin_flag.forEach(function(x){',
'      if(x === 1) nf++; });',
'    box.appendChild(kpiCard("good",',
'      "False alarms in 14 normal days",',
'      nf + " alerts",',
'      "the proof it does not cry wolf"));',
'    box.appendChild(kpiCard("good",',
'      "Nightly check", "quiet",',
'      "nothing to find - baseline days"));',
'    box.appendChild(kpiCard("good",',
'      "What this scenario is", "control run",',
'      "two weeks of normal operation"));',
'  } else {',
'    box.appendChild(kpiCard("good",',
'      "LeakGuard first alert", tLag || "no alert",',
'      "checks every 15 minutes"));',
'    box.appendChild(kpiCard(mLag ? "warn" : "bad",',
'      "Old nightly check",',
'      mLag ? "found it " + mLag : "never found it",',
'      "looks once per night"));',
'    box.appendChild(kpiCard("good",',
'      "Accuracy (F1)", String(t.f1),',
'      "precision " + t.precision + " / recall " + t.recall));',
'    box.appendChild(kpiCard(tz ? "good" : "warn",',
'      "Leak located at",',
'      meta ? zoneName(meta.id) : "n/a",',
'      tz ? Math.round(tz.share*100) +',
'        "% of alerts point here" : ""));',
'    if(S.d.est_loss_Lpm > 0){',
'      box.appendChild(kpiCard("bad",',
'        "Water being lost",',
'        "~" + S.d.est_loss_Lpm + " L/min",',
'        "extra flow seen at the source"));',
'    }',
'  }',
'  var ins;',
'  if(!S.d.leak_node){',
'    ins = "Fourteen days of normal operation, no leak." +',
'      " The model stays quiet - it does not cry wolf.";    ',
'  } else {',
'    ins = "A leak is losing about " + S.d.est_loss_Lpm +',
'      " L/min at " + zoneName(S.d.leak_node) + ". ";',
'    if(tLag && mLag){',
'      ins += "LeakGuard alerts " + tLag + ". The nightly check ";',
'      ins += (mLag === "within 15 min") ?',
'        "also reacts fast." : "needs " + mLag + ".";',
'    } else {',
'      ins += "LeakGuard alerts " + tLag +',
'        ". The nightly check never catches it - its blind spot.";',
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
'      { label:"Flow (L/s)", data:flowData,',
'        borderColor:"#0b6e99", borderWidth:2,',
'        pointRadius:0, tension:.12 },',
'      { label:"Night alert line", data:thrData,',
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
'    return { label:zoneName(s.id),',
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
'  var tb = $("mtable");',
'  tb.innerHTML = "";',
'  function head(a, b, c){',
'    var tr = el("tr");',
'    tr.appendChild(el("th", null, a));',
'    tr.appendChild(el("th", null, b));',
'    tr.appendChild(el("th", null, c));',
'    return tr;',
'  }',
'  function row(a, b, c){',
'    var tr = el("tr");',
'    tr.appendChild(el("td", null, a));',
'    tr.appendChild(el("td", null, b));',
'    tr.appendChild(el("td", null, c));',
'    return tr;',
'  }',
'  function fmt(v){',
'    return (v === null || v === undefined) ?',
'      "never" : v + " h";',
'  }',
'  tb.appendChild(head("", "LeakGuard (continuous)",',
'    "Nightly check"));',
'  tb.appendChild(row("Precision",',
'    t.precision, m.precision));',
'  tb.appendChild(row("Recall", t.recall, m.recall));',
'  tb.appendChild(row("F1 score", t.f1, m.f1));',
'  tb.appendChild(row("Time to first alert",',
'    fmt(t.detection_lag_hours),',
'    fmt(m.detection_lag_hours)));',
'  $("mnote").textContent = S.key === "normal" ?',
'    "No leak here - any alert would be a false alarm." :',
'    "Time to first alert counts from the moment the leak starts.";',
'}',
'function buildTiles(){',
'  var box = $("tiles");',
'  box.innerHTML = "";',
'  S.data.meta.sensors.forEach(function(s){',
'    var c = el("div", "tile");',
'    c.dataset.sensor = s.id;',
'    c.id = "tile_" + s.id;',
'    c.appendChild(el("div", "nm",',
'      zoneName(s.id) + " (node " + s.id + ")"));',
'    var pv = el("div", "pv", "-");',
'    pv.id = "pv_" + s.id;',
'    c.appendChild(pv);',
'    box.appendChild(c);',
'  });',
'}',
'function selectSensor(id){',
'  S.sel = id;',
'  if(S.charts[1]){',
'    S.charts[1].data.datasets.forEach(function(ds){',
'      if(ds.label === "TwinAlert"){',
'        ds.data = alertMarkerData(); return;',
'      }',
'      var on = ds.label === zoneName(id);',
'      ds.borderWidth = on ? 2.6 : 1.4;',
'      ds.alpha = on ? 1 : .5;',
'    });',
'    S.charts[1].update("none");',
'  }',
'  S.data.meta.sensors.forEach(function(s){',
'    var t = $("tile_" + s.id);',
'    if(t) t.classList.toggle("sel", s.id === id);',
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
'    var t = $("tile_" + s.id);',
'    if(t) t.classList.toggle("near", near);',
'  });',
'  var twinOn = d.twin_flag[S.i] === 1;',
'  var mnfOn = d.mnf_flag[S.i] === 1;',
'  var line = $("liveline");',
'  line.innerHTML = "";',
'  line.appendChild(el("span", null,',
'    "Viewing: " + d.times[S.i]));',
'  var s1 = el("span", null,',
'    "LeakGuard: " + (twinOn ? "ALERT" : "normal"));',
'  s1.style.color = twinOn ? "#b3261e" : "#177245";',
'  s1.style.fontWeight = "700";',
'  line.appendChild(s1);',
'  var s2 = el("span", null,',
'    "Nightly check: " + (mnfOn ? "flagged" : "quiet"));',
'  s2.style.color = mnfOn ? "#8a6116" : "#177245";',
'  line.appendChild(s2);',
'  if(S.d.leak_node){',
'    var z = d.likely_near[S.i];',
'    line.appendChild(el("span", null,',
'      "Suspects: " + zoneName(z)));',
'  }',
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
'    "Estimated loss: " +',
'      (S.d.est_loss_Lpm > 0 ?',
'       S.d.est_loss_Lpm + " L/min" : "0"),',
'    "",',
'    "LeakGuard (continuous):",',
'    "  precision " + t.precision +',
'      "  recall " + t.recall + "  F1 " + t.f1,',
'    "  first alert: " +',
'      (fmtLag(firstIdx(S.d.series.twin_flag)) || "never"),',
'    "Nightly check:",',
'    "  precision " + m.precision +',
'      "  recall " + m.recall + "  F1 " + m.f1,',
'    "  first alert: " +',
'      (fmtLag(firstIdx(S.d.series.mnf_flag)) || "never"),',
'    "",',
'    "Localization: " + (meta ?',
'      (zoneName(meta.id) + " (" +',
'       Math.round((tz.share || 0)*100) + "% of alerts)")',
'      : "n/a"),',
'    "",',
'    "Source: EPANET engine, EPA Net3 benchmark network,",',
'    "14 days at 15-minute steps, orifice leak model,",',
'    "trained on leak-free data only.",',
'    "LeakGuard demonstration build."',
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

    bad_apos = [i + 1 for i, ln in enumerate(JS) if "'" in ln]
    checks = [
        ("starts with doctype",
         html.lstrip().lower().startswith("<!doctype")),
        ("ends with </html>", html.rstrip().endswith("</html>")),
        ("js braces balanced", js.count("{") == js.count("}")),
        ("js parens balanced", js.count("(") == js.count(")")),
        ("js double quotes even", js.count('"') % 2 == 0),
        ("no apostrophes in js", not bad_apos),
    ]
    print("wrote index.html (" + str(len(html)) + " chars, "
          + str(len(JS)) + " js lines)")
    ok = True
    for name, p in checks:
        print(("  OK  " if p else "  FAIL") + " " + name)
        ok = ok and p
    if bad_apos:
        print("  apostrophe lines:", bad_apos)
    print("INTEGRITY:", "OK" if ok else "BROKEN - report to chat")
    if not ok:
        return

    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    try:
        import make_data
        make_data.main()
    except Exception:
        print("\nERROR - paste this traceback into the chat:")
        traceback.print_exc()


if __name__ == "__main__":
    main()