from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.paths import FRONTEND_DIR

router = APIRouter(tags=["Web App"], include_in_schema=False)

PAGES = {
    "/": "index.html",
    "/register": "register.html",
    "/login": "login.html",
    "/home": "home.html",
    "/learn": "learn.html",
    "/settings": "settings.html",
}


def render_page(page: str) -> FileResponse:
    path = FRONTEND_DIR / page
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page '{page}' is missing from frontend/.",
        )
    return FileResponse(path)


@router.get("/")
def landing():
    return render_page(PAGES["/"])


@router.get("/register")
def register():
    return render_page(PAGES["/register"])


@router.get("/login")
def login():
    return render_page(PAGES["/login"])


@router.get("/home")
def home():
    return render_page(PAGES["/home"])


@router.get("/learn")
def learn():
    return render_page(PAGES["/learn"])


@router.get("/settings")
def settings():
    return render_page(PAGES["/settings"])