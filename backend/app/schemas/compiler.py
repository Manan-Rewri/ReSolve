from pydantic import BaseModel, Field

# Judge0 language ids. We ship C++ only for now.
LANGUAGE_CXX = 54


class CompileRequest(BaseModel):
    source_code: str = Field(min_length=1, max_length=50_000)
    stdin: str = Field(default="", max_length=10_000)
    language_id: int = LANGUAGE_CXX


class CompileResult(BaseModel):
    stdout: str
    stderr: str
    compile_output: str
    status: int
    status_text: str
    time: str | None = None
    memory_kb: int | None = None
