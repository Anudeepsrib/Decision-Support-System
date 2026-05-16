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
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

try:
    from .config import get_settings
    from .database import SessionLocal, get_db
    from .models import (
        Document, ExtractionJob, ExtractedRow, NormalizedLineItem, Comparison, Review, GeneratedOrder
    )
    from .schemas import (
        DocumentUploadResponse, DocumentListItem,
        ExtractionResultResponse, ExtractedRowResponse,
        ComparisonResponse, ComparisonItemResponse,
        ReviewRequest, ReviewResponse,
        GenerateOrderRequest, GeneratedOrderResponse,
        NormalizedItemResponse, AuditEntry, JobStatusResponse,
    )
    from .extractor import extract_tables_from_pdf_path
    from .normalizer import normalize_row_label
    from .comparison import calculate_variance, classify_decision
    from .canonical_registry import (
        REGISTRY_BY_ID,
        canonicalize_records,
        contract_document_type,
        map_record_to_canonical,
    )
    from .prompts import generate_variance_explanation
except ImportError:  # Support direct imports from the backend directory.
    from config import get_settings
    from database import SessionLocal, get_db
    from models import (
        Document, ExtractionJob, ExtractedRow, NormalizedLineItem, Comparison, Review, GeneratedOrder
    )
    from schemas import (
        DocumentUploadResponse, DocumentListItem,
        ExtractionResultResponse, ExtractedRowResponse,
        ComparisonResponse, ComparisonItemResponse,
        ReviewRequest, ReviewResponse,
        GenerateOrderRequest, GeneratedOrderResponse,
        NormalizedItemResponse, AuditEntry, JobStatusResponse,
    )
    from extractor import extract_tables_from_pdf_path
    from normalizer import normalize_row_label
    from comparison import calculate_variance, classify_decision
    from canonical_registry import (
        REGISTRY_BY_ID,
        canonicalize_records,
        contract_document_type,
        map_record_to_canonical,
    )
    from prompts import generate_variance_explanation

router = APIRouter(prefix="/api", tags=["MVP API"])
compat_router = APIRouter(tags=["Compatibility API"])
DEFAULT_FINANCIAL_YEAR = "2024-25"

# Upload directory
settings = get_settings()
UPLOAD_DIR = str(settings.upload_dir)
settings.upload_dir.mkdir(parents=True, exist_ok=True)


def infer_financial_year_from_filename(filename: str) -> Optional[str]:
    """Infer FY like 2023-24 from deterministic filename markers."""
    text = re.sub(r"[_/]+", " ", (filename or "").lower())
    match = re.search(r"\b(20\d{2})\s*[-–—_/ ]\s*(\d{2})\b", text)
    if not match:
        return None
    start_year = int(match.group(1))
    end_year = int(f"20{match.group(2)}")
    if end_year - start_year != 1:
        return None
    return f"{start_year}-{match.group(2)}"


def _effective_financial_year(filename: str, doc_type: str, requested_year: Optional[str]) -> str:
    inferred = infer_financial_year_from_filename(filename)
    if doc_type == "truing_up_petition" and inferred:
        return inferred
    return requested_year or inferred or DEFAULT_FINANCIAL_YEAR


def _case_id_for_year(financial_year: str) -> str:
    """Use one deterministic demo case per financial year."""
    return f"kserc-{financial_year}"


def _validate_pdf_upload(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    
    # Check magic header
    header = file.file.read(4)
    file.file.seek(0)  # Reset file pointer
    if header != b"%PDF":
        raise HTTPException(status_code=400, detail="Invalid PDF file format.")


async def _save_upload_file(file: UploadFile, file_path: str) -> int:
    """Stream an uploaded PDF to disk without keeping the whole file in memory."""
    max_size = 75 * 1024 * 1024
    total_size = 0
    with open(file_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size:
                out.close()
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                raise HTTPException(status_code=413, detail="File exceeds 75MB limit.")
            out.write(chunk)
    return total_size


def _latest_extracted_document(
    db: Session,
    doc_type: str,
    financial_year: str,
) -> Optional[Document]:
    exact = (
        db.query(Document)
        .filter(
            Document.doc_type == doc_type,
            Document.financial_year == financial_year,
            Document.status == "extracted",
        )
        .order_by(Document.upload_timestamp.desc())
        .first()
    )
    if exact:
        return exact

    candidates = (
        db.query(Document)
        .filter(
            Document.doc_type == doc_type,
            Document.status == "extracted",
        )
        .order_by(Document.upload_timestamp.desc())
        .all()
    )
    for candidate in candidates:
        if _effective_financial_year(candidate.filename, candidate.doc_type, candidate.financial_year) == financial_year:
            return candidate

    if doc_type == "arr_order":
        # ARR/MYT orders often cover a control period rather than one FY. If a
        # same-year ARR record is unavailable, use the latest extracted ARR
        # order as the deterministic approved-value source.
        substantive = [candidate for candidate in candidates if (candidate.page_count or 0) > 20]
        return (substantive or candidates)[0] if candidates else None
    return None


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


def _latest_job_for_document(db: Session, document_id: str) -> Optional[ExtractionJob]:
    return (
        db.query(ExtractionJob)
        .filter(ExtractionJob.document_id == document_id)
        .order_by(ExtractionJob.created_at.desc())
        .first()
    )


def _job_response(job: ExtractionJob, doc: Optional[Document] = None) -> JobStatusResponse:
    doc = doc or job.document
    return JobStatusResponse(
        id=job.id,
        document_id=job.document_id,
        filename=doc.filename if doc else None,
        doc_type=doc.doc_type if doc else None,
        status=job.status,
        stage=job.stage or "",
        progress=round(job.progress or 0, 1),
        processed_pages=job.processed_pages or 0,
        total_pages=job.total_pages,
        rows_extracted=job.rows_extracted or 0,
        case_id=job.case_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _update_job(
    db: Session,
    job: ExtractionJob,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    progress: Optional[float] = None,
    processed_pages: Optional[int] = None,
    total_pages: Optional[int] = None,
    rows_extracted: Optional[int] = None,
    case_id: Optional[str] = None,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    commit: bool = True,
):
    if started_at is not None:
        job.started_at = started_at
    if completed_at is not None:
        job.completed_at = completed_at
    if status is not None:
        job.status = status
        if status == "PROCESSING" and job.started_at is None:
            job.started_at = datetime.utcnow()
        if status in ("COMPLETED", "FAILED") and job.completed_at is None:
            job.completed_at = datetime.utcnow()
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = max(0.0, min(100.0, float(progress)))
    if processed_pages is not None:
        job.processed_pages = processed_pages
    if total_pages is not None:
        job.total_pages = total_pages
    if rows_extracted is not None:
        job.rows_extracted = rows_extracted
    if case_id is not None:
        job.case_id = case_id
    if error_message is not None:
        job.error_message = error_message
    if commit:
        db.commit()


def _create_extraction_job(db: Session, doc: Document) -> ExtractionJob:
    job = ExtractionJob(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        status="PENDING",
        stage="Queued for extraction",
        progress=0.0,
        rows_extracted=0,
    )
    doc.status = "extracting"
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _run_extraction_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        if not job:
            return

        doc = db.query(Document).filter(Document.id == job.document_id).first()
        if not doc:
            _update_job(
                db,
                job,
                status="FAILED",
                stage="Document record missing",
                error_message="Uploaded document record could not be found.",
                progress=0.0,
                completed_at=datetime.utcnow(),
            )
            return

        if job.status not in ("PENDING", "FAILED"):
            return

        _update_job(
            db,
            job,
            status="PROCESSING",
            stage="Starting extraction",
            progress=3.0,
            total_pages=doc.page_count,
            processed_pages=0,
            commit=True,
        )

        try:
            rows = _store_extraction(db, doc, job=job)
            try:
                comparison = _run_comparison_for_financial_year(db, doc.financial_year)
                job.case_id = comparison.case_id
            except HTTPException:
                job.case_id = None

            _update_job(
                db,
                job,
                status="COMPLETED",
                stage=f"Extraction completed ({len(rows)} rows)",
                progress=100.0,
                processed_pages=doc.page_count or 0,
                total_pages=doc.page_count,
                rows_extracted=len(rows),
                completed_at=datetime.utcnow(),
            )
            db.commit()
        except Exception as extraction_error:
            db.rollback()
            db.add(job)
            _update_job(
                db,
                job,
                status="FAILED",
                stage="Extraction failed",
                progress=0.0,
                error_message=str(extraction_error),
                completed_at=datetime.utcnow(),
            )
            if doc:
                doc.status = "failed"
            db.commit()
    finally:
        db.close()


def _store_extraction(
    db: Session,
    doc: Document,
    job: Optional[ExtractionJob] = None,
) -> List[ExtractedRow]:
    doc.financial_year = _effective_financial_year(doc.filename, doc.doc_type, doc.financial_year)
    last_progress_commit = 0.0

    def progress_callback(stage: str, progress: float, processed_pages: int, total_pages: int):
        nonlocal last_progress_commit
        if not job:
            return
        now = datetime.utcnow().timestamp()
        if now - last_progress_commit < 0.75 and progress < 99:
            return
        _update_job(
            db,
            job,
            status="PROCESSING",
            stage=stage,
            progress=progress,
            processed_pages=processed_pages,
            total_pages=total_pages,
        )
        last_progress_commit = now

    extracted, page_count, target_pages = extract_tables_from_pdf_path(
        doc.file_path,
        doc.filename,
        doc.doc_type,
        progress_callback=progress_callback,
    )
    doc.page_count = page_count
    _delete_extraction_for_document(db, doc.id)

    rows: List[ExtractedRow] = []
    normalized_items: List[NormalizedLineItem] = []
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
            unit=row_data.unit,
            confidence=row_data.confidence,
            extraction_method="targeted_table" if getattr(row_data, "target_id", None) else "pdfplumber",
            raw_text=row_data.raw_text,
        )
        rows.append(row)

        norm = normalize_row_label(row_data.row_label)
        normalized_items.append(NormalizedLineItem(
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
        ))

    if rows:
        db.bulk_save_objects(rows)
    if normalized_items:
        db.bulk_save_objects(normalized_items)

    doc.status = "extracted"
    if job:
        _update_job(
            db,
            job,
            status="PROCESSING",
            stage=f"Saved {len(rows)} extracted rows from {len(target_pages)} targeted pages",
            progress=86,
            processed_pages=page_count,
            total_pages=page_count,
            rows_extracted=len(rows),
            commit=False,
        )
    db.commit()
    return rows


def _row_response(row: ExtractedRow, doc: Document) -> ExtractedRowResponse:
    norm = normalize_row_label(row.row_label)
    canonical_item = map_record_to_canonical({
        "raw_label": row.row_label,
        "normalized_label": norm.canonical_name,
        "table_name": row.table_name,
        "raw_text": row.raw_text,
    })
    return ExtractedRowResponse(
        id=row.id,
        document_id=doc.id,
        page_number=row.page_number,
        table_index=row.table_index,
        table_name=row.table_name,
        raw_label=row.row_label,
        row_label=row.row_label,
        normalized_label=norm.canonical_name,
        value=row.value,
        value_type=row.value_type or "value",
        document_type=doc.doc_type,
        contract_document_type=contract_document_type(doc.doc_type),
        financial_year=doc.financial_year,
        sbu=canonical_item.sbu if canonical_item else None,
        category=canonical_item.section if canonical_item else norm.category,
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
            "normalized_label": item.canonical_name,
            "cost_head": item.cost_head,
            "value": item.value,
            "value_type": item.value_type,
            "mapping_confidence": confidence,
            "raw_label": row.row_label,
            "source_page": row.page_number,
            "source_table": row.table_name,
            "source_document_id": doc.id,
            "raw_text": row.raw_text,
            "document_id": doc.id,
            "document_type": contract_document_type(doc.doc_type),
            "financial_year": doc.financial_year,
            "unit": row.unit or item.unit or "Rs. Cr.",
        })
    return records


def _best_by_canonical_id(records: List[Dict]) -> Dict[str, Dict]:
    grouped: Dict[str, List[Dict]] = {}
    for record in records:
        name = record.get("canonical_id") or record.get("canonical_name")
        if not name:
            continue
        grouped.setdefault(name, []).append(record)

    best: Dict[str, Dict] = {}
    for name, group in grouped.items():
        if name in {"OM_COST", "OM_EXPENSES_GENERATION", "OM_EXPENSES_TRANSMISSION"}:
            total_like = [
                record for record in group
                if record.get("raw_label")
                and record.get("value") is not None
                and any(token in record["raw_label"].lower() for token in ("o&m", "o & m", "operation and maintenance", "total o"))
                and "lakh" not in record["raw_label"].lower()
            ]
            if not total_like:
                valued = [record for record in group if record.get("value") is not None]
                if valued:
                    aggregate = dict(valued[0])
                    aggregate["value"] = round(sum(record.get("value") or 0.0 for record in valued), 2)
                    aggregate["mapping_confidence"] = min(record.get("mapping_confidence") or 1.0 for record in valued)
                    aggregate["raw_label"] = "Aggregated O&M Cost"
                    aggregate["source_page"] = min(record.get("source_page") or 0 for record in valued) or None
                    aggregate["source_table"] = "Aggregated from mapped O&M component rows"
                    best[name] = aggregate
                    continue
            if total_like:
                def om_score(record: Dict) -> tuple:
                    label = (record.get("raw_label") or "").lower()
                    return (
                        4 if label.strip() in {"o&m expenses", "o & m expenses"} else 0,
                        3 if "expenses - total" in label or "expenses total" in label else 0,
                        -2 if "total normative" in label else (1 if "total" in label else 0),
                        1 if not any(token in label for token in ("existing", "new", "one month", "rate")) else 0,
                        record.get("mapping_confidence") or 0,
                    )
                group = sorted(total_like, key=om_score, reverse=True)
                best[name] = group[0]
                continue
            else:
                group = group

        selected = group[0]
        for record in group[1:]:
            current_score = (
                selected.get("mapping_confidence") or 0,
                1 if selected.get("value") is not None else 0,
            )
            new_score = (
                record.get("mapping_confidence") or 0,
                1 if record.get("value") is not None else 0,
            )
            if new_score > current_score:
                selected = record
        best[name] = selected
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
        canonical_id=comparison.canonical_id or comparison.canonical_name,
        display_name=comparison.display_name or comparison.canonical_name,
        sbu=comparison.sbu,
        unit=comparison.unit or "Rs. Cr.",
        section=comparison.section,
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
        .order_by(Comparison.section, Comparison.sbu, Comparison.canonical_name)
        .all()
    )
    if not comparisons:
        raise HTTPException(status_code=404, detail="Case not found.")
    report_financial_year = comparisons[0].financial_year or req.financial_year

    latest_reviews = _latest_reviews_by_comparison(db, [c.id for c in comparisons])
    auto_count = sum(1 for c in comparisons if c.decision_class == "ACCEPTABLE_VARIANCE")
    review_count = len(comparisons) - auto_count
    non_total = [
        c for c in comparisons
        if not (REGISTRY_BY_ID.get(c.canonical_id or "") and REGISTRY_BY_ID[c.canonical_id].is_total)
    ]
    variance_rows = non_total or comparisons
    total_var = sum(c.variance or 0 for c in variance_rows)

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
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
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

    arr_records = canonicalize_records(_load_normalized_records(db, arr_doc, "approved"))
    petition_approved_records = canonicalize_records(_load_normalized_records(db, petition_doc, "approved"))
    actual_records = canonicalize_records(_load_normalized_records(db, petition_doc, "actual"))
    claimed_records = canonicalize_records(_load_normalized_records(db, petition_doc, "claimed"))
    deviation_records = canonicalize_records(_load_normalized_records(db, petition_doc, "deviation"))

    arr_lookup = _best_by_canonical_id(arr_records + petition_approved_records)
    actual_lookup = _best_by_canonical_id(actual_records)
    claimed_lookup = _best_by_canonical_id(claimed_records)
    deviation_lookup = _best_by_canonical_id(deviation_records)

    if not arr_lookup:
        raise HTTPException(status_code=404, detail="No canonical ARR approved rows found after filtering.")
    if not actual_lookup:
        raise HTTPException(status_code=404, detail="No canonical Petition actual rows found after filtering.")

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
        deviation_item = deviation_lookup.get(name)
        metadata_item = arr_item or actual_item or claimed_item or {}

        approved_val = arr_item.get("value") if arr_item else None
        actual_val = actual_item.get("value") if actual_item else None
        claimed_val = claimed_item.get("value") if claimed_item else None
        comparison_val = claimed_val if claimed_val is not None else actual_val
        variance, variance_pct = calculate_variance(approved_val, comparison_val)
        if deviation_item and approved_val is not None and comparison_val is not None:
            extracted_deviation = deviation_item.get("value")
            calculated_deviation = round(comparison_val - approved_val, 2)
            if extracted_deviation is not None and abs(extracted_deviation - calculated_deviation) <= max(0.1, abs(calculated_deviation) * 0.02):
                variance = round(extracted_deviation, 2)
                variance_pct = round((variance / abs(approved_val)) * 100, 2) if approved_val else (0.0 if variance == 0 else None)

        confidences = [
            item.get("mapping_confidence")
            for item in (arr_item, actual_item, claimed_item)
            if item and item.get("mapping_confidence") is not None
        ]
        confidence = min(confidences) if confidences else 1.0
        decision_class, flag_reason = classify_decision(
            variance_pct,
            confidence,
            missing_values=approved_val is None or comparison_val is None,
        )

        cost_head = (
            metadata_item.get("sbu")
            or metadata_item.get("cost_head")
            or "Other"
        )
        display_name = metadata_item.get("display_name") or metadata_item.get("canonical_name") or name

        db.add(Comparison(
            id=str(uuid.uuid4()),
            case_id=case_id,
            financial_year=financial_year,
            canonical_id=name,
            canonical_name=display_name,
            display_name=display_name,
            sbu=metadata_item.get("sbu"),
            unit=metadata_item.get("unit") or "Rs. Cr.",
            section=metadata_item.get("section"),
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
    background_tasks: BackgroundTasks,
) -> DocumentUploadResponse:
    _validate_pdf_upload(file)
    if doc_type not in {"arr_order", "truing_up_petition"}:
        raise HTTPException(
            status_code=400,
            detail="doc_type must be 'arr_order' or 'truing_up_petition'.",
        )
    effective_year = _effective_financial_year(file.filename or "", doc_type, financial_year)

    doc_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    file_size = await _save_upload_file(file, file_path)

    doc = Document(
        id=doc_id,
        filename=file.filename,
        doc_type=doc_type,
        financial_year=effective_year,
        file_path=file_path,
        file_size=file_size,
        page_count=None,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = _create_extraction_job(db, doc)
    background_tasks.add_task(_run_extraction_job, job.id)

    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        doc_type=doc_type,
        file_size=file_size,
        page_count=None,
        status=doc.status,
        rows_extracted=0,
        extraction_job_id=job.id,
        job_status=job.status,
        status_url=f"/api/job/{job.id}",
    )


# ─── 1. Document Upload ───

@router.post("/upload/arr", response_model=DocumentUploadResponse)
async def upload_arr_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    financial_year: str = Form(DEFAULT_FINANCIAL_YEAR),
    db: Session = Depends(get_db),
):
    """Upload ARR Approval Order PDF and enqueue background extraction."""
    return await _upload_document_of_type(file, financial_year, "arr_order", db, background_tasks)


@router.post("/upload/petition", response_model=DocumentUploadResponse)
async def upload_petition_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    financial_year: str = Form(DEFAULT_FINANCIAL_YEAR),
    db: Session = Depends(get_db),
):
    """Upload Truing-Up Petition PDF and enqueue background extraction."""
    return await _upload_document_of_type(file, financial_year, "truing_up_petition", db, background_tasks)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form("arr_order"),  # arr_order | truing_up_petition
    financial_year: str = Form(DEFAULT_FINANCIAL_YEAR),
    db: Session = Depends(get_db),
):
    """Legacy upload endpoint - use /upload/arr or /upload/petition instead."""
    return await _upload_document_of_type(file, financial_year, doc_type, db, background_tasks)


@router.get("/documents", response_model=List[DocumentListItem])
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents."""
    docs = db.query(Document).order_by(Document.upload_timestamp.desc()).all()
    items = []
    for d in docs:
        job = _latest_job_for_document(db, d.id)
        effective_year = _effective_financial_year(d.filename, d.doc_type, d.financial_year)
        items.append(DocumentListItem(
            id=d.id,
            filename=d.filename,
            doc_type=d.doc_type,
            financial_year=effective_year,
            file_size=d.file_size,
            page_count=d.page_count,
            status=d.status,
            upload_timestamp=d.upload_timestamp,
            extraction_job_id=job.id if job else None,
            job_status=job.status if job else None,
            job_stage=job.stage if job else None,
            job_progress=job.progress if job else None,
        ))
    return items


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the status and progress of a background extraction job."""
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found.")
    return _job_response(job)


# ─── 2. Extraction ───

@router.post("/extraction/{doc_id}/run", response_model=JobStatusResponse)
async def run_extraction(doc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Run table extraction on an uploaded document in the background."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")

    job = _create_extraction_job(db, doc)
    background_tasks.add_task(_run_extraction_job, job.id)
    return _job_response(job, doc)


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
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
    db: Session = Depends(get_db),
):
    """
    Run three-way comparison: ARR Approved vs Petition Actual vs Petition Claimed.
    Uses normalized line items from both uploaded documents.
    """
    return _run_comparison_for_financial_year(db, financial_year)


@router.get("/comparison/latest", response_model=ComparisonResponse)
async def get_latest_comparison(
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
    db: Session = Depends(get_db),
):
    """Get the current deterministic comparison case for a financial year."""
    return _comparison_response(db, _case_id_for_year(financial_year))


@router.get("/comparison/results", response_model=ComparisonResponse)
async def get_comparison_results(
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
    db: Session = Depends(get_db),
):
    """Compatibility endpoint for the latest comparison results."""
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
    
    # Generate deterministic explanation if needed.
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
        comp.decision_class = "ACCEPTABLE_VARIANCE"
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
            missing_values=comp.approved_value is None or review_req.edited_value is None,
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
    try:
        from .pdf_generator import generate_order_pdf
    except ImportError:
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
            "canonical_id": c.canonical_id or c.canonical_name,
            "display_name": c.display_name or c.canonical_name,
            "sbu": c.sbu,
            "unit": c.unit or "Rs. Cr.",
            "section": c.section,
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
            financial_year=report_financial_year,
            comparisons=comp_dicts,
            reviews=review_dicts,
            officer_name=req.officer_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
    
    # Save order record
    auto_count = sum(1 for c in comparisons if c.decision_class == "ACCEPTABLE_VARIANCE")
    review_count = len(comparisons) - auto_count
    
    order = GeneratedOrder(
        id=str(uuid.uuid4()),
        case_id=req.case_id,
        financial_year=report_financial_year,
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
        financial_year=report_financial_year,
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
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
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


# ─── 8. Local MVP Compatibility Endpoints ───
#
# The React app uses the /api/* routes above. These no-prefix aliases make the
# smoke-test flow and README commands match the product workflow terms:
# /upload/*, /comparison/results, and /report/*.

@compat_router.post("/upload/arr", response_model=DocumentUploadResponse)
async def compat_upload_arr_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    financial_year: str = Form(DEFAULT_FINANCIAL_YEAR),
    db: Session = Depends(get_db),
):
    return await _upload_document_of_type(file, financial_year, "arr_order", db, background_tasks)


@compat_router.post("/upload/petition", response_model=DocumentUploadResponse)
async def compat_upload_petition_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    financial_year: str = Form(DEFAULT_FINANCIAL_YEAR),
    db: Session = Depends(get_db),
):
    return await _upload_document_of_type(
        file, financial_year, "truing_up_petition", db, background_tasks
    )


@compat_router.post("/comparison/run", response_model=ComparisonResponse)
async def compat_run_comparison(
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
    db: Session = Depends(get_db),
):
    return _run_comparison_for_financial_year(db, financial_year)


@compat_router.get("/comparison/results", response_model=ComparisonResponse)
async def compat_get_comparison_results(
    financial_year: str = DEFAULT_FINANCIAL_YEAR,
    db: Session = Depends(get_db),
):
    return _comparison_response(db, _case_id_for_year(financial_year))


@compat_router.post("/report/generate", response_model=GeneratedOrderResponse)
async def compat_generate_report(
    req: GenerateOrderRequest,
    db: Session = Depends(get_db),
):
    return await generate_order(req, db)


@compat_router.get("/report/{order_id}")
async def compat_download_report(order_id: str, db: Session = Depends(get_db)):
    return await download_order(order_id, db)
