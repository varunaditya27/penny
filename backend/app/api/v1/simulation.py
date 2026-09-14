import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_simulation_service, verify_user_access
from backend.app.exceptions import UserNotFoundError
from backend.app.schemas.simulation import TrajectoryResponse
from backend.app.services.simulation_service import SimulationService

logger = logging.getLogger("penny.api.simulation")

router = APIRouter(prefix="/simulation", tags=["Simulation"])


@router.get("/trajectory/{user_id}", response_model=TrajectoryResponse)
def get_cashflow_trajectory(
    user_id: str,
    prospective_amount: Optional[float] = Query(
        None, gt=0, description="Optional prospective purchase amount to evaluate against baseline"
    ),
    start_date: Optional[str] = Query(None, description="Simulation starting date (YYYY-MM-DD)"),
    days: int = Query(90, ge=1, le=180, description="Forecast horizon in days (default 90)"),
    service: SimulationService = Depends(get_simulation_service),
    _authorized_user: str = Depends(verify_user_access),
):
    """
    Simulates and returns the daily cash-flow balance trajectory for a user,
    providing both baseline balances and with-purchase comparison points.
    """
    try:
        trajectory = service.compute_user_trajectory(
            user_id=user_id,
            prospective_amount=prospective_amount,
            start_date=start_date,
            days=days,
        )
        return trajectory
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error computing trajectory for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while calculating the cash-flow trajectory.",
        )
