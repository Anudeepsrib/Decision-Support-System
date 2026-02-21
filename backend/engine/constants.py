"""
KSERC 2022-27 MYT Framework Regulatory Constants.
Hard-coded normative values for the Deterministic Rule Engine.
These constants are versioned and must match the Order under analysis.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class KSERCConstants:
    """Immutable regulatory constants for the KSERC MYT 2022-27 control period."""

    # Rule Version Identifier
    VERSION: str = "KSERC-MYT-2022-27-v1.0"
    ORDER_DATE: str = "30.06.2025"

    # ─── O&M Escalation ───
    CPI_WEIGHT: float = 0.70
    WPI_WEIGHT: float = 0.30

    # ─── Gain/Loss Sharing (Controllable Efficiencies) ───
    UTILITY_GAIN_SHARE: float = 2 / 3   # ~66.67%
    CONSUMER_GAIN_SHARE: float = 1 / 3  # ~33.33%
    UTILITY_LOSS_SHARE: float = 1.0     # 100% loss borne by utility
    CONSUMER_LOSS_SHARE: float = 0.0

    # ─── Interest & Finance ───
    SBI_EBLR: float = 0.0850            # SBI External Benchmark Lending Rate (8.50%)
    INTEREST_SPREAD: float = 0.02        # +2% normative spread
    NORMATIVE_INTEREST_RATE: float = 0.1050  # SBI EBLR + 2%

    # ─── Return on Equity ───
    ROE_RATE: float = 0.155              # 15.5% pre-tax

    # ─── Technical Loss Targets ───
    T_AND_D_LOSS_TARGET: float = 0.14    # 14% normative cap
    AT_AND_C_LOSS_TARGET: float = 0.18   # 18% (Aggregate Technical & Commercial)

    # ─── Depreciation ───
    DEPRECIATION_METHOD: str = "Straight-Line"
    ASSET_LIFE_YEARS: int = 25

    # ─── Demand Growth ───
    GROWTH_PROJECTION: float = 0.05      # +5% annual growth projection

    # ─── Uncontrollable Pass-Through ───
    UNCONTROLLABLE_PASSTHROUGH: float = 1.0  # 100% to consumer


# Singleton instance
KSERC = KSERCConstants()
