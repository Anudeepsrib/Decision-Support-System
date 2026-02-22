"""
FastAPI endpoint: PDF Table Extraction with Page/Table Anchors.
Implements the "Evidence Pack" requirement — every extracted figure
links to its specific page and table in the source document.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from backend.security.auth import get_current_user, require_permission, TokenData
from backend.api.extraction_graph import extraction_graph, ExtractedField
from backend.api.ocr_service import ocr_service
import io
import PyPDF2

router = APIRouter(prefix="/extract", tags=["Extraction"])


# ─── Request/Response Models ───

class ExtractedField(BaseModel):
    """A single extracted data point with full provenance."""
    field_name: str               # e.g., "Actual O&M Cost"
    sbu_code: str                 # SBU Partitioning: SBU-G, SBU-T, SBU-D
    extracted_value: Optional[float]
    confidence_score: float        # 0.0 to 1.0
    source_page: int
    source_table: Optional[int] = None
    cell_reference: Optional[str] = None  # e.g., "B4"
    raw_text: Optional[str] = None
    review_required: bool = False  # True if confidence < threshold


class ExtractionResponse(BaseModel):
    """Full extraction report for a single PDF."""
    job_id: str
    filename: str
    total_pages_processed: int
    total_fields_extracted: int
    fields_requiring_review: int
    extraction_method: str
    timestamp: str
    fields: List[ExtractedField]


# ─── Endpoints ───

@router.post("/upload", response_model=ExtractionResponse)
async def extract_tables_from_pdf(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),  # F-12: RBAC enforced
    _perm=Depends(require_permission("extraction.upload")),
):
    """
    Accepts a PDF petition or audited financials document.
    Extracts structured financial tables with page/table anchors.

    Every extracted value carries provenance metadata linking it
    to the specific page, table, and cell in the source document.
    Requires: extraction.upload permission.
    """
    allowed_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only PDF and Image files are accepted.")

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)

    if file_size_mb > 50:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")

    job_id = f"ext-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Document Processing: PyPDF2 Native -> OCR Fallback
    raw_pages = {}
    is_image = ocr_service.is_image(contents, file.filename)
    
    if is_image:
        raw_pages = ocr_service.process_image(contents)
    else:
        # Try native text extraction via PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(contents))
        total_text_length = 0
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text() or ""
            raw_pages[i+1] = text
            total_text_length += len(text.strip())
        
        # If very little text is found, we assume it is a scanned document and hit OCR
        if total_text_length < 50:
            raw_pages = ocr_service.process_pdf(contents)

    # Initialize Graph State
    initial_state = {
        "job_id": job_id,
        "filename": file.filename,
        "raw_ocr_pages": raw_pages,
        "extracted_fields": [],
        "retry_count": 0,
        "requires_human_review": False
    }

    # Asynchronously invoke LangGraph Pipeline with Thread Checkpoint
    config = {"configurable": {"thread_id": job_id}}
    final_state = await extraction_graph.ainvoke(initial_state, config=config)

    # Convert state dicts back to Pydantic objects for the API response
    result_fields = [ExtractedField(**f) for f in final_state.get("extracted_fields", [])]

    fields_needing_review = sum(1 for f in result_fields if f.review_required)

    return ExtractionResponse(
        job_id=job_id,
        filename=file.filename,
        total_pages_processed=len(initial_state["raw_ocr_pages"]),
        total_fields_extracted=len(result_fields),
        fields_requiring_review=fields_needing_review,
        extraction_method="LangGraph + ChatOpenAI",
        timestamp=datetime.now(timezone.utc).isoformat(),
        fields=result_fields
    )
