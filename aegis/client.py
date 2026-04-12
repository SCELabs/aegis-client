import os
from typing import Any, Dict, Optional

import requests

from .exceptions import AegisAPIError, AegisConnectionError, AegisTimeoutError
from .types import StabilizeRequest, StabilizeResponse


class AegisClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("AEGIS_API_KEY")
        self.base_url = (base_url or os.getenv("AEGIS_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, payload: StabilizeRequest) -> StabilizeResponse:
        url = f"{self.base_url}/v1/stabilize"

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
                data = response.json()
                if isinstance(data, dict) and data.get("detail"):
                    message = str(data["detail"])
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

    def stabilize(
        self,
        *,
        system_type: str,
        base_prompt: str,
        symptoms: list[str],
        severity: str,
        policy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StabilizeResponse:
        payload: StabilizeRequest = {
            "system_type": system_type,
            "base_prompt": base_prompt,
            "symptoms": symptoms,
            "severity": severity,
        }
        if policy is not None:
            payload["policy"] = policy
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post(payload)

    def stabilize_with_runtime(
        self,
        *,
        system_type: str,
        base_prompt: str,
        symptoms: list[str],
        severity: str,
        policy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StabilizeResponse:
        payload: StabilizeRequest = {
            "system_type": system_type,
            "base_prompt": base_prompt,
            "symptoms": symptoms,
            "severity": severity,
            "include_runtime": True,
        }
        if policy is not None:
            payload["policy"] = policy
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post(payload)

    def auto(
        self,
        *,
        system_type: str,
        base_prompt: str,
        symptoms: list[str],
        severity: str,
        policy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StabilizeResponse:
        return self.stabilize_with_runtime(
            system_type=system_type,
            base_prompt=base_prompt,
            symptoms=symptoms,
            severity=severity,
            policy=policy,
            metadata=metadata,
        )
