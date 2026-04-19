from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


Mode = Literal["light", "balanced", "aggressive"]
FallbackMode = Literal["safe", "baseline", "strict"]


@dataclass(slots=True)
class AegisConfig:
    """Client-side SDK configuration aligned with backend runtime controls."""

    mode: Mode = "balanced"
    max_interventions: int = 3
    allow_retries: bool = True
    allow_retrieval_expansion: bool = True
    allow_context_reduction: bool = True
    allow_prompt_shaping: bool = True
    fallback: FallbackMode = "baseline"
    explain: bool = False
    emit_trace: bool = False
    policy: str | None = None
    timeout_ms: int = 30_000

    def to_dict(self) -> dict:
        return asdict(self)