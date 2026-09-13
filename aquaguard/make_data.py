"""Runs the WNTR/EPANET pipeline; auto-calibrates leak sizes so they are
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
