"""
VectorizedBlockIngestion.py
Performance-optimized ingestion of 15-minute block data (35,040 rows/year).
Uses NumPy vectorized operations to ensure Prudence Check executes in < 5 seconds.
"""

import numpy as np
import pandas as pd
import time
import json
from datetime import datetime


class VectorizedPrudenceEngine:
    """
    High-performance vectorized engine for processing 15-minute block
    power purchase data (365 days × 96 blocks = 35,040 rows per year).
    """

    def __init__(self, historical_mean: float, historical_std: float, z_threshold: float = 3.0):
        self.historical_mean = historical_mean
        self.historical_std = historical_std
        self.z_threshold = z_threshold  # Z-score threshold for anomaly flagging

    def ingest_and_analyze(self, block_data: np.ndarray) -> dict:
        """
        Vectorized analysis of an entire year's 15-minute block data.
        Uses NumPy broadcasting instead of row-by-row iteration.

        Args:
            block_data: 1-D NumPy array of price_per_unit values (35,040 entries).

        Returns:
            JSON-serializable report dict.
        """
        start = time.perf_counter()

        # Vectorized Z-score computation (no loops)
        z_scores = (block_data - self.historical_mean) / self.historical_std

        # Boolean mask for anomalies
        anomaly_mask = np.abs(z_scores) > self.z_threshold
        anomaly_count = int(np.sum(anomaly_mask))
        anomaly_indices = np.where(anomaly_mask)[0]

        # Vectorized statistics
        stats = {
            "mean": round(float(np.mean(block_data)), 4),
            "std": round(float(np.std(block_data)), 4),
            "min": round(float(np.min(block_data)), 4),
            "max": round(float(np.max(block_data)), 4),
            "p95": round(float(np.percentile(block_data, 95)), 4),
            "p99": round(float(np.percentile(block_data, 99)), 4),
        }

        elapsed = time.perf_counter() - start

        # Build flags for anomalous blocks (capped at 50 for report readability)
        flags = []
        for idx in anomaly_indices[:50]:
            flags.append({
                "block_index": int(idx),
                "day": int(idx // 96) + 1,
                "slot": int(idx % 96) + 1,
                "price": round(float(block_data[idx]), 4),
                "z_score": round(float(z_scores[idx]), 4),
                "reasoning": (
                    f"Block {int(idx)} (Day {int(idx // 96) + 1}, Slot {int(idx % 96) + 1}) "
                    f"has price {block_data[idx]:.4f} with Z-score {z_scores[idx]:.2f}, "
                    f"exceeding the ±{self.z_threshold} threshold."
                )
            })

        report = {
            "timestamp": datetime.now().isoformat(),
            "module": "VectorizedPrudenceEngine",
            "total_blocks_analyzed": len(block_data),
            "anomalies_detected": anomaly_count,
            "execution_time_seconds": round(elapsed, 6),
            "performance_target_met": elapsed < 5.0,
            "statistics": stats,
            "flags": flags
        }

        return report


# --- Demo Execution ---
if __name__ == "__main__":
    print("=" * 60)
    print("Vectorized 15-Minute Block Ingestion Performance Test")
    print("=" * 60)

    np.random.seed(42)

    # Simulate one full year: 365 days × 96 blocks = 35,040 rows
    BLOCKS_PER_YEAR = 365 * 96  # 35,040

    # Normal market prices with 5 injected extreme spikes
    block_prices = np.random.normal(loc=4.0, scale=0.3, size=BLOCKS_PER_YEAR)
    spike_indices = np.random.choice(BLOCKS_PER_YEAR, size=5, replace=False)
    block_prices[spike_indices] = np.random.uniform(12.0, 18.0, size=5)

    print(f"\nGenerated {BLOCKS_PER_YEAR:,} block records.")
    print(f"Injected {len(spike_indices)} extreme price spikes.\n")

    # Run the vectorized engine
    engine = VectorizedPrudenceEngine(historical_mean=4.0, historical_std=0.3, z_threshold=3.0)
    report = engine.ingest_and_analyze(block_prices)

    print(f"Execution Time: {report['execution_time_seconds']}s")
    print(f"Performance Target (< 5s): {'✅ PASS' if report['performance_target_met'] else '❌ FAIL'}")
    print(f"Anomalies Detected: {report['anomalies_detected']}")
    print(f"\nStatistics: {json.dumps(report['statistics'], indent=2)}")

    if report['flags']:
        print(f"\nSample Flags (showing first 3):")
        for flag in report['flags'][:3]:
            print(f"  - {flag['reasoning']}")
