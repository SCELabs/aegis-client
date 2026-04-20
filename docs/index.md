# Aegis Documentation

## What is Aegis?

Aegis is a **runtime stabilization layer for AI systems**.

It sits above your existing pipeline and improves:

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
Your System → Aegis → Stabilized Output
```

Aegis observes behavior, applies control, and returns structured results.

---

## How Aegis Works

At runtime:

1. You call Aegis using a scope (`llm`, `rag`, or `step`)
2. You describe instability via:

   * `symptoms`
   * `severity`
3. Aegis evaluates system behavior
4. It applies minimal corrective actions
5. It returns a structured `AegisResult`

---

## Quick Example

```python
from aegis import AegisClient, AegisConfig

client = AegisClient(
    api_key="YOUR_API_KEY",
    config=AegisConfig(mode="balanced"),
)

result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.final_answer)
```

---

## Scopes

Aegis operates through **scopes**, which define where control is applied:

| Scope  | Use Case                         |
| ------ | -------------------------------- |
| `llm`  | Stabilize model calls            |
| `rag`  | Stabilize retrieval + generation |
| `step` | Stabilize agent/workflow steps   |

---

## Result Model

All calls return an `AegisResult`:

* `final_answer`
* `actions`
* `trace`
* `metrics`
* `used_fallback`
* `scope_data`
* `explanation`

Aegis is **observable by design** — you can see what it did.

---

## Key Principles

### 1. Runtime Control

Aegis operates at execution time, not training time.

### 2. Minimal Intervention

It applies only the smallest changes needed to stabilize behavior.

### 3. System-Level Thinking

Aegis improves the system, not the model.

### 4. Model Agnostic

Works with any LLM or framework.

---

## Backend Reality (Important)

Aegis uses a **scope-first SDK**, but supports multiple backend routes:

* Preferred: `/v1/auto/<scope>`
* Compatible: `/v1/stabilize`

The client handles this automatically.

---

## Docs

* [Architecture](./architecture.md)
* [SDK Overview](./sdk-overview.md)
* [Scopes](./scopes.md)
* [Result Model](./result-model.md)
* [Integration Patterns](./integration-patterns.md)
* [Demo Proofs](./demo-proofs.md)
* [Legacy & Migration](./legacy-and-migration.md)

---

## Next Step

Start with:

→ `architecture.md`

Then move into:

→ `sdk-overview.md`
