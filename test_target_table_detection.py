#!/usr/bin/env python3
"""Tests for deterministic chapter and target-table detection."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from extractor import detect_chapter_ranges_from_text, _extract_rows_from_target_table
from table_targets import TARGETS_BY_ID


def test_detects_sbu_chapter_ranges_from_reference_style_text():
    page_texts = [
        "Table of Contents\nChapter 2 SBU-G\nChapter 3 SBU-T",
        "CHAPTER-2\nTRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT GENERATION\nSBU-G",
        "Table 2.19 Approved Transfer Cost of SBU-G",
        "CHAPTER-3\nTRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT TRANSMISSION\nSBU-T",
        "Table 3.1 Summary of ARR and ERC claimed for SBU-T",
        "CHAPTER-4\nEnergy sales and T&D loss\nTransmission loss\nDistribution loss",
        "CHAPTER-5\nSBU-D DISTRIBUTION\nARR, ERC and Revenue Gap",
    ]
    ranges = detect_chapter_ranges_from_text(page_texts)
    assert ranges["SBU_G"] == (2, 3)
    assert ranges["SBU_T"] == (4, 5)
    assert ranges["ENERGY_TD"] == (6, 6)
    assert ranges["SBU_D"] == (7, 7)


def test_detects_sbu_g_target_table_from_reference_style_table():
    table = [
        ["Particulars", "ARR Approval", "Actuals", "TU Sought", "Difference"],
        ["Cost of Generation of Power", "100.00", "110.00", "112.00", "12.00"],
        ["O&M expenses", "25.00", "26.00", "27.00", "2.00"],
        ["Net ARR / Transfer Cost to SBU-D", "150.00", "160.00", "162.00", "12.00"],
    ]
    extracted = _extract_rows_from_target_table(
        table,
        12,
        0,
        TARGETS_BY_ID["SBU_G_TRANSFER_COST"],
        "Approved Transfer Cost of SBU-G",
        "truing_up_petition",
    )
    labels = {row.row_label for row in extracted.rows}
    value_types = {row.value_type for row in extracted.rows}
    assert "Cost of Generation of Power" in labels
    assert "Net ARR / Transfer Cost to SBU-D" in labels
    assert {"approved", "actual", "claimed", "deviation"}.issubset(value_types)
    assert extracted.target_id == "SBU_G_TRANSFER_COST"


def test_detects_sbu_t_and_sbu_d_summary_tables():
    sbu_t_table = [
        ["Particulars", "MYT Order dated 25.06.2022", "Actual", "Sought for TU"],
        ["O&M expenses", "10.00", "11.00", "12.00"],
        ["Net ARR / Transmission charges", "90.00", "95.00", "96.00"],
    ]
    sbu_d_table = [
        ["Particulars", "Approved", "Actual", "Claimed"],
        ["Purchase of power", "1000.00", "1050.00", "1060.00"],
        ["Cost of Generation (SBU-G)", "150.00", "160.00", "162.00"],
        ["Cost of Intra-State Transmission (SBU-T)", "90.00", "95.00", "96.00"],
    ]

    sbu_t = _extract_rows_from_target_table(
        sbu_t_table,
        20,
        0,
        TARGETS_BY_ID["SBU_T_ARR_SUMMARY"],
        "Summary of ARR and ERC claimed for SBU-T",
        "truing_up_petition",
    )
    sbu_d = _extract_rows_from_target_table(
        sbu_d_table,
        30,
        0,
        TARGETS_BY_ID["SBU_D_ARR_SUMMARY"],
        "ARR, ERC and Revenue Gap claimed for SBU-D",
        "truing_up_petition",
    )

    assert any(row.row_label == "Net ARR / Transmission charges" for row in sbu_t.rows)
    assert any(row.row_label == "Cost of Generation (SBU-G)" for row in sbu_d.rows)
    assert any(row.row_label == "Cost of Intra-State Transmission (SBU-T)" for row in sbu_d.rows)

