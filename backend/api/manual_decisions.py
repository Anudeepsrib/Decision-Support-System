"""
Manual Justification API — Human-in-the-Loop Decision Override System.

Implements the Manual Justification Module from the master prompt:
- Officer can override AI decision
- Provide structured justification (MANDATORY for overrides)
- Tag external factor category
- Store full audit trail

Validation Rules:
- If override: justification_text REQUIRED
- If same as AI: optional but encouraged
- External factors must be categorized when detected
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timezone
import hashlib
import json

from backend.security.auth import get_current_user, require_permission, TokenData
from backend.engine.decision_mode_classifier import (
    DecisionMode, DecisionType, ExternalFactorCategory
)

router = APIRouter(prefix="/manual-decisions", tags=["Manual Decisions"])


# ─── Request/Response Models ───

class ManualJustificationRequest(BaseModel):
    """Officer's manual override with mandatory justification."""
    ai_decision_id: int = Field(..., description="ID of the AI decision being reviewed")
    officer_decision: Literal["APPROVE", "PARTIAL", "DISALLOW"] = Field(..., description="Final officer decision")
    final_value: float = Field(..., description="Approved/Disallowed value")
    
    # Justification (MANDATORY for overrides)
    justification_text: str = Field(..., min_length=20, description="Detailed justification for the decision")
    
    # External Factor (if applicable)
    external_factor_category: Optional[Literal[
        "Hydrology", "Power_Purchase_Volatility", "Government_Mandate", 
        "Court_Order", "CapEx_Overrun", "Force_Majeure", "Other"
    ]] = Field(None, description="External factor category if applicable")
    external_factor_description: Optional[str] = Field(None, description="Description of external factor")
    
    # Compliance References
    electricity_act_section: Optional[str] = Field(None, description="Relevant Electricity Act section")
    kserc_regulation_ref: Optional[str] = Field(None, description="KSERC regulation reference")
    
    # Officer Info
    officer_name: str = Field(..., min_length=2, description="Officer name")
    officer_designation: Optional[str] = Field(None, description="Officer designation")
    
    @field_validator("justification_text")
    @classmethod
    def validate_justification(cls, v, info):
        """Ensure justification is substantive for overrides."""
        if not v or len(v.strip()) < 20:
            raise ValueError("Justification must be at least 20 characters for all decisions.")
        return v.strip()


class ManualJustificationResponse(BaseModel):
    """Confirmation receipt for manual override with audit metadata."""
    justification_id: int
    ai_decision_id: int
    status: str
    
    # Decision Summary
    ai_recommendation: str
    officer_decision: str
    final_value: float
    
    # Justification
    justification_text: str
    external_factor_category: Optional[str]
    
    # Audit Metadata
    decided_by: str
    decided_at: str
    audit_checksum: str
    
    # Next Action
    next_pending_decision: Optional[int] = None
    completion_percent: float


class DecisionItem(BaseModel):
    """Single decision item for the workbench."""
    ai_decision_id: int
    deviation_report_id: int
    sbu_code: str
    cost_head: str
    financial_year: str
    
    # Values
    petition_value: float
    approved_value: float
    actual_value: Optional[float]
    variance_percent: float
    
    # AI Recommendation
    ai_recommendation: str
    confidence_score: float
    decision_mode: str
    
    # Flags
    variance_exceeds_threshold: bool
    external_factor_detected: bool
    external_factor_category: Optional[str]
    
    # AI Justification
    ai_justification: str
    regulatory_clause: str
    
    # Status
    is_reviewed: bool = False
    officer_decision: Optional[str] = None


class DecisionWorkbenchResponse(BaseModel):
    """Response for the manual decisions workbench."""
    sbu_code: str
    total_items: int
    pending_items: int
    reviewed_items: int
    completion_percent: float
    
    # Grouped by status
    pending_decisions: List[DecisionItem]
    reviewed_decisions: List[DecisionItem]
    
    # Summary
    external_factors_count: int
    high_variance_count: int


class BatchNavigationResponse(BaseModel):
    """Response for batch navigation (next pending)."""
    current_decision_id: int
    next_pending_id: Optional[int]
    previous_decision_id: Optional[int]
    total_pending: int
    position: int


class ProgressSummaryResponse(BaseModel):
    """Overall progress summary for all SBUs."""
    total_decisions: int
    ai_auto_count: int
    pending_manual_count: int
    manual_override_count: int
    completion_percent: float
    
    # By SBU
    sbu_progress: Dict[str, Dict[str, Any]]
    
    # Can finalize?
    can_finalize: bool
    pending_count: int


class AIDraftJustificationRequest(BaseModel):
    """Request AI-generated draft justification."""
    deviation_report_id: int
    officer_decision: Literal["APPROVE", "PARTIAL", "DISALLOW"]
    external_factor_category: Optional[str] = None


class AIDraftJustificationResponse(BaseModel):
    """AI-generated draft justification (no fabricated numbers)."""
    draft_justification: str
    regulatory_clause: str
    confidence_score: float
    placeholders: List[str]  # Values that need manual insertion


# ─── In-Memory Store (production: PostgreSQL via ManualJustification model) ───
_manual_decision_store: Dict[int, Dict[str, Any]] = {}
_ai_decision_store: Dict[int, Dict[str, Any]] = {}
_next_justification_id = 1
_next_ai_decision_id = 1


def _generate_checksum(data: Dict[str, Any]) -> str:
    """Generate SHA-256 checksum for audit integrity."""
    canonical = json.dumps(data, sort_keys=True, default=str, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _log_override_audit(action_type: str, entity_type: str, entity_id: int,
                       officer_name: str, field_changed: Optional[str] = None,
                       old_value: Optional[str] = None, new_value: Optional[str] = None,
                       change_reason: Optional[str] = None, request: Request = None):
    """Log override action to audit trail."""
    audit_entry = {
        "action_type": action_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "officer_name": officer_name,
        "field_changed": field_changed,
        "old_value": old_value,
        "new_value": new_value,
        "change_reason": change_reason,
        "justification_provided": change_reason is not None and len(change_reason) > 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    if request:
        audit_entry["ip_address"] = request.client.host if request.client else None
        audit_entry["user_agent"] = request.headers.get("user-agent")
    
    audit_entry["checksum"] = _generate_checksum(audit_entry)
    
    # In production, this would insert into OverrideAuditLog table
    print(f"[AUDIT] {action_type} by {officer_name}: {entity_type}#{entity_id}")
    return audit_entry


# ─── API Endpoints ───

@router.get("/workbench/{sbu_code}", response_model=DecisionWorkbenchResponse)
async def get_decision_workbench(
    sbu_code: str,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Get all decisions for an SBU, grouped by pending and reviewed.
    Supports the Manual Decisions tab UI with progress tracking.
    """
    # Filter decisions by SBU
    sbu_decisions = [
        d for d in _ai_decision_store.values()
        if d.get("sbu_code") == sbu_code
    ]
    
    pending = []
    reviewed = []
    
    for d in sbu_decisions:
        item = DecisionItem(
            ai_decision_id=d["id"],
            deviation_report_id=d["deviation_report_id"],
            sbu_code=d["sbu_code"],
            cost_head=d["cost_head"],
            financial_year=d["financial_year"],
            petition_value=d["petition_value"],
            approved_value=d["approved_value"],
            actual_value=d.get("actual_value"),
            variance_percent=d["variance_percent"],
            ai_recommendation=d["ai_recommendation"],
            confidence_score=d["confidence_score"],
            decision_mode=d["decision_mode"],
            variance_exceeds_threshold=d["variance_exceeds_threshold"],
            external_factor_detected=d["external_factor_detected"],
            external_factor_category=d.get("external_factor_category"),
            ai_justification=d["ai_justification"],
            regulatory_clause=d["regulatory_clause"],
            is_reviewed=d.get("is_reviewed", False),
            officer_decision=d.get("officer_decision")
        )
        
        if d.get("is_reviewed"):
            reviewed.append(item)
        else:
            pending.append(item)
    
    total = len(sbu_decisions)
    reviewed_count = len(reviewed)
    completion = round((reviewed_count / total * 100), 1) if total > 0 else 0
    
    external_factors = sum(1 for d in sbu_decisions if d.get("external_factor_detected"))
    high_variance = sum(1 for d in sbu_decisions if d.get("variance_exceeds_threshold"))
    
    return DecisionWorkbenchResponse(
        sbu_code=sbu_code,
        total_items=total,
        pending_items=len(pending),
        reviewed_items=reviewed_count,
        completion_percent=completion,
        pending_decisions=pending,
        reviewed_decisions=reviewed,
        external_factors_count=external_factors,
        high_variance_count=high_variance
    )


@router.post("/submit", response_model=ManualJustificationResponse)
async def submit_manual_decision(
    req: ManualJustificationRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.write")),
):
    """
    Submit officer's manual decision with mandatory justification.
    
    Validation:
    - justification_text is REQUIRED (min 20 chars)
    - If overriding AI: justification must explain the deviation
    """
    global _next_justification_id
    
    # Validate AI decision exists
    ai_decision = _ai_decision_store.get(req.ai_decision_id)
    if not ai_decision:
        raise HTTPException(status_code=404, detail=f"AI Decision {req.ai_decision_id} not found")
    
    # Check if already reviewed
    if ai_decision.get("is_reviewed"):
        raise HTTPException(
            status_code=409, 
            detail=f"Decision {req.ai_decision_id} has already been reviewed"
        )
    
    # Determine if this is an override
    is_override = req.officer_decision != ai_decision["ai_recommendation"]
    
    # Additional validation for overrides
    if is_override and len(req.justification_text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Override justifications must be at least 50 characters"
        )
    
    # Create justification record
    decided_at = datetime.now(timezone.utc).isoformat()
    
    justification_record = {
        "id": _next_justification_id,
        "ai_decision_id": req.ai_decision_id,
        "officer_name": req.officer_name,
        "officer_designation": req.officer_designation,
        "officer_decision": req.officer_decision,
        "final_value": req.final_value,
        "justification_text": req.justification_text,
        "external_factor_category": req.external_factor_category,
        "external_factor_description": req.external_factor_description,
        "electricity_act_section": req.electricity_act_section,
        "kserc_regulation_ref": req.kserc_regulation_ref,
        "decided_at": decided_at,
        "is_override": is_override,
        "ip_address": request.client.host if request.client else None,
    }
    
    # Generate checksum
    justification_record["checksum"] = _generate_checksum(justification_record)
    
    # Store record
    _manual_decision_store[_next_justification_id] = justification_record
    
    # Update AI decision
    ai_decision["is_reviewed"] = True
    ai_decision["officer_decision"] = req.officer_decision
    ai_decision["decision_mode"] = DecisionMode.MANUAL_OVERRIDE.value if is_override else DecisionMode.AI_AUTO.value
    ai_decision["final_value"] = req.final_value
    ai_decision["justification_id"] = _next_justification_id
    
    # Log audit trail
    _log_override_audit(
        action_type="OVERRIDE" if is_override else "CONFIRM",
        entity_type="AIDecision",
        entity_id=req.ai_decision_id,
        officer_name=req.officer_name,
        field_changed="decision",
        old_value=ai_decision["ai_recommendation"],
        new_value=req.officer_decision,
        change_reason=req.justification_text,
        request=request
    )
    
    # Find next pending decision
    sbu_decisions = [
        d for d in _ai_decision_store.values()
        if d.get("sbu_code") == ai_decision["sbu_code"] and not d.get("is_reviewed")
    ]
    next_pending = sbu_decisions[0]["id"] if sbu_decisions else None
    
    # Calculate completion
    all_sbu_decisions = [d for d in _ai_decision_store.values() if d.get("sbu_code") == ai_decision["sbu_code"]]
    reviewed_count = sum(1 for d in all_sbu_decisions if d.get("is_reviewed"))
    completion = round((reviewed_count / len(all_sbu_decisions) * 100), 1) if all_sbu_decisions else 0
    
    response = ManualJustificationResponse(
        justification_id=_next_justification_id,
        ai_decision_id=req.ai_decision_id,
        status="OVERRIDDEN" if is_override else "CONFIRMED",
        ai_recommendation=ai_decision["ai_recommendation"],
        officer_decision=req.officer_decision,
        final_value=req.final_value,
        justification_text=req.justification_text,
        external_factor_category=req.external_factor_category,
        decided_by=req.officer_name,
        decided_at=decided_at,
        audit_checksum=justification_record["checksum"],
        next_pending_decision=next_pending,
        completion_percent=completion
    )
    
    _next_justification_id += 1
    return response


@router.get("/navigation/{sbu_code}/{current_id}", response_model=BatchNavigationResponse)
async def get_batch_navigation(
    sbu_code: str,
    current_id: int,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Get next and previous pending decision IDs for batch navigation.
    """
    # Get pending decisions for SBU
    pending = [
        d for d in _ai_decision_store.values()
        if d.get("sbu_code") == sbu_code and not d.get("is_reviewed")
    ]
    pending_ids = [d["id"] for d in pending]
    
    try:
        current_idx = pending_ids.index(current_id)
        next_id = pending_ids[current_idx + 1] if current_idx < len(pending_ids) - 1 else None
        prev_id = pending_ids[current_idx - 1] if current_idx > 0 else None
    except ValueError:
        next_id = pending_ids[0] if pending_ids else None
        prev_id = None
    
    return BatchNavigationResponse(
        current_decision_id=current_id,
        next_pending_id=next_id,
        previous_decision_id=prev_id,
        total_pending=len(pending_ids),
        position=pending_ids.index(current_id) + 1 if current_id in pending_ids else 0
    )


@router.get("/progress", response_model=ProgressSummaryResponse)
async def get_progress_summary(
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Get overall progress summary across all SBUs.
    """
    sbu_codes = ["SBU-G", "SBU-T", "SBU-D"]
    sbu_progress = {}
    
    total_decisions = 0
    ai_auto = 0
    pending = 0
    manual_override = 0
    
    for sbu in sbu_codes:
        sbu_items = [d for d in _ai_decision_store.values() if d.get("sbu_code") == sbu]
        sbu_reviewed = sum(1 for d in sbu_items if d.get("is_reviewed"))
        sbu_pending = len(sbu_items) - sbu_reviewed
        sbu_completion = round((sbu_reviewed / len(sbu_items) * 100), 1) if sbu_items else 0
        
        sbu_progress[sbu] = {
            "total": len(sbu_items),
            "reviewed": sbu_reviewed,
            "pending": sbu_pending,
            "completion_percent": sbu_completion
        }
        
        total_decisions += len(sbu_items)
        ai_auto += sum(1 for d in sbu_items if d.get("decision_mode") == DecisionMode.AI_AUTO.value)
        manual_override += sum(1 for d in sbu_items if d.get("decision_mode") == DecisionMode.MANUAL_OVERRIDE.value)
        pending += sbu_pending
    
    completion = round(((total_decisions - pending) / total_decisions * 100), 1) if total_decisions > 0 else 0
    
    return ProgressSummaryResponse(
        total_decisions=total_decisions,
        ai_auto_count=ai_auto,
        pending_manual_count=pending,
        manual_override_count=manual_override,
        completion_percent=completion,
        sbu_progress=sbu_progress,
        can_finalize=pending == 0,
        pending_count=pending
    )


@router.post("/ai-draft-justification", response_model=AIDraftJustificationResponse)
async def generate_ai_draft_justification(
    req: AIDraftJustificationRequest,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("decisions.read")),
):
    """
    Generate AI draft justification for officer review.
    Uses deviation, regulation, and external factor context.
    NO fabricated numbers — uses placeholders where needed.
    """
    # Get deviation report
    # In production, fetch from database
    
    # Generate template justification
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


# ─── Helper Functions for Data Population ───

def populate_sample_decisions():
    """Populate sample AI decisions for testing (remove in production)."""
    global _next_ai_decision_id
    
    sample_data = [
        {
            "sbu_code": "SBU-D",
            "cost_head": "O&M",
            "financial_year": "2024-25",
            "petition_value": 1500000000,
            "approved_value": 1450000000,
            "actual_value": 1480000000,
            "variance_percent": 2.1,
            "ai_recommendation": DecisionType.APPROVE.value,
            "confidence_score": 0.92,
            "decision_mode": DecisionMode.AI_AUTO.value,
            "variance_exceeds_threshold": False,
            "external_factor_detected": False,
            "ai_justification": "Variance within acceptable limits. Controllable gain detected.",
            "regulatory_clause": "Regulation 9.2 — Controllable Gains Sharing"
        },
        {
            "sbu_code": "SBU-D",
            "cost_head": "Power_Purchase",
            "financial_year": "2024-25",
            "petition_value": 4500000000,
            "approved_value": 4200000000,
            "actual_value": 4800000000,
            "variance_percent": 14.3,
            "ai_recommendation": DecisionType.PARTIAL.value,
            "confidence_score": 0.78,
            "decision_mode": DecisionMode.PENDING_MANUAL.value,
            "variance_exceeds_threshold": False,
            "external_factor_detected": True,
            "external_factor_category": ExternalFactorCategory.POWER_PURCHASE_VOLATILITY.value,
            "ai_justification": "High variance due to power purchase volatility. Manual review required.",
            "regulatory_clause": "Regulation 9.4 — Uncontrollable Pass-Through"
        },
        {
            "sbu_code": "SBU-D",
            "cost_head": "Interest",
            "financial_year": "2024-25",
            "petition_value": 800000000,
            "approved_value": 750000000,
            "actual_value": 920000000,
            "variance_percent": 22.7,
            "ai_recommendation": DecisionType.PARTIAL.value,
            "confidence_score": 0.81,
            "decision_mode": DecisionMode.PENDING_MANUAL.value,
            "variance_exceeds_threshold": False,
            "external_factor_detected": False,
            "ai_justification": "Variance approaching threshold. Normative interest calculation may need review.",
            "regulatory_clause": "Regulation 6.3 — Normative Interest (SBI EBLR + 2%)"
        },
        {
            "sbu_code": "SBU-G",
            "cost_head": "O&M",
            "financial_year": "2024-25",
            "petition_value": 500000000,
            "approved_value": 450000000,
            "actual_value": 580000000,
            "variance_percent": 28.9,
            "ai_recommendation": DecisionType.DISALLOW.value,
            "confidence_score": 0.88,
            "decision_mode": DecisionMode.PENDING_MANUAL.value,
            "variance_exceeds_threshold": True,
            "external_factor_detected": False,
            "ai_justification": "High variance (>25%). CapEx overrun suspected. Requires officer review.",
            "regulatory_clause": "Regulation 9.3 — Controllable Loss Disallowance"
        }
    ]
    
    for data in sample_data:
        data["id"] = _next_ai_decision_id
        data["deviation_report_id"] = _next_ai_decision_id
        data["is_reviewed"] = False
        _ai_decision_store[_next_ai_decision_id] = data
        _next_ai_decision_id += 1
    
    print(f"[INIT] Populated {_next_ai_decision_id - 1} sample AI decisions")


# Initialize sample data for development
populate_sample_decisions()
