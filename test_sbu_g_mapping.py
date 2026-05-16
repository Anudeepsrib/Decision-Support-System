#!/usr/bin/env python3
"""Tests for SBU-G deterministic canonical mapping."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from canonical_registry import map_record_to_canonical


SBU_G_TABLE = "SBU_G_TRANSFER_COST | SBU_G | Approved Transfer Cost of SBU-G"


def _canonical_id(label: str) -> str:
    item = map_record_to_canonical(
        {
            "raw_label": label,
            "table_name": SBU_G_TABLE,
            "raw_text": f"chapter=SBU_G row={label}",
        }
    )
    assert item is not None, label
    return item.canonical_id


def test_maps_sbu_g_core_financial_heads():
    assert _canonical_id("Cost of Generation of Power") == "COST_OF_GENERATION"
    assert _canonical_id("O&M expenses") == "OM_EXPENSES_GENERATION"
    assert _canonical_id("Interest & Finance Charges") == "INTEREST_FINANCE_GENERATION"
    assert _canonical_id("Depreciation") == "DEPRECIATION_GENERATION"
    assert _canonical_id("RoE") == "ROE_GENERATION"
    assert _canonical_id("Less Non-Tariff Income") == "NON_TARIFF_INCOME_GENERATION"
    assert _canonical_id("Net ARR / Transfer Cost to SBU-D") == "NET_ARR_GENERATION"

