#!/usr/bin/env python3
"""
Test PDF generation functionality
"""
import os
import sys
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from pdf_generator import generate_order_html, generate_order_pdf

from datetime import datetime

def test_pdf_generation():
    print("=== Testing PDF Generation ===")
    
    # Mock comparison data
    mock_comparisons = [
        {
            "id": "comp1",
            "canonical_name": "Power Purchase Cost",
            "cost_head": "Power_Purchase",
            "approved_value": 1000.0,
            "actual_value": 1150.0,
            "claimed_value": 1150.0,
            "variance": 150.0,
            "variance_percent": 15.0,
            "decision_class": "REVIEW_REQUIRED"
        },
        {
            "id": "comp2", 
            "canonical_name": "O&M Expenses",
            "cost_head": "O&M",
            "approved_value": 500.0,
            "actual_value": 475.0,
            "claimed_value": 475.0,
            "variance": -25.0,
            "variance_percent": -5.0,
            "decision_class": "AI_AUTO"
        },
        {
            "id": "comp3",
            "canonical_name": "Interest & Finance Charges",
            "cost_head": "Interest", 
            "approved_value": 200.0,
            "actual_value": 180.0,
            "claimed_value": 180.0,
            "variance": -20.0,
            "variance_percent": -10.0,
            "decision_class": "AI_AUTO"
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
        ("Contains summary table", "Table 5.1" in html_content),
        ("Contains variance data", "₹" in html_content and "%" in html_content),
        ("Contains order narrative", "The Commission has" in html_content),
        ("Contains draft notice", "DRAFT FOR COMMISSION REVIEW" in html_content),
        ("Contains officer name", "Test Officer" in html_content),
        ("Contains footer", "AI Decision Support System" in html_content),
    ]
    
    print("\nHTML validation:")
    for check_name, passed in html_checks:
        status = "✓" if passed else "✗"
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

    print(f"PDF generated successfully:")
    print(f"  File path: {pdf_result['file_path']}")
    print(f"  File size: {pdf_result['file_size']} bytes")
    print(f"  File hash: {pdf_result['file_hash'][:16]}...")

    assert os.path.exists(pdf_result['file_path']), "PDF file not found on disk"
    assert pdf_result['file_size'] > 1000, "PDF file size too small"
    print("  ✓ PDF file created on disk")
    print("  ✓ PDF file size is reasonable")

def test_pdf_quality():
    """Test PDF output quality metrics"""
    print("\n=== Testing PDF Quality ===")
    
    # Test with larger dataset
    large_comparisons = []
    for i in range(20):  # 20 line items
        large_comparisons.append({
            "id": f"comp{i}",
            "canonical_name": f"Line Item {i+1}",
            "cost_head": "Other",
            "approved_value": float(100 + i * 10),
            "actual_value": float(100 + i * 10 + (i % 3 - 1) * 5),
            "claimed_value": float(100 + i * 10 + (i % 3 - 1) * 5),
            "variance": float((i % 3 - 1) * 5),
            "variance_percent": float((i % 3 - 1) * 5),
            "decision_class": "REVIEW_REQUIRED" if i % 3 == 0 else "AI_AUTO"
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
            ("Summary table caption", "Table 5.1" in html_content),
            ("Commission views section", "Commission Views" in html_content),
            ("SBU-G section", "SBU-G Analysis" in html_content),
            ("SBU-T section", "SBU-T Analysis" in html_content),
            ("Proper formatting", "<table" in html_content and "</table>" in html_content),
            ("CSS styling", "style=" in html_content),
        ]
        
        print("Quality validation:")
        for check_name, passed in quality_checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            
    except Exception as e:
        print(f"Quality test failed: {e}")

if __name__ == "__main__":
    test_pdf_generation()
    test_pdf_quality()
