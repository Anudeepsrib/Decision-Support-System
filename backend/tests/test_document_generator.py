"""
Tests for KSERC Order Document Generator.
"""

import pytest
from datetime import datetime, timezone
from backend.engine.document_generator import (
    KSERCOrderGenerator, OrderMetadata, DecisionItem,
    DecisionMode, DecisionType, GeneratedOrder
)


class TestOrderGenerator:
    """Test KSERC-compliant order generation."""
    
    def test_generate_basic_order(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-001",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024"
        )
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=1480000000,
                final_value=1480000000,
                ai_recommendation=DecisionType.APPROVE, ai_value=0.0, officer_value=None,
                officer_decision=None,
                decision_mode=DecisionMode.AI_AUTO,
                ai_justification="Variance within limits",
                officer_justification=None,
                regulatory_clause="Regulation 9.2",
                external_factor_category=None,
                decision_marker="[A]"
            )
        ]
        
        result = generator.generate(metadata, decisions)
        
        assert isinstance(result, GeneratedOrder)
        assert result.order_id == "TU-2024-25-SBU-D-001"
        assert "KSERC" in result.html_content
        assert "Truing-Up" in result.html_content
    
    def test_draft_watermark_with_pending(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-002",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024"
        )
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=None,
                final_value=0,
                ai_recommendation=DecisionType.PARTIAL, ai_value=0.0, officer_value=None,
                officer_decision=None,
                decision_mode=DecisionMode.PENDING_MANUAL,
                ai_justification="High variance detected",
                officer_justification=None,
                regulatory_clause="Regulation 9.1",
                external_factor_category=None,
                decision_marker="[P]"
            )
        ]
        
        result = generator.generate(metadata, decisions)
        
        assert result.is_draft is True
        assert result.has_pending is True
        assert result.can_finalize is False
        assert "DRAFT" in result.html_content
        assert "watermark" in result.html_content.lower() or "draft" in result.html_content.lower()
    
    def test_manual_override_justification_block(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-003",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024",
            is_draft=False
        )
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=1480000000,
                final_value=1460000000,
                ai_recommendation=DecisionType.APPROVE, ai_value=0.0, officer_value=None,
                officer_decision=DecisionType.PARTIAL,
                decision_mode=DecisionMode.MANUAL_OVERRIDE,
                ai_justification="AI recommended approval",
                officer_justification="Officer reviewed and approved partial amount due to exceptional circumstances.",
                regulatory_clause="Regulation 9.1",
                external_factor_category="CapEx_Overrun",
                decision_marker="[M]"
            )
        ]
        
        result = generator.generate(metadata, decisions)
        
        assert result.is_draft is False
        assert "Commission’s Analysis and Justification:" in result.html_content
        assert "Officer reviewed and approved partial" in result.html_content
        assert "CapEx_Overrun" in result.html_content
    
    def test_validate_can_finalize_pass(self):
        generator = KSERCOrderGenerator()
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=1480000000,
                final_value=1480000000,
                ai_recommendation=DecisionType.APPROVE, ai_value=0.0, officer_value=None,
                officer_decision=None,
                decision_mode=DecisionMode.AI_AUTO,
                ai_justification="Variance within limits",
                officer_justification=None,
                regulatory_clause="Regulation 9.2",
                external_factor_category=None,
                decision_marker="[A]"
            )
        ]
        
        can_finalize, issues = generator.validate_order_can_finalize(decisions)
        
        assert can_finalize is True
        assert len(issues) == 0
    
    def test_validate_can_finalize_fail_pending(self):
        generator = KSERCOrderGenerator()
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=None,
                final_value=0,
                ai_recommendation=DecisionType.PARTIAL, ai_value=0.0, officer_value=None,
                officer_decision=None,
                decision_mode=DecisionMode.PENDING_MANUAL,
                ai_justification="High variance",
                officer_justification=None,
                regulatory_clause="Regulation 9.1",
                external_factor_category=None,
                decision_marker="[P]"
            )
        ]
        
        can_finalize, issues = generator.validate_order_can_finalize(decisions)
        
        assert can_finalize is False
        assert len(issues) == 1
        assert "pending" in issues[0].lower()
    
    def test_validate_can_finalize_fail_missing_justification(self):
        generator = KSERCOrderGenerator()
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=1480000000,
                final_value=1460000000,
                ai_recommendation=DecisionType.APPROVE, ai_value=0.0, officer_value=None,
                officer_decision=DecisionType.PARTIAL,
                decision_mode=DecisionMode.MANUAL_OVERRIDE,
                ai_justification="AI recommended approval",
                officer_justification=None,  # Missing!
                regulatory_clause="Regulation 9.1",
                external_factor_category=None,
                decision_marker="[M]"
            )
        ]
        
        can_finalize, issues = generator.validate_order_can_finalize(decisions)
        
        assert can_finalize is False
        assert len(issues) == 1
        assert "justification" in issues[0].lower()
    
    def test_all_sections_present(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-004",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024"
        )
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=1480000000,
                final_value=1480000000,
                ai_recommendation=DecisionType.APPROVE, ai_value=0.0, officer_value=None,
                officer_decision=None,
                decision_mode=DecisionMode.AI_AUTO,
                ai_justification="Within limits",
                officer_justification=None,
                regulatory_clause="Regulation 9.2",
                external_factor_category=None,
                decision_marker="[A]"
            )
        ]
        
        result = generator.generate(metadata, decisions)
        html = result.html_content
        
        # Check all 8 sections are present
        assert "1. INTRODUCTION" in html or "INTRODUCTION" in html
        assert "2. REGULATORY FRAMEWORK" in html or "REGULATORY" in html
        assert "3. PETITION SUMMARY" in html or "PETITION" in html
        assert "4. SBU-WISE ANALYSIS" in html or "SBU-WISE" in html
        assert "5. DEVIATIONS & FINDINGS" in html or "DEVIATIONS" in html
        assert "6. COMMISSION DECISIONS" in html or "COMMISSION DECISIONS" in html
        assert "7. FINAL ORDER" in html or "FINAL ORDER" in html
        assert "8. APPENDIX" in html or "APPENDIX" in html
    
    def test_decision_markers(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-005",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024"
        )
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="O&M",
                financial_year="2024-25",
                petition_value=1500000000,
                approved_value=1450000000,
                actual_value=1480000000,
                final_value=1480000000,
                ai_recommendation=DecisionType.APPROVE, ai_value=0.0, officer_value=None,
                officer_decision=None,
                decision_mode=DecisionMode.AI_AUTO,
                ai_justification="Within limits",
                officer_justification=None,
                regulatory_clause="Regulation 9.2",
                external_factor_category=None,
                decision_marker="[A]"
            ),
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="Power_Purchase",
                financial_year="2024-25",
                petition_value=4500000000,
                approved_value=4200000000,
                actual_value=4800000000,
                final_value=4500000000,
                ai_recommendation=DecisionType.PARTIAL, ai_value=0.0, officer_value=None,
                officer_decision=DecisionType.PARTIAL,
                decision_mode=DecisionMode.MANUAL_OVERRIDE,
                ai_justification="High variance",
                officer_justification="Partial approval due to external factors",
                regulatory_clause="Regulation 9.4",
                external_factor_category="Power_Purchase_Volatility",
                decision_marker="[M]"
            )
        ]
        
        result = generator.generate(metadata, decisions)
        html = result.html_content
        
        assert "[A]" in html
        assert "[M]" in html
    
    def test_external_factor_in_appendix(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-006",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024"
        )
        
        decisions = [
            DecisionItem(
                sbu_code="SBU-D",
                cost_head="Power_Purchase",
                financial_year="2024-25",
                petition_value=4500000000,
                approved_value=4200000000,
                actual_value=4800000000,
                final_value=4500000000,
                ai_recommendation=DecisionType.PARTIAL, ai_value=0.0, officer_value=None,
                officer_decision=DecisionType.PARTIAL,
                decision_mode=DecisionMode.MANUAL_OVERRIDE,
                ai_justification="High variance detected",
                officer_justification="Approved partial amount due to power purchase volatility",
                regulatory_clause="Regulation 9.4",
                external_factor_category="Power_Purchase_Volatility",
                decision_marker="[M]"
            )
        ]
        
        result = generator.generate(metadata, decisions)
        html = result.html_content
        
        assert "Power_Purchase_Volatility" in html or "Power Purchase Volatility" in html
    
    def test_compliance_references(self):
        generator = KSERCOrderGenerator()
        
        metadata = OrderMetadata(
            order_id="TU-2024-25-SBU-D-007",
            financial_year="2024-25",
            sbu_code="SBU-D",
            order_date="31.03.2024"
        )
        
        decisions = []
        
        result = generator.generate(metadata, decisions)
        html = result.html_content
        
        # Check Electricity Act references
        assert "Section 61" in html or "Electricity Act" in html
        assert "Section 62" in html or "Electricity Act" in html
        
        # Check KSERC regulations
        assert "KSERC" in html
        assert "MYT" in html or "Multi-Year Tariff" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
