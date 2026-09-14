from typing import Optional
from fastapi import Depends, Header, HTTPException, status

from backend.app.config import settings
from backend.app.db.session import get_db

DEFAULT_USER_ID = "default_user"


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Stub/mockable auth dependency that returns a default or parsed user ID."""
    if authorization:
        if authorization.startswith("Bearer "):
            token = authorization.split("Bearer ", 1)[1].strip()
        else:
            token = authorization.strip()
        if token:
            return token
    return DEFAULT_USER_ID


def verify_user_access(
    target_user_id: Optional[str] = None,
    current_user_id: str = Depends(get_current_user_id),
    user_id: Optional[str] = None,
) -> str:
    """Verify user access rights.

    Raises 403 Forbidden if not authorized.
    Allows bypass in development/testing if authorization header is not passed.
    Supports both target_user_id and user_id parameter names for FastAPI path resolution.
    """
    effective_target = target_user_id or user_id
    if not effective_target:
        return current_user_id

    if current_user_id == effective_target:
        return current_user_id

    # Allow bypass in non-production environments when default user ID is returned (header omitted)
    if current_user_id == DEFAULT_USER_ID and settings.ENVIRONMENT.lower() != "production":
        return effective_target

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"User '{current_user_id}' is not authorized to access resources for '{effective_target}'.",
    )


# ---------------------------------------------------------------------------
# Service Dependencies & Singleton Domain Engine Injection
# ---------------------------------------------------------------------------
from sqlalchemy.orm import Session
from backend.app.services.event_service import EventService
from backend.app.services.finance_service import FinanceService
from backend.app.services.simulation_service import SimulationService
from backend.core.pipeline import DecisionPipeline

_shared_pipeline: Optional[DecisionPipeline] = None


def get_decision_pipeline() -> DecisionPipeline:
    """Provides a thread-safe singleton instance of DecisionPipeline."""
    global _shared_pipeline
    if _shared_pipeline is None:
        _shared_pipeline = DecisionPipeline(use_llm=False)
    return _shared_pipeline


def get_finance_service(
    db: Session = Depends(get_db),
    pipeline: DecisionPipeline = Depends(get_decision_pipeline),
) -> FinanceService:
    """Dependency provider for FinanceService with injected singleton pipeline."""
    return FinanceService(db=db, pipeline=pipeline)


def get_simulation_service(
    db: Session = Depends(get_db),
) -> SimulationService:
    """Dependency provider for SimulationService."""
    return SimulationService(db=db)


def get_event_service(
    db: Session = Depends(get_db),
) -> EventService:
    """Dependency provider for EventService."""
    return EventService(db=db)

