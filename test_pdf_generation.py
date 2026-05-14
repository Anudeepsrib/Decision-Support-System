#!/usr/bin/env python3
"""
Test PDF generation functionality
"""
import os
import sys
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pdf_generator import BANNED_PDF_STRINGS, generate_order_html, generate_order_pdf


def test_pdf_generation():
    print("=== Testing PDF Generation ===")
    
    # Mock comparison data
    mock_comparisons = [
        {
            "id": "comp1",
            "canonical_id": "PURCHASE_OF_POWER",
            "display_name": "Purchase of Power",
            "canonical_name": "Purchase of Power",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "cost_head": "SBU-D",
            "approved_value": 1000.0,
            "actual_value": 1150.0,
            "claimed_value": 1150.0,
            "variance": 150.0,
            "variance_percent": 15.0,
            "decision_class": "REVIEW_REQUIRED"
        },
        {
            "id": "comp2", 
            "canonical_id": "OM_COST",
            "display_name": "O&M Cost",
            "canonical_name": "O&M Cost",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "cost_head": "SBU-D",
            "approved_value": 500.0,
            "actual_value": 475.0,
            "claimed_value": 475.0,
            "variance": -25.0,
            "variance_percent": -5.0,
            "decision_class": "ACCEPTABLE_VARIANCE"
        },
        {
            "id": "comp3",
            "canonical_id": "INTEREST_FINANCE_CHARGES",
            "display_name": "Interest and Finance Charges",
            "canonical_name": "Interest and Finance Charges",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "cost_head": "SBU-D",
            "approved_value": 200.0,
            "actual_value": 180.0,
            "claimed_value": 180.0,
            "variance": -20.0,
            "variance_percent": -10.0,
            "decision_class": "ACCEPTABLE_VARIANCE"
        }
    ]
    
    # Mock review data
    mock_reviews = [
        {
            "comparison_id": "comp1",
            "action": "review",
            "officer_comment": "Variance exceeds threshold - requires detailed justification"
        }
    ]
    
    # Test HTML generation
    print("Testing HTML generation...")
    html_content = generate_order_html(
        case_id="test-case-123",
        financial_year="2024-25",
        comparisons=mock_comparisons,
        reviews=mock_reviews,
        officer_name="Test Officer"
    )
    
    print(f"HTML generated: {len(html_content)} characters")
    
    # Validate HTML content
    html_checks = [
        ("Contains KSERC header", "KERALA STATE ELECTRICITY REGULATORY COMMISSION" in html_content),
        ("Contains case ID", "test-case-123" in html_content),
        ("Contains financial year", "2024-25" in html_content),
        ("Contains table of contents", "Table of Contents" in html_content),
        ("Contains SBU-D chapter", "STRATEGIC BUSINESS UNIT DISTRIBUTION" in html_content),
        ("Contains variance data", "Rs. Cr." in html_content or "%" in html_content),
        ("Contains order narrative", "The Commission has" in html_content),
        ("Contains order date", "ORDER DATED" in html_content),
        ("Contains officer name", "Test Officer" in html_content),
        ("Contains signature marker", "Sd/-" in html_content),
    ]

    for banned in BANNED_PDF_STRINGS:
        assert banned not in html_content
    
    print("\nHTML validation:")
    for check_name, passed in html_checks:
        status = "PASS" if passed else "FAIL"
        print(f"  {status} {check_name}")
    
    # Test PDF generation using the app's configured backend.
    print("\nTesting PDF generation...")
    pdf_result = asyncio.run(generate_order_pdf(
        case_id="test-case-123",
        financial_year="2024-25",
        comparisons=mock_comparisons,
        reviews=mock_reviews,
        officer_name="Test Officer"
    ))

    print("PDF generated successfully:")
    print(f"  File path: {pdf_result['file_path']}")
    print(f"  File size: {pdf_result['file_size']} bytes")
    print(f"  File hash: {pdf_result['file_hash'][:16]}...")

    assert os.path.exists(pdf_result['file_path']), "PDF file not found on disk"
    assert pdf_result['file_size'] > 1000, "PDF file size too small"
    print("  PASS PDF file created on disk")
    print("  PASS PDF file size is reasonable")

def test_pdf_quality():
    """Test PDF output quality metrics"""
    print("\n=== Testing PDF Quality ===")
    
    # Test with larger dataset
    large_comparisons = []
    for i in range(20):  # 20 line items
        large_comparisons.append({
            "id": f"comp{i}",
            "canonical_id": "PURCHASE_OF_POWER" if i % 2 == 0 else "OM_COST",
            "display_name": f"Line Item {i+1}",
            "canonical_name": f"Line Item {i+1}",
            "sbu": "SBU-D",
            "unit": "Rs. Cr.",
            "section": "sbu_d",
            "cost_head": "SBU-D",
            "approved_value": float(100 + i * 10),
            "actual_value": float(100 + i * 10 + (i % 3 - 1) * 5),
            "claimed_value": float(100 + i * 10 + (i % 3 - 1) * 5),
            "variance": float((i % 3 - 1) * 5),
            "variance_percent": float((i % 3 - 1) * 5),
            "decision_class": "REVIEW_REQUIRED" if i % 3 == 0 else "ACCEPTABLE_VARIANCE"
        })
    
    try:
        html_content = generate_order_html(
            case_id="quality-test",
            financial_year="2024-25",
            comparisons=large_comparisons,
            reviews=[],
            officer_name="Quality Test Officer"
        )
        
        # Quality checks
        quality_checks = [
            ("Title page", "KERALA STATE ELECTRICITY REGULATORY COMMISSION" in html_content),
            ("Table of contents", "Table of Contents" in html_content),
            ("SBU-G chapter", "STRATEGIC BUSINESS UNIT GENERATION" in html_content),
            ("SBU-T chapter", "STRATEGIC BUSINESS UNIT TRANSMISSION" in html_content),
            ("SBU-D chapter", "STRATEGIC BUSINESS UNIT DISTRIBUTION" in html_content),
            ("Proper formatting", "<table" in html_content and "</table>" in html_content),
            ("Reference table header", "Sought for TU" in html_content),
        ]
        
        print("Quality validation:")
        for check_name, passed in quality_checks:
            status = "PASS" if passed else "FAIL"
            print(f"  {status} {check_name}")
            
    except Exception as e:
        print(f"Quality test failed: {e}")

if __name__ == "__main__":
    test_pdf_generation()
    test_pdf_quality()
