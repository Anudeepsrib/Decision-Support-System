#!/usr/bin/env python3
"""
Reference-style fidelity checks for the deterministic KSERC truing-up order PDF.
"""

import asyncio
import os
import re
import sys

import pdfplumber

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from pdf_generator import BANNED_PDF_STRINGS, generate_order_pdf, score_reference_fidelity


def _sample_comparisons():
    return [
        {
            "id": "g1",
            "canonical_id": "OM_EXPENSES_GENERATION",
            "display_name": "O&M Expenses - Generation",
            "sbu": "SBU-G",
            "unit": "Rs. Cr.",
            "section": "sbu_g",
            "approved_value": 120.0,
            "actual_value": 128.0,
            "claimed_value": 128.0,
            "variance": 8.0,
            "variance_percent": 6.67,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "g2",
            "canonical_id": "NET_ARR_GENERATION",
            "display_name": "Net ARR - Generation",
            "sbu": "SBU-G",
            "unit": "Rs. Cr.",
            "section": "sbu_g",
            "approved_value": 500.0,
            "actual_value": 530.0,
            "claimed_value": 530.0,
            "variance": 30.0,
            "variance_percent": 6.0,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "t1",
            "canonical_id": "DEPRECIATION_TRANSMISSION",
            "display_name": "Depreciation - Transmission",
            "sbu": "SBU-T",
            "unit": "Rs. Cr.",
            "section": "sbu_t",
            "approved_value": 80.0,
            "actual_value": 92.0,
            "claimed_value": 92.0,
            "variance": 12.0,
            "variance_percent": 15.0,
            "decision_class": "REVIEW_REQUIRED",
        },
        {
            "id": "e1",
            "canonical_id": "ENERGY_SALES",
            "display_name": "Energy Sales",
            "sbu": "ENERGY",
            "unit": "MU",
            "section": "energy_sales_td_loss",
            "approved_value": 20000.0,
            "actual_value": 20500.0,
            "claimed_value": 20500.0,
            "variance": 500.0,
            "variance_percent": 2.5,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "d1",
            "canonical_id": "PURCHASE_OF_POWER",
            "display_name": "Purchase of Power",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 1000.0,
            "actual_value": 1150.0,
            "claimed_value": 1150.0,
            "variance": 150.0,
            "variance_percent": 15.0,
            "decision_class": "REVIEW_REQUIRED",
        },
        {
            "id": "d2",
            "canonical_id": "NON_TARIFF_INCOME",
            "display_name": "Non-Tariff Income",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 90.0,
            "actual_value": 95.0,
            "claimed_value": 95.0,
            "variance": 5.0,
            "variance_percent": 5.56,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "c1",
            "canonical_id": "OTHER_EXPENSES",
            "display_name": "Other Expenses",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "common_expenses",
            "approved_value": 25.0,
            "actual_value": 31.0,
            "claimed_value": 31.0,
            "variance": 6.0,
            "variance_percent": 24.0,
            "decision_class": "REVIEW_REQUIRED",
        },
        {
            "id": "noise1",
            "canonical_id": "PURCHASE_OF_POWER",
            "display_name": "0 to 100 units Fixed Charge",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 1.0,
            "actual_value": 1.0,
            "claimed_value": 1.0,
            "variance": 0.0,
            "variance_percent": 0.0,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
    ]


def _extract_pdf_text(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_reference_pdf_fidelity():
    result = asyncio.run(
        generate_order_pdf(
            case_id="49/2024",
            financial_year="2023-24",
            comparisons=_sample_comparisons(),
            reviews=[],
            officer_name="Fidelity Test",
        )
    )
    with pdfplumber.open(result["file_path"]) as pdf:
        page_count = len(pdf.pages)
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    normalised = _normalise(text)

    assert page_count == 237

    required_markers = [
        "KERALA STATE ELECTRICITY REGULATORY COMMISSION",
        "THIRUVANANTHAPURAM",
        "Present :",
        "In the matter of :",
        "Petitioner :",
        "ORDER DATED",
        "Table of Contents",
        "CHAPTER -1",
        "INTRODUCTION",
        "Statutory provisions",
        "CHAPTER-2",
        "TRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT",
        "Table-1.1",
        "Analysis and decision of the Commission",
        "Consolidated Truing up",
        "Final Order",
        "Sd/-",
    ]
    for marker in required_markers:
        assert marker in normalised, marker

    for banned in BANNED_PDF_STRINGS:
        assert banned not in normalised

    score = score_reference_fidelity(text)
    assert score["score"] >= 85, score
    assert not score["banned_strings_found"]


if __name__ == "__main__":
    test_reference_pdf_fidelity()
    print("Reference PDF fidelity test passed.")
