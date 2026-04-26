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

    @property
    def execution(self) -> dict[str, Any]:
        scope_data = self.scope_data if isinstance(self.scope_data, dict) else {}
        execution = scope_data.get("execution")
        return execution if isinstance(execution, dict) else {}

    @property
    def model_tier(self) -> str | None:
        value = self.execution.get("model_tier")
        return value if isinstance(value, str) else None

    @property
    def context_mode(self) -> str | None:
        value = self.execution.get("context_mode")
        return value if isinstance(value, str) else None

    @property
    def max_retries(self) -> int | None:
        value = self.execution.get("max_retries")
        if isinstance(value, bool):
            return None
        return value if isinstance(value, int) else None

    @property
    def allow_escalation(self) -> bool | None:
        value = self.execution.get("allow_escalation")
        return value if isinstance(value, bool) else None

    def summary_lines(self) -> list[str]:
        scope = self.scope or "unknown"
        fallback = "yes" if self.used_fallback else "no"
        lines = [
            f"Scope: {scope}",
            f"Fallback: {fallback}",
            f"Actions: {len(self.actions)} runtime controls",
            f"Trace: {len(self.trace)} steps",
        ]

        if self.explanation:
            lines.append(f"Explanation: {self.explanation}")

        metric_label_map = {
            "step_count": "steps",
            "tool_call_count": "tool calls",
            "failed_tool_call_count": "failed tool calls",
            "carry_forward_count": "carry-forward",
            "input_message_count": "input messages",
            "output_message_count": "output messages",
            "input_tool_result_count": "input tool results",
            "output_tool_result_count": "output tool results",
            "retrieved_context_count": "retrieved context",
            "retrieved_context_count_before_context_control": "retrieved context (before)",
            "retrieved_context_count_after_context_control": "retrieved context (after)",
        }
        important_metric_keys = (
            "step_count",
            "tool_call_count",
            "failed_tool_call_count",
            "carry_forward_count",
            "input_message_count",
            "output_message_count",
            "input_tool_result_count",
            "output_tool_result_count",
            "retrieved_context_count_before_context_control",
            "retrieved_context_count_after_context_control",
            "retrieved_context_count",
        )
        metric_parts = []
        for key in important_metric_keys:
            if key in self.metrics:
                metric_parts.append(f"{metric_label_map[key]}={self.metrics[key]}")
            if len(metric_parts) >= 5:
                break
        if metric_parts:
            lines.append(f"Metrics: {', '.join(metric_parts)}")

        execution_parts = []
        if self.model_tier is not None:
            execution_parts.append(f"model_tier={self.model_tier}")
        if self.context_mode is not None:
            execution_parts.append(f"context={self.context_mode}")
        if self.max_retries is not None:
            execution_parts.append(f"max_retries={self.max_retries}")
        if self.allow_escalation is not None:
            execution_parts.append(f"escalation={self.allow_escalation}")
        if execution_parts:
            lines.append(f"Execution: {', '.join(execution_parts)}")

        carry_forward = self.metrics.get("carry_forward_count")
        scope_data = self.scope_data if isinstance(self.scope_data, dict) else {}

        if scope == "context":
            cleaned_messages = scope_data.get("cleaned_messages")
            cleaned_tool_results = scope_data.get("cleaned_tool_results")
            detail_parts = []
            if isinstance(cleaned_messages, list):
                detail_parts.append(f"cleaned messages={len(cleaned_messages)}")
            elif self.metrics.get("output_message_count") is not None:
                detail_parts.append(
                    f"cleaned messages={self.metrics.get('output_message_count')}"
                )
            if isinstance(cleaned_tool_results, list):
                detail_parts.append(f"cleaned tool results={len(cleaned_tool_results)}")
            elif self.metrics.get("output_tool_result_count") is not None:
                detail_parts.append(
                    f"cleaned tool results={self.metrics.get('output_tool_result_count')}"
                )
            if carry_forward is not None:
                detail_parts.append(f"carry-forward={carry_forward}")
            if detail_parts:
                lines.append(f"Context: {', '.join(detail_parts)}")

        elif scope == "agent":
            agent_runtime = scope_data.get("agent_runtime")
            if isinstance(agent_runtime, dict):
                detail_parts = []
                stop_reason = agent_runtime.get("stop_reason")
                if stop_reason:
                    detail_parts.append(f"stop_reason={stop_reason}")
                step_count = agent_runtime.get("step_count")
                if step_count is None and isinstance(agent_runtime.get("steps"), list):
                    step_count = len(agent_runtime["steps"])
                if step_count is not None:
                    detail_parts.append(f"steps={step_count}")
                tool_call_count = agent_runtime.get("tool_call_count")
                if tool_call_count is None and isinstance(
                    agent_runtime.get("tool_calls"), list
                ):
                    tool_call_count = len(agent_runtime["tool_calls"])
                if tool_call_count is not None:
                    detail_parts.append(f"tool calls={tool_call_count}")
                if detail_parts:
                    lines.append(f"Agent: {', '.join(detail_parts)}")

        elif scope == "rag":
            detail_parts = []
            before = self.metrics.get("retrieved_context_count_before_context_control")
            after = self.metrics.get("retrieved_context_count_after_context_control")
            total = self.metrics.get("retrieved_context_count")
            if before is not None:
                detail_parts.append(f"before={before}")
            if after is not None:
                detail_parts.append(f"after={after}")
            if total is not None:
                detail_parts.append(f"total={total}")
            if detail_parts:
                lines.append(f"RAG: retrieved context {', '.join(detail_parts)}")

        elif scope == "step":
            detail_parts = []
            if carry_forward is not None:
                detail_parts.append(f"carry-forward={carry_forward}")
            context_count = self.metrics.get("retrieved_context_count")
            if context_count is not None:
                detail_parts.append(f"context={context_count}")
            memory_count = scope_data.get("memory_count")
            if memory_count is not None:
                detail_parts.append(f"memory={memory_count}")
            if detail_parts:
                lines.append(f"Step: {', '.join(detail_parts)}")

        elif scope == "llm":
            lines.append(
                "LLM: "
                f"runtime controls={len(self.actions)}, fallback={fallback}"
            )

        return lines or ["No result details available."]

    def summary(self) -> str:
        return "\n".join(self.summary_lines())

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
            "execution": self.execution,
        }
