"""Anomaly detection engine for health telemetry.

The :class:`AnomalyDetector` encapsulates logic for identifying anomalies in
health signals, simulating adversarial attacks, and computing high‑level
security posture metrics. Anomalies are detected via robust z‑scores
computed against a rolling baseline. Simulations inject missingness,
latency, spoofing or noise into data to test detection resilience.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from ..data_pipeline.normalization import build_robust_baseline, _mad


class AnomalyDetector:
    """Detect anomalies, simulate attacks and compute security metrics.

    Parameters
    ----------
    metrics:
        Optional list of metric column names. If None, a default set
        comprising sleep hours, resting heart rate, heart rate variability,
        steps, calories and weight is used.
    """

    DEFAULT_METRICS = ["sleep_hours", "resting_hr", "hrv", "steps", "calories", "weight"]

    def __init__(self, metrics: List[str] | None = None) -> None:
        self.metrics = metrics or self.DEFAULT_METRICS

    def compute_anomalies(self, df: pd.DataFrame) -> List[Dict[str, any]]:
        """Detect anomalies in the dataset using robust z‑scores.

        For each day, this method computes a robust z‑score for each metric
        relative to a rolling median and MAD baseline. It aggregates these
        scores into a single anomaly score. A day is considered anomalous if
        the score exceeds 1.5. Detailed driver information and a narrative
        description are returned for interpretability.

        Parameters
        ----------
        df:
            Input DataFrame sorted by date containing at least the metric
            columns specified at initialisation.

        Returns
        -------
        list
            A list of dictionaries, one per day, containing the anomaly
            results. Each dictionary includes ``user_id``, ``date``,
            ``anomaly_score``, ``is_anomaly``, a list of ``drivers`` and a
            ``narrative``.
        """
        df_base = build_robust_baseline(df)
        results: List[Dict[str, any]] = []
        for idx, row in df_base.iterrows():
            date = row["date"]
            drivers = []
            z_scores = []
            for m in self.metrics:
                val = row.get(m)
                med = row.get(f"{m}_median")
                mad = row.get(f"{m}_mad")
                if pd.isna(val) or pd.isna(med) or pd.isna(mad):
                    continue
                z = float((val - med) / (1.4826 * mad))
                z_scores.append(abs(z))
                if abs(z) > 2.0:
                    drivers.append({
                        "metric": m,
                        "value": float(val),
                        "z_score": z,
                        "direction": "high" if z > 0 else "low",
                    })
            if not z_scores:
                score = 0.0
            else:
                z_arr = np.array(z_scores)
                score = float(np.mean(z_arr) + 0.25 * np.max(z_arr))
            is_anom = score >= 1.5
            # Craft narrative
            if score < 1.0:
                narrative = f"{date}: Within normal variation."
            elif not drivers:
                narrative = f"{date}: Elevated deviation detected but no specific metric stands out."
            else:
                top = sorted(drivers, key=lambda d: abs(d["z_score"]), reverse=True)[:2]
                parts = []
                for d in top:
                    direction = "above" if d["direction"] == "high" else "below"
                    parts.append(f"{d['metric'].replace('_',' ')} is {direction} baseline (z={d['z_score']:.1f})")
                narrative = f"{date}: Anomaly (score={score:.2f}). " + "; ".join(parts) + "."
            results.append({
                "user_id": row["user_id"],
                "date": date,
                "anomaly_score": score,
                "is_anomaly": is_anom,
                "drivers": drivers,
                "narrative": narrative,
            })
        return results

    def simulate_attack(self, df: pd.DataFrame, mode: str = "missing", fraction: float = 0.1) -> pd.DataFrame:
        """Simulate adversarial tampering or noise injection on a copy of df.

        Supported modes:

        * ``missing`` – randomly set a fraction of values to NaN.
        * ``delay`` – copy values from a previous day to simulate delayed upload.
        * ``spoof`` – multiply values by a factor to simulate spoofed sensor data.
        * ``noise`` – add Gaussian noise to random values.
        """
        perturbed = df.copy()
        n_rows = len(df)
        for m in self.metrics:
            n_vals = int(n_rows * fraction)
            indices = np.random.choice(n_rows, n_vals, replace=False) if n_vals > 0 else []
            for idx in indices:
                if mode == "missing":
                    perturbed.at[idx, m] = np.nan
                elif mode == "delay":
                    src = max(0, idx - 3)
                    perturbed.at[idx, m] = df.at[src, m]
                elif mode == "spoof":
                    val = df.at[idx, m]
                    if pd.notna(val):
                        perturbed.at[idx, m] = val * (1.5 + np.random.rand())
                elif mode == "noise":
                    val = df.at[idx, m]
                    if pd.notna(val):
                        noise = np.random.normal(0, 0.1 * abs(val) if val != 0 else 0.1)
                        perturbed.at[idx, m] = val + noise
        return perturbed

    def compute_security_metrics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute high‑level security metrics for a dataset.

        Attack Surface Score – proportion of untrusted surface (1 - mean trust).
        Signal Integrity – mean trust across all metric/day combinations.
        Anomaly Precision/Recall – treating days with any missing values as
          ground‑truth anomalies. Precision is the fraction of detected
          anomalies that correspond to true anomalies; recall is the fraction
          of true anomalies detected.
        Mean Time to Detect (MTTD) – average number of days between the first
          occurrence of a ground‑truth anomaly and its detection.
        """
        # We reuse TrustEngine to compute trust scores on the fly
        from .trust_engine import TrustEngine  # imported here to avoid circular import
        trust_engine = TrustEngine(metrics=self.metrics)
        _, trust_entries = trust_engine.compute_trust_scores(df)
        trust_vals = [t["score"] for t in trust_entries]
        mean_trust = float(np.mean(trust_vals)) if trust_vals else 1.0
        attack_surface = 1.0 - mean_trust
        signal_integrity = mean_trust
        # Ground truth anomalies: any day with missing values
        true_anomaly_dates = []
        for _, row in df.iterrows():
            if any(pd.isna(row.get(m)) for m in self.metrics):
                true_anomaly_dates.append(row["date"])
        # Detected anomalies
        det_results = self.compute_anomalies(df)
        detected_dates = [r["date"] for r in det_results if r["is_anomaly"]]
        if not true_anomaly_dates:
            precision = 1.0
            recall = 1.0
            mttd = 0.0
        else:
            tp = len([d for d in detected_dates if d in true_anomaly_dates])
            fp = len(detected_dates) - tp
            fn = len([d for d in true_anomaly_dates if d not in detected_dates])
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            # MTTD calculation
            date_to_idx = {row["date"]: idx for idx, row in df.reset_index(drop=True).iterrows()}
            mttd_vals = []
            for adate in true_anomaly_dates:
                if adate in detected_dates:
                    mttd_vals.append(0.0)
                else:
                    a_idx = date_to_idx[adate]
                    future_detect_indices = [date_to_idx[d] for d in detected_dates if date_to_idx[d] > a_idx]
                    if future_detect_indices:
                        mttd_vals.append(min(future_detect_indices) - a_idx)
            mttd = float(np.mean(mttd_vals)) if mttd_vals else 0.0
        return {
            "attack_surface_score": attack_surface,
            "signal_integrity": signal_integrity,
            "anomaly_precision": precision,
            "anomaly_recall": recall,
            "mean_time_to_detect": mttd,
        }