from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class AegisResult:
    output: Any = None
    final_answer: Any = None
    metrics: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    used_fallback: bool = False
    explanation: str | None = None
    scope: str | None = None
    scope_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AegisResult":
        return cls(
            output=payload.get("output"),
            final_answer=payload.get("final_answer"),
            metrics=payload.get("metrics") or {},
            actions=payload.get("actions") or [],
            trace=payload.get("trace") or [],
            used_fallback=bool(payload.get("used_fallback", False)),
            explanation=payload.get("explanation"),
            scope=payload.get("scope"),
            scope_data=payload.get("scope_data") or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def debug_summary(self) -> str:
        scope = self.scope or "unknown"
        action_count = len(self.actions)
        trace_count = len(self.trace)
        fallback = "yes" if self.used_fallback else "no"
        return (
            f"scope={scope} actions={action_count} "
            f"trace_steps={trace_count} used_fallback={fallback}"
        )

    def to_log_record(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "used_fallback": self.used_fallback,
            "action_count": len(self.actions),
            "trace_steps": len(self.trace),
            "metrics": self.metrics,
            "explanation": self.explanation,
        }