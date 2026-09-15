from fastapi import APIRouter

from backend.app.api.v1.affordability import router as affordability_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.events import (
    events_compat_router,
    router as events_router,
)
from backend.app.api.v1.simulation import router as simulation_router
from backend.app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(events_router)
api_router.include_router(events_compat_router)
api_router.include_router(affordability_router)
api_router.include_router(simulation_router)
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])

