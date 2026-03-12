"""
FastAPI endpoint: Order vs Reference Document Comparison.
Accepts two PDFs (order + reference), extracts text deterministically,
and produces a structured discrepancy analysis.
NO LLM dependency — comparison is fully rule-based.
"""

import io
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import PyPDF2

from backend.security.auth import get_current_user, require_permission, TokenData
from backend.api.ocr_service import ocr_service
from backend.ai.OrderComparator import OrderComparator

router = APIRouter(prefix="/compare", tags=["Order Comparison"])


# ─── Response Models ───

class FieldComparison(BaseModel):
    """Comparison result for a single order-level field."""
    order_value: str = ""
    reference_value: str = ""
    status: str = ""
    reason: str = ""


class ItemComparison(BaseModel):
    """Comparison result for a single line item."""
    product_name_order: str = ""
    product_name_reference: str = ""
    quantity_order: str = ""
    quantity_reference: str = ""
    unit_price_order: str = ""
    unit_price_reference: str = ""
    total_price_order: str = ""
    total_price_reference: str = ""
    status: str = ""
    reason: str = ""


class ComparisonSummary(BaseModel):
    """Aggregate summary of the comparison."""
    total_items_order: str = ""
    matched_items: str = ""
    mismatched_items: str = ""
    missing_items: str = ""
    extra_items: str = ""
    overall_status: str = ""


class OrderComparisonResponse(BaseModel):
    """Full comparison response including JSON analysis and reports."""
    job_id: str
    order_filename: str
    reference_filename: str
    timestamp: str
    order_level_comparison: Dict[str, FieldComparison] = {}
    items_comparison: List[ItemComparison] = []
    missing_items_in_reference: List[str] = []
    extra_items_in_reference: List[str] = []
    summary: ComparisonSummary = ComparisonSummary()
    confidence_score: str = ""
    executive_report: str = ""
    llm_report: str = ""


# ─── PDF Text Extraction Helper ───

async def _extract_text_from_pdf(contents: bytes, filename: str) -> str:
    """
    Extract text from a PDF or image file using PyPDF2 with OCR fallback.
    Fully deterministic — no LLM involved.
    """
    is_image = ocr_service.is_image(contents, filename)

    if is_image:
        raw_pages = ocr_service.process_image(contents)
    else:
        def _extract_text_sync(pdf_bytes):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text_pages = {}
            total_len = 0
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text() or ""
                text_pages[i + 1] = text
                total_len += len(text.strip())
            return text_pages, total_len

        raw_pages, total_text_length = await asyncio.to_thread(
            _extract_text_sync, contents
        )

        if total_text_length < 50:
            raw_pages = ocr_service.process_pdf(contents)

    combined = "\n\n".join(
        f"--- Page {page_num} ---\n{text}"
        for page_num, text in sorted(raw_pages.items())
    )
    return combined


# ─── Endpoint ───

@router.post("/upload", response_model=OrderComparisonResponse)
async def compare_order_documents(
    order_file: UploadFile = File(..., description="The Order PDF document"),
    reference_file: UploadFile = File(..., description="The Reference PDF document"),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("extraction.upload")),
):
    """
    Compare an Order PDF against a Reference PDF using deterministic rules.
    No LLM is required — comparison uses regex, difflib, and rule-based logic.
    An optional LLM-generated report is included if OPENAI_API_KEY is set.
    """
    allowed_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")

    if not order_file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Order file must be a PDF or image file.")
    if not reference_file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Reference file must be a PDF or image file.")

    order_contents = await order_file.read()
    reference_contents = await reference_file.read()

    for label, contents in [("Order", order_contents), ("Reference", reference_contents)]:
        if len(contents) / (1024 * 1024) > 50:
            raise HTTPException(status_code=413, detail=f"{label} file exceeds 50MB limit.")

    job_id = f"cmp-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    try:
        order_text = await _extract_text_from_pdf(order_contents, order_file.filename)
        reference_text = await _extract_text_from_pdf(reference_contents, reference_file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text from PDFs: {str(e)}")

    if len(order_text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Order document contains no extractable text.")
    if len(reference_text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Reference document contains no extractable text.")

    # Run deterministic comparison — NO LLM needed
    try:
        comparator = OrderComparator()
        result = comparator.compare(order_text, reference_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison engine error: {str(e)}")

    comparison = result.get("comparison_result", {})

    # Map order-level comparisons
    order_level = {}
    for field_name, field_data in comparison.get("order_level_comparison", {}).items():
        if isinstance(field_data, dict):
            order_level[field_name] = FieldComparison(
                order_value=str(field_data.get("order_value", "")),
                reference_value=str(field_data.get("reference_value", "")),
                status=str(field_data.get("status", "")),
                reason=str(field_data.get("reason", "")),
            )

    # Map item-level comparisons
    items = []
    for item_data in comparison.get("items_comparison", []):
        if isinstance(item_data, dict):
            items.append(ItemComparison(**{
                k: str(item_data.get(k, "")) for k in ItemComparison.model_fields
            }))

    # Map summary
    raw_summary = comparison.get("summary", {})
    summary = ComparisonSummary(**{
        k: str(raw_summary.get(k, "")) for k in ComparisonSummary.model_fields
    })

    return OrderComparisonResponse(
        job_id=job_id,
        order_filename=order_file.filename,
        reference_filename=reference_file.filename,
        timestamp=result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        order_level_comparison=order_level,
        items_comparison=items,
        missing_items_in_reference=[str(i) for i in comparison.get("missing_items_in_reference", [])],
        extra_items_in_reference=[str(i) for i in comparison.get("extra_items_in_reference", [])],
        summary=summary,
        confidence_score=str(comparison.get("confidence_score", "")),
        executive_report=result.get("executive_report", ""),
        llm_report=result.get("llm_report", "LLM_REPORT_DISABLED"),
    )
