from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from backend.security.auth import get_current_user, require_permission, TokenData

router = APIRouter(prefix="/history", tags=["Historical Trends"])

class HistoricalTrendResponse(BaseModel):
    financial_year: str
    power_purchase_cost: float
    o_and_m_cost: float
    staff_cost: float
    line_loss_percent: float
    total_approved_arr: float
    total_actual_arr: float
    revenue_gap: float

@router.get("/trends", response_model=List[HistoricalTrendResponse])
async def get_historical_trends(
    current_user: TokenData = Depends(get_current_user), # RBAC enforced
    _perm=Depends(require_permission("reports.read")),
):
    """
    Returns aggregated year-over-year Truing-Up data.
    Provides the required dataset for visualizing multi-year trends (e.g., via Recharts).
    """
    
    # In production, this queries db.query(HistoricalRecord).order_by(HistoricalRecord.financial_year).all()
    # Providing simulated robust dataset for immediate frontend integration and validation
    
    historical_data = [
        {
            "financial_year": "2019-20",
            "power_purchase_cost": 650000000.0,
            "o_and_m_cost": 120000000.0,
            "staff_cost": 80000000.0,
            "line_loss_percent": 14.2,
            "total_approved_arr": 950000000.0,
            "total_actual_arr": 980000000.0,
            "revenue_gap": -30000000.0
        },
        {
            "financial_year": "2020-21",
            "power_purchase_cost": 680000000.0,
            "o_and_m_cost": 125000000.0,
            "staff_cost": 82000000.0,
            "line_loss_percent": 13.5,
            "total_approved_arr": 980000000.0,
            "total_actual_arr": 1020000000.0,
            "revenue_gap": -40000000.0
        },
        {
            "financial_year": "2021-22",
            "power_purchase_cost": 710000000.0,
            "o_and_m_cost": 132000000.0,
            "staff_cost": 86000000.0,
            "line_loss_percent": 12.8,
            "total_approved_arr": 1050000000.0,
            "total_actual_arr": 1080000000.0,
            "revenue_gap": -30000000.0
        },
        {
            "financial_year": "2022-23",
            "power_purchase_cost": 850000000.0,  # Spike year
            "o_and_m_cost": 140000000.0,
            "staff_cost": 91000000.0,
            "line_loss_percent": 12.1,
            "total_approved_arr": 1150000000.0,
            "total_actual_arr": 1250000000.0,
            "revenue_gap": -100000000.0
        },
        {
            "financial_year": "2023-24",
            "power_purchase_cost": 820000000.0,
            "o_and_m_cost": 148000000.0,
            "staff_cost": 95000000.0,
            "line_loss_percent": 11.5,
            "total_approved_arr": 1200000000.0,
            "total_actual_arr": 1220000000.0,
            "revenue_gap": -20000000.0
        }
    ]
    
    return [HistoricalTrendResponse(**data) for data in historical_data]
