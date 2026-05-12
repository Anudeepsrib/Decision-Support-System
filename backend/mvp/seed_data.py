"""
MVP Demo Seed Data — Realistic KSERC financial data for demonstration.

Seeds the database with:
- Two documents (ARR Order + Truing-Up Petition)
- Extracted rows with provenance
- Normalized line items
- Pre-computed comparisons
- Sample reviews
"""

import uuid
from datetime import datetime
from backend.mvp.database import SessionLocal
from backend.mvp.models import (
    Document, ExtractedRow, NormalizedLineItem, Comparison, Review
)


# ─── Realistic KSERC Financial Data (FY 2024-25) ───
# Values in Rs. Crores — based on typical KSERC distribution SBU patterns

SEED_ARR_DATA = [
    {"canonical": "Power Purchase Cost",        "cost_head": "Power_Purchase", "approved": 12456.78, "actual": 14123.45},
    {"canonical": "Employee Cost",              "cost_head": "O&M",           "approved": 4567.12,  "actual": 4890.34},
    {"canonical": "Repair & Maintenance",       "cost_head": "O&M",           "approved": 892.45,   "actual": 945.67},
    {"canonical": "A&G Expenses",               "cost_head": "O&M",           "approved": 234.56,   "actual": 256.78},
    {"canonical": "Depreciation",               "cost_head": "Depreciation",  "approved": 1234.56,  "actual": 1289.01},
    {"canonical": "Interest & Finance Charges", "cost_head": "Interest",      "approved": 2345.67,  "actual": 2567.89},
    {"canonical": "Return on Equity",           "cost_head": "ROE",           "approved": 1567.89,  "actual": 1567.89},
    {"canonical": "Transmission Charges",       "cost_head": "Other",         "approved": 789.12,   "actual": 834.56},
    {"canonical": "Terminal Benefits",          "cost_head": "O&M",           "approved": 345.67,   "actual": 412.34},
    {"canonical": "Provision for Bad Debts",    "cost_head": "Other",         "approved": 123.45,   "actual": 145.67},
    {"canonical": "Total ARR",                  "cost_head": "Total",         "approved": 24557.27, "actual": 27033.60},
    {"canonical": "Revenue from Tariff",        "cost_head": "Revenue",       "approved": 18234.56, "actual": 17890.12},
    {"canonical": "Non-Tariff Income",          "cost_head": "Revenue",       "approved": 1234.56,  "actual": 1345.78},
    {"canonical": "Expected Revenue (ERC)",     "cost_head": "Revenue",       "approved": 19469.12, "actual": 19235.90},
    {"canonical": "Revenue Gap / (Surplus)",    "cost_head": "Gap",           "approved": 5088.15,  "actual": 7797.70},
]


def seed_demo_data():
    """Seed the database with demo data."""
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing = db.query(Document).first()
        if existing:
            print("[MVP Seed] Demo data already exists, skipping.")
            return
        
        print("[MVP Seed] Seeding demo data...")
        
        # ─── 1. Create Documents ───
        arr_doc_id = str(uuid.uuid4())
        petition_doc_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        
        arr_doc = Document(
            id=arr_doc_id,
            filename="KSERC_ARR_Order_2024-25.pdf",
            doc_type="arr_order",
            financial_year="2024-25",
            file_path="data/demo_arr_order.pdf",
            file_size=3797628,
            page_count=156,
            status="extracted",
        )
        
        petition_doc = Document(
            id=petition_doc_id,
            filename="KSEBL_TruingUp_Petition_2024-25.pdf",
            doc_type="truing_up_petition",
            financial_year="2024-25",
            file_path="data/demo_petition.pdf",
            file_size=287996,
            page_count=89,
            status="extracted",
        )
        
        db.add(arr_doc)
        db.add(petition_doc)
        
        # ─── 2. Create Extracted Rows ───
        for idx, item in enumerate(SEED_ARR_DATA):
            # ARR Order rows
            arr_row = ExtractedRow(
                id=str(uuid.uuid4()),
                document_id=arr_doc_id,
                page_number=45 + idx,
                table_index=0,
                table_name="ARR Summary — SBU-D",
                row_label=item["canonical"],
                value=item["approved"],
                confidence=0.92,
                extraction_method="pdfplumber",
                raw_text=f'{item["canonical"]} | {item["approved"]:,.2f}',
            )
            db.add(arr_row)
            
            # Petition rows
            pet_row = ExtractedRow(
                id=str(uuid.uuid4()),
                document_id=petition_doc_id,
                page_number=23 + idx,
                table_index=0,
                table_name="Truing-Up Summary — FY 2024-25",
                row_label=item["canonical"],
                value=item["actual"],
                confidence=0.88,
                extraction_method="pdfplumber",
                raw_text=f'{item["canonical"]} | {item["actual"]:,.2f}',
            )
            db.add(pet_row)
        
        # ─── 3. Create Normalized Line Items ───
        for item in SEED_ARR_DATA:
            # Approved item
            norm_approved = NormalizedLineItem(
                id=str(uuid.uuid4()),
                canonical_name=item["canonical"],
                category="ARR" if item["cost_head"] not in ("Revenue", "Gap") else ("ERC" if item["cost_head"] == "Revenue" else "Revenue_Gap"),
                cost_head=item["cost_head"],
                source_doc_type="arr_order",
                financial_year="2024-25",
                value=item["approved"],
                mapping_confidence=0.95,
                mapping_method="rule_based",
            )
            db.add(norm_approved)
            
            # Actual item
            norm_actual = NormalizedLineItem(
                id=str(uuid.uuid4()),
                canonical_name=item["canonical"],
                category="ARR" if item["cost_head"] not in ("Revenue", "Gap") else ("ERC" if item["cost_head"] == "Revenue" else "Revenue_Gap"),
                cost_head=item["cost_head"],
                source_doc_type="truing_up_petition",
                financial_year="2024-25",
                value=item["actual"],
                mapping_confidence=0.90,
                mapping_method="rule_based",
            )
            db.add(norm_actual)
        
        # ─── 4. Create Comparisons ───
        comparison_ids = []
        for item in SEED_ARR_DATA:
            approved = item["approved"]
            actual = item["actual"]
            variance = round(actual - approved, 2)
            variance_pct = round((actual - approved) / abs(approved) * 100, 2) if approved != 0 else 0.0
            
            # Classify
            if abs(variance_pct) < 15:
                decision_class = "AI_AUTO"
                flag_reason = None
            else:
                decision_class = "REVIEW_REQUIRED"
                direction = "increase" if variance_pct > 0 else "decrease"
                flag_reason = f"Variance of {variance_pct:+.1f}% ({direction}) exceeds 15% threshold"
            
            comp_id = str(uuid.uuid4())
            comparison_ids.append((comp_id, item["canonical"]))
            
            comp = Comparison(
                id=comp_id,
                case_id=case_id,
                financial_year="2024-25",
                canonical_name=item["canonical"],
                cost_head=item["cost_head"],
                approved_value=approved,
                actual_value=actual,
                claimed_value=actual,
                variance=variance,
                variance_percent=variance_pct,
                decision_class=decision_class,
                flag_reason=flag_reason,
                approved_source_page=45,
                actual_source_page=23,
            )
            db.add(comp)
        
        # ─── 5. Create Sample Reviews ───
        # Add reviews for some REVIEW_REQUIRED items
        for comp_id, canonical in comparison_ids:
            if canonical == "Power Purchase Cost":
                review = Review(
                    id=str(uuid.uuid4()),
                    comparison_id=comp_id,
                    action="approve",
                    officer_name="Shri R. Krishnakumar",
                    officer_comment="Increase justified due to hydrology shortfall and increased power purchase from central stations during peak demand.",
                    ai_explanation="The increase in power purchase cost is attributed to below-normal rainfall affecting hydro generation, necessitating increased thermal and spot market procurement.",
                )
                db.add(review)
            elif canonical == "Terminal Benefits":
                review = Review(
                    id=str(uuid.uuid4()),
                    comparison_id=comp_id,
                    action="edit",
                    officer_name="Shri R. Krishnakumar",
                    officer_comment="Partially approved — terminal benefits capped at 5% escalation over approved.",
                    edited_value=362.95,
                    ai_explanation="Terminal benefit claims exceed normative escalation. Commission may consider capping at regulatory norms.",
                )
                db.add(review)
        
        db.commit()
        print(f"[MVP Seed] Demo data seeded successfully. Case ID: {case_id}")
        
    except Exception as e:
        db.rollback()
        print(f"[MVP Seed] Error seeding demo data: {e}")
        raise
    finally:
        db.close()
