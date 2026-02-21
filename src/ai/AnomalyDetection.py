import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
import json
from datetime import datetime, timezone
from typing import Dict, Optional


class AnomalyDetector:
    """
    Phase 2: Isolation Forest Anomaly Detection for "Prudence Check" violations.
    Target: Sudden spikes in Short-term Power Purchase prices and other financial metrics.

    F-17: Scores are calibrated to [0, 1] using min-max normalization.
    F-18: Supports SBU-isolated training to prevent cross-SBU data leakage.
    """

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.feature_columns: list = []
        # F-18: Per-SBU model isolation — separate model per SBU
        self._models: Dict[str, IsolationForest] = {}
        self._score_ranges: Dict[str, tuple] = {}  # (min_score, max_score) per SBU
        self._global_model: Optional[IsolationForest] = None
        self._global_score_range: Optional[tuple] = None

    def _create_model(self) -> IsolationForest:
        return IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
        )

    def load_historical_data(
        self, df: pd.DataFrame, feature_columns: list, sbu_code: Optional[str] = None
    ):
        """
        Loads the 'normal' historical baseline data (e.g., 5-year trend).
        F-18: If sbu_code is provided, trains an SBU-specific model.
        """
        self.feature_columns = feature_columns
        features = df[self.feature_columns]

        if sbu_code:
            # F-18: SBU-isolated training — each SBU gets its own model
            model = self._create_model()
            model.fit(features)
            raw_scores = model.score_samples(features)
            self._models[sbu_code] = model
            self._score_ranges[sbu_code] = (float(raw_scores.min()), float(raw_scores.max()))
            print(
                f"[{datetime.now(timezone.utc).isoformat()}] "
                f"Isolation Forest trained for {sbu_code} on {len(df)} records."
            )
        else:
            # Global model (backward compatible)
            model = self._create_model()
            model.fit(features)
            raw_scores = model.score_samples(features)
            self._global_model = model
            self._global_score_range = (float(raw_scores.min()), float(raw_scores.max()))
            print(
                f"[{datetime.now(timezone.utc).isoformat()}] "
                f"Isolation Forest trained globally on {len(df)} records."
            )

    @property
    def is_trained(self) -> bool:
        return self._global_model is not None or len(self._models) > 0

    def _get_model_for_sbu(self, sbu_code: Optional[str]):
        """F-18: Resolve the correct model. SBU-specific first, then global fallback."""
        if sbu_code and sbu_code in self._models:
            return self._models[sbu_code], self._score_ranges[sbu_code]
        if self._global_model:
            return self._global_model, self._global_score_range
        raise ValueError("No model available. Train with load_historical_data() first.")

    def _calibrate_score(self, raw_score: float, score_range: tuple) -> float:
        """
        F-17: Calibrate raw Isolation Forest score to [0, 1] range.
        0.0 = completely normal, 1.0 = extreme anomaly.
        Raw scores are negative log-likelihood; more negative = more anomalous.
        """
        min_score, max_score = score_range
        if max_score == min_score:
            return 0.5  # degenerate case
        # Invert: lower raw score = higher anomaly score
        calibrated = 1.0 - (raw_score - min_score) / (max_score - min_score)
        return round(max(0.0, min(1.0, calibrated)), 4)

    def analyze_petition_data(
        self, test_df: pd.DataFrame, sbu_code: Optional[str] = None
    ) -> dict:
        """
        Analyzes new petition data for anomalies.
        F-17: Returns calibrated [0,1] anomaly scores.
        F-18: Uses SBU-specific model when available.
        """
        model, score_range = self._get_model_for_sbu(sbu_code)

        predictions = model.predict(test_df[self.feature_columns])
        raw_scores = model.score_samples(test_df[self.feature_columns])

        results = test_df.copy()
        results["is_anomaly"] = predictions == -1
        results["raw_anomaly_score"] = raw_scores
        results["calibrated_score"] = [
            self._calibrate_score(s, score_range) for s in raw_scores
        ]

        analysis_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "module": "AI-Prudence-Check-IsolationForest",
            "sbu_code": sbu_code or "GLOBAL",
            "total_records_analyzed": len(test_df),
            "anomalies_detected": int(sum(results["is_anomaly"])),
            "flags": [],
        }

        for idx, row in results[results["is_anomaly"]].iterrows():
            reasoning = self._generate_reasoning_block(row)
            flag = {
                "record_index": int(idx),
                "cost_head": row.get("cost_head", "Power_Purchase"),
                "value_analyzed": row[self.feature_columns].to_dict(),
                "calibrated_anomaly_score": row["calibrated_score"],  # F-17: [0, 1]
                "confidence_label": self._score_to_label(row["calibrated_score"]),
                "reasoning_block": reasoning,
            }
            analysis_report["flags"].append(flag)

        return analysis_report

    @staticmethod
    def _score_to_label(calibrated_score: float) -> str:
        """F-17: Human-readable anomaly confidence label."""
        if calibrated_score >= 0.9:
            return "CRITICAL — Extreme deviation"
        elif calibrated_score >= 0.7:
            return "HIGH — Significant deviation"
        elif calibrated_score >= 0.5:
            return "MODERATE — Notable deviation"
        else:
            return "LOW — Minor deviation"

    def _generate_reasoning_block(self, flagged_row) -> str:
        """Generates human-readable explanation for the regulatory officer."""
        head = flagged_row.get("cost_head", "Metric")
        price = flagged_row.get("price_per_unit", "N/A")
        score = flagged_row.get("calibrated_score", 0)
        label = self._score_to_label(score)

        reasoning = (
            f"PRUDENCE VIOLATION DETECTED [{label}]: The {head} value "
            f"demonstrates statistically significant deviation (anomaly score: {score:.2%}). "
            f"The analyzed instance ({price}) is an outlier relative to the "
            f"historical baseline established from prior control periods."
        )
        return reasoning


# --- Demo Execution Block ---
if __name__ == "__main__":
    np.random.seed(42)
    historical_prices = np.random.normal(loc=4.0, scale=0.3, size=1000)
    history_df = pd.DataFrame(
        {
            "cost_head": ["Power_Purchase"] * 1000,
            "price_per_unit": historical_prices,
            "volume_mw": np.random.normal(loc=500, scale=50, size=1000),
        }
    )

    detector = AnomalyDetector(contamination=0.01)

    # F-18: Train per-SBU
    detector.load_historical_data(
        history_df, feature_columns=["price_per_unit", "volume_mw"], sbu_code="SBU-G"
    )

    new_petition_df = pd.DataFrame(
        {
            "cost_head": ["Power_Purchase"] * 3,
            "price_per_unit": [4.1, 4.3, 12.5],  # 12.5 is the spike
            "volume_mw": [510, 480, 800],
        }
    )

    report = detector.analyze_petition_data(new_petition_df, sbu_code="SBU-G")

    print("\n--- AI Prudence Check Report (Calibrated) ---")
    print(json.dumps(report, indent=2))
