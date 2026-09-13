import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.models import FinancialEventDB, UserDB
from backend.app.db.session import get_db
from backend.app.schemas.event import FinancialEventCreate, FinancialEventResponse

router = APIRouter(prefix="/users/{user_id}/events", tags=["Financial Events"])


@router.get("", response_model=List[FinancialEventResponse])
def list_user_events(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    return user.events


@router.post("", response_model=FinancialEventResponse, status_code=status.HTTP_201_CREATED)
def create_financial_event(user_id: str, event_in: FinancialEventCreate, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter_by(user_id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")

    ev_id = event_in.event_id or f"event_{uuid.uuid4().hex[:8]}"
    event = FinancialEventDB(
        event_id=ev_id,
        user_id=user_id,
        event_type=event_in.event_type,
        description=event_in.description,
        category=event_in.category,
        direction=event_in.direction,
        amount=event_in.amount,
        currency=event_in.currency,
        event_date=event_in.event_date,
        settlement_date=event_in.settlement_date,
        status=event_in.status,
        linked_event_id=event_in.linked_event_id,
        flexibility=event_in.flexibility,
        minimum_allowed_amount=event_in.minimum_allowed_amount,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
