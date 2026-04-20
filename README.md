# Aegis Client

**Runtime stabilization for AI systems.**

Aegis sits on top of your AI pipeline and ensures consistent, structured, and reliable behavior at runtime — without changing your models.

---

## Why Aegis

Modern AI systems fail in subtle but costly ways:

* inconsistent outputs across identical inputs
* unstable multi-step reasoning
* retrieval drift in RAG systems
* fragile agent execution loops

Aegis solves this by applying **runtime control and stabilization**, not retraining, prompt hacks, or model swaps.

---

## Core Idea

Instead of trying to make models *smarter*, Aegis makes systems **more stable, predictable, and efficient**.

You call your system through Aegis:

```python
from aegis import AegisClient

client = AegisClient(api_key="YOUR_API_KEY")

result = client.auto().llm(...)
```

Aegis will:

* detect instability signals
* apply minimal corrective actions
* return a structured result you can inspect and use

---

## Installation

```bash
pip install scelabs-aegis
```

---

## Quickstart

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
print(result.actions)
print(result.trace)
```

---

## SDK Surface

Aegis uses a **scope-first runtime interface**:

```python
client.auto().<scope>(...)
```

### Supported scopes

#### LLM

Stabilize model calls and generation behavior.

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

#### RAG

Control retrieval + generation consistency.

```python
result = client.auto().rag(
    query="Summarize the updated policy.",
    retrieved_context=["Policy v2 released last week."],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

---

#### Step

Stabilize workflow steps or agent coordination.

```python
result = client.auto().step(
    step_name="ticket_triage",
    step_input={"text": "User cannot login"},
    symptoms=["misclassification"],
    severity="high",
)
```

---

## AegisResult

Every call returns a structured result object:

```python
result = client.auto().llm(...)
```

### Key fields

* `final_answer` — stabilized output
* `actions` — runtime interventions applied
* `trace` — execution trace (observations → decisions → changes)
* `metrics` — performance and behavior signals
* `used_fallback` — whether fallback logic was triggered
* `scope` — llm / rag / step
* `scope_data` — scope-specific debug data
* `explanation` — human-readable reasoning

### Debugging

```python
print(result.debug_summary())
print(result.to_dict())
```

---

## Configuration

```python
from aegis import AegisConfig

config = AegisConfig(
    mode="balanced",              # light | balanced | aggressive
    max_interventions=3,
    allow_retries=True,
    allow_retrieval_expansion=True,
    allow_context_reduction=True,
    allow_prompt_shaping=True,
    fallback="baseline",          # safe | baseline | strict
    explain=False,
    emit_trace=False,
    policy=None,
    timeout_ms=30000,
)
```

---

## How It Works (High-Level)

Aegis acts as a **runtime control layer**:

1. You describe instability via `symptoms` + `severity`
2. Aegis evaluates system behavior
3. It selects minimal corrective actions
4. It returns structured controls and outputs

This happens **without modifying your model integration**.

---

## Backend Compatibility

The Aegis client is **scope-first**, but supports multiple backend shapes:

* Preferred: `/v1/auto/<scope>` (llm / rag / step)
* Fallback: `/v1/stabilize`

If a scope route is unavailable, the client automatically falls back to the stabilize endpoint.

This ensures compatibility across:

* local deployments
* older backend versions
* production environments

---

## Design Principles

* Runtime control over training
* Minimal intervention, maximum stability
* Observable system behavior (trace + actions)
* Model-agnostic integration

---

## Status

* Stable client SDK
* Production backend available
* Active scopes: `llm`, `rag`, `step`

---

## License

MIT
