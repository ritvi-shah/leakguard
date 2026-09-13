"""Leak detectors.

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
