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
    rows_extracted: int = 0
    case_id: Optional[str] = None
    extraction_job_id: Optional[str] = None
    job_status: Optional[str] = None
    status_url: Optional[str] = None

class DocumentListItem(BaseModel):
    id: str
    filename: str
    doc_type: str
    financial_year: str
    file_size: int
    page_count: Optional[int] = None
    status: str
    upload_timestamp: datetime
    extraction_job_id: Optional[str] = None
    job_status: Optional[str] = None
    job_stage: Optional[str] = None
    job_progress: Optional[float] = None


# ─── Extraction Schemas ───

class ExtractedRowResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    table_index: Optional[int] = None
    table_name: Optional[str] = None
    raw_label: str
    row_label: str
    normalized_label: Optional[str] = None
    value: Optional[float] = None
    value_type: str = "value"
    document_type: str
    contract_document_type: Optional[str] = None
    financial_year: Optional[str] = None
    sbu: Optional[str] = None
    category: Optional[str] = None
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


class JobStatusResponse(BaseModel):
    id: str
    document_id: str
    filename: Optional[str] = None
    doc_type: Optional[str] = None
    status: str
    stage: str
    progress: float
    processed_pages: int = 0
    total_pages: Optional[int] = None
    rows_extracted: int = 0
    case_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ─── Normalization Schemas ───

class NormalizedItemResponse(BaseModel):
    id: str
    canonical_name: str
    category: str
    cost_head: Optional[str] = None
    source_doc_type: str
    value_type: Optional[str] = None
    value: Optional[float] = None
    unit: str = "Rs. Cr."
    mapping_confidence: float
    mapping_method: str


# ─── Comparison Schemas ───

class ComparisonItemResponse(BaseModel):
    id: str
    canonical_id: Optional[str] = None
    display_name: Optional[str] = None
    sbu: Optional[str] = None
    unit: Optional[str] = "Rs. Cr."
    section: Optional[str] = None
    canonical_name: str
    cost_head: Optional[str] = None
    approved_value: Optional[float] = None
    actual_value: Optional[float] = None
    claimed_value: Optional[float] = None
    variance: Optional[float] = None
    variance_percent: Optional[float] = None
    decision_class: str
    flag_reason: Optional[str] = None
    latest_review_action: Optional[str] = None
    latest_review_comment: Optional[str] = None
    latest_reviewed_at: Optional[datetime] = None
    approved_source_document_id: Optional[str] = None
    actual_source_document_id: Optional[str] = None
    claimed_source_document_id: Optional[str] = None
    approved_source_page: Optional[int] = None
    actual_source_page: Optional[int] = None
    claimed_source_page: Optional[int] = None
    approved_source_table: Optional[str] = None
    actual_source_table: Optional[str] = None
    claimed_source_table: Optional[str] = None
    approved_confidence: Optional[float] = None
    actual_confidence: Optional[float] = None
    claimed_confidence: Optional[float] = None

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
