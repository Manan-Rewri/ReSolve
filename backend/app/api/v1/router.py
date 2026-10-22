from fastapi import APIRouter

from app.api.v1 import compiler, health, practice, problems, profile

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(compiler.router)
api_router.include_router(problems.router)
api_router.include_router(practice.router)
api_router.include_router(profile.router)
