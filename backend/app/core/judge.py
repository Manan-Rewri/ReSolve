"""Runs C++ code.

The public Judge0 instance is slow: a run takes the best part of half a
minute on a good day and the connection is dropped often enough that the
compiler page feels broken. It is also shared with everybody else.

So the code is compiled and run **here** when a C++ compiler is on the
machine, and Judge0 is the fallback. Both paths answer in the same shape —
the same status ids, the same fields — so nothing above this module has to
know which one ran.

The browser never talks to either of them directly.
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import get_settings

#: Where a compiler might be. The environment variable wins, then whatever
#: is on the path, then the toolchain this machine was built with.
DEFAULT_CXX_PATHS = (
    r"C:\w64devkit\bin\g++.exe",
    r"C:\msys64\mingw64\bin\g++.exe",
    "/usr/bin/g++",
    "/usr/local/bin/g++",
)

#: Judge0 status ids. They are used as-is so the two paths agree.
STATUS_ACCEPTED = 3
STATUS_TIME_LIMIT = 5
STATUS_COMPILE_ERROR = 6
STATUS_RUNTIME_ERROR = 10


@dataclass
class RunResult:
    """What a run produced."""

    status: int
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time: str | None = None
    memory_kb: int | None = None


def local_compiler() -> str | None:
    """The C++ compiler to use, or `None` when there is not one."""
    settings = get_settings()
    if not settings.judge_prefer_local:
        return None

    candidates: list[str] = []
    if settings.local_cxx_path:
        candidates.append(settings.local_cxx_path)
    found = shutil.which("g++")
    if found:
        candidates.append(found)
    candidates.extend(DEFAULT_CXX_PATHS)

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


async def run_cxx(source_code: str, stdin: str = "") -> RunResult:
    """Compile and run a C++ program, locally when there is a compiler."""
    compiler = local_compiler()
    if compiler:
        return await run_local(compiler, source_code, stdin)
    return await run_judge0(source_code, stdin)


async def run_local(compiler: str, source_code: str, stdin: str = "") -> RunResult:
    """Compile and run on this machine.

    The work happens in a thread, not in the event loop. This server runs on
    the selector loop — the Windows workaround in `app/loop.py` — and that
    loop has no subprocess support at all. A thread does not care, and the
    event loop stays free to answer other requests while the compiler runs.
    """
    return await asyncio.to_thread(_run_local, compiler, source_code, stdin)


def _run_local(compiler: str, source_code: str, stdin: str = "") -> RunResult:
    """Compile and run on this machine. Blocks."""
    settings = get_settings()
    timeout = settings.local_timeout_seconds

    with tempfile.TemporaryDirectory(prefix="resolve-judge-") as folder:
        source_path = Path(folder) / "main.cpp"
        binary_path = Path(folder) / "main.exe"
        source_path.write_text(source_code, encoding="utf-8")

        try:
            compiled = subprocess.run(
                [
                    compiler,
                    "-std=c++17",
                    "-O1",
                    "-w",
                    "-o",
                    str(binary_path),
                    str(source_path),
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                status=STATUS_TIME_LIMIT,
                compile_output="The program took too long to compile.",
            )
        except OSError as exc:
            return RunResult(
                status=STATUS_COMPILE_ERROR,
                compile_output=f"Could not run the compiler: {exc}",
            )

        if compiled.returncode != 0:
            return RunResult(
                status=STATUS_COMPILE_ERROR,
                compile_output=compiled.stderr[:4000],
            )

        started = time.perf_counter()
        try:
            finished = subprocess.run(
                [str(binary_path)],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                status=STATUS_TIME_LIMIT,
                compile_output="The program ran for too long and was stopped.",
            )
        except OSError as exc:
            return RunResult(
                status=STATUS_RUNTIME_ERROR,
                stderr=f"Could not run the program: {exc}",
            )

        elapsed = time.perf_counter() - started
        status = (
            STATUS_ACCEPTED if finished.returncode == 0 else STATUS_RUNTIME_ERROR
        )
        return RunResult(
            status=status,
            stdout=finished.stdout,
            stderr=finished.stderr[:4000],
            time=f"{elapsed:.3f}",
        )


async def run_judge0(source_code: str, stdin: str = "") -> RunResult:
    """Compile and run on Judge0."""
    import base64

    settings = get_settings()

    headers: dict[str, str] = {}
    if settings.judge0_api_key:
        headers = {
            "X-RapidAPI-Key": settings.judge0_api_key,
            "X-RapidAPI-Host": settings.judge0_host,
        }

    body = {
        "source_code": base64.b64encode(source_code.encode("utf-8")).decode("ascii"),
        "language_id": 54,  # C++ (GCC 9.2.0)
        "stdin": base64.b64encode(stdin.encode("utf-8")).decode("ascii"),
    }

    try:
        async with httpx.AsyncClient(timeout=settings.judge0_timeout_seconds) as client:
            response = await client.post(
                f"{settings.judge0_base_url}/submissions",
                params={"base64_encoded": "true", "wait": "true"},
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        return RunResult(
            status=STATUS_TIME_LIMIT,
            compile_output="The judge did not answer in time. Try again.",
        )
    except httpx.HTTPStatusError as exc:
        return RunResult(
            status=STATUS_COMPILE_ERROR,
            compile_output=f"The judge rejected the submission: {_unb64(exc.response.text)[:200]}",
        )
    except httpx.HTTPError as exc:
        return RunResult(
            status=STATUS_RUNTIME_ERROR,
            compile_output=f"Could not reach the judge: {exc}",
        )

    status_id = data.get("status", {}).get("id")
    if not isinstance(status_id, int):
        return RunResult(
            status=STATUS_RUNTIME_ERROR,
            compile_output="The judge returned an unexpected response.",
        )

    def field(name: str) -> str:
        value = data.get(name)
        return _unb64(value) if value else ""

    return RunResult(
        status=status_id,
        stdout=field("stdout"),
        stderr=field("stderr"),
        compile_output=field("compile_output"),
        time=data.get("time"),
        memory_kb=data.get("memory"),
    )


def _unb64(text: str) -> str:
    """Decode a Judge0 field, tolerating one that was never encoded."""
    import base64

    try:
        return base64.b64decode(text, validate=True).decode("utf-8", "replace")
    except (ValueError, UnicodeDecodeError):
        return text


def compiler_environment() -> dict[str, str]:
    """The environment a compiler run should have."""
    environment = dict(os.environ)
    environment.setdefault("LANG", "C.UTF-8")
    return environment
