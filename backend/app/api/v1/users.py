from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.api.deps import get_finance_service, verify_user_access
from backend.app.exceptions import UserNotFoundError
from backend.app.schemas.profile import UserProfileResponse, UserProfileUpdate
from backend.app.services.finance_service import FinanceService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}", response_model=UserProfileResponse)
@router.get("/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(
    user_id: str,
    include_risk_metrics: bool = Query(True, description="Whether to calculate cashflow risk metrics"),
    service: FinanceService = Depends(get_finance_service),
    _authorized_user: str = Depends(verify_user_access),
):
    profile = service.get_user_profile(user_id=user_id, include_risk_metrics=include_risk_metrics)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
    return profile


@router.patch("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(
    user_id: str,
    update_in: UserProfileUpdate,
    service: FinanceService = Depends(get_finance_service),
    _authorized_user: str = Depends(verify_user_access),
):
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    updated_user = service.update_user(user, update_in)
    risk_metrics = service.compute_user_risk_metrics(updated_user)
    return service.map_user_to_response(updated_user, risk_metrics)
