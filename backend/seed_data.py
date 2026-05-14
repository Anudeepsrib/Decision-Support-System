"""
Local demo seed data for the KSERC DSS MVP.

This is optional. The primary workflow is still upload ARR and Petition PDFs,
but seed data gives developers a quick way to verify comparison and report
generation without hunting for documents first.
"""

from __future__ import annotations

import uuid

try:
    from .database import SessionLocal
    from .models import (
        Comparison,
        Document,
        ExtractedRow,
        GeneratedOrder,
        NormalizedLineItem,
        Review,
    )
except ImportError:  # Support direct imports from the backend directory.
    from database import SessionLocal
    from models import (
        Comparison,
        Document,
        ExtractedRow,
        GeneratedOrder,
        NormalizedLineItem,
        Review,
    )


CASE_ID = "kserc-2024-25"

SEED_ARR_DATA = [
    {"canonical_id": "PURCHASE_OF_POWER", "canonical": "Purchase of Power", "cost_head": "SBU-D", "section": "sbu_d", "approved": 12456.78, "actual": 14123.45},
    {"canonical_id": "OM_COST", "canonical": "O&M Cost", "cost_head": "SBU-D", "section": "sbu_d", "approved": 5694.13, "actual": 6092.79},
    {"canonical_id": "DEPRECIATION", "canonical": "Depreciation", "cost_head": "SBU-D", "section": "sbu_d", "approved": 1234.56, "actual": 1289.01},
    {"canonical_id": "INTEREST_FINANCE_CHARGES", "canonical": "Interest and Finance Charges", "cost_head": "SBU-D", "section": "sbu_d", "approved": 2345.67, "actual": 2567.89},
    {"canonical_id": "ROE", "canonical": "Return on Equity", "cost_head": "SBU-D", "section": "sbu_d", "approved": 1567.89, "actual": 1567.89},
    {"canonical_id": "NET_EXPENDITURE", "canonical": "Net Expenditure", "cost_head": "SBU-D", "section": "sbu_d", "approved": 24557.27, "actual": 27033.60},
    {"canonical_id": "REVENUE_FROM_TARIFF_EXTERNAL_SALE", "canonical": "Revenue from Tariff and External Sale", "cost_head": "SBU-D", "section": "sbu_d", "approved": 18234.56, "actual": 17890.12},
    {"canonical_id": "NON_TARIFF_INCOME", "canonical": "Non-Tariff Income", "cost_head": "SBU-D", "section": "sbu_d", "approved": 1234.56, "actual": 1345.78},
    {"canonical_id": "TOTAL_INCOME", "canonical": "Total Income", "cost_head": "SBU-D", "section": "sbu_d", "approved": 19469.12, "actual": 19235.90},
    {"canonical_id": "REVENUE_SURPLUS_GAP", "canonical": "Revenue Surplus / Gap", "cost_head": "SBU-D", "section": "sbu_d", "approved": 5088.15, "actual": 7797.70},
]


def _category(cost_head: str) -> str:
    if cost_head == "Revenue":
        return "ERC"
    if cost_head == "Gap":
        return "Revenue_Gap"
    return "ARR"


def _clear_demo_data(db) -> None:
    db.query(GeneratedOrder).delete(synchronize_session=False)
    db.query(Review).delete(synchronize_session=False)
    db.query(Comparison).delete(synchronize_session=False)
    db.query(NormalizedLineItem).delete(synchronize_session=False)
    db.query(ExtractedRow).delete(synchronize_session=False)
    db.query(Document).delete(synchronize_session=False)
    db.commit()


def seed_demo_data(clear: bool = False) -> str:
    """Seed deterministic local demo data and return the case id."""
    db = SessionLocal()

    try:
        if clear:
            _clear_demo_data(db)
        elif db.query(Comparison).filter(Comparison.case_id == CASE_ID).first():
            print(f"[MVP Seed] Demo comparison already exists. Case ID: {CASE_ID}")
            return CASE_ID

        print("[MVP Seed] Seeding demo data...")

        arr_doc_id = str(uuid.uuid4())
        petition_doc_id = str(uuid.uuid4())

        db.add(Document(
            id=arr_doc_id,
            filename="KSERC_ARR_Order_2024-25_demo.pdf",
            doc_type="arr_order",
            financial_year="2024-25",
            file_path="demo://arr-order",
            file_size=3797628,
            page_count=156,
            status="extracted",
        ))
        db.add(Document(
            id=petition_doc_id,
            filename="KSEBL_TruingUp_Petition_2024-25_demo.pdf",
            doc_type="truing_up_petition",
            financial_year="2024-25",
            file_path="demo://petition",
            file_size=287996,
            page_count=89,
            status="extracted",
        ))

        comparison_ids: list[tuple[str, str]] = []

        for idx, item in enumerate(SEED_ARR_DATA):
            arr_row_id = str(uuid.uuid4())
            petition_actual_row_id = str(uuid.uuid4())
            petition_claimed_row_id = str(uuid.uuid4())

            db.add(ExtractedRow(
                id=arr_row_id,
                document_id=arr_doc_id,
                page_number=45 + idx,
                table_index=0,
                table_name="ARR Summary - SBU-D",
                row_label=item["canonical"],
                value=item["approved"],
                value_type="approved",
                confidence=0.92,
                extraction_method="seed",
                raw_text=f'{item["canonical"]} | {item["approved"]:,.2f}',
            ))
            db.add(ExtractedRow(
                id=petition_actual_row_id,
                document_id=petition_doc_id,
                page_number=23 + idx,
                table_index=0,
                table_name="Truing-Up Actuals - FY 2024-25",
                row_label=item["canonical"],
                value=item["actual"],
                value_type="actual",
                confidence=0.88,
                extraction_method="seed",
                raw_text=f'{item["canonical"]} | actual | {item["actual"]:,.2f}',
            ))
            db.add(ExtractedRow(
                id=petition_claimed_row_id,
                document_id=petition_doc_id,
                page_number=24 + idx,
                table_index=1,
                table_name="Truing-Up Claimed - FY 2024-25",
                row_label=item["canonical"],
                value=item["actual"],
                value_type="claimed",
                confidence=0.86,
                extraction_method="seed",
                raw_text=f'{item["canonical"]} | claimed | {item["actual"]:,.2f}',
            ))

            for row_id, doc_type, value_type, value, confidence in (
                (arr_row_id, "arr_order", "approved", item["approved"], 0.95),
                (petition_actual_row_id, "truing_up_petition", "actual", item["actual"], 0.90),
                (petition_claimed_row_id, "truing_up_petition", "claimed", item["actual"], 0.88),
            ):
                db.add(NormalizedLineItem(
                    id=str(uuid.uuid4()),
                    extracted_row_id=row_id,
                    canonical_name=item["canonical"],
                    category=_category(item["cost_head"]),
                    cost_head=item["cost_head"],
                    source_doc_type=doc_type,
                    financial_year="2024-25",
                    value_type=value_type,
                    value=value,
                    mapping_confidence=confidence,
                    mapping_method="seed",
                ))

            approved = item["approved"]
            actual = item["actual"]
            variance = round(actual - approved, 2)
            variance_pct = round((actual - approved) / abs(approved) * 100, 2) if approved else 0.0
            if abs(variance_pct) < 15:
                decision_class = "ACCEPTABLE_VARIANCE"
                flag_reason = None
            else:
                decision_class = "REVIEW_REQUIRED"
                direction = "increase" if variance_pct > 0 else "decrease"
                flag_reason = f"Variance of {variance_pct:+.1f}% ({direction}) exceeds 15.0% threshold"

            comp_id = str(uuid.uuid4())
            comparison_ids.append((comp_id, item["canonical"]))
            db.add(Comparison(
                id=comp_id,
                case_id=CASE_ID,
                financial_year="2024-25",
                canonical_id=item["canonical_id"],
                canonical_name=item["canonical"],
                display_name=item["canonical"],
                sbu=item["cost_head"],
                unit="Rs. Cr.",
                section=item["section"],
                cost_head=item["cost_head"],
                approved_value=approved,
                actual_value=actual,
                claimed_value=actual,
                variance=variance,
                variance_percent=variance_pct,
                decision_class=decision_class,
                flag_reason=flag_reason,
                approved_source_document_id=arr_doc_id,
                actual_source_document_id=petition_doc_id,
                claimed_source_document_id=petition_doc_id,
                approved_source_page=45 + idx,
                actual_source_page=23 + idx,
                claimed_source_page=24 + idx,
                approved_source_table="ARR Summary - SBU-D",
                actual_source_table="Truing-Up Actuals - FY 2024-25",
                claimed_source_table="Truing-Up Claimed - FY 2024-25",
                approved_confidence=0.92,
                actual_confidence=0.88,
                claimed_confidence=0.86,
            ))

        for comp_id, canonical in comparison_ids:
            if canonical == "Purchase of Power":
                db.add(Review(
                    id=str(uuid.uuid4()),
                    comparison_id=comp_id,
                    action="approve",
                    officer_name="Demo Officer",
                    officer_comment="Increase noted for demo review of power purchase cost.",
                    ai_explanation="The item is marked for deterministic officer review based on variance from approved values.",
                ))

        db.commit()
        print(f"[MVP Seed] Demo data seeded successfully. Case ID: {CASE_ID}")
        return CASE_ID

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
