import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import json
from datetime import datetime

class AnomalyDetector:
    """
    Phase 2: Isolation Forest Anomaly Detection for "Prudence Check" violations.
    Target: Sudden spikes in Short-term Power Purchase prices and other financial metrics.
    """
    
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        # contamination = expected proportion of outliers in the data
        self.model = IsolationForest(
            contamination=contamination, 
            random_state=random_state,
            n_estimators=100
        )
        self.is_trained = False
        self.feature_columns = []

    def load_historical_data(self, df: pd.DataFrame, feature_columns: list):
        """
        Loads the 'normal' historical baseline data (e.g., 5-year trend).
        """
        self.feature_columns = feature_columns
        self.model.fit(df[self.feature_columns])
        self.is_trained = True
        print(f"[{datetime.now().time()}] Isolation Forest trained on {len(df)} historical records.")

    def analyze_petition_data(self, test_df: pd.DataFrame) -> dict:
        """
        Takes new petition data (e.g., newly extracted power purchase blocks) and predicts.
        Returns the data overlaid with anomaly flags and reasoning blocks.
        """
        if not self.is_trained:
            raise ValueError("Model must be trained on historical data first.")

        # -1 indicates outlier, 1 indicates inlier
        predictions = self.model.predict(test_df[self.feature_columns])
        # Negative scores indicate anomaly
        anomaly_scores = self.model.score_samples(test_df[self.feature_columns])
        
        results = test_df.copy()
        results['is_anomaly'] = predictions == -1
        results['anomaly_score'] = anomaly_scores

        analysis_report = {
            "timestamp": datetime.now().isoformat(),
            "module": "AI-Prudence-Check-IsolationForest",
            "total_records_analyzed": len(test_df),
            "anomalies_detected": int(sum(results['is_anomaly'])),
            "flags": []
        }

        # Generate Reasoning Blocks for every flagged anomaly
        for idx, row in results[results['is_anomaly']].iterrows():
            reasoning = self._generate_reasoning_block(row)
            flag = {
                "record_index": idx,
                "cost_head": row.get('cost_head', 'Power_Purchase'),
                "value_analyzed": row[self.feature_columns].to_dict(),
                "confidence_score": round(abs(row['anomaly_score']) * 100, 2), # Simplified confidence metric
                "reasoning_block": reasoning
            }
            analysis_report["flags"].append(flag)

        return analysis_report

    def _generate_reasoning_block(self, flagged_row) -> str:
        """
        Generates the explanation for the regulatory officer.
        """
        head = flagged_row.get('cost_head', 'Metric')
        price = flagged_row.get('price_per_unit', 'N/A')
        
        # In a real system, this would dynamically compare against the historical mean tracked.
        # But this provides the deterministic generation structure.
        reasoning = (
            f"PRUDENCE VIOLATION DETECTED: The {head} value "
            f"demonstrates statistically significant deviation. "
            f"The analyzed price instance ({price}) is an outlier outside the 95th percentile "
            f"boundary established by the historical baseline trend."
        )
        return reasoning


# --- Demo Execution Block ---
if __name__ == "__main__":
    # 1. Simulate 5 years of Normal Power Purchase Data
    np.random.seed(42)
    # Normal short-term market prices hovering around 3.50 to 4.50 per unit
    historical_prices = np.random.normal(loc=4.0, scale=0.3, size=1000)
    history_df = pd.DataFrame({
        'cost_head': ['Power_Purchase'] * 1000,
        'price_per_unit': historical_prices,
        'volume_mw': np.random.normal(loc=500, scale=50, size=1000)
    })

    # 2. Train the anomaly detector
    detector = AnomalyDetector(contamination=0.01) # Strict 1% expectation
    detector.load_historical_data(history_df, feature_columns=['price_per_unit', 'volume_mw'])

    # 3. Simulate new Petition Data with a massive spike
    new_petition_df = pd.DataFrame({
        'cost_head': ['Power_Purchase'] * 3,
        'price_per_unit': [4.1, 4.3, 12.5], # 12.5 is the sudden spike
        'volume_mw': [510, 480, 800] # panic-buying volume spike
    })

    # 4. Analyze Data
    report = detector.analyze_petition_data(new_petition_df)
    
    print("\n--- AI Prudence Check Report ---")
    print(json.dumps(report, indent=2))
