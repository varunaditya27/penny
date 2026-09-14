from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.api.v1.api import api_router
from backend.app.config import settings
from backend.app.db.session import Base, engine


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    Base.metadata.create_all(bind=engine)
    yield


docs_url = None if settings.ENVIRONMENT.lower() == "production" else "/docs"
redoc_url = None if settings.ENVIRONMENT.lower() == "production" else "/redoc"

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Penny — Autonomous AI Financial Affordability Assistant & Simulation Engine API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Penny API", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to Penny AI Financial Affordability API",
        "docs_url": docs_url,
        "version": "0.1.0",
    }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
