"""
a zero‑trust, resilient ingestion pipeline that can detect data
poisoning, drift and outliers — concepts borrowed from AI‑driven
cybersecurity systems.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import random
METRICS = ["sleep_hours", "resting_hr", "hrv", "steps", "calories", "weight"]


def _mad(series: pd.Series) -> float:
    """Compute the median absolute deviation with a small epsilon to avoid zero."""
    median = series.median()
    mad = np.median(np.abs(series - median))
    return float(mad if mad > 1e-6 else 1e-6)


def build_robust_baseline(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Attach rolling median and MAD baselines to a DataFrame.

    For each metric, compute a rolling median and MAD over a preceding window
    of days. The baseline is shifted so that the current day's value is
    compared only to past data, avoiding look‑ahead bias.
    """
    out = df.copy()
    for m in METRICS:
        out[f"{m}_median"] = out[m].rolling(window=window, min_periods=max(5, window // 2)).median().shift(1)
        out[f"{m}_mad"] = out[m].rolling(window=window, min_periods=max(5, window // 2)).apply(_mad).shift(1)
    return out


def compute_trust_scores(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, any]]]:
    """ Compute a trust score for each metric on each day.

    The trust score is derived from three factors:

    • Missingness: if the value is missing, trust = 0.
    • Distribution shift: robust z‑score relative to the rolling baseline. A large
      z reduces trust; a score of 1 indicates no deviation.
    • Cross‑signal deviation: predicted value using a linear combination of other
      metrics. If the actual value is far from the predicted one, trust is lower.

    Returns the original DataFrame with additional columns for trust scores per
    metric, and a flattened list of trust entries for serialisation.
    """
    df_baseline = build_robust_baseline(df)
    # Compute cross‑correlation matrix using complete cases only
    corr = df[METRICS].corr()
    trust_entries = []
    # Precompute simple linear predictors: for each metric m, build weights to
    # predict m from the remaining metrics using correlation coefficients.
    predictor_weights: Dict[str, Dict[str, float]] = {}
    for m in METRICS:
        # Solve linear system: corr[m, others] * weights = corr[others,m]
        others = [o for o in METRICS if o != m]
        sub_corr = corr.loc[others, others]
        target = corr.loc[others, m]
        try:
            weights = np.linalg.solve(sub_corr.values, target.values)
            predictor_weights[m] = dict(zip(others, weights))
        except Exception:
            # Fallback: no prediction if matrix is singular
            predictor_weights[m] = {o: 0.0 for o in others}

    # Iterate through rows to compute trust scores
    for idx, row in df_baseline.iterrows():
        date = row["date"]
        for m in METRICS:
            val = row.get(m)
            median = row.get(f"{m}_median")
            mad = row.get(f"{m}_mad")
            # Missingness factor
            if pd.isna(val):
                score = 0.0
                drivers = ["missing"]
            else:
                drivers = []
                # Distribution shift factor
                if pd.isna(median) or pd.isna(mad):
                    # Not enough data to compute baseline
                    z = 0.0
                else:
                    z = float((val - median) / (1.4826 * mad))
                dist_score = max(0.0, 1.0 - min(abs(z) / 3.0, 1.0))  # saturate at z=3
                if dist_score < 0.6:
                    drivers.append("distribution shift")
                # Cross‑signal deviation factor
                # Compute predicted value using linear combination of other metrics
                others = [o for o in METRICS if o != m]
                preds = [row.get(o) if pd.notna(row.get(o)) else 0.0 for o in others]
                predicted = sum(predictor_weights[m][o] * preds[i] for i, o in enumerate(others))
                # Normalise residual by baseline MAD if available
                residual = abs(val - predicted)
                # Determine typical scale: use median absolute deviation of the metric over the entire df
                overall_mad = _mad(df[m].dropna())
                res_score = max(0.0, 1.0 - min(residual / (3.0 * overall_mad), 1.0))
                if res_score < 0.6:
                    drivers.append("cross‑signal deviation")
                # Combine factors multiplicatively to reflect joint confidence
                score = dist_score * res_score
            col_name = f"trust_{m}"
            df_baseline.at[idx, col_name] = score
            trust_entries.append({
                "metric": m,
                "date": date,
                "score": float(score),
                "drivers": drivers,
            })
    return df_baseline, trust_entries


def compute_anomalies(df: pd.DataFrame) -> List[Dict[str, any]]:
    """Detect anomalies in the dataset using robust z‑scores.

    For each day, compute a robust z‑score for each metric relative to the
    rolling baseline. Aggregate these into a single anomaly score by taking
    the mean absolute z plus a fraction of the maximum absolute z. This helps
    emphasise extreme deviations. A threshold of 1.5 is used to determine
    whether the day is anomalous.
    """
    df_base = build_robust_baseline(df)
    results: List[Dict[str, any]] = []
    for idx, row in df_base.iterrows():
        date = row["date"]
        drivers = []
        z_scores = []
        for m in METRICS:
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
        # Craft narrative message
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


def compute_correlations(df: pd.DataFrame) -> List[Dict[str, any]]:
    """Compute pairwise Pearson correlations between metrics.

    Returns a list of dictionaries with metric pairs and their correlation
    coefficients. Values range in [‑1,1]. Missing values are ignored. Pairs
    where one or both metrics have insufficient data produce NaN and are
    omitted.
    """
    corr = df[METRICS].corr()
    correlations: List[Dict[str, any]] = []
    for i, m1 in enumerate(METRICS):
        for j in range(i + 1, len(METRICS)):
            m2 = METRICS[j]
            c = corr.loc[m1, m2]
            if pd.isna(c):
                continue
            correlations.append({
                "metric_x": m1,
                "metric_y": m2,
                "correlation": float(c),
            })
    return correlations


def simulate_attack(df: pd.DataFrame, mode: str = "missing", fraction: float = 0.1) -> pd.DataFrame:
    """Simulate adversarial tampering or noise injection on a copy of df.

    The function returns a new DataFrame with a specified fraction of values
    altered. Supported modes:

    • missing – randomly set a fraction of data points to NaN.
    • delay – copy values from a previous day to simulate delayed upload.
    • spoof – multiply values by a factor to simulate spoofed sensor data.
    • noise – add Gaussian noise to random values.
    """
    perturbed = df.copy()
    n_rows = len(df)
    for m in METRICS:
        n_vals = int(n_rows * fraction)
        indices = random.sample(range(n_rows), n_vals) if n_vals > 0 else []
        for idx in indices:
            if mode == "missing":
                perturbed.at[idx, m] = np.nan
            elif mode == "delay":
                # Copy value from three days earlier if available
                src = max(0, idx - 3)
                perturbed.at[idx, m] = df.at[src, m]
            elif mode == "spoof":
                val = df.at[idx, m]
                if pd.notna(val):
                    perturbed.at[idx, m] = val * (1.5 + random.random())  # between 1.5x and 2.5x
            elif mode == "noise":
                val = df.at[idx, m]
                if pd.notna(val):
                    noise = np.random.normal(0, 0.1 * abs(val) if val != 0 else 0.1)
                    perturbed.at[idx, m] = val + noise
    return perturbed
