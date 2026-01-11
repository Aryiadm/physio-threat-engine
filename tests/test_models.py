"""Unit tests for the TrustEngine and AnomalyDetector classes.

These tests verify that the core ML logic produces reasonable outputs.
In particular, they ensure trust scores fall within the [0,1] range and
that adding noise via the simulation pipeline leads to an increase in
detected anomalies. Running these tests demonstrates robustness
characteristics of the model and highlights best practices for testing
machine learning code.
"""

import unittest
import numpy as np
import pandas as pd

from backend.models.trust_engine import TrustEngine
from backend.models.anomaly_detector import AnomalyDetector


class TestModels(unittest.TestCase):
    """Test suite for model classes."""

    def setUp(self) -> None:
        # Seed the random number generator for reproducibility
        np.random.seed(42)
        # Create a synthetic dataset for a single user across 30 days
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        self.df = pd.DataFrame({
            'user_id': ['test'] * len(dates),
            'date': dates.strftime('%Y-%m-%d'),
            'sleep_hours': np.random.normal(7, 0.5, len(dates)),
            'resting_hr': np.random.normal(60, 5, len(dates)),
            'hrv': np.random.normal(50, 10, len(dates)),
            'steps': np.random.normal(8000, 1000, len(dates)),
            'calories': np.random.normal(2000, 200, len(dates)),
            'weight': np.random.normal(70, 3, len(dates)),
        })

    def test_trust_scores_range(self) -> None:
        """Trust scores should always lie within [0, 1]."""
        engine = TrustEngine()
        _, entries = engine.compute_trust_scores(self.df.copy())
        for e in entries:
            self.assertGreaterEqual(e['score'], 0.0)
            self.assertLessEqual(e['score'], 1.0)

    def test_noise_simulation_detects_anomalies(self) -> None:
        """Noise injection should result in more detected anomalies."""
        detector = AnomalyDetector()
        # Baseline anomaly count
        baseline_results = detector.compute_anomalies(self.df.copy())
        baseline_anoms = [r for r in baseline_results if r['is_anomaly']]
        # Apply noise simulation
        df_noise = detector.simulate_attack(self.df.copy(), mode='noise', fraction=0.3)
        noise_results = detector.compute_anomalies(df_noise)
        noise_anoms = [r for r in noise_results if r['is_anomaly']]
        # We expect at least as many anomalies after noise injection
        self.assertGreaterEqual(len(noise_anoms), len(baseline_anoms))
        # There should be at least one anomaly detected in the noisy dataset
        self.assertTrue(any(r['is_anomaly'] for r in noise_results))


if __name__ == '__main__':
    unittest.main()