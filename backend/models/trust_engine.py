"""Trust scoring engine for health telemetry.

The :class:`TrustEngine` encapsulates the logic for computing trust scores
for health signals and performing federated trust evaluation. Trust scores
quantify the confidence in each metric on each day based on missingness,
distribution shifts relative to a rolling baseline and cross‑signal
deviations. Federated trust scores compare a user's aggregate signal
distribution to a global cohort distribution in a privacy‑preserving way.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from ..data_pipeline.normalization import build_robust_baseline, _mad


class TrustEngine:
    """Compute trust scores for health metrics and federated trust for a user.

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

    def compute_trust_scores(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, any]]]:
        """Compute a trust score for each metric on each day.

        The trust score is derived from three factors:

        * Missingness: if the value is missing, trust = 0.
        * Distribution shift: robust z‑score relative to the rolling baseline. A large
          z reduces trust; a score of 1 indicates no deviation.
        * Cross‑signal deviation: predicted value using a linear combination of other
          metrics. If the actual value is far from the predicted one, trust is lower.

        The returned DataFrame includes additional columns ``trust_{metric}`` for
        each metric. The second return value is a flat list of trust entries
        containing the metric name, date, score and drivers for serialisation.

        Parameters
        ----------
        df:
            Input DataFrame sorted by date containing at least the metric
            columns specified at initialisation.

        Returns
        -------
        tuple
            A tuple ``(df_with_trust, trust_entries)`` where ``df_with_trust`` is
            a copy of ``df`` with trust columns attached and ``trust_entries`` is
            a list of dictionaries with keys ``metric``, ``date``, ``score`` and
            ``drivers``.
        """
        df_baseline = build_robust_baseline(df)
        # Compute correlation matrix using complete cases only
        corr = df[self.metrics].corr()
        trust_entries: List[Dict[str, any]] = []
        # Precompute linear predictors: for each metric m, compute weights to
        # predict m from other metrics using correlation coefficients.
        predictor_weights: Dict[str, Dict[str, float]] = {}
        for m in self.metrics:
            others = [o for o in self.metrics if o != m]
            sub_corr = corr.loc[others, others]
            target = corr.loc[others, m]
            try:
                weights = np.linalg.solve(sub_corr.values, target.values)
                predictor_weights[m] = dict(zip(others, weights))
            except Exception:
                predictor_weights[m] = {o: 0.0 for o in others}
        # Iterate through rows to compute trust scores
        for idx, row in df_baseline.iterrows():
            date = row["date"]
            for m in self.metrics:
                val = row.get(m)
                median = row.get(f"{m}_median")
                mad = row.get(f"{m}_mad")
                if pd.isna(val):
                    score = 0.0
                    drivers = ["missing"]
                else:
                    drivers = []
                    # Distribution shift factor
                    if pd.isna(median) or pd.isna(mad):
                        z = 0.0
                    else:
                        z = float((val - median) / (1.4826 * mad))
                    dist_score = max(0.0, 1.0 - min(abs(z) / 3.0, 1.0))
                    if dist_score < 0.6:
                        drivers.append("distribution shift")
                    # Cross‑signal deviation factor
                    others = [o for o in self.metrics if o != m]
                    preds = [row.get(o) if pd.notna(row.get(o)) else 0.0 for o in others]
                    predicted = sum(predictor_weights[m][o] * preds[i] for i, o in enumerate(others))
                    residual = abs(val - predicted)
                    # Normalise residual by overall MAD of the metric
                    overall_mad = _mad(df[m].dropna())
                    res_score = max(0.0, 1.0 - min(residual / (3.0 * overall_mad), 1.0))
                    if res_score < 0.6:
                        drivers.append("cross‑signal deviation")
                    # Combine factors multiplicatively
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

    def _compute_embedding(self, df: pd.DataFrame) -> np.ndarray:
        """Compute a normalised embedding vector for a user's signal distribution.

        The embedding is the mean of each metric across the DataFrame, normalised
        to unit length. Missing values are ignored when computing the mean.
        """
        means = []
        for m in self.metrics:
            series = df[m].dropna()
            if len(series) == 0:
                means.append(0.0)
            else:
                means.append(float(series.mean()))
        vec = np.array(means, dtype=float)
        norm = np.linalg.norm(vec) + 1e-8
        return vec / norm

    def compute_federated_trust_score(self, user_df: pd.DataFrame, global_df: pd.DataFrame) -> float:
        """Compute a privacy‑preserving federated trust score for a user.

        A local embedding is compared to a global cohort embedding using cosine
        similarity. The similarity is mapped to [0,1] such that +1 → 1.0 and
        -1 → 0.0. This method does not leak raw signal values; only the
        aggregate embeddings are compared.
        """
        user_embed = self._compute_embedding(user_df)
        global_embed = self._compute_embedding(global_df)
        dot = float(np.dot(user_embed, global_embed))
        denom = float(np.linalg.norm(user_embed) * np.linalg.norm(global_embed) + 1e-8)
        similarity = dot / denom
        trust_score = max(0.0, min((similarity + 1.0) / 2.0, 1.0))
        return trust_score