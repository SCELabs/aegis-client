# Aegis Client

**Runtime control for AI systems.**

Aegis sits on top of your AI pipeline and returns structured control decisions that stabilize behavior at runtime without replacing your model, agent, or retrieval system.

---

## Why Aegis

Modern AI systems often fail in subtle but costly ways:

* inconsistent outputs across similar inputs
* unstable multi-step reasoning
* retrieval drift in RAG systems
* fragile workflow and agent execution

Aegis addresses these problems with **runtime stabilization**, not retraining, fine-tuning, or model swapping.

---

## Core Idea

Aegis is a **control layer**, not an execution layer.

```python
from aegis import AegisClient

client = AegisClient(api_key="YOUR_API_KEY")

result = client.auto().llm(...)
```

Aegis will:

* detect instability signals
* select corrective actions
* return runtime controls and observability data

Aegis does **not** execute the downstream LLM call for you.

---

## Installation

```bash
pip install scelabs-aegis
```

---

## Hosted or Self-Hosted

You can use Aegis through the hosted API or against your own backend deployment.

---

## Get an API Key

### Hosted

```bash
curl -X POST https://aegis-backend-production-4b47.up.railway.app/v1/onboard \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

### Local

```bash
curl -X POST http://localhost:8000/v1/onboard \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

This returns:

* `api_key`
* `auto_llm_url`
* `auto_rag_url`
* `auto_step_url`
* example usage

---

## Set Environment

### Hosted

```bash
export AEGIS_API_KEY=your_key_here
export AEGIS_BASE_URL=https://aegis-backend-production-4b47.up.railway.app
```

### Local

```bash
export AEGIS_API_KEY=your_key_here
export AEGIS_BASE_URL=http://localhost:8000
```

---

## First Call

```python
from aegis import AegisClient, AegisConfig

client = AegisClient(
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
print(result.scope_data)
```

---

## Scope-First API

Aegis uses a **scope-first runtime interface**:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

These calls map to first-class public backend routes:

* POST /v1/auto/llm
* POST /v1/auto/rag
* POST /v1/auto/step

---

## Scopes

### LLM

Use `llm` when you need stabilization around a direct model call.

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input={"user_query": "Explain recursion simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

### RAG

Use `rag` when instability appears in retrieval plus generation.

```python
result = client.auto().rag(
    query="What changed in the policy?",
    retrieved_context=[
        "Policy updated last week.",
        "Refund window reduced to 14 days."
    ],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

### Step

Use `step` when you need stabilization for a workflow or agent step.

```python
result = client.auto().step(
    step_name="coordinator",
    step_input={"task": "resolve ticket"},
    symptoms=["unstable_workflow"],
    severity="medium",
)
```

---

## What Aegis Returns

Every call returns an `AegisResult`.

```python
result = client.auto().llm(...)
```

### Key fields

* `actions` — interventions Aegis selected
* `trace` — list-based control trace
* `metrics` — runtime signals
* `used_fallback` — whether fallback behavior was used
* `explanation` — concise rationale
* `scope` — llm, rag, or step
* `scope_data` — scope-specific runtime data

### Important

Aegis is a **control layer**.

That means:

* `final_answer` may be None
* `output` may be None

Aegis does not generate the final model answer itself. It returns the control decisions and runtime shaping you apply to your own model or system.

---

## Typical LLM Integration Pattern

```python
result = client.auto().llm(
    base_prompt="You are a helpful assistant.",
    input={"user_query": "Explain black holes simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

runtime_config = result.scope_data.get("runtime_config", {})
controlled_prompt = result.scope_data.get("controlled_prompt")

print(runtime_config)
print(controlled_prompt)
print(result.actions)
```

You then apply the returned controls in your own downstream model call.

---

## Example Result Shape

```json
{
  "output": null,
  "final_answer": null,
  "metrics": {
    "action_count": 2
  },
  "actions": [
    {
      "type": "reduce_variability",
      "intensity": "medium",
      "label": "Reduce output variability"
    }
  ],
  "trace": [
    {
      "scope": "llm",
      "observation": {},
      "decision": {},
      "actions": [],
      "fallback": {
        "used_fallback": false
      },
      "changes": {},
      "upstream": {}
    }
  ],
  "used_fallback": false,
  "explanation": "Selected because it achieved the highest overall score.",
  "scope": "llm",
  "scope_data": {
    "runtime_config": {
      "temperature": 0.2,
      "top_p": 0.8
    },
    "controlled_prompt": "You are a helpful assistant. ..."
  }
}
```

---

## Debugging

```python
print(result.debug_summary())
print(result.to_dict())
```

Useful fields to inspect first:

```python
print(result.actions)
print(result.explanation)
print(result.trace)
print(result.scope_data)
```

---

## Configuration

```python
from aegis import AegisConfig

config = AegisConfig(
    mode="balanced",
    max_interventions=3,
    allow_retries=True,
    allow_retrieval_expansion=True,
    allow_context_reduction=True,
    allow_prompt_shaping=True,
    fallback="baseline",
    explain=False,
    emit_trace=False,
    policy=None,
    timeout_ms=30000,
)
```

---

## Required Request Inputs

For scope calls, provide:

* `symptoms` — required, non-empty list
* `severity` — required, one of: low, medium, high

Example:

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

## Design Principles

* runtime control over training
* minimal intervention
* observable behavior through trace and actions
* model-agnostic integration

---

## Documentation

Docs in `/docs` explain:

* architecture
* scopes
* result behavior
* integration guidance
* migration and usage patterns

---

## Status

* Stable SDK surface
* Active scopes: llm, rag, step
* Public backend routes aligned to the scope-first contract

---

## License

MIT
