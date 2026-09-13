#!/usr/bin/env python3
# fix_v2.py - calibrated leaks, persistent-sigma detector, docx report,
# tile-click opens chart, trimmed text. Verifies before writing.
import glob
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

DETECTORS = r'''"""Leak detectors.

1. MinimumNightFlowDetector - standard utility method: nightly 02:00-04:00
   flow vs fitted baseline. Inspects once per night.
2. ResidualTwinDetector - learns normal pressure per district per time slot
   from leak-free data; flags when any district runs >2.5 sigma below normal
   for two consecutive readings (30 minutes), and names the district with
   the largest normalized drop.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

STEPS_PER_DAY = 96
SIGMA = 2.5
PERSIST = 2


class MinimumNightFlowDetector:
    def __init__(self, threshold_pct: float = 0.20, baseline_days: int = 5):
        self.threshold_pct = threshold_pct
        self.baseline_days = baseline_days

    def fit(self, df_normal: pd.DataFrame):
        night = df_normal[(df_normal.hour_of_day >= 2) & (df_normal.hour_of_day < 4)]
        self.baseline_mnf_ = night["source_flow_Ls"].mean()
        self.baseline_std_ = night["source_flow_Ls"].std()
        return self

    def predict(self, df: pd.DataFrame):
        df = df.copy()
        night = df[(df.hour_of_day >= 2) & (df.hour_of_day < 4)].copy()
        night["day"] = night.step // STEPS_PER_DAY
        daily_mnf = night.groupby("day")["source_flow_Ls"].mean()
        threshold = self.baseline_mnf_ * (1 + self.threshold_pct)
        flagged_days = daily_mnf[daily_mnf > threshold].index.tolist()
        df["day"] = df.step // STEPS_PER_DAY
        df["mnf_flag"] = df["day"].isin(flagged_days).astype(int)
        return df, daily_mnf, threshold


class ResidualTwinDetector:
    def __init__(self, sensor_cols: list[str], contamination: float = 0.05):
        self.sensor_cols = sensor_cols
        self.contamination = contamination

    def _expected_pressure(self, df: pd.DataFrame) -> pd.DataFrame:
        expected = pd.DataFrame(index=df.index)
        for col in self.sensor_cols:
            hour_bin = (df["hour_of_day"] * 4).round().astype(int) % (24 * 4)
            expected[col] = hour_bin.map(self._twin_tables[col])
        return expected

    def fit(self, df_normal: pd.DataFrame):
        self._twin_tables = {}
        hour_bin = (df_normal["hour_of_day"] * 4).round().astype(int) % (24 * 4)
        for col in self.sensor_cols:
            self._twin_tables[col] = df_normal.groupby(hour_bin)[col].mean()
        expected = self._expected_pressure(df_normal)
        residuals = df_normal[self.sensor_cols].values - expected[self.sensor_cols].values
        self.resid_mean_ = residuals.mean(axis=0)
        self.resid_std_ = residuals.std(axis=0) + 1e-9
        norm = (residuals - self.resid_mean_) / self.resid_std_
        self.model_ = IsolationForest(
            n_estimators=200, contamination=self.contamination,
            random_state=42).fit(norm)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        expected = self._expected_pressure(df)
        residuals = df[self.sensor_cols].values - expected[self.sensor_cols].values
        norm = (residuals - self.resid_mean_) / self.resid_std_

        zmin = norm.min(axis=1)
        persist = np.zeros(len(df), dtype=int)
        persist[PERSIST:] = (
            (zmin[PERSIST:] < -SIGMA) & (zmin[:-PERSIST] < -SIGMA)
        ).astype(int)

        raw = self.model_.predict(norm)
        df["twin_flag"] = ((persist == 1) | (raw == -1)).astype(int)
        df["anomaly_score"] = -self.model_.score_samples(norm)

        zdf = pd.DataFrame(norm, columns=self.sensor_cols, index=df.index)
        df["likely_leak_near"] = zdf.idxmin(axis=1)
        return df


def score_detection(df: pd.DataFrame, flag_col: str) -> dict:
    y_true = df["leak_active"].values
    y_pred = df[flag_col].values
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    leak_steps = df.index[df["leak_active"] == 1]
    lag_hours = None
    if len(leak_steps) > 0:
        onset = leak_steps[0]
        flagged_after = df.index[(df.index >= onset) & (df[flag_col] == 1)]
        if len(flagged_after) > 0:
            lag_hours = (flagged_after[0] - onset) * 15 / 60
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "detection_lag_hours": round(lag_hours, 2) if lag_hours is not None else None,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }
'''

MAKE_DATA = r'''"""Runs the WNTR/EPANET pipeline; auto-calibrates leak sizes so they are
hydraulically visible; writes dashboard/data/results.json (+ evidence, pipes)."""
import glob
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
         csv="data/scenario_normal.csv", gen=dict(n_days=14),
         target_lps=None),
    dict(key="leak_a", label="Hidden leak - Central Park",
         csv="data/scenario_leak_a.csv",
         gen=dict(n_days=14, leak_node="105", leak_coeff=0.003),
         target_lps=15),
    dict(key="leak_b", label="Burst - South Harbor",
         csv="data/scenario_leak_b.csv",
         gen=dict(n_days=14, leak_node="201", leak_coeff=0.010),
         target_lps=120),
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


def fmt_time(step):
    step = int(step)
    day = step // STEPS_PER_DAY + 1
    mins = (step % STEPS_PER_DAY) * DT_MIN
    return "Day " + str(day) + " " + str(mins // 60).zfill(2) + ":" \
        + str(mins % 60).zfill(2)


def expected_tables(df_normal):
    bins = (df_normal["hour_of_day"] * 4).round().astype(int) % 96
    tables = {}
    for col in SENSOR_COLS:
        tables[col] = df_normal.groupby(bins)[col].mean()
    return tables


def mean_deviation(df, tables, mask):
    bins = (df["hour_of_day"] * 4).round().astype(int) % 96
    out = {}
    for col in SENSOR_COLS:
        exp = bins.map(tables[col])
        dev = (df[col] - exp)[mask]
        out[col] = float(dev.mean()) if len(dev) else 0.0
    return out


def main():
    dfs = {}
    print("[1/4] baseline scenario ...", flush=True)
    nsc = SCENARIOS[0]
    if os.path.exists(nsc["csv"]):
        dfs["normal"] = pd.read_csv(nsc["csv"])
        print("  normal: cached")
    else:
        dfs["normal"] = generate_scenario(**nsc["gen"])
        os.makedirs("data", exist_ok=True)
        dfs["normal"].to_csv(nsc["csv"], index=False)
    df_normal = dfs["normal"]
    base_mean = df_normal["source_flow_Ls"].mean()
    tables = expected_tables(df_normal)

    print("[2/4] leak scenarios (auto-calibrated to visible size) ...",
          flush=True)
    for sc in SCENARIOS[1:]:
        if os.path.exists(sc["csv"]):
            os.remove(sc["csv"])
        target = sc["target_lps"]
        c = sc["gen"]["leak_coeff"]
        df = None
        added = 0.0
        for attempt in range(4):
            df = generate_scenario(**{**sc["gen"], "leak_coeff": c})
            added = df["source_flow_Ls"].mean() - base_mean
            print("  " + sc["key"] + " coeff=" + str(round(c, 6)) +
                  " -> +" + str(round(added, 1)) + " L/s", flush=True)
            if added <= 0.5:
                c *= 10
                continue
            if added >= target * 0.55 and added <= target * 1.9:
                break
            c = c * (target / added)
        sc["gen"]["leak_coeff"] = c
        df.to_csv(sc["csv"], index=False)
        dfs[sc["key"]] = df

    print("[3/4] network map + training ...", flush=True)
    network = extract_network()
    mnf = MinimumNightFlowDetector(threshold_pct=0.20).fit(df_normal)
    twin = ResidualTwinDetector(sensor_cols=SENSOR_COLS).fit(df_normal)

    print("[4/4] scoring ...", flush=True)
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
            added = df["source_flow_Ls"].mean() - base_mean
            est_lpm = round(max(0.0, added) * 60, 1)
            note = " | leak adds ~" + str(round(added, 1)) + " L/s"

        evidence = []
        pipes = []
        if has_leak:
            devs = mean_deviation(df, tables, df["leak_active"] == 1)
            for col, dv in sorted(devs.items(), key=lambda kv: kv[1]):
                nid = col.replace("pressure_", "")
                evidence.append(dict(id=nid,
                                     label=NODE_LABELS.get(nid, nid),
                                     dev=round(dv, 2)))
            node = sc["gen"]["leak_node"]
            for lk in network["links"]:
                if node in (lk["frm"], lk["to"]):
                    pipes.append(lk["frm"] + " - " + lk["to"])

        out[sc["key"]] = dict(
            label=sc["label"],
            leak_node=sc["gen"].get("leak_node"),
            leak_start=("from Day 1 (demo)" if has_leak else None),
            est_loss_Lpm=est_lpm,
            metrics=dict(mnf=score_detection(df_mnf, "mnf_flag"),
                         twin=score_detection(df_tw, "twin_flag")),
            evidence=evidence,
            pipes=pipes,
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
        print("  " + sc["key"] + ": twin P=" + str(mt["precision"]) +
              " R=" + str(mt["recall"]) + " F1=" + str(mt["f1"]) +
              " lag=" + str(mt["detection_lag_hours"]) + "h | nightly F1=" +
              str(mm["f1"]) + note, flush=True)

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
    print("\nWROTE dashboard/data/results.json - restart server, then Ctrl+Shift+R")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nPIPELINE ERROR - paste this traceback into the chat:")
        traceback.print_exc()
'''

ROUTE = '''@app.route("/api/report/<key>")
def api_report(key):
    import io
    from datetime import datetime
    from flask import send_file

    data = load_results()
    sc = data.get("scenarios", {}).get(key)
    if not sc:
        return jsonify(error="unknown scenario"), 404
    try:
        from docx import Document
    except ImportError:
        return jsonify(error="python-docx missing. Run: pip install python-docx"), 500

    labels = {s["id"]: s["label"] for s in data["meta"]["sensors"]}
    ZONE = {"15": "Northside", "35": "Downtown", "101": "Eastside",
            "105": "Central Park", "113": "Westside", "201": "South Harbor"}

    def zn(nid):
        return ZONE.get(nid, labels.get(nid, nid))

    t = sc["metrics"]["twin"]
    m = sc["metrics"]["mnf"]
    s = sc["series"]
    counts = {}
    for i, f in enumerate(s["twin_flag"]):
        if f:
            z = s["likely_near"][i]
            counts[z] = counts.get(z, 0) + 1
    tz = max(counts, key=counts.get) if counts else None
    share = round(counts[tz] / sum(counts.values()) * 100) if counts else 0

    doc = Document()
    doc.add_heading("LeakGuard - Leak Assessment Report", 0)
    doc.add_paragraph("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    doc.add_heading("1. Situation", level=1)
    doc.add_paragraph("Scenario: " + sc["label"])
    if sc["leak_node"]:
        doc.add_paragraph("Leak location (ground truth): node "
                          + sc["leak_node"] + " - " + zn(sc["leak_node"]))
        doc.add_paragraph("Leak active: " + str(sc.get("leak_start") or "n/a"))
        doc.add_paragraph("Estimated water loss: ~"
                          + str(sc.get("est_loss_Lpm", 0)) + " L/min ("
                          + str(round(sc.get("est_loss_Lpm", 0) * 60))
                          + " L/hour)")
    else:
        doc.add_paragraph("No leak in this scenario (control run).")
    doc.add_heading("2. Verdict and localization", level=1)
    if tz:
        doc.add_paragraph("LeakGuard points to: " + zn(tz)
                          + " (" + str(share) + "% of alerts)")
        if sc["leak_node"]:
            doc.add_paragraph("Ground-truth check: "
                              + ("MATCH - top zone is the true leak district."
                                 if tz == sc["leak_node"] else
                                 "top zone differs from the true district."))
    else:
        doc.add_paragraph("No suspicion recorded.")
    doc.add_heading("3. Evidence - district pressure deviation", level=1)
    doc.add_paragraph("Average deviation from normal while the leak is active "
                      "(most negative = strongest leak sign):")
    ev = sc.get("evidence") or []
    if ev:
        tb = doc.add_table(rows=1, cols=3)
        tb.style = "Light Grid Accent 1"
        for j, h in enumerate(("Rank", "District (node)", "Deviation (m)")):
            tb.rows[0].cells[j].text = h
        for idx, r in enumerate(ev):
            row = tb.add_row().cells
            row[0].text = str(idx + 1)
            row[1].text = r["label"] + " (node " + r["id"] + ")"
            row[2].text = str(r["dev"])
    doc.add_heading("4. Pipes to isolate at the leak node", level=1)
    p = sc.get("pipes") or []
    doc.add_paragraph("; ".join(p) if p else "n/a")
    doc.add_heading("5. Detector performance (this scenario)", level=1)
    tb = doc.add_table(rows=5, cols=3)
    tb.style = "Light Grid Accent 1"
    hdr = ("", "LeakGuard (continuous)", "Nightly check")
    for j, h in enumerate(hdr):
        tb.rows[0].cells[j].text = h
    rows = [
        ("Precision", t["precision"], m["precision"]),
        ("Recall", t["recall"], m["recall"]),
        ("F1", t["f1"], m["f1"]),
        ("First alert", (str(t["detection_lag_hours"]) + " h")
         if t["detection_lag_hours"] is not None else "never",
         (str(m["detection_lag_hours"]) + " h")
         if m["detection_lag_hours"] is not None else "never"),
    ]
    for i, r in enumerate(rows):
        tb.rows[i + 1].cells[0].text = r[0]
        tb.rows[i + 1].cells[1].text = str(r[1])
        tb.rows[i + 1].cells[2].text = str(r[2])
    doc.add_heading("6. Method and data source", level=1)
    doc.add_paragraph("Hydraulics: EPANET engine (WNTR) on the EPA Net3 "
                      "benchmark network, 14 days at 15-minute steps. "
                      "Leak model: pressure-dependent orifice emitter. "
                      "Training: leak-free data only. All scores measured "
                      "against known ground truth.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    fname = "leakguard-report-" + key + ".docx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument."
                              "wordprocessingml.document")


'''

HTML_PATH = os.path.join(ROOT, "dashboard", "templates", "index.html")
APP_PATH = os.path.join(ROOT, "dashboard", "app.py")
REQ_PATH = os.path.join(ROOT, "requirements.txt")


def main():
    # 1) core + pipeline
    with open(os.path.join(ROOT, "core", "detectors.py"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(DETECTORS)
    print("wrote core/detectors.py (persistent-sigma rule)")
    with open(os.path.join(ROOT, "make_data.py"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(MAKE_DATA)
    print("wrote make_data.py (auto-calibrated leaks + evidence + pipes)")

    # 2) stale leak data out (re-simulated at calibrated sizes)
    for p in glob.glob(os.path.join(ROOT, "data", "scenario_leak_*.csv")):
        os.remove(p)
        print("removed", os.path.basename(p))

    # 3) report route into app.py
    app_src = open(APP_PATH, encoding="utf-8").read()
    if "/api/report/" not in app_src:
        anchor = '@app.route("/healthz")'
        if anchor not in app_src:
            print("FAIL app.py anchor missing - tell the chat")
            return
        app_src = app_src.replace(anchor, ROUTE + anchor, 1)
        with open(APP_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(app_src)
        print("OK   report route added to dashboard/app.py")
    else:
        print("SKIP report route (already present)")

    # 4) requirements
    req = open(REQ_PATH, encoding="utf-8").read() if os.path.exists(REQ_PATH) else ""
    if "python-docx" not in req:
        with open(REQ_PATH, "a", encoding="utf-8", newline="\n") as f:
            f.write("" if req.endswith("\n") or not req else "\n")
            f.write("python-docx\n")
        print("OK   python-docx added to requirements.txt")

    # 5) page: trimmed text, tile click opens chart, Word report button
    src = open(HTML_PATH, encoding="utf-8").read()
    fails = []

    def rep(a, b, label):
        nonlocal src
        n = src.count(a)
        if n == 1:
            src = src.replace(a, b)
            print("OK   " + label)
        elif n == 0 and b in src:
            print("SKIP " + label + " (already applied)")
        else:
            print("FAIL " + label + " (found " + str(n) + ")")
            fails.append(label)

    rep(".errbox{",
        ".insight,.whycap{display:none!important}\n.errbox{",
        "hide insight line + caption")
    rep("Click one to highlight it in Charts.",
        "Click a district to open its chart.",
        "tile hint text")
    rep('function selectSensor(id){\n  S.sel = id;',
        'function selectSensor(id){\n  S.sel = id;\n'
        '  var tb = document.querySelector("[data-tab=\\"analysis\\"]");\n'
        '  if(tb && !$("panel-analysis").classList.contains("active"))'
        ' tb.click();',
        "tile click opens chart")
    rep('<button id="dlBtn" class="dlbtn">Download report (.txt)</button>',
        '<button id="dlBtn" class="dlbtn">Download report (Word)</button>',
        "report button label")
    rep('  $("dlBtn").onclick = downloadReport;',
        '  $("dlBtn").onclick = function(){\n'
        '    window.open("/api/report/" + S.key, "_blank");\n'
        '  };',
        "report button wired to docx")

    js_all = src[src.find("<script>\n") + 9: src.rfind("</script>")]
    checks = [
        ("js braces balanced", js_all.count("{") == js_all.count("}")),
        ("js parens balanced", js_all.count("(") == js_all.count(")")),
        ("js double quotes even", js_all.count('"') % 2 == 0),
        ("ends with </html>", src.rstrip().endswith("</html>")),
    ]
    for name, ok in checks:
        print(("  OK  " if ok else "  FAIL") + " " + name)
    if fails or not all(ok for _, ok in checks):
        print("FAILED:", fails, "- page NOT written; core/pipeline WERE written.")
        return
    with open(HTML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
    print("wrote index.html (" + str(len(src)) + " chars)")
    print("PAGE INTEGRITY: OK")

    # 6) regenerate data with calibrated leaks
    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    try:
        import make_data
        make_data.main()
    except Exception:
        print("\nERROR - paste this traceback into the chat:")
        traceback.print_exc()
        return

    print("\nFINISHED. Now restart the server (the new report route needs it):")
    print("  taskkill /F /IM python.exe")
    print("  python -m dashboard.app")
    print("Then browser -> localhost:9000 -> Ctrl+Shift+R")


if __name__ == "__main__":
    main()