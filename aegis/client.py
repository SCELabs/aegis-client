from __future__ import annotations

import os
from typing import Any

import requests

from .auto import AegisAutoFacade
from .config import AegisConfig
from .exceptions import AegisAPIError, AegisConnectionError, AegisTimeoutError
from .result import AegisResult


class AegisClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        config: AegisConfig | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("AEGIS_API_KEY")
        self.base_url = (base_url or os.getenv("AEGIS_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.config = config or AegisConfig()
        self.timeout = self.config.timeout_ms / 1000.0
        self._auto_facade: AegisAutoFacade | None = None

    def auto(self) -> AegisAutoFacade:
        if self._auto_facade is None:
            self._auto_facade = AegisAutoFacade(self)
        return self._auto_facade

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise AegisTimeoutError("Request to Aegis API timed out.") from exc
        except requests.ConnectionError as exc:
            raise AegisConnectionError("Could not connect to the Aegis API.") from exc
        except requests.RequestException as exc:
            raise AegisAPIError(f"Request failed: {exc}") from exc

        if not response.ok:
            message = f"Aegis API returned status {response.status_code}"
            try:
                error_payload = response.json()
                if isinstance(error_payload, dict) and error_payload.get("detail"):
                    message = str(error_payload["detail"])
            except ValueError:
                pass
            raise AegisAPIError(message, status_code=response.status_code)

        try:
            data = response.json()
        except ValueError as exc:
            raise AegisAPIError("Aegis API returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise AegisAPIError("Aegis API returned an unexpected response format.")
        return data

    def _build_auto_payload(self, *, scope: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "scope": scope,
            "config": self.config.to_dict(),
            **payload,
        }

    def _build_stabilize_payload(self, *, scope: str, payload: dict[str, Any]) -> dict[str, Any]:
        base_prompt = payload.get("base_prompt")
        metadata = payload.get("metadata") or {}

        if scope == "rag":
            base_prompt = payload.get("query", "")
            metadata = {
                **metadata,
                "retrieved_context": payload.get("retrieved_context", []),
            }
        elif scope == "step":
            base_prompt = payload.get("step_name", "")
            metadata = {
                **metadata,
                "step_input": payload.get("step_input"),
            }
        elif payload.get("input") is not None:
            metadata = {
                **metadata,
                "input": payload.get("input"),
            }

        stabilize_payload = {
            "system_type": scope,
            "base_prompt": base_prompt or "",
            "symptoms": payload.get("symptoms", []),
            "severity": payload.get("severity", "medium"),
            "include_runtime": True,
            "metadata": metadata,
            "config": self.config.to_dict(),
            "scope": scope,
        }

        if self.config.policy:
            stabilize_payload["policy"] = self.config.policy

        return stabilize_payload

    def _execute_scope(self, *, scope: str, payload: dict[str, Any]) -> AegisResult:
        auto_payload = self._build_auto_payload(scope=scope, payload=payload)

        try:
            raw = self._post_json(f"/v1/auto/{scope}", auto_payload)
        except AegisAPIError as exc:
            if exc.status_code not in (404, 405):
                raise
            stabilize_payload = self._build_stabilize_payload(scope=scope, payload=payload)
            raw = self._post_json("/v1/stabilize", stabilize_payload)

        raw.setdefault("scope", scope)
        return AegisResult.from_dict(raw)