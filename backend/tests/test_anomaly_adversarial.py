"""
test_anomaly_adversarial.py
Adversarial test suite for the Phase 2 Anomaly Detection Engine.
Scenarios: Dirty Data, Limit Tests, Cross-Order Regulatory Conflict.
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai'))
from AnomalyDetection import AnomalyDetector


class TestAdversarialAnomalyDetection(unittest.TestCase):
    """Stress-test the Isolation Forest engine with edge-case and adversarial inputs."""

    @classmethod
    def setUpClass(cls):
        """Train the detector on clean historical baseline data."""
        np.random.seed(42)
        cls.detector = AnomalyDetector(contamination=0.02)
        history = pd.DataFrame({
            'cost_head': ['Power_Purchase'] * 500,
            'price_per_unit': np.random.normal(loc=4.0, scale=0.3, size=500),
            'volume_mw': np.random.normal(loc=500, scale=50, size=500)
        })
        cls.detector.load_historical_data(history, feature_columns=['price_per_unit', 'volume_mw'])

    # ──────────────────────────────────────────────
    # Scenario A: Dirty Data — Missing/NaN blocks
    # ──────────────────────────────────────────────
    def test_dirty_data_nan_values(self):
        """Engine must NOT crash on NaN values; it should either flag or handle gracefully."""
        dirty_df = pd.DataFrame({
            'cost_head': ['Power_Purchase', 'Power_Purchase'],
            'price_per_unit': [4.1, np.nan],  # One missing block
            'volume_mw': [500, 480]
        })
        # IsolationForest will propagate NaN issues — the system must catch this
        try:
            report = self.detector.analyze_petition_data(dirty_df)
            # If it runs, verify report structure is intact
            self.assertIn('total_records_analyzed', report)
            self.assertEqual(report['total_records_analyzed'], 2)
        except ValueError:
            # Acceptable: engine rightfully rejects unclean data
            pass
        print("  ✔️ Dirty Data (NaN) — Handled gracefully.")

    def test_dirty_data_negative_prices(self):
        """Negative power purchase prices are nonsensical and should be flagged as anomalies."""
        dirty_df = pd.DataFrame({
            'cost_head': ['Power_Purchase', 'Power_Purchase'],
            'price_per_unit': [-5.0, -10.0],  # Impossible values
            'volume_mw': [500, 600]
        })
        report = self.detector.analyze_petition_data(dirty_df)
        self.assertGreater(report['anomalies_detected'], 0, "Negative prices MUST be flagged as anomalies.")
        print("  ✔️ Dirty Data (Negative Prices) — Correctly flagged.")

    # ──────────────────────────────────────────────
    # Scenario B: The Limit Test — Exactly at normative cap
    # ──────────────────────────────────────────────
    def test_limit_exactly_on_boundary(self):
        """Values precisely at the historical mean should NOT be flagged."""
        boundary_df = pd.DataFrame({
            'cost_head': ['Power_Purchase'],
            'price_per_unit': [4.0],  # Exactly the trained mean
            'volume_mw': [500.0]       # Exactly the trained mean
        })
        report = self.detector.analyze_petition_data(boundary_df)
        self.assertEqual(report['anomalies_detected'], 0, "Exact-mean values should NOT be anomalous.")
        print("  ✔️ Limit Test (Exact Boundary) — No false positive.")

    def test_limit_one_sigma_above(self):
        """Values 1 standard deviation above mean should typically be inliers."""
        sigma_df = pd.DataFrame({
            'cost_head': ['Power_Purchase'],
            'price_per_unit': [4.3],  # ~1 sigma above mean
            'volume_mw': [550.0]
        })
        report = self.detector.analyze_petition_data(sigma_df)
        self.assertEqual(report['anomalies_detected'], 0, "1-sigma values should remain inliers.")
        print("  ✔️ Limit Test (1-Sigma Above) — Correctly classified as inlier.")

    # ──────────────────────────────────────────────
    # Scenario C: Cross-Order Regulatory Conflict
    # ──────────────────────────────────────────────
    def test_cross_order_regulatory_mismatch(self):
        """
        Simulate a petition referencing a retired regulation.
        The AI must flag anomalies when patterns deviate from the trained baseline order (30.06.2025).
        If data patterns from a 2019 Order are injected (different cost structure), the engine should flag.
        """
        # 2019-era data had much lower prices (~2.5 avg) — this is a structural mismatch
        retired_order_df = pd.DataFrame({
            'cost_head': ['Power_Purchase'] * 3,
            'price_per_unit': [2.5, 2.3, 2.6],  # Old order pricing regime
            'volume_mw': [300, 280, 310]          # Old order volumes
        })
        report = self.detector.analyze_petition_data(retired_order_df)
        self.assertGreater(
            report['anomalies_detected'], 0,
            "Cross-Order data from a retired regulation MUST trigger anomaly flags."
        )
        # Verify reasoning blocks exist for each flag
        for flag in report['flags']:
            self.assertIn('reasoning_block', flag)
            self.assertIsInstance(flag['reasoning_block'], str)
            self.assertGreater(len(flag['reasoning_block']), 0)
        print("  ✔️ Cross-Order Conflict — Regulatory Mismatch correctly detected.")


if __name__ == '__main__':
    print("=" * 60)
    print("Adversarial Anomaly Detection Test Suite")
    print("=" * 60 + "\n")
    unittest.main(verbosity=2)
