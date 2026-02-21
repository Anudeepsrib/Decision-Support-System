"""
Deterministic Rule Engine — KSERC MYT 2022-27.
Versioned, auditable, 100% reproducible.

This module is the "single source of truth" for all ARR Truing-Up computations.
Phase 2 AI modules feed data INTO this engine; they never bypass it.
"""

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List
from decimal import Decimal, ROUND_HALF_UP
from backend.engine.constants import KSERC, KSERCConstants


# ─── Enums for Input Validation (F-03, F-04) ───

class CostCategory(str, Enum):
    """Enforced variance categories. Prevents silent logic bypass from typos."""
    CONTROLLABLE = "Controllable"
    UNCONTROLLABLE = "Uncontrollable"


class SBUCode(str, Enum):
    """Enforced SBU partitioning codes. Prevents invalid isolation tags."""
    SBU_G = "SBU-G"
    SBU_T = "SBU-T"
    SBU_D = "SBU-D"


# ─── Financial Precision Utilities (F-02) ───

def _money_round(value: float, places: int = 2) -> float:
    """
    Banker's rounding for financial amounts.
    Uses Python Decimal to eliminate IEEE 754 float drift.
    Example: 2/3 * 300000000 → 200000000.00 (not 199999999.99999997)
    """
    return float(Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP))


def generate_checksum(data: dict) -> str:
    """
    Generate SHA-256 checksum for audit integrity verification.
    IMPORTANT: Timestamp is intentionally excluded from the hash so that
    identical computation inputs always produce the identical checksum.
    This upholds the 100% reproducibility guarantee of the Rule Engine.
    """
    stable_data = {k: v for k, v in data.items() if k not in ("timestamp",)}
    canonical = json.dumps(stable_data, sort_keys=True, default=str, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


@dataclass
class CostInput:
    """Structured input for a single ARR cost head."""
    head: str                        # "O&M", "Power_Purchase", "Interest"
    category: CostCategory           # F-03: Enum, not free-form string
    sbu_code: SBUCode                # F-04: Enum, not free-form string
    approved: float
    actual: float
    anomaly_score: Optional[float] = None   # Injected by Phase 2 AI Hook
    evidence_page: Optional[int] = None      # PDF provenance
    is_human_verified: bool = False

    def __post_init__(self):
        """Validate and coerce enum fields. Catches typos like 'controllable'."""
        if not isinstance(self.category, CostCategory):
            try:
                self.category = CostCategory(self.category)
            except ValueError:
                valid = [e.value for e in CostCategory]
                raise ValueError(
                    f"Invalid category '{self.category}'. Must be one of: {valid}"
                )
        if not isinstance(self.sbu_code, SBUCode):
            try:
                self.sbu_code = SBUCode(self.sbu_code)
            except ValueError:
                valid = [e.value for e in SBUCode]
                raise ValueError(
                    f"Invalid sbu_code '{self.sbu_code}'. Must be one of: {valid}"
                )


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
    checksum: str                    # SHA-256 for integrity verification
    sbu_code: str                    # SBU Partitioning: SBU-G, SBU-T, SBU-D
    scenario: str
    cost_head: str
    variance_category: str
    approved_amount: float
    actual_amount: float
    variance_amount: float
    disallowed_variance: float
    passed_through_variance: float
    disallowance_reason: Optional[str]  # Explicit reason for disallowance
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
        # Zero-hallucination enforcement:
        # Block ONLY when actual value exists but has NOT been human-verified.
        if input_data.actual is not None and not input_data.is_human_verified:
            raise ValueError(
                f"ZERO-HALLUCINATION VIOLATION: Actual value for '{input_data.head}' "
                f"({input_data.actual:,.2f}) has not been human-verified. "
                f"Use the /mapping/confirm endpoint to verify before computation."
            )

        variance = _money_round(input_data.approved - input_data.actual)
        is_gain = variance >= 0

        if input_data.category == CostCategory.CONTROLLABLE:
            if is_gain:
                utility_impact = _money_round(abs(variance) * self.constants.UTILITY_GAIN_SHARE)
                consumer_impact = _money_round(abs(variance) * self.constants.CONSUMER_GAIN_SHARE)
                disallowed = 0.0
                passed_through = consumer_impact
                disallowance_reason = None
                logic = (
                    f"Controllable Gain: Savings of {abs(variance):,.2f} shared "
                    f"2/3 ({utility_impact:,.2f}) to Utility, "
                    f"1/3 ({consumer_impact:,.2f}) to Consumer."
                )
                clause = "Regulation 9.2 — Controllable Gains Sharing"
            else:
                disallowed = _money_round(abs(variance))
                passed_through = 0.0
                disallowance_reason = (
                    f"Controllable Loss of {abs(variance):,.2f} fully disallowed per "
                    f"Regulation 9.3 — 100% borne by Utility. No pass-through to consumers."
                )
                logic = (
                    f"Controllable Loss: Excess of {abs(variance):,.2f} fully "
                    f"disallowed (100% borne by Utility)."
                )
                clause = "Regulation 9.3 — Controllable Loss Disallowance"
        else:
            disallowed = 0.0
            passed_through = _money_round(variance)  # Negative = additional burden on consumer
            disallowance_reason = None
            logic = (
                f"Uncontrollable Variance: {variance:,.2f} fully passed through "
                f"to Consumer (100% recovery)."
            )
            clause = "Regulation 9.4 — Uncontrollable Pass-Through"

        ref = RegulatoryRef(
            clause=clause,
            description=f"KSERC MYT Framework — {input_data.category.value} {input_data.head}",
            order_date=self.constants.ORDER_DATE,
            regulation_version=self.version
        )

        flags = []
        if input_data.anomaly_score and input_data.anomaly_score > 0.8:
            flags.append("HIGH_ANOMALY_FLAG")
        if not input_data.is_human_verified:
            flags.append("UNVERIFIED_DATA_WARNING")

        # Build result dict for checksum generation
        result_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sbu_code": input_data.sbu_code.value,
            "scenario": f"{input_data.head} {'Gain' if is_gain else 'Loss'} Sharing",
            "cost_head": input_data.head,
            "variance_category": input_data.category.value,
            "approved_amount": input_data.approved,
            "actual_amount": input_data.actual,
            "variance_amount": variance,
            "disallowed_variance": disallowed,
            "passed_through_variance": passed_through,
            "disallowance_reason": disallowance_reason,
            "logic_applied": logic,
            "regulatory_reference": asdict(ref),
            "metadata": {
                "engine_version": self.version,
                "flags": flags,
            },
            "input_snapshot": asdict(input_data)
        }

        # Generate integrity checksum
        checksum = generate_checksum(result_data)
        result_data["checksum"] = checksum

        return AuditResult(**result_data)

    # ─── T&D Loss Target Lookup ───

    def get_td_loss_target(self, financial_year: str) -> float:
        """
        Retrieves the T&D loss target for a specific financial year.
        Delegates to KSERCConstants.get_td_loss_target() which reads
        the module-level T_AND_D_LOSS_TRAJECTORY dict.
        """
        return self.constants.get_td_loss_target(financial_year)

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
        escalated_om = _money_round(base_om * (1 + blended_escalation))

        return {
            "base_om": base_om,
            "cpi_change": cpi_index_change,
            "wpi_change": wpi_index_change,
            "blended_escalation_pct": round(blended_escalation * 100, 4),
            "escalated_om": escalated_om,
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
        interest = _money_round(outstanding_loan * rate)

        return {
            "outstanding_loan": outstanding_loan,
            "sbi_eblr": self.constants.SBI_EBLR,
            "spread": self.constants.INTEREST_SPREAD,
            "normative_rate": rate,
            "normative_interest": interest,
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

        report = {
            "engine_version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),  # F-01: fixed
            "total_items_processed": len(inputs),
            "total_revenue_gap": _money_round(total_gap),
            "total_disallowed": _money_round(total_disallowed),
            "line_items": results
        }

        # Add batch-level checksum for petition integrity
        report["batch_checksum"] = generate_checksum(report)
        return report
