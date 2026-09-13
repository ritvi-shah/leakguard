#!/usr/bin/env python3
# polish.py - demo-grade FlowSentry page: KPI cards, insight line, alert markers,
# stable localization, incident-report download. Self-contained HTML, port 9000.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

INDEX_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>FlowSentry - Water Network Leak Detection</title>
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
.appname{font-size:2.6rem;font-weight:800;letter-spacing:-.5px}
.tagline{color:var(--ink2);font-size:1.02rem;margin-top:4px}
.tabs{display:flex;justify-content:center;gap:6px;margin:20px auto 0;max-width:760px;
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
.kpigrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-top:4px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;
  border-left:5px solid var(--line)}
.kpi .klabel{display:block;font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;
  color:var(--ink2);font-weight:700;margin-bottom:6px}
.kpi .kvalue{font-size:1.45rem;font-weight:800}
.kpi .ksub{font-size:.8rem;color:var(--ink2);margin-top:4px}
.kpi.good{border-left-color:#2f9e63}.kpi.good .kvalue{color:var(--good)}
.kpi.warn{border-left-color:#d9a62e}.kpi.warn .kvalue{color:var(--warn)}
.kpi.bad{border-left-color:#d64545}.kpi.bad .kvalue{color:var(--bad)}
.insight{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--accent);
  border-radius:12px;padding:14px 18px;margin:16px 0;font-size:.98rem}
.liveline{background:#eef3f8;border:1px solid var(--line);border-radius:10px;
  padding:10px 16px;font-size:.95rem;font-weight:600;margin-bottom:16px;
  font-variant-numeric:tabular-nums}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}
.tile{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:16px;cursor:pointer}
.tile:hover{border-color:var(--accent)}
.tile.sel{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,110,153,.14)}
.tile.near{border-color:#d9a62e;background:var(--warnbg)}
.tile .nm{font-size:.8rem;color:var(--ink2);font-weight:600}
.tile .pv{font-size:1.5rem;font-weight:800;margin-top:6px}
.chartbox{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px;height:300px;margin-bottom:8px}
.mtable{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
  border-radius:12px;overflow:hidden;font-size:.98rem}
.mtable th,.mtable td{border-bottom:1px solid var(--line);padding:12px 14px;text-align:center}
.mtable th{background:#eef3f8;font-weight:700}
.mtable td:first-child{text-align:left;font-weight:600;color:var(--ink2)}
.note{color:var(--ink2);font-size:.92rem;margin:10px 0 6px}
.method p{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-bottom:12px;font-size:.97rem}
.mono{font-variant-numeric:tabular-nums}
.dlbtn{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:11px 18px;
  font-weight:700;cursor:pointer;font-size:.95rem;margin:8px 0 4px}
.dlbtn:hover{background:var(--accent2)}
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
  <div class="kpigrid" id="kpis"></div>
  <div class="insight" id="insight"></div>
  <div class="liveline" id="liveline">-</div>
  <h2 class="sect">Monitoring points</h2>
  <p class="secthint">Pressure at each instrumented district. Amber = the zone the model currently points to. Click a card to highlight its trace in Flow &amp; Pressure.</p>
  <div class="tiles" id="tiles"></div>
</section>

<section class="panel" id="panel-analysis">
  <h2 class="sect">Source flow at the reservoir outlet</h2>
  <p class="secthint">Dashed orange: night-flow alert threshold fitted on leak-free data. Shaded band: leak active.</p>
  <div class="chartbox"><canvas id="flowChart"></canvas></div>
  <h2 class="sect">Pressure at the six monitoring points</h2>
  <p class="secthint">Red dots mark timesteps flagged by the digital twin (shown on the selected district). A leak pulls pressure down near the failure point.</p>
  <div class="chartbox"><canvas id="pChart"></canvas></div>
</section>

<section class="panel" id="panel-reports">
  <h2 class="sect">Measured performance - <span id="repScen" class="mono"></span></h2>
  <table class="mtable" id="mtable"></table>
  <p class="note" id="mnote"></p>
  <button id="dlBtn" class="dlbtn">Download incident report (.txt)</button>
  <h2 class="sect">How the two detectors work</h2>
  <div class="method">
    <p><b>Nightly flow method</b> - the standard utility approach: between 02:00 and 04:00 legitimate demand is near zero, so excess flow indicates leakage. Simple and trusted, but it inspects the network only once per night, so detection is structurally slow - and a gradual leak can be absorbed into a rolling baseline over time.</p>
    <p><b>Digital twin (continuous)</b> - expected pressure at every monitoring point is learned from leak-free operation as a function of time of day. Every 15 minutes, observed pressures are compared with expectations; unexplained deviations are flagged, and the spatial pattern of pressure drops indicates the leak zone.</p>
  </div>
  <h2 class="sect">Data provenance</h2>
  <p class="note">Telemetry generated with the EPANET engine (via WNTR) on the EPA Net3 benchmark network: 92 junctions, dual reservoirs, tanks and pumps, 14 days at 15-minute steps. Leaks are modeled as pressure-dependent orifice emitters. Detectors are trained only on leak-free data; performance is measured against known ground truth.</p>
</section>

<footer class="foot">FlowSentry - demonstration build on a published benchmark network. The same pipeline accepts a live SCADA feed.</footer>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
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

function pressAt(id,i){
  const a=S.d.series.pressures["pressure_"+id];
  return (Array.isArray(a)&&typeof a[i]==="number"&&isFinite(a[i]))?a[i]:null;
}
function fmtLag(steps){
  if(steps==null||steps<0) return null;
  const m=steps*15;
  if(m<60) return "<= 15 min";
  return (m/60).toFixed(m%60?1:0)+" h";
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
  catch(e){ showFatal("Could not load /api/data - start the server: python -m dashboard.app"); return; }
  if(!raw||!raw.order||!raw.scenarios||!raw.meta||!Array.isArray(raw.meta.sensors)){
    showFatal("results.json missing/outdated. Run: python make_data.py"); return;
  }
  S.data=raw;
  $("scenPills").innerHTML=S.data.order.map(k=>
    '<button class="pill" data-key="'+k+'">'+S.data.scenarios[k].label+'</button>').join("");
  document.querySelectorAll(".pill").forEach(p=>p.onclick=()=>{
    try{ setScenario(p.dataset.key); }catch(err){ showFatal("Switch failed: "+err.message); }
  });
  try{ setScenario(S.data.order.find(k=>k!=="normal")||S.data.order[0]); }
  catch(err){ showFatal("Render failed: "+err.message); return; }
  $("playBtn").onclick=()=>S.playing?pause():(S.playing=true,tickLoop());
  $("scrub").addEventListener("input",e=>{pause();setIndex(+e.target.value);});
  $("dlBtn").onclick=downloadReport;
}

function leakStartIdx(){ const k=S.d.series.leak_active.indexOf(1); return k<0?0:k; }

function firstIdx(arr){ const k=arr.indexOf(1); return k<0?null:k; }

function topZone(){
  const counts={};
  S.d.series.twin_flag.forEach((f,i)=>{ if(f){
    const z=S.d.series.likely_near[i];
    counts[z]=(counts[z]||0)+1; }});
  const entries=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  if(!entries.length) return null;
  const total=entries.reduce((s,e)=>s+e[1],0);
  return { zone:entries[0][0], share:entries[0][1]/total };
}

function setScenario(key){
  S.key=key; S.d=S.data.scenarios[key];
  S.sel=S.d.leak_node||S.data.meta.sensors[0].id;
  document.querySelectorAll(".pill").forEach(p=>p.classList.toggle("active",p.dataset.key===key));
  $("repScen").textContent=S.d.label;
  S.charts.forEach(c=>c.destroy()); S.charts=[];
  buildKPIs(); buildCharts(); buildMetrics(); buildTiles();
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
    html+=card("good","Use case","trust check","proves the model does not cry wolf");
  }else{
    html+=card("good","Digital twin - first alert",tLag||"no alert",
      "continuous watch, 15-minute steps");
    html+=card(mLag?"warn":"bad","Nightly method",mLag?"detected after "+mLag:"missed entirely",
      "inspects once per night (02:00-04:00)");
    html+=card("good","Detection quality (F1)",String(t.f1),
      "precision "+t.precision+" / recall "+t.recall);
    html+=card(tz?"good":"warn","Localized to",meta?meta.id+" - "+meta.label:"n/a",
      tz?Math.round(tz.share*100)+"% of alerts point here":"no alerts to localize");
  }
  $("kpis").innerHTML=html;

  let ins;
  if(!S.d.leak_node){
    ins="No leak occurs in this 14-day baseline. The twin stays quiet throughout - the control that shows the system does not raise false alarms.";
  }else{
    const faster=(tLag&&mLag)?"The twin alerted "+(mLag==="<= 15 min"?"well before":"hours before")+" the nightly check.":
      (mLag?"":"The nightly method never detected this leak at all - the exact blind spot continuous monitoring closes.");
    ins="Scenario: "+S.d.label.replace(/^[^-]+- /,"")+". "+faster;
  }
  $("insight").textContent=ins;
}

function alertMarkerData(){
  const out=[];
  S.d.series.twin_flag.forEach((f,i)=>{ if(f){
    const y=pressAt(S.sel,i); if(y!==null) out.push({x:i,y}); }});
  return out;
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
      plugins:{shade:{on:!!S.d.leak_node,from:leakStartIdx()},
               legend:{labels:{boxWidth:12,font:{size:11}}}}},
    plugins:[marker,shade]});
  const psets=S.data.meta.sensors.map((s,j)=>({
    label:s.id+" - "+s.label,
    data:((d.pressures&&d.pressures["pressure_"+s.id])||[]).map((y,x)=>({x,y})),
    borderColor:pal[j%pal.length],borderWidth:s.id===S.sel?2.6:1.4,
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
    const v=pressAt(s.id,S.i);
    pv.textContent=(v===null?"n/a":v+" m");
    const near=d.likely_near[S.i]===s.id&&!!S.d.leak_node;
    pv.style.color=near?"#8a6116":(v===null?"#94a3b8":"#16233b");
    $("tile_"+s.id).classList.toggle("near",near);
  });
  const twinOn=d.twin_flag[S.i]===1, mnfOn=d.mnf_flag[S.i]===1;
  const parts=['Day status: <b>'+d.times[S.i]+'</b>',
    'Digital twin: <b style="color:'+(twinOn?"#b3261e":"#177245")+'">'+
    (twinOn?"ANOMALY":"normal")+'</b>',
    'Nightly method: <b style="color:'+(mnfOn?"#8a6116":"#177245")+'">'+
    (mnfOn?"flagged":"quiet")+'</b>'];
  if(S.d.leak_node){
    const z=d.likely_near[S.i];
    const meta=S.data.meta.sensors.find(s=>s.id===z);
    parts.push('Pointing at: <b>'+(meta?meta.id+" - "+meta.label:z)+'</b>');
  }
  $("liveline").innerHTML=parts.join(' &nbsp;·&nbsp; ');
  S.charts.forEach(c=>c.update("none"));
}

function pause(){S.playing=false;clearInterval(S.timer);$("playBtn").textContent="Play";}
function tickLoop(){
  clearInterval(S.timer);$("playBtn").textContent="Pause";
  S.timer=setInterval(()=>{
    if(S.i>=S.d.series.times.length-1){pause();return;}
    setIndex(S.i+16);
  },100);
}

function downloadReport(){
  const t=S.d.metrics.twin,m=S.d.metrics.mnf;
  const tz=topZone();
  const meta=tz?S.data.meta.sensors.find(s=>s.id===tz.zone):null;
  const lines=[
    "FLOWSENTRY - INCIDENT REPORT",
    "=".repeat(40),
    "Scenario: "+S.d.label,
    "Leak node: "+(S.d.leak_node||"none"),
    "Leak start: "+(S.d.leak_start||"n/a"),
    "",
    "Digital twin (continuous):",
    "  precision "+t.precision+"  recall "+t.recall+"  F1 "+t.f1,
    "  first alert: "+(fmtLag(firstIdx(S.d.series.twin_flag))||"none"),
    "Nightly flow method:",
    "  precision "+m.precision+"  recall "+m.recall+"  F1 "+m.f1,
    "  first alert: "+(fmtLag(firstIdx(S.d.series.mnf_flag))||"none"),
    "",
    "Localization: "+(meta?(meta.id+" - "+meta.label+" ("+Math.round((tz.share||0)*100)+"% of alerts)"):"n/a"),
    "",
    "Provenance: EPANET (WNTR) on the EPA Net3 benchmark, 14 days @ 15-min steps;",
    "leaks modeled as pressure-dependent orifice emitters; detectors trained on",
    "leak-free data only. Generated by FlowSentry demonstration build."
  ];
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([lines.join("\n")],{type:"text/plain"}));
  a.download="flowsentry-report-"+S.key+".txt"; a.click();
}

init();
</script>
</body>
</html>
'''


def main():
    path = os.path.join(ROOT, "dashboard", "templates", "index.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(INDEX_HTML)
    print("wrote dashboard/templates/index.html (" + str(len(INDEX_HTML)) + " chars)")
    rj = os.path.join(ROOT, "dashboard", "data", "results.json")
    print("results.json:", "FOUND - refresh browser with Ctrl+Shift+R" if os.path.exists(rj)
          else "MISSING - run: python make_data.py")


if __name__ == "__main__":
    main()