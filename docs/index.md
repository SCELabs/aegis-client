# Aegis Documentation

## What is Aegis?

Aegis is a **runtime control layer for AI systems**.

It sits above your existing pipeline and returns structured control decisions that improve:

* consistency
* efficiency
* execution reliability

Aegis does not replace your models, frameworks, or workflows.
It controls how they behave at runtime.

---

## Who this is for

* Engineers building AI-powered applications
* Developers using LLMs, RAG systems, or agents
* Teams deploying AI systems in production
* AI coding agents integrating Aegis into pipelines

---

## Core Mental Model

You already have a system:

```
LLM / RAG / Agent → inconsistent behavior
```

Aegis sits on top:

```
Your System → Aegis → Control Decisions → Your System Executes
```

Aegis observes behavior, applies control, and returns structured outputs.

---

## How Aegis Works

At runtime:

1. You call Aegis using a scope (`llm`, `rag`, or `step`)

2. You describe instability via:

   * `symptoms`
   * `severity`

3. Aegis evaluates system behavior

4. It selects minimal corrective actions

5. It returns a structured `AegisResult`

You then apply those controls in your system.

---

## Quick Example

```python id="q3r9w1"
from aegis import AegisClient, AegisConfig

client = AegisClient(
    api_key="YOUR_API_KEY",
    config=AegisConfig(mode="balanced"),
)

result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input={"user_query": "Explain recursion simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.actions)
print(result.explanation)
```

---

## Important

Aegis is a **control layer**.

That means:

* it does **not** execute your model
* it does **not** generate the final answer
* `final_answer` may be `None`

Instead, Aegis returns:

* control actions
* runtime configuration
* prompt shaping
* trace and observability

You use these to run your own system.

---

## Scopes

Aegis operates through **scopes**, which define where control is applied:

| Scope  | Use Case                         |
| ------ | -------------------------------- |
| `llm`  | Stabilize model calls            |
| `rag`  | Stabilize retrieval + generation |
| `step` | Stabilize agent/workflow steps   |

Each scope maps to a backend endpoint:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`

---

## Result Model

All calls return an `AegisResult`.

Key fields:

* `actions`
* `trace` (list of decision events)
* `metrics`
* `used_fallback`
* `scope_data`
* `explanation`

Optional fields:

* `final_answer` (often `None`)
* `output` (often `None`)

Aegis is **observable by design** — you can inspect exactly what it did.

---

## Key Principles

### 1. Runtime Control

Aegis operates at execution time, not training time.

---

### 2. Minimal Intervention

It applies only the smallest changes needed to stabilize behavior.

---

### 3. System-Level Thinking

Aegis improves the system, not the model.

---

### 4. Model Agnostic

Works with any LLM or framework.

---

## Backend Reality

Aegis now uses a **scope-first API**:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`

These are the primary public endpoints.

---

## Docs

* [Architecture](./architecture.md)
* [Scopes](./scopes.md)
* [Result Model](./result-model.md)
* [Integration Patterns](./integration-patterns.md)
* [Migration Guide](./migration-guide.md)
* [Troubleshooting](./troubleshooting.md)

---

## Next Step

Start with:

→ `architecture.md`

Then move into:

→ `scopes.md`

Then:

→ `integration-patterns.md`

---

## Summary

Aegis does not replace your system.

It stabilizes how your system behaves at runtime by returning structured control decisions you apply during execution.
