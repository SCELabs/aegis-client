# Architecture

## Overview

Aegis is a runtime control layer for AI systems.

It observes request state, selects stabilization controls, and returns structured outputs your existing system applies during execution.

Core layers:

1. Client SDK (this repo)
2. Backend control layer (Aegis API)
3. Your runtime system (models, retrieval, tools, workflows)

---

## Client SDK Interface

The SDK exposes a scope-first interface:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
client.auto().context(...)
client.auto().agent(...)
```

The SDK is responsible for request shaping, transport, and `AegisResult` normalization.

---

## Public API

Current public routes:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`
* `POST /v1/auto/context`
* `POST /v1/auto/agent`

---

## Request Flow

```text
client.auto().<scope>(...)
  -> build scope payload
  -> POST /v1/auto/<scope>
  -> backend evaluates stability
  -> backend returns control decisions
  -> SDK maps response to AegisResult
```

New backends use `/v1/auto/*` routes directly. The SDK keeps legacy fallback only for `llm`/`rag`/`step` when older backends return 404/405. `context` and `agent` require a newer backend.

---

## Control Model

Aegis decisions are based on:

* symptoms (instability signals)
* severity (`low`/`medium`/`high`)
* scope (`llm`, `rag`, `step`, `context`, `agent`)

Scope defines both SDK behavior and backend route boundary.

---

## Result Contract

All calls return `AegisResult` with control and observability data:

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

`output` and `final_answer` may be empty depending on scope and backend response shape.

---

## Execution Responsibility

Aegis does not replace model/tool/workflow execution.

Your system still executes downstream model calls, tool calls, and workflow steps. The `agent` scope controls workflow decisions and can return structured run data, but it is still runtime control on top of your existing system.

---

## Summary

Aegis separates decision-making from execution so you can stabilize behavior without replacing your stack.
