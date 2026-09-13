from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.simulation import TrajectoryResponse
from backend.app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["Simulation"])


@router.get("/trajectory/{user_id}", response_model=TrajectoryResponse)
def get_cashflow_trajectory(
    user_id: str,
    prospective_amount: Optional[float] = Query(None, description="Optional prospective purchase amount to evaluate against baseline"),
    start_date: Optional[str] = Query(None, description="Simulation starting date (YYYY-MM-DD)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days (default 90)"),
    db: Session = Depends(get_db),
):
    """
    Simulates and returns the daily cash-flow balance trajectory for a user,
    providing both baseline balances and with-purchase comparison points.
    """
    service = SimulationService(db)
    try:
        trajectory = service.compute_user_trajectory(
            user_id=user_id,
            prospective_amount=prospective_amount,
            start_date=start_date,
            days=days,
        )
        return trajectory
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Trajectory calculation error: {str(e)}")
