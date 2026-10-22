from pydantic import BaseModel, EmailStr


class CurrentUser(BaseModel):
    """The authenticated caller, projected from the Supabase auth user."""

    id: str
    email: EmailStr | None = None
