from __future__ import annotations

from typing import Any

from .result import AegisResult


class AegisAutoFacade:
    """Facade for scope-specific runtime stabilization calls."""

    def __init__(self, client: "AegisClient") -> None:
        self._client = client

    def llm(
        self,
        *,
        base_prompt: str,
        symptoms: list[str],
        severity: str,
        input: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> AegisResult:
        payload = {
            "base_prompt": base_prompt,
            "symptoms": symptoms,
            "severity": severity,
            "input": input,
            "metadata": metadata or {},
        }
        return self._client._execute_scope(scope="llm", payload=payload)

    def rag(
        self,
        *,
        query: str,
        retrieved_context: list[str],
        symptoms: list[str],
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> AegisResult:
        payload = {
            "query": query,
            "retrieved_context": retrieved_context,
            "symptoms": symptoms,
            "severity": severity,
            "metadata": metadata or {},
        }
        return self._client._execute_scope(scope="rag", payload=payload)

    def step(
        self,
        *,
        step_name: str,
        step_input: Any,
        symptoms: list[str],
        severity: str,
        metadata: dict[str, Any] | None = None,
    ) -> AegisResult:
        payload = {
            "step_name": step_name,
            "step_input": step_input,
            "symptoms": symptoms,
            "severity": severity,
            "metadata": metadata or {},
        }
        return self._client._execute_scope(scope="step", payload=payload)