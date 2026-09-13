#!/usr/bin/env python3
# repair_page.py - rebuilds the final page from final_build.py, replacing the
# downloadReport block with a verified-balanced version. Writes index.html
# only if ALL integrity checks pass.
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import final_build as fb

REPLACEMENT = [
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
    start = None
    for i, ln in enumerate(js_list):
        if ln.startswith("function downloadReport"):
            start = i
            break
    if start is None:
        print("Could not find downloadReport in final_build.py - tell the chat.")
        return
    end = None
    for i in range(len(js_list) - 1, -1, -1):
        if js_list[i].strip() == "init();":
            end = i
            break
    if end is None:
        print("Could not find init(); marker - tell the chat.")
        return

    new_list = js_list[:start] + REPLACEMENT
    js = "\n".join(new_list)

    checks = [
        ("js braces balanced", js.count("{") == js.count("}")),
        ("js parens balanced", js.count("(") == js.count(")")),
        ("js double quotes even", js.count('"') % 2 == 0),
        ("no apostrophes in js", not any("'" in ln for ln in new_list)),
    ]
    for name, ok in checks:
        print(("  OK  " if ok else "  FAIL") + " " + name)

    if not all(ok for _, ok in checks):
        print("STILL UNBALANCED - report to chat; nothing written.")
        return

    html = (fb.HEAD + fb.HTML + fb.MID + js + fb.TAIL)
    path = os.path.join(ROOT, "dashboard", "templates", "index.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote index.html (" + str(len(html)) + " chars)")
    print("INTEGRITY: OK")
    print("NOW: refresh browser at localhost:9000 with Ctrl+Shift+R")


if __name__ == "__main__":
    main()