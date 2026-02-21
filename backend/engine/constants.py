"""
KSERC 2022-27 MYT Framework Regulatory Constants.
Hard-coded normative values for the Deterministic Rule Engine.
These constants are versioned and must match the Order under analysis.

FIX NOTE: @property is illegal on frozen dataclasses. T&D trajectory is now
a module-level constant. NORMATIVE_INTEREST_RATE is derived to prevent
silent staleness if SBI_EBLR is ever updated.
"""

from dataclasses import dataclass, field
from typing import Dict

# ─── T&D Loss Trajectory (module-level — cannot use @property in frozen dataclass) ───
# Reference: KSERC MYT 2022-27 Control Period Order — Progressive reduction trajectory
T_AND_D_LOSS_TRAJECTORY: Dict[str, float] = {
    "FY_2022-23": 0.155,  # 15.5% — Baseline year
    "FY_2023-24": 0.150,  # 15.0% — 0.5% reduction
    "FY_2024-25": 0.145,  # 14.5% — 0.5% reduction
    "FY_2025-26": 0.140,  # 14.0% — Target year (KPUPL Order OP 15/2025, Page 36)
    "FY_2026-27": 0.135,  # 13.5% — Final control period year
}


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
    INTEREST_SPREAD: float = 0.02       # +2% normative spread
    # NOTE: Derived at class level below to prevent silent staleness.
    # If SBI_EBLR changes, update only that field — rate auto-updates.
    # Python frozen dataclasses don't support @property; use __post_init__ workaround.

    # ─── Return on Equity ───
    ROE_RATE: float = 0.155             # 15.5% pre-tax

    # ─── Technical Loss Targets ───
    # Default cap for the current target year (FY_2025-26).
    T_AND_D_LOSS_TARGET: float = 0.140  # 14.0% normative cap
    AT_AND_C_LOSS_TARGET: float = 0.18  # 18% (Aggregate Technical & Commercial)

    # ─── Depreciation ───
    DEPRECIATION_METHOD: str = "Straight-Line"
    ASSET_LIFE_YEARS: int = 25

    # ─── Demand Growth ───
    GROWTH_PROJECTION: float = 0.05     # +5% annual growth projection

    # ─── Uncontrollable Pass-Through ───
    UNCONTROLLABLE_PASSTHROUGH: float = 1.0  # 100% to consumer

    @property
    def NORMATIVE_INTEREST_RATE(self) -> float:
        """
        Derived normative interest rate: SBI EBLR + spread.
        Always consistent with SBI_EBLR. Never hardcode this separately.
        Note: @property IS valid on frozen dataclasses (read-only is fine;
        only __set__ is blocked).
        """
        return round(self.SBI_EBLR + self.INTEREST_SPREAD, 6)

    def get_td_loss_target(self, financial_year: str) -> float:
        """
        Retrieves the T&D loss target for a specific financial year
        from the module-level T_AND_D_LOSS_TRAJECTORY lookup.

        Args:
            financial_year: e.g. "2024-25" or "FY_2024-25"

        Returns:
            Normative T&D loss target as a decimal (e.g., 0.145 for 14.5%)
        """
        if not financial_year.startswith("FY_"):
            financial_year = f"FY_{financial_year}"
        return T_AND_D_LOSS_TRAJECTORY.get(financial_year, self.T_AND_D_LOSS_TARGET)


# Singleton instance
KSERC = KSERCConstants()
