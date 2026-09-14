import logging
import uuid
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import FinancialEventDB, UserDB
from backend.app.exceptions import UserNotFoundError
from backend.app.schemas.event import FinancialEventCreate

logger = logging.getLogger("penny.services.events")


class EventService:
    """
    Manages financial transaction event querying and persistence.
    """

    def __init__(self, db: Session):
        self.db = db

    def list_user_events(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[FinancialEventDB]:
        """
        Lists paginated financial events for a specific user using a lightweight scalar check.
        """
        user_exists = self.db.query(UserDB.user_id).filter_by(user_id=user_id).scalar()
        if not user_exists:
            raise UserNotFoundError(f"User '{user_id}' not found.")

        return (
            self.db.query(FinancialEventDB)
            .filter(FinancialEventDB.user_id == user_id)
            .order_by(FinancialEventDB.event_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create_event(
        self, user_id: str, event_in: FinancialEventCreate
    ) -> FinancialEventDB:
        """
        Creates a new financial event under the given user account.
        """
        user_exists = self.db.query(UserDB.user_id).filter_by(user_id=user_id).scalar()
        if not user_exists:
            raise UserNotFoundError(f"User '{user_id}' not found.")

        ev_id = event_in.event_id or f"evt_{uuid.uuid4().hex[:10]}"
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
            settlement_date=event_in.settlement_date or event_in.event_date,
            status=event_in.status,
            linked_event_id=event_in.linked_event_id,
            flexibility=event_in.flexibility,
            minimum_allowed_amount=event_in.minimum_allowed_amount,
        )

        try:
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            return event
        except IntegrityError as e:
            self.db.rollback()
            logger.warning("Integrity error inserting event %s: %s", ev_id, str(e))
            raise
