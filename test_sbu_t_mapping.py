#!/usr/bin/env python3
"""Tests for SBU-T deterministic canonical mapping."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from canonical_registry import map_record_to_canonical


SBU_T_TABLE = "SBU_T_TRANSFER_COST | SBU_T | Summary of ARR and ERC claimed for SBU-T"


def _canonical_id(label: str) -> str:
    item = map_record_to_canonical(
        {
            "raw_label": label,
            "table_name": SBU_T_TABLE,
            "raw_text": f"chapter=SBU_T row={label}",
        }
    )
    assert item is not None, label
    return item.canonical_id


def test_maps_sbu_t_core_financial_heads():
    assert _canonical_id("O&M expenses") == "OM_EXPENSES_TRANSMISSION"
    assert _canonical_id("Interest and Finance Charges") == "INTEREST_FINANCE_TRANSMISSION"
    assert _canonical_id("Depreciation") == "DEPRECIATION_TRANSMISSION"
    assert _canonical_id("Return on Equity") == "ROE_TRANSMISSION"
    assert _canonical_id("Net ARR / Transmission charges") == "NET_ARR_TRANSMISSION"

