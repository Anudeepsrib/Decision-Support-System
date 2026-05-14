#!/usr/bin/env python3
"""
Test deterministic KSERC order HTML generation without rendering a PDF.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from pdf_generator import BANNED_PDF_STRINGS, generate_order_html


def test_pdf_html_generation():
    html_template = generate_order_html(
        case_id="html-test",
        financial_year="2024-25",
        comparisons=[
            {
                "id": "comp1",
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
            }
        ],
        reviews=[],
        officer_name="HTML Test Officer",
    )

    checks = [
        ("Contains KSERC header", "KERALA STATE ELECTRICITY REGULATORY COMMISSION" in html_template),
        ("Contains title page matter marker", "In the matter of" in html_template),
        ("Contains table of contents", "Table of Contents" in html_template),
        ("Contains chapter marker", "CHAPTER -1" in html_template),
        ("Contains regulatory table header", "Sought for TU" in html_template),
        ("Contains final order", "Final Order" in html_template),
        ("Contains signature", "Sd/-" in html_template),
    ]

    for check_name, passed in checks:
        assert passed, check_name
    for banned in BANNED_PDF_STRINGS:
        assert banned not in html_template

    output_file = os.path.join(os.path.dirname(__file__), "output", "test_order_output.html")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)


def test_pdf_structure_requirements():
    html_template = generate_order_html(
        case_id="structure-test",
        financial_year="2024-25",
        comparisons=[],
        reviews=[],
        officer_name="Structure Test Officer",
    )
    required_sections = [
        "KERALA STATE ELECTRICITY REGULATORY COMMISSION",
        "Table of Contents",
        "Statutory provisions",
        "MYT framework provisions",
        "Analysis and decision of the Commission",
        "Order of the Commission",
    ]
    for section in required_sections:
        assert section in html_template


if __name__ == "__main__":
    test_pdf_html_generation()
    test_pdf_structure_requirements()
    print("PDF HTML-only tests passed.")
