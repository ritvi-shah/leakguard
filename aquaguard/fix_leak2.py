#!/usr/bin/env python3
# fix_leak2.py - SIMPLE leak modeling: emitter always on, one sim per scenario.
# No splicing. Purges stale data, regenerates, verifies.
import glob
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))

SIMULATE_PY = r'''"""
Time-series scenario generator using WNTR/EPANET.

Leaks are modeled as EPANET emitters (orifice discharge, Q = C*sqrt(pressure)) -
the standard EPANET mechanism for pressure-dependent leakage. In leak scenarios
the leak is active from the first record; the detectors' baseline comes from
the separate no-leak scenario.
"""
import wntr
import pandas as pd

from core.network import NETWORK_PATH

PRESSURE_SENSOR_NODES = ["15", "35", "101", "105", "113", "201"]
SOURCE_LINK = "60"

NODE_LABELS = {
    "15":  "Northside Residential",
    "35":  "Downtown Commercial",
    "101": "Eastside Industrial",
    "105": "Central Park District",
    "113": "Westside Suburb",
    "201": "South Harbor Zone",
}


def generate_scenario(
    n_days: int = 14,
    leak_node: str | None = None,
    leak_start_hour: float | None = None,
    leak_coeff: float = 0.003,
    seed: int = 0,
) -> pd.DataFrame:
    wn = wntr.network.WaterNetworkModel(NETWORK_PATH)

    wn.options.time.duration = n_days * 24 * 3600
    wn.options.time.hydraulic_timestep = 900
    wn.options.time.report_timestep = 900

    if leak_node is not None:
        wn.get_node(leak_node).emitter_coefficient = leak_coeff

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    times = results.node["pressure"].index.values
    pressures = results.node["pressure"]
    flows = results.link["flowrate"]

    rows = []
    for i, t in enumerate(times):
        row = {
            "step": i,
            "hour_of_day": (t % (24 * 3600)) / 3600,
            "source_flow_Ls": flows.loc[t, SOURCE_LINK] * 1000,
            "leak_active": int(leak_node is not None),
            "leak_node": leak_node,
        }
        for node in PRESSURE_SENSOR_NODES:
            row[f"pressure_{node}"] = pressures.loc[t, node]
        rows.append(row)

    return pd.DataFrame(rows)
'''

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
    print("[1/3] scenarios ...", flush=True)
    for sc in SCENARIOS:
        dfs[sc["key"]] = get_or_generate(sc)
    df_normal = dfs["normal"]

    print("[2/3] training detectors on leak-free baseline ...", flush=True)
    mnf = MinimumNightFlowDetector(threshold_pct=0.20).fit(df_normal)
    twin = ResidualTwinDetector(sensor_cols=SENSOR_COLS).fit(df_normal)

    print("[3/3] scoring scenarios ...", flush=True)
    out = {}
    for sc in SCENARIOS:
        df = dfs[sc["key"]]
        has_leak = "leak_node" in sc["gen"]
        df_mnf, daily_mnf, thr = mnf.predict(df)
        df_tw = twin.predict(df)

        # honest lag: the nightly method's result is only knowable after the
        # 02:00-04:00 window completes, so flags only count from 04:00 onward
        df_mnf.loc[df_mnf["hour_of_day"] < 4.0, "mnf_flag"] = 0

        # sanity: leak effect on source flow vs the no-leak baseline
        note = ""
        if has_leak:
            base_f = df_normal["source_flow_Ls"].mean()
            leak_f = df[df.leak_active == 1]["source_flow_Ls"].mean()
            note = " | leak adds ~" + str(round(leak_f - base_f, 1)) + " L/s avg flow"

        out[sc["key"]] = dict(
            label=sc["label"],
            leak_node=sc["gen"].get("leak_node"),
            leak_start=("Day 1 00:00 (active from first record)" if has_leak else None),
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
        print("  " + sc["key"] + ": twin P=" + str(mt["precision"]) +
              " R=" + str(mt["recall"]) + " F1=" + str(mt["f1"]) +
              " lag=" + str(mt["detection_lag_hours"]) + "h | nightly P=" +
              str(mm["precision"]) + " R=" + str(mm["recall"]) + " F1=" +
              str(mm["f1"]) + " lag=" + str(mm["detection_lag_hours"]) + "h" + note,
              flush=True)

    payload = dict(
        meta=dict(steps_per_day=STEPS_PER_DAY, dt_min=DT_MIN,
                  sensors=[dict(id=n, label=NODE_LABELS.get(n, n)) for n in PRESSURE_SENSOR_NODES],
                  baseline_mnf_Ls=round(float(mnf.baseline_mnf_), 2)),
        order=[sc["key"] for sc in SCENARIOS],
        scenarios=out,
    )
    os.makedirs("dashboard/data", exist_ok=True)
    with open("dashboard/data/results.json", "w") as f:
        json.dump(payload, f)
    print("\nWROTE dashboard/data/results.json - refresh the browser (Ctrl+Shift+R)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\nPIPELINE ERROR - paste this traceback into the chat:")
        traceback.print_exc()
'''


def main():
    for rel, content in [("core/simulate.py", SIMULATE_PY),
                         ("make_data.py", MAKE_DATA_PY)]:
        path = os.path.join(ROOT, rel)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("wrote", rel)

    for pat in ["data/scenario_*.csv", "dashboard/data/results.json"]:
        for p in glob.glob(os.path.join(ROOT, pat)):
            os.remove(p)
            print("removed stale", os.path.basename(p))

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