"""
Schemas for the code execution (compile & run) feature.

Mirrors the shape Judge0 returns, normalised into something the frontend can
render directly: what the program printed, what errors it produced, and how
the execution ended.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.config import settings


class CodeLanguage(str, Enum):
    """Languages we expose in the UI. Judge0 supports 60+, we start small."""

    cpp = "cpp"
    c = "c"
    python = "python"
    java = "java"
    javascript = "javascript"


class ExecutionRequest(BaseModel):
    """Payload sent by the frontend to run a snippet of code."""

    language: CodeLanguage = Field(
        default=CodeLanguage.cpp,
        description="Programming language for the snippet.",
    )
    source_code: str = Field(
        ...,
        min_length=1,
        max_length=settings.MAX_SOURCE_CODE_LENGTH,
        description="The source code to compile and run.",
    )
    stdin: str = Field(
        default="",
        max_length=settings.MAX_STDIN_LENGTH,
        description="Text piped to the program's standard input.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "language": "cpp",
                    "source_code": (
                        "#include <iostream>\n"
                        "int main(){\n"
                        "    int a, b;\n"
                        "    std::cin >> a >> b;\n"
                        "    std::cout << a + b << \"\\n\";\n"
                        "    return 0;\n"
                        "}\n"
                    ),
                    "stdin": "3 4",
                }
            ]
        }
    }


class ExecutionStatus(BaseModel):
    """Normalised execution outcome (a subset of Judge0's statuses)."""

    id: int
    description: str


class ExecutionResult(BaseModel):
    """Result of compiling and running a snippet."""

    language: CodeLanguage
    status: ExecutionStatus
    succeeded: bool = Field(
        description="True only when the program compiled and ran without error."
    )
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    time: Optional[float] = Field(
        default=None, description="Program run time in seconds."
    )
    memory: Optional[int] = Field(
        default=None, description="Peak memory used, in kilobytes."
    )
    exit_code: Optional[int] = None


class LanguageInfo(BaseModel):
    """Description of a supported language for the UI dropdown."""

    id: CodeLanguage
    label: str
