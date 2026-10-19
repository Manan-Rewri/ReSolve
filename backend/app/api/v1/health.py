from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Deliberately does not touch Supabase."""
    return {"status": "ok", "service": "resolve-api"}
