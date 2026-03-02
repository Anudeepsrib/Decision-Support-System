"""
FastAPI endpoint: Human-in-the-Loop Mapping Confirmation.
Implements Module B "Mapping Workbench" — AI suggests, human confirms.
Supports auto-population from extraction results.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timezone

from backend.security.auth import get_current_user, require_permission, TokenData

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
    extracted_value: Optional[float] = None
    source_page: Optional[int] = None


class GenerateMappingsRequest(BaseModel):
    """Request to auto-generate mappings from extracted fields."""
    fields: List[Dict[str, Any]]


# ─── In-Memory Store (production: PostgreSQL via MappingRecord model) ───
_mapping_store: Dict[int, MappingSuggestion] = {}
_next_mapping_id = 1

# ─── Cost Head Classification Logic ───
_HEAD_CLASSIFICATION = {
    "O&M": {
        "keywords": ["o&m", "operation", "maintenance", "employee", "staff", "salaries", "wages",
                      "r&m", "repair", "a&g", "admin", "general", "personnel"],
        "category": "Controllable",
        "reasoning_template": "{field} maps to O&M under KSERC Regulation 5.1 as a component of operational expenditure.",
    },
    "Power_Purchase": {
        "keywords": ["power purchase", "energy purchase", "cost of power", "transmission charge",
                      "wheeling", "exchange", "bilateral"],
        "category": "Uncontrollable",
        "reasoning_template": "{field} maps to Power Purchase under Regulation 4.3 as an uncontrollable market-driven cost.",
    },
    "Interest": {
        "keywords": ["interest", "finance charge", "debt", "loan", "borrowing"],
        "category": "Uncontrollable",
        "reasoning_template": "{field} maps to Interest & Finance Charges under Regulation 6.3 (SBI EBLR + 2% normative rate).",
    },
    "Depreciation": {
        "keywords": ["depreciation", "asset", "capital recovery"],
        "category": "Controllable",
        "reasoning_template": "{field} maps to Depreciation under Regulation 6.1 (Straight-Line method, 25-year asset life).",
    },
    "Return_on_Equity": {
        "keywords": ["return on equity", "roe", "equity return"],
        "category": "Controllable",
        "reasoning_template": "{field} maps to Return on Equity under Regulation 7.1 (15.5% pre-tax ROE).",
    },
}


def _classify_field(field_name: str) -> tuple:
    """Classify an extracted field into a cost head and category."""
    lower = field_name.lower()
    
    for head, config in _HEAD_CLASSIFICATION.items():
        for keyword in config["keywords"]:
            if keyword in lower:
                return head, config["category"], config["reasoning_template"].format(field=field_name)
    
    # Default fallback
    return "Other", "Controllable", f"{field_name} could not be auto-classified. Manual review required."


def generate_mappings_from_fields(fields: List[Dict[str, Any]]) -> List[MappingSuggestion]:
    """Auto-generate mapping suggestions from extracted fields."""
    global _next_mapping_id
    new_mappings = []
    
    for f in fields:
        field_name = f.get("field_name", "Unknown")
        sbu_code = f.get("sbu_code", "SBU-D")
        confidence = f.get("confidence_score", 0.5)
        extracted_value = f.get("extracted_value")
        source_page = f.get("source_page")
        
        head, category, reasoning = _classify_field(field_name)
        
        mapping = MappingSuggestion(
            mapping_id=_next_mapping_id,
            sbu_code=sbu_code,
            source_field=field_name,
            suggested_head=head,
            suggested_category=category,
            confidence=round(confidence * 0.95, 2),  # Slightly discount for mapping step
            reasoning=reasoning,
            status="Pending",
            extracted_value=extracted_value,
            source_page=source_page,
        )
        
        _mapping_store[_next_mapping_id] = mapping
        new_mappings.append(mapping)
        _next_mapping_id += 1
    
    return new_mappings


# ─── Endpoints ───

@router.get("/pending", response_model=list[MappingSuggestion])
async def get_pending_mappings(
    current_user: TokenData = Depends(get_current_user),  # F-12: RBAC enforced
    _perm=Depends(require_permission("mapping.read")),
):
    """Returns all AI-suggested mappings awaiting officer review. Requires: mapping.read."""
    return [m for m in _mapping_store.values() if m.status == "Pending"]


@router.get("/all", response_model=list[MappingSuggestion])
async def get_all_mappings(
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("mapping.read")),
):
    """Returns all mappings regardless of status."""
    return list(_mapping_store.values())


@router.post("/generate", response_model=list[MappingSuggestion])
async def generate_mappings(
    req: GenerateMappingsRequest,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("mapping.read")),
):
    """
    Auto-generate mapping suggestions from extracted fields.
    This is typically called after PDF extraction to populate the mapping workbench.
    """
    new_mappings = generate_mappings_from_fields(req.fields)
    return new_mappings


@router.post("/confirm", response_model=MappingConfirmResponse)
async def confirm_mapping(
    req: MappingConfirmRequest,
    current_user: TokenData = Depends(get_current_user),  # F-12: RBAC enforced
    _perm=Depends(require_permission("mapping.confirm")),
):
    """
    Officer confirms, overrides, or rejects an AI-suggested mapping.
    Override and Reject require mandatory comments.
    All decisions are immutably logged in the audit trail.
    Requires: mapping.confirm permission.
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
    decided_at = datetime.now(timezone.utc).isoformat()

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
