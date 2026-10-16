from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.execute import router as execute_router
from app.routers.problems import router as problems_router
from app.routers.web import router as web_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "execute_router",
    "problems_router",
    "web_router",
]