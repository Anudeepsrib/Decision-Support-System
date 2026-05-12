"""
MVP Pydantic Schemas — Request/Response models for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Document Schemas ───

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    doc_type: str
    file_size: int
    page_count: Optional[int] = None
    status: str

class DocumentListItem(BaseModel):
    id: str
    filename: str
    doc_type: str
    financial_year: str
    file_size: int
    page_count: Optional[int] = None
    status: str
    upload_timestamp: datetime


# ─── Extraction Schemas ───

class ExtractedRowResponse(BaseModel):
    id: str
    page_number: int
    table_index: Optional[int] = None
    table_name: Optional[str] = None
    row_label: str
    value: Optional[float] = None
    unit: str = "Rs. Cr."
    confidence: float
    extraction_method: str
    raw_text: Optional[str] = None

class ExtractionResultResponse(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    total_pages: int
    total_rows_extracted: int
    rows_needing_review: int
    extraction_method: str
    rows: List[ExtractedRowResponse]


# ─── Normalization Schemas ───

class NormalizedItemResponse(BaseModel):
    id: str
    canonical_name: str
    category: str
    cost_head: Optional[str] = None
    source_doc_type: str
    value: Optional[float] = None
    unit: str = "Rs. Cr."
    mapping_confidence: float
    mapping_method: str


# ─── Comparison Schemas ───

class ComparisonItemResponse(BaseModel):
    id: str
    canonical_name: str
    cost_head: Optional[str] = None
    approved_value: Optional[float] = None
    actual_value: Optional[float] = None
    claimed_value: Optional[float] = None
    variance: Optional[float] = None
    variance_percent: Optional[float] = None
    decision_class: str
    flag_reason: Optional[str] = None
    approved_source_page: Optional[int] = None
    actual_source_page: Optional[int] = None

class ComparisonResponse(BaseModel):
    case_id: str
    financial_year: str
    total_items: int
    auto_approved: int
    review_required: int
    total_variance: float
    items: List[ComparisonItemResponse]


# ─── Review Schemas ───

class ReviewRequest(BaseModel):
    action: str = Field(..., description="approve | reject | edit")
    officer_name: str = "Demo Officer"
    officer_comment: Optional[str] = None
    edited_value: Optional[float] = None

class ReviewResponse(BaseModel):
    id: str
    comparison_id: str
    action: str
    officer_name: str
    officer_comment: Optional[str] = None
    edited_value: Optional[float] = None
    ai_explanation: Optional[str] = None
    reviewed_at: datetime


# ─── PDF Generation Schemas ───

class GenerateOrderRequest(BaseModel):
    case_id: str
    financial_year: str = "2024-25"
    officer_name: str = "Demo Officer"

class GeneratedOrderResponse(BaseModel):
    id: str
    case_id: str
    financial_year: str
    file_path: str
    file_size: int
    is_draft: bool
    total_items: int
    auto_approved: int
    review_required: int
    generated_at: datetime
    download_url: str


# ─── Audit Schemas ───

class AuditEntry(BaseModel):
    timestamp: datetime
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str] = None
    officer: Optional[str] = None
