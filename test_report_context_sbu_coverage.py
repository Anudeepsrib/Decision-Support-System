#!/usr/bin/env python3
"""Tests for SBU-G/SBU-T report context coverage modes."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from pdf_generator import generate_order_html
from report_context import build_report_context


def _comparison(canonical_id, display_name, sbu, section, value=100.0):
    return {
        "id": f"{canonical_id}-id",
        "canonical_id": canonical_id,
        "display_name": display_name,
        "canonical_name": display_name,
        "sbu": sbu,
        "unit": "Rs. Cr.",
        "section": section,
        "approved_value": value,
        "actual_value": value + 5,
        "claimed_value": value + 6,
        "variance": 6.0,
        "variance_percent": 6.0,
        "decision_class": "ACCEPTABLE_VARIANCE",
        "approved_source_page": 10,
        "actual_source_page": 11,
        "claimed_source_page": 11,
        "approved_source_table": "target table",
        "actual_source_table": "target table",
        "claimed_source_table": "target table",
    }


def test_sbu_g_full_sbu_t_fallback_and_missing_modes():
    context = build_report_context(
        case_id="coverage-test",
        financial_year="2024-25",
        comparisons=[
            _comparison("OM_EXPENSES_GENERATION", "O&M Expenses - Generation", "SBU-G", "sbu_g"),
            _comparison("NET_ARR_TRANSMISSION_TRANSFER_FALLBACK", "SBU-T Transmission Cost from SBU-D Summary", "SBU-T", "sbu_t"),
        ],
    )

    assert context["chapter_2_sbu_g"]["source"] == "chapter_table"
    assert context["chapter_3_sbu_t"]["source"] == "fallback_from_sbu_d_summary"
    coverage = {row["chapter"]: row for row in context["extraction_coverage"]}
    assert coverage["SBU-G"]["status"] == "Full"
    assert coverage["SBU-T"]["status"] == "Fallback"
    assert coverage["Energy/T&D"]["status"] == "Missing"


def test_report_renders_fallback_and_missing_modes():
    html = generate_order_html(
        case_id="coverage-html-test",
        financial_year="2024-25",
        comparisons=[
            _comparison("NET_ARR_GENERATION_TRANSFER_FALLBACK", "SBU-G Transfer Cost from SBU-D Summary", "SBU-G", "sbu_g"),
        ],
        reviews=[],
        officer_name="Coverage Officer",
    )

    assert "Fallback transfer-cost value for SBU-G" in html
    assert "fallback_from_sbu_d_summary" in html
    assert "Status of mapped values for SBU-T" in html
    assert "target tables attempted" in html.lower()

