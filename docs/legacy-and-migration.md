# Migration Guide

## Overview

This guide covers migration from legacy Aegis route assumptions to the current scope-first public contract.

Use this as the source of truth:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
client.auto().context(...)
client.auto().agent(...)
```

---

## Current Contract (Recommended)

New integrations should use either:

* `client.auto().<scope>(...)` in the SDK
* `/v1/auto/*` routes directly if integrating at HTTP level

Current public routes:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`
* `POST /v1/auto/context`
* `POST /v1/auto/agent`

---

## Legacy Routes

`/v1/stabilize` is legacy.

It should not be treated as the primary route for new integrations.

The SDK preserves compatibility fallback to `/v1/stabilize` only for:

* `llm`
* `rag`
* `step`

Fallback behavior applies only when older backends return 404/405 on `/v1/auto/<scope>`.

`context` and `agent` do not fallback to `/v1/stabilize` and require newer backend support.

---

## Migration Checklist

1. Replace direct legacy route usage with `client.auto().<scope>(...)` or `/v1/auto/*` routes.
2. Keep `llm`/`rag`/`step` symptom + severity inputs explicit.
3. Use `context` and `agent` directly when backend support exists.
4. Treat Aegis responses as control/observability output (`AegisResult`).

---

## Result Handling Reminder

`AegisResult` is shared across scopes and contains runtime control decisions (`actions`, `trace`, `scope_data`, etc.).

It does not replace downstream model/tool/workflow execution.

---

## Summary

For all new work, integrate against scope-first APIs (`client.auto().*` or `/v1/auto/*`). Keep legacy route assumptions only for compatibility with older backends.
