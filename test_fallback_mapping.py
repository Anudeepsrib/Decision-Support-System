#!/usr/bin/env python3
"""Tests for deterministic SBU-D summary fallback mapping."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from canonical_registry import map_record_to_canonical


SBU_D_SUMMARY_TABLE = "SBU_D_ARR_SUMMARY | SBU_D | ARR, ERC and Revenue Gap claimed for SBU-D"


def _fallback_id(label: str) -> str:
    item = map_record_to_canonical(
        {
            "raw_label": label,
            "table_name": SBU_D_SUMMARY_TABLE,
            "raw_text": f"target_id=SBU_D_ARR_SUMMARY; chapter=SBU_D; row={label}",
        }
    )
    assert item is not None, label
    return item.canonical_id


def test_uses_sbu_d_generation_row_for_sbu_g_fallback():
    assert _fallback_id("Cost of Generation (SBU-G)") == "NET_ARR_GENERATION_TRANSFER_FALLBACK"
    assert _fallback_id("Cost of Internal Generation") == "NET_ARR_GENERATION_TRANSFER_FALLBACK"


def test_uses_sbu_d_transmission_row_for_sbu_t_fallback():
    assert _fallback_id("Cost of Intra-State Transmission (SBU-T)") == "NET_ARR_TRANSMISSION_TRANSFER_FALLBACK"
    assert _fallback_id("Intra-State Transmission charges") == "NET_ARR_TRANSMISSION_TRANSFER_FALLBACK"

