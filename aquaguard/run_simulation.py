"""One-command AquaGuard pipeline:
  simulate 14 days -> run both detectors -> evaluate vs ground truth
  -> print metric table -> write data/telemetry.csv + dashboard/data/results.json
"""

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from core.simulate import run_simulation
from core.detectors import run_all_detectors
from core.network import build_network, SENSOR_NODES, LEAK_NODE, SOURCE_HEAD_M


def build_all(cfg=None, verbose=True):
    if verbose:
        print("[1/4] simulating network hydraulics ...")
    telemetry, meta, net = run_simulation(cfg, verbose=verbose)

    if verbose:
        print("[2/4] running detectors (MNF + digital twin) ...")
    det = run_all_detectors(telemetry, meta)

    if verbose:
        print("[3/4] evaluating against ground truth ...")
    report = {
        "meta": meta,
        "network": {
            "nodes": [{"id": n, "x": net.x[n], "y": net.y[n], "elev": net.elevations[n],
                       "demand_lps": net.base_demand_m3s[n] * 1000,
                       "is_sensor": n in SENSOR_NODES, "is_leak": n == LEAK_NODE,
                       "is_source": n == net.reservoir_id} for n in net.node_ids],
            "edges": [{"id": p["id"], "from": p["from_node"], "to": p["to_node"]}
                      for p in net.pipes],
            "n_loops": net.n_loops, "source_head_m": SOURCE_HEAD_M,
        },
        "times": [str(t) for t in pd.DatetimeIndex(telemetry["time"])],
        "series": {
            "source_flow_lps": telemetry["source_flow_lps"].round(3).tolist(),
            "leak_flow_lps": telemetry["leak_flow_lps"].round(3).tolist(),
            "leak_active": telemetry["leak_active"].astype(int).tolist(),
            "pressure": {s: telemetry[f"p_sensor_{s}"].round(3).tolist() for s in SENSOR_NODES},
            "mnf_alert": det["mnf"]["alert"].astype(int).tolist(),
            "ml_alert": det["digital_twin"]["alert"].astype(int).tolist(),
            "localized_node": [v if v else "" for v in det["digital_twin"]["localized"]],
            "resid_z": {s: np.round(det["digital_twin"]["z"][:, j], 2).tolist()
                        for j, s in enumerate(SENSOR_NODES)},
        },
        "metrics": {"mnf": det["mnf"]["metrics"],
                    "digital_twin": det["digital_twin"]["metrics"]},
        "mnf_nightly": det["mnf"]["info"]["nightly"],
    }

    os.makedirs("data", exist_ok=True)
    os.makedirs("dashboard/data", exist_ok=True)
    telemetry.to_csv("data/telemetry.csv", index=False)
    with open("dashboard/data/results.json", "w") as f:
        json.dump(report, f)

    if verbose:
        print("[4/4] artifacts written: data/telemetry.csv, dashboard/data/results.json\n")
        _print_report(report)
    return report


def _print_report(rep):
    leak_node, leak_start = rep["meta"]["leak_node"], rep["meta"]["leak_start"]
    print("=" * 76)
    print(f"SCENARIO  leak node {leak_node}  -  starts {leak_start}  -  "
          f"{len(rep['times'])} timesteps @ {rep['meta']['dt_min']} min")
    print("=" * 76)
    print(f"{'Detector':<38}{'Precision':>10}{'Recall':>8}{'F1':>7}{'Lag':>12}")
    print("-" * 76)
    for key, label in [("mnf", "Minimum Night Flow (status quo)"),
                       ("digital_twin", "Digital-twin ML detector (ours)")]:
        m = rep["metrics"][key]
        print(f"{label:<38}{m['precision']:>10.2f}{m['recall']:>8.2f}"
              f"{m['f1']:>7.2f}{str(m['detection_lag']):>12}")
    print("-" * 76)
    dt = rep["metrics"]["digital_twin"]
    acc = dt["localization_accuracy"]
    print(f"Localization: {dt['localized_readings']} significant flagged readings, "
          f"{(acc * 100 if acc else 0):.1f}% mapped to true leak node {leak_node}")
    print(f"Nightly mean source flow (L/s): {rep['mnf_nightly']}\n")


if __name__ == "__main__":
    build_all()
