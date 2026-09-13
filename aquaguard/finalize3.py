#!/usr/bin/env python3
# finalize3.py - SELF-CONTAINED FlowSentry: all CSS+JS inlined in one HTML file.
# No static files needed, no cache issues, no script-tag 404s. Port 9000.
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

APP_PY = r'''"""FlowSentry backend. Run: python -m dashboard.app -> http://localhost:9000"""
import json
import os

from flask import Flask, jsonify, send_file

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(APP_DIR, "templates", "index.html")
RESULTS = os.path.join(APP_DIR, "data", "results.json")
app = Flask(__name__)


@app.route("/")
def index():
    # served raw: no template processing, fully self-contained page
    return send_file(PAGE)


@app.route("/api/data")
def api_data():
    if not os.path.exists(RESULTS):
        return jsonify(error="results.json missing - run: python run_pipeline.py"), 500
    with open(RESULTS) as f:
        return jsonify(json.load(f))


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 9000)), debug=True)
'''

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>FlowSentry - Water Network Leak Detection</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"/>
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
.sitehead{text-align:center;padding:34px 16px 10px}
.appname{font-size:2.6rem;font-weight:800;letter-spacing:-.5px;color:var(--ink)}
.tagline{color:var(--ink2);font-size:1.02rem;margin-top:4px}
.tabs{display:flex;justify-content:center;gap:6px;margin:22px auto 0;max-width:760px;
  background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px}
.tab{flex:1;border:none;background:transparent;color:var(--ink2);font-size:1rem;
  font-weight:600;padding:11px 10px;border-radius:8px;cursor:pointer}
.tab:hover{background:#eef3f8;color:var(--ink)}
.tab.active{background:var(--accent);color:#fff}
.controlstrip{max-width:1100px;margin:16px auto 0;padding:0 20px;display:flex;
  flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between}
.pills{display:flex;gap:8px;flex-wrap:wrap}
.pill{border:1.5px solid var(--line);background:var(--card);color:var(--ink2);
  border-radius:999px;padding:9px 16px;font-size:.92rem;font-weight:600;cursor:pointer}
.pill:hover{border-color:var(--accent);color:var(--accent)}
.pill.active{background:var(--accent);border-color:var(--accent);color:#fff}
.playwrap{display:flex;align-items:center;gap:10px;min-width:300px;flex:1;max-width:460px}
.playbtn{background:var(--accent);border:none;color:#fff;font-weight:700;border-radius:8px;
  padding:9px 16px;cursor:pointer;font-size:.92rem}
.playbtn:hover{background:var(--accent2)}
.playwrap input[type=range]{flex:1;accent-color:var(--accent)}
.timelabel{font-variant-numeric:tabular-nums;font-size:.9rem;color:var(--ink2);min-width:110px}
.panel{display:none;max-width:1100px;margin:20px auto 40px;padding:0 20px}
.panel.active{display:block}
.sect{font-size:1.15rem;font-weight:700;margin:30px 0 4px}
.secthint{color:var(--ink2);font-size:.95rem;margin-bottom:14px}
.statusgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:4px}
.statcard{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;
  border-left:5px solid var(--line)}
.statlabel{display:block;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;
  color:var(--ink2);font-weight:600;margin-bottom:6px}
.statvalue{font-size:1.25rem;font-weight:700}
.statcard.ok{border-left-color:#2f9e63}.statcard.ok .statvalue{color:var(--good)}
.statcard.warn{border-left-color:#d9a62e}.statcard.warn .statvalue{color:var(--warn)}
.statcard.alert{border-left-color:#d64545;background:var(--badbg)}
.statcard.alert .statvalue{color:var(--bad)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.tile{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:16px;cursor:pointer}
.tile:hover{border-color:var(--accent)}
.tile.sel{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,110,153,.14)}
.tile.near{border-color:#d9a62e;background:var(--warnbg)}
.tile .nm{font-size:.8rem;color:var(--ink2);font-weight:600}
.tile .pv{font-size:1.5rem;font-weight:800;margin-top:6px;color:var(--ink)}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px;height:300px;margin-bottom:8px}
.mtable{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
  border-radius:12px;overflow:hidden;font-size:.98rem}
.mtable th,.mtable td{border-bottom:1px solid var(--line);padding:12px 14px;text-align:center}
.mtable th{background:#eef3f8;color:var(--ink);font-weight:700}
.mtable td:first-child{text-align:left;font-weight:600;color:var(--ink2)}
.note{color:var(--ink2);font-size:.92rem;margin:10px 0 6px}
.method p{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-bottom:12px;font-size:.97rem}
.mono{font-variant-numeric:tabular-nums}
.foot{text-align:center;color:var(--ink2);font-size:.85rem;padding:0 20px 40px}
.errbox{max-width:1100px;margin:14px auto 0;background:var(--badbg);color:var(--bad);
  border:1px solid #e5b5b2;border-radius:10px;padding:12px 16px;font-size:.9rem;
  font-family:Consolas,monospace}
</style>
</head>
<body>
<div id="errbox" class="errbox" hidden></div>

<header class="sitehead">
  <h1 class="appname">FlowSentry</h1>
  <p class="tagline">Leak detection for water distribution networks</p>
</header>

<nav class="tabs" aria-label="Sections">
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
  <div class="statusgrid">
    <div class="statcard" id="statusTwin"><span class="statlabel">Digital twin</span><span class="statvalue" id="vTwin">-</span></div>
    <div class="statcard" id="statusMnf"><span class="statlabel">Nightly flow method</span><span class="statvalue" id="vMnf">-</span></div>
    <div class="statcard" id="statusLoc"><span class="statlabel">Likely leak zone</span><span class="statvalue" id="vLoc">-</span></div>
    <div class="statcard" id="statusScore"><span class="statlabel">Anomaly score</span><span class="statvalue" id="vScore">-</span></div>
  </div>
  <h2 class="sect">Monitoring points</h2>
  <p class="secthint">Live pressure at each instrumented district. Amber highlight marks the zone the model currently points to. Click a card to highlight its line in the Flow &amp; Pressure tab.</p>
  <div class="tiles" id="tiles"></div>
</section>

<section class="panel" id="panel-analysis">
  <h2 class="sect">Source flow at the reservoir outlet</h2>
  <p class="secthint">The dashed orange line is the night-flow alert threshold, fitted on leak-free data. The shaded band marks the true leak window.</p>
  <div class="chartbox"><canvas id="flowChart"></canvas></div>
  <h2 class="sect">Pressure at the six monitoring points</h2>
  <p class="secthint">A leak pulls pressure down near the failure point while the normal daily pattern continues elsewhere.</p>
  <div class="chartbox"><canvas id="pChart"></canvas></div>
</section>

<section class="panel" id="panel-reports">
  <h2 class="sect">Measured performance - <span id="repScen" class="mono"></span></h2>
  <table class="mtable" id="mtable"></table>
  <p class="note" id="mnote"></p>
  <h2 class="sect">How the two detectors work</h2>
  <div class="method">
    <p><b>Nightly flow method</b> - the standard approach used by utilities: each night between 02:00 and 04:00, legitimate demand is near zero, so flow above the baseline indicates leakage. It is simple and trusted, but it only inspects the network once per day, so detection is inherently slow - and an ongoing leak can be absorbed into a rolling baseline over time.</p>
    <p><b>Digital twin (continuous)</b> - a model of expected pressure at every monitoring point is learned from leak-free operation as a function of time of day. Every 15 minutes, observed pressures are compared with expected values. Deviations that the model of normal operation cannot explain are flagged, and the pattern of pressure drops across districts indicates where the leak is.</p>
  </div>
  <h2 class="sect">Data provenance</h2>
  <p class="note">Telemetry is generated with the EPANET engine (via WNTR) on the EPA Net3 benchmark network - 92 junctions, dual reservoirs, tanks and pumps over 14 days at 15-minute steps. Detectors are trained only on leak-free data. Performance is measured against known ground truth, not asserted.</p>
</section>

<footer class="foot">FlowSentry - demonstration build. Simulated telemetry from a published benchmark network; the same pipeline accepts a real SCADA feed.</footer>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const S = { data: null, key: null, d: null, i: 0, playing: false, timer: null,
            charts: [], sel: null };
const $ = id => document.getElementById(id);

window.onerror = (msg, src, line) => {
  const b = $("errbox");
  if (b) { b.hidden = false; b.textContent = "Script error: " + msg + " (line " + line + ")"; }
};
function showFatal(t){ const b=$("errbox"); if(b){ b.hidden=false; b.textContent=t; } }

const marker = { id:"marker", afterDatasetsDraw(c){
  const x=c.scales.x.getPixelForValue(S.i),{top,bottom}=c.chartArea,ctx=c.ctx;
  ctx.save();ctx.strokeStyle="#8aa0b8";ctx.setLineDash([5,4]);ctx.lineWidth=1.2;
  ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();ctx.restore(); }};
const shade = { id:"shade", beforeDatasetsDraw(c){
  const o=c.options.plugins.shade; if(!o||!o.on) return;
  const x0=c.scales.x.getPixelForValue(o.from),{top,bottom,right}=c.chartArea;
  c.ctx.save();c.ctx.fillStyle="rgba(214,69,69,.08)";
  c.ctx.fillRect(x0,top,right-x0,bottom-top);c.ctx.restore(); }};

function xScale(N){ return { type:"linear", min:0, max:Math.max(N-1,1),
  ticks:{ maxTicksLimit:7, callback:v=>(S.d&&S.d.series.times[Math.round(v)])||"" },
  grid:{ color:"#e8edf3" } }; }

function pressAt(series,id,i){
  const a=series.pressures?series.pressures["pressure_"+id]:null;
  if(!Array.isArray(a)) return null;
  const v=a[i]; return (typeof v==="number"&&isFinite(v))?v:null;
}

function wireTabs(){
  document.querySelectorAll(".tab").forEach(btn=>{
    btn.onclick=()=>{
      document.querySelectorAll(".tab").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".panel").forEach(p=>p.classList.remove("active"));
      $("panel-"+btn.dataset.tab).classList.add("active");
      S.charts.forEach(c=>c.resize());
    };
  });
}

async function init(){
  wireTabs();
  let raw;
  try{ raw=await(await fetch("/api/data")).json(); }
  catch(e){ showFatal("Could not load /api/data - is the server running? (python -m dashboard.app)"); return; }
  if(!raw||!raw.order||!raw.scenarios||!raw.meta||!Array.isArray(raw.meta.sensors)){
    showFatal("results.json is missing or outdated. Run: python run_pipeline.py  then restart the server."); return;
  }
  S.data=raw;

  const problems=[];
  for(const k of S.data.order){
    const sc=S.data.scenarios[k]||{};
    for(const s of S.data.meta.sensors){
      const a=(sc.series&&sc.series.pressures)?sc.series.pressures["pressure_"+s.id]:null;
      if(!Array.isArray(a)||!a.length) problems.push(k+" / sensor "+s.id);
    }
  }
  if(problems.length) showFatal("Missing pressure data for: "+problems.join(", ")+
    ".  Fix: delete data/scenario_*.csv, run python run_pipeline.py, restart the server.");

  $("scenPills").innerHTML=S.data.order.map(k=>
    '<button class="pill" data-key="'+k+'">'+S.data.scenarios[k].label+'</button>').join("");
  document.querySelectorAll(".pill").forEach(p=>p.onclick=()=>{
    try{ setScenario(p.dataset.key); }catch(err){ showFatal("Switch failed: "+err.message); }
  });

  try{ setScenario(S.data.order.find(k=>k!=="normal")||S.data.order[0]); }
  catch(err){ showFatal("Initial render failed: "+err.message); return; }
  wirePlay();
}

function leakIdx(){ const k=S.d.series.leak_active.indexOf(1); return k<0?0:k; }

function setScenario(key){
  S.key=key; S.d=S.data.scenarios[key];
  S.sel=S.d.leak_node||S.data.meta.sensors[0].id;
  document.querySelectorAll(".pill").forEach(p=>p.classList.toggle("active",p.dataset.key===key));
  $("repScen").textContent=S.d.label;
  S.charts.forEach(c=>c.destroy()); S.charts=[];
  buildCharts(); buildMetrics(); buildTiles();
  const li=S.d.series.leak_active.indexOf(1);
  setIndex(li>96?li-96:0);
}

function buildCharts(){
  const d=S.d.series, N=d.times.length;
  const pal=["#0b6e99","#177245","#b3261e","#6d5bb8","#c07a1a","#0e8f8f"];
  const flow=new Chart($("flowChart"),{type:"line",
    data:{datasets:[
      {label:"Source flow (L/s)",data:(d.source_flow_Ls||[]).map((y,x)=>({x,y})),
       borderColor:"#0b6e99",borderWidth:2,pointRadius:0,tension:.12},
      {label:"Night-flow alert threshold",data:(d.source_flow_Ls||[]).map((_,x)=>({x,y:d.mnf_threshold})),
       borderColor:"#c07a1a",borderDash:[7,5],borderWidth:1.6,pointRadius:0}]},
    options:{animation:false,maintainAspectRatio:false,
      scales:{x:xScale(N),y:{title:{display:true,text:"L/s"}}},
      plugins:{shade:{on:!!S.d.leak_node,from:leakIdx()},
               legend:{labels:{boxWidth:12,font:{size:11}}}}},
    plugins:[marker,shade]});

  const psets=S.data.meta.sensors.map((s,j)=>({
    label:s.id+" - "+s.label,
    data:((d.pressures&&d.pressures["pressure_"+s.id])||[]).map((y,x)=>({x,y})),
    borderColor:pal[j%pal.length],borderWidth:s.id===S.sel?2.6:1.4,
    pointRadius:0,tension:.1,alpha:s.id===S.sel?1:.5}));
  const press=new Chart($("pChart"),{type:"line",data:{datasets:psets},
    options:{animation:false,maintainAspectRatio:false,
      scales:{x:xScale(N),y:{title:{display:true,text:"pressure (m)"}}},
      plugins:{shade:{on:!!S.d.leak_node,from:leakIdx()},
               legend:{labels:{boxWidth:12,font:{size:10}}}}},
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
    ?"No leak occurs in this scenario - any flag here would be a false alarm."
    :"Detection lag = time from the true leak start to the first alarm. The nightly method inspects flows once per night (02:00-04:00), so its lag is structurally large.";
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
      const on=ds.label.startsWith(id+" ");
      ds.borderWidth=on?2.6:1.4; ds.alpha=on?1:.5;});
    S.charts[1].update("none");
  }
  S.data.meta.sensors.forEach(s=>$("tile_"+s.id).classList.toggle("sel",s.id===id));
};

function setIndex(i){
  S.i=Math.max(0,Math.min(i,S.d.series.times.length-1));
  const d=S.d.series;
  $("scrub").value=S.i;
  $("tlabel").textContent=d.times[S.i];

  S.data.meta.sensors.forEach(s=>{
    const pv=$("pv_"+s.id); if(!pv) return;
    const v=pressAt(d,s.id,S.i);
    pv.textContent=(v===null?"n/a":v+" m");
    const near=d.likely_near[S.i]===s.id&&!!S.d.leak_node;
    $("tile_"+s.id).classList.toggle("near",near);
  });

  const set=(id,cls,txt)=>{const e=$(id);e.className="statcard "+cls;
    e.querySelector(".statvalue").textContent=txt;};
  set("statusTwin",d.twin_flag[S.i]?"alert":"ok",
      d.twin_flag[S.i]?"Anomaly detected":"Normal");
  set("statusMnf",d.mnf_flag[S.i]?"warn":"ok",
      d.mnf_flag[S.i]?"Flagged":"Quiet (nightly check)");
  if(!S.d.leak_node) set("statusLoc","ok","None");
  else{
    const near=d.likely_near[S.i];
    const meta=S.data.meta.sensors.find(s=>s.id===near);
    set("statusLoc",near===S.d.leak_node?"alert":"warn",
        meta?meta.id+" - "+meta.label:near);
  }
  const sc=Number(d.anomaly_score[S.i]);
  set("statusScore",isFinite(sc)&&sc>0.3?"warn":"ok",isFinite(sc)?sc.toFixed(3):"n/a");
  S.charts.forEach(c=>c.update("none"));
}

function wirePlay(){
  $("scrub").max=S.d.series.times.length-1;
  $("scrub").addEventListener("input",e=>{pause();setIndex(+e.target.value);});
  $("playBtn").onclick=()=>S.playing?pause():(S.playing=true,tickLoop());
}
function pause(){S.playing=false;clearInterval(S.timer);$("playBtn").textContent="Play";}
function tickLoop(){
  clearInterval(S.timer);$("playBtn").textContent="Pause";
  const step=16;
  S.timer=setInterval(()=>{
    if(S.i>=S.d.series.times.length-1){pause();return;}
    setIndex(S.i+step);
  },100);
}

init();
</script>
</body>
</html>
'''


def main():
    for rel, content in [("dashboard/app.py", APP_PY),
                         ("dashboard/templates/index.html", INDEX_HTML)]:
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("wrote", rel, "(" + str(len(content)) + " chars)")

    print()
    rj = os.path.join(ROOT, "dashboard", "data", "results.json")
    if os.path.exists(rj):
        with open(rj) as f:
            d = json.load(f)
        sens = [s["id"] for s in d.get("meta", {}).get("sensors", [])]
        print("results.json: FOUND")
        print("  scenarios:", d.get("order"))
        print("  sensors:", sens)
        if not d.get("order") or not sens:
            print("  WARNING: structure looks wrong -> run python run_pipeline.py")
    else:
        print("results.json: MISSING -> after starting, run: python run_pipeline.py")
        print("  then restart the server.")
    print()
    print("ALL SET. Start with:  python -m dashboard.app")
    print("Then open http://localhost:9000 and press Ctrl+Shift+R")
    print("NOTE: do not run scripts from any other chat session - they overwrite these files.")


if __name__ == "__main__":
    main()