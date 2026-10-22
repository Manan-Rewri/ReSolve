from pydantic import BaseModel, Field


class ProblemSummary(BaseModel):
    """Just enough to render and filter the list."""

    slug: str
    title: str
    difficulty: str
    tags: list[str]


class Example(BaseModel):
    input: str
    output: str


class TestCase(BaseModel):
    """One case, with the answer the reference solution produced."""

    #: One entry per parameter. A list, not a joined string: an argument can
    #: contain a comma, and splitting a joined string is lossy.
    args: list[str]
    expected: str


class Problem(BaseModel):
    """A problem, with everything the Learn page needs to render it."""

    slug: str
    title: str
    difficulty: str
    tags: list[str]
    statement: str
    examples: list[Example]
    constraints: list[str]
    signature: str
    #: What the editor starts as: the signature and an empty body.
    editor_start: str


class Sheet(BaseModel):
    """A named group of problems, in the order they should be done."""

    id: str
    name: str
    blurb: str
    tier: str
    #: The problem slugs, in order.
    problems: list[str]
    total: int


class JudgeRequest(BaseModel):
    """A user's function. The harness around it is server-side."""

    slug: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=20_000)


class CaseResult(BaseModel):
    """One case: what was expected, and what the submission actually produced."""

    args: list[str]
    expected: str
    actual: str
    passed: bool


class JudgeResponse(BaseModel):
    slug: str
    passed: int
    total: int
    cases: list[CaseResult]
    #: The compiler's own message, when the submission did not build.
    compile_output: str = ""
    status_text: str
