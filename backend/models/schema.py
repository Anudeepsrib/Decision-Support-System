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


class DecisionMode(PyEnum):
    """Decision classification modes for AI + Human-in-the-Loop system."""
    AI_AUTO = "AI_AUTO"
    PENDING_MANUAL = "PENDING_MANUAL"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class ExternalFactorCategory(PyEnum):
    """External factor categories that trigger manual review."""
    HYDROLOGY = "Hydrology"
    POWER_PURCHASE_VOLATILITY = "Power_Purchase_Volatility"
    GOVT_MANDATE = "Government_Mandate"
    COURT_ORDER = "Court_Order"
    CAPEX_OVERRUN = "CapEx_Overrun"
    FORCE_MAJEURE = "Force_Majeure"
    OTHER = "Other"


class DecisionType(PyEnum):
    """Regulatory decision outcomes."""
    APPROVE = "APPROVE"
    PARTIAL = "PARTIAL"
    DISALLOW = "DISALLOW"


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

class KSERCBenchmark(Base):
    """
    Cached historical benchmarks scraped from erckerala.org.
    Used by the Rule Engine to calculate Year-over-Year trends and validate norms.
    """
    __tablename__ = "kserc_benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    financial_year = Column(String(10), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False) # e.g., "Approved_Distribution_Loss_Percent"
    metric_value = Column(Float, nullable=False)
    source_url = Column(String(255), nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("financial_year", "metric_name", name="uq_fy_metric"),
    )

    def __repr__(self):
        return f"<KSERCBenchmark(fy={self.financial_year}, metric={self.metric_name}, val={self.metric_value})>"

class HistoricalRecord(Base):
    """
    Stores finalized year-over-year Truing-Up financial aggregates.
    Designed for fast 'Side-by-Side' multi-year dashboard rendering.
    """
    __tablename__ = "historical_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    financial_year = Column(String(10), nullable=False, unique=True, index=True) # e.g. "2022-23"
    
    # Core Aggregates 
    power_purchase_cost = Column(Float, nullable=False, default=0.0)
    o_and_m_cost = Column(Float, nullable=False, default=0.0)
    staff_cost = Column(Float, nullable=False, default=0.0)
    line_loss_percent = Column(Float, nullable=False, default=0.0)
    
    total_approved_arr = Column(Float, nullable=False, default=0.0)
    total_actual_arr = Column(Float, nullable=False, default=0.0)
    revenue_gap = Column(Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<HistoricalRecord(fy={self.financial_year}, gap={self.revenue_gap})>"


# ─── AI + Human-in-the-Loop Models (KSERC Truing-Up) ───

class PetitionData(Base):
    """
    Stores extracted petition document data with SBU-wise breakdown.
    Links to source PDF evidence for traceability.
    """
    __tablename__ = "petition_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)
    financial_year = Column(String(10), nullable=False, index=True)
    petition_id = Column(String(100), nullable=False, index=True)
    
    # Core ARR Components from Petition
    claimed_arr = Column(Float, nullable=False, default=0.0)
    claimed_erc = Column(Float, nullable=False, default=0.0)
    claimed_revenue_gap = Column(Float, nullable=False, default=0.0)
    
    # Cost Head Breakdown
    om_cost = Column(Float, nullable=False, default=0.0)
    power_purchase_cost = Column(Float, nullable=False, default=0.0)
    interest_cost = Column(Float, nullable=False, default=0.0)
    depreciation = Column(Float, nullable=False, default=0.0)
    roe = Column(Float, nullable=False, default=0.0)
    
    # Source Document Reference
    source_filename = Column(String(255), nullable=False)
    extraction_confidence = Column(Float, nullable=False, default=0.0)
    extraction_method = Column(String(50), nullable=False, default="OCR")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("sbu_code", "financial_year", "petition_id", name="uq_petition_sbu_fy"),
    )

    def __repr__(self):
        return f"<PetitionData(sbu={self.sbu_code.value}, fy={self.financial_year}, claimed={self.claimed_arr})>"


class ARRData(Base):
    """
    Stores Approved ARR data from KSERC Orders for comparison.
    """
    __tablename__ = "arr_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)
    financial_year = Column(String(10), nullable=False, index=True)
    order_reference = Column(String(100), nullable=False)  # e.g., "OP 15/2025"
    
    # Approved Values
    approved_arr = Column(Float, nullable=False, default=0.0)
    approved_erc = Column(Float, nullable=False, default=0.0)
    approved_revenue_gap = Column(Float, nullable=False, default=0.0)
    
    # Cost Head Breakdown
    om_cost = Column(Float, nullable=False, default=0.0)
    power_purchase_cost = Column(Float, nullable=False, default=0.0)
    interest_cost = Column(Float, nullable=False, default=0.0)
    depreciation = Column(Float, nullable=False, default=0.0)
    roe = Column(Float, nullable=False, default=0.0)
    
    # Source Document Reference
    source_filename = Column(String(255), nullable=False)
    order_date = Column(String(20), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("sbu_code", "financial_year", name="uq_arr_sbu_fy"),
    )

    def __repr__(self):
        return f"<ARRData(sbu={self.sbu_code.value}, fy={self.financial_year}, approved={self.approved_arr})>"


class DeviationReport(Base):
    """
    Pre-computed deviation analysis between Petition vs Approved vs Actual.
    Stores variance calculations with classification.
    """
    __tablename__ = "deviation_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)
    financial_year = Column(String(10), nullable=False, index=True)
    cost_head = Column(Enum(CostHeadType), nullable=False)
    
    # Variance Values
    petition_value = Column(Float, nullable=False, default=0.0)
    approved_value = Column(Float, nullable=False, default=0.0)
    actual_value = Column(Float, nullable=True)
    
    # Computed Deviations
    deviation_petition_vs_approved = Column(Float, nullable=False, default=0.0)
    deviation_approved_vs_actual = Column(Float, nullable=True)
    variance_percent = Column(Float, nullable=True)
    
    # Classification
    category = Column(Enum(VarianceCategory), nullable=False)
    is_controllable = Column(Boolean, nullable=False, default=True)
    
    # External Factor Detection
    external_factor_detected = Column(Boolean, default=False)
    external_factor_category = Column(Enum(ExternalFactorCategory), nullable=True)
    external_factor_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("sbu_code", "financial_year", "cost_head", name="uq_deviation_sbu_fy_head"),
    )

    def __repr__(self):
        return f"<DeviationReport(sbu={self.sbu_code.value}, fy={self.financial_year}, head={self.cost_head.value})>"


class AIDecision(Base):
    """
    AI-generated recommendation for each line item with confidence scoring.
    Part of the Human-in-the-Loop decision flow.
    """
    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deviation_report_id = Column(Integer, ForeignKey("deviation_reports.id"), nullable=False)
    
    # AI Recommendation
    decision = Column(Enum(DecisionType), nullable=False)
    decision_mode = Column(Enum(DecisionMode), nullable=False, default=DecisionMode.AI_AUTO)
    confidence_score = Column(Float, nullable=False, default=0.0)
    
    # Variance Analysis
    recommended_value = Column(Float, nullable=False, default=0.0)
    variance_percent = Column(Float, nullable=False, default=0.0)
    
    # Auto-Flagging Triggers
    variance_exceeds_threshold = Column(Boolean, default=False)
    low_confidence = Column(Boolean, default=False)
    partial_decision = Column(Boolean, default=False)
    
    # Justification (AI-generated draft)
    ai_justification = Column(Text, nullable=True)
    regulatory_clause = Column(String(200), nullable=True)
    
    # External Factor Detection
    external_factor_category = Column(Enum(ExternalFactorCategory), nullable=True)
    external_factor_detected = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deviation_report = relationship("DeviationReport")

    def __repr__(self):
        return f"<AIDecision(decision={self.decision.value}, mode={self.decision_mode.value}, confidence={self.confidence_score})>"


class ManualJustification(Base):
    """
    Officer's manual override with mandatory justification.
    Part of the Human-in-the-Loop system.
    """
    __tablename__ = "manual_justifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ai_decision_id = Column(Integer, ForeignKey("ai_decisions.id"), nullable=False)
    
    # Officer Information
    officer_name = Column(String(100), nullable=False)
    officer_designation = Column(String(100), nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)
    
    # Decision Override
    officer_decision = Column(Enum(DecisionType), nullable=False)
    final_value = Column(Float, nullable=False, default=0.0)
    
    # Justification (MANDATORY for overrides)
    justification_text = Column(Text, nullable=False)
    external_factor_category = Column(Enum(ExternalFactorCategory), nullable=True)
    external_factor_description = Column(Text, nullable=True)
    
    # Audit Metadata
    ip_address = Column(String(50), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Compliance Reference
    electricity_act_section = Column(String(50), nullable=True)
    kserc_regulation_ref = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ai_decision = relationship("AIDecision")

    def __repr__(self):
        return f"<ManualJustification(officer={self.officer_name}, decision={self.officer_decision.value})>"


class FinalOrder(Base):
    """
    Generated KSERC-compliant Truing-Up Order.
    Contains aggregated decisions and embedded justifications.
    """
    __tablename__ = "final_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Order Metadata
    financial_year = Column(String(10), nullable=False, index=True)
    sbu_code = Column(Enum(SBUType), nullable=False, index=True)
    order_date = Column(String(20), nullable=False)
    
    # Order Status
    is_draft = Column(Boolean, default=True)
    has_pending_decisions = Column(Boolean, default=False)
    draft_watermark = Column(Boolean, default=True)
    
    # Aggregated Values
    total_approved_arr = Column(Float, nullable=False, default=0.0)
    total_actual_arr = Column(Float, nullable=False, default=0.0)
    total_revenue_gap = Column(Float, nullable=False, default=0.0)
    total_disallowed = Column(Float, nullable=False, default=0.0)
    total_passed_through = Column(Float, nullable=False, default=0.0)
    
    # Order Content (JSON for structured data)
    sbu_analysis = Column(JSON, nullable=True)
    deviations_findings = Column(JSON, nullable=True)
    commission_decisions = Column(JSON, nullable=True)
    
    # Generated Document
    document_html = Column(Text, nullable=True)
    document_pdf_path = Column(String(500), nullable=True)
    
    # Manual Decisions Summary
    manual_decisions_count = Column(Integer, default=0)
    ai_auto_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    
    # Approval Chain
    prepared_by = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<FinalOrder(order_id={self.order_id}, draft={self.is_draft}, pending={self.has_pending_decisions})>"


class OverrideAuditLog(Base):
    """
    Dedicated audit log for all manual overrides and edits.
    Ensures 100% traceability for regulatory compliance.
    """
    __tablename__ = "override_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Action Reference
    action_type = Column(String(50), nullable=False)  # "OVERRIDE", "EDIT", "GENERATE"
    entity_type = Column(String(50), nullable=False)  # "AIDecision", "ManualJustification", "FinalOrder"
    entity_id = Column(Integer, nullable=False)
    
    # Actor Information
    officer_name = Column(String(100), nullable=False)
    officer_role = Column(String(100), nullable=True)
    
    # Change Details
    field_changed = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_reason = Column(Text, nullable=True)
    
    # Compliance
    justification_provided = Column(Boolean, default=False)
    regulatory_basis = Column(String(200), nullable=True)
    
    # Technical Metadata
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Integrity
    checksum = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_officer", "officer_name", "created_at"),
    )

    def __repr__(self):
        return f"<OverrideAuditLog(action={self.action_type}, officer={self.officer_name})>"
