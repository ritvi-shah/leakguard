#!/usr/bin/env python3
# fix_leak.py - leaks via EPANET emitters (EpanetSimulator ignores add_leak),
# purges stale CSVs, regenerates data, prints leak-effect sanity checks.
import glob
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))

SIMULATE_PY = r'''"""
Time-series scenario generator using WNTR/EPANET.

Leaks are modeled as EPANET emitters (orifice discharge, Q = C*sqrt(pressure)) -
the standard EPANET mechanism for pressure-dependent leakage. Note: WNTR's
add_leak() is only simulated by WNTRSimulator; EpanetSimulator ignores it.
"""
import wntr
import numpy as np
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
    leak_coeff: float = 0.003,   # emitter coeff, m^3/s per m^0.5
    seed: int = 0,
) -> pd.DataFrame:
    wn = wntr.network.WaterNetworkModel(NETWORK_PATH)

    wn.options.time.duration = n_days * 24 * 3600
    wn.options.time.hydraulic_timestep = 900
    wn.options.time.report_timestep = 900

    if leak_node is not None and leak_start_hour is not None:
        start_s = leak_start_hour * 3600
        # activate the emitter at leak start via source control pattern:
        # simplest reliable route - run once with emitter from t=0 handled by
        # two-phase approach is complex; EPANET emitters are always-on, so we
        # shift the timeline instead: leak active from the first step AFTER
        # start is handled below by zeroing the label pre-onset and, for
        # hydraulics, we emulate onset by running the sim WITH the emitter and
        # only labeling steps >= start. To keep hydraulics honest AND onset
        # real, we simulate the pre-leak period by disabling the emitter via
        # a tiny coefficient before start using a pattern is not supported;
        # therefore we run TWO sims and splice: no-leak before onset.
        pre = None
        if start_s > 0:
            wn_pre = wntr.network.WaterNetworkModel(NETWORK_PATH)
            wn_pre.options.time.duration = int(start_s)
            wn_pre.options.time.hydraulic_timestep = 900
            wn_pre.options.time.report_timestep = 900
            pre = wntr.sim.EpanetSimulator(wn_pre).run_sim()

        wn.get_node(leak_node).emitter_coefficient = leak_coeff
        post_duration = max(n_days * 24 * 3600 - start_s, 900)
        wn.options.time.duration = int(post_duration)
        post = wntr.sim.EpanetSimulator(wn).run_sim()

        return _assemble(pre, post, leak_node, start_s)

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()
    return _frame_from(results, leak_node=None, offset_s=0, pre_steps=0)


def _frame_from(results, leak_node, offset_s, pre_steps):
    times = results.node["pressure"].index.values
    pressures = results.node["pressure"]
    flows = results.link["flowrate"]
    rows = []
    for i, t in enumerate(times):
        abs_step = pre_steps + i
        rows.append({
            "step": abs_step,
            "hour_of_day": (t % (24 * 3600)) / 3600,
            "source_flow_Ls": flows.loc[t, SOURCE_LINK] * 1000,
            "leak_active": int(leak_node is not None),
            "leak_node": leak_node,
        })
        for node in PRESSURE_SENSOR_NODES:
            rows[-1][f"pressure_{node}"] = pressures.loc[t, node]
    return pd.DataFrame(rows)


def _assemble(pre, post, leak_node, start_s):
    pre_steps = int(start_s // 900)
    df_pre = _frame_from(pre, leak_node=None, offset_s=0, pre_steps=0)
    df_pre["step"] = range(pre_steps)
    df_post = _frame_from(post, leak_node=leak_node, offset_s=start_s,
                          pre_steps=pre_steps)
    df_post["step"] = range(pre_steps, pre_steps + len(df_post))
    # recompute hour_of_day continuously for post (EPANET restarts clock)
    for i in range(len(df_post)):
        secs = (pre_steps + i) * 900
        df_post.iloc[i, df_post.columns.get_loc("hour_of_day")] = (secs % 86400) / 3600
    out = pd.concat([df_pre, df_post], ignore_index=True)
    return out


if __name__ == "__main__":
    df = generate_scenario(n_days=14, leak_node="105",
                           leak_start_hour=8 * 24 + 10, leak_coeff=0.003)
    print(df.head())
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
    dict(key="leak_a", label="Scenario A - gradual aging pipe leak",
         csv="data/scenario_leak_a.csv",
         gen=dict(n_days=14, leak_node="105", leak_start_hour=8 * 24 + 10,
                  leak_coeff=0.003)),
    dict(key="leak_b", label="Scenario B - sudden pipe burst",
         csv="data/scenario_leak_b.csv",
         gen=dict(n_days=14, leak_node="201", leak_start_hour=5 * 24 + 2,
                  leak_coeff=0.010)),
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

        # sanity: did the leak actually change hydraulics?
        note = ""
        if has_leak:
            onset = int(df[df.leak_active == 1]["step"].min())
            pre_f = df[(df.step >= onset - 96) & (df.step < onset)]["source_flow_Ls"].mean()
            dur_f = df[df.leak_active == 1]["source_flow_Ls"].mean()
            note = " | leak adds ~" + str(round(dur_f - pre_f, 1)) + " L/s avg flow"

        out[sc["key"]] = dict(
            label=sc["label"],
            leak_node=sc["gen"].get("leak_node"),
            leak_start=fmt_time(sc["gen"]["leak_start_hour"] * 3600 / DT_MIN / 60) if has_leak else None,
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
        order=[sc["key"] for sc in SCENARIOS],
        scenarios=out,
    )
    os.makedirs("dashboard/data", exist_ok=True)
    with open("dashboard/data/results.json", "w") as f:
        json.dump(payload, f)
    print("\nWROTE dashboard/data/results.json")


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

    # purge stale data (generated without real leaks)
    for pat in ["data/scenario_*.csv", "dashboard/data/results.json"]:
        for p in glob.glob(os.path.join(ROOT, pat)):
            os.remove(p)
            print("removed stale", pat)

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