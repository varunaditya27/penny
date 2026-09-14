import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from backend.app.api.deps import get_event_service, verify_user_access
from backend.app.exceptions import UserNotFoundError
from backend.app.schemas.event import FinancialEventCreate, FinancialEventResponse
from backend.app.services.event_service import EventService

logger = logging.getLogger("penny.api.events")

router = APIRouter(prefix="/users/{user_id}/events", tags=["Financial Events"])


@router.get("", response_model=List[FinancialEventResponse])
def list_user_events(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records offset for pagination"),
    service: EventService = Depends(get_event_service),
    _authorized_user: str = Depends(verify_user_access),
):
    try:
        return service.list_user_events(user_id=user_id, limit=limit, offset=offset)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Failed to retrieve events for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving user events.",
        )


@router.post("", response_model=FinancialEventResponse, status_code=status.HTTP_201_CREATED)
def create_financial_event(
    user_id: str,
    event_in: FinancialEventCreate,
    service: EventService = Depends(get_event_service),
    _authorized_user: str = Depends(verify_user_access),
):
    try:
        return service.create_event(user_id=user_id, event_in=event_in)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Financial event with ID '{event_in.event_id}' already exists or violates database constraints.",
        )
    except Exception as e:
        logger.exception("Failed to create event for user %s: %s", user_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the financial event.",
        )
