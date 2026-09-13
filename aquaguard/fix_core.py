#!/usr/bin/env python3
# fix_core.py - installs the correct WNTR core files (verbatim from your pasted
# versions), locates the Net3 .inp, verifies sensor IDs, then runs the pipeline.
import glob
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))

NETWORK_PY = r'''"""Net3 network file locator (EPANET .inp)."""
import glob
import os

import wntr

_PKG = os.path.dirname(wntr.__file__)

_CANDIDATES = [
    "temp.inp", "Net3.inp", "net3.inp",
    os.path.join("data", "temp.inp"),
    os.path.join("data", "Net3.inp"),
]
_CANDIDATES += sorted(glob.glob("*.inp"))
_CANDIDATES += sorted(glob.glob(os.path.join("data", "*.inp")))
_CANDIDATES += sorted(glob.glob(os.path.join(_PKG, "**", "Net3.inp"), recursive=True))

NETWORK_PATH = next((c for c in _CANDIDATES if os.path.exists(c)), None)

if NETWORK_PATH is None:
    raise FileNotFoundError(
        "Net3 .inp file not found. Place temp.inp (or Net3.inp) in the "
        "project root or the data/ folder.")
'''

SIMULATE_PY = r'''"""
Time-series scenario generator using WNTR.

Produces multi-day sensor time series (source flow + pressure sensors)
with realistic diurnal demand and injected leak events.
"""
import wntr
import numpy as np
import pandas as pd

from core.network import NETWORK_PATH

# Pressure sensor nodes from Net3
PRESSURE_SENSOR_NODES = ["15", "35", "101", "105", "113", "201"]
SOURCE_LINK = "60"  # connects the River reservoir

# Human-readable zone labels for display in the UI
NODE_LABELS = {
    "15":  "Northside Residential",
    "35":  "Downtown Commercial",
    "101": "Eastside Industrial",
    "105": "Central Park District",
    "113": "Westside Suburb",
    "201": "South Harbor Zone",
    "River": "Main Reservoir (River)",
    "Lake":  "Secondary Reservoir (Lake)",
}


def generate_scenario(
    n_days: int = 14,
    leak_node: str | None = None,
    leak_start_hour: float | None = None,
    leak_area: float = 0.005,
    seed: int = 0,
) -> pd.DataFrame:
    wn = wntr.network.WaterNetworkModel(NETWORK_PATH)

    wn.options.time.duration = n_days * 24 * 3600
    wn.options.time.hydraulic_timestep = 900  # 15 minutes
    wn.options.time.report_timestep = 900

    if leak_node is not None and leak_start_hour is not None:
        wn.get_node(leak_node).add_leak(
            wn,
            area=leak_area,
            start_time=leak_start_hour * 3600
        )

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    times = results.node['pressure'].index.values
    steps = len(times)

    pressures = results.node['pressure']
    flows = results.link['flowrate']

    leak_active_array = np.zeros(steps, dtype=int)
    if leak_node is not None and leak_start_hour is not None:
        start_step = int(leak_start_hour * 3600 / 900)
        leak_active_array[start_step:] = 1

    rows = []
    for i in range(steps):
        t = times[i]
        row = {
            "step": i,
            "hour_of_day": (t % (24 * 3600)) / 3600,
            "demand_multiplier": 1.0,
            "source_flow_Ls": flows.loc[t, SOURCE_LINK] * 1000,
            "leak_active": leak_active_array[i],
            "leak_node": leak_node if leak_active_array[i] else None,
        }
        for node in PRESSURE_SENSOR_NODES:
            row[f"pressure_{node}"] = pressures.loc[t, node]
        rows.append(row)

    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("Generating no-leak baseline scenario (14 days)...")
    df_normal = generate_scenario(n_days=14, seed=1)
    df_normal.to_csv("data/scenario_normal.csv", index=False)
    print(f"  saved {len(df_normal)} rows -> data/scenario_normal.csv")

    print("Generating Scenario A: gradual aging pipe leak at node 105 (day 8)...")
    df_leak_a = generate_scenario(
        n_days=14, leak_node="105", leak_start_hour=8 * 24 + 10,
        leak_area=0.005, seed=2)
    df_leak_a.to_csv("data/scenario_leak_a.csv", index=False)
    print(f"  saved {len(df_leak_a)} rows -> data/scenario_leak_a.csv")

    print("Generating Scenario B: sudden pipe burst at node 201 (day 5)...")
    df_leak_b = generate_scenario(
        n_days=14, leak_node="201", leak_start_hour=5 * 24 + 2,
        leak_area=0.015, seed=3)
    df_leak_b.to_csv("data/scenario_leak_b.csv", index=False)
    print(f"  saved {len(df_leak_b)} rows -> data/scenario_leak_b.csv")
'''

DETECTORS_PY = r'''"""
Leak detectors.

1. MinimumNightFlowDetector - the standard utility method: compare each
   night's 02:00-04:00 flow against a fitted baseline.
2. ResidualTwinDetector - a digital twin of expected pressures (function of
   time of day, learned on leak-free data); flags timesteps whose residual
   pattern is anomalous, and names the sensor with the largest unexpected
   pressure drop as the likely nearest point to the leak.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

STEPS_PER_DAY = 96


class MinimumNightFlowDetector:
    """Flags a day as leaking if its 2-4am average flow exceeds the
    baseline MNF by more than `threshold_pct`."""

    def __init__(self, threshold_pct: float = 0.20, baseline_days: int = 5):
        self.threshold_pct = threshold_pct
        self.baseline_days = baseline_days

    def fit(self, df_normal: pd.DataFrame):
        night = df_normal[(df_normal.hour_of_day >= 2) & (df_normal.hour_of_day < 4)]
        self.baseline_mnf_ = night["source_flow_Ls"].mean()
        self.baseline_std_ = night["source_flow_Ls"].std()
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
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
    """Twin = expected pressure per sensor per hour, learned on leak-free
    data. IsolationForest scores the residual vector; the sensor with the
    largest negative residual (unexpected pressure drop) localizes."""

    def __init__(self, sensor_cols: list[str], contamination: float = 0.05):
        self.sensor_cols = sensor_cols
        self.contamination = contamination

    def _expected_pressure(self, df: pd.DataFrame) -> pd.DataFrame:
        expected = pd.DataFrame(index=df.index)
        for col in self.sensor_cols:
            bin_means = self._twin_tables[col]
            hour_bin = (df["hour_of_day"] * 4).round().astype(int) % (24 * 4)
            expected[col] = hour_bin.map(bin_means)
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

        norm_resid = (residuals - self.resid_mean_) / self.resid_std_
        self.model_ = IsolationForest(
            n_estimators=200, contamination=self.contamination, random_state=42
        )
        self.model_.fit(norm_resid)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        expected = self._expected_pressure(df)
        residuals = df[self.sensor_cols].values - expected[self.sensor_cols].values
        norm_resid = (residuals - self.resid_mean_) / self.resid_std_

        raw_pred = self.model_.predict(norm_resid)
        df["twin_flag"] = (raw_pred == -1).astype(int)
        df["anomaly_score"] = -self.model_.score_samples(norm_resid)

        resid_df = pd.DataFrame(residuals, columns=self.sensor_cols, index=df.index)
        df["likely_leak_near"] = resid_df.idxmin(axis=1)
        return df


def score_detection(df: pd.DataFrame, flag_col: str) -> dict:
    """Precision/recall/F1 vs ground truth, plus detection lag in hours."""
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
            lag_steps = flagged_after[0] - onset
            lag_hours = lag_steps * 15 / 60

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


def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("wrote", rel)


def main():
    write("core/network.py", NETWORK_PY)
    write("core/simulate.py", SIMULATE_PY)
    write("core/detectors.py", DETECTORS_PY)
    print()

    sys.path.insert(0, ROOT)
    os.chdir(ROOT)

    try:
        import wntr
        print("wntr version:", wntr.__version__)
    except ImportError:
        print("\nwntr is NOT installed. Run:  pip install wntr  then re-run this script.")
        return

    from core.network import NETWORK_PATH
    print("Net3 inp file:", os.path.abspath(NETWORK_PATH))

    # verify sensor/link IDs exist in the model
    wn = wntr.network.WaterNetworkModel(NETWORK_PATH)
    missing_nodes = [n for n in ["15", "35", "101", "105", "113", "201"]
                     if wn.get_node(n) is None]
    link_ok = True
    try:
        wn.get_link("60")
    except Exception:
        link_ok = False
    print("sensor nodes present:", "YES" if not missing_nodes else "MISSING " + str(missing_nodes))
    print("source link '60' present:", "YES" if link_ok else "NO")
    if missing_nodes or not link_ok:
        print("\nThe .inp found is not the expected Net3 file. Place the temp.inp")
        print("from your other session into the project root and re-run.")
        return

    print("\nRunning the data pipeline (EPANET sims; cached in data/ after first run)...")
    try:
        import make_data
        make_data.main()
    except Exception:
        print("\nPIPELINE ERROR - paste this traceback into the chat:")
        traceback.print_exc()


if __name__ == "__main__":
    main()