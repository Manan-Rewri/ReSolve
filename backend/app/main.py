from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.paths import ASSETS_DIR
from app.routers import (
    auth_router,
    dashboard_router,
    execute_router,
    problems_router,
    web_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Spaced repetition for DSA and LeetCode problems, with a sandboxed code runner.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for api_router in (
    auth_router,
    problems_router,
    dashboard_router,
    execute_router,
):
    app.include_router(api_router, prefix=settings.API_V1_STR)

app.include_router(web_router)

if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/api", tags=["Health Check"])
def api_info():
    return {
        "message": "Welcome to Resolve",
        "app_ui": "/",
        "docs": "/docs",
        "health": "/health",
        "version": settings.VERSION,
    }


@app.get("/health", tags=["Health Check"])
def health():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }