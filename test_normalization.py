#!/usr/bin/env python3
"""
Test normalization pipeline with extracted rows
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from normalizer import normalize_row_label, normalize_batch
from extractor import extract_tables_from_pdf

def test_normalization():
    # Load extracted data from existing PDF
    data_dir = os.path.join(os.path.dirname(__file__), 'mvp_uploads')
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found")
        return
    
    test_file = os.path.join(data_dir, pdf_files[0])
    print(f"Testing normalization on: {pdf_files[0]}")
    
    try:
        with open(test_file, 'rb') as f:
            pdf_bytes = f.read()
        
        extracted = extract_tables_from_pdf(pdf_bytes, pdf_files[0])
        print(f"Extracted {len(extracted)} rows")
        
        # Test normalization on sample rows
        test_labels = [
            "Purchase of power",
            "Power Purchase Cost", 
            "Cost of Power Purchased",
            "Generation Cost",
            "Interest & Finance Charges",
            "Depreciation",
            "Return on Equity",
            "O&M Expenses",
            "Employee Cost",
            "Total ARR",
            "Expected Revenue (ERC)",
            "Revenue Gap / (Surplus)"
        ]
        
        print("\n=== Testing Known Patterns ===")
        for label in test_labels:
            result = normalize_row_label(label)
            print(f"'{label}' -> '{result.canonical_name}' (confidence: {result.confidence:.2f}, method: {result.method})")
        
        # Test normalization on first 20 extracted rows
        print("\n=== Testing Extracted Rows (first 20) ===")
        unique_labels = []
        for i, row in enumerate(extracted):
            if row.row_label not in unique_labels and len(unique_labels) < 20:
                unique_labels.append(row.row_label)
        
        for label in unique_labels:
            result = normalize_row_label(label)
            print(f"'{label}' -> '{result.canonical_name}' (confidence: {result.confidence:.2f}, category: {result.category})")
        
        # Analyze normalization success rate
        all_labels = [row.row_label for row in extracted]
        normalized_results = normalize_batch(all_labels)
        
        high_conf = sum(1 for r in normalized_results if r.confidence >= 0.8)
        med_conf = sum(1 for r in normalized_results if 0.6 <= r.confidence < 0.8)
        low_conf = sum(1 for r in normalized_results if r.confidence < 0.6)
        
        print(f"\n=== Normalization Confidence Distribution ===")
        print(f"High (>=0.8): {high_conf} ({high_conf/len(normalized_results)*100:.1f}%)")
        print(f"Medium (0.6-0.8): {med_conf} ({med_conf/len(normalized_results)*100:.1f}%)")
        print(f"Low (<0.6): {low_conf} ({low_conf/len(normalized_results)*100:.1f}%)")
        
        # Show unmapped items
        unmapped = [r for r in normalized_results if r.confidence < 0.6]
        if unmapped:
            print(f"\n=== Unmapped Items (confidence < 0.6) ===")
            for i, r in enumerate(unmapped[:10]):  # Show first 10
                print(f"{i+1}. '{r.canonical_name}' (from: '{all_labels[normalized_results.index(r)]}')")
        
    except Exception as e:
        print(f"Normalization test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_normalization()
