#!/usr/bin/env python3
# repair2.py - fixes the Chart-creation paren bug AND the report block,
# then writes index.html only if ALL checks pass.
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import final_build as fb

CHART_OLD_START = '    S.why = new Chart($("whyChart"), { type:"bar",'
CHART_NEW = [
'    S.why = new Chart($("whyChart"), { type:"bar",',
'      data:{ labels:sensors.map(function(s){',
'          return zoneName(s.id); }),',
'        datasets:[{ data:devs, borderWidth:1,',
'          borderRadius:5, barPercentage:.7 } ] },',
'      options:{ indexAxis:"y", animation:false,',
'        maintainAspectRatio:false,',
'        scales:{ x:{ title:{ display:true,',
'          text:"meters below / above normal" },',
'          suggestedMin:-3, suggestedMax:1 },',
'          y:{ ticks:{ font:{ size:12 } } } },',
'        plugins:{ legend:{ display:false } } } });',
]

REPORT = [
'function downloadReport(){',
'  var t = S.d.metrics.twin, m = S.d.metrics.mnf;',
'  var tz = topZone();',
'  var loss = S.d.est_loss_Lpm || 0;',
'  var L = [];',
'  L.push("LEAKGUARD - INCIDENT REPORT");',
'  L.push("========================================");',
'  L.push("Scenario: " + S.d.label);',
'  L.push("Leak node: " + (S.d.leak_node || "none"));',
'  L.push("Leak start: " + (S.d.leak_start || "n/a"));',
'  L.push("Estimated loss: " +',
'    (loss > 0 ? loss + " L/min" : "0"));',
'  L.push("");',
'  L.push("LeakGuard (continuous):");',
'  L.push("  precision " + t.precision +',
'    "  recall " + t.recall + "  F1 " + t.f1);',
'  L.push("  first alert: " +',
'    (fmtLag(firstIdx(S.d.series.twin_flag)) || "never"));',
'  L.push("Nightly check:");',
'  L.push("  precision " + m.precision +',
'    "  recall " + m.recall + "  F1 " + m.f1);',
'  L.push("  first alert: " +',
'    (fmtLag(firstIdx(S.d.series.mnf_flag)) || "never"));',
'  L.push("");',
'  if(tz){',
'    L.push("Localization: " + zoneName(tz.zone) +',
'      " (" + Math.round(tz.share * 100) + "% of alerts)");',
'  } else {',
'    L.push("Localization: n/a");',
'  }',
'  L.push("");',
'  L.push("Source: EPANET engine, EPA Net3 network,");',
'  L.push("14 days at 15-minute steps, orifice leaks,");',
'  L.push("trained on leak-free data only.");',
'  L.push("LeakGuard demonstration build.");',
'  var blob = new Blob([L.join("\\n")],',
'    { type: "text/plain" });',
'  var a = document.createElement("a");',
'  a.href = URL.createObjectURL(blob);',
'  a.download = "leakguard-report-" + S.key + ".txt";',
'  a.click();',
'}',
'init();',
]


def main():
    js_list = list(fb.JS)

    # --- fix 1: the Chart creation block in renderWhy ---
    ci = None
    for i, ln in enumerate(js_list):
        if ln == CHART_OLD_START:
            ci = i
            break
    if ci is None:
        print("Chart block not found - tell the chat.")
        return
    ce = None
    for i in range(ci, len(js_list)):
        if "plugins:{ legend:{ display:false } } }) });" in js_list[i]:
            ce = i
            break
    if ce is None:
        print("Chart block end not found - tell the chat.")
        return
    js_list = js_list[:ci] + CHART_NEW + js_list[ce + 1:]
    print("OK  chart block replaced")

    # --- fix 2: the downloadReport block ---
    ri = None
    for i, ln in enumerate(js_list):
        if ln.startswith("function downloadReport"):
            ri = i
            break
    if ri is None:
        print("downloadReport not found - tell the chat.")
        return
    re_ = None
    for i in range(len(js_list) - 1, -1, -1):
        if js_list[i].strip() == "init();":
            re_ = i
            break
    if re_ is None:
        print("init(); marker not found - tell the chat.")
        return
    js_list = js_list[:ri] + REPORT
    print("OK  report block replaced")

    js = "\n".join(js_list)
    checks = [
        ("js braces balanced", js.count("{") == js.count("}")),
        ("js parens balanced", js.count("(") == js.count(")")),
        ("js double quotes even", js.count('"') % 2 == 0),
        ("no apostrophes in js", not any("'" in ln for ln in js_list)),
    ]
    for name, ok in checks:
        print(("  OK  " if ok else "  FAIL") + " " + name)

    if not all(ok for _, ok in checks):
        print("STILL UNBALANCED - nothing written; report to chat.")
        return

    html = fb.HEAD + fb.HTML + fb.MID + js + fb.TAIL
    path = os.path.join(ROOT, "dashboard", "templates", "index.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote index.html (" + str(len(html)) + " chars)")
    print("INTEGRITY: OK")
    print("NOW: browser localhost:9000 -> Ctrl+Shift+R")


if __name__ == "__main__":
    main()