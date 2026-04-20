# SDK Overview

## Introduction

The Aegis SDK provides a **scope-first runtime interface** for stabilizing AI systems.

It allows you to wrap existing execution with minimal changes while gaining:

* consistency
* efficiency
* observability

---

## Installation

```bash
pip install scelabs-aegis
```

---

## Basic Setup

```python
from aegis import AegisClient, AegisConfig

client = AegisClient(
    api_key="YOUR_API_KEY",
    base_url="http://localhost:8000",  # optional
    config=AegisConfig(mode="balanced"),
)
```

### Environment Variables (optional)

```bash
AEGIS_API_KEY=...
AEGIS_BASE_URL=http://localhost:8000
```

---

## Core Usage Pattern

All Aegis calls use:

```python
client.auto().<scope>(...)
```

This is the **only primary interface**.

---

## Scopes

### LLM Scope

Used for stabilizing direct model calls.

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
    input="Explain recursion simply."
)
```

---

### RAG Scope

Used for stabilizing retrieval + generation.

```python
result = client.auto().rag(
    query="What changed in the new policy?",
    retrieved_context=[
        "Policy v2 was released last week.",
        "Refund window reduced to 14 days."
    ],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

---

### Step Scope

Used for stabilizing workflow steps or agents.

```python
result = client.auto().step(
    step_name="ticket_triage",
    step_input={"text": "User cannot login"},
    symptoms=["misclassification"],
    severity="high",
)
```

---

## Required Inputs

All scopes require:

### symptoms

A list of instability signals:

```python
symptoms=["inconsistent_outputs"]
```

Examples:

* `"inconsistent_outputs"`
* `"unstable_workflow"`
* `"agents_disagree"`
* `"retrieval_drift"`

---

### severity

Controls intervention strength:

```python
severity="medium"
```

Options:

* `"low"`
* `"medium"`
* `"high"`

---

## Optional Inputs

Depending on scope:

* `input` → for LLM calls
* `metadata` → additional context
* `retrieved_context` → for RAG
* `step_input` → for step scope

---

## AegisResult

Every call returns:

```python
result = client.auto().llm(...)
```

### Fields

* `output` → raw output
* `final_answer` → stabilized result
* `metrics` → execution metrics
* `actions` → applied interventions
* `trace` → decision trace
* `used_fallback` → fallback indicator
* `explanation` → reasoning summary
* `scope` → llm / rag / step
* `scope_data` → scope-specific data

---

## Debugging

```python
print(result.debug_summary())
print(result.to_dict())
print(result.to_log_record())
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

## Modes

### light

* minimal intervention
* low overhead

### balanced (default)

* moderate stabilization
* recommended for most cases

### aggressive

* stronger corrections
* higher control intensity

---

## Execution Behavior

When you call:

```python
client.auto().llm(...)
```

The SDK:

1. builds a scope payload
2. sends request to backend
3. receives response
4. converts it into `AegisResult`

---

## Backend Routing (Important)

The SDK may call:

```text
/v1/auto/<scope>   (if available)
```

If not available:

```text
/v1/stabilize
```

This fallback is automatic.

---

## Best Practices

### Use the smallest scope

* use `llm` for single calls
* use `rag` for retrieval pipelines
* use `step` for workflows

---

### Provide accurate symptoms

Better inputs → better stabilization.

---

### Inspect results

Aegis is designed to be observable:

```python
result.actions
result.trace
```

---

### Avoid overuse

Do not wrap every call blindly.
Use Aegis where instability exists.

---

## Common Mistakes

### Missing symptoms

```python
# ❌ incorrect
client.auto().llm(base_prompt="...")

# ✅ correct
client.auto().llm(
    base_prompt="...",
    symptoms=["inconsistent_outputs"],
    severity="medium"
)
```

---

### Wrong scope

* using `step` for simple prompts
* using `llm` inside agent loops

---

## Summary

The SDK provides:

* a clean scope-based interface
* automatic backend compatibility
* structured runtime outputs

It is the **primary integration point for Aegis**.