/* FlowSentry v5 - working tabs, scenario pills, defensive rendering. */
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
    `<button class="pill" data-key="${k}">${S.data.scenarios[k].label}</button>`).join("");
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
  const row=(a,b,c)=>`<tr><td>${a}</td><td>${b}</td><td>${c}</td></tr>`;
  const fmt=v=>(v==null?"no detection":v+" h");
  $("mtable").innerHTML=
    `<tr><th></th><th>Digital twin (continuous)</th><th>Nightly flow method</th></tr>`+
    row("Precision",t.precision,m.precision)+
    row("Recall",t.recall,m.recall)+
    row("F1",t.f1,m.f1)+
    row("Detection lag",fmt(t.detection_lag_hours),fmt(m.detection_lag_hours));
  $("mnote").textContent=S.key==="normal"
    ?"No leak occurs in this scenario - any flag here would be a false alarm."
    :"Detection lag = time from the true leak start to the first alarm. The nightly method inspects flows once per night (02:00-04:00), so its lag is structurally large.";
}

function buildTiles(){
  $("tiles").innerHTML=S.data.meta.sensors.map(s=>`
    <div class="tile" id="tile_${s.id}" onclick="selectSensor('${s.id}')">
      <div class="nm">${s.id} - ${s.label}</div>
      <div class="pv" id="pv_${s.id}">-</div>
    </div>`).join("");
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
