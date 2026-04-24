# Aegis Documentation

## What is Aegis?

Aegis is a runtime control layer for AI systems.

It sits on top of your existing model, retrieval, and workflow stack and returns structured control decisions that help stabilize runtime behavior.

Aegis is not a model, not a full execution engine, and not a replacement for LangChain, LangGraph, or tools.

---

## How Aegis Works

At runtime:

1. You call Aegis with a scope: `llm`, `rag`, `step`, `context`, or `agent`
2. You provide instability signals (typically `symptoms` and `severity`)
3. Aegis evaluates state and selects minimal corrective actions
4. Aegis returns an `AegisResult` with controls and observability
5. Your system applies those controls during downstream execution

---

## Scope Table

| Scope     | Purpose                                   |
| --------- | ----------------------------------------- |
| `llm`     | control generation/model-call behavior    |
| `rag`     | control retrieved evidence/context        |
| `step`    | control one workflow/action               |
| `context` | control information state                 |
| `agent`   | control multi-step workflow loops         |

---

## Quick Example

```python
from aegis import AegisClient

client = AegisClient()

result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.actions)
print(result.explanation)
```

---

## Important

Aegis generally returns control outputs, not final model execution.

That means:

* `final_answer` and `output` may be `None`
* `context` and `agent` may return cleaned context or run-summary style output data
* your downstream model/tool/workflow execution still happens in your system

---

## Backend Reality

Current public auto routes:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`
* `POST /v1/auto/context`
* `POST /v1/auto/agent`

---

## Docs

* [Architecture](./architecture.md)
* [Scopes](./scopes.md)
* [Result Model](./result-model.md)
* [Integration Patterns](./integration-patterns.md)
* [Migration Guide](./legacy-and-migration.md)
* [Troubleshooting](./troubleshoot.md)

---

## Summary

Aegis stabilizes runtime behavior by returning structured control decisions your existing system can apply safely.
