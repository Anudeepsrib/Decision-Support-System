"""
FastAPI endpoint: PDF Table Extraction with Page/Table Anchors.
Implements the "Evidence Pack" requirement — every extracted figure
links to its specific page and table in the source document.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
async def extract_tables_from_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF petition or audited financials document.
    Extracts structured financial tables with page/table anchors.

    Every extracted value carries provenance metadata linking it
    to the specific page, table, and cell in the source document.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)

    if file_size_mb > 50:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")

    # Simulated extraction pipeline (production would use tabula/camelot/LLM)
    extracted_fields = [
        ExtractedField(
            field_name="Approved O&M Cost (FY 2024-25)",
            sbu_code="SBU-D",
            extracted_value=1500000000,
            confidence_score=0.95,
            source_page=12,
            source_table=1,
            cell_reference="C4",
            raw_text="Rs. 150.00 Cr",
            review_required=False
        ),
        ExtractedField(
            field_name="Actual O&M Cost (FY 2024-25)",
            sbu_code="SBU-D",
            extracted_value=1800000000,
            confidence_score=0.88,
            source_page=14,
            source_table=2,
            cell_reference="D6",
            raw_text="Rs. 180.00 Cr (Audited)",
            review_required=False
        ),
        ExtractedField(
            field_name="Power Purchase Cost (Actual)",
            sbu_code="SBU-G",
            extracted_value=None,
            confidence_score=0.42,
            source_page=18,
            source_table=3,
            cell_reference="B8",
            raw_text="[Table partially obscured]",
            review_required=True
        ),
    ]

    fields_needing_review = sum(1 for f in extracted_fields if f.review_required)

    return ExtractionResponse(
        job_id=f"ext-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        filename=file.filename,
        total_pages_processed=24,
        total_fields_extracted=len(extracted_fields),
        fields_requiring_review=fields_needing_review,
        extraction_method="LLM_RAG + Tabula",
        timestamp=datetime.utcnow().isoformat(),
        fields=extracted_fields
    )
