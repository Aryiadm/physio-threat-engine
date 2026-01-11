"""Normalization utilities for health telemetry.

This module implements robust baseline estimation and median absolute
deviation computation used throughout the threat intelligence engine.

The functions here are intentionally stateless so they can be reused by
different model components. A rolling baseline is built via a median and
MAD computed on a sliding window; the baseline is shifted by one day to
avoid peeking into the future. The MAD function includes a small epsilon
to avoid divide‑by‑zero errors when the data has little variation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from typing import Optional

def _mad(series: pd.Series) -> float:
    """Compute the median absolute deviation of a Pandas Series.

    If the MAD is extremely small, a minimum epsilon is returned to avoid
    numerical issues when dividing by zero. The MAD is a robust measure
    of scale used to compute z‑scores in a way that is less sensitive to
    outliers than the standard deviation.
    """
    median = series.median()
    mad = np.median(np.abs(series - median))
    return float(mad if mad > 1e-6 else 1e-6)


def build_robust_baseline(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Attach rolling median and MAD baselines to a DataFrame.

    For each metric column in the input DataFrame, this function computes a
    rolling median and median absolute deviation (MAD) over a preceding
    window of days. The baseline columns are suffixed with ``_median`` and
    ``_mad`` respectively. To prevent look‑ahead bias, the baselines are
    shifted by one day so that the current day's value is compared only to
    past data. The minimum window size is half the window or 5, whichever
    is larger. Missing values are ignored in the rolling computations.

    Parameters
    ----------
    df:
        Input DataFrame containing numeric metric columns. It must include
        the date column and at least one metric.
    window:
        Size of the rolling window in days. Defaults to 14.

    Returns
    -------
    pandas.DataFrame
        A copy of the input DataFrame with additional columns for the
        rolling median and MAD for each metric. The new columns are named
        ``{metric}_median`` and ``{metric}_mad``.
    """
    out = df.copy()
    # Determine which columns are metrics: numeric and not the date or user_id
    metric_cols = [col for col in df.columns if col not in {"date", "user_id"}]
    for m in metric_cols:
        # Rolling median
        out[f"{m}_median"] = (
            out[m]
            .rolling(window=window, min_periods=max(5, window // 2))
            .median()
            .shift(1)
        )
        # Rolling MAD using the helper; note the shift
        out[f"{m}_mad"] = (
            out[m]
            .rolling(window=window, min_periods=max(5, window // 2))
            .apply(_mad, raw=False)
            .shift(1)
        )
    return out