"""
FastAPI endpoint: Human-in-the-Loop Mapping Confirmation.
Implements Module B "Mapping Workbench" — AI suggests, human confirms.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import datetime

router = APIRouter(prefix="/mapping", tags=["Mapping Workbench"])


# ─── Request/Response Models ───

class MappingConfirmRequest(BaseModel):
    """Officer's confirmation or override of an AI-suggested mapping."""
    mapping_id: int
    decision: Literal["Confirmed", "Overridden", "Rejected"]
    override_head: Optional[str] = None          # Required if Overridden
    override_category: Optional[str] = None      # Required if Overridden
    comment: str                                  # Always mandatory
    officer_name: str

    @field_validator("comment")
    @classmethod
    def comment_must_not_be_empty(cls, v):
        if not v or len(v.strip()) < 5:
            raise ValueError("Comment is mandatory and must be at least 5 characters.")
        return v.strip()

    @field_validator("override_head")
    @classmethod
    def override_required_if_overridden(cls, v, info):
        if info.data.get("decision") == "Overridden" and not v:
            raise ValueError("override_head is required when decision is 'Overridden'.")
        return v


class MappingConfirmResponse(BaseModel):
    """Confirmation receipt with audit metadata."""
    mapping_id: int
    status: str
    original_ai_suggestion: dict
    final_mapping: dict
    officer_comment: str
    decided_by: str
    decided_at: str
    audit_note: str


class MappingSuggestion(BaseModel):
    """AI's suggested mapping for a single extracted field."""
    mapping_id: int
    sbu_code: str                      # SBU Partitioning: SBU-G, SBU-T, SBU-D
    source_field: str                  # e.g., "Employee Expense"
    suggested_head: str                # e.g., "O&M"
    suggested_category: str            # e.g., "Controllable"
    confidence: float                  # 0.0 to 1.0
    reasoning: str
    status: str = "Pending"


# ─── In-Memory Store (production: PostgreSQL via MappingRecord model) ───
_mapping_store = {
    1: MappingSuggestion(
        mapping_id=1,
        sbu_code="SBU-D",
        source_field="Employee Expense (Salaries & Wages)",
        suggested_head="O&M",
        suggested_category="Controllable",
        confidence=0.92,
        reasoning="Employee costs are a sub-component of O&M under KSERC Regulation 5.1."
    ),
    2: MappingSuggestion(
        mapping_id=2,
        sbu_code="SBU-G",
        source_field="Short-Term Power Purchase (Exchange)",
        suggested_head="Power_Purchase",
        suggested_category="Uncontrollable",
        confidence=0.87,
        reasoning="Exchange-based purchases are classified as Uncontrollable under Regulation 4.3."
    ),
    3: MappingSuggestion(
        mapping_id=3,
        sbu_code="SBU-T",
        source_field="Legal & Professional Fees",
        suggested_head="O&M",
        suggested_category="Controllable",
        confidence=0.65,
        reasoning="Professional fees typically map to O&M, but low confidence due to ambiguous classification."
    ),
}


# ─── Endpoints ───

@router.get("/pending", response_model=list[MappingSuggestion])
async def get_pending_mappings():
    """Returns all AI-suggested mappings awaiting officer review."""
    return [m for m in _mapping_store.values() if m.status == "Pending"]


@router.post("/confirm", response_model=MappingConfirmResponse)
async def confirm_mapping(req: MappingConfirmRequest):
    """
    Officer confirms, overrides, or rejects an AI-suggested mapping.
    Override and Reject require mandatory comments.
    All decisions are immutably logged in the audit trail.
    """
    mapping = _mapping_store.get(req.mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail=f"Mapping ID {req.mapping_id} not found.")

    if mapping.status != "Pending":
        raise HTTPException(status_code=409, detail=f"Mapping {req.mapping_id} already decided: {mapping.status}.")

    original = {
        "source_field": mapping.source_field,
        "suggested_head": mapping.suggested_head,
        "suggested_category": mapping.suggested_category,
        "confidence": mapping.confidence
    }

    if req.decision == "Confirmed":
        final_head = mapping.suggested_head
        final_category = mapping.suggested_category
        audit_note = f"AI suggestion accepted by {req.officer_name}."
    elif req.decision == "Overridden":
        final_head = req.override_head or mapping.suggested_head
        final_category = req.override_category or mapping.suggested_category
        audit_note = f"AI suggestion overridden by {req.officer_name}: {mapping.suggested_head} -> {final_head}."
    else:
        final_head = "REJECTED"
        final_category = "REJECTED"
        audit_note = f"AI suggestion rejected by {req.officer_name}. Reason: {req.comment}"

    mapping.status = req.decision
    decided_at = datetime.utcnow().isoformat()

    return MappingConfirmResponse(
        mapping_id=req.mapping_id,
        status=req.decision,
        original_ai_suggestion=original,
        final_mapping={"head": final_head, "category": final_category},
        officer_comment=req.comment,
        decided_by=req.officer_name,
        decided_at=decided_at,
        audit_note=audit_note
    )
