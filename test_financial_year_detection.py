#!/usr/bin/env python3
"""Tests for deterministic financial-year inference."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from api import _best_by_canonical_id, _effective_financial_year, infer_financial_year_from_filename


def test_infers_petition_financial_year_from_filename():
    assert infer_financial_year_from_filename("2023 -24 petition by ksebl.pdf") == "2023-24"
    assert infer_financial_year_from_filename("KSEBL_TruingUp_Petition_2024-25.pdf") == "2024-25"


def test_does_not_treat_myt_control_period_as_single_financial_year():
    assert infer_financial_year_from_filename("ARR 2022-27 dated 25.06.2022-final.pdf") is None


def test_petition_filename_overrides_default_form_year():
    assert (
        _effective_financial_year(
            "2023 -24 petition by ksebl.pdf",
            "truing_up_petition",
            "2024-25",
        )
        == "2023-24"
    )


def test_best_by_canonical_id_prefers_summary_om_over_lakh_detail_rows():
    best = _best_by_canonical_id(
        [
            {
                "canonical_id": "OM_EXPENSES_TRANSMISSION",
                "raw_label": "Total Normative O&M expenses - (A) + (B) Rs. Cr",
                "value": 625.20,
                "mapping_confidence": 1.0,
            },
            {
                "canonical_id": "OM_EXPENSES_TRANSMISSION",
                "raw_label": "O&M expenses",
                "value": 588.95,
                "mapping_confidence": 0.99,
            },
        ]
    )
    assert best["OM_EXPENSES_TRANSMISSION"]["value"] == 588.95
