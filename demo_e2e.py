"""
End-to-End Demo Script for the ARR Truing-Up Decision Support System
====================================================================
Tests the full pipeline: Login → PDF Upload → Extraction → Mapping → Reports → Efficiency → History

Usage:
    1. Start the backend: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
    2. Run this script:   python demo_e2e.py
"""

import requests
import os
import sys
import json

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "Admin@12345678"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ═══════════════════════════════════════════════════════════
#  1. HEALTH CHECK
# ═══════════════════════════════════════════════════════════
section("1. Health Check")
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    test("GET /health returns 200", r.status_code == 200, f"got {r.status_code}")
except requests.ConnectionError:
    print("  ❌ Cannot connect to backend. Is the server running?")
    print(f"     Start it with: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════
#  2. AUTHENTICATION
# ═══════════════════════════════════════════════════════════
section("2. Authentication — Login as admin")
login_res = requests.post(f"{BASE_URL}/auth/login", data={
    "username": ADMIN_USER,
    "password": ADMIN_PASS,
})
test("POST /auth/login returns 200", login_res.status_code == 200, f"got {login_res.status_code}: {login_res.text[:200]}")

token = None
if login_res.status_code == 200:
    data = login_res.json()
    test("Login response has token", data.get("success") and data.get("token"), json.dumps(data)[:200])
    token = data["token"]["access_token"]

if not token:
    print("\n  ❌ Cannot continue without auth token. Aborting.")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Test profile
profile_res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
test("GET /auth/me returns admin profile", profile_res.status_code == 200, f"got {profile_res.status_code}")
if profile_res.status_code == 200:
    profile = profile_res.json()
    test("Profile has SUPER_ADMIN role", profile.get("role") == "super_admin", f"got {profile.get('role')}")


# ═══════════════════════════════════════════════════════════
#  3. PDF EXTRACTION — Upload both PDFs
# ═══════════════════════════════════════════════════════════
section("3. PDF Extraction — Upload sample PDFs")

pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".pdf")]
test(f"Found {len(pdf_files)} PDF(s) in data/", len(pdf_files) >= 1, f"files: {pdf_files}")

extraction_results = []
for pdf_name in pdf_files:
    pdf_path = os.path.join(DATA_DIR, pdf_name)
    with open(pdf_path, "rb") as f:
        upload_res = requests.post(
            f"{BASE_URL}/extract/upload",
            files={"file": (pdf_name, f, "application/pdf")},
            headers=headers,
            timeout=120,
        )
    
    test(f"Upload '{pdf_name}' returns 200", upload_res.status_code == 200, f"got {upload_res.status_code}: {upload_res.text[:300]}")
    
    if upload_res.status_code == 200:
        result = upload_res.json()
        n_fields = result.get("total_fields_extracted", 0)
        n_pages = result.get("total_pages_processed", 0)
        test(f"  Extracted {n_fields} fields from {n_pages} pages", n_fields > 0, f"fields={n_fields}")
        extraction_results.append(result)
        
        # Print extracted fields summary
        for field in result.get("fields", [])[:5]:
            val = field.get("extracted_value")
            name = field.get("field_name", "?")
            conf = field.get("confidence_score", 0)
            page = field.get("source_page", "?")
            val_str = f"₹{val:,.2f}" if val else "N/A"
            review = " ⚠️ REVIEW" if field.get("review_required") else ""
            print(f"       • {name}: {val_str} (conf={conf:.0%}, page={page}){review}")
        if len(result.get("fields", [])) > 5:
            print(f"       ... and {len(result['fields']) - 5} more fields")


# ═══════════════════════════════════════════════════════════
#  4. MAPPING WORKBENCH
# ═══════════════════════════════════════════════════════════
section("4. Mapping Workbench — Review AI Suggestions")

pending_res = requests.get(f"{BASE_URL}/mapping/pending", headers=headers)
test("GET /mapping/pending returns 200", pending_res.status_code == 200, f"got {pending_res.status_code}")

if pending_res.status_code == 200:
    pending = pending_res.json()
    test(f"Found {len(pending)} pending mappings", len(pending) > 0, "no pending mappings")
    
    # Confirm first 3 mappings
    confirmed = 0
    for m in pending[:3]:
        confirm_res = requests.post(f"{BASE_URL}/mapping/confirm", json={
            "mapping_id": m["mapping_id"],
            "decision": "Confirmed",
            "comment": "AI suggestion verified and accepted for demo",
            "officer_name": "System Administrator",
        }, headers=headers)
        if confirm_res.status_code == 200:
            confirmed += 1
    
    test(f"Confirmed {confirmed} mappings", confirmed > 0, "could not confirm any")


# ═══════════════════════════════════════════════════════════
#  5. ANALYTICAL REPORTS
# ═══════════════════════════════════════════════════════════
section("5. Analytical Reports")

report_res = requests.get(f"{BASE_URL}/reports/analytical?financial_year=2024-25", headers=headers)
test("GET /reports/analytical returns 200", report_res.status_code == 200, f"got {report_res.status_code}: {report_res.text[:300]}")

if report_res.status_code == 200:
    report = report_res.json()
    summary = report.get("preliminary_summary", {})
    test("Report has cost head analysis", summary.get("total_cost_heads_analyzed", 0) > 0,
         f"heads={summary.get('total_cost_heads_analyzed')}")
    test("Report has variance analysis", len(report.get("variance_analysis", [])) > 0,
         f"count={len(report.get('variance_analysis', []))}")
    test("Report has insights", len(report.get("insights", [])) > 0,
         f"count={len(report.get('insights', []))}")
    
    print(f"\n       📊 Report Summary:")
    print(f"          Total Approved ARR: ₹{summary.get('total_approved_arr', 0):,.2f}")
    print(f"          Total Actual ARR:   ₹{summary.get('total_actual_arr', 0):,.2f}")
    print(f"          Net Variance:       ₹{summary.get('net_variance', 0):,.2f}")
    print(f"          Anomalies Flagged:  {report.get('anomaly_count', 0)}")

# SBU Summary
sbu_res = requests.get(f"{BASE_URL}/reports/sbu-summary?financial_year=2024-25", headers=headers)
test("GET /reports/sbu-summary returns 200", sbu_res.status_code == 200, f"got {sbu_res.status_code}")
if sbu_res.status_code == 200:
    sbus = sbu_res.json()
    test(f"SBU summary has {len(sbus)} entries", len(sbus) > 0, "empty")


# ═══════════════════════════════════════════════════════════
#  6. EFFICIENCY ANALYSIS
# ═══════════════════════════════════════════════════════════
section("6. Efficiency Analysis — Line Loss Evaluation")

eff_res = requests.post(f"{BASE_URL}/efficiency/line-loss", json={
    "financial_year": "2024-25",
    "actual_line_loss_percent": 12.5,
}, headers=headers)
test("POST /efficiency/line-loss returns 200", eff_res.status_code == 200, f"got {eff_res.status_code}: {eff_res.text[:200]}")

if eff_res.status_code == 200:
    eff = eff_res.json()
    test(f"Target: {eff.get('target_loss_percent')}%, Actual: {eff.get('actual_loss_percent')}%",
         eff.get("target_loss_percent") is not None, "missing data")
    violation_status = "VIOLATION ⚠️" if eff.get("is_violation") else "COMPLIANT ✅"
    print(f"       Status: {violation_status}")
    print(f"       Logic: {eff.get('logic_applied', '')[:100]}")


# ═══════════════════════════════════════════════════════════
#  7. HISTORICAL TRENDS
# ═══════════════════════════════════════════════════════════
section("7. Historical Trends")

hist_res = requests.get(f"{BASE_URL}/history/trends", headers=headers)
test("GET /history/trends returns 200", hist_res.status_code == 200, f"got {hist_res.status_code}")

if hist_res.status_code == 200:
    trends = hist_res.json()
    test(f"Historical data has {len(trends)} years", len(trends) >= 3, f"got {len(trends)}")
    for t in trends[:3]:
        print(f"       {t['financial_year']}: ARR ₹{t['total_actual_arr']:,.0f}, Gap ₹{t['revenue_gap']:,.0f}, Loss {t['line_loss_percent']}%")


# ═══════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  DEMO RESULTS: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print(f"  ALL TESTS PASSED ✅")
else:
    print(f"  SOME TESTS FAILED ❌")
print(f"{'═'*60}\n")

sys.exit(0 if failed == 0 else 1)
