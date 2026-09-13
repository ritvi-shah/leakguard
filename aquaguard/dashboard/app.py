"""FlowSentry backend. Run: python -m dashboard.app -> http://localhost:9000"""
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


@app.route("/api/report/<key>")
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


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 9000)), debug=True)
