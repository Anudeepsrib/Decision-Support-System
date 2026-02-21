"""
Canonical SQLAlchemy Schema for the ARR Truing-Up Decision Support System.
Models: ARRComponent, RuleSet, AuditTrail, MappingRecord, ExtractionEvidence.
Database: PostgreSQL (relational) for audited ARR heads.
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# ─── Enumerations ───

class CostHeadType(PyEnum):
    O_AND_M = "O&M"
    POWER_PURCHASE = "Power_Purchase"
    INTEREST = "Interest"
    DEPRECIATION = "Depreciation"
    ROE = "Return_on_Equity"
    OTHER = "Other"


class VarianceCategory(PyEnum):
    CONTROLLABLE = "Controllable"
    UNCONTROLLABLE = "Uncontrollable"


class MappingStatus(PyEnum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    OVERRIDDEN = "Overridden"
    REJECTED = "Rejected"


class SBUType(PyEnum):
    """Strategic Business Unit types for data isolation (SBU Partitioning constraint)."""
    SBU_GENERATION = "SBU-G"
    SBU_TRANSMISSION = "SBU-T"
    SBU_DISTRIBUTION = "SBU-D"


# ─── Core Models ───

class ARRComponent(Base):
    """
    Represents a single line-item in the Annual Revenue Requirement.
    Each row maps to a cost head (O&M, Power Purchase, Interest, etc.)
    with Approved vs. Actual values for a specific financial year.
    """
    __tablename__ = "arr_components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)  # SBU Partitioning: SBU-G, SBU-T, SBU-D
    financial_year = Column(String(10), nullable=False, index=True)  # e.g., "2024-25"
    cost_head = Column(Enum(CostHeadType), nullable=False)
    category = Column(Enum(VarianceCategory), nullable=False)
    approved_amount = Column(Float, nullable=False)
    actual_amount = Column(Float, nullable=True)  # Null until human-verified
    variance = Column(Float, nullable=True)
    is_human_verified = Column(Boolean, default=False)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    mappings = relationship("MappingRecord", back_populates="arr_component")
    evidence = relationship("ExtractionEvidence", back_populates="arr_component")

    __table_args__ = (
        UniqueConstraint("sbu_code", "financial_year", "cost_head", name="uq_sbu_fy_costhead"),
        Index("ix_arr_sbu_fy_head", "sbu_code", "financial_year", "cost_head"),
    )

    def __repr__(self):
        return f"<ARRComponent(sbu={self.sbu_code.value}, fy={self.financial_year}, head={self.cost_head.value}, approved={self.approved_amount})>"


class RuleSet(Base):
    """
    Versioned regulatory rule configuration.
    Ensures 100% reproducibility: if rules_v1.2 is used, the results are deterministic.
    """
    __tablename__ = "rule_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False, unique=True)  # e.g., "KSERC-MYT-2022-27-v1.0"
    order_date = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    constants_snapshot = Column(JSON, nullable=False)  # Frozen snapshot of all constants
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    deprecated_at = Column(DateTime, nullable=True)

    # Relationships
    audit_trails = relationship("AuditTrail", back_populates="rule_set")

    def __repr__(self):
        return f"<RuleSet(version={self.version}, active={self.is_active})>"


class AuditTrail(Base):
    """
    Immutable audit log for every computation performed by the Rule Engine.
    Provides full traceability: clause references, input snapshots, and output values.
    Designed for WORM (Write Once, Read Many) compliance.
    """
    __tablename__ = "audit_trails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    checksum = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 for integrity
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)  # SBU Partitioning
    rule_set_id = Column(Integer, ForeignKey("rule_sets.id"), nullable=False)
    arr_component_id = Column(Integer, ForeignKey("arr_components.id"), nullable=True)
    scenario_label = Column(String(100), nullable=False)
    cost_head = Column(String(50), nullable=False)
    variance_category = Column(String(20), nullable=False)
    approved_amount = Column(Float, nullable=False)
    actual_amount = Column(Float, nullable=False)
    variance_amount = Column(Float, nullable=False)
    disallowed_variance = Column(Float, nullable=False, default=0.0)
    passed_through_variance = Column(Float, nullable=False, default=0.0)
    disallowance_reason = Column(Text, nullable=True)  # Explicit reason for disallowance
    logic_applied = Column(Text, nullable=False)
    regulatory_clause = Column(String(200), nullable=False)
    regulatory_description = Column(Text, nullable=True)
    engine_version = Column(String(50), nullable=False)
    flags = Column(JSON, default=list)
    input_snapshot = Column(JSON, nullable=True)  # Full input data frozen at computation time

    # Relationships
    rule_set = relationship("RuleSet", back_populates="audit_trails")

    def __repr__(self):
        return f"<AuditTrail(sbu={self.sbu_code.value}, scenario={self.scenario_label}, head={self.cost_head}, checksum={self.checksum[:8]}...)>"


class MappingRecord(Base):
    """
    Human-in-the-loop mapping verification.
    Tracks AI-suggested mappings (e.g., "Employee Expense" -> "O&M Component")
    and the officer's Confirm/Override decision with mandatory comments.
    """
    __tablename__ = "mapping_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)  # SBU Partitioning
    arr_component_id = Column(Integer, ForeignKey("arr_components.id"), nullable=False)
    ai_suggested_head = Column(String(100), nullable=False)
    ai_suggested_category = Column(String(50), nullable=False)
    ai_confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    officer_decision = Column(Enum(MappingStatus), default=MappingStatus.PENDING)
    officer_override_head = Column(String(100), nullable=True)
    officer_comment = Column(Text, nullable=True)  # Mandatory on Override/Reject
    decided_by = Column(String(100), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    arr_component = relationship("ARRComponent", back_populates="mappings")

    def __repr__(self):
        return f"<MappingRecord(sbu={self.sbu_code.value}, ai={self.ai_suggested_head}, status={self.officer_decision.value})>"


class ExtractionEvidence(Base):
    """
    PDF extraction provenance.
    Links every extracted figure to its source page, table, and bounding coordinates.
    Ensures that if the system claims O&M = 500 Cr, it can cite the exact PDF location.
    """
    __tablename__ = "extraction_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)  # SBU Partitioning
    arr_component_id = Column(Integer, ForeignKey("arr_components.id"), nullable=False)
    source_filename = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=False)
    table_index = Column(Integer, nullable=True)  # Which table on the page
    cell_reference = Column(String(20), nullable=True)  # e.g., "B4"
    extracted_value = Column(Float, nullable=False)
    extraction_confidence = Column(Float, nullable=False)
    extraction_method = Column(String(50), nullable=False)  # "OCR", "LLM_RAG", "Manual"
    raw_text_snippet = Column(Text, nullable=True)  # The raw text around the extraction
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    arr_component = relationship("ARRComponent", back_populates="evidence")

    def __repr__(self):
        return f"<ExtractionEvidence(sbu={self.sbu_code.value}, file={self.source_filename}, page={self.page_number}, value={self.extracted_value})>"
