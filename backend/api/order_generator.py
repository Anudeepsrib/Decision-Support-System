"""
Document Generator API — KSERC Truing-Up Order Generation Endpoint.

Provides endpoints for:
- Generating draft/final Truing-Up Orders
- Validating order can be finalized
- Downloading order as HTML/PDF
- Previewing order before generation
- PDF Generation with versioning and audit logging
- DEMO MODE: Bypasses validation, always generates DRAFT, auto-login
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pathlib import Path
import os

from sqlalchemy.orm import Session

from backend.security.auth import get_current_user, require_permission, TokenData
from backend.models.database import get_db
from backend.models.schema import (
    GeneratedDocument, DocumentGenerationMode, DocumentStatus,
    PetitionData, OverrideAuditLog, SBUType
)
from backend.engine.document_generator import (
    KSERCOrderGenerator, OrderMetadata, DecisionItem, 
    DecisionMode, DecisionType, GeneratedOrder,
    generate_truing_up_order_pdf, WEASYPRINT_AVAILABLE
)
from backend.config.settings import is_demo_mode, get_demo_user

router = APIRouter(prefix="/api/v1", tags=["Order Generation"])

# Configuration
GENERATED_DOCS_PATH = Path(os.getenv("GENERATED_DOCS_PATH", "./generated_docs"))

# Ensure the generated_docs directory exists
GENERATED_DOCS_PATH.mkdir(parents=True, exist_ok=True)

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


class GeneratePDFRequest(BaseModel):
    """Request to generate PDF for a case."""
    mode: str = Field(..., description="DRAFT or FINAL")


class GeneratePDFResponse(BaseModel):
    """Response from PDF generation."""
    status: str = "success"
    version: str
    mode: str
    download_url: str


class DocumentHistoryItem(BaseModel):
    """Single document in the version history."""
    document_id: UUID
    version: str
    mode: str
    file_hash: str
    file_size: int
    generated_at: str
    generated_by: str
    download_count: int
    is_finalized: bool


class DocumentHistoryResponse(BaseModel):
    """Response with document version history."""
    case_id: UUID
    order_id: str
    total_documents: int
    documents: List[DocumentHistoryItem]


class ValidateOrderResponse(BaseModel):
    """Response from order validation."""
    can_finalize: bool
    total_decisions: int
    pending_count: int
    manual_override_count: int
    ai_auto_count: int
    issues: List[str]


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


@router.get("/summary")
async def get_orders_summary(
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Get summary of all orders in the system.
    """
    drafts = 0
    finalized = 0
    by_sbu = {}
    
    return {
        "drafts": drafts,
        "finalized": finalized,
        "by_sbu": by_sbu
    }


def _log_pdf_audit_event(
    db: Session,
    action_type: str,
    entity_id: UUID,
    current_user: TokenData,
    change_reason: Optional[str] = None,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None
):
    """Log PDF-related events to OverrideAuditLog."""
    audit_entry = OverrideAuditLog(
        id=uuid4(),
        action_type=action_type,
        entity_type="GeneratedDocument",
        entity_id=entity_id,
        officer_name=current_user.username if current_user else "System",
        officer_role=current_user.role if hasattr(current_user, 'role') else None,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        change_reason=change_reason,
        justification_provided=True
    )
    db.add(audit_entry)
    db.commit()


@router.post("/cases/{case_id}/generate-pdf", response_model=GeneratePDFResponse)
async def generate_pdf(
    case_id: UUID,
    req: GeneratePDFRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.generate")),
):
    """
    Generate PDF for a case (Draft or Final).
    
    HARD RULE: Cannot generate FINAL PDF if any PENDING_MANUAL decisions exist.
    Returns HTTP 409 if attempting to generate FINAL with pending items.
    
    DEMO MODE: Always generates DRAFT, bypasses validation, FINAL never allowed.
    """
    # DEMO MODE: Force DRAFT mode and bypass validation
    if is_demo_mode():
        mode = "DRAFT"  # Force DRAFT in demo mode
        # Safety guard: FINAL PDF never allowed in demo mode
        if req.mode.upper() == "FINAL":
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "DEMO MODE: FINAL PDF generation is not allowed.",
                    "note": "Demo mode only supports DRAFT PDF generation for demonstration purposes."
                }
            )
    else:
        # Validate mode (production)
        mode = req.mode.upper()
        if mode not in ["DRAFT", "FINAL"]:
            raise HTTPException(status_code=400, detail="Mode must be DRAFT or FINAL")
    
    # Check for WeasyPrint availability
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="PDF generation service not available. WeasyPrint not installed."
        )
    
    # Get case data and decisions from database
    case = db.query(PetitionData).filter(PetitionData.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    # For now, we'll need to get decisions from the AI decisions table
    # This is a simplified implementation - in production you'd build the decisions from case data
    from backend.models.schema import AIDecision, DeviationReport, DecisionMode
    
    # Get AI decisions for this case
    ai_decisions = db.query(AIDecision).join(AIDecision.deviation_report).filter(
        DeviationReport.case_id == case_id
    ).all()
    
    # Convert to DecisionItem format
    decision_items = []
    for ai_dec in ai_decisions:
        dr = ai_dec.deviation_report
        # Determine decision marker
        if ai_dec.decision_mode == DecisionMode.AI_AUTO:
            marker = "[A]"
        elif ai_dec.decision_mode == DecisionMode.MANUAL_OVERRIDE.value:
            marker = "[M]"
        else:
            marker = "[P]"
        
        decision_items.append(DecisionItem(
            sbu_code=dr.sbu_code.value,
            cost_head=dr.cost_head.value,
            financial_year=dr.financial_year,
            petition_value=dr.petition_value,
            approved_value=dr.approved_value,
            actual_value=dr.actual_value,
            final_value=dr.actual_value or dr.approved_value,
            ai_recommendation=ai_dec.decision.value,
            ai_value=ai_dec.recommended_value,
            officer_decision=None,  # Would come from ManualJustification
            officer_value=None,
            decision_mode=ai_dec.decision_mode.value,
            ai_justification=ai_dec.ai_justification,
            officer_justification=None,
            regulatory_clause=ai_dec.regulatory_clause,
            external_factor_category=ai_dec.external_factor_category.value if ai_dec.external_factor_category else None,
            created_by=None,
            created_at=None,
            decision_marker=marker
        ))
    
    # Check for pending decisions (HARD RULE) - bypassed in DEMO MODE
    pending_count = sum(1 for d in decision_items if d.decision_mode == DecisionMode.PENDING_MANUAL.value)
    has_pending = pending_count > 0
    
    # HARD RULE: Block FINAL generation if pending items exist (PRODUCTION only)
    if not is_demo_mode() and mode == "FINAL" and has_pending:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Cannot generate FINAL PDF - pending manual decisions exist",
                "pending_count": pending_count,
                "blocking_items": [
                    {"cost_head": d.cost_head, "decision_mode": d.decision_mode}
                    for d in decision_items if d.decision_mode == DecisionMode.PENDING_MANUAL.value
                ]
            }
        )
    
    # Determine version
    existing_docs = db.query(GeneratedDocument).filter(
        GeneratedDocument.case_id == case_id
    ).order_by(GeneratedDocument.generated_at.desc()).all()
    
    version = "v1"
    if existing_docs:
        # Extract version number and increment
        last_version = existing_docs[0].version
        try:
            version_num = int(last_version.replace("v", ""))
            version = f"v{version_num + 1}"
        except ValueError:
            version = f"v{len(existing_docs) + 1}"
    
    # Generate file path
    order_id = f"ORDER-{case.sbu_code.value}-{case.financial_year}"
    safe_order_id = re.sub(r'[^\w\-]', '_', order_id)
    filename = f"{safe_order_id}_{version}_{mode}.pdf"
    case_dir = GENERATED_DOCS_PATH / str(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)
    output_path = case_dir / filename
    
    # Build metadata
    # DEMO MODE: Use demo user info
    demo_user = get_demo_user() if is_demo_mode() else None
    prepared_by = demo_user["username"] if demo_user else (current_user.username if current_user else "System")
    
    metadata = OrderMetadata(
        order_id=order_id,
        financial_year=case.financial_year,
        sbu_code=case.sbu_code.value,
        order_date=datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        utility_name="Kerala State Electricity Board Ltd. (KSEBL)",
        is_draft=True,  # Always draft in demo mode
        has_pending_decisions=has_pending,
        prepared_by=prepared_by,
        reviewed_by="",
        approved_by="",
        total_approved_arr=case.approved_arr,
        total_actual_arr=case.claimed_arr,
        total_revenue_gap=case.claimed_revenue_gap,
        total_disallowed=0.0,
        total_passed_through=0.0
    )
    
    # Generate PDF
    try:
        file_path, file_hash, file_size = generate_truing_up_order_pdf(
            metadata=metadata,
            decisions=decision_items,
            output_path=str(output_path),
            is_draft=(mode == "DRAFT")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    
    # Create database record
    # DEMO MODE: Add is_demo flag to document
    document = GeneratedDocument(
        id=uuid4(),
        case_id=case_id,
        version=version,
        mode=DocumentGenerationMode.DRAFT,  # Always DRAFT in demo
        document_status=DocumentStatus.DRAFT_GENERATED,
        file_path=str(file_path),
        file_hash=file_hash,
        file_size=file_size,
        generated_by=prepared_by,
        generated_at=datetime.utcnow(),
        order_id=order_id,
        financial_year=case.financial_year,
        sbu_code=case.sbu_code,
        is_finalized=False,  # Never finalized in demo
        finalized_at=None
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Log audit event
    _log_pdf_audit_event(
        db=db,
        action_type=f"PDF_GENERATED_{mode}",
        entity_id=document.id,
        current_user=current_user,
        change_reason=f"Generated {mode} PDF for case {case_id}{' [DEMO MODE]' if is_demo_mode() else ''}",
        field_changed="document",
        new_value=str(document.id)
    )
    
    # Build download URL
    download_url = f"/api/v1/cases/{case_id}/download-pdf?version={version}"
    
    return GeneratePDFResponse(
        status="success",
        version=version,
        mode=mode,
        download_url=download_url
    )


@router.get("/cases/{case_id}/download-pdf")
async def download_pdf(
    case_id: UUID,
    version: Optional[str] = Query(None, description="Version to download (e.g., v1, v2)"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Download a generated PDF by version.
    
    Query Parameters:
    - version: Version string (e.g., v1, v2). If not provided, downloads latest.
    """
    # Find document
    if version:
        document = db.query(GeneratedDocument).filter(
            GeneratedDocument.case_id == case_id,
            GeneratedDocument.version == version
        ).first()
    else:
        # Get latest document
        document = db.query(GeneratedDocument).filter(
            GeneratedDocument.case_id == case_id
        ).order_by(GeneratedDocument.generated_at.desc()).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file not found on disk at {file_path}")
    
    # Additional check for file readability
    try:
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise HTTPException(status_code=500, detail="PDF file is empty")
    except OSError:
        raise HTTPException(status_code=500, detail=f"Cannot access PDF file at {file_path}")
    
    # Update download tracking
    document.download_count += 1
    document.last_downloaded_at = datetime.utcnow()
    db.commit()
    
    # Log audit event
    _log_pdf_audit_event(
        db=db,
        action_type="PDF_DOWNLOAD",
        entity_id=document.id,
        current_user=current_user,
        change_reason=f"Downloaded PDF {document.version} for case {case_id}"
    )
    
    # Return file
    return FileResponse(
        path=document.file_path,
        filename=f"KSERC_Order_{document.order_id}_{document.version}_{document.mode.value}.pdf",
        media_type="application/pdf"
    )


@router.get("/cases/{case_id}/documents", response_model=DocumentHistoryResponse)
async def get_document_history(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Get version history of all generated documents for a case.
    """
    documents = db.query(GeneratedDocument).filter(
        GeneratedDocument.case_id == case_id
    ).order_by(GeneratedDocument.generated_at.desc()).all()
    
    if not documents:
        return DocumentHistoryResponse(
            case_id=case_id,
            order_id="",
            total_documents=0,
            documents=[]
        )
    
    document_items = [
        DocumentHistoryItem(
            document_id=doc.id,
            version=doc.version,
            mode=doc.mode.value,
            file_hash=doc.file_hash,
            file_size=doc.file_size,
            generated_at=doc.generated_at.isoformat(),
            generated_by=doc.generated_by,
            download_count=doc.download_count,
            is_finalized=doc.is_finalized
        )
        for doc in documents
    ]
    
    return DocumentHistoryResponse(
        case_id=case_id,
        order_id=documents[0].order_id,
        total_documents=len(documents),
        documents=document_items
    )


@router.get("/cases/{case_id}/latest-pdf")
async def download_latest_pdf(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("orders.read")),
):
    """
    Download the most recent PDF for a case.
    """
    document = db.query(GeneratedDocument).filter(
        GeneratedDocument.case_id == case_id
    ).order_by(GeneratedDocument.generated_at.desc()).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="No documents found for this case")
    
    if not Path(document.file_path).exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    
    # Update download tracking
    document.download_count += 1
    document.last_downloaded_at = datetime.utcnow()
    db.commit()
    
    # Log audit event
    _log_pdf_audit_event(
        db=db,
        action_type="PDF_DOWNLOAD",
        entity_id=document.id,
        current_user=current_user,
        change_reason=f"Downloaded latest PDF {document.version} for case {case_id}"
    )
    
    return FileResponse(
        path=document.file_path,
        filename=f"KSERC_Order_{document.order_id}_{document.version}_{document.mode.value}.pdf",
        media_type="application/pdf"
    )
