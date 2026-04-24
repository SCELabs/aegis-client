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

    def context(
        self,
        *,
        objective: str,
        messages: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        constraints: list[str] | None = None,
        symptoms: list[str] | None = None,
        severity: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> AegisResult:
        payload = {
            "objective": objective,
            "messages": messages or [],
            "tool_results": tool_results or [],
            "constraints": constraints or [],
            "symptoms": symptoms or ["context_noise"],
            "severity": severity,
            "metadata": metadata or {},
        }
        return self._client._execute_scope(scope="context", payload=payload)

    def agent(
        self,
        *,
        goal: str,
        steps: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
        max_steps: int | None = None,
        symptoms: list[str] | None = None,
        severity: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> AegisResult:
        merged_metadata = dict(metadata or {})
        if session_id and "session_id" not in merged_metadata:
            merged_metadata["session_id"] = session_id

        payload = {
            "goal": goal,
            "steps": steps or [],
            "tools": tools or [],
            "symptoms": symptoms or ["unstable_workflow"],
            "severity": severity,
            "metadata": merged_metadata,
        }
        if max_steps is not None:
            payload["max_steps"] = max_steps

        return self._client._execute_scope(scope="agent", payload=payload)
