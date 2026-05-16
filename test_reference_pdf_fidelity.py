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
            "canonical_id": "OM_COST",
            "display_name": "O&M Cost",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 500.0,
            "actual_value": 475.0,
            "claimed_value": 475.0,
            "variance": -25.0,
            "variance_percent": -5.0,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "d3",
            "canonical_id": "INTEREST_FINANCE_CHARGES",
            "display_name": "Interest and Finance Charges",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 200.0,
            "actual_value": 180.0,
            "claimed_value": 180.0,
            "variance": -20.0,
            "variance_percent": -10.0,
            "decision_class": "REVIEW_REQUIRED",
        },
        {
            "id": "d4",
            "canonical_id": "DEPRECIATION",
            "display_name": "Depreciation",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 150.0,
            "actual_value": 165.0,
            "claimed_value": 165.0,
            "variance": 15.0,
            "variance_percent": 10.0,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "d5",
            "canonical_id": "ROE",
            "display_name": "Return on Equity",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 75.0,
            "actual_value": 75.0,
            "claimed_value": 75.0,
            "variance": 0.0,
            "variance_percent": 0.0,
            "decision_class": "ACCEPTABLE_VARIANCE",
        },
        {
            "id": "d6",
            "canonical_id": "NET_EXPENDITURE",
            "display_name": "Net Expenditure",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": 2000.0,
            "actual_value": 2145.0,
            "claimed_value": 2145.0,
            "variance": 145.0,
            "variance_percent": 7.25,
            "decision_class": "REVIEW_REQUIRED",
            "is_total": True,
        },
        {
            "id": "d7",
            "canonical_id": "REVENUE_SURPLUS_GAP",
            "display_name": "Revenue Surplus / Gap",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "approved_value": -50.0,
            "actual_value": 120.0,
            "claimed_value": 120.0,
            "variance": 170.0,
            "variance_percent": 340.0,
            "decision_class": "REVIEW_REQUIRED",
            "is_total": True,
        },
        {
            "id": "d8",
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


def _chapter_page_count(page_texts, start_marker, end_marker):
    start_pattern = re.compile(rf"(^|\n)\s*{re.escape(start_marker)}\s*(\n|$)", re.IGNORECASE)
    end_pattern = re.compile(rf"(^|\n)\s*{re.escape(end_marker)}\s*(\n|$)", re.IGNORECASE)
    start = next((i for i, page in enumerate(page_texts) if start_pattern.search(page)), None)
    if start is None:
        return 0
    end = next((i for i in range(start + 1, len(page_texts)) if end_pattern.search(page_texts[i])), len(page_texts))
    return max(1, end - start)


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
        page_texts = [page.extract_text() or "" for page in pdf.pages]
        page_count = len(pdf.pages)
        text = "\n".join(page_texts)
    normalised = _normalise(text)

    assert page_count <= 60

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
        "TRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT GENERATION",
        "CHAPTER-3",
        "STRATEGIC BUSINESS UNIT TRANSMISSION",
        "CHAPTER-4",
        "ENERGY SALES AND T&D LOSS",
        "CHAPTER-5",
        "CHAPTER-7",
        "STRATEGIC BUSINESS UNIT DISTRIBUTION",
        "Table-1.1",
        "Table 5.1",
        "Consolidated Truing up",
        "Final Order",
        "ORDER OF THE COMMISSION",
        "Sd/-",
    ]
    for marker in required_markers:
        assert marker in normalised, marker

    for banned in BANNED_PDF_STRINGS:
        assert banned not in normalised
    assert "draft regulatory order page" not in normalised
    assert not re.search(r"\bPart\s+\d+\b", normalised)
    assert "Documents considered - Part" not in normalised
    assert "No mapped canonical value" not in normalised

    sbu_g_text = normalised.split("CHAPTER-2", 1)[1].split("CHAPTER-3", 1)[0]
    sbu_t_text = normalised.split("CHAPTER-3", 1)[1].split("CHAPTER-4", 1)[0]
    sbu_d_text = normalised.split("CHAPTER-5", 1)[1].split("CHAPTER-6", 1)[0]
    chapter_1_text = normalised.split("CHAPTER -1", 1)[1].split("CHAPTER-2", 1)[0]

    assert "Purchase of Power" not in sbu_g_text
    assert "Purchase of Power" not in sbu_t_text
    assert "Purchase of Power" in sbu_d_text
    assert chapter_1_text.count("Purchase of Power") <= 1
    assert _chapter_page_count(page_texts, "CHAPTER -1", "CHAPTER-2") <= 8
    assert _chapter_page_count(page_texts, "CHAPTER-2", "CHAPTER-3") <= 2
    assert _chapter_page_count(page_texts, "CHAPTER-3", "CHAPTER-4") <= 2

    repeated_sentences = [
        re.sub(r"\s+", " ", sentence).strip().lower()
        for sentence in re.findall(r"[^.!?]+[.!?]", text)
        if len(re.sub(r"\s+", " ", sentence).strip()) > 40
    ]
    assert not {sentence for sentence in repeated_sentences if repeated_sentences.count(sentence) > 3}

    score = score_reference_fidelity(text)
    assert score["score"] >= 90, score
    assert not score["banned_strings_found"]


if __name__ == "__main__":
    test_reference_pdf_fidelity()
    print("Reference PDF fidelity test passed.")
