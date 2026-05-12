#!/usr/bin/env python3
"""
Test traceability and audit trail functionality
"""
import os
import sys
import sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_database_traceability():
    print("=== Testing Database Traceability ===")
    
    db_path = os.path.join(os.path.dirname(__file__), 'kserc_dss.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test 1: Check table relationships
    print("\n1. Testing Table Relationships:")
    
    # Documents to ExtractedRows
    cursor.execute("""
        SELECT d.filename, COUNT(er.id) as extracted_rows
        FROM documents d
        LEFT JOIN extracted_rows er ON d.id = er.document_id
        GROUP BY d.id
    """)
    doc_rows = cursor.fetchall()
    for filename, count in doc_rows:
        print(f"  Document '{filename}': {count} extracted rows")
    
    # ExtractedRows to NormalizedLineItems
    cursor.execute("""
        SELECT er.row_label, COUNT(nli.id) as normalized_items
        FROM extracted_rows er
        LEFT JOIN normalized_line_items nli ON er.id = nli.extracted_row_id
        GROUP BY er.id
        LIMIT 10
    """)
    norm_rows = cursor.fetchall()
    print(f"\n  Sample normalization mapping (first 10):")
    for row_label, count in norm_rows:
        print(f"    '{row_label}' -> {count} normalized items")
    
    # Test 2: Check audit fields
    print("\n2. Testing Audit Fields:")
    
    # Check timestamps
    tables_with_timestamps = ['documents', 'extracted_rows', 'comparisons', 'reviews', 'generated_orders', 'normalized_line_items']
    for table in tables_with_timestamps:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        timestamp_cols = [col for col in columns if 'time' in col.lower() or 'date' in col.lower()]
        print(f"  {table}: {timestamp_cols}")
    
    # Test 3: Check foreign key constraints
    print("\n3. Testing Foreign Key Constraints:")
    
    # Check if extracted_rows properly link to documents
    cursor.execute("""
        SELECT COUNT(*) as orphaned_rows
        FROM extracted_rows er
        LEFT JOIN documents d ON er.document_id = d.id
        WHERE d.id IS NULL
    """)
    orphaned = cursor.fetchone()[0]
    print(f"  Orphaned extracted_rows: {orphaned}")
    
    # Check if reviews properly link to comparisons
    cursor.execute("""
        SELECT COUNT(*) as orphaned_reviews
        FROM reviews r
        LEFT JOIN comparisons c ON r.comparison_id = c.id
        WHERE c.id IS NULL
    """)
    orphaned_reviews = cursor.fetchone()[0]
    print(f"  Orphaned reviews: {orphaned_reviews}")
    
    conn.close()

def test_provenance_tracking():
    print("\n=== Testing Provenance Tracking ===")
    
    db_path = os.path.join(os.path.dirname(__file__), 'kserc_dss.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test provenance fields in extracted_rows
    cursor.execute("SELECT page_number, table_name, confidence, extraction_method FROM extracted_rows LIMIT 5")
    provenance_samples = cursor.fetchall()
    
    print("Sample provenance data:")
    for i, (page, table, conf, method) in enumerate(provenance_samples, 1):
        print(f"  Row {i}: Page {page}, Table '{table}', Confidence {conf:.2f}, Method '{method}'")
    
    # Test source tracking in comparisons
    cursor.execute("""
        SELECT canonical_name, approved_source_page, actual_source_page 
        FROM comparisons 
        WHERE approved_source_page IS NOT NULL OR actual_source_page IS NOT NULL
        LIMIT 5
    """)
    source_tracking = cursor.fetchall()
    
    print(f"\nSource page tracking ({len(source_tracking)} items with source info):")
    for i, (name, approved_page, actual_page) in enumerate(source_tracking, 1):
        print(f"  {i}. {name}: Approved page {approved_page}, Actual page {actual_page}")
    
    conn.close()

def test_audit_trail_completeness():
    print("\n=== Testing Audit Trail Completeness ===")
    
    db_path = os.path.join(os.path.dirname(__file__), 'kserc_dss.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if all major entities have audit fields
    audit_checks = [
        ("documents", ["upload_timestamp", "status"]),
        ("extracted_rows", ["extracted_at", "confidence"]),
        ("normalized_line_items", ["created_at", "mapping_confidence"]),
        ("comparisons", ["created_at", "decision_class"]),
        ("reviews", ["reviewed_at", "officer_name"]),
        ("generated_orders", ["generated_at", "file_hash"])
    ]
    
    print("Audit field verification:")
    for table, expected_fields in audit_checks:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        missing_fields = [f for f in expected_fields if f not in columns]
        
        if missing_fields:
            print(f"  ✗ {table}: Missing {missing_fields}")
        else:
            print(f"  ✓ {table}: All audit fields present")
    
    # Test data integrity
    print("\nData integrity checks:")
    
    # Check for null critical fields
    cursor.execute("SELECT COUNT(*) FROM documents WHERE filename IS NULL")
    null_docs = cursor.fetchone()[0]
    print(f"  Documents with null filename: {null_docs}")
    
    cursor.execute("SELECT COUNT(*) FROM extracted_rows WHERE document_id IS NULL")
    null_extractions = cursor.fetchone()[0]
    print(f"  Extracted rows with null document_id: {null_extractions}")
    
    cursor.execute("SELECT COUNT(*) FROM comparisons WHERE case_id IS NULL")
    null_comparisons = cursor.fetchone()[0]
    print(f"  Comparisons with null case_id: {null_comparisons}")
    
    conn.close()

def test_end_to_end_traceability():
    print("\n=== Testing End-to-End Traceability ===")
    
    db_path = os.path.join(os.path.dirname(__file__), 'kserc_dss.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Trace a complete workflow: Document -> Extraction -> Normalization -> Comparison -> Review
    
    # Get a document
    cursor.execute("SELECT id, filename FROM documents LIMIT 1")
    doc_result = cursor.fetchone()
    if not doc_result:
        print("  No documents found in database")
        return
    
    doc_id, filename = doc_result
    print(f"  Tracing workflow for document: {filename}")
    
    # Get extracted rows for this document
    cursor.execute("""
        SELECT id, row_label, page_number, confidence 
        FROM extracted_rows 
        WHERE document_id = ? 
        LIMIT 3
    """, (doc_id,))
    extracted = cursor.fetchall()
    
    for ext_id, row_label, page, conf in extracted:
        print(f"    Extracted: '{row_label}' (Page {page}, Confidence {conf:.2f})")
        
        # Check if this was normalized
        cursor.execute("""
            SELECT canonical_name, mapping_confidence 
            FROM normalized_line_items 
            WHERE extracted_row_id = ?
        """, (ext_id,))
        normalized = cursor.fetchone()
        
        if normalized:
            canon_name, map_conf = normalized
            print(f"      Normalized to: '{canon_name}' (Confidence {map_conf:.2f})")
            
            # Check if this appears in comparisons
            cursor.execute("""
                SELECT id, variance, decision_class 
                FROM comparisons 
                WHERE canonical_name = ?
            """, (canon_name,))
            comparison = cursor.fetchone()
            
            if comparison:
                comp_id, variance, decision = comparison
                print(f"        Compared: Variance {variance}, Decision {decision}")
                
                # Check if reviewed
                cursor.execute("""
                    SELECT action, officer_name, reviewed_at 
                    FROM reviews 
                    WHERE comparison_id = ?
                """, (comp_id,))
                review = cursor.fetchone()
                
                if review:
                    action, officer, reviewed_at = review
                    print(f"          Reviewed: {action} by {officer} at {reviewed_at}")
                else:
                    print(f"          Not yet reviewed")
    
    conn.close()

if __name__ == "__main__":
    test_database_traceability()
    test_provenance_tracking()
    test_audit_trail_completeness()
    test_end_to_end_traceability()
