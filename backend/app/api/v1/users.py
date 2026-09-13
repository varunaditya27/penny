from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.models import UserDB
from backend.app.db.session import get_db
from backend.app.schemas.profile import UserProfileResponse, UserProfileUpdate

from backend.app.services.finance_service import FinanceService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    service = FinanceService(db)
    risk_metrics = service.compute_user_risk_metrics(user)

    return UserProfileResponse(
        user_id=user.user_id,
        home_currency=user.home_currency,
        current_available_balance=user.current_available_balance,
        minimum_balance_to_keep=user.minimum_balance_to_keep,
        financial_priorities=user.financial_priorities.split("|") if user.financial_priorities else [],
        expense_categories_to_protect=user.expense_categories_to_protect.split("|") if user.expense_categories_to_protect else [],
        expense_categories_to_reduce=user.expense_categories_to_reduce.split("|") if user.expense_categories_to_reduce else [],
        expense_categories_to_stop=user.expense_categories_to_stop.split("|") if user.expense_categories_to_stop else [],
        payment_methods_user_will_consider=user.payment_methods_user_will_consider.split("|") if user.payment_methods_user_will_consider else [],
        max_installment_months=user.max_installment_months,
        risk_metrics=risk_metrics,
    )


@router.patch("/{user_id}", response_model=UserProfileResponse)
def update_user_profile(user_id: str, update_in: UserProfileUpdate, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    if update_in.minimum_balance_to_keep is not None:
        user.minimum_balance_to_keep = update_in.minimum_balance_to_keep
    if update_in.financial_priorities is not None:
        user.financial_priorities = "|".join(update_in.financial_priorities)
    if update_in.expense_categories_to_protect is not None:
        user.expense_categories_to_protect = "|".join(update_in.expense_categories_to_protect)
    if update_in.expense_categories_to_reduce is not None:
        user.expense_categories_to_reduce = "|".join(update_in.expense_categories_to_reduce)
    if update_in.expense_categories_to_stop is not None:
        user.expense_categories_to_stop = "|".join(update_in.expense_categories_to_stop)
    if update_in.payment_methods_user_will_consider is not None:
        user.payment_methods_user_will_consider = "|".join(update_in.payment_methods_user_will_consider)
    if update_in.max_installment_months is not None:
        user.max_installment_months = update_in.max_installment_months

    db.commit()
    db.refresh(user)

    return get_user_profile(user_id=user_id, db=db)
