from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.security.auth import get_current_user, require_permission, TokenData
from backend.engine.rule_engine import RuleEngine

router = APIRouter(prefix="/efficiency", tags=["Efficiency Analysis"])

class EfficiencyRequest(BaseModel):
    financial_year: str
    actual_line_loss_percent: float

class EfficiencyResponse(BaseModel):
    financial_year: str
    target_loss_percent: float
    actual_loss_percent: float
    deviation_percent: float
    is_violation: bool
    logic_applied: str
    regulatory_clause: str
    penalty_estimate_cr: Optional[float] = 0.0

@router.post("/line-loss", response_model=EfficiencyResponse)
async def analyze_line_loss(
    request: EfficiencyRequest,
    current_user: TokenData = Depends(get_current_user), # RBAC enforced
    _perm=Depends(require_permission("reports.read")),
):
    """
    Evaluates submitted Line Loss percentages against normative KSERC trajectories 
    to output specific efficiency deviations and estimated penalty logic.
    """
    engine = RuleEngine()
    try:
        result = engine.compute_line_loss_efficiency(
            financial_year=request.financial_year, 
            actual_loss_pct=request.actual_line_loss_percent
        )
        
        # Simple mockup penalty estimation: roughly Rs 10 Cr penalty per 1% excess loss for a standard SBU
        penalty = 0.0
        if result["is_violation"]:
            penalty = round(result["deviation_percent"] * 10.0, 2)
            
        return EfficiencyResponse(
            **result,
            penalty_estimate_cr=penalty
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
