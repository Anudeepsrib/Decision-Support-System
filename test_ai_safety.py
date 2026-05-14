#!/usr/bin/env python3
"""
Test deterministic narrative generation
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from prompts import generate_variance_explanation

def test_ai_safety():
    print("=== Testing Deterministic Narrative Safety ===")
    
    # Test cases with different scenarios
    test_cases = [
        {
            "line_item": "Power Purchase Cost",
            "approved_value": 1000.0,
            "actual_value": 1150.0,
            "variance_percent": 15.0,
            "cost_head": "Power_Purchase"
        },
        {
            "line_item": "O&M Expenses",
            "approved_value": 500.0,
            "actual_value": 425.0,
            "variance_percent": -15.0,
            "cost_head": "O&M"
        },
        {
            "line_item": "Interest & Finance Charges",
            "approved_value": 200.0,
            "actual_value": 180.0,
            "variance_percent": -10.0,
            "cost_head": "Interest"
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {case['line_item']}")
        print(f"  Approved: Rs. {case['approved_value']:,.2f} Cr.")
        print(f"  Actual: Rs. {case['actual_value']:,.2f} Cr.")
        print(f"  Variance: {case['variance_percent']:+.1f}%")
        
        explanation = generate_variance_explanation(
            case['line_item'],
            case['approved_value'],
            case['actual_value'],
            case['variance_percent'],
            case['cost_head']
        )
        
        print(f"  Explanation: {explanation}")
        
        # Safety checks
        safety_checks = [
            ("Contains supplied values", all(f"{x:,.2f}" in explanation for x in [case['approved_value'], case['actual_value']])),
            ("No unsupported legal conclusion", "final approval" not in explanation.lower()),
            ("Reasonable length", len(explanation) < 500),
            ("Deterministic tone", "deterministic" in explanation.lower() or "reviewing officer" in explanation.lower()),
        ]
        
        for check_name, passed in safety_checks:
            status = "PASS" if passed else "FAIL"
            print(f"  {status} {check_name}")
    
    print("\n=== Testing Template Output ===")
    
    explanation = generate_variance_explanation(
        "Power Purchase Cost",
        1000.0,
        1150.0,
        15.0,
        "Power_Purchase"
    )
    
    print(f"Template explanation: {explanation}")
    
    # Verify template contains expected elements
    template_checks = [
        ("Contains variance amount", "Rs. 150.00" in explanation or "150.00" in explanation),
        ("Contains percentage", "+15.0%" in explanation or "15.0%" in explanation),
        ("Contains line item", "power purchase" in explanation.lower()),
        ("Professional language", "reviewing officer" in explanation.lower()),
    ]
    
    for check_name, passed in template_checks:
        status = "PASS" if passed else "FAIL"
        print(f"  {status} {check_name}")

def test_no_number_fabrication():
    """Test that deterministic templates do not fabricate numbers."""
    print("\n=== Testing Number Fabrication Prevention ===")
    
    # Test with specific numbers
    explanation = generate_variance_explanation(
        "Test Line Item",
        123.45,
        156.78,
        27.0,
        "Other"
    )
    
    print(f"Explanation: {explanation}")
    
    # Check that only our numbers appear
    numbers_in_text = []
    for word in explanation.split():
        try:
            num = float(word.replace('Rs.', '').replace(',', '').replace('%', ''))
            numbers_in_text.append(num)
        except ValueError:
            continue
    
    expected_numbers = [123.45, 156.78, 33.33, 27.0]
    unexpected_numbers = [n for n in numbers_in_text if n not in expected_numbers]
    
    if unexpected_numbers:
        print(f"FAIL UNEXPECTED NUMBERS FOUND: {unexpected_numbers}")
        print("This indicates potential number fabrication!")
    else:
        print("PASS No unexpected numbers found - safety check passed")

if __name__ == "__main__":
    test_ai_safety()
    test_no_number_fabrication()
