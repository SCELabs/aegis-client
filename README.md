# Aegis Client

**Runtime stabilization for AI systems.**

Aegis sits on top of your AI pipeline and ensures consistent, structured, and reliable behavior at runtime—without changing your models.

---

## Why Aegis

AI systems often fail in subtle ways:

* inconsistent outputs across identical inputs
* unstable multi-step reasoning
* retrieval drift in RAG systems
* fragile agent execution

Aegis fixes this by applying **runtime control and stabilization**, not retraining or prompt hacking.

---

## Core Idea

Instead of trying to make models “smarter,” Aegis makes systems **more stable and predictable**.

You call your system through Aegis:

```python
from aegis import AegisClient

client = AegisClient(api_key="YOUR_API_KEY")
result = client.auto().llm(...)
```

Aegis:

* detects instability signals
* applies minimal corrective actions
* returns a structured result you can inspect

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

## Supported Scopes

### LLM

Stabilize single or multi-call model behavior.

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

### RAG

Control retrieval + generation consistency.

```python
result = client.auto().rag(
    query="Summarize the updated support policy.",
    retrieved_context=["Policy v2 released last week."],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

---

### Step

Stabilize individual pipeline or agent steps.

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

Every call returns a structured result:

```python
result = client.auto().llm(...)
```

### Key fields

* `final_answer` – stabilized output
* `actions` – adjustments applied at runtime
* `trace` – execution trace of decisions
* `metrics` – performance and behavior metrics
* `used_fallback` – whether fallback logic was triggered
* `scope` – llm / rag / step
* `scope_data` – scope-specific metadata
* `explanation` – human-readable reasoning

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
    mode="balanced",           # light | balanced | aggressive
    max_interventions=3,
    allow_retries=True,
    allow_retrieval_expansion=True,
    allow_context_reduction=True,
    allow_prompt_shaping=True,
    fallback="safe",           # safe | baseline | strict
    explain=True,
    emit_trace=True,
    policy="best_score",
    timeout_ms=30000,
)
```

---

## Error Handling

Aegis raises explicit errors:

* `AegisAPIError` – API-level failures
* `AegisConnectionError` – network issues
* `AegisTimeoutError` – request timeouts

---

## Design Principles

* **Runtime control over training**
* **Minimal intervention, maximum stability**
* **Observable system behavior (trace + actions)**
* **Model-agnostic integration**

---

## Status

* Stable client SDK
* Production backend available
* Current scopes: `llm`, `rag`, `step`

---

## License

MIT
