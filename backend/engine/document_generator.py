"""
KSERC-Compliant Document Generator — Truing-Up Order Generation System.

Generates structured Truing-Up Orders in strict KSERC format:
1. Introduction
2. Regulatory Framework
3. Petition Summary
4. SBU-wise Analysis
5. Deviations & Findings
6. Commission Decisions
7. Final Order
8. Appendix (Manual Decisions)

Features:
- Decision mode markers: [A] AI Auto, [M] Manual Override, [P] Pending
- Mandatory justification insertion for overrides
- Draft watermark if pending decisions exist
- Blocks final generation if pending decisions exist
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
import re


class DecisionMode(str, Enum):
    AI_AUTO = "AI_AUTO"
    PENDING_MANUAL = "PENDING_MANUAL"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    PARTIAL = "PARTIAL"
    DISALLOW = "DISALLOW"


# ─── Data Classes ───

@dataclass
class DecisionItem:
    """Single decision item for order generation."""
    sbu_code: str
    cost_head: str
    financial_year: str
    
    # Values
    petition_value: float
    approved_value: float
    actual_value: Optional[float]
    final_value: float
    
    # Decision
    ai_recommendation: str
    officer_decision: Optional[str]
    decision_mode: str
    
    # Justification
    ai_justification: str
    officer_justification: Optional[str]
    regulatory_clause: str
    
    # External Factor
    external_factor_category: Optional[str]
    
    # Marker
    decision_marker: str  # [A], [M], [P]


@dataclass
class OrderMetadata:
    """Metadata for the Truing-Up Order."""
    order_id: str
    financial_year: str
    sbu_code: str
    order_date: str
    
    # Utility Info
    utility_name: str = "Kerala State Electricity Board Ltd. (KSEBL)"
    control_period: str = "2022-27"
    
    # Status
    is_draft: bool = True
    has_pending_decisions: bool = False
    
    # Approval Chain
    prepared_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    
    # Aggregated Values
    total_approved_arr: float = 0.0
    total_actual_arr: float = 0.0
    total_revenue_gap: float = 0.0
    total_disallowed: float = 0.0
    total_passed_through: float = 0.0


@dataclass
class GeneratedOrder:
    """Result of order generation."""
    order_id: str
    html_content: str
    is_draft: bool
    has_pending: bool
    checksum: str
    generated_at: str
    can_finalize: bool


# ─── Document Generator ───

class KSERCOrderGenerator:
    """
    Generates KSERC-compliant Truing-Up Orders with embedded justifications.
    
    Key Features:
    - Structured 8-section format
    - Decision mode markers
    - Mandatory justification blocks for overrides
    - Draft watermark support
    - Hard rule: Block final if pending decisions exist
    """
    
    def __init__(self):
        self.regulatory_framework = """
        <p>This Order is passed under the provisions of the Electricity Act, 2003 
        (Central Act 36 of 2003), specifically:</p>
        <ul>
            <li><strong>Section 61</strong> — Terms and conditions of tariff</li>
            <li><strong>Section 62</strong> — Determination of tariff</li>
            <li><strong>Section 64</strong> — Principles and methodologies for tariff</li>
        </ul>
        <p>And in accordance with the <strong>KSERC Multi-Year Tariff Regulations, 2021</strong> 
        (as amended), specifically Regulations 5.1 (O&M Escalation), 6.3 (Normative Interest), 
        7.4 (T&D Loss Target), and 9.1-9.4 (Gain/Loss Sharing).</p>
        """
    
    def generate(self, 
                 metadata: OrderMetadata, 
                 decisions: List[DecisionItem]) -> GeneratedOrder:
        """
        Generate a complete KSERC Truing-Up Order.
        
        Args:
            metadata: Order metadata and approval chain
            decisions: List of all decision items
            
        Returns:
            GeneratedOrder with HTML content and status
        """
        # Check for pending decisions (HARD RULE)
        pending_count = sum(1 for d in decisions if d.decision_mode == DecisionMode.PENDING_MANUAL.value)
        has_pending = pending_count > 0
        
        if has_pending:
            metadata.is_draft = True
            metadata.has_pending_decisions = True
        
        can_finalize = not has_pending
        
        # Build order sections
        sections = []
        sections.append(self._generate_header(metadata))
        sections.append(self._generate_introduction(metadata))
        sections.append(self._generate_regulatory_framework(metadata))
        sections.append(self._generate_petition_summary(metadata, decisions))
        sections.append(self._generate_sbu_analysis(metadata, decisions))
        sections.append(self._generate_deviations_findings(metadata, decisions))
        sections.append(self._generate_commission_decisions(metadata, decisions))
        sections.append(self._generate_final_order(metadata, decisions))
        sections.append(self._generate_appendix(metadata, decisions))
        sections.append(self._generate_footer(metadata))
        
        # Combine sections
        html_content = "\n".join(sections)
        
        # Generate checksum
        checksum = self._generate_checksum(html_content)
        
        return GeneratedOrder(
            order_id=metadata.order_id,
            html_content=html_content,
            is_draft=metadata.is_draft,
            has_pending=has_pending,
            checksum=checksum,
            generated_at=datetime.now(timezone.utc).isoformat(),
            can_finalize=can_finalize
        )
    
    def _generate_header(self, metadata: OrderMetadata) -> str:
        """Generate order header with watermark if draft."""
        watermark = ""
        if metadata.is_draft:
            watermark = """
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-45deg);
                        font-size: 72px; color: rgba(255, 0, 0, 0.15); font-weight: bold;
                        pointer-events: none; z-index: 1000;">
                DRAFT — PENDING REVIEW
            </div>
            """
        
        return f"""
        <div class="order-header" style="text-align: center; margin-bottom: 30px;">
            {watermark}
            <h1 style="font-size: 18px; font-weight: bold; margin-bottom: 10px;">
                KERALA STATE ELECTRICITY REGULATORY COMMISSION
            </h1>
            <h2 style="font-size: 16px; font-weight: bold; margin-bottom: 5px;">
                Truing-Up Order for FY {metadata.financial_year}
            </h2>
            <p style="font-size: 12px; color: #666;">
                Order ID: {metadata.order_id} | Date: {metadata.order_date}
            </p>
            <p style="font-size: 12px; color: #666;">
                Control Period: {metadata.control_period} | SBU: {metadata.sbu_code}
            </p>
            {"<p style='color: red; font-weight: bold;'>⚠ DRAFT — DO NOT PUBLISH</p>" if metadata.is_draft else ""}
        </div>
        """
    
    def _generate_introduction(self, metadata: OrderMetadata) -> str:
        """Generate Section 1: Introduction."""
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                1. INTRODUCTION
            </h3>
            <p style="text-align: justify; line-height: 1.6;">
                The Kerala State Electricity Regulatory Commission ("the Commission") hereby 
                issues this Truing-Up Order for the Financial Year {metadata.financial_year} for 
                {metadata.utility_name} under the {metadata.sbu_code} Strategic Business Unit.
            </p>
            <p style="text-align: justify; line-height: 1.6;">
                This Order is the outcome of the Truing-Up process mandated under the KSERC 
                Multi-Year Tariff (MYT) Framework for the Control Period 2022-27. The Commission 
                has reviewed the Petition filed by the Utility, compared the Approved Annual 
                Revenue Requirement (ARR) against Actual audited figures, and applied the 
                applicable Gain/Loss Sharing Mechanism as per Regulation 9.
            </p>
            <p style="text-align: justify; line-height: 1.6;">
                <strong>Order Status:</strong> This is a {"<span style='color: red;'>DRAFT ORDER</span>" if metadata.is_draft else "<span style='color: green;'>FINAL ORDER</span>"} 
                {"with <strong>" + str(sum(1 for d in [] if d.decision_mode == DecisionMode.PENDING_MANUAL.value)) + " pending decisions</strong> requiring officer review." if metadata.has_pending_decisions else ""}
            </p>
        </div>
        """
    
    def _generate_regulatory_framework(self, metadata: OrderMetadata) -> str:
        """Generate Section 2: Regulatory Framework."""
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                2. REGULATORY FRAMEWORK
            </h3>
            {self.regulatory_framework}
            <p style="text-align: justify; line-height: 1.6; margin-top: 15px;">
                <strong>Applicable MYT Control Period:</strong> 2022-27<br>
                <strong>Regulatory Constants Applied:</strong> CPI Weight 70%, WPI Weight 30%, 
                ROE Rate 15.5%, SBI EBLR + 2% for Interest
            </p>
        </div>
        """
    
    def _generate_petition_summary(self, metadata: OrderMetadata, decisions: List[DecisionItem]) -> str:
        """Generate Section 3: Petition Summary."""
        summary_rows = ""
        for d in decisions[:5]:  # Show first 5 in summary
            summary_rows += f"""
            <tr>
                <td style="border: 1px solid #333; padding: 5px;">{d.cost_head}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: right;">₹{d.petition_value:,.2f}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: right;">₹{d.approved_value:,.2f}</td>
                <td style="border: 1px solid #333; padding: 5px; text-align: right;">
                    {((d.petition_value - d.approved_value) / d.approved_value * 100):.1f}%
                </td>
            </tr>
            """
        
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                3. PETITION SUMMARY
            </h3>
            <p style="text-align: justify; line-height: 1.6;">
                The Utility filed its Truing-Up Petition for FY {metadata.financial_year}, 
                claiming a total ARR of ₹{metadata.total_actual_arr:,.2f} against the 
                Approved ARR of ₹{metadata.total_approved_arr:,.2f}.
            </p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 11px;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="border: 1px solid #333; padding: 5px;">Cost Head</th>
                        <th style="border: 1px solid #333; padding: 5px;">Petition Claimed</th>
                        <th style="border: 1px solid #333; padding: 5px;">Approved ARR</th>
                        <th style="border: 1px solid #333; padding: 5px;">Variance</th>
                    </tr>
                </thead>
                <tbody>
                    {summary_rows}
                </tbody>
            </table>
        </div>
        """
    
    def _generate_sbu_analysis(self, metadata: OrderMetadata, decisions: List[DecisionItem]) -> str:
        """Generate Section 4: SBU-wise Analysis."""
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                4. SBU-WISE ANALYSIS: {metadata.sbu_code}
            </h3>
            <p style="text-align: justify; line-height: 1.6;">
                The Commission has analyzed each cost head for the {metadata.sbu_code} 
                Strategic Business Unit. The analysis applies the Gain/Loss Sharing Mechanism 
                separately for Controllable and Uncontrollable cost heads as per Regulation 9.
            </p>
            <p style="text-align: justify; line-height: 1.6;">
                <strong>Controllable Costs:</strong> O&M, Depreciation, Return on Equity<br>
                <strong>Uncontrollable Costs:</strong> Power Purchase, Interest & Finance Charges
            </p>
        </div>
        """
    
    def _generate_deviations_findings(self, metadata: OrderMetadata, decisions: List[DecisionItem]) -> str:
        """Generate Section 5: Deviations & Findings."""
        findings = ""
        for d in decisions:
            marker = d.decision_marker
            variance_pct = ((d.petition_value - d.approved_value) / d.approved_value * 100) if d.approved_value else 0
            
            external_factor_note = ""
            if d.external_factor_category:
                external_factor_note = f"<br><em>External Factor Detected: {d.external_factor_category}</em>"
            
            findings += f"""
            <div style="margin: 15px 0; padding: 10px; border-left: 3px solid {'#4CAF50' if d.decision_mode == DecisionMode.AI_AUTO.value else '#FF9800'};">
                <p style="margin: 0; font-weight: bold;">
                    {marker} {d.cost_head} — {d.financial_year}
                </p>
                <p style="margin: 5px 0; font-size: 11px;">
                    Approved: ₹{d.approved_value:,.2f} | 
                    Actual: ₹{d.actual_value:,.2f if d.actual_value else 0:,.2f} | 
                    Variance: {variance_pct:.1f}%
                    {external_factor_note}
                </p>
                <p style="margin: 5px 0; font-size: 11px; color: #555;">
                    <strong>AI Analysis:</strong> {d.ai_justification[:200]}...
                </p>
            </div>
            """
        
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                5. DEVIATIONS & FINDINGS
            </h3>
            <p style="text-align: justify; line-height: 1.6;">
                The Commission has identified the following deviations between Approved ARR and 
                Actual audited figures. Each deviation has been analyzed with AI assistance and 
                flagged for manual review where necessary.
            </p>
            <p style="font-size: 11px; margin: 10px 0;">
                <strong>Legend:</strong> 
                <span style="color: #4CAF50;">[A] AI Auto-Approved</span> | 
                <span style="color: #FF9800;">[M] Manual Override</span> | 
                <span style="color: #F44336;">[P] Pending Review</span>
            </p>
            {findings}
        </div>
        """
    
    def _generate_commission_decisions(self, metadata: OrderMetadata, decisions: List[DecisionItem]) -> str:
        """Generate Section 6: Commission Decisions."""
        decision_blocks = ""
        
        for d in decisions:
            marker = d.decision_marker
            
            # Determine final decision
            final_decision = d.officer_decision if d.officer_decision else d.ai_recommendation
            
            # Justification block
            justification_block = ""
            if d.decision_mode == DecisionMode.MANUAL_OVERRIDE.value and d.officer_justification:
                justification_block = f"""
                <div style="background-color: #FFF8E1; padding: 10px; margin: 10px 0; border: 1px solid #FFB74D;">
                    <p style="margin: 0; font-weight: bold; color: #E65100;">
                        Commission's Analysis and Justification:
                    </p>
                    <p style="margin: 5px 0; font-size: 11px;">
                        <strong>AI Recommendation:</strong> {d.ai_recommendation}<br>
                        <strong>Final Decision:</strong> {final_decision}<br>
                        <strong>Officer Justification:</strong> {d.officer_justification}
                    </p>
                    {f"<p style='margin: 5px 0; font-size: 11px;'><em>External Factor: {d.external_factor_category}</em></p>" if d.external_factor_category else ""}
                </div>
                """
            
            decision_blocks += f"""
            <div style="margin: 20px 0; padding: 15px; border: 1px solid #ddd;">
                <p style="margin: 0; font-weight: bold; font-size: 13px;">
                    {marker} {d.cost_head}
                </p>
                <p style="margin: 5px 0; font-size: 11px;">
                    <strong>Decision:</strong> {final_decision} | 
                    <strong>Final Value:</strong> ₹{d.final_value:,.2f} | 
                    <strong>Regulatory Basis:</strong> {d.regulatory_clause}
                </p>
                {justification_block}
            </div>
            """
        
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                6. COMMISSION DECISIONS
            </h3>
            <p style="text-align: justify; line-height: 1.6;">
                After due consideration of the Petition, the Approved ARR, the Actual audited 
                figures, and the AI-assisted analysis, the Commission hereby decides as follows:
            </p>
            {decision_blocks}
        </div>
        """
    
    def _generate_final_order(self, metadata: OrderMetadata, decisions: List[DecisionItem]) -> str:
        """Generate Section 7: Final Order."""
        pending_warning = ""
        if metadata.has_pending_decisions:
            pending_warning = """
            <div style="background-color: #FFEBEE; border: 2px solid #F44336; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; color: #C62828; font-weight: bold; text-align: center;">
                    ⚠ THIS ORDER CANNOT BE FINALIZED
                </p>
                <p style="margin: 10px 0 0 0; color: #C62828; text-align: center;">
                    Pending decisions require officer review before finalization.
                    This draft may be used for internal review only.
                </p>
            </div>
            """
        
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                7. FINAL ORDER
            </h3>
            {pending_warning}
            <p style="text-align: justify; line-height: 1.6;">
                The Commission hereby approves the Truing-Up of ARR for FY {metadata.financial_year} 
                for {metadata.utility_name} ({metadata.sbu_code}) as follows:
            </p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 12px;">
                <tr style="background-color: #f0f0f0;">
                    <td style="border: 1px solid #333; padding: 8px; font-weight: bold;">Total Approved ARR</td>
                    <td style="border: 1px solid #333; padding: 8px; text-align: right;">₹{metadata.total_approved_arr:,.2f}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #333; padding: 8px; font-weight: bold;">Total Actual ARR</td>
                    <td style="border: 1px solid #333; padding: 8px; text-align: right;">₹{metadata.total_actual_arr:,.2f}</td>
                </tr>
                <tr style="background-color: #f0f0f0;">
                    <td style="border: 1px solid #333; padding: 8px; font-weight: bold;">Revenue Gap</td>
                    <td style="border: 1px solid #333; padding: 8px; text-align: right;">₹{metadata.total_revenue_gap:,.2f}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #333; padding: 8px; font-weight: bold;">Disallowed Amount</td>
                    <td style="border: 1px solid #333; padding: 8px; text-align: right; color: #C62828;">₹{metadata.total_disallowed:,.2f}</td>
                </tr>
                <tr style="background-color: #E8F5E9;">
                    <td style="border: 1px solid #333; padding: 8px; font-weight: bold;">Passed Through to Consumers</td>
                    <td style="border: 1px solid #333; padding: 8px; text-align: right; color: #2E7D32;">₹{metadata.total_passed_through:,.2f}</td>
                </tr>
            </table>
            <p style="text-align: center; margin-top: 30px;">
                <strong>Order Date:</strong> {metadata.order_date}
            </p>
        </div>
        """
    
    def _generate_appendix(self, metadata: OrderMetadata, decisions: List[DecisionItem]) -> str:
        """Generate Section 8: Appendix (Manual Decisions)."""
        # Filter manual decisions and overrides
        manual_decisions = [d for d in decisions if d.decision_mode in 
                          [DecisionMode.MANUAL_OVERRIDE.value, DecisionMode.PENDING_MANUAL.value]]
        
        if not manual_decisions:
            return """
            <div class="section" style="margin-bottom: 25px;">
                <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                    8. APPENDIX — MANUAL DECISIONS SUMMARY
                </h3>
                <p style="text-align: center; color: #666; font-style: italic;">
                    All decisions were AI Auto-Approved. No manual overrides recorded.
                </p>
            </div>
            """
        
        rows = ""
        for d in manual_decisions:
            final = d.officer_decision if d.officer_decision else "PENDING"
            rows += f"""
            <tr>
                <td style="border: 1px solid #333; padding: 5px; font-size: 10px;">{d.sbu_code}</td>
                <td style="border: 1px solid #333; padding: 5px; font-size: 10px;">{d.cost_head}</td>
                <td style="border: 1px solid #333; padding: 5px; font-size: 10px;">{d.ai_recommendation}</td>
                <td style="border: 1px solid #333; padding: 5px; font-size: 10px; font-weight: bold;">
                    {final}
                </td>
                <td style="border: 1px solid #333; padding: 5px; font-size: 10px; text-align: right;">
                    ₹{d.final_value:,.2f}
                </td>
                <td style="border: 1px solid #333; padding: 5px; font-size: 10px;">
                    {d.officer_justification[:100] + "..." if d.officer_justification and len(d.officer_justification) > 100 else (d.officer_justification or "N/A")}
                </td>
            </tr>
            """
        
        return f"""
        <div class="section" style="margin-bottom: 25px;">
            <h3 style="font-size: 14px; font-weight: bold; border-bottom: 1px solid #333; padding-bottom: 5px;">
                8. APPENDIX — MANUAL DECISIONS SUMMARY
            </h3>
            <p style="text-align: justify; line-height: 1.6; font-size: 11px;">
                The following table summarizes all decisions that required manual officer review 
                or were overridden from the AI recommendation:
            </p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 10px;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="border: 1px solid #333; padding: 5px;">SBU</th>
                        <th style="border: 1px solid #333; padding: 5px;">Cost Head</th>
                        <th style="border: 1px solid #333; padding: 5px;">AI Decision</th>
                        <th style="border: 1px solid #333; padding: 5px;">Final Decision</th>
                        <th style="border: 1px solid #333; padding: 5px;">Final Value</th>
                        <th style="border: 1px solid #333; padding: 5px;">Justification Summary</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def _generate_footer(self, metadata: OrderMetadata) -> str:
        """Generate order footer with signatures and integrity info."""
        return f"""
        <div class="footer" style="margin-top: 40px; border-top: 2px solid #333; padding-top: 20px;">
            <div style="display: flex; justify-content: space-between; margin-top: 50px;">
                <div style="width: 30%; text-align: center;">
                    <p style="margin: 0; font-weight: bold;">{metadata.prepared_by or "[Prepared By]"}</p>
                    <p style="margin: 5px 0 0 0; font-size: 10px;">Prepared By</p>
                </div>
                <div style="width: 30%; text-align: center;">
                    <p style="margin: 0; font-weight: bold;">{metadata.reviewed_by or "[Reviewed By]"}</p>
                    <p style="margin: 5px 0 0 0; font-size: 10px;">Reviewed By</p>
                </div>
                <div style="width: 30%; text-align: center;">
                    <p style="margin: 0; font-weight: bold;">{metadata.approved_by or "[Approved By]"}</p>
                    <p style="margin: 5px 0 0 0; font-size: 10px;">Chairman, KSERC</p>
                </div>
            </div>
            <p style="text-align: center; margin-top: 30px; font-size: 9px; color: #666;">
                <strong>Document Integrity:</strong> This order is digitally signed and tamper-evident.<br>
                Order ID: {metadata.order_id} | Generated: {datetime.now(timezone.utc).isoformat()}
            </p>
        </div>
        </body>
        </html>
        """
    
    def _generate_checksum(self, content: str) -> str:
        """Generate SHA-256 checksum for document integrity."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def validate_order_can_finalize(self, decisions: List[DecisionItem]) -> tuple[bool, List[str]]:
        """
        Validate if order can be finalized.
        
        Returns:
            (can_finalize, list of blocking issues)
        """
        issues = []
        
        # Check for pending decisions (HARD RULE)
        pending = [d for d in decisions if d.decision_mode == DecisionMode.PENDING_MANUAL.value]
        if pending:
            issues.append(f"{len(pending)} pending decisions require officer review")
        
        # Check for missing justifications on overrides
        missing_justification = [
            d for d in decisions 
            if d.decision_mode == DecisionMode.MANUAL_OVERRIDE.value and not d.officer_justification
        ]
        if missing_justification:
            issues.append(f"{len(missing_justification)} manual overrides missing justification")
        
        return len(issues) == 0, issues


# ─── Singleton Instance ───
_generator = None

def get_generator() -> KSERCOrderGenerator:
    """Get or create singleton generator instance."""
    global _generator
    if _generator is None:
        _generator = KSERCOrderGenerator()
    return _generator


def generate_truing_up_order(metadata: OrderMetadata, decisions: List[DecisionItem]) -> GeneratedOrder:
    """Convenience function to generate a Truing-Up Order."""
    return get_generator().generate(metadata, decisions)
