from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.profile import UserProfileResponse, UserProfileUpdate
from backend.app.services.finance_service import FinanceService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    service = FinanceService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    risk_metrics = service.compute_user_risk_metrics(user)
    return service.map_user_to_response(user, risk_metrics)


@router.patch("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(user_id: str, update_in: UserProfileUpdate, db: Session = Depends(get_db)):
    service = FinanceService(db)
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    updated_user = service.update_user(user, update_in)
    risk_metrics = service.compute_user_risk_metrics(updated_user)
    return service.map_user_to_response(updated_user, risk_metrics)
