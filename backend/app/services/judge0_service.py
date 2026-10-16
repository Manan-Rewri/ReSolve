import asyncio
import base64
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status as http_status

from app.config import settings
from app.schemas.execution import (
    CodeLanguage,
    ExecutionResult,
    ExecutionStatus,
)

# SECURITY: user code is never compiled or run here. A submitted program could
# read our secrets, delete files or exhaust the host, so every run is relayed to
# a sandboxed Judge0 instance that isolates it.
#
# Same code works against the free public instance, Judge0 on RapidAPI
# (X-RapidAPI-* headers) and self-hosted/Sulu (X-Auth-Token).
LANGUAGES: Dict[CodeLanguage, Dict[str, Any]] = {
    CodeLanguage.cpp: {"id": 54, "label": "C++ (GCC 9.2.0)"},
    CodeLanguage.c: {"id": 50, "label": "C (GCC 9.2.0)"},
    CodeLanguage.python: {"id": 71, "label": "Python (3.8.1)"},
    CodeLanguage.java: {"id": 62, "label": "Java (OpenJDK 13.0.1)"},
    CodeLanguage.javascript: {"id": 63, "label": "JavaScript (Node.js 12.14.0)"},
}

# Language ids are shared across the public, RapidAPI and Sulu deployments.
PENDING_STATUS_IDS = {1, 2}
ACCEPTED_STATUS_ID = 3
INTERNAL_ERROR_STATUS_ID = 13

MAX_POLL_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 0.5


class Judge0Service:
    def __init__(self) -> None:
        self._base_url = settings.JUDGE0_BASE_URL.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.JUDGE0_API_HOST:
            headers["X-RapidAPI-Host"] = settings.JUDGE0_API_HOST
        if settings.JUDGE0_API_KEY:
            if settings.JUDGE0_API_HOST:
                headers["X-RapidAPI-Key"] = settings.JUDGE0_API_KEY
            else:
                headers["X-Auth-Token"] = settings.JUDGE0_API_KEY
        return headers

    @staticmethod
    def language_options() -> list:
        return [{"id": lang, "label": meta["label"]} for lang, meta in LANGUAGES.items()]

    async def execute(
        self,
        source_code: str,
        language: CodeLanguage = CodeLanguage.cpp,
        stdin: str = "",
        cpu_time_limit: Optional[float] = None,
        memory_limit: Optional[int] = None,
    ) -> ExecutionResult:
        language_meta = LANGUAGES.get(language)
        if language_meta is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported language: {language}",
            )

        payload = {
            "language_id": language_meta["id"],
            # base64 keeps non-ASCII source and control characters intact.
            "source_code": self._encode(source_code),
            "stdin": self._encode(stdin or ""),
            "cpu_time_limit": cpu_time_limit or settings.DEFAULT_CPU_TIME_LIMIT,
            "memory_limit": memory_limit or settings.DEFAULT_MEMORY_LIMIT_KB,
        }
        create_url = f"{self._base_url}/submissions?base64_encoded=true&wait=true"

        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS
        ) as client:
            try:
                response = await client.post(
                    create_url, json=payload, headers=self._headers()
                )
            except httpx.RequestError:
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Code execution service is currently unreachable. "
                        "Please try again in a moment."
                    ),
                )

            self._raise_for_upstream_error(response)
            data = response.json()

            # Some hosts ignore wait=true and only return a token.
            token = data.get("token")
            if "status" not in data and token:
                data = await self._poll(client, token)

        return self._to_result(data, language)

    async def _poll(self, client: httpx.AsyncClient, token: str) -> Dict[str, Any]:
        url = f"{self._base_url}/submissions/{token}?base64_encoded=true"
        for _ in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            response = await client.get(url, headers=self._headers())
            self._raise_for_upstream_error(response)
            data = response.json()
            if data.get("status", {}).get("id") not in PENDING_STATUS_IDS:
                return data

        raise HTTPException(
            status_code=http_status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out waiting for the code execution service.",
        )

    @staticmethod
    def _raise_for_upstream_error(response: httpx.Response) -> None:
        if response.status_code == 429:
            raise HTTPException(
                status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many code submissions right now. Please wait a moment.",
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=http_status.HTTP_502_BAD_GATEWAY,
                detail="Code execution service returned an unexpected error.",
            )

    @staticmethod
    def _encode(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return base64.b64decode(value).decode("utf-8", errors="replace")

    def _to_result(self, data: Dict[str, Any], language: CodeLanguage) -> ExecutionResult:
        status = data.get("status") or {}
        status_id = status.get("id", INTERNAL_ERROR_STATUS_ID)

        return ExecutionResult(
            language=language,
            status=ExecutionStatus(
                id=status_id, description=status.get("description", "Unknown")
            ),
            succeeded=status_id == ACCEPTED_STATUS_ID,
            stdout=self._decode(data.get("stdout")),
            stderr=self._decode(data.get("stderr")),
            compile_output=self._decode(data.get("compile_output")),
            message=self._decode(data.get("message")),
            time=self._to_float(data.get("time")),
            memory=data.get("memory"),
            exit_code=data.get("exit_code"),
        )

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


judge0_service = Judge0Service()