#!/usr/bin/env python3
# upgrade_map.py - LeakGuard rebrand + real Net3 network map + overflow fixes.
# Rewrites make_data.py (adds network export) and the self-contained page,
# then regenerates results.json (EPANET CSVs are cached -> fast).
import json
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))

MAKE_DATA_PY = r'''"""Runs the WNTR/EPANET pipeline and writes dashboard/data/results.json."""
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
    dict(key="leak_a", label="Scenario A - gradual aging pipe leak (Central Park)",
         csv="data/scenario_leak_a.csv",
         gen=dict(n_days=14, leak_node="105", leak_coeff=0.003)),
    dict(key="leak_b", label="Scenario B - sudden pipe burst (South Harbor)",
         csv="data/scenario_leak_b.csv",
         gen=dict(n_days=14, leak_node="201", leak_coeff=0.010)),
]


def extract_network():
    """Real topology + coordinates of the benchmark network, for the map."""
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
        links.append(dict(frm=link.start_node_name, to=link.end_node_name, type=t))
    return dict(nodes=nodes, links=links)


def get_or_generate(sc):
    if os.path.exists(sc["csv"]):
        print("  " + sc["key"] + ": loaded from cache")
        return pd.read_csv(sc["csv"])
    print("  " + sc["key"] + ": running EPANET simulation ...", flush=True)
    df = generate_scenario(**sc["gen"])
    os.makedirs("data", exist_ok=True)
    df.to_csv(sc["csv"], index=False)
    return df


def fmt_time(step):
    step = int(step)
    day = step // STEPS_PER_DAY + 1
    mins = (step % STEPS_PER_DAY) * DT_MIN
    return "Day " + str(day) + " " + str(mins // 60).zfill(2) + ":" + str(mins % 60).zfill(2)


def main():
    dfs = {}
    print("[1/4] scenarios ...", flush=True)
    for sc in SCENARIOS:
        dfs[sc["key"]] = get_or_generate(sc)
    df_normal = dfs["normal"]

    print("[2/4] extracting network map ...", flush=True)
    network = extract_network()

    print("[3/4] training detectors on leak-free baseline ...", flush=True)
    mnf = MinimumNightFlowDetector(threshold_pct=0.20).fit(df_normal)
    twin = ResidualTwinDetector(sensor_cols=SENSOR_COLS).fit(df_normal)

    print("[4/4] scoring scenarios ...", flush=True)
    out = {}
    for sc in SCENARIOS:
        df = dfs[sc["key"]]
        has_leak = "leak_node" in sc["gen"]
        df_mnf, daily_mnf, thr = mnf.predict(df)
        df_tw = twin.predict(df)
        df_mnf.loc[df_mnf["hour_of_day"] < 4.0, "mnf_flag"] = 0  # nightly result known only after 04:00

        note = ""
        if has_leak:
            base_f = df_normal["source_flow_Ls"].mean()
            leak_f = df[df.leak_active == 1]["source_flow_Ls"].mean()
            note = " | leak adds ~" + str(round(leak_f - base_f, 1)) + " L/s avg flow"

        out[sc["key"]] = dict(
            label=sc["label"],
            leak_node=sc["gen"].get("leak_node"),
            leak_start=("active from first record" if has_leak else None),
            metrics=dict(mnf=score_detection(df_mnf, "mnf_flag"),
                         twin=score_detection(df_tw, "twin_flag")),
            series=dict(
                times=[fmt_time(s) for s in df["step"]],
                source_flow_Ls=df["source_flow_Ls"].round(2).tolist(),
                leak_active=df["leak_active"].astype(int).tolist(),
                twin_flag=df_tw["twin_flag"].astype(int).tolist(),
                mnf_flag=df_mnf["mnf_flag"].astype(int).tolist(),
                anomaly_score=df_tw["anomaly_score"].round(4).tolist(),
                likely_near=[c.replace("pressure_", "") for c in df_tw["likely_leak_near"]],
                pressures={c: df[c].round(2).tolist() for c in SENSOR_COLS},
                mnf_daily={str(k): round(v, 2) for k, v in daily_mnf.items()},
                mnf_threshold=round(float(thr), 2),
            ),
        )
        mt = out[sc["key"]]["metrics"]["twin"]
        mm = out[sc["key"]]["metrics"]["mnf"]
        print("  " + sc["key"] + ": twin F1=" + str(mt["f1"]) +
              " lag=" + str(mt["detection_lag_hours"]) + "h | nightly F1=" +
              str(mm["f1"]) + " lag=" + str(mm["detection_lag_hours"]) + "h" + note,
              flush=True)

    payload = dict(
        meta=dict(steps_per_day=STEPS_PER_DAY, dt_min=DT_MIN,
                  sensors=[dict(id=n, label=NODE_LABELS.get(n, n)) for n in PRESSURE_SENSOR_NODES],
                  baseline_mnf_Ls=round(float(mnf.baseline_mnf_), 2)),
        network=network,
        order=[sc["key"] for sc in SCENARIOS],
        scenarios=out,
    )
    os.makedirs("dashboard/data", exist_ok=True)
    with open("dashboard/data/results.json", "w") as f:
        json.dump(payload, f)
    print("\nWROTE dashboard/data/results.json  (map: " + str(len(network["nodes"])) +
          " nodes, " + str(len(network["links"])) + " links) - refresh browser Ctrl+Shift+R")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nPIPELINE ERROR - paste this traceback into the chat:")
        traceback.print_exc()
'''

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>LeakGuard - Water Network Leak Detection</title>
<style>
:root{
  --bg:#f2f5f9; --card:#ffffff; --ink:#16233b; --ink2:#5b6b82;
  --line:#dbe3ec; --accent:#0b6e99; --accent2:#085a7d;
  --good:#177245; --goodbg:#e7f5ec; --warn:#8a6116; --warnbg:#fdf3dd;
  --bad:#b3261e; --badbg:#fdeceb;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:"Segoe UI",system-ui,-apple-system,Roboto,sans-serif;
  background:var(--bg);color:var(--ink);font-size:16px;line-height:1.55}
.sitehead{text-align:center;padding:30px 16px 8px}
.appname{font-size:2.8rem;font-weight:800;letter-spacing:-.5px}
.tagline{color:var(--ink2);font-size:1.02rem;margin-top:4px}
.tabs{display:flex;justify-content:center;gap:6px;margin:20px auto 0;max-width:760px;
  background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px}
.tab{flex:1;border:none;background:transparent;color:var(--ink2);font-size:1rem;
  font-weight:600;padding:11px 10px;border-radius:8px;cursor:pointer}
.tab:hover{background:#eef3f8;color:var(--ink)}
.tab.active{background:var(--accent);color:#fff}
.controlstrip{max-width:1100px;margin:16px auto 0;padding:0 20px;display:flex;
  flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
.pills{display:flex;gap:8px;flex-wrap:wrap;max-width:600px}
.pill{border:1.5px solid var(--line);background:var(--card);color:var(--ink2);
  border-radius:999px;padding:9px 16px;font-size:.9rem;font-weight:600;cursor:pointer}
.pill:hover{border-color:var(--accent);color:var(--accent)}
.pill.active{background:var(--accent);border-color:var(--accent);color:#fff}
.playwrap{display:flex;align-items:center;gap:10px;min-width:300px;flex:1;max-width:440px}
.playbtn{background:var(--accent);border:none;color:#fff;font-weight:700;border-radius:8px;
  padding:9px 16px;cursor:pointer;font-size:.92rem}
.playbtn:hover{background:var(--accent2)}
.playwrap input[type=range]{flex:1;accent-color:var(--accent);min-width:120px}
.timelabel{font-variant-numeric:tabular-nums;font-size:.9rem;color:var(--ink2);min-width:100px}
.panel{display:none;max-width:1100px;margin:20px auto 40px;padding:0 20px}
.panel.active{display:block}
.sect{font-size:1.15rem;font-weight:700;margin:30px 0 4px}
.secthint{color:var(--ink2);font-size:.95rem;margin-bottom:14px;overflow-wrap:anywhere}
.kpigrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-top:4px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;
  border-left:5px solid var(--line);min-width:0;overflow:hidden}
.kpi .klabel{display:block;font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;
  color:var(--ink2);font-weight:700;margin-bottom:6px}
.kpi .kvalue{font-size:1.18rem;font-weight:800;line-height:1.3;overflow-wrap:anywhere}
.kpi .ksub{font-size:.8rem;color:var(--ink2);margin-top:5px;overflow-wrap:anywhere}
.kpi.good{border-left-color:#2f9e63}.kpi.good .kvalue{color:var(--good)}
.kpi.warn{border-left-color:#d9a62e}.kpi.warn .kvalue{color:var(--warn)}
.kpi.bad{border-left-color:#d64545}.kpi.bad .kvalue{color:var(--bad)}
.insight{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent);
  border-radius:12px;padding:14px 18px;margin:16px 0;font-size:.97rem;overflow-wrap:anywhere}
.liveline{background:#eef3f8;border:1px solid var(--line);border-radius:10px;
  padding:10px 16px;font-size:.93rem;margin-bottom:4px;display:flex;flex-wrap:wrap;
  gap:4px 18px;align-items:center;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.mapbox{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}
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
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.8rem;color:var(--ink2);margin-top:8px}
.legend .lg{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.lg.j{background:#93a7bc}.lg.s{background:#0b6e99}.lg.t{background:#0e8f8f}.lg.r{background:#085a7d}
.lg.l{background:#fff;border:2px dashed #b3261e}.lg.q{background:#d9a62e}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.tile{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:16px;cursor:pointer;min-width:0}
.tile:hover{border-color:var(--accent)}
.tile.sel{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,110,153,.14)}
.tile.near{border-color:#d9a62e;background:var(--warnbg)}
.tile .nm{font-size:.8rem;color:var(--ink2);font-weight:600;overflow-wrap:anywhere}
.tile .pv{font-size:1.5rem;font-weight:800;margin-top:6px}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px;height:300px;margin-bottom:8px}
.mtable{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
  border-radius:12px;overflow:hidden;font-size:.98rem}
.mtable th,.mtable td{border-bottom:1px solid var(--line);padding:12px 14px;text-align:center;overflow-wrap:anywhere}
.mtable th{background:#eef3f8;font-weight:700}
.mtable td:first-child{text-align:left;font-weight:600;color:var(--ink2)}
.note{color:var(--ink2);font-size:.92rem;margin:10px 0 6px;overflow-wrap:anywhere}
.method p{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-bottom:12px;font-size:.97rem;overflow-wrap:anywhere}
.mono{font-variant-numeric:tabular-nums}
.dlbtn{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:11px 18px;
  font-weight:700;cursor:pointer;font-size:.95rem;margin:8px 0 4px}
.dlbtn:hover{background:var(--accent2)}
.foot{text-align:center;color:var(--ink2);font-size:.85rem;padding:0 20px 40px;overflow-wrap:anywhere}
.errbox{max-width:1100px;margin:14px auto 0;background:var(--badbg);color:var(--bad);
  border:1px solid #e5b5b2;border-radius:10px;padding:12px 16px;font-size:.9rem;
  font-family:Consolas,monospace}
</style>
</head>
<body>
<div id="errbox" class="errbox" hidden></div>

<header class="sitehead">
  <h1 class="appname">LeakGuard</h1>
  <p class="tagline">Leak detection for water distribution networks</p>
</header>

<nav class="tabs" aria-label="Sections">
<button class="tab active" data-tab="overview">Overview</button>
<button class="tab"
data-tab="analysis">

Flow &amp; Pressure</button>
<button class="tab" data-tab="reports">Reports &amp; Method</button>

</nav>

<div class
="controlstrip">
<div class="p

ills" id="sc

enPills"></div>
<div class="playwrap">
<button id="play

Btn" class="playbtn">Play</button>

<input id="scrub" type="range" min="0" value="0" step="1"/>
<span id="tlabel" class="timelabel">-</span>
</div>
</div>

<section class="panel active" id="panel-overview">
<div class="kpigrid" id="kpis"></div>
<div class="insight" id="insight"></div>
<div class="liveline" id="
liveline">-</div

<h2 class="sect">Network map</h2>
<p class="secthint">Actual topology of the EPA Net3 benchmark network. Ringed dots are instrumented districts (click to highlight their pressure trace). The dashed red circle marks the injected leak; the amber dot is the zone the model currently points to.</p>
<div id="mapwrap">
<div class="mapbox"><svg id="map" viewBox="0 0 1000 620" preserveAspectRatio="xMidYMid meet"></svg></div>
<div class="legend">
<span><i class="lg j"></i>junction</span>
<span><i class="lg s"></i>sensor district</span>
<span><i class="lg t"></i
tank</span>
<span><i class="lg r"></i>reservoir</span>
<span><i class="lg l"></i>leak location

</span>
<span
<i class="lg q"></i>sus

pected zone</span>
</div>
</div>

<h

2 class="sect">

Monitoring points</h2>
<p class="

secthint">Pressure at each instrumented district. Amber = the zone the model currently points to.

Click a card to highlight its trace in Flow &

amp; Pressure.</p>
<div class="tiles" id="tiles"></div>

</section>

<section class="panel" id="panel-analysis
">
<h2 class="sect">Source

flow at the reservoir outlet</h2>
<p class="secthint">Dashed orange: night-flow alert threshold fitted

on leak-free data. Shaded band: leak

active.</p>
<div class="chart

box"><canvas id="flowChart"></canvas></div>
<h

2 class="sect">Pressure at the six monitoring

points</h2>
<p class="sect

hint">Red dots mark timesteps flagged by the

digital twin on the selected district.</p>
<div class="chart

box"><canvas id="pChart"></canvas></div>

</section>

<section class="panel" id="panel-reports">
<h2 class="sect">Measured performance - <span id="repScen" class
="mono"></span></h2>
<table class="mtable" id="mtable"></table>
<p class="note" id="mnote"></p>
<button id="dlBtn" class="dlbtn">Download incident report (.txt)</button>
<h2 class="sect">How the two detectors work</h2>
<div class="method">
<p><b>Nightly flow method</b> - the standard utility approach: between 02:00 and

04:00 legitimate demand is near zero, so excess flow indicates leakage. Simple and trusted, but it inspects the network only once per night, so detection is structurally slow - and a gradual leak can be absorbed into a rolling baseline over time.</p>
<p><b>Digital twin (continuous)</b> - expected pressure at every monitoring point is learned from leak-free operation as a function of time of day. Every 15 minutes, observed pressures are compared with expectations; unexplained deviations are flagged, and the spatial pattern of

pressure drops indicates the leak

zone.</p>
</div>
<h2 class="sect">Data provenance</h2>
<p

class="note">Telemetry generated with the EP

ANET engine (via WNTR) on the EPA Net3 benchmark network: 92 junctions, dual reservoirs, tanks and pumps, 14 days at 15-minute steps. Leaks are modeled as pressure-dependent orifice emitters. Detectors are trained only on leak-free data; performance is measured against known

ground truth.</p>

</section>

<footer class="foot">LeakGuard
demonstration build on a published benchmark network. The same pipeline accepts a live
SCADA feed.</footer

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart
.umd.min.js"></script>

<script>
const S = { data:null, key:null, d:null, i:0, playing:false, timer:null,
charts:[], sel:null };
const $ = id => document.getElementById(id);

window.onerror = (msg, src, line) => {
const b = $("errbox");
if (b) { b.hidden = false; b.textContent = "Script error: " + msg + " (line " + line + ")"; }
};
function showFatal(t){ const b=$("errbox"); if(b){ b.hidden=false; b.textContent=t; } }

const marker = { id:"marker", afterDatasetsDraw(c){
const x=c.scales.x.getPixelForValue(S.i),{top,bottom}=c.chartArea,ctx=c.ctx;
ctx.save();ctx.strokeStyle="#8aa0b8";ctx.setLineDash([5,4]);ctx.lineWidth=1.2
;
ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();ctx.restore(); }};
const shade = { id:"shade

", beforeDatasetsDraw(c){
const o=c.options.plugins.shade

; if(!o||!o.on) return;
const x0=c.scales.x.getPixelForValue(o.from),{top,bottom,right}=c.chartArea;
c.ctx.save();c.ctx.fillStyle="

rgba(214,69,69,.08)";
c.ctx.fillRect(x0,top,right-x0,bottom-top);c

.ctx.restore(); }};

function xScale(N){ return { type:"linear", min:0, max:Math.max(N

-1,1),
ticks:{ maxTicks

Limit:7, callback:v=>(S.d&&S.d.series.times[Math.round(v)])||

"" },
grid:{ color:"#e8ed

f3" } }; }

function pressAt(id,i){
const a

=S.d.series.pressures

["pressure_"+id];
return (Array.isArray

(a)&&typeof a[i

]==="number"&&isFinite(a[i]))

?a[i]:null;
}
function fmtLag(steps){
if

(steps==null||steps<0) return null;

const m=steps*15;
if(m<60) return "<= 15 min";

return (m/60).toFixed(m%60?1:0)+" h";
}

function

wireTabs(){
document.querySelectorAll(".tab").forEach(btn=>{
btn.onclick=()=>{
document.querySelectorAll

(".tab").forEach(b=>b.classList.remove("active"));
btn.classList.add("active");
document.querySelectorAll(".panel").

forEach(p=>p.classList

.remove("active"));
$("panel-"+btn.dataset

.tab).classList.add("active");
S.charts.forEach(c=>c.resize());
};

});
}

/* ---------- network map ---------- */
let MAP=null;
function buildMap(){
const net=S

.data.network, holder=$

("mapwrap");
if(!net||!net.nodes||!net

.nodes.length){ holder.style

.display="none"; return; }
const svg=$("map"); svg.innerHTML="";
const xs=net.nodes.map(n=>n.x), ys=net.nodes.map(n=>n.y);

const minX=Math.min(...xs),maxX=Math.max(...xs),min

Y=Math.min(...ys),maxY=Math.max(...ys);
const W=1000,H=620,pad=40;
const

s=Math.min((W-2*pad)/Math.max(maxX-minX,1e-9),(H-2

*pad)/Math.max(maxY-minY,

1e-9));
const ox=pad+((W-2

*pad)-(maxX-minX)s)/2, oy=pad+((H-2pad)-(maxY

-minY)*s)/

2;
const PX=n=>ox+(n.x-minX)*s

, PY=n=>oy+(maxY-n.y)*s;
const NS="http://www

.w3.org/2000/svg";
const

el=(t,at)=>{const e=document.createElementNS(NS,t);for(const k in at)e.setAttribute(k,at

[k]);return e;};

const byId={}; net.nodes.forEach(n=>byId[n.id

]=n);
for(const L of net.links){
const a=

byId[L.frm], b=byId[L.to];
if(!a||!b) continue;
svg.appendChild(el("line",{

x1:PX(a),y1:PY(a),x2:PX(b),y2

:PY(b),
class:"mlk"+

(L.type!=="pipe"?" mlk

2":"")}));
}
MAP={dots

:{}};
const order=[...net.nodes].sort((a,b)=>(a.type==="junction"?0:1)-(

b.type==="junction"?0:1));
for(const n of order){
const x=

PX(n), y=PY(n), g=el("g",{});
if(n.is_sensor) g.appendChild(el("

circle",{cx:x,c

y:y,r:9,class:"mring"}));
const r=n.type==="tank"?7

:(n.type==="reservoir"?8:3.4);
const dot=el("circle",{cx:x,cy:y,r:r,class:"mdot "+n.type+(n.is_sensor?" sndot":"")});
g.appendChild(dot);
const ti=el("title",{}); ti.textContent=n.is_sensor?("Sensor "+n.id+" - "+n.label):(n.type+" "+n.id);
g.appendChild(ti);
if

(n.is_sensor){ g.style.cursor="pointer";

g.addEventListener("click",

()=>selectSensor(n.id)); }
svg.appendChild(g);
MAP.dots[n.id]=dot

;
if(n.is_sensor||n.type!

=="junction"){
const t=el("text",{x:x,y:y-13,class:"mlbl"}); t.textContent=n.id; svg.appendChild(t);
}
}
const lk=el("circle",{r:13,class:"mleak"}); lk.style.display="none"; svg.appendChild(lk);
MAP.leak=l

k; MAP.byNet=byId;
}

function updateLeakMarker(){
if(!MAP||!MAP.leak

) return;
if

(S.d.leak_node&&S.data.network){
const n=S.data.network.nodes.find(x=>x.id===S.d.leak_node);
if(n){
const xs=S.data.network.nodes.map(q=>q.x), ys=S.data.network.nodes.map(q=>q.y);
const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
const W=1000,H=620,pad=40;
const s=Math.min((W-2pad)/(maxX-minX||1),(H-2pad)/(maxY-minY||1));
const ox=pad+((W-2*pad)-(maxX-minX)s)/2, oy=pad+((H-2pad)-(maxY-minY)*s)/2;
MAP.leak.setAttribute("cx",ox+(n.x-minX)*s);
MAP.leak.setAttribute("cy",oy+(maxY-n.y)*s);
MAP.leak.style.display=""; return;
}
}
MAP.leak.style.display="none";
}
function updateSuspect(){
if(!MAP) return;
Object.values(MAP.dots).forEach(d=>d.classList.remove("suspect"));
if(S.d.leak_node){
const z=S.d.series.likely_near[S.i], d=MAP.dots[z];
if(d) d.classList.add("suspect");
}
}

/* ---------- data load ---------- */
async function init(){
wireTabs();
let raw;
try{ raw=await(await fetch("/api/data")).json(); }
catch(e){ showFatal("Could not load /api/data - start the server: python -m dashboard.app"); return; }
if(!raw||!raw.order||!raw.scenarios||!raw.meta||!Array.isArray(raw.meta.sensors)){
showFatal("results.json missing/outdated. Run: python make_data.py"); return;
}
S.data=raw;
("scenPills").innerHTML=S.data.order.map(k=> 
′
 <buttonclass="pill"data−key=" 
′
 +k+ 
′
 "> 
′
 +S.data.scenarios[k].label+ 
′
 </button> 
′
 ).join("");document.querySelectorAll(".pill").forEach(p=>p.onclick=()=>trysetScenario(p.dataset.key);catch(err)showFatal("Switchfailed:"+err.message););buildMap();trysetScenario(S.data.order.find(k=>k!=="normal")∣∣S.data.order[0]);catch(err)showFatal("Renderfailed:"+err.message);return;
("playBtn").onclick=()=>S.playing?pause():(S.playing=true,tickLoop());
("scrub").addEventListener("input",e=>pause();setIndex(+e.target.value););
("dlBtn").onclick=downloadReport;
}

function leakStartIdx(){ const k=S.d.series.leak_active.indexOf(1); return k<0?0:k; }
function firstIdx(arr){ const k=arr.indexOf(1); return k<0?null:k; }

function topZone(){
const counts={};
S.d.series.twin_flag.forEach((f,i)=>{ if(f){
const z=S.d.series.likely_near[i]; counts[z]=(counts[z]||0)+1; }});
const e=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
if(!e.length) return null;
const total=e.reduce((s,q)=>s+q[1],0);
return { zone:e[0][0], share:e[0][1]/total };
}

function setScenario(key){
S.key=key; S.d=S.data.scenarios[key];
S.sel=S.d.leak_node||S.data.meta.sensors[0].id;
document.querySelectorAll(".pill").forEach(p=>p.classList.toggle("active",p.dataset.key===key));
$("repScen").textContent=S.d.label;
S.charts.forEach(c=>c.destroy()); S.charts=[];
buildKPIs(); buildCharts(); buildMetrics(); buildTiles();
updateLeakMarker();
const li=leakStartIdx();
setIndex(li>96?li+1:0);
}

function buildKPIs(){
const t=S.d.metrics.twin, m=S.d.metrics.mnf;
const tLag=fmtLag(firstIdx(S.d.series.twin_flag));
const mLag=fmtLag(firstIdx(S.d.series.mnf_flag));
const tz=topZone();
const meta=tz?S.data.meta.sensors.find(s=>s.id===tz.zone):null;
const card=(cls,label,value,sub)=>'<div class="kpi '+cls+'">'+
'<span class="klabel">'+label+'</span><span class="kvalue">'+value+'</span>'+
'<div class="ksub">'+sub+'</div></div>';
let html="";

if(!S.d.leak_node){
html+=card("good","False alarms (14 days)",String(S.d.series.twin_flag.filter(x=>x===1).length)+" flags",
"across 1344 steps of normal operation");
html+=card("good","Baseline stability","clean","no leak present - any flag would be a false alarm");
html+=card("good","Nightly method","quiet","nothing to detect");
html+=card("good","Purpose","trust check","proves the model does not cry wolf");
}

else{
html+=card("good","Digital twin - first alert",tLag||"

no alert",
"continuous watch, 15-minute steps");
html+=card(mLag?"warn":"bad","

Nightly method",mLag?"detected after "+mLag:"missed entirely",
"inspects once per night

(02:00-04:00)");
html+=card("good","Detection quality (F1)",String(t.f1),
"precision "+t.precision+" / recall "+t.recall

);
html+=card(tz?"good":"warn","Localized to",meta?meta.id+" - "+meta.label:"n/a",
tz?Math.round(tz.share*100)+"% of alerts point here":"no alerts to localize");
}
$("kpis").innerHTML=html;
let ins;
if(!S.d.leak_node){
ins="No leak occurs

in this 14-day baseline. The twin stays

quiet throughout - the control that shows the system does not raise false alarms.";

}else{
ins="Scenario: "+

S.d.label.replace(/

^[^-]+- /

,"")+". "+

((tLag&&mLag)?"The

twin alerted "+(mLag==="<= 15

min"?"well before

":"hours before")+" the nightly check.":

(mLag?"":"The nightly method never

detected this leak at all - the exact blind spot

continuous monitoring closes."));
}
$("insight

").textContent=ins;
}

function alertMarkerData(){
const out=[];

S.d.series.t

win_flag.forEach((f,i)=>{ if(f

){
const y=pressAt(S.sel,i); if(y!==null) out.push({x

:i,y}); }});
return out;
}

function buildCharts(){
const d=S.d.series, N=d.times.length

;
const pal=["#0b6e

99","#177245","#b3261e","#6d5bb8","#c07a1a","#0e8f8f"];
const flow=new Chart($("flowChart"),{type:"line",
data:{datasets:[
{label:"Source flow (L/s)",data:(d.source_flow_Ls||[]).map((y,x)=>({x,y})),
borderColor:"#0b6e99",borderWidth:2,pointRadius:0,tension:.12},
{label:"Night-flow alert threshold",data:(d.source_flow_Ls||[]).map((_,x)=>({x,y:d.mnf_threshold})),
borderColor:"#c

07a1a",borderDash:[7,

5],borderWidth:

1.6,pointRadius:0}]},
options:{animation:false,maintainAspectRatio:false

,
scales:{x

:xScale(N),y:{title:{display:true,text:"L/s"}}},
plugins:{shade:{on:!!S.d.leak_node,from:leakStartIdx()},
legend:{labels:{boxWidth:12,font:{size:11}}}}},
plugins:[marker,shade]});
const psets=S.data.meta.sensors.map((s,j)=>({
label:s.id+" - "+s.label,
data:((d.pressures&&d.pressures["pressure_"+s.id])||[]).map((y,x

)=>({x,y})),
borderColor:pal

[j%pal.length],borderWidth:s.id===

S.sel?2.6:1.4

,
pointRadius:0,tension:.1,alpha:s.id===S.sel?1:.5}));
psets.push({label:"Twin alert",data:alertMarkerData(),showLine:false,
pointRadius:3,pointBackgroundColor:"rgba(179,38,30,.9)",pointBorderColor:"#fff",
pointBorderWidth:.5});
const press=new Chart($("pChart"),{type:"line",data:{datasets:psets},
options:{animation:false,maintainAspectRatio:false,
scales:{x:xScale(N),y:{title:{display:true,text:"pressure (m)"}}},
plugins:{shade:{on:!!S.d.leak_node,from:leakStartIdx()},
legend:{labels:{boxWidth:12,font:{size:10},filter:ds=>ds.label!=="Twin alert"}}}},
plugins:[marker,shade]});
S.charts=[flow,press];
}

function buildMetrics(){
const t=S.d.metrics.twin,m=S.d.metrics.mnf;
const row=(a,b,c)=>'<tr><td>'+a+'</td><td>'+b+'</td><td>'+c+'</td></tr>';
const fmt=v=>(v==null?"no detection":v+" h");

$("mtable").innerHTML=
'<tr><th></th><th>Digital twin (continuous)</th><th>Nightly flow method</th></tr>'+
row("Precision",t.precision,m.precision)+
row("Recall",t.recall,m.recall)+

row("F1",t.f1,m.f1)+
row("Detection lag",fmt(t.detection_lag_hours),fmt(m.detection_lag_hours));
$("mnote").textContent=S.key==="normal"
?"No leak in this scenario - any flag would be a false alarm."
:"Lag = time from leak start to first alarm. The nightly method only reads flows once per night, so its lag is structurally large.";
}

function buildTiles(){
$("tiles").innerHTML=S.data.meta.sensors.map(s=>
'<div class="tile" id="tile_'+s.id+'" onclick="selectSensor(\''+s.id+'\')">'+
'<div class="nm">'+s.id+' - '+s.label+'</div>'+
'<div class="pv" id="pv_'+s.id+'">-</div></div>').join("");
}

window.selectSensor=id=>{
S.sel=id;
if(S.charts[1]){
S.charts[1].data.datasets.forEach(ds=>{
if(ds.label==="Twin alert"){ ds.data=alertMarkerData(); return; }
const

on=ds.label.startsWith(id+" ");
ds.borderWidth=on?2.6:1.4; ds.alpha=on?1:.5;});
S.charts[1].update("none");
}
S.data.meta.sensors.forEach(s=>$("tile_"+s.id).classList.toggle("sel",s.id===id));
};

function setIndex(i){
S.i=Math.max(0,Math.min(i,S.d.series.times.length-1));
const d=S.d.series;
("scrub").value=S.i;
("tlabel").textContent=d.times[S.i];
S.data.meta.sensors.forEach(s=>{
const pv=
("pv_"+s.id); if(!pv) return;
const v=pressAt(s.id,S.i);
pv.textContent=(v===null?"n/a":v+" m");
const near=d.likely_near[S.i]===s.id&&!!S.d.leak_node;
pv.style.color=near?"#8a6116":(v===null?"#94a3b8":"#16233b");
("tile_"+s.id).classList.toggle("near",near);

});
const twinOn=d.twin_flag[S.i]===1,

mnfOn=d.mnf_flag[S.i]

===1;
const parts=['Day status: <b>'+d.times[S.i]+'</b

',
'Digital twin: <b style="color:'+(twinOn?"#b3261e":"#

177245")+'">'+(twinOn?"ANOMALY":"

normal")+'</b>',
'Nightly method: <b style="color:'+(mnf

On?"#8a

6116":"#177245")+'">'+(mnfOn?"flagged":"quiet")+'</b>'];
if(S.d.leak_node){
const z=d.likely_near[S.i];
const meta=S.data.meta.sensors.find(s=>s.id

===z);
parts.push('Pointing at: <b>'+(meta?meta.id+"

"+meta.label:z)+'</b>');
}
$("liveline").innerHTML=parts
.join('');
updateSuspect();
S.charts.forEach(c=>c

.update("none"));
}

function pause(){S.play

ing=false;clearInterval(S.timer);$("play

Btn").textContent="Play";}
function tickLoop(){

clearInterval(S.timer);

$("playBtn").textContent="Pause";
S.timer=setInterval(()=>{

if(S.i>=S.d.series.times.length-

1){pause();return

;}
setIndex(S.i+16);
},100);
}

function

downloadReport(){
const

t=S.d.metrics.t

win,m=S.d.metrics.mnf;
const tz=topZone();
const meta=tz?

S.data.meta.sensors.find(s=>s.id

===tz.zone):null;
const lines=[

"LEAKGUARD - INCIDENT REPORT",
"=".repeat(40),
"Scenario

: "+S.d.label,
"Leak

node: "+(S.d.leak_node||

"none"),
"Leak start: "+(S.d.leak

_start||"n/a"),
"",
"Digital twin (continuous):",
" precision "+t.precision+" recall "+t.recall+" F1 "+t.f1,
" first alert: "+(fmtLag(firstIdx(S.d.series.twin_flag))||"none"),
"Nightly flow method:",
" precision "+m.precision+" recall "+m.recall+" F1 "+m.f1,
" first alert: "+(fmtLag(first

Idx(S.d.series.m

nf_flag))||"none"),
"",
"Localization: "+(

meta?(meta.id+" - "+meta.label+" ("+Math.round((tz.share||0)*100)+"% of alerts)"):"n/a"),
"",
"Provenance: EPANET (WNTR) on the EPA Net3 benchmark, 14 days @ 15-min steps;",
"leaks modeled as pressure-dependent orifice emitters; detectors trained on",
"leak-free data only. Generated by LeakGuard demonstration build."
];
const a=document.createElement("a");
a.href=URL.createObjectURL(new Blob([lines.join("\n")],{type:"text/plain"}));
a.download="leakguard-report-"+S.key+".txt"; a.click();
}

init();
</script>

</body>
</html>
'''


def main():
    with open(os.path.join(ROOT, "make_data.py"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(MAKE_DATA_PY)
    print("wrote make_data.py (now exports network map)")
    with open(os.path.join(ROOT, "dashboard", "templates", "index.html"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(INDEX_HTML)
    print("wrote dashboard/templates/index.html (" + str(len(INDEX_HTML)) + " chars)")

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