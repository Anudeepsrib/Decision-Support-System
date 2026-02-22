"""
LangGraph State Machine for Table Extraction
Implements Human-in-the-loop (HITL) and self-correction routing
"""

import os
from typing import TypedDict, List, Optional, Any, Dict
from datetime import datetime, timezone
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# Mocking LangChain LLM for the scope of the system
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

# -- Graph Nodes --

async def extract_data(state: ExtractionState) -> Dict:
    """Simulates LLM call asynchronously generating structured fields."""
    
    # In production, this would use ChatOpenAI.with_structured_output(ExtractedField)
    # over the raw_ocr_pages. We mock it exactly as the previous implementation did.
    mock_fields = [
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
        ).model_dump(),
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
        ).model_dump(),
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
        ).model_dump(),
    ]
    
    # Check if any field returned by the AI needs review
    needs_review = any(f["review_required"] for f in mock_fields)
    
    return {
        "extracted_fields": mock_fields,
        "requires_human_review": needs_review
    }


async def self_correction(state: ExtractionState) -> Dict:
    """If the LLM failed hard, try one self-correction pass before escalating to a human."""
    new_count = state["retry_count"] + 1
    # Mocking correction logic: We just keep the state we have and loop out.
    return {"retry_count": new_count}


async def human_review(state: ExtractionState) -> Dict:
    """
    Node dedicated to capturing HITL logic. 
    LangGraph will `interrupt_before` this node.
    When a Regulatory Officer corrects the JSON in the Mapping Workbench, 
    the system will resume the graph from here.
    """
    return {"requires_human_review": False} # The human fixed it.


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
workflow.add_edge("human_review", END) # After the human approves, the pipeline finishes.

# To support `interrupt_before`, we must use a checkpointer.
# We'll use an in-memory saver for high-speed low-latency ops initially.
memory = MemorySaver()
extraction_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_review"] # Pause the graph here for the UI / Mapping Workbench!
)
