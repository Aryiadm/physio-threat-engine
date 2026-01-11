"""Data pipeline utilities for the Physiological Threat Intelligence Engine.

This package contains modules that implement data normalisation and baseline
computation for health signals. By isolating these functions from the
models, the core ML components can operate independently of the details
of rolling statistics and z‑score calculations. Additional preprocessing
modules should be added here as the pipeline evolves.
"""

from .normalization import build_robust_baseline, _mad  # noqa: F401