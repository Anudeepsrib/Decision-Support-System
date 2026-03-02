"""
LangGraph State Machine for Table Extraction
Implements Human-in-the-loop (HITL) and self-correction routing
with regex-based extraction from real PDF text.
"""

import os
import re
from typing import TypedDict, List, Optional, Any, Dict
from datetime import datetime, timezone
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, AIMessage

# -- Pydantic schema matching the api/extraction.py output --
class ExtractedField(BaseModel):
    field_name: str
    sbu_code: str
    extracted_value: Optional[float]
    confidence_score: float
    source_page: int
    source_table: Optional[int] = None
    cell_reference: Optional[str] = None
    raw_text: Optional[str] = None
    review_required: bool = False

class ExtractionState(TypedDict):
    """The graph's state."""
    job_id: str
    filename: str
    raw_ocr_pages: Dict[int, str]
    extracted_fields: List[Dict[str, Any]]
    retry_count: int
    requires_human_review: bool


# -- Regex-Based Financial Data Extraction --

# Patterns to extract monetary values in various Indian formats
# Matches: Rs. 150.00 Cr, ₹1500.00 Lakhs, 2500000000, 150,00,00,000 etc.
_MONEY_PATTERNS = [
    # "Rs. 150.00 Cr" or "₹ 150.00 Crore"
    r'(?:Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:Cr(?:ore)?|cr)',
    # "Rs. 1500.00 Lakhs" or "₹ 1500 Lakh"
    r'(?:Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:Lakh|lakh)',
    # Plain large numbers with commas (Indian format)
    r'([\d,]+\.?\d*)\s*(?:Cr(?:ore)?|cr)',
    r'([\d,]+\.?\d*)\s*(?:Lakh|lakh)',
]

# Field extraction patterns — keywords to look for in text
_FIELD_PATTERNS = [
    {
        "pattern": r'(?:O\s*[&]\s*M|Operation\s+(?:and|&)\s+Maintenance|O\s*and\s*M)\s*(?:Cost|Expense|Expenditure)?[:\s]*',
        "field_name": "O&M Cost",
        "head": "O&M",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Employee|Staff|Salaries?\s*(?:and|&)\s*Wages?|Personnel)\s*(?:Cost|Expense|Expenditure)?[:\s]*',
        "field_name": "Employee Cost",
        "head": "O&M",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:R\s*[&]\s*M|Repair\s+(?:and|&)\s+Maintenance|Repairs?\s*(?:and|&)\s*Maintenance)\s*(?:Cost|Expense|Expenditure)?[:\s]*',
        "field_name": "R&M Expense",
        "head": "O&M",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:A\s*[&]\s*G|Admin(?:istration)?\s*(?:and|&)\s*General)\s*(?:Cost|Expense|Expenditure)?[:\s]*',
        "field_name": "A&G Expense",
        "head": "O&M",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Power\s+Purchase|Cost\s+of\s+Power\s+Purchase|Energy\s+Purchase)\s*(?:Cost|Expense)?[:\s]*',
        "field_name": "Power Purchase Cost",
        "head": "Power_Purchase",
        "category": "Uncontrollable",
        "sbu_code": "SBU-G",
    },
    {
        "pattern": r'(?:Interest\s+(?:and|&)\s+Finance|Interest\s+on\s+(?:Loan|Debt)|Finance\s+(?:Cost|Charge))\s*(?:s)?[:\s]*',
        "field_name": "Interest & Finance Charges",
        "head": "Interest",
        "category": "Uncontrollable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Depreciation)\s*(?:Cost|Charge|Expense)?[:\s]*',
        "field_name": "Depreciation",
        "head": "Depreciation",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Return\s+on\s+Equity|RoE|ROE)\s*[:\s]*',
        "field_name": "Return on Equity",
        "head": "Return_on_Equity",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Transmission\s+(?:Cost|Charge|Expense))\s*[:\s]*',
        "field_name": "Transmission Charges",
        "head": "Power_Purchase",
        "category": "Uncontrollable",
        "sbu_code": "SBU-T",
    },
    {
        "pattern": r'(?:T\s*(?:and|&)\s*D\s+Loss|T&D\s+Loss|Transmission\s+(?:and|&)\s+Distribution\s+Loss|Line\s+Loss)\s*[:\s]*',
        "field_name": "T&D Loss Percentage",
        "head": "Other",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Total\s+ARR|Aggregate\s+Revenue\s+Requirement|Total\s+Revenue\s+Requirement)\s*[:\s]*',
        "field_name": "Total ARR",
        "head": "Other",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Revenue\s+(?:Gap|Deficit|Surplus)|Net\s+Revenue\s+Gap)\s*[:\s]*',
        "field_name": "Revenue Gap",
        "head": "Other",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
]


def _parse_money(text: str) -> Optional[float]:
    """Parse an Indian monetary string into a float value in absolute rupees."""
    for pattern in _MONEY_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                value = float(raw)
            except ValueError:
                continue
            # Check multiplier
            lower = text[m.start():m.end()].lower()
            if "cr" in lower:
                value *= 1e7  # 1 Crore = 10,000,000
            elif "lakh" in lower:
                value *= 1e5  # 1 Lakh = 100,000
            return value
    
    # Try plain large numbers (no unit suffix)
    plain = re.search(r'([\d,]{4,}\.?\d*)', text)
    if plain:
        raw = plain.group(1).replace(",", "")
        try:
            return float(raw)
        except ValueError:
            pass
    return None


def _extract_percentage(text: str) -> Optional[float]:
    """Extract percentage value from text."""
    m = re.search(r'([\d]+\.?\d*)\s*%', text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _extract_fields_from_text(pages: Dict[int, str]) -> List[Dict[str, Any]]:
    """Extract structured financial fields from raw page texts using regex."""
    extracted = []
    seen_fields = set()
    
    for page_num, page_text in pages.items():
        if not page_text or len(page_text.strip()) < 10:
            continue
        
        # Split page into lines for context
        lines = page_text.split("\n")
        
        for line_idx, line in enumerate(lines):
            for fp in _FIELD_PATTERNS:
                if fp["field_name"] in seen_fields:
                    continue
                
                match = re.search(fp["pattern"], line, re.IGNORECASE)
                if match:
                    # Found a field keyword — now look for a value on this line or the next few
                    context = line
                    # Also grab the next 2 lines for context
                    for offset in range(1, min(3, len(lines) - line_idx)):
                        context += " " + lines[line_idx + offset]
                    
                    # Special handling for percentage fields
                    if "Loss" in fp["field_name"] and "Percent" in fp["field_name"]:
                        value = _extract_percentage(context)
                    else:
                        value = _parse_money(context)
                    
                    # Calculate confidence based on whether we found a value
                    if value is not None:
                        confidence = 0.85 + (0.1 if len(context) > 50 else 0.0)
                    else:
                        confidence = 0.40
                    
                    field = ExtractedField(
                        field_name=fp["field_name"],
                        sbu_code=fp["sbu_code"],
                        extracted_value=value,
                        confidence_score=round(min(confidence, 0.99), 2),
                        source_page=page_num,
                        source_table=None,
                        cell_reference=None,
                        raw_text=line.strip()[:200],
                        review_required=(confidence < 0.7 or value is None)
                    ).model_dump()
                    
                    extracted.append(field)
                    seen_fields.add(fp["field_name"])
    
    # If we didn't find enough fields, create some with data gleaned from numbers in the doc
    if len(extracted) < 3:
        # Fallback: scan for any table-like rows with numbers
        for page_num, page_text in pages.items():
            lines = page_text.split("\n")
            for line in lines:
                # Look for lines with "Approved" / "Actual" / "ARR" keywords
                if any(kw in line for kw in ["Approved", "Actual", "Total", "ARR"]):
                    value = _parse_money(line)
                    if value and f"Auto_{page_num}_{line[:20]}" not in seen_fields:
                        field_name = line.strip()[:60].replace("\t", " ")
                        field = ExtractedField(
                            field_name=field_name,
                            sbu_code="SBU-D",
                            extracted_value=value,
                            confidence_score=0.60,
                            source_page=page_num,
                            raw_text=line.strip()[:200],
                            review_required=True
                        ).model_dump()
                        extracted.append(field)
                        seen_fields.add(f"Auto_{page_num}_{line[:20]}")
                        if len(extracted) >= 12:
                            break
            if len(extracted) >= 12:
                break
    
    return extracted


# -- Graph Nodes --

async def extract_data(state: ExtractionState) -> Dict:
    """Extract structured fields from PDF text using regex-based parsing."""
    
    raw_pages = state.get("raw_ocr_pages", {})
    
    # Use regex-based extraction on the raw text
    fields = _extract_fields_from_text(raw_pages)
    
    # Check if any field needs review
    needs_review = any(f.get("review_required") for f in fields)
    
    return {
        "extracted_fields": fields,
        "requires_human_review": needs_review
    }


async def self_correction(state: ExtractionState) -> Dict:
    """If the LLM failed hard, try one self-correction pass before escalating to a human."""
    new_count = state["retry_count"] + 1
    return {"retry_count": new_count}


async def human_review(state: ExtractionState) -> Dict:
    """
    Node dedicated to capturing HITL logic. 
    LangGraph will `interrupt_before` this node.
    When a Regulatory Officer corrects the JSON in the Mapping Workbench, 
    the system will resume the graph from here.
    """
    return {"requires_human_review": False}


# -- Graph Edges/Routing --

def should_self_correct(state: ExtractionState) -> str:
    """Determine if we should try an automated retry or escalate to HITL/END."""
    needs_review = state.get("requires_human_review", False)
    
    if needs_review and state.get("retry_count", 0) < 1:
        return "self_correction"
    elif needs_review:
        return "human_review"
    
    return END

# -- Graph Compilation --

workflow = StateGraph(ExtractionState)

workflow.add_node("extract_data", extract_data)
workflow.add_node("self_correction", self_correction)
workflow.add_node("human_review", human_review)

workflow.set_entry_point("extract_data")
workflow.add_conditional_edges("extract_data", should_self_correct)
workflow.add_edge("self_correction", "extract_data")
workflow.add_edge("human_review", END)

memory = MemorySaver()
extraction_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_review"]
)
