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
from typing import Dict, List, Optional, Tuple

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
from comparison import calculate_variance, classify_decision
from prompts import generate_variance_explanation

router = APIRouter(prefix="/api", tags=["MVP API"])

# Upload directory
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mvp_uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _case_id_for_year(financial_year: str) -> str:
    """Use one deterministic demo case per financial year."""
    return f"kserc-{financial_year}"


def _validate_pdf_upload(file: UploadFile, contents: bytes):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")


def _latest_extracted_document(
    db: Session,
    doc_type: str,
    financial_year: str,
) -> Optional[Document]:
    return (
        db.query(Document)
        .filter(
            Document.doc_type == doc_type,
            Document.financial_year == financial_year,
            Document.status == "extracted",
        )
        .order_by(Document.upload_timestamp.desc())
        .first()
    )


def _delete_extraction_for_document(db: Session, document_id: str):
    row_ids = [
        row_id
        for (row_id,) in db.query(ExtractedRow.id)
        .filter(ExtractedRow.document_id == document_id)
        .all()
    ]
    if row_ids:
        db.query(NormalizedLineItem).filter(
            NormalizedLineItem.extracted_row_id.in_(row_ids)
        ).delete(synchronize_session=False)
    db.query(ExtractedRow).filter(
        ExtractedRow.document_id == document_id
    ).delete(synchronize_session=False)


def _store_extraction(
    db: Session,
    doc: Document,
    pdf_bytes: bytes,
) -> List[ExtractedRow]:
    extracted = extract_tables_from_pdf(pdf_bytes, doc.filename, doc.doc_type)
    _delete_extraction_for_document(db, doc.id)

    rows: List[ExtractedRow] = []
    for row_data in extracted:
        row_id = str(uuid.uuid4())
        row = ExtractedRow(
            id=row_id,
            document_id=doc.id,
            page_number=row_data.page_number,
            table_index=row_data.table_index,
            table_name=row_data.table_name,
            row_label=row_data.row_label,
            value=row_data.value,
            value_type=row_data.value_type,
            confidence=row_data.confidence,
            extraction_method="pdfplumber",
            raw_text=row_data.raw_text,
        )
        db.add(row)
        rows.append(row)

        norm = normalize_row_label(row_data.row_label)
        norm_item = NormalizedLineItem(
            id=str(uuid.uuid4()),
            extracted_row_id=row_id,
            canonical_name=norm.canonical_name,
            category=norm.category,
            cost_head=norm.cost_head,
            source_doc_type=doc.doc_type,
            financial_year=doc.financial_year,
            value_type=row_data.value_type,
            value=row_data.value,
            mapping_confidence=min(norm.confidence, row_data.confidence),
            mapping_method=norm.method,
        )
        db.add(norm_item)

    doc.status = "extracted"
    db.commit()
    return rows


def _row_response(row: ExtractedRow, doc: Document) -> ExtractedRowResponse:
    norm = normalize_row_label(row.row_label)
    return ExtractedRowResponse(
        id=row.id,
        page_number=row.page_number,
        table_index=row.table_index,
        table_name=row.table_name,
        row_label=row.row_label,
        normalized_label=norm.canonical_name,
        value=row.value,
        value_type=row.value_type or "value",
        document_type=doc.doc_type,
        unit=row.unit or "Rs. Cr.",
        confidence=row.confidence,
        extraction_method=row.extraction_method or "pdfplumber",
        raw_text=row.raw_text,
    )


def _extraction_response(doc: Document, rows: List[ExtractedRow]) -> ExtractionResultResponse:
    review_count = sum(1 for r in rows if (r.confidence or 0) < 0.6)
    return ExtractionResultResponse(
        document_id=doc.id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        total_pages=doc.page_count or 0,
        total_rows_extracted=len(rows),
        rows_needing_review=review_count,
        extraction_method="pdfplumber",
        rows=[_row_response(r, doc) for r in rows],
    )


def _load_normalized_records(
    db: Session,
    doc: Document,
    value_type: Optional[str] = None,
) -> List[Dict]:
    query = (
        db.query(NormalizedLineItem, ExtractedRow)
        .join(ExtractedRow, NormalizedLineItem.extracted_row_id == ExtractedRow.id)
        .filter(ExtractedRow.document_id == doc.id)
    )
    if value_type:
        query = query.filter(NormalizedLineItem.value_type == value_type)

    records = []
    for item, row in query.all():
        confidence = min(
            item.mapping_confidence if item.mapping_confidence is not None else 1.0,
            row.confidence if row.confidence is not None else 1.0,
        )
        records.append({
            "canonical_name": item.canonical_name,
            "cost_head": item.cost_head,
            "value": item.value,
            "value_type": item.value_type,
            "mapping_confidence": confidence,
            "source_page": row.page_number,
            "source_table": row.table_name,
            "source_document_id": doc.id,
        })
    return records


def _best_by_name(records: List[Dict]) -> Dict[str, Dict]:
    best: Dict[str, Dict] = {}
    for record in records:
        name = record.get("canonical_name")
        if not name:
            continue
        current = best.get(name)
        if current is None:
            best[name] = record
            continue

        current_score = (
            current.get("mapping_confidence") or 0,
            1 if current.get("value") is not None else 0,
        )
        new_score = (
            record.get("mapping_confidence") or 0,
            1 if record.get("value") is not None else 0,
        )
        if new_score > current_score:
            best[name] = record
    return best


def _latest_reviews_by_comparison(db: Session, comparison_ids: List[str]) -> Dict[str, Review]:
    if not comparison_ids:
        return {}
    reviews = (
        db.query(Review)
        .filter(Review.comparison_id.in_(comparison_ids))
        .order_by(Review.reviewed_at.asc())
        .all()
    )
    return {review.comparison_id: review for review in reviews}


def _comparison_item_response(
    comparison: Comparison,
    latest_review: Optional[Review] = None,
) -> ComparisonItemResponse:
    return ComparisonItemResponse(
        id=comparison.id,
        canonical_name=comparison.canonical_name,
        cost_head=comparison.cost_head,
        approved_value=comparison.approved_value,
        actual_value=comparison.actual_value,
        claimed_value=comparison.claimed_value,
        variance=comparison.variance,
        variance_percent=comparison.variance_percent,
        decision_class=comparison.decision_class,
        flag_reason=comparison.flag_reason,
        latest_review_action=latest_review.action if latest_review else None,
        latest_review_comment=latest_review.officer_comment if latest_review else None,
        latest_reviewed_at=latest_review.reviewed_at if latest_review else None,
        approved_source_document_id=comparison.approved_source_document_id,
        actual_source_document_id=comparison.actual_source_document_id,
        claimed_source_document_id=comparison.claimed_source_document_id,
        approved_source_page=comparison.approved_source_page,
        actual_source_page=comparison.actual_source_page,
        claimed_source_page=comparison.claimed_source_page,
        approved_source_table=comparison.approved_source_table,
        actual_source_table=comparison.actual_source_table,
        claimed_source_table=comparison.claimed_source_table,
        approved_confidence=comparison.approved_confidence,
        actual_confidence=comparison.actual_confidence,
        claimed_confidence=comparison.claimed_confidence,
    )


def _comparison_response(db: Session, case_id: str) -> ComparisonResponse:
    comparisons = (
        db.query(Comparison)
        .filter(Comparison.case_id == case_id)
        .order_by(Comparison.cost_head, Comparison.canonical_name)
        .all()
    )
    if not comparisons:
        raise HTTPException(status_code=404, detail="Case not found.")

    latest_reviews = _latest_reviews_by_comparison(db, [c.id for c in comparisons])
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
            _comparison_item_response(c, latest_reviews.get(c.id))
            for c in comparisons
        ],
    )


def _run_comparison_for_financial_year(
    db: Session,
    financial_year: str = "2024-25",
) -> ComparisonResponse:
    arr_doc = _latest_extracted_document(db, "arr_order", financial_year)
    petition_doc = _latest_extracted_document(db, "truing_up_petition", financial_year)

    if not arr_doc:
        raise HTTPException(
            status_code=404,
            detail="No extracted ARR data found. Please upload ARR Order first.",
        )
    if not petition_doc:
        raise HTTPException(
            status_code=404,
            detail="No extracted Petition data found. Please upload Petition first.",
        )

    arr_lookup = _best_by_name(_load_normalized_records(db, arr_doc, "approved"))
    actual_lookup = _best_by_name(_load_normalized_records(db, petition_doc, "actual"))
    claimed_lookup = _best_by_name(_load_normalized_records(db, petition_doc, "claimed"))

    if not arr_lookup:
        raise HTTPException(status_code=404, detail="No normalized ARR approved rows found.")
    if not actual_lookup:
        raise HTTPException(status_code=404, detail="No normalized Petition actual rows found.")
    if not claimed_lookup:
        claimed_lookup = actual_lookup

    case_id = _case_id_for_year(financial_year)
    old_comp_ids = [
        comp_id
        for (comp_id,) in db.query(Comparison.id)
        .filter(Comparison.case_id == case_id)
        .all()
    ]
    if old_comp_ids:
        db.query(Review).filter(
            Review.comparison_id.in_(old_comp_ids)
        ).delete(synchronize_session=False)
    db.query(Comparison).filter(
        Comparison.case_id == case_id
    ).delete(synchronize_session=False)

    all_names = set(arr_lookup) | set(actual_lookup) | set(claimed_lookup)

    for name in sorted(all_names):
        arr_item = arr_lookup.get(name)
        actual_item = actual_lookup.get(name)
        claimed_item = claimed_lookup.get(name)

        approved_val = arr_item.get("value") if arr_item else None
        actual_val = actual_item.get("value") if actual_item else None
        claimed_val = claimed_item.get("value") if claimed_item else None
        variance, variance_pct = calculate_variance(approved_val, actual_val)

        confidences = [
            item.get("mapping_confidence")
            for item in (arr_item, actual_item, claimed_item)
            if item and item.get("mapping_confidence") is not None
        ]
        confidence = min(confidences) if confidences else 1.0
        decision_class, flag_reason = classify_decision(variance_pct, confidence)

        cost_head = (
            (arr_item or {}).get("cost_head")
            or (actual_item or {}).get("cost_head")
            or (claimed_item or {}).get("cost_head")
            or "Other"
        )

        db.add(Comparison(
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
            approved_source_document_id=(arr_item or {}).get("source_document_id"),
            actual_source_document_id=(actual_item or {}).get("source_document_id"),
            claimed_source_document_id=(claimed_item or {}).get("source_document_id"),
            approved_source_page=(arr_item or {}).get("source_page"),
            actual_source_page=(actual_item or {}).get("source_page"),
            claimed_source_page=(claimed_item or {}).get("source_page"),
            approved_source_table=(arr_item or {}).get("source_table"),
            actual_source_table=(actual_item or {}).get("source_table"),
            claimed_source_table=(claimed_item or {}).get("source_table"),
            approved_confidence=(arr_item or {}).get("mapping_confidence"),
            actual_confidence=(actual_item or {}).get("mapping_confidence"),
            claimed_confidence=(claimed_item or {}).get("mapping_confidence"),
        ))

    db.commit()
    return _comparison_response(db, case_id)


async def _upload_document_of_type(
    file: UploadFile,
    financial_year: str,
    doc_type: str,
    db: Session,
) -> DocumentUploadResponse:
    contents = await file.read()
    _validate_pdf_upload(file, contents)
    file_size = len(contents)

    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        page_count = get_page_count(contents)
    except Exception:
        page_count = None

    doc = Document(
        id=doc_id,
        filename=file.filename,
        doc_type=doc_type,
        financial_year=financial_year,
        file_path=file_path,
        file_size=file_size,
        page_count=page_count,
        status="uploaded",
    )
    db.add(doc)
    db.commit()

    status = "uploaded"
    rows_extracted = 0
    case_id = None
    try:
        rows = _store_extraction(db, doc, contents)
        status = "extracted"
        rows_extracted = len(rows)
        try:
            comparison = _run_comparison_for_financial_year(db, financial_year)
            case_id = comparison.case_id
        except HTTPException:
            case_id = None
    except Exception as e:
        db.rollback()
        print(f"[MVP] Auto-extraction failed for {doc_type}: {e}")

    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        doc_type=doc_type,
        file_size=file_size,
        page_count=page_count,
        status=status,
        rows_extracted=rows_extracted,
        case_id=case_id,
    )


# ─── 1. Document Upload ───

@router.post("/upload/arr", response_model=DocumentUploadResponse)
async def upload_arr_document(
    file: UploadFile = File(...),
    financial_year: str = Form("2024-25"),
    db: Session = Depends(get_db),
):
    """Upload ARR Approval Order PDF and auto-extract tables."""
    return await _upload_document_of_type(file, financial_year, "arr_order", db)


@router.post("/upload/petition", response_model=DocumentUploadResponse)
async def upload_petition_document(
    file: UploadFile = File(...),
    financial_year: str = Form("2024-25"),
    db: Session = Depends(get_db),
):
    """Upload Truing-Up Petition PDF and auto-extract tables."""
    return await _upload_document_of_type(file, financial_year, "truing_up_petition", db)


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
    
    try:
        rows = _store_extraction(db, doc, pdf_bytes)
        try:
            _run_comparison_for_financial_year(db, doc.financial_year)
        except HTTPException:
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    return _extraction_response(doc, rows)


@router.get("/extraction/{doc_id}", response_model=ExtractionResultResponse)
async def get_extraction_results(doc_id: str, db: Session = Depends(get_db)):
    """Get extraction results for a document."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    rows = (
        db.query(ExtractedRow)
        .filter(ExtractedRow.document_id == doc_id)
        .order_by(ExtractedRow.page_number, ExtractedRow.table_index, ExtractedRow.row_label)
        .all()
    )
    return _extraction_response(doc, rows)


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
    return _run_comparison_for_financial_year(db, financial_year)


@router.get("/comparison/latest", response_model=ComparisonResponse)
async def get_latest_comparison(
    financial_year: str = "2024-25",
    db: Session = Depends(get_db),
):
    """Get the current deterministic comparison case for a financial year."""
    return _comparison_response(db, _case_id_for_year(financial_year))


@router.get("/comparison/{case_id}", response_model=ComparisonResponse)
async def get_comparison(case_id: str, db: Session = Depends(get_db)):
    """Get comparison results for a case."""
    return _comparison_response(db, case_id)


@router.get("/comparison", response_model=List[ComparisonResponse])
async def list_cases(db: Session = Depends(get_db)):
    """List all comparison cases."""
    cases = db.query(Comparison.case_id).distinct().all()
    return [_comparison_response(db, case_id) for (case_id,) in cases]


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
        comp.flag_reason = "Approved by officer"
    elif review_req.action == "reject":
        comp.decision_class = "REVIEW_REQUIRED"
        comp.flag_reason = review_req.officer_comment or "Rejected by officer"
    elif review_req.action == "edit" and review_req.edited_value is not None:
        comp.actual_value = review_req.edited_value
        comp.variance, comp.variance_percent = calculate_variance(
            comp.approved_value,
            review_req.edited_value,
        )
        confidence_values = [
            value
            for value in (comp.approved_confidence, comp.actual_confidence, comp.claimed_confidence)
            if value is not None
        ]
        confidence = min(confidence_values) if confidence_values else 1.0
        comp.decision_class, comp.flag_reason = classify_decision(
            comp.variance_percent,
            confidence,
        )
        if comp.flag_reason is None:
            comp.flag_reason = "Edited by officer and variance is within threshold"
    
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
    from pdf_generator import generate_order_pdf
    
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
            "claimed_value": c.claimed_value,
            "variance": c.variance,
            "variance_percent": c.variance_percent,
            "decision_class": c.decision_class,
            "flag_reason": c.flag_reason,
            "approved_source_page": c.approved_source_page,
            "actual_source_page": c.actual_source_page,
            "claimed_source_page": c.claimed_source_page,
            "approved_source_table": c.approved_source_table,
            "actual_source_table": c.actual_source_table,
            "claimed_source_table": c.claimed_source_table,
            "approved_confidence": c.approved_confidence,
            "actual_confidence": c.actual_confidence,
            "claimed_confidence": c.claimed_confidence,
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
            value_type=i.value_type,
            value=i.value,
            unit=i.unit or "Rs. Cr.",
            mapping_confidence=i.mapping_confidence,
            mapping_method=i.mapping_method,
        )
        for i in items
    ]
