"""
Deterministic Rule Engine — KSERC MYT 2022-27.
Versioned, auditable, 100% reproducible.

This module is the "single source of truth" for all ARR Truing-Up computations.
Phase 2 AI modules feed data INTO this engine; they never bypass it.
"""

import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List
from backend.engine.constants import KSERC, KSERCConstants


@dataclass
class CostInput:
    """Structured input for a single ARR cost head."""
    head: str             # "O&M", "Power_Purchase", "Interest"
    category: str         # "Controllable" or "Uncontrollable"
    approved: float
    actual: float
    anomaly_score: Optional[float] = None   # Injected by Phase 2 AI Hook
    evidence_page: Optional[int] = None      # PDF provenance
    is_human_verified: bool = False


@dataclass
class RegulatoryRef:
    """Citation object linking computation to a specific regulatory clause."""
    clause: str
    description: str
    order_date: str
    regulation_version: str


@dataclass
class AuditResult:
    """Fully traceable output object for every computation."""
    timestamp: str
    scenario: str
    cost_head: str
    variance_category: str
    approved_amount: float
    actual_amount: float
    variance_amount: float
    disallowed_variance: float
    passed_through_variance: float
    logic_applied: str
    regulatory_reference: dict
    metadata: dict
    input_snapshot: dict

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


class RuleEngine:
    """
    Production-grade Deterministic Rule Engine.
    Versioned for 100% reproducibility under KSERC MYT 2022-27.
    """

    def __init__(self, constants: KSERCConstants = KSERC):
        self.constants = constants
        self.version = constants.VERSION

    # ─── Core: Gain/Loss Sharing ───

    def compute_variance(self, input_data: CostInput) -> AuditResult:
        """
        Apply the 30.06.2025 Order gain/loss sharing logic.
        Controllable Gains: 2/3 Utility, 1/3 Consumer.
        Controllable Losses: 100% borne by Utility (disallowed).
        Uncontrollable: 100% passed through to Consumer.
        """
        if not input_data.is_human_verified and input_data.actual is not None:
            raise ValueError(
                f"ZERO-HALLUCINATION VIOLATION: Actual value for {input_data.head} "
                f"has not been human-verified. Cannot proceed."
            )

        variance = input_data.approved - input_data.actual
        is_gain = variance >= 0

        if input_data.category == "Controllable":
            if is_gain:
                utility_impact = abs(variance) * self.constants.UTILITY_GAIN_SHARE
                consumer_impact = abs(variance) * self.constants.CONSUMER_GAIN_SHARE
                disallowed = 0.0
                passed_through = consumer_impact
                logic = (
                    f"Controllable Gain: Savings of {abs(variance):,.2f} shared "
                    f"2/3 ({utility_impact:,.2f}) to Utility, "
                    f"1/3 ({consumer_impact:,.2f}) to Consumer."
                )
                clause = "Regulation 9.2 — Controllable Gains Sharing"
            else:
                disallowed = abs(variance)
                passed_through = 0.0
                logic = (
                    f"Controllable Loss: Excess of {abs(variance):,.2f} fully "
                    f"disallowed (100% borne by Utility)."
                )
                clause = "Regulation 9.3 — Controllable Loss Disallowance"
        else:
            disallowed = 0.0
            passed_through = variance  # Negative = additional burden on consumer
            logic = (
                f"Uncontrollable Variance: {variance:,.2f} fully passed through "
                f"to Consumer (100% recovery)."
            )
            clause = "Regulation 9.4 — Uncontrollable Pass-Through"

        ref = RegulatoryRef(
            clause=clause,
            description=f"KSERC MYT Framework — {input_data.category} {input_data.head}",
            order_date=self.constants.ORDER_DATE,
            regulation_version=self.version
        )

        flags = []
        if input_data.anomaly_score and input_data.anomaly_score > 0.8:
            flags.append("HIGH_ANOMALY_FLAG")
        if not input_data.is_human_verified:
            flags.append("UNVERIFIED_DATA_WARNING")

        return AuditResult(
            timestamp=datetime.utcnow().isoformat(),
            scenario=f"{input_data.head} {'Gain' if is_gain else 'Loss'} Sharing",
            cost_head=input_data.head,
            variance_category=input_data.category,
            approved_amount=input_data.approved,
            actual_amount=input_data.actual,
            variance_amount=variance,
            disallowed_variance=disallowed,
            passed_through_variance=passed_through,
            logic_applied=logic,
            regulatory_reference=asdict(ref),
            metadata={
                "engine_version": self.version,
                "flags": flags,
            },
            input_snapshot=asdict(input_data)
        )

    # ─── O&M Normative Escalation ───

    def compute_om_escalation(
        self, base_om: float, cpi_index_change: float, wpi_index_change: float
    ) -> dict:
        """
        Computes the normative O&M escalation using actual CPI:WPI (70:30) indices.
        Formula: Escalated_O&M = Base × (1 + (CPI_wt × ΔCPI + WPI_wt × ΔWPI))
        """
        blended_escalation = (
            self.constants.CPI_WEIGHT * cpi_index_change +
            self.constants.WPI_WEIGHT * wpi_index_change
        )
        escalated_om = base_om * (1 + blended_escalation)

        return {
            "base_om": base_om,
            "cpi_change": cpi_index_change,
            "wpi_change": wpi_index_change,
            "blended_escalation_pct": round(blended_escalation * 100, 4),
            "escalated_om": round(escalated_om, 2),
            "formula": f"{base_om} × (1 + ({self.constants.CPI_WEIGHT}×{cpi_index_change} + {self.constants.WPI_WEIGHT}×{wpi_index_change}))",
            "regulatory_clause": "Regulation 5.1 — O&M Escalation (CPI:WPI 70:30)"
        }

    # ─── Interest Logic ───

    def compute_normative_interest(self, outstanding_loan: float) -> dict:
        """
        Computes normative interest on outstanding loans.
        Formula: Interest = Outstanding_Loan × (SBI_EBLR + 2%)
        """
        rate = self.constants.NORMATIVE_INTEREST_RATE
        interest = outstanding_loan * rate

        return {
            "outstanding_loan": outstanding_loan,
            "sbi_eblr": self.constants.SBI_EBLR,
            "spread": self.constants.INTEREST_SPREAD,
            "normative_rate": rate,
            "normative_interest": round(interest, 2),
            "formula": f"{outstanding_loan} × ({self.constants.SBI_EBLR} + {self.constants.INTEREST_SPREAD})",
            "regulatory_clause": "Regulation 6.3 — Normative Interest (SBI EBLR + 2%)"
        }

    # ─── Batch Processing ───

    def process_petition(self, inputs: List[CostInput]) -> dict:
        """
        Processes an entire petition (multiple cost heads) and returns
        a consolidated report with total Revenue Gap.
        """
        results = []
        total_gap = 0.0
        total_disallowed = 0.0

        for inp in inputs:
            result = self.compute_variance(inp)
            results.append(asdict(result))
            total_gap += result.variance_amount
            total_disallowed += result.disallowed_variance

        return {
            "engine_version": self.version,
            "timestamp": datetime.utcnow().isoformat(),
            "total_items_processed": len(inputs),
            "total_revenue_gap": round(total_gap, 2),
            "total_disallowed": round(total_disallowed, 2),
            "line_items": results
        }
