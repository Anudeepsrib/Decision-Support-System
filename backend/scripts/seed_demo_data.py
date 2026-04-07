"""
Demo Data Seeding Script — KSERC Truing-Up AI Decision Support System.

Seeds the database with sample data for demo mode:
- 1 sample case
- Petition + ARR parsed data
- Deviation reports (line items)
- AI decisions

Usage:
    python -m backend.scripts.seed_demo_data

Or run on startup (if DEMO_MODE=true):
    from backend.scripts.seed_demo_data import seed_demo_data_if_needed
    seed_demo_data_if_needed()
"""

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from sqlalchemy.orm import Session
from backend.models.database import SessionLocal, engine
from backend.models.schema import (
    PetitionData, SBUType, DeviationReport, CostHead, AIDecision,
    DecisionType, DecisionMode, ExternalFactorCategory
)
from backend.config.settings import is_demo_mode, get_settings


# ─── Demo Data Constants ───

DEMO_CASE_ID = "demo-case-001"
DEMO_FINANCIAL_YEAR = "2024-25"
DEMO_SBU_CODE = SBUType.SBU_DISTRIBUTION

# Sample cost heads for demo
DEMO_LINE_ITEMS = [
    {
        "cost_head": CostHead.POWER_PURCHASE_COST,
        "petition_value": 8500.0,
        "approved_value": 8200.0,
        "actual_value": 8750.0,
        "category": "Uncontrollable"
    },
    {
        "cost_head": CostHead.OPERATION_AND_MAINTENANCE,
        "petition_value": 1200.0,
        "approved_value": 1100.0,
        "actual_value": 1250.0,
        "category": "Controllable"
    },
    {
        "cost_head": CostHead.DEPRECIATION,
        "petition_value": 950.0,
        "approved_value": 900.0,
        "actual_value": 920.0,
        "category": "Controllable"
    },
    {
        "cost_head": CostHead.INTEREST_AND_FINANCE_CHARGES,
        "petition_value": 450.0,
        "approved_value": 420.0,
        "actual_value": 440.0,
        "category": "Uncontrollable"
    },
    {
        "cost_head": CostHead.RETURN_ON_EQUITY,
        "petition_value": 680.0,
        "approved_value": 650.0,
        "actual_value": 660.0,
        "category": "Controllable"
    }
]


def create_demo_case(db: Session) -> PetitionData:
    """Create or get the demo case."""
    # Check if demo case already exists
    existing = db.query(PetitionData).filter(
        PetitionData.id == DEMO_CASE_ID
    ).first()
    
    if existing:
        print(f"Demo case already exists: {existing.id}")
        return existing
    
    # Create new demo case
    case = PetitionData(
        id=DEMO_CASE_ID,
        sbu_code=DEMO_SBU_CODE,
        financial_year=DEMO_FINANCIAL_YEAR,
        petition_number="PTN/DEMO/2024/001",
        utility_name="Kerala State Electricity Board Ltd. (KSEBL)",
        filing_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
        total_arr_claimed=11780.0,
        approved_arr=11270.0,
        claimed_arr=11780.0,
        claimed_revenue_gap=510.0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(case)
    db.commit()
    db.refresh(case)
    
    print(f"Created demo case: {case.id}")
    return case


def create_deviation_reports(db: Session, case_id: str) -> list:
    """Create deviation reports (line items) for demo case."""
    reports = []
    
    for item in DEMO_LINE_ITEMS:
        # Check if already exists
        existing = db.query(DeviationReport).filter(
            DeviationReport.case_id == case_id,
            DeviationReport.cost_head == item["cost_head"]
        ).first()
        
        if existing:
            reports.append(existing)
            continue
        
        # Calculate variance
        variance = item["actual_value"] - item["approved_value"]
        variance_percent = (variance / item["approved_value"]) * 100 if item["approved_value"] else 0
        
        report = DeviationReport(
            id=str(uuid4()),
            case_id=case_id,
            sbu_code=DEMO_SBU_CODE,
            cost_head=item["cost_head"],
            financial_year=DEMO_FINANCIAL_YEAR,
            petition_value=item["petition_value"],
            approved_value=item["approved_value"],
            actual_value=item["actual_value"],
            variance_value=variance,
            variance_percent=abs(variance_percent),
            category=item["category"],
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(report)
        reports.append(report)
    
    db.commit()
    print(f"Created {len(reports)} deviation reports")
    return reports


def create_ai_decisions(db: Session, reports: list) -> list:
    """Create AI decisions for deviation reports."""
    decisions = []
    
    for report in reports:
        # Check if AI decision already exists
        existing = db.query(AIDecision).filter(
            AIDecision.deviation_report_id == report.id
        ).first()
        
        if existing:
            decisions.append(existing)
            continue
        
        # Determine AI recommendation based on variance
        if report.variance_value > 0:
            recommendation = DecisionType.DISALLOW  # Overrun
        elif report.variance_value < 0:
            recommendation = DecisionType.APPROVE  # Savings
        else:
            recommendation = DecisionType.APPROVE
        
        # Determine decision mode based on thresholds
        variance_high = report.variance_percent > 25.0
        is_controllable = report.category == "Controllable"
        
        if variance_high and is_controllable:
            decision_mode = DecisionMode.PENDING_MANUAL
            confidence = 0.75
        else:
            decision_mode = DecisionMode.AI_AUTO
            confidence = 0.92
        
        # Generate justification
        if recommendation == DecisionType.DISALLOW:
            justification = (
                f"Approved {report.cost_head.value}: ₹{report.approved_value:,.2f} "
                f"vs Actual: ₹{report.actual_value:,.2f}. "
                f"Variance of {report.variance_percent:.1f}% exceeds threshold. "
                f"AI recommends DISALLOWANCE per Regulation 9.3 for controllable losses."
            )
        elif recommendation == DecisionType.PARTIAL:
            justification = (
                f"Partial approval recommended for {report.cost_head.value} "
                f"due to variance of {report.variance_percent:.1f}%. "
                f"Further documentation required."
            )
        else:
            justification = (
                f"Approved {report.cost_head.value}: ₹{report.approved_value:,.2f} "
                f"vs Actual: ₹{report.actual_value:,.2f}. "
                f"AI recommends FULL APPROVAL based on variance within acceptable limits."
            )
        
        # Get regulatory clause
        if is_controllable:
            if recommendation == DecisionType.APPROVE:
                regulatory_clause = "Regulation 9.2 — Controllable Gains Sharing"
            else:
                regulatory_clause = "Regulation 9.3 — Controllable Loss Disallowance"
        else:
            regulatory_clause = "Regulation 9.4 — Uncontrollable Pass-Through"
        
        ai_decision = AIDecision(
            id=str(uuid4()),
            deviation_report_id=report.id,
            decision=recommendation,
            confidence_score=confidence,
            recommended_value=report.actual_value if recommendation == DecisionType.APPROVE else report.approved_value,
            decision_mode=decision_mode,
            variance_percent=report.variance_percent,
            variance_exceeds_threshold=variance_high,
            external_factor_detected=False,
            external_factor_category=None,
            ai_justification=justification,
            regulatory_clause=regulatory_clause,
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
            reviewed_by=None
        )
        
        db.add(ai_decision)
        decisions.append(ai_decision)
    
    db.commit()
    print(f"Created {len(decisions)} AI decisions")
    return decisions


def seed_demo_data():
    """Main function to seed demo data."""
    print("=" * 60)
    print("Seeding Demo Data for KSERC Truing-Up System")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Create demo case
        case = create_demo_case(db)
        
        # Create deviation reports
        reports = create_deviation_reports(db, case.id)
        
        # Create AI decisions
        decisions = create_ai_decisions(db, reports)
        
        print("=" * 60)
        print("Demo data seeding completed successfully!")
        print(f"Case ID: {case.id}")
        print(f"Total Line Items: {len(reports)}")
        print(f"AI Decisions: {len(decisions)}")
        print("=" * 60)
        
        return {
            "case_id": case.id,
            "reports_count": len(reports),
            "decisions_count": len(decisions)
        }
        
    except Exception as e:
        print(f"Error seeding demo data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_demo_data_if_needed():
    """
    Seed demo data only if DEMO_MODE is enabled and data doesn't exist.
    Call this on application startup.
    """
    if not is_demo_mode():
        print("DEMO_MODE is disabled. Skipping demo data seeding.")
        return None
    
    settings = get_settings()
    print(f"DEMO_MODE is enabled. Checking demo data...")
    
    return seed_demo_data()


def clear_demo_data():
    """Clear all demo data from the database."""
    print("Clearing demo data...")
    
    db = SessionLocal()
    try:
        # Delete AI decisions for demo case
        db.query(AIDecision).filter(
            AIDecision.deviation_report.has(case_id=DEMO_CASE_ID)
        ).delete(synchronize_session=False)
        
        # Delete deviation reports for demo case
        db.query(DeviationReport).filter(
            DeviationReport.case_id == DEMO_CASE_ID
        ).delete(synchronize_session=False)
        
        # Delete demo case
        db.query(PetitionData).filter(
            PetitionData.id == DEMO_CASE_ID
        ).delete(synchronize_session=False)
        
        db.commit()
        print("Demo data cleared successfully.")
        
    except Exception as e:
        print(f"Error clearing demo data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Run standalone
    seed_demo_data()
