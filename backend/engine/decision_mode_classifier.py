"""
Decision Mode Classifier — KSERC Truing-Up AI Decision Support System.

This module implements the decision mode classification logic for the
Human-in-the-Loop system as per the master prompt requirements.

Logic:
- AI_AUTO: Variance < 25%, confidence >= 0.85, no external factors
- PENDING_MANUAL: Variance >= 25%, external factors detected, low confidence
- MANUAL_OVERRIDE: Officer explicitly overrides AI decision

DEMO MODE Behavior:
- Convert all PENDING_MANUAL → MANUAL_OVERRIDE
- Auto-fill justifications using AI draft

Pipeline Integration:
ingestion → extraction → comparison → rule_engine → decision_mode_classifier → reasoning → document_generator
"""

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import re

# Import demo mode settings
try:
    from backend.config.settings import is_demo_mode, get_demo_user
except ImportError:
    # Fallback if config not available
    def is_demo_mode() -> bool:
        return False
    def get_demo_user() -> dict:
        return {"id": "demo-admin", "username": "Demo Admin", "role": "admin"}


class DecisionMode(str, Enum):
    """Decision classification modes for AI + Human-in-the-Loop system."""
    AI_AUTO = "AI_AUTO"
    PENDING_MANUAL = "PENDING_MANUAL"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class ExternalFactorCategory(str, Enum):
    """External factor categories that trigger manual review."""
    HYDROLOGY = "Hydrology"
    POWER_PURCHASE_VOLATILITY = "Power_Purchase_Volatility"
    GOVT_MANDATE = "Government_Mandate"
    COURT_ORDER = "Court_Order"
    CAPEX_OVERRUN = "CapEx_Overrun"
    FORCE_MAJEURE = "Force_Majeure"
    OTHER = "Other"


class DecisionType(str, Enum):
    """Regulatory decision outcomes."""
    APPROVE = "APPROVE"
    PARTIAL = "PARTIAL"
    DISALLOW = "DISALLOW"


# ─── Configuration Constants ───

# Thresholds for auto-flagging (per master prompt)
VARIANCE_THRESHOLD_PERCENT = 25.0
CONFIDENCE_THRESHOLD = 0.85
CAPEX_OVERRUN_THRESHOLD_PERCENT = 30.0


# ─── Data Classes ───

@dataclass
class ExternalFactorDetection:
    """Result of external factor detection analysis."""
    detected: bool
    category: Optional[ExternalFactorCategory]
    confidence: float
    evidence: List[str]
    description: str


@dataclass
class DecisionModeResult:
    """Result of decision mode classification."""
    decision_mode: DecisionMode
    ai_recommendation: DecisionType
    confidence_score: float
    variance_percent: float
    external_factor: Optional[ExternalFactorDetection]
    
    # Auto-flagging reasons
    variance_exceeds_threshold: bool
    low_confidence: bool
    partial_decision: bool
    
    # Justification
    ai_justification: str
    regulatory_clause: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeviationInput:
    """Input data for decision mode classification."""
    sbu_code: str
    cost_head: str
    petition_value: float
    approved_value: float
    actual_value: Optional[float]
    category: str  # "Controllable" or "Uncontrollable"
    
    # Text context for external factor detection
    petition_text: Optional[str] = None
    order_text: Optional[str] = None
    
    # AI confidence from extraction
    extraction_confidence: float = 0.0


# ─── External Factor Detection Engine ───

class ExternalFactorDetector:
    """
    Detects external factors that require manual review per KSERC regulations.
    
    Categories:
    - Hydrology: Poor monsoon, drought, flood conditions
    - Power Purchase Volatility: Market price spikes, fuel shortages
    - Govt Mandate: Policy changes, subsidy adjustments
    - Court Order: Legal interventions
    - CapEx Overrun: >30% deviation from approved capital expenditure
    - Force Majeure: Natural disasters, pandemics
    """
    
    # Keyword patterns for each category
    PATTERNS = {
        ExternalFactorCategory.HYDROLOGY: [
            r'(?i)(monsoon|drought|flood|rainfall|hydrology|water shortage|reservoir level)',
            r'(?i)(deficient rainfall|excess rainfall|climate variation)',
        ],
        ExternalFactorCategory.POWER_PURCHASE_VOLATILITY: [
            r'(?i)(power purchase|fuel price|coal price|gas price|market volatility)',
            r'(?i)(short term power purchase|bilateral|exchange|IEX|PXIL)',
            r'(?i)(fuel shortage|coal shortage|generation shortage)',
        ],
        ExternalFactorCategory.GOVT_MANDATE: [
            r'(?i)(government order|GO|ministry|MNRE|CEA|central government)',
            r'(?i)(subsidy|DBT|direct benefit transfer|policy change|notification)',
            r'(?i)(solar obligation|RPO|renewable purchase obligation)',
        ],
        ExternalFactorCategory.COURT_ORDER: [
            r'(?i)(court order|hon.*ble court|supreme court|high court|tribunal)',
            r'(?i)(APTEL|CEGRAT|judgment|direction|contempt)',
        ],
        ExternalFactorCategory.CAPEX_OVERRUN: [
            r'(?i)(capex overrun|capital expenditure|project delay|cost escalation)',
            r'(?i)(transmission line|substation|infrastructure|augmentation)',
        ],
        ExternalFactorCategory.FORCE_MAJEURE: [
            r'(?i)(force majeure|pandemic|covid|natural disaster|earthquake|cyclone)',
            r'(?i)(lockdown|curfew|emergency|war|riot|civil disturbance)',
        ],
    }
    
    def detect(self, text: Optional[str], 
               petition_value: float, 
               approved_value: float,
               actual_value: Optional[float] = None) -> ExternalFactorDetection:
        """
        Detect external factors from text context and numerical deviations.
        
        Args:
            text: Petition or order text for keyword analysis
            petition_value: Claimed value from petition
            approved_value: Approved value from KSERC order
            actual_value: Actual audited value (if available)
            
        Returns:
            ExternalFactorDetection with category and confidence
        """
        evidence = []
        detected_categories = []
        
        # Text-based detection
        if text:
            for category, patterns in self.PATTERNS.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    if matches:
                        detected_categories.append(category)
                        evidence.extend(matches[:3])  # Limit evidence
                        break
        
        # CapEx overrun detection (numerical)
        if actual_value and approved_value > 0:
            overrun_pct = abs((actual_value - approved_value) / approved_value) * 100
            if overrun_pct > CAPEX_OVERRUN_THRESHOLD_PERCENT:
                detected_categories.append(ExternalFactorCategory.CAPEX_OVERRUN)
                evidence.append(f"CapEx overrun: {overrun_pct:.1f}% (threshold: {CAPEX_OVERRUN_THRESHOLD_PERCENT}%)")
        
        # Determine primary category and confidence
        if detected_categories:
            primary = detected_categories[0]
            confidence = min(0.95, 0.7 + (0.05 * len(evidence)))
            description = f"External factor detected: {primary.value}. Evidence: {', '.join(evidence[:2])}"
            return ExternalFactorDetection(
                detected=True,
                category=primary,
                confidence=confidence,
                evidence=list(set(evidence)),  # Deduplicate
                description=description
            )
        
        return ExternalFactorDetection(
            detected=False,
            category=None,
            confidence=0.0,
            evidence=[],
            description="No external factors detected"
        )


# ─── Decision Mode Classifier ───

class DecisionModeClassifier:
    """
    Classifies each line item into AI_AUTO, PENDING_MANUAL, or MANUAL_OVERRIDE.
    
    Per master prompt:
    Mark as PENDING_MANUAL if:
    - Variance > 25%
    - External factors detected
    - Low confidence (< 0.85)
    - Partial decisions
    """
    
    def __init__(self):
        self.external_factor_detector = ExternalFactorDetector()
    
    def classify(self, input_data: DeviationInput) -> DecisionModeResult:
        """
        Classify a deviation into appropriate decision mode.
        
        DEMO MODE: Converts PENDING_MANUAL → MANUAL_OVERRIDE with auto-filled justification.
        
        Args:
            input_data: DeviationInput with petition, approved, actual values
            
        Returns:
            DecisionModeResult with classification and justification
        """
        # Calculate variance
        if input_data.approved_value != 0:
            variance_pct = abs((input_data.petition_value - input_data.approved_value) 
                             / input_data.approved_value) * 100
        else:
            variance_pct = 0.0
        
        # Detect external factors
        text_to_analyze = " ".join(filter(None, [input_data.petition_text, input_data.order_text]))
        external_factor = self.external_factor_detector.detect(
            text_to_analyze,
            input_data.petition_value,
            input_data.approved_value,
            input_data.actual_value
        )
        
        # Determine AI recommendation based on variance
        if input_data.actual_value is not None:
            actual_variance = input_data.approved_value - input_data.actual_value
            if actual_variance > 0:
                ai_recommendation = DecisionType.APPROVE  # Gain
            elif actual_variance < 0:
                ai_recommendation = DecisionType.DISALLOW  # Loss
            else:
                ai_recommendation = DecisionType.APPROVE
        else:
            # No actuals yet, compare petition vs approved
            petition_variance = input_data.petition_value - input_data.approved_value
            if petition_variance > 0:
                ai_recommendation = DecisionType.PARTIAL  # Partial approval
            else:
                ai_recommendation = DecisionType.APPROVE
        
        # Auto-flagging conditions
        variance_exceeds = variance_pct > VARIANCE_THRESHOLD_PERCENT
        low_confidence = input_data.extraction_confidence < CONFIDENCE_THRESHOLD
        partial_decision = ai_recommendation == DecisionType.PARTIAL
        
        # Decision mode classification
        if variance_exceeds or external_factor.detected or low_confidence or partial_decision:
            decision_mode = DecisionMode.PENDING_MANUAL
        else:
            decision_mode = DecisionMode.AI_AUTO
        
        # DEMO MODE OVERRIDE: Convert PENDING_MANUAL → MANUAL_OVERRIDE
        demo_justification = None
        if is_demo_mode() and decision_mode == DecisionMode.PENDING_MANUAL:
            decision_mode = DecisionMode.MANUAL_OVERRIDE
            # Generate demo justification
            demo_justification = self._generate_demo_justification(
                input_data, ai_recommendation, external_factor, variance_pct
            )
        
        # Confidence score calculation
        base_confidence = input_data.extraction_confidence
        if variance_exceeds:
            base_confidence *= 0.8
        if external_factor.detected:
            base_confidence *= 0.85
        
        # Generate AI justification
        ai_justification = demo_justification or self._generate_justification(
            input_data, ai_recommendation, external_factor, variance_pct
        )
        
        # Regulatory clause reference
        regulatory_clause = self._get_regulatory_clause(
            input_data.category, ai_recommendation
        )
        
        return DecisionModeResult(
            decision_mode=decision_mode,
            ai_recommendation=ai_recommendation,
            confidence_score=round(base_confidence, 4),
            variance_percent=round(variance_pct, 2),
            external_factor=external_factor if external_factor.detected else None,
            variance_exceeds_threshold=variance_exceeds,
            low_confidence=low_confidence,
            partial_decision=partial_decision,
            ai_justification=ai_justification,
            regulatory_clause=regulatory_clause
        )
    
    def _generate_justification(self, 
                               input_data: DeviationInput,
                               recommendation: DecisionType,
                               external_factor: ExternalFactorDetection,
                               variance_pct: float) -> str:
        """Generate AI draft justification without fabricated numbers."""
        parts = []
        
        # Variance description
        if input_data.actual_value:
            parts.append(
                f"Approved {input_data.cost_head}: ₹{input_data.approved_value:,.2f} "
                f"vs Actual: ₹{input_data.actual_value:,.2f}"
            )
        else:
            parts.append(
                f"Petition claimed {input_data.cost_head}: ₹{input_data.petition_value:,.2f} "
                f"vs Approved: ₹{input_data.approved_value:,.2f}"
            )
        
        # Decision reasoning
        if recommendation == DecisionType.APPROVE:
            parts.append("AI recommends FULL APPROVAL based on variance within acceptable limits.")
        elif recommendation == DecisionType.PARTIAL:
            parts.append("AI recommends PARTIAL APPROVAL pending officer review of variance.")
        else:
            parts.append("AI recommends DISALLOWANCE per Regulation 9.3 for controllable losses.")
        
        # External factor mention
        if external_factor.detected:
            parts.append(
                f"External factor detected: {external_factor.category.value}. "
                "Manual review recommended."
            )
        
        return " ".join(parts)
    
    def _generate_demo_justification(self,
                                      input_data: DeviationInput,
                                      recommendation: DecisionType,
                                      external_factor: ExternalFactorDetection,
                                      variance_pct: float) -> str:
        """
        Generate demo mode justification with auto-filled content.
        Marks justification as "Auto-generated in Demo Mode".
        """
        base_justification = self._generate_justification(
            input_data, recommendation, external_factor, variance_pct
        )
        
        demo_note = "[AUTO-GENERATED IN DEMO MODE] "
        
        # Add officer override reasoning for demo
        if recommendation == DecisionType.PARTIAL:
            override_reason = (
                "Upon review, the variance warrants partial consideration. "
                "Approved value adjusted based on documented evidence. "
            )
        elif recommendation == DecisionType.DISALLOW:
            override_reason = (
                "Per Regulation 9.3, controllable losses are disallowed. "
                "Utility failed to demonstrate cost efficiency measures. "
            )
        else:
            override_reason = (
                "Full approval granted. Costs verified within approved parameters. "
            )
        
        return f"{demo_note}{base_justification} {override_reason}"
    
    def _get_regulatory_clause(self, category: str, recommendation: DecisionType) -> str:
        """Get applicable regulatory clause reference."""
        if category == "Controllable":
            if recommendation == DecisionType.APPROVE:
                return "Regulation 9.2 — Controllable Gains Sharing (2/3 Utility, 1/3 Consumer)"
            else:
                return "Regulation 9.3 — Controllable Loss Disallowance (100% Utility borne)"
        else:
            return "Regulation 9.4 — Uncontrollable Pass-Through (100% Consumer recovery)"
    
    def batch_classify(self, inputs: List[DeviationInput]) -> List[DecisionModeResult]:
        """Classify multiple deviations in batch."""
        return [self.classify(inp) for inp in inputs]
    
    def get_summary(self, results: List[DecisionModeResult]) -> Dict[str, Any]:
        """Get summary statistics for a batch of classifications."""
        total = len(results)
        ai_auto = sum(1 for r in results if r.decision_mode == DecisionMode.AI_AUTO)
        pending_manual = sum(1 for r in results if r.decision_mode == DecisionMode.PENDING_MANUAL)
        
        external_factors = sum(
            1 for r in results 
            if r.external_factor and r.external_factor.detected
        )
        
        return {
            "total_items": total,
            "ai_auto_count": ai_auto,
            "pending_manual_count": pending_manual,
            "manual_override_count": 0,  # Will be updated after officer decisions
            "external_factors_detected": external_factors,
            "high_variance_count": sum(1 for r in results if r.variance_exceeds_threshold),
            "low_confidence_count": sum(1 for r in results if r.low_confidence),
            "completion_percent": round((ai_auto / total * 100), 1) if total > 0 else 0,
            "requires_manual_review": pending_manual > 0
        }


# ─── Singleton Instance ───
_classifier = None

def get_classifier() -> DecisionModeClassifier:
    """Get or create singleton classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = DecisionModeClassifier()
    return _classifier


# ─── Convenience Functions ───

def classify_deviation(input_data: DeviationInput) -> DecisionModeResult:
    """Convenience function to classify a single deviation."""
    return get_classifier().classify(input_data)


def batch_classify_deviations(inputs: List[DeviationInput]) -> List[DecisionModeResult]:
    """Convenience function to classify multiple deviations."""
    return get_classifier().batch_classify(inputs)
