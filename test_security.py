#!/usr/bin/env python3
"""
Test security and stability aspects
"""
import requests
import os
import tempfile

API_BASE = "http://localhost:8000/api"

def test_file_upload_security():
    print("=== Testing File Upload Security ===")
    
    # Test 1: File size limits
    print("\n1. Testing file size validation:")
    
    # Create a large test file (>50MB)
    large_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    large_file.write(b'0' * (51 * 1024 * 1024))  # 51MB
    large_file.close()
    
    try:
        with open(large_file.name, 'rb') as f:
            files = {'file': (large_file.name, f, 'application/pdf')}
            response = requests.post(f"{API_BASE}/documents/upload", files=files)
        
        if response.status_code == 413:
            print("  ✓ File size limit enforced (413)")
        else:
            print(f"  ✗ File size limit not enforced: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Upload test failed: {e}")
    finally:
        os.unlink(large_file.name)
    
    # Test 2: File type validation
    print("\n2. Testing file type validation:")
    
    # Create a non-PDF file with .pdf extension
    fake_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, mode='w')
    fake_pdf.write("This is not a PDF file")
    fake_pdf.close()
    
    try:
        with open(fake_pdf.name, 'rb') as f:
            files = {'file': (fake_pdf.name, f, 'application/pdf')}
            response = requests.post(f"{API_BASE}/documents/upload", files=files)
        
        if response.status_code == 400:
            print("  ✓ File type validation enforced (400)")
        else:
            print(f"  ✗ File type validation not enforced: {response.status_code}")
    except Exception as e:
        print(f"  ✗ File type test failed: {e}")
    finally:
        os.unlink(fake_pdf.name)
    
    # Test 3: Empty file handling
    print("\n3. Testing empty file handling:")
    
    empty_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    empty_file.close()
    
    try:
        with open(empty_file.name, 'rb') as f:
            files = {'file': (empty_file.name, f, 'application/pdf')}
            response = requests.post(f"{API_BASE}/documents/upload", files=files)
        
        print(f"  Empty file response: {response.status_code}")
        if response.status_code in [400, 422]:
            print("  ✓ Empty file properly rejected")
        else:
            print("  ✗ Empty file not properly handled")
    except Exception as e:
        print(f"  ✗ Empty file test failed: {e}")
    finally:
        os.unlink(empty_file.name)

def test_api_error_handling():
    print("\n=== Testing API Error Handling ===")
    
    # Test 1: Invalid document ID
    print("\n1. Testing invalid document ID:")
    response = requests.get(f"{API_BASE}/extraction/invalid-id-123")
    print(f"  Invalid document ID response: {response.status_code}")
    if response.status_code == 404:
        print("  ✓ Proper 404 response")
    else:
        print("  ✗ Invalid ID not properly handled")
    
    # Test 2: Invalid comparison ID
    print("\n2. Testing invalid comparison ID:")
    response = requests.post(f"{API_BASE}/review/invalid-comparison-123", json={"action": "approve"})
    print(f"  Invalid comparison ID response: {response.status_code}")
    if response.status_code == 404:
        print("  ✓ Proper 404 response")
    else:
        print("  ✗ Invalid comparison ID not properly handled")
    
    # Test 3: Invalid review action
    print("\n3. Testing invalid review action:")
    response = requests.post(f"{API_BASE}/review/some-id", json={"action": "invalid-action"})
    print(f"  Invalid action response: {response.status_code}")
    if response.status_code == 400:
        print("  ✓ Proper 400 response")
    else:
        print("  ✗ Invalid action not properly handled")
    
    # Test 4: Missing required fields
    print("\n4. Testing missing required fields:")
    response = requests.post(f"{API_BASE}/generate", json={})
    print(f"  Missing fields response: {response.status_code}")
    if response.status_code in [400, 422]:
        print("  ✓ Proper validation response")
    else:
        print("  ✗ Missing fields not properly validated")

def test_input_validation():
    print("\n=== Testing Input Validation ===")
    
    # Test SQL injection attempts
    print("\n1. Testing SQL injection protection:")
    
    malicious_ids = [
        "'; DROP TABLE documents; --",
        "1' OR '1'='1",
        "1 UNION SELECT * FROM documents --"
    ]
    
    for mal_id in malicious_ids:
        response = requests.get(f"{API_BASE}/extraction/{mal_id}")
        if response.status_code == 404:
            print(f"  ✓ SQL injection blocked: {mal_id[:20]}...")
        else:
            print(f"  ✗ SQL injection not blocked: {mal_id[:20]}...")
    
    # Test XSS attempts
    print("\n2. Testing XSS protection:")
    
    xss_payload = "<script>alert('xss')</script>"
    response = requests.post(f"{API_BASE}/documents/upload", 
                          data={'doc_type': xss_payload})
    print(f"  XSS payload response: {response.status_code}")
    if response.status_code in [400, 422]:
        print("  ✓ XSS payload properly rejected")
    else:
        print("  ✗ XSS payload not properly handled")

def test_concurrent_requests():
    print("\n=== Testing Concurrent Request Handling ===")
    
    import threading
    import time
    
    results = []
    
    def make_request():
        try:
            start_time = time.time()
            response = requests.get(f"{API_BASE}/documents", timeout=10)
            end_time = time.time()
            results.append({
                'status': response.status_code,
                'time': end_time - start_time,
                'success': response.status_code == 200
            })
        except Exception as e:
            results.append({
                'status': 'error',
                'time': 0,
                'success': False,
                'error': str(e)
            })
    
    # Launch 10 concurrent requests
    threads = []
    for i in range(10):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Analyze results
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    avg_time = sum(r['time'] for r in results if 'time' in r) / len(results)
    
    print(f"  Concurrent requests: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Average response time: {avg_time:.2f}s")
    
    if successful >= 8:  # At least 80% success
        print("  ✓ Concurrent handling is stable")
    else:
        print("  ✗ Concurrent handling has issues")

def test_backend_stability():
    print("\n=== Testing Backend Stability ===")
    
    # Test backend health
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("  ✓ Backend health endpoint responding")
        else:
            print(f"  ✗ Health endpoint issue: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Backend not accessible: {e}")
    
    # Test API documentation
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        if response.status_code == 200:
            print("  ✓ API documentation accessible")
        else:
            print(f"  ✗ Documentation issue: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Documentation not accessible: {e}")
    
    # Test memory usage (basic check)
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        print(f"  Memory usage: {memory_mb:.1f} MB")
        if memory_mb < 500:  # Less than 500MB is reasonable
            print("  ✓ Memory usage is reasonable")
        else:
            print("  ⚠ Memory usage is high")
    except ImportError:
        print("  psutil not available - skipping memory check")
    except Exception as e:
        print(f"  Memory check failed: {e}")

if __name__ == "__main__":
    test_file_upload_security()
    test_api_error_handling()
    test_input_validation()
    test_concurrent_requests()
    test_backend_stability()
