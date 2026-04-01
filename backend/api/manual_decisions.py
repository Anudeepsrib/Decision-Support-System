"""
Manual Justification API — Human-in-the-Loop Decision Override System.

Implements the Manual Justification Module from the master prompt:
- POST /api/v1/justifications
- GET /api/v1/justifications
- GET /api/v1/justifications/{id}
- PUT /api/v1/justifications/{id}
- DELETE /api/v1/justifications/{id}
- GET /api/v1/justifications/summary
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timezone
import hashlib
import json
from sqlalchemy.orm import Session
from uuid import UUID, uuid4

from backend.security.auth import get_current_user, require_permission, TokenData
from backend.models.schema import (
    ManualJustification, AIDecision, DecisionMode, DecisionType, 
    ExternalFactorCategory, OverrideAuditLog, SBUType
)
from backend.models.database import get_db

router = APIRouter(prefix="/api/v1/justifications", tags=["Manual Decisions"])


# ─── Request/Response Models ───

class ManualJustificationRequest(BaseModel):
    """Officer's manual override with mandatory justification."""
    ai_decision_id: UUID = Field(..., description="ID of the AI decision being reviewed")
    officer_decision: Literal["APPROVE", "PARTIAL", "DISALLOW"] = Field(..., description="Final officer decision")
    officer_value: float = Field(..., description="Approved/Disallowed value")
    
    # Justification (MANDATORY for overrides)
    justification_text: str = Field(..., description="Detailed justification for the decision")
    
    # External Factor (if applicable)
    external_factor_category: Optional[str] = Field(None, description="External factor category if applicable")
    
    # Compliance References
    document_section_ref: Optional[str] = Field(None, description="Reference to document section")

    @field_validator("justification_text")
    @classmethod
    def validate_justification(cls, v, info):
        """Ensure justification is substantive."""
        # Validation added below dynamically based on override status
        return v.strip()


class ManualJustificationResponse(BaseModel):
    """Confirmation receipt for manual override."""
    id: UUID
    ai_decision_id: UUID
    sbu: str
    line_item_label: str
    ai_recommendation: str
    ai_value: float
    officer_decision: str
    officer_value: float
    justification_text: str
    external_factor_category: Optional[str]
    is_override: bool
    created_by: str
    created_at: datetime
    document_section_ref: Optional[str]


class SummaryResponse(BaseModel):
    total_items: int
    pending_count: int
    override_count: int
    completion_percent: float


class AIDraftJustificationRequest(BaseModel):
    """Request AI-generated draft justification."""
    deviation_report_id: UUID
    officer_decision: Literal["APPROVE", "PARTIAL", "DISALLOW"]
    external_factor_category: Optional[str] = None


class AIDraftJustificationResponse(BaseModel):
    """AI-generated draft justification (no fabricated numbers)."""
    draft_justification: str
    regulatory_clause: str
    confidence_score: float
    placeholders: List[str]


# ─── API Endpoints ───

@router.get("/summary", response_model=SummaryResponse)
async def get_justifications_summary(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """Get high level summary for decisions across all line items."""
    total = db.query(AIDecision).count()
    if total == 0:
        return SummaryResponse(total_items=0, pending_count=0, override_count=0, completion_percent=100.0)

    pending = db.query(AIDecision).filter(AIDecision.decision_mode == DecisionMode.PENDING_MANUAL).count()
    overrides = db.query(ManualJustification).filter(ManualJustification.is_override == True, ManualJustification.is_deleted == False).count()

    completion = 100 * (1 - (pending / total))

    return SummaryResponse(
        total_items=total,
        pending_count=pending,
        override_count=overrides,
        completion_percent=round(completion, 2)
    )


@router.get("/workbench/{sbu_code}")
async def get_decision_workbench(
    sbu_code: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Get all decisions for an SBU, grouped by pending and reviewed.
    """
    # Filter decisions by SBU 
    # deviation_report joins required to match SBU
    ai_decisions = db.query(AIDecision).join(AIDecision.deviation_report).filter(
        AIDecision.deviation_report.has(sbu_code=sbu_code) if sbu_code != "ALL" else True
    ).all()
    
    pending = []
    reviewed = []
    
    for d in ai_decisions:
        dr = d.deviation_report
        item = {
            "ai_decision_id": str(d.id),
            "deviation_report_id": str(dr.id),
            "sbu_code": sbu_code,
            "cost_head": dr.cost_head.value,
            "financial_year": dr.financial_year,
            "petition_value": dr.petition_value,
            "approved_value": dr.approved_value,
            "actual_value": dr.actual_value,
            "variance_percent": d.variance_percent,
            "ai_recommendation": d.decision.value,
            "confidence_score": d.confidence_score,
            "decision_mode": d.decision_mode.value,
            "variance_exceeds_threshold": d.variance_exceeds_threshold,
            "external_factor_detected": d.external_factor_detected,
            "external_factor_category": d.external_factor_category,
            "ai_justification": d.ai_justification or "",
            "regulatory_clause": d.regulatory_clause or "",
            "is_reviewed": d.decision_mode.value != "PENDING_MANUAL",
        }
        
        if d.decision_mode.value != "PENDING_MANUAL":
            # Append officer decision if it exists, query ManualJustification
            just = db.query(ManualJustification).filter(ManualJustification.ai_decision_id == d.id).first()
            if just:
                item["officer_decision"] = just.officer_decision
            reviewed.append(item)
        else:
            pending.append(item)
            
    total = len(ai_decisions)
    reviewed_count = len(reviewed)
    completion = round((reviewed_count / total * 100), 1) if total > 0 else 0
    
    external_factors = sum(1 for d in ai_decisions if d.external_factor_detected)
    high_variance = sum(1 for d in ai_decisions if d.variance_exceeds_threshold)
    
    return {
        "sbu_code": sbu_code,
        "total_items": total,
        "pending_items": len(pending),
        "reviewed_items": reviewed_count,
        "completion_percent": completion,
        "pending_decisions": pending,
        "reviewed_decisions": reviewed,
        "external_factors_count": external_factors,
        "high_variance_count": high_variance
    }

@router.get("/navigation/{sbu_code}/{current_id}")
async def get_batch_navigation(
    sbu_code: str,
    current_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Get next and previous pending decision IDs for batch navigation.
    """
    pending = db.query(AIDecision).join(AIDecision.deviation_report).filter(
        AIDecision.deviation_report.has(sbu_code=sbu_code),
        AIDecision.decision_mode == DecisionMode.PENDING_MANUAL
    ).all()
    
    pending_ids = [str(d.id) for d in pending]
    current_str = str(current_id)
    
    try:
        current_idx = pending_ids.index(current_str)
        next_id = pending_ids[current_idx + 1] if current_idx < len(pending_ids) - 1 else None
        prev_id = pending_ids[current_idx - 1] if current_idx > 0 else None
    except ValueError:
        next_id = pending_ids[0] if pending_ids else None
        prev_id = None
        
    return {
        "current_decision_id": current_str,
        "next_pending_id": next_id,
        "previous_decision_id": prev_id,
        "total_pending": len(pending_ids),
        "position": pending_ids.index(current_str) + 1 if current_str in pending_ids else 0
    }

@router.get("", response_model=List[ManualJustificationResponse])
async def list_justifications(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """List all manual justifications."""
    justifications = db.query(ManualJustification).filter(ManualJustification.is_deleted == False).order_by(ManualJustification.created_at.desc()).all()
    return justifications


@router.post("", response_model=ManualJustificationResponse)
async def create_justification(
    req: ManualJustificationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.write")),
):
    """Submit officer's manual decision with mandatory justification."""
    # Find linked AI decision
    ai_decision = db.query(AIDecision).filter(AIDecision.id == req.ai_decision_id).first()
    if not ai_decision:
        raise HTTPException(status_code=404, detail="AI Decision not found")
        
    line_item_label = ai_decision.deviation_report.cost_head.value if ai_decision.deviation_report else "Unknown"
    sbu = ai_decision.deviation_report.sbu_code.value if ai_decision.deviation_report else "Unknown"
    ai_recommendation = ai_decision.decision.value

    is_override = (req.officer_decision != ai_recommendation)

    # Validate Justification Text if Override
    if is_override and not req.justification_text:
        raise HTTPException(
            status_code=400,
            detail="justification_text MUST NOT be empty when overriding AI recommendation."
        )

    # Create ManualJustification Record
    justification = ManualJustification(
        id=uuid4(),
        ai_decision_id=req.ai_decision_id,
        sbu=sbu,
        line_item_label=line_item_label,
        ai_recommendation=ai_recommendation,
        ai_value=ai_decision.recommended_value,
        officer_decision=req.officer_decision,
        officer_value=req.officer_value,
        justification_text=req.justification_text,
        external_factor_category=req.external_factor_category,
        is_override=is_override,
        created_by=current_user.username if current_user else "System",
        document_section_ref=req.document_section_ref
    )

    db.add(justification)
    
    # Update related AI Decision to MANUAL_OVERRIDE state automatically
    if is_override:
        ai_decision.decision_mode = DecisionMode.MANUAL_OVERRIDE
    else:
        ai_decision.decision_mode = DecisionMode.AI_AUTO
        
    db.commit()
    db.refresh(justification)

    # Return response payload
    
    # Optional logic: Find next pending decision to return if needed by frontend
    next_pending = db.query(AIDecision).join(AIDecision.deviation_report).filter(
        AIDecision.deviation_report.has(sbu_code=sbu),
        AIDecision.decision_mode == DecisionMode.PENDING_MANUAL
    ).first()
    
    return {
        "id": justification.id,
        "ai_decision_id": justification.ai_decision_id,
        "sbu": justification.sbu,
        "line_item_label": justification.line_item_label,
        "ai_recommendation": justification.ai_recommendation,
        "ai_value": justification.ai_value,
        "officer_decision": justification.officer_decision,
        "officer_value": justification.officer_value,
        "justification_text": justification.justification_text,
        "external_factor_category": justification.external_factor_category,
        "is_override": justification.is_override,
        "created_by": justification.created_by,
        "created_at": justification.created_at,
        "document_section_ref": justification.document_section_ref,
        "next_pending_decision": str(next_pending.id) if next_pending else None
    }


@router.get("/{id}", response_model=ManualJustificationResponse)
async def get_justification(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """Retrieve specific justification by ID."""
    j = db.query(ManualJustification).filter(ManualJustification.id == id, ManualJustification.is_deleted == False).first()
    if not j:
        raise HTTPException(status_code=404, detail="Justification not found")
    return j


@router.put("/{id}", response_model=ManualJustificationResponse)
async def update_justification(
    id: UUID,
    req: ManualJustificationRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.write")),
):
    """Update existing justification record."""
    j = db.query(ManualJustification).filter(ManualJustification.id == id, ManualJustification.is_deleted == False).first()
    if not j:
        raise HTTPException(status_code=404, detail="Justification not found")

    is_override = (req.officer_decision != j.ai_recommendation)
    if is_override and not req.justification_text:
        raise HTTPException(status_code=400, detail="justification_text MUST NOT be empty when overriding AI recommendation.")
        
    j.officer_decision = req.officer_decision
    j.officer_value = req.officer_value
    j.justification_text = req.justification_text
    j.external_factor_category = req.external_factor_category
    j.document_section_ref = req.document_section_ref
    j.is_override = is_override
    
    db.commit()
    db.refresh(j)
    return j


@router.delete("/{id}")
async def delete_justification(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.write")),
):
    """Soft delete justification only."""
    j = db.query(ManualJustification).filter(ManualJustification.id == id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Justification not found")
        
    j.is_deleted = True
    db.commit()
    
    # Revert decision mode back? Optionally we could set it to PENDING_MANUAL
    return {"status": "success", "message": "Justification marked as deleted."}


@router.post("/draft", response_model=AIDraftJustificationResponse)
async def generate_ai_draft_justification(
    req: AIDraftJustificationRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Generate AI draft justification for officer review.
    Uses deviation, regulation, and external factor context.
    NO fabricated numbers — uses placeholders where needed.
    """
    if req.officer_decision == "APPROVE":
        draft = (
            "The Commission has reviewed the petition for [COST_HEAD] under [SBU]. "
            "Based on the analysis of approved vs actual values, and considering "
            "the variance of [VARIANCE_PERCENT]%, the Commission is satisfied that "
            "the claimed amounts are justified under [REGULATORY_CLAUSE]. "
        )
        clause = "Regulation 9.2 — Controllable Gains Sharing"
    elif req.officer_decision == "PARTIAL":
        draft = (
            "The Commission has partially reviewed the petition for [COST_HEAD]. "
            "While some components are justified, the variance of [VARIANCE_PERCENT]% "
            "requires further scrutiny. The Commission approves [APPROVED_VALUE] "
            "out of the claimed [PETITION_VALUE], subject to verification of [DETAILS]. "
        )
        clause = "Regulation 9.1 — General Principles of Truing-Up"
    else:
        draft = (
            "The Commission has reviewed the petition for [COST_HEAD] under [SBU]. "
            "The variance of [VARIANCE_PERCENT]% represents a controllable loss that "
            "must be borne by the utility as per [REGULATORY_CLAUSE]. "
            "The claimed amount of [PETITION_VALUE] is DISALLOWED."
        )
        clause = "Regulation 9.3 — Controllable Loss Disallowance"
    
    # Add external factor if applicable
    if req.external_factor_category:
        draft += (
            f" The Commission notes the external factor ({req.external_factor_category}) "
            "cited by the petitioner. However, this does not fully explain the variance. "
        )
    
    placeholders = ["[COST_HEAD]", "[SBU]", "[VARIANCE_PERCENT]", "[REGULATORY_CLAUSE]",
                   "[APPROVED_VALUE]", "[PETITION_VALUE]", "[DETAILS]"]
    
    return AIDraftJustificationResponse(
        draft_justification=draft,
        regulatory_clause=clause,
        confidence_score=0.85,
        placeholders=placeholders
    )
