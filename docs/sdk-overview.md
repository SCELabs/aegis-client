# SDK Overview

## Introduction

The Aegis SDK provides a scope-first runtime interface for stabilizing AI systems.

Aegis is a control layer that returns structured decisions and observability data your existing system applies.

---

## Core Interface

All public SDK usage goes through:

```python
client.auto().<scope>(...)
```

Current scopes:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
client.auto().context(...)
client.auto().agent(...)
```

---

## Backend Routes

Scopes map to public backend endpoints:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`
* `POST /v1/auto/context`
* `POST /v1/auto/agent`

The SDK keeps legacy fallback only for `llm`, `rag`, and `step` when older backends return 404/405. `context` and `agent` require newer backend support.

---

## Minimal Scope Examples

### LLM

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

### RAG

```python
result = client.auto().rag(
    query="What changed in refund policy?",
    retrieved_context=["Policy v3", "Refund window is 14 days"],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

### Step

```python
result = client.auto().step(
    step_name="ticket_triage",
    step_input={"ticket_id": "T-42"},
    symptoms=["routing_instability"],
    severity="high",
)
```

### Context

```python
result = client.auto().context(
    objective="Prepare context for the next response.",
    messages=[{"role": "user", "content": "Summarize blockers"}],
)
```

### Agent

```python
result = client.auto().agent(
    goal="Resolve support ticket safely.",
    steps=[
        {"name": "triage", "input": {"ticket_id": "T-42"}},
        {"name": "draft_response", "input": {"channel": "email"}},
    ],
    max_steps=4,
)
```

---

## Inputs and Defaults

* `llm`, `rag`, and `step` require explicit `symptoms` and `severity`
* `context` and `agent` provide safe defaults for `symptoms` and `severity`
* `severity` values are: `low`, `medium`, `high`

---

## Common Return Type

Every scope call returns `AegisResult`.

Common fields include:

* `actions`
* `trace`
* `metrics`
* `used_fallback`
* `explanation`
* `scope`
* `scope_data`
* `execution` (from `scope_data.execution`, when present)
* `model_tier` (`cheap`/`mid`/`premium`, when present)
* `context_mode` (when present)
* `max_retries` (when present)
* `allow_escalation` (when present)

AegisResult is a control/observability contract, not a guarantee of downstream model execution output.

---

## Summary

The SDK exposes one consistent interface across all five scopes and returns a common `AegisResult` for runtime control integration.
