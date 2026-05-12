#!/usr/bin/env python3
"""
Test human review workflow via API
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def test_review_workflow():
    print("=== Testing Review Workflow API ===")
    
    # 1. Check if backend is running
    try:
        response = requests.get(f"{API_BASE}/documents")
        print(f"Backend status: {response.status_code}")
        if response.status_code != 200:
            print("Backend not accessible - cannot test review workflow")
            return
    except Exception as e:
        print(f"Cannot connect to backend: {e}")
        return
    
    # 2. Get existing documents
    docs_response = requests.get(f"{API_BASE}/documents")
    if docs_response.status_code == 200:
        documents = docs_response.json()
        print(f"Found {len(documents)} documents in system")
        for doc in documents:
            print(f"  - {doc['filename']} ({doc['doc_type']})")
    
    # 3. Get comparison cases
    comparison_response = requests.get(f"{API_BASE}/comparison")
    if comparison_response.status_code == 200:
        cases = comparison_response.json()
        print(f"Found {len(cases)} comparison cases")
        for case in cases:
            print(f"  Case {case['case_id']}: {case['total_items']} items, {case['review_required']} need review")
    
    # 4. Test review submission (mock)
    if cases:
        test_case = cases[0]
        if test_case['items']:
            test_item = test_case['items'][0]
            comparison_id = test_item['id']
            
            review_data = {
                "action": "approve",
                "officer_name": "Test Officer",
                "officer_comment": "Approved during QA testing"
            }
            
            print(f"\nSubmitting review for item {comparison_id}")
            review_response = requests.post(
                f"{API_BASE}/review/{comparison_id}",
                json=review_data
            )
            
            if review_response.status_code == 200:
                review_result = review_response.json()
                print(f"Review submitted successfully:")
                print(f"  Action: {review_result['action']}")
                print(f"  Officer: {review_result['officer_name']}")
                print(f"  Comment: {review_result['officer_comment']}")
            else:
                print(f"Review submission failed: {review_response.status_code}")
                print(f"Error: {review_response.text}")
    
    # 5. Test PDF generation
    if cases:
        generate_data = {
            "case_id": test_case['case_id'],
            "financial_year": "2024-25",
            "officer_name": "Test Officer"
        }
        
        print(f"\nTesting PDF generation for case {test_case['case_id']}")
        generate_response = requests.post(
            f"{API_BASE}/generate",
            json=generate_data
        )
        
        if generate_response.status_code == 200:
            order_result = generate_response.json()
            print(f"PDF generation initiated:")
            print(f"  Order ID: {order_result['id']}")
            print(f"  File path: {order_result['file_path']}")
            print(f"  File size: {order_result['file_size']} bytes")
            print(f"  Download URL: {order_result['download_url']}")
        else:
            print(f"PDF generation failed: {generate_response.status_code}")
            print(f"Error: {generate_response.text}")

def test_api_endpoints():
    """Test all API endpoints for basic functionality"""
    print("\n=== Testing API Endpoints ===")
    
    endpoints = [
        ("/", "GET"),
        ("/health", "GET"),
        ("/documents", "GET"),
        ("/comparison", "GET"),
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{API_BASE}{endpoint}")
            print(f"{method} {endpoint}: {response.status_code}")
            if response.status_code != 200:
                print(f"  Error: {response.text[:200]}")
        except Exception as e:
            print(f"{method} {endpoint}: FAILED - {e}")

if __name__ == "__main__":
    test_api_endpoints()
    test_review_workflow()
