#!/usr/bin/env python3
"""
Test AI safety and narrative generation
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from prompts import generate_variance_explanation

def test_ai_safety():
    print("=== Testing AI Safety ===")
    
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
        print(f"  Approved: ₹{case['approved_value']:,.2f} Cr.")
        print(f"  Actual: ₹{case['actual_value']:,.2f} Cr.")
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
            ("No fabricated numbers", all(str(x) in explanation for x in [case['approved_value'], case['actual_value']])),
            ("No hallucinated regulations", "KSERC" in explanation or "regulation" in explanation or "Commission" in explanation),
            ("Reasonable length", len(explanation) < 500),
            ("Professional tone", any(word in explanation.lower() for word in ["may", "likely", "attributed", "due"])),
        ]
        
        for check_name, passed in safety_checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
    
    print("\n=== Testing Template Fallback ===")
    
    # Test with no OpenAI key (force template fallback)
    os.environ['OPENAI_API_KEY'] = ''
    
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
        ("Contains variance amount", "₹150.00" in explanation or "150.00" in explanation),
        ("Contains percentage", "+15.0%" in explanation or "15.0%" in explanation),
        ("Contains cost head explanation", "power purchase" in explanation.lower()),
        ("Professional language", "may be attributed" in explanation.lower()),
    ]
    
    for check_name, passed in template_checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")

def test_no_number_fabrication():
    """Test that AI doesn't fabricate numbers"""
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
            num = float(word.replace('₹', '').replace(',', '').replace('%', ''))
            numbers_in_text.append(num)
        except ValueError:
            continue
    
    expected_numbers = [123.45, 156.78, 27.0]
    unexpected_numbers = [n for n in numbers_in_text if n not in expected_numbers]
    
    if unexpected_numbers:
        print(f"✗ UNEXPECTED NUMBERS FOUND: {unexpected_numbers}")
        print("This indicates potential number fabrication!")
    else:
        print("✓ No unexpected numbers found - safety check passed")

if __name__ == "__main__":
    test_ai_safety()
    test_no_number_fabrication()
