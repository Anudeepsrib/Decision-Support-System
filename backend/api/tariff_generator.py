from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from backend.security.auth import get_current_user, require_permission, TokenData

router = APIRouter(prefix="/tariff", tags=["Tariff Generation"])

# ─── Request/Response Models ───

class TariffGenerationRequest(BaseModel):
    financial_year: str
    net_revenue_gap: float
    total_approved_arr: float
    total_actual_arr: float
    controllable_gap: float
    uncontrollable_gap: float
    anomaly_flags_count: int

class TariffDraftResponse(BaseModel):
    draft_id: str
    financial_year: str
    generated_at: str
    llm_model: str
    draft_narrative: str
    human_review_required: bool = True

# ─── Prompt Template ───

TARIFF_DRAFT_TEMPLATE = """
As a Regulatory AI Assistant for the Kerala State Electricity Board (KSEB) Truing-Up process:
You are tasked with drafting a professional regulatory summary evaluating the finalized revenue gaps.

### CONTEXT
Financial Year: {financial_year}
Total Approved ARR: ₹{total_approved_arr:,.2f}
Total Actual ARR: ₹{total_actual_arr:,.2f}
Net Revenue Gap: ₹{net_revenue_gap:,.2f} (Negative implies a deficit/loss to be recovered, Positive implies a surplus)
Controllable Gap: ₹{controllable_gap:,.2f}
Uncontrollable Gap: ₹{uncontrollable_gap:,.2f}
Anomalies Flagged During Audit: {anomaly_flags_count}

### INSTRUCTIONS
1. Write a 2-3 paragraph plain language summary explaining what the Net Revenue Gap means for this cycle.
2. Clearly suggest whether a tariff revision (increase, decrease, or maintain) is warranted based on the deficit or surplus. 
3. Address the Controllable vs Uncontrollable gap natively according to standard regulatory principles (e.g. uncontrollable gaps are usually passed to consumers, controllable gaps are shared/penalized).
4. Provide a formal "Draft Regulatory Summary" paragraph suitable for inclusion in an official KSERC order.

### WARNING
Keep the tone strictly professional, objective, and regulatory. Do not hallucinate financial numbers outside of the context provided.
"""

# ─── Endpoint ───

@router.post("/generate-draft", response_model=TariffDraftResponse)
async def generate_tariff_draft(
    request: TariffGenerationRequest,
    current_user: TokenData = Depends(get_current_user), # RBAC enforced
    _perm=Depends(require_permission("reports.read")),
):
    """
    Consumes final extracted Rule Engine metrics to generate an LLM-assisted draft 
    regulatory narrative summarizing the revenue gap and tariff implications.
    """
    try:
        # Initialize LangChain Components
        llm = ChatOpenAI(temperature=0.2, model="gpt-4o-mini")
        prompt = PromptTemplate(
            template=TARIFF_DRAFT_TEMPLATE,
            input_variables=[
                "financial_year", 
                "total_approved_arr", 
                "total_actual_arr", 
                "net_revenue_gap", 
                "controllable_gap", 
                "uncontrollable_gap", 
                "anomaly_flags_count"
            ]
        )
        chain = prompt | llm | StrOutputParser()

        # Execute Chain
        narrative = await chain.ainvoke({
            "financial_year": request.financial_year,
            "total_approved_arr": request.total_approved_arr,
            "total_actual_arr": request.total_actual_arr,
            "net_revenue_gap": request.net_revenue_gap,
            "controllable_gap": request.controllable_gap,
            "uncontrollable_gap": request.uncontrollable_gap,
            "anomaly_flags_count": request.anomaly_flags_count
        })

        return TariffDraftResponse(
            draft_id=f"TRF-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            financial_year=request.financial_year,
            generated_at=datetime.now(timezone.utc).isoformat(),
            llm_model="gpt-4o-mini",
            draft_narrative=narrative,
            human_review_required=True
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate tariff draft: {str(e)}")
