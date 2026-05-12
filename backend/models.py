"""
MVP SQLAlchemy Models — Minimal schemas for the demo.

Tables:
  - documents:            Uploaded PDFs with metadata
  - extraction_jobs:      Background extraction job state
  - extracted_rows:       Raw extracted financial rows with provenance
  - normalized_line_items: Canonical mapped line items
  - comparisons:          Approved vs Actual vs Claimed comparisons
  - reviews:              Officer review decisions
  - generated_orders:     Generated PDF order metadata
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from database import Base


def _uuid():
    return str(uuid.uuid4())


# ─── 1. Documents ───

class Document(Base):
    """Uploaded PDF documents."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=_uuid)
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)  # "arr_order" | "truing_up_petition"
    financial_year = Column(String(10), nullable=False, default="2024-25")
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=True)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="uploaded")  # uploaded | extracted | processed

    # Relationships
    extracted_rows = relationship("ExtractedRow", back_populates="document", cascade="all, delete-orphan")
    extraction_jobs = relationship("ExtractionJob", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document({self.filename}, {self.doc_type})>"


# ─── 1b. Extraction Jobs ───

class ExtractionJob(Base):
    """Background extraction progress for uploaded PDFs."""
    __tablename__ = "extraction_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    status = Column(String(20), default="PENDING", index=True)  # PENDING | PROCESSING | COMPLETED | FAILED
    stage = Column(String(200), default="Queued for extraction")
    progress = Column(Float, default=0.0)
    processed_pages = Column(Integer, default=0)
    total_pages = Column(Integer, nullable=True)
    rows_extracted = Column(Integer, default=0)
    case_id = Column(String(36), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="extraction_jobs")

    __table_args__ = (
        Index("ix_extraction_job_doc_created", "document_id", "created_at"),
    )


# ─── 2. Extracted Rows ───

class ExtractedRow(Base):
    """Raw extracted financial table rows with provenance."""
    __tablename__ = "extracted_rows"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    
    # Provenance
    page_number = Column(Integer, nullable=False)
    table_index = Column(Integer, nullable=True)
    table_name = Column(String(200), nullable=True)  # Detected table title
    
    # Data
    row_label = Column(String(300), nullable=False)  # Raw row label from PDF
    value = Column(Float, nullable=True)
    value_type = Column(String(20), nullable=False, default="value")  # approved | actual | claimed | value
    unit = Column(String(20), default="Rs. Cr.")  # Rs. Cr., MU, %, etc.
    
    # Quality
    confidence = Column(Float, nullable=False, default=0.0)
    extraction_method = Column(String(50), default="pdfplumber")
    raw_text = Column(Text, nullable=True)
    
    extracted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extracted_rows")

    __table_args__ = (
        Index("ix_extracted_doc_page", "document_id", "page_number"),
    )


# ─── 3. Normalized Line Items ───

class NormalizedLineItem(Base):
    """Canonical mapped line items after normalization."""
    __tablename__ = "normalized_line_items"

    id = Column(String(36), primary_key=True, default=_uuid)
    extracted_row_id = Column(String(36), ForeignKey("extracted_rows.id"), nullable=True)
    
    # Canonical mapping
    canonical_name = Column(String(200), nullable=False)  # e.g., "Power Purchase Cost"
    category = Column(String(50), nullable=False)  # "ARR" | "ERC" | "Revenue_Gap" | "Operating_Expense"
    cost_head = Column(String(50), nullable=True)   # O&M, Power_Purchase, Interest, etc.
    
    # Source info
    source_doc_type = Column(String(50), nullable=False)  # "arr_order" | "truing_up_petition"
    financial_year = Column(String(10), nullable=False, default="2024-25")
    
    # Value type for petition documents
    value_type = Column(String(20), nullable=True)  # "actual" | "claimed" | "approved"
    
    # Normalized value
    value = Column(Float, nullable=True)
    unit = Column(String(20), default="Rs. Cr.")
    
    # Mapping quality
    mapping_confidence = Column(Float, default=1.0)
    mapping_method = Column(String(50), default="rule_based")  # rule_based | ai_semantic
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_norm_canonical_year", "canonical_name", "financial_year", "source_doc_type"),
        Index("ix_norm_doc_type", "source_doc_type", "financial_year"),
    )


# ─── 4. Comparisons ───

class Comparison(Base):
    """Approved vs Actual vs Claimed variance comparison."""
    __tablename__ = "comparisons"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), nullable=False, index=True)  # Groups a comparison set
    financial_year = Column(String(10), nullable=False, default="2024-25")
    
    # Line item
    canonical_name = Column(String(200), nullable=False)
    cost_head = Column(String(50), nullable=True)
    
    # Three-way values
    approved_value = Column(Float, nullable=True)   # From ARR Order
    actual_value = Column(Float, nullable=True)      # From Truing-Up Petition
    claimed_value = Column(Float, nullable=True)     # What utility claims
    
    # Computed variance
    variance = Column(Float, nullable=True)           # actual - approved
    variance_percent = Column(Float, nullable=True)   # (actual - approved) / approved * 100
    
    # Classification
    decision_class = Column(String(30), default="PENDING")  # AI_AUTO | REVIEW_REQUIRED | PENDING
    flag_reason = Column(String(200), nullable=True)
    
    # Provenance
    approved_source_document_id = Column(String(36), nullable=True)
    actual_source_document_id = Column(String(36), nullable=True)
    claimed_source_document_id = Column(String(36), nullable=True)
    approved_source_page = Column(Integer, nullable=True)
    actual_source_page = Column(Integer, nullable=True)
    claimed_source_page = Column(Integer, nullable=True)
    approved_source_table = Column(String(200), nullable=True)
    actual_source_table = Column(String(200), nullable=True)
    claimed_source_table = Column(String(200), nullable=True)
    approved_confidence = Column(Float, nullable=True)
    actual_confidence = Column(Float, nullable=True)
    claimed_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_comparison_case", "case_id", "canonical_name"),
    )


# ─── 5. Reviews ───

class Review(Base):
    """Officer review decisions on comparison items."""
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=_uuid)
    comparison_id = Column(String(36), ForeignKey("comparisons.id"), nullable=False, index=True)
    
    # Officer action
    action = Column(String(20), nullable=False)  # "approve" | "reject" | "edit"
    officer_name = Column(String(100), default="Demo Officer")
    officer_comment = Column(Text, nullable=True)
    
    # Edited values (if action == "edit")
    edited_value = Column(Float, nullable=True)
    
    # AI draft note
    ai_explanation = Column(Text, nullable=True)
    
    reviewed_at = Column(DateTime, default=datetime.utcnow)


# ─── 6. Generated Orders ───

class GeneratedOrder(Base):
    """Generated PDF order metadata."""
    __tablename__ = "generated_orders"

    id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), nullable=False, index=True)
    financial_year = Column(String(10), nullable=False, default="2024-25")
    
    # PDF info
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256
    file_size = Column(Integer, default=0)
    
    # Status
    is_draft = Column(Boolean, default=True)
    watermark_text = Column(String(100), default="DRAFT GENERATED FOR REVIEW")
    
    # Stats
    total_items = Column(Integer, default=0)
    auto_approved = Column(Integer, default=0)
    review_required = Column(Integer, default=0)
    
    generated_by = Column(String(100), default="system")
    generated_at = Column(DateTime, default=datetime.utcnow)
