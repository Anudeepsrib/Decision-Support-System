"""
Document Generator API — KSERC Truing-Up Order Generation Endpoint.

Provides endpoints for:
- Generating draft/final Truing-Up Orders
- Validating order can be finalized
- Downloading order as HTML/PDF
- Previewing order before generation
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.security.auth import get_current_user, require_permission, TokenData
from backend.engine.document_generator import (
    KSERCOrderGenerator, OrderMetadata, DecisionItem, 
    DecisionMode, DecisionType, GeneratedOrder
)

router = APIRouter(prefix="/orders", tags=["Order Generation"])


# ─── Request/Response Models ───

class DecisionInput(BaseModel):
    """Input decision item for order generation."""
    sbu_code: str
    cost_head: str
    financial_year: str
    petition_value: float
    approved_value: float
    actual_value: Optional[float] = None
    final_value: float
    ai_recommendation: str
    ai_value: float
    officer_decision: Optional[str] = None
    officer_value: Optional[float] = None
    decision_mode: str
    ai_justification: str
    officer_justification: Optional[str] = None
    regulatory_clause: str
    external_factor_category: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class GenerateOrderRequest(BaseModel):
    """Request to generate a Truing-Up Order."""
    order_id: str = Field(..., description="Unique order identifier")
    financial_year: str = Field(..., description="Financial year e.g., 2024-25")
    sbu_code: str = Field(..., description="SBU code: SBU-G, SBU-T, SBU-D")
    utility_name: Optional[str] = "Kerala State Electricity Board Ltd. (KSEBL)"
    
    decisions: List[DecisionInput]
    
    # Approval Chain
    prepared_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    
    # Force draft mode (optional)
    force_draft: bool = False


class GenerateOrderResponse(BaseModel):
    """Response from order generation."""
    order_id: str
    status: str  # "DRAFT" or "FINAL"
    can_finalize: bool
    has_pending_decisions: bool
    html_content: str
    checksum: str
    generated_at: str
    warnings: List[str]
    blocking_issues: List[str]


class ValidateOrderResponse(BaseModel):
    """Response from order validation."""
    can_finalize: bool
    total_decisions: int
    pending_count: int
    manual_override_count: int
    ai_auto_count: int
    issues: List[str]


class OrderSummaryResponse(BaseModel):
    """Summary of orders in the system."""
    drafts: int
    finalized: int
    by_sbu: Dict[str, int]


# ─── In-Memory Store ───
_order_store: Dict[str, Dict[str, Any]] = {}


def _to_decision_items(inputs: List[DecisionInput]) -> List[DecisionItem]:
    """Convert API input to DecisionItem objects."""
    items = []
    for inp in inputs:
        # Determine decision marker
        if inp.decision_mode == DecisionMode.AI_AUTO.value:
            marker = "[A]"
        elif inp.decision_mode == DecisionMode.MANUAL_OVERRIDE.value:
            marker = "[M]"
        else:
            marker = "[P]"
        
        items.append(DecisionItem(
            sbu_code=inp.sbu_code,
            cost_head=inp.cost_head,
            financial_year=inp.financial_year,
            petition_value=inp.petition_value,
            approved_value=inp.approved_value,
            actual_value=inp.actual_value,
            final_value=inp.final_value,
            ai_recommendation=inp.ai_recommendation,
            ai_value=inp.ai_value,
            officer_decision=inp.officer_decision,
            officer_value=inp.officer_value,
            decision_mode=inp.decision_mode,
            ai_justification=inp.ai_justification,
            officer_justification=inp.officer_justification,
            regulatory_clause=inp.regulatory_clause,
            external_factor_category=inp.external_factor_category,
            created_by=inp.created_by,
            created_at=inp.created_at,
            decision_marker=marker
        ))
    return items


# ─── API Endpoints ───

@router.post("/generate", response_model=GenerateOrderResponse)
async def generate_order(
    req: GenerateOrderRequest,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.generate")),
):
    """
    Generate a KSERC Truing-Up Order (Draft or Final).
    
    Hard Rule: If any pending decisions exist, order is always DRAFT.
    """
    generator = KSERCOrderGenerator()
    
    # Convert inputs
    decision_items = _to_decision_items(req.decisions)
    
    # Check for pending decisions
    pending_count = sum(1 for d in decision_items if d.decision_mode == DecisionMode.PENDING_MANUAL.value)
    has_pending = pending_count > 0
    
    # Validate can finalize
    can_finalize, issues = generator.validate_order_can_finalize(decision_items)
    
    if not req.force_draft and not can_finalize:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Cannot finalize order — pending manual decisions or blocking issues found",
                "issues": issues
            }
        )
    
    # Calculate totals
    total_approved = sum(d.approved_value for d in decision_items)
    total_actual = sum(d.actual_value or 0 for d in decision_items)
    total_gap = total_actual - total_approved
    
    # Build metadata
    metadata = OrderMetadata(
        order_id=req.order_id,
        financial_year=req.financial_year,
        sbu_code=req.sbu_code,
        order_date=datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        utility_name=req.utility_name,
        is_draft=has_pending or req.force_draft,
        has_pending_decisions=has_pending,
        prepared_by=req.prepared_by,
        reviewed_by=req.reviewed_by,
        approved_by=req.approved_by,
        total_approved_arr=total_approved,
        total_actual_arr=total_actual,
        total_revenue_gap=total_gap,
        total_disallowed=sum(d.final_value for d in decision_items if d.decision_mode == DecisionMode.MANUAL_OVERRIDE.value and d.officer_decision == DecisionType.DISALLOW.value),
        total_passed_through=sum(d.final_value for d in decision_items if d.decision_mode == DecisionMode.AI_AUTO.value)
    )
    
    # Generate order
    result = generator.generate(metadata, decision_items)
    
    # Store order
    _order_store[req.order_id] = {
        "order_id": req.order_id,
        "metadata": metadata,
        "decisions": decision_items,
        "generated": result.generated_at,
        "checksum": result.checksum,
        "html": result.html_content,
        "is_draft": result.is_draft,
        "can_finalize": result.can_finalize
    }
    
    warnings = []
    if has_pending:
        warnings.append(f"{pending_count} pending decisions detected — order is DRAFT")
    if req.force_draft:
        warnings.append("Draft mode forced by request")
    
    return GenerateOrderResponse(
        order_id=result.order_id,
        status="DRAFT" if result.is_draft else "FINAL",
        can_finalize=result.can_finalize,
        has_pending_decisions=result.has_pending,
        html_content=result.html_content,
        checksum=result.checksum,
        generated_at=result.generated_at,
        warnings=warnings,
        blocking_issues=issues if issues else []
    )


@router.get("/validate/{order_id}", response_model=ValidateOrderResponse)
async def validate_order(
    order_id: str,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Validate if an order can be finalized.
    Checks for pending decisions and missing justifications.
    """
    order = _order_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    
    decisions = order.get("decisions", [])
    generator = KSERCOrderGenerator()
    can_finalize, issues = generator.validate_order_can_finalize(decisions)
    
    pending = sum(1 for d in decisions if d.decision_mode == DecisionMode.PENDING_MANUAL.value)
    manual = sum(1 for d in decisions if d.decision_mode == DecisionMode.MANUAL_OVERRIDE.value)
    ai_auto = sum(1 for d in decisions if d.decision_mode == DecisionMode.AI_AUTO.value)
    
    return ValidateOrderResponse(
        can_finalize=can_finalize,
        total_decisions=len(decisions),
        pending_count=pending,
        manual_override_count=manual,
        ai_auto_count=ai_auto,
        issues=issues
    )


@router.post("/finalize/{order_id}")
async def finalize_order(
    order_id: str,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.finalize")),
):
    """
    Finalize a draft order.
    
    HARD RULE: Cannot finalize if pending decisions exist.
    """
    order = _order_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    
    if not order.get("is_draft", True):
        raise HTTPException(status_code=409, detail="Order is already finalized")
    
    # Validate
    decisions = order.get("decisions", [])
    generator = KSERCOrderGenerator()
    can_finalize, issues = generator.validate_order_can_finalize(decisions)
    
    if not can_finalize:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Cannot finalize order — pending manual decisions or blocking issues found",
                "issues": issues
            }
        )
    
    # Update order status
    order["is_draft"] = False
    order["finalized_at"] = datetime.now(timezone.utc).isoformat()
    order["finalized_by"] = current_user.username
    
    return {
        "order_id": order_id,
        "status": "FINALIZED",
        "finalized_at": order["finalized_at"],
        "finalized_by": order["finalized_by"]
    }


@router.get("/{order_id}/preview")
async def preview_order(
    order_id: str,
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Get HTML preview of an order.
    """
    order = _order_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    
    return {
        "order_id": order_id,
        "html": order.get("html", ""),
        "is_draft": order.get("is_draft", True),
        "checksum": order.get("checksum", "")
    }


@router.get("/summary", response_model=OrderSummaryResponse)
async def get_orders_summary(
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Get summary of all orders in the system.
    """
    drafts = sum(1 for o in _order_store.values() if o.get("is_draft", True))
    finalized = sum(1 for o in _order_store.values() if not o.get("is_draft", True))
    
    by_sbu = {}
    for order in _order_store.values():
        sbu = order.get("metadata", {}).sbu_code if hasattr(order.get("metadata"), "sbu_code") else "UNKNOWN"
        by_sbu[sbu] = by_sbu.get(sbu, 0) + 1
    
    return OrderSummaryResponse(
        drafts=drafts,
        finalized=finalized,
        by_sbu=by_sbu
    )
