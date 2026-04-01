"""
Tests for Decision Mode Classifier.
"""

import pytest
from backend.engine.decision_mode_classifier import (
    DecisionModeClassifier, DeviationInput, DecisionMode,
    DecisionType, ExternalFactorCategory, ExternalFactorDetector
)


class TestExternalFactorDetector:
    """Test external factor detection engine."""
    
    def test_detect_hydrology(self):
        detector = ExternalFactorDetector()
        text = "The monsoon was deficient this year, leading to reduced hydro generation."
        result = detector.detect(text, 100, 100)
        
        assert result.detected is True
        assert result.category == ExternalFactorCategory.HYDROLOGY
        assert result.confidence > 0.7
        assert "monsoon" in [e.lower() for e in result.evidence]
    
    def test_detect_power_purchase_volatility(self):
        detector = ExternalFactorDetector()
        text = "Due to fuel price escalation, short term power purchase costs increased significantly."
        result = detector.detect(text, 100, 100)
        
        assert result.detected is True
        assert result.category == ExternalFactorCategory.POWER_PURCHASE_VOLATILITY
    
    def test_detect_govt_mandate(self):
        detector = ExternalFactorDetector()
        text = "As per Government Order dated 15.03.2024, solar RPO targets were revised."
        result = detector.detect(text, 100, 100)
        
        assert result.detected is True
        assert result.category == ExternalFactorCategory.GOVT_MANDATE
    
    def test_detect_court_order(self):
        detector = ExternalFactorDetector()
        text = "The Hon'ble High Court directed the Commission to review the tariff order."
        result = detector.detect(text, 100, 100)
        
        assert result.detected is True
        assert result.category == ExternalFactorCategory.COURT_ORDER
    
    def test_detect_capex_overrun_numerical(self):
        detector = ExternalFactorDetector()
        # 35% overrun (>30% threshold)
        result = detector.detect("", 100, 135)
        
        assert result.detected is True
        assert result.category == ExternalFactorCategory.CAPEX_OVERRUN
        assert "35.0%" in result.evidence[0]
    
    def test_no_external_factor(self):
        detector = ExternalFactorDetector()
        result = detector.detect("Normal operations within approved limits.", 100, 100)
        
        assert result.detected is False
        assert result.category is None


class TestDecisionModeClassifier:
    """Test decision mode classification logic."""
    
    def test_ai_auto_low_variance(self):
        classifier = DecisionModeClassifier()
        
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=150,
            approved_value=145,
            actual_value=148,
            category="Controllable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert result.decision_mode == DecisionMode.AI_AUTO
        assert result.variance_exceeds_threshold is False
        assert result.low_confidence is False
    
    def test_pending_manual_high_variance(self):
        classifier = DecisionModeClassifier()
        
        # 30% variance (>25% threshold)
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=130,
            approved_value=100,
            actual_value=130,
            category="Controllable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert result.decision_mode == DecisionMode.PENDING_MANUAL
        assert result.variance_exceeds_threshold is True
    
    def test_pending_manual_low_confidence(self):
        classifier = DecisionModeClassifier()
        
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=150,
            approved_value=145,
            actual_value=148,
            category="Controllable",
            extraction_confidence=0.75  # <0.85 threshold
        )
        
        result = classifier.classify(input_data)
        
        assert result.decision_mode == DecisionMode.PENDING_MANUAL
        assert result.low_confidence is True
    
    def test_pending_manual_external_factor(self):
        classifier = DecisionModeClassifier()
        
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="Power_Purchase",
            petition_value=150,
            approved_value=145,
            actual_value=160,
            category="Uncontrollable",
            extraction_confidence=0.92,
            petition_text="Due to monsoon failure, power purchase costs escalated."
        )
        
        result = classifier.classify(input_data)
        
        assert result.decision_mode == DecisionMode.PENDING_MANUAL
        assert result.external_factor is not None
        assert result.external_factor.detected is True
    
    def test_ai_recommendation_gain(self):
        classifier = DecisionModeClassifier()
        
        # Approved > Actual = Gain
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=150,
            approved_value=150,
            actual_value=140,  # Actual < Approved = Gain
            category="Controllable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert result.ai_recommendation == DecisionType.APPROVE
    
    def test_ai_recommendation_loss(self):
        classifier = DecisionModeClassifier()
        
        # Actual > Approved = Loss (for controllable)
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=150,
            approved_value=150,
            actual_value=160,  # Actual > Approved = Loss
            category="Controllable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert result.ai_recommendation == DecisionType.DISALLOW
    
    def test_regulatory_clause_controllable_gain(self):
        classifier = DecisionModeClassifier()
        
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=150,
            approved_value=150,
            actual_value=140,
            category="Controllable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert "9.2" in result.regulatory_clause
        assert "Controllable Gains" in result.regulatory_clause
    
    def test_regulatory_clause_controllable_loss(self):
        classifier = DecisionModeClassifier()
        
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="O&M",
            petition_value=150,
            approved_value=150,
            actual_value=160,
            category="Controllable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert "9.3" in result.regulatory_clause
        assert "Controllable Loss" in result.regulatory_clause
    
    def test_regulatory_clause_uncontrollable(self):
        classifier = DecisionModeClassifier()
        
        input_data = DeviationInput(
            sbu_code="SBU-D",
            cost_head="Power_Purchase",
            petition_value=150,
            approved_value=150,
            actual_value=160,
            category="Uncontrollable",
            extraction_confidence=0.92
        )
        
        result = classifier.classify(input_data)
        
        assert "9.4" in result.regulatory_clause
        assert "Uncontrollable" in result.regulatory_clause
    
    def test_batch_classify(self):
        classifier = DecisionModeClassifier()
        
        inputs = [
            DeviationInput(sbu_code="SBU-D", cost_head="O&M", petition_value=100, approved_value=100, actual_value=95, category="Controllable", extraction_confidence=0.92),
            DeviationInput(sbu_code="SBU-D", cost_head="Power_Purchase", petition_value=100, approved_value=100, actual_value=130, category="Uncontrollable", extraction_confidence=0.92),
        ]
        
        results = classifier.batch_classify(inputs)
        
        assert len(results) == 2
        assert all(hasattr(r, 'decision_mode') for r in results)
    
    def test_summary_stats(self):
        classifier = DecisionModeClassifier()
        
        results = [
            classifier.classify(DeviationInput(sbu_code="SBU-D", cost_head="O&M", petition_value=100, approved_value=100, actual_value=95, category="Controllable", extraction_confidence=0.92)),
            classifier.classify(DeviationInput(sbu_code="SBU-D", cost_head="Power_Purchase", petition_value=130, approved_value=100, actual_value=130, category="Uncontrollable", extraction_confidence=0.92)),
        ]
        
        summary = classifier.get_summary(results)
        
        assert summary["total_items"] == 2
        assert "ai_auto_count" in summary
        assert "pending_manual_count" in summary
        assert "completion_percent" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
