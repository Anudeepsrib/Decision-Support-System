#!/usr/bin/env python3
"""
Test extraction pipeline with sample PDFs
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from extractor import extract_tables_from_pdf, get_page_count

def test_extraction():
    # Check if we have any PDFs in mvp_uploads directory
    data_dir = os.path.join(os.path.dirname(__file__), 'mvp_uploads')
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
    
    print(f"Found {len(pdf_files)} PDF files in data directory:")
    for f in pdf_files:
        print(f"  - {f}")
    
    if not pdf_files:
        print("No PDF files found for testing extraction")
        return
    
    # Test extraction on first PDF
    test_file = os.path.join(data_dir, pdf_files[0])
    print(f"\nTesting extraction on: {pdf_files[0]}")
    
    try:
        with open(test_file, 'rb') as f:
            pdf_bytes = f.read()
        
        page_count = get_page_count(pdf_bytes)
        print(f"Page count: {page_count}")
        
        extracted = extract_tables_from_pdf(pdf_bytes, pdf_files[0])
        print(f"Extracted {len(extracted)} rows")
        
        # Show first few rows
        for i, row in enumerate(extracted[:5]):
            print(f"Row {i+1}: {row.row_label} = {row.value} (confidence: {row.confidence:.2f})")
        
        # Show confidence distribution
        high_conf = sum(1 for r in extracted if r.confidence >= 0.8)
        med_conf = sum(1 for r in extracted if 0.6 <= r.confidence < 0.8)
        low_conf = sum(1 for r in extracted if r.confidence < 0.6)
        
        print("\nConfidence distribution:")
        print(f"  High (>=0.8): {high_conf}")
        print(f"  Medium (0.6-0.8): {med_conf}")
        print(f"  Low (<0.6): {low_conf}")
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction()
