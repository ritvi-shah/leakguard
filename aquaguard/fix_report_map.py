#!/usr/bin/env python3
# fix_report_map.py - richer report, one-line pills/tiles, visible junctions,
# map tooltips, verdict-based highlight, live map counter. Verified write.
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")

src = open(PATH, encoding="utf-8").read()
fails = []


def rep(a, b, label, optional=False):
    global src
    n = src.count(a)
    if n == 1:
        src = src.replace(a, b)
        print("OK   " + label)
    elif optional and n == 0:
        print("SKIP " + label + " (already applied)")
    else:
        print("FAIL " + label + " (found " + str(n) + ")")
        fails.append(label)


# ---------- layout: pills on one full-width line ----------
rep(".pills{display:flex;gap:8px;flex-wrap:wrap;max-width:620px}",
    ".pills{display:flex;gap:8px;flex:1 1 100%;overflow-x:auto;"
    "padding-bottom:2px}",
    "pills full-width row")
rep(".pill{border:1.5px solid var(--line);background:var(--card);\n"
    "color:var(--ink2);border-radius:999px;padding:9px 16px;\n"
    "font-size:.9rem;font-weight:600;cursor:pointer}",
    ".pill{border:1.5px solid var(--line);background:var(--card);\n"
    "color:var(--ink2);border-radius:999px;padding:9px 16px;\n"
    "font-size:.9rem;font-weight:600;cursor:pointer;\n"
    "white-space:nowrap;flex:1 1 0;text-align:center}",
    "pills one line, equal width")

# ---------- tiles: district name on one line ----------
rep(".tile .nm{font-size:.8rem;color:var(--ink2);font-weight:600;\n"
    "overflow-wrap:anywhere}",
    ".tile .nm{font-size:.8rem;color:var(--ink2);font-weight:600;\n"
    "white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "tile name single line")
rep('    c.appendChild(el("div", "nm",\n'
    '      zoneName(s.id) + " (node " + s.id + ")"));',
    '    c.appendChild(el("div", "nm", zoneName(s.id)));\n'
    '    c.title = "Node " + s.id;',
    "tile label text")

# ---------- map: visible junctions + live counter ----------
rep(".mdot.junction{fill:#bcc9d6}",
    ".mdot.junction{fill:#a9b9c9}",
    "junction dots darker")
rep('(n.type === "reservoir" ? 8 : 2.6);',
    '(n.type === "reservoir" ? 8 : 3);',
    "junction dots bigger")
rep("92 junctions, dual reservoirs, tanks and pumps,",
    "92 junctions + 2 reservoirs + 3 tanks (all drawn on the map),",
    "provenance text matches map")
rep('.mleak{fill:none;stroke:#b3261e;stroke-width:2.4;'
    'stroke-dasharray:6 4}',
    '.mleak{fill:none;stroke:#b3261e;stroke-width:2.4;'
    'stroke-dasharray:6 4}\n'
    '.mtip{fill:#fff;font-size:13px;font-weight:700}\n'
    '.mtip2{fill:#cbd5e1;font-size:11.5px}\n'
    '.mapcount{font-size:.78rem;color:#5b6b82;margin-top:6px}',
    "tooltip + counter css")

# ---------- map interactivity: tooltip on click ----------
rep('        selectSensor(n.id); });',
    '        selectSensor(n.id); showMapTip(n.id); });',
    "map click opens tooltip")
rep('  var lk = el("circle", { r:13, "class":"mleak" });\n'
    '  lk.style.display = "none";\n'
    '  svg.appendChild(lk);\n'
    '  MAP.leak = lk;\n'
    '}',
    '  var lk = el("circle", { r:13, "class":"mleak" });\n'
    '  lk.style.display = "none";\n'
    '  svg.appendChild(lk);\n'
    '  MAP.leak = lk;\n'
    '  var tipG = el("g", {});\n'
    '  tipG.style.display = "none";\n'
    '  tipG.appendChild(el("rect", { x:0, y:0, rx:5, ry:5,\n'
    '    width:200, height:46, fill:"#16233b", opacity:.93 }));\n'
    '  var t1 = el("text", { x:10, y:18, "class":"mtip" });\n'
    '  var t2 = el("text", { x:10, y:36, "class":"mtip2" });\n'
    '  tipG.appendChild(t1); tipG.appendChild(t2);\n'
    '  svg.appendChild(tipG);\n'
    '  MAP.tip = tipG; MAP.tip1 = t1; MAP.tip2 = t2;\n'
    '  MAP.tipId = null;\n'
    '}\n'
    'function showMapTip(id){\n'
    '  if(!MAP || !MAP.byId[id]) return;\n'
    '  if(MAP.tipId === id && MAP.tip.style.display !== "none"){\n'
    '    MAP.tip.style.display = "none";\n'
    '    MAP.tipId = null; return;\n'
    '  }\n'
    '  MAP.tipId = id;\n'
    '  var n = MAP.byId[id];\n'
    '  var x = MAP.ox + (n.x - MAP.minX)*MAP.sc;\n'
    '  var y = MAP.oy + (MAP.maxY - n.y)*MAP.sc;\n'
    '  var p = pressAt(id, S.i);\n'
    '  var dev = devAt(id, S.i);\n'
    '  MAP.tip1.textContent = "Watched: " + zoneName(id);\n'
    '  var dTxt = "";\n'
    '  if(dev !== null){\n'
    '    dTxt = " (" + (dev < 0 ? "" : "+") +\n'
    '      dev.toFixed(1) + " m vs normal)";\n'
    '  }\n'
    '  MAP.tip2.textContent =\n'
    '    (p === null ? "no data" : p + " m") + dTxt;\n'
    '  MAP.tip.setAttribute("transform",\n'
    '    "translate(" + (x + 14) + "," + (y - 52) + ")");\n'
    '  MAP.tip.style.display = "";\n'
    '}\n'
    'function hideMapTip(){\n'
    '  if(MAP && MAP.tip){\n'
    '    MAP.tip.style.display = "none";\n'
    '    MAP.tipId = null;\n'
    '  }\n'
    '}',
    "tooltip functions")
rep('  $("scrub").value = S.i;\n'
    '  $("tlabel").textContent = d.times[S.i];\n',
    '  $("scrub").value = S.i;\n'
    '  $("tlabel").textContent = d.times[S.i];\n'
    '  hideMapTip();\n',
    "tooltip hides on scrub")
rep('  updateLeakMarker();\n  var li = leakStartIdx();',
    '  updateLeakMarker(); hideMapTip();\n  var li = leakStartIdx();',
    "tooltip hides on scenario switch")

# ---------- stable amber highlight (verdict-based) ----------
rep('    var near = d.likely_near[S.i] === s.id && !!S.d.leak_node;',
    '    var vd = currentVerdict();\n'
    '    var near = !!(vd && vd.zone === s.id);',
    "verdict-based tile highlight")
rep('  var v = currentVerdict();\n'
    '  if(v){\n'
    '    var d = MAP.dots[v.zone];',
    '  var v = currentVerdict();\n'
    '  if(v){\n'
    '    var d = MAP.dots[v.zone];',
    "suspect uses verdict (verify)", optional=True)

# ---------- richer report ----------
REPORT = [
'function downloadReport(){',
'  var t = S.d.metrics.twin, m = S.d.metrics.mnf;',
'  var loss = S.d.est_loss_Lpm || 0;',
'  var now = new Date();',
'  var L = [];',
'  L.push("LEAKGUARD - LEAK ASSESSMENT REPORT");',
'  L.push("Generated: " + now.toLocaleString());',
'  L.push("==========================================");',
'  L.push("");',
'  L.push("1. SITUATION");',
'  L.push("Scenario: " + S.d.label);',
'  if(S.d.leak_node){',
'    L.push("Leak location (ground truth): node " +',
'      S.d.leak_node + " - " + zoneName(S.d.leak_node));',
'    L.push("Leak active: " + (S.d.leak_start || "n/a"));',
'    L.push("Estimated water loss: ~" + loss + " L/min" +',
'      " (~" + (loss * 60).toFixed(0) + " L/hour)");',
'  } else {',
'    L.push("No leak in this scenario (control run).");',
'  }',
'  L.push("");',
'  L.push("2. VERDICT AND LOCALIZATION");',
'  var tz = topZone();',
'  var vd = currentVerdict();',
'  if(vd){',
'    L.push("LeakGuard suspects: " + zoneName(vd.zone) +',
'      " (" + Math.round(vd.conf * 100) + "% of recent checks)");',
'  } else if(tz){',
'    L.push("LeakGuard alerts point to: " + zoneName(tz.zone) +',
'      " (" + Math.round(tz.share * 100) + "% of alerts)");',
'  } else {',
'    L.push("No suspicion recorded.");',
'  }',
'  if(S.d.leak_node && tz){',
'    var hit = (tz.zone === S.d.leak_node);',
'    L.push("Ground-truth check: " +',
'      (hit ? "top zone MATCHES the true leak district." :',
'            "top zone differs from the true district."));',
'  }',
'  L.push("");',
'  L.push("3. EVIDENCE - DISTRICT PRESSURE DEVIATION");',
'  L.push("Average deviation from normal while leak is active:");',
'  var sensors = S.data.meta.sensors;',
'  var rows = [];',
'  sensors.forEach(function(s){',
'    var sum = 0, n = 0;',
'    S.d.series.leak_active.forEach(function(a, i){',
'      if(a === 1){',
'        var dv = devAt(s.id, i);',
'        if(dv !== null){ sum += dv; n += 1; }',
'      } });',
'    rows.push([s.id, n ? sum / n : 0]);',
'  });',
'  rows.sort(function(a, b){ return a[1] - b[1]; });',
'  rows.forEach(function(r, idx){',
'    L.push("  " + (idx + 1) + ". " + zoneName(r[0]) +',
'      " (node " + r[0] + "): " + r[1].toFixed(2) + " m");',
'  });',
'  L.push("(most negative = strongest sign of a leak nearby)");',
'  L.push("");',
'  L.push("4. PIPES TO ISOLATE AT THE LEAK NODE");',
'  if(S.d.leak_node && S.data.network){',
'    var pipes = [];',
'    S.data.network.links.forEach(function(lk){',
'      if(lk.frm === S.d.leak_node || lk.to === S.d.leak_node){',
'        pipes.push(lk.frm + " - " + lk.to); } });',
'    if(pipes.length){',
'      L.push("Isolation candidates: " + pipes.join("; "));',
'    } else {',
'      L.push("None found in network data.");',
'    }',
'  } else {',
'    L.push("n/a (no leak in scenario)");',
'  }',
'  L.push("");',
'  L.push("5. DETECTOR PERFORMANCE (this scenario)");',
'  L.push("                      LeakGuard    Nightly check");',
'  L.push("  precision           " + t.precision +',
'      "            " + m.precision);',
'  L.push("  recall              " + t.recall +',
'      "            " + m.recall);',
'  L.push("  F1                  " + t.f1 +',
'      "            " + m.f1);',
'  L.push("  first alert         " +',
'      (fmtLag(firstIdx(S.d.series.twin_flag)) || "never") +',
'      "        " +',
'      (fmtLag(firstIdx(S.d.series.mnf_flag)) || "never"));',
'  L.push("");',
'  L.push("6. METHOD AND DATA SOURCE");',
'  L.push("Hydraulics: EPANET engine (WNTR) on the EPA Net3");',
'  L.push("benchmark network, 14 days at 15-minute steps.");',
'  L.push("Leak model: pressure-dependent orifice emitter.");',
'  L.push("Training: leak-free data only. All scores measured");',
'  L.push("against known ground truth.");',
'  L.push("");',
'  L.push("LeakGuard demonstration build.");',
'  var blob = new Blob([L.join("\\n")], { type:"text/plain" });',
'  var a = document.createElement("a");',
'  a.href = URL.createObjectURL(blob);',
'  a.download = "leakguard-report-" + S.key + ".txt";',
'  a.click();',
'}',
'init();',
]

start = src.find("function downloadReport(){")
end = src.rfind("init();")
if start == -1 or end == -1 or end < start:
    fails.append("report block anchors")
else:
    js = src[start:end] + "init();"
    pc = js.count("(") - js.count(")")
    bc = js.count("{") - js.count("}")
    print("     old report block paren diff:", pc, "brace diff:", bc)
    src = src[:start] + "\n".join(REPORT)
    print("OK   report block replaced")

# ---------- verify everything before writing ----------
js_all = src[src.find("<script>\n") + 9: src.rfind("</script>")]
checks = [
    ("js braces balanced", js_all.count("{") == js_all.count("}")),
    ("js parens balanced", js_all.count("(") == js_all.count(")")),
    ("js double quotes even", js_all.count('"') % 2 == 0),
    ("no apostrophes in js", "'" not in js_all),
]
for name, ok in checks:
    print(("  OK  " if ok else "  FAIL") + " " + name)

if fails or not all(ok for _, ok in checks):
    print("FAILED ITEMS:", fails)
    print("NOTHING WRITTEN - report to chat.")
else:
    with open(PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print("saved (" + str(len(src)) + " chars)")
    print("INTEGRITY: OK - browser -> Ctrl+Shift+R")


if __name__ == "__main__":
    main()