from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.affordability import AffordabilityRequest, AffordabilityResponse
from backend.app.services.finance_service import FinanceService

router = APIRouter(prefix="/affordability", tags=["Affordability"])


@router.post("/evaluate", response_model=AffordabilityResponse)
def evaluate_affordability(
    request_in: AffordabilityRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluates whether a purchase is safe across a forward 90-day simulation window.
    Determines amount_safe_to_pay, affordability_status, recommended_payment_method,
    payment_plan, earliest_date_for_full_payment, and required spending modifications.
    """
    service = FinanceService(db)
    try:
        response = service.evaluate_affordability(request_in)
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Simulation error: {str(e)}")
