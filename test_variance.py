#!/usr/bin/env python3
"""
Test variance calculation and decision classification
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from comparison import calculate_variance, classify_decision, VARIANCE_THRESHOLD_PERCENT, CONFIDENCE_THRESHOLD

def test_variance_calculations():
    print("=== Testing Variance Calculations ===")
    
    test_cases = [
        # (approved, actual, expected_variance, expected_variance_pct)
        (100.0, 110.0, 10.0, 10.0),    # 10% increase
        (100.0, 85.0, -15.0, -15.0),   # 15% decrease
        (100.0, 100.0, 0.0, 0.0),      # No variance
        (0.0, 0.0, 0.0, 0.0),          # Both zero
        (0.0, 50.0, 50.0, None),        # Approved zero, actual non-zero
        (100.0, None, None, None),       # Missing actual
        (None, 100.0, None, None),       # Missing approved
    ]
    
    for i, (approved, actual, exp_var, exp_pct) in enumerate(test_cases):
        variance, variance_pct = calculate_variance(approved, actual)
        print(f"Test {i+1}: Approved={approved}, Actual={actual}")
        print(f"  Expected: variance={exp_var}, pct={exp_pct}")
        print(f"  Got: variance={variance}, pct={variance_pct}")
        
        # Verify results
        if variance is not None and exp_var is not None:
            assert abs(variance - exp_var) < 0.01, f"Variance mismatch: {variance} != {exp_var}"
        if variance_pct is not None and exp_pct is not None:
            assert abs(variance_pct - exp_pct) < 0.01, f"Percentage mismatch: {variance_pct} != {exp_pct}"
        print("  PASS")
        print()

def test_decision_classification():
    print("=== Testing Decision Classification ===")
    print(f"Variance threshold: {VARIANCE_THRESHOLD_PERCENT}%")
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print()
    
    test_cases = [
        # (variance_pct, confidence, expected_decision, expected_reason)
        (10.0, 0.8, "ACCEPTABLE_VARIANCE", None),
        (14.9, 0.9, "ACCEPTABLE_VARIANCE", None),
        (15.0, 0.9, "REVIEW_REQUIRED", "Deviation of +15.0% (increase) exceeds 15.0% threshold"),
        (20.0, 0.9, "REVIEW_REQUIRED", "Deviation of +20.0% (increase) exceeds 15.0% threshold"),
        (-15.0, 0.9, "REVIEW_REQUIRED", "Deviation of -15.0% (decrease) exceeds 15.0% threshold"),
        (5.0, 0.5, "REVIEW_REQUIRED", "Low extraction confidence (50%)"),
        (None, 0.9, "REVIEW_REQUIRED", "Approved value is zero; percentage deviation is not applicable"),
    ]
    
    for i, (variance_pct, confidence, expected_decision, expected_reason) in enumerate(test_cases):
        decision, reason = classify_decision(variance_pct, confidence)
        print(f"Test {i+1}: Variance={variance_pct}%, Confidence={confidence}")
        print(f"  Expected: {expected_decision}, Reason: {expected_reason}")
        print(f"  Got: {decision}, Reason: {reason}")
        
        assert decision == expected_decision, f"Decision mismatch: {decision} != {expected_decision}"
        if expected_reason:
            assert expected_reason in reason, f"Reason mismatch: {reason} doesn't contain {expected_reason}"
        print("  PASS")
        print()

def test_edge_cases():
    print("=== Testing Edge Cases ===")
    
    # Test division by zero protection
    variance, variance_pct = calculate_variance(0.0, 100.0)
    print(f"Approved=0, Actual=100 -> variance={variance}, pct={variance_pct}")
    assert variance == 100.0, "Variance should be 100"
    assert variance_pct is None, "Percentage should be NA/None"
    print("PASS Division by zero handled correctly")

    decision, reason = classify_decision(None, 0.9, missing_values=True)
    assert decision == "INCOMPLETE_DATA"
    assert "Missing approved" in reason
    print("PASS Missing values classified as incomplete data")
    
    # Test rounding
    variance, variance_pct = calculate_variance(100.0, 115.555555)
    print(f"Rounding test: variance={variance}, pct={variance_pct}")
    assert variance == 15.56, "Variance should be rounded to 2 decimals"
    assert variance_pct == 15.56, "Percentage should be rounded to 2 decimals"
    print("PASS Rounding works correctly")
    print()

if __name__ == "__main__":
    test_variance_calculations()
    test_decision_classification()
    test_edge_cases()
    print("All variance engine tests passed!")
