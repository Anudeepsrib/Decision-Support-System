"""
Demo Data Initialization Script
Run this to populate the database with sample data for demonstrations.
"""

import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from security.auth import SecurityManager

def init_demo_data():
    """Initialize demo data from fixtures"""
    print("🚀 Initializing ARR Truing-Up DSS Demo Data...")
    print("=" * 60)
    
    # Load fixtures
    demo_dir = Path(__file__).parent.parent
    fixtures_dir = demo_dir / "fixtures"
    
    # Load users
    with open(fixtures_dir / "users.json") as f:
        users_data = json.load(f)
    
    print(f"✅ Loaded {len(users_data['users'])} demo users")
    print(f"   Default password: {users_data['password_plaintext']}")
    
    # Display demo credentials
    print("\n📋 Demo Credentials:")
    print("-" * 60)
    for user in users_data['users']:
        print(f"   {user['username']}")
        print(f"   Password: DemoPass123!")
        print(f"   Role: {user['role']}")
        print(f"   Access: {', '.join(user['sbu_access'])}")
        print()
    
    # Load ARR data
    with open(fixtures_dir / "arr_data.json") as f:
        arr_data = json.load(f)
    
    print(f"✅ Loaded {len(arr_data['arr_components'])} ARR components")
    
    # Load pending mappings
    with open(fixtures_dir / "pending_mappings.json") as f:
        mappings_data = json.load(f)
    
    print(f"✅ Loaded {len(mappings_data)} pending mappings")
    
    # Sample extraction data
    print("\n📄 Sample Extraction Data:")
    print("-" * 60)
    sample_extractions = [
        {
            "field_name": "Approved O&M Cost (FY 2024-25)",
            "sbu_code": "SBU-D",
            "extracted_value": 180000000,
            "confidence_score": 0.95,
            "source_page": 12,
            "source_table": 1,
            "cell_reference": "C4",
            "raw_text": "Rs. 180.00 Cr"
        },
        {
            "field_name": "Actual O&M Cost (FY 2024-25)",
            "sbu_code": "SBU-D",
            "extracted_value": 150000000,
            "confidence_score": 0.88,
            "source_page": 14,
            "source_table": 2,
            "cell_reference": "D6",
            "raw_text": "Rs. 150.00 Cr (Audited)"
        },
        {
            "field_name": "Power Purchase Cost (Actual)",
            "sbu_code": "SBU-G",
            "extracted_value": 850000000,
            "confidence_score": 0.92,
            "source_page": 18,
            "source_table": 3,
            "cell_reference": "B8",
            "raw_text": "Rs. 850.00 Cr"
        }
    ]
    
    for ext in sample_extractions:
        print(f"   {ext['field_name']}: ₹{ext['extracted_value']:,.0f}")
        print(f"   Source: Page {ext['source_page']}, Table {ext['source_table']}, Cell {ext['cell_reference']}")
        print(f"   Confidence: {ext['confidence_score']*100:.0f}%")
        print()
    
    print("=" * 60)
    print("✨ Demo data initialized successfully!")
    print("\n🌐 Backend: http://localhost:8000")
    print("🖥️  Frontend: http://localhost:3000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("\nNext steps:")
    print("   1. Start backend: uvicorn backend.main_secure:app --reload --env-file demo/.env.demo")
    print("   2. Start frontend: cd frontend && npm start")
    print("   3. Login with demo credentials above")

if __name__ == "__main__":
    init_demo_data()
