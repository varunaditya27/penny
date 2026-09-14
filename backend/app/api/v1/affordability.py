import logging
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_finance_service, verify_user_access
from backend.app.exceptions import UserNotFoundError
from backend.app.schemas.affordability import AffordabilityRequest, AffordabilityResponse
from backend.app.services.finance_service import FinanceService

logger = logging.getLogger("penny.api.affordability")

router = APIRouter(prefix="/affordability", tags=["Affordability"])


@router.post("/evaluate", response_model=AffordabilityResponse)
def evaluate_affordability(
    request_in: AffordabilityRequest,
    service: FinanceService = Depends(get_finance_service),
    _authorized_user: str = Depends(verify_user_access),
):
    """
    Evaluates whether a purchase is safe across a forward 90-day simulation window.
    Determines amount_safe_to_pay, affordability_status, recommended_payment_method,
    payment_plan, earliest_date_for_full_payment, and required spending modifications.
    """
    try:
        response = service.evaluate_affordability(request_in)
        return response
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error evaluating affordability for user %s: %s", request_in.user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while evaluating purchase affordability.",
        )
