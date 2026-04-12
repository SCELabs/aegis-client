import os
from typing import Any, Dict, Optional

import httpx
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

    def auto_openai_config(
        self,
        *,
        model: str,
        messages: list[dict],
        symptoms: list[str],
        severity: str,
        policy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        system_type: str = "multi_agent",
    ) -> Dict[str, Any]:
        """
        Returns an OpenAI-ready config after applying Aegis stabilization.
        Does NOT call OpenAI. Just prepares the payload.
        """
        base_prompt = ""
        if messages and messages[0].get("role") == "system":
            base_prompt = messages[0]["content"]

        result = self.auto(
            system_type=system_type,
            base_prompt=base_prompt,
            symptoms=symptoms,
            severity=severity,
            policy=policy,
            metadata=metadata,
        )

        runtime = result.get("runtime_config", {})
        prompt_suffix = runtime.get("prompt_suffix")

        updated_messages = [dict(message) for message in messages]
        if prompt_suffix and updated_messages:
            if updated_messages[0].get("role") == "system":
                updated_messages[0]["content"] += " " + prompt_suffix

        return {
            "model": model,
            "messages": updated_messages,
            "temperature": runtime.get("temperature", 0.7),
            "top_p": runtime.get("top_p", 1.0),
            "aegis": result,
        }


class AsyncAegisClient:
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

    async def _post(self, payload: StabilizeRequest) -> StabilizeResponse:
        url = f"{self.base_url}/v1/stabilize"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise AegisTimeoutError("Request to Aegis API timed out.") from exc
        except httpx.ConnectError as exc:
            raise AegisConnectionError("Could not connect to the Aegis API.") from exc
        except httpx.HTTPError as exc:
            raise AegisAPIError(f"Request failed: {exc}") from exc

        if response.status_code >= 400:
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

    async def stabilize(
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

        return await self._post(payload)

    async def stabilize_with_runtime(
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

        return await self._post(payload)

    async def auto(
        self,
        *,
        system_type: str,
        base_prompt: str,
        symptoms: list[str],
        severity: str,
        policy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StabilizeResponse:
        return await self.stabilize_with_runtime(
            system_type=system_type,
            base_prompt=base_prompt,
            symptoms=symptoms,
            severity=severity,
            policy=policy,
            metadata=metadata,
        )

    async def auto_openai_config(
        self,
        *,
        model: str,
        messages: list[dict],
        symptoms: list[str],
        severity: str,
        policy: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        system_type: str = "multi_agent",
    ) -> Dict[str, Any]:
        """
        Returns an OpenAI-ready config after applying Aegis stabilization.
        Does NOT call OpenAI. Just prepares the payload.
        """
        base_prompt = ""
        if messages and messages[0].get("role") == "system":
            base_prompt = messages[0]["content"]

        result = await self.auto(
            system_type=system_type,
            base_prompt=base_prompt,
            symptoms=symptoms,
            severity=severity,
            policy=policy,
            metadata=metadata,
        )

        runtime = result.get("runtime_config", {})
        prompt_suffix = runtime.get("prompt_suffix")

        updated_messages = [dict(message) for message in messages]
        if prompt_suffix and updated_messages:
            if updated_messages[0].get("role") == "system":
                updated_messages[0]["content"] += " " + prompt_suffix

        return {
            "model": model,
            "messages": updated_messages,
            "temperature": runtime.get("temperature", 0.7),
            "top_p": runtime.get("top_p", 1.0),
            "aegis": result,
        }
