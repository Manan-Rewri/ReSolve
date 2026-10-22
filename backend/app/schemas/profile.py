from pydantic import BaseModel, ConfigDict, Field


class ShareResponse(BaseModel):
    """The token behind a share link. Only the owner can ask for it."""

    token: str
    username: str
    public: bool


class TagCount(BaseModel):
    tag: str
    count: int


class PublicProfileResponse(BaseModel):
    """What a stranger sees at `/p/<token>`. Counts only, never private data."""

    model_config = ConfigDict(populate_by_name=True)

    v: int = 1
    name: str
    joined: str | None = None
    at: str
    solved: int
    in_sheet: int = Field(alias="inSheet")
    reviews: int
    streak: int
    retention: int
    graduated: int
    by_difficulty: dict[str, int] = Field(alias="byDifficulty")
    top_tags: list[TagCount] = Field(alias="topTags")
    live: bool = True
