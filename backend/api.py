"""
MVP API Routes — All REST endpoints for the KSERC DSS MVP.

Endpoints:
  POST /api/documents/upload       — Upload a PDF
  GET  /api/documents              — List all documents
  GET  /api/extraction/{doc_id}    — Get extraction results
  POST /api/extraction/{doc_id}/run — Run extraction on a document
  GET  /api/comparison/{case_id}   — Get comparison results
  POST /api/comparison/run         — Run comparison
  POST /api/review/{comp_id}       — Submit officer review
  GET  /api/review/{case_id}/all   — Get all reviews for a case
  POST /api/generate               — Generate PDF order
  GET  /api/generate/{order_id}/download — Download generated PDF
  GET  /api/audit                  — Get audit trail
"""

import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Document, ExtractedRow, NormalizedLineItem, Comparison, Review, GeneratedOrder
)
from schemas import (
    DocumentUploadResponse, DocumentListItem,
    ExtractionResultResponse, ExtractedRowResponse,
    ComparisonResponse, ComparisonItemResponse,
    ReviewRequest, ReviewResponse,
    GenerateOrderRequest, GeneratedOrderResponse,
    NormalizedItemResponse, AuditEntry,
)
from extractor import extract_tables_from_pdf, get_page_count
from normalizer import normalize_row_label
from comparison import run_comparison, calculate_variance, classify_decision
from prompts import generate_variance_explanation

router = APIRouter(prefix="/api", tags=["MVP API"])

# Upload directory
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mvp_uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── 1. Document Upload ───

@router.post("/upload/arr", response_model=DocumentUploadResponse)
async def upload_arr_document(
    file: UploadFile = File(...),
    financial_year: str = Form("2024-25"),
    db: Session = Depends(get_db),
):
    """Upload ARR Approval Order PDF and auto-extract tables."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")
    
    # Save file
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Get page count
    try:
        page_count = get_page_count(contents)
    except Exception:
        page_count = None
    
    # Save to DB
    doc = Document(
        id=doc_id,
        filename=file.filename,
        doc_type="arr_order",
        financial_year=financial_year,
        file_path=file_path,
        file_size=file_size,
        page_count=page_count,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    
    # Auto-extract tables after upload
    status = "uploaded"
    try:
        extracted = extract_tables_from_pdf(contents, file.filename)
        db.query(ExtractedRow).filter(ExtractedRow.document_id == doc_id).delete()
        for row_data in extracted:
            row = ExtractedRow(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                page_number=row_data.page_number,
                table_index=row_data.table_index,
                table_name=row_data.table_name,
                row_label=row_data.row_label,
                value=row_data.value,
                confidence=row_data.confidence,
                extraction_method="pdfplumber",
                raw_text=row_data.raw_text,
            )
            db.add(row)
        for row_data in extracted:
            norm = normalize_row_label(row_data.row_label)
            norm_item = NormalizedLineItem(
                id=str(uuid.uuid4()),
                canonical_name=norm.canonical_name,
                category=norm.category,
                cost_head=norm.cost_head,
                source_doc_type="arr_order",
                financial_year=financial_year,
                value=row_data.value,
                mapping_confidence=norm.confidence,
                mapping_method=norm.method,
            )
            db.add(norm_item)
        doc.status = "extracted"
        status = "extracted"
        db.commit()
    except Exception as e:
        print(f"[MVP] Auto-extraction failed for ARR: {e}")
    
    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        doc_type="arr_order",
        file_size=file_size,
        page_count=page_count,
        status=status,
    )


@router.post("/upload/petition", response_model=DocumentUploadResponse)
async def upload_petition_document(
    file: UploadFile = File(...),
    financial_year: str = Form("2024-25"),
    db: Session = Depends(get_db),
):
    """Upload Truing-Up Petition PDF and auto-extract tables."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")
    
    # Save file
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Get page count
    try:
        page_count = get_page_count(contents)
    except Exception:
        page_count = None
    
    # Save to DB
    doc = Document(
        id=doc_id,
        filename=file.filename,
        doc_type="truing_up_petition",
        financial_year=financial_year,
        file_path=file_path,
        file_size=file_size,
        page_count=page_count,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    
    # Auto-extract tables after upload
    status = "uploaded"
    try:
        extracted = extract_tables_from_pdf(contents, file.filename)
        db.query(ExtractedRow).filter(ExtractedRow.document_id == doc_id).delete()
        for row_data in extracted:
            row = ExtractedRow(
                id=str(uuid.uuid4()),
                document_id=doc_id,
                page_number=row_data.page_number,
                table_index=row_data.table_index,
                table_name=row_data.table_name,
                row_label=row_data.row_label,
                value=row_data.value,
                confidence=row_data.confidence,
                extraction_method="pdfplumber",
                raw_text=row_data.raw_text,
            )
            db.add(row)
        for row_data in extracted:
            norm = normalize_row_label(row_data.row_label)
            norm_item = NormalizedLineItem(
                id=str(uuid.uuid4()),
                canonical_name=norm.canonical_name,
                category=norm.category,
                cost_head=norm.cost_head,
                source_doc_type="truing_up_petition",
                financial_year=financial_year,
                value=row_data.value,
                mapping_confidence=norm.confidence,
                mapping_method=norm.method,
            )
            db.add(norm_item)
        doc.status = "extracted"
        status = "extracted"
        db.commit()
    except Exception as e:
        print(f"[MVP] Auto-extraction failed for Petition: {e}")
    
    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        doc_type="truing_up_petition",
        file_size=file_size,
        page_count=page_count,
        status=status,
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("arr_order"),  # arr_order | truing_up_petition
    financial_year: str = Form("2024-25"),
    db: Session = Depends(get_db),
):
    """Legacy upload endpoint - use /upload/arr or /upload/petition instead."""
    return await upload_arr_document(file, financial_year, db) if doc_type == "arr_order" else await upload_petition_document(file, financial_year, db)


@router.get("/documents", response_model=List[DocumentListItem])
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents."""
    docs = db.query(Document).order_by(Document.upload_timestamp.desc()).all()
    return [
        DocumentListItem(
            id=d.id,
            filename=d.filename,
            doc_type=d.doc_type,
            financial_year=d.financial_year,
            file_size=d.file_size,
            page_count=d.page_count,
            status=d.status,
            upload_timestamp=d.upload_timestamp,
        )
        for d in docs
    ]


# ─── 2. Extraction ───

@router.post("/extraction/{doc_id}/run", response_model=ExtractionResultResponse)
async def run_extraction(doc_id: str, db: Session = Depends(get_db)):
    """Run table extraction on an uploaded document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Read PDF bytes
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")
    
    with open(doc.file_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Run extraction
    try:
        extracted = extract_tables_from_pdf(pdf_bytes, doc.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    
    # Clear existing rows for this document
    db.query(ExtractedRow).filter(ExtractedRow.document_id == doc_id).delete()
    
    # Save extracted rows
    rows = []
    for row_data in extracted:
        row = ExtractedRow(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            page_number=row_data.page_number,
            table_index=row_data.table_index,
            table_name=row_data.table_name,
            row_label=row_data.row_label,
            value=row_data.value,
            confidence=row_data.confidence,
            extraction_method="pdfplumber",
            raw_text=row_data.raw_text,
        )
        db.add(row)
        rows.append(row)
    
    # Also normalize and save normalized items
    for row_data in extracted:
        norm = normalize_row_label(row_data.row_label)
        norm_item = NormalizedLineItem(
            id=str(uuid.uuid4()),
            canonical_name=norm.canonical_name,
            category=norm.category,
            cost_head=norm.cost_head,
            source_doc_type=doc.doc_type,
            financial_year=doc.financial_year,
            value=row_data.value,
            mapping_confidence=norm.confidence,
            mapping_method=norm.method,
        )
        db.add(norm_item)
    
    # Update document status
    doc.status = "extracted"
    db.commit()
    
    # Build response
    review_count = sum(1 for r in rows if r.confidence < 0.6)
    
    return ExtractionResultResponse(
        document_id=doc_id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        total_pages=doc.page_count or 0,
        total_rows_extracted=len(rows),
        rows_needing_review=review_count,
        extraction_method="pdfplumber",
        rows=[
            ExtractedRowResponse(
                id=r.id,
                page_number=r.page_number,
                table_index=r.table_index,
                table_name=r.table_name,
                row_label=r.row_label,
                value=r.value,
                unit=r.unit,
                confidence=r.confidence,
                extraction_method=r.extraction_method,
                raw_text=r.raw_text,
            )
            for r in rows
        ],
    )


@router.get("/extraction/{doc_id}", response_model=ExtractionResultResponse)
async def get_extraction_results(doc_id: str, db: Session = Depends(get_db)):
    """Get extraction results for a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    rows = db.query(ExtractedRow).filter(ExtractedRow.document_id == doc_id).all()
    review_count = sum(1 for r in rows if r.confidence < 0.6)
    
    return ExtractionResultResponse(
        document_id=doc_id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        total_pages=doc.page_count or 0,
        total_rows_extracted=len(rows),
        rows_needing_review=review_count,
        extraction_method="pdfplumber",
        rows=[
            ExtractedRowResponse(
                id=r.id,
                page_number=r.page_number,
                table_index=r.table_index,
                table_name=r.table_name,
                row_label=r.row_label,
                value=r.value,
                unit=r.unit or "Rs. Cr.",
                confidence=r.confidence,
                extraction_method=r.extraction_method or "pdfplumber",
                raw_text=r.raw_text,
            )
            for r in rows
        ],
    )


# ─── 3. Comparison ───

@router.post("/comparison/run", response_model=ComparisonResponse)
async def run_comparison_endpoint(
    financial_year: str = "2024-25",
    db: Session = Depends(get_db),
):
    """
    Run three-way comparison: ARR Approved vs Petition Actual vs Petition Claimed.
    Uses normalized line items from both uploaded documents.
    """
    case_id = str(uuid.uuid4())
    
    # Get ARR approved items
    arr_items = db.query(NormalizedLineItem).filter(
        NormalizedLineItem.source_doc_type == "arr_order",
        NormalizedLineItem.financial_year == financial_year,
    ).all()
    
    # Get petition actual items
    petition_actual_items = db.query(NormalizedLineItem).filter(
        NormalizedLineItem.source_doc_type == "truing_up_petition",
        NormalizedLineItem.value_type == "actual",
        NormalizedLineItem.financial_year == financial_year,
    ).all()
    
    # Get petition claimed items
    petition_claimed_items = db.query(NormalizedLineItem).filter(
        NormalizedLineItem.source_doc_type == "truing_up_petition",
        NormalizedLineItem.value_type == "claimed",
        NormalizedLineItem.financial_year == financial_year,
    ).all()
    
    # If no value_type specified, treat all petition items as both actual and claimed
    if not petition_actual_items and not petition_claimed_items:
        petition_items = db.query(NormalizedLineItem).filter(
            NormalizedLineItem.source_doc_type == "truing_up_petition",
            NormalizedLineItem.financial_year == financial_year,
        ).all()
        petition_actual_items = petition_items
        petition_claimed_items = petition_items
    
    if not arr_items:
        raise HTTPException(
            status_code=404,
            detail="No ARR data found. Please upload and extract ARR Order first."
        )
    
    if not petition_actual_items:
        raise HTTPException(
            status_code=404,
            detail="No Petition data found. Please upload and extract Petition first."
        )
    
    # Clear existing comparisons for this case
    db.query(Comparison).filter(Comparison.case_id == case_id).delete()
    
    # Build lookup dictionaries
    arr_lookup = {item.canonical_name: item for item in arr_items}
    actual_lookup = {item.canonical_name: item for item in petition_actual_items}
    claimed_lookup = {item.canonical_name: item for item in petition_claimed_items}
    
    # Union of all canonical names
    all_names = set(arr_lookup.keys()) | set(actual_lookup.keys()) | set(claimed_lookup.keys())
    
    results = []
    
    for name in sorted(all_names):
        arr_item = arr_lookup.get(name)
        actual_item = actual_lookup.get(name)
        claimed_item = claimed_lookup.get(name)
        
        approved_val = arr_item.value if arr_item else None
        actual_val = actual_item.value if actual_item else None
        claimed_val = claimed_item.value if claimed_item else None
        
        # Calculate variance (actual vs approved)
        variance, variance_pct = calculate_variance(approved_val, actual_val)
        
        # Get confidence (min of all available sources)
        confidences = []
        if arr_item and arr_item.mapping_confidence:
            confidences.append(arr_item.mapping_confidence)
        if actual_item and actual_item.mapping_confidence:
            confidences.append(actual_item.mapping_confidence)
        if claimed_item and claimed_item.mapping_confidence:
            confidences.append(claimed_item.mapping_confidence)
        
        confidence = min(confidences) if confidences else 1.0
        
        # Classify decision
        decision_class, flag_reason = classify_decision(variance_pct, confidence)
        
        cost_head = (
            (arr_item.cost_head if arr_item else None) or 
            (actual_item.cost_head if actual_item else None) or 
            (claimed_item.cost_head if claimed_item else None) or 
            "Other"
        )
        
        # Create comparison record
        comp = Comparison(
            id=str(uuid.uuid4()),
            case_id=case_id,
            financial_year=financial_year,
            canonical_name=name,
            cost_head=cost_head,
            approved_value=approved_val,
            actual_value=actual_val,
            claimed_value=claimed_val,
            variance=variance,
            variance_percent=variance_pct,
            decision_class=decision_class,
            flag_reason=flag_reason,
            approved_source_page=None,
            actual_source_page=None,
        )
        db.add(comp)
        results.append(comp)
    
    db.commit()
    
    # Build response
    auto_count = sum(1 for r in results if r.decision_class == "AI_AUTO")
    review_count = len(results) - auto_count
    total_var = sum(r.variance or 0 for r in results)
    
    return ComparisonResponse(
        case_id=case_id,
        financial_year=financial_year,
        total_items=len(results),
        auto_approved=auto_count,
        review_required=review_count,
        total_variance=round(total_var, 2),
        items=[
            ComparisonItemResponse(
                id=r.id,
                canonical_name=r.canonical_name,
                cost_head=r.cost_head,
                approved_value=r.approved_value,
                actual_value=r.actual_value,
                claimed_value=r.claimed_value,
                variance=r.variance,
                variance_percent=r.variance_percent,
                decision_class=r.decision_class,
                flag_reason=r.flag_reason,
                approved_source_page=r.approved_source_page,
                actual_source_page=r.actual_source_page,
            )
            for r in results
        ],
    )


@router.get("/comparison/{case_id}", response_model=ComparisonResponse)
async def get_comparison(case_id: str, db: Session = Depends(get_db)):
    """Get comparison results for a case."""
    comparisons = db.query(Comparison).filter(Comparison.case_id == case_id).all()
    
    if not comparisons:
        raise HTTPException(status_code=404, detail="Case not found.")
    
    auto_count = sum(1 for c in comparisons if c.decision_class == "AI_AUTO")
    review_count = len(comparisons) - auto_count
    total_var = sum(c.variance or 0 for c in comparisons)
    
    return ComparisonResponse(
        case_id=case_id,
        financial_year=comparisons[0].financial_year,
        total_items=len(comparisons),
        auto_approved=auto_count,
        review_required=review_count,
        total_variance=round(total_var, 2),
        items=[
            ComparisonItemResponse(
                id=c.id,
                canonical_name=c.canonical_name,
                cost_head=c.cost_head,
                approved_value=c.approved_value,
                actual_value=c.actual_value,
                claimed_value=c.claimed_value,
                variance=c.variance,
                variance_percent=c.variance_percent,
                decision_class=c.decision_class,
                flag_reason=c.flag_reason,
                approved_source_page=c.approved_source_page,
                actual_source_page=c.actual_source_page,
            )
            for c in comparisons
        ],
    )


@router.get("/comparison", response_model=List[ComparisonResponse])
async def list_cases(db: Session = Depends(get_db)):
    """List all comparison cases."""
    # Get unique case IDs
    cases = db.query(Comparison.case_id).distinct().all()
    
    results = []
    for (case_id,) in cases:
        comparisons = db.query(Comparison).filter(Comparison.case_id == case_id).all()
        auto_count = sum(1 for c in comparisons if c.decision_class == "AI_AUTO")
        review_count = len(comparisons) - auto_count
        total_var = sum(c.variance or 0 for c in comparisons)
        
        results.append(ComparisonResponse(
            case_id=case_id,
            financial_year=comparisons[0].financial_year if comparisons else "2024-25",
            total_items=len(comparisons),
            auto_approved=auto_count,
            review_required=review_count,
            total_variance=round(total_var, 2),
            items=[
                ComparisonItemResponse(
                    id=c.id,
                    canonical_name=c.canonical_name,
                    cost_head=c.cost_head,
                    approved_value=c.approved_value,
                    actual_value=c.actual_value,
                    claimed_value=c.claimed_value,
                    variance=c.variance,
                    variance_percent=c.variance_percent,
                    decision_class=c.decision_class,
                    flag_reason=c.flag_reason,
                )
                for c in comparisons
            ],
        ))
    
    return results


# ─── 4. Review ───

@router.post("/review/{comparison_id}", response_model=ReviewResponse)
async def submit_review(
    comparison_id: str,
    review_req: ReviewRequest,
    db: Session = Depends(get_db),
):
    """Submit an officer review for a comparison item."""
    comp = db.query(Comparison).filter(Comparison.id == comparison_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison item not found.")
    
    if review_req.action not in ("approve", "reject", "edit"):
        raise HTTPException(status_code=400, detail="Action must be: approve, reject, or edit.")
    
    # Generate AI explanation if needed
    ai_explanation = None
    if comp.approved_value and comp.actual_value and comp.variance_percent:
        ai_explanation = generate_variance_explanation(
            line_item=comp.canonical_name,
            approved_value=comp.approved_value,
            actual_value=comp.actual_value,
            variance_percent=comp.variance_percent,
            cost_head=comp.cost_head or "Other",
        )
    
    # Create review
    review = Review(
        id=str(uuid.uuid4()),
        comparison_id=comparison_id,
        action=review_req.action,
        officer_name=review_req.officer_name,
        officer_comment=review_req.officer_comment,
        edited_value=review_req.edited_value,
        ai_explanation=ai_explanation,
    )
    db.add(review)
    
    # Update comparison status
    if review_req.action == "approve":
        comp.decision_class = "AI_AUTO"
    elif review_req.action == "edit" and review_req.edited_value is not None:
        comp.actual_value = review_req.edited_value
        # Recalculate variance
        if comp.approved_value:
            comp.variance = round(review_req.edited_value - comp.approved_value, 2)
            comp.variance_percent = round(
                (review_req.edited_value - comp.approved_value) / abs(comp.approved_value) * 100, 2
            )
    
    db.commit()
    
    return ReviewResponse(
        id=review.id,
        comparison_id=comparison_id,
        action=review.action,
        officer_name=review.officer_name,
        officer_comment=review.officer_comment,
        edited_value=review.edited_value,
        ai_explanation=review.ai_explanation,
        reviewed_at=review.reviewed_at,
    )


@router.get("/review/{case_id}/all", response_model=List[ReviewResponse])
async def get_reviews(case_id: str, db: Session = Depends(get_db)):
    """Get all reviews for a case."""
    comparisons = db.query(Comparison).filter(Comparison.case_id == case_id).all()
    comp_ids = [c.id for c in comparisons]
    
    reviews = db.query(Review).filter(Review.comparison_id.in_(comp_ids)).all()
    
    return [
        ReviewResponse(
            id=r.id,
            comparison_id=r.comparison_id,
            action=r.action,
            officer_name=r.officer_name,
            officer_comment=r.officer_comment,
            edited_value=r.edited_value,
            ai_explanation=r.ai_explanation,
            reviewed_at=r.reviewed_at,
        )
        for r in reviews
    ]


# ─── 5. PDF Generation ───

@router.post("/generate", response_model=GeneratedOrderResponse)
async def generate_order(
    req: GenerateOrderRequest,
    db: Session = Depends(get_db),
):
    """Generate a KSERC-style truing-up draft order PDF."""
    from pdf_generator import generate_order_pdf, PLAYWRIGHT_AVAILABLE
    
    if not PLAYWRIGHT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Playwright is not installed. PDF generation unavailable."
        )
    
    # Get comparison data
    comparisons = db.query(Comparison).filter(
        Comparison.case_id == req.case_id
    ).all()
    
    if not comparisons:
        raise HTTPException(status_code=404, detail="Case not found.")
    
    # Get reviews
    comp_ids = [c.id for c in comparisons]
    reviews = db.query(Review).filter(Review.comparison_id.in_(comp_ids)).all()
    
    # Convert to dicts
    comp_dicts = [
        {
            "id": c.id,
            "canonical_name": c.canonical_name,
            "cost_head": c.cost_head,
            "approved_value": c.approved_value,
            "actual_value": c.actual_value,
            "variance": c.variance,
            "variance_percent": c.variance_percent,
            "decision_class": c.decision_class,
            "flag_reason": c.flag_reason,
        }
        for c in comparisons
    ]
    
    review_dicts = [
        {
            "comparison_id": r.comparison_id,
            "action": r.action,
            "officer_name": r.officer_name,
            "officer_comment": r.officer_comment,
            "edited_value": r.edited_value,
        }
        for r in reviews
    ]
    
    # Generate PDF
    try:
        result = await generate_order_pdf(
            case_id=req.case_id,
            financial_year=req.financial_year,
            comparisons=comp_dicts,
            reviews=review_dicts,
            officer_name=req.officer_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    
    # Save order record
    auto_count = sum(1 for c in comparisons if c.decision_class == "AI_AUTO")
    review_count = len(comparisons) - auto_count
    
    order = GeneratedOrder(
        id=str(uuid.uuid4()),
        case_id=req.case_id,
        financial_year=req.financial_year,
        file_path=result["file_path"],
        file_hash=result["file_hash"],
        file_size=result["file_size"],
        is_draft=True,
        total_items=len(comparisons),
        auto_approved=auto_count,
        review_required=review_count,
        generated_by=req.officer_name,
    )
    db.add(order)
    db.commit()
    
    return GeneratedOrderResponse(
        id=order.id,
        case_id=req.case_id,
        financial_year=req.financial_year,
        file_path=result["file_path"],
        file_size=result["file_size"],
        is_draft=True,
        total_items=len(comparisons),
        auto_approved=auto_count,
        review_required=review_count,
        generated_at=order.generated_at,
        download_url=f"/api/generate/{order.id}/download",
    )


@router.get("/generate/{order_id}/download")
async def download_order(order_id: str, db: Session = Depends(get_db)):
    """Download a generated PDF order."""
    order = db.query(GeneratedOrder).filter(GeneratedOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    
    if not os.path.exists(order.file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")
    
    return FileResponse(
        order.file_path,
        media_type="application/pdf",
        filename=os.path.basename(order.file_path),
    )


@router.get("/generate", response_model=List[GeneratedOrderResponse])
async def list_orders(db: Session = Depends(get_db)):
    """List all generated orders."""
    orders = db.query(GeneratedOrder).order_by(GeneratedOrder.generated_at.desc()).all()
    
    return [
        GeneratedOrderResponse(
            id=o.id,
            case_id=o.case_id,
            financial_year=o.financial_year,
            file_path=o.file_path,
            file_size=o.file_size,
            is_draft=o.is_draft,
            total_items=o.total_items,
            auto_approved=o.auto_approved,
            review_required=o.review_required,
            generated_at=o.generated_at,
            download_url=f"/api/generate/{o.id}/download",
        )
        for o in orders
    ]


# ─── 6. Audit Trail ───

@router.get("/audit", response_model=List[AuditEntry])
async def get_audit_trail(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Get audit trail of all system actions."""
    entries: List[AuditEntry] = []
    
    # Document uploads
    docs = db.query(Document).order_by(Document.upload_timestamp.desc()).limit(limit).all()
    for d in docs:
        entries.append(AuditEntry(
            timestamp=d.upload_timestamp,
            action="UPLOAD",
            entity_type="document",
            entity_id=d.id,
            details=f"Uploaded {d.filename} ({d.doc_type})",
        ))
    
    # Reviews
    reviews = db.query(Review).order_by(Review.reviewed_at.desc()).limit(limit).all()
    for r in reviews:
        entries.append(AuditEntry(
            timestamp=r.reviewed_at,
            action=f"REVIEW_{r.action.upper()}",
            entity_type="review",
            entity_id=r.id,
            details=r.officer_comment,
            officer=r.officer_name,
        ))
    
    # Generated orders
    orders = db.query(GeneratedOrder).order_by(GeneratedOrder.generated_at.desc()).limit(limit).all()
    for o in orders:
        entries.append(AuditEntry(
            timestamp=o.generated_at,
            action="GENERATE_PDF",
            entity_type="order",
            entity_id=o.id,
            details=f"Generated {'DRAFT' if o.is_draft else 'FINAL'} order for FY {o.financial_year}",
            officer=o.generated_by,
        ))
    
    # Sort all entries by timestamp
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    
    return entries[:limit]


# ─── 7. Normalized Items ───

@router.get("/normalized", response_model=List[NormalizedItemResponse])
async def list_normalized_items(
    source_doc_type: Optional[str] = None,
    financial_year: str = "2024-25",
    db: Session = Depends(get_db),
):
    """List normalized line items."""
    query = db.query(NormalizedLineItem).filter(
        NormalizedLineItem.financial_year == financial_year
    )
    if source_doc_type:
        query = query.filter(NormalizedLineItem.source_doc_type == source_doc_type)
    
    items = query.all()
    
    return [
        NormalizedItemResponse(
            id=i.id,
            canonical_name=i.canonical_name,
            category=i.category,
            cost_head=i.cost_head,
            source_doc_type=i.source_doc_type,
            value=i.value,
            unit=i.unit or "Rs. Cr.",
            mapping_confidence=i.mapping_confidence,
            mapping_method=i.mapping_method,
        )
        for i in items
    ]
