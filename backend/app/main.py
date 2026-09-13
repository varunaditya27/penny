from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.api import api_router
from backend.app.config import settings
from backend.app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Penny — Autonomous AI Financial Affordability Assistant & Simulation Engine API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Penny API", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to Penny AI Financial Affordability API",
        "docs_url": "/docs",
        "version": "0.1.0",
    }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
