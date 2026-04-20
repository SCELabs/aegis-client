# Scopes

## Overview

Scopes define **where Aegis applies control** in your system.

They are both:

* a **client interface**
* a **backend API boundary**

Each scope maps directly to a runtime control endpoint.

---

## Available Scopes

Aegis currently supports:

* `llm`
* `rag`
* `step`

All scopes follow the same pattern:

```python
client.auto().<scope>(...)
```

---

## LLM Scope

### What it is

Stabilization for **single model calls**.

---

### When to use

* inconsistent outputs
* prompt instability
* formatting drift
* unreliable reasoning

---

### Example

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input={"user_query": "Explain recursion simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

### What Aegis does

* reduce output variability
* adjust generation parameters
* apply prompt shaping
* enforce consistency

---

### What you do next

Aegis returns control decisions. You apply them:

```python
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
```

Use these in your model call.

---

### When NOT to use

* multi-step workflows
* retrieval pipelines

---

## RAG Scope

### What it is

Stabilization for **retrieval + generation pipelines**.

---

### When to use

* missing context
* irrelevant retrieval
* inconsistent answers
* weak grounding

---

### Example

```python
result = client.auto().rag(
    query="What changed in the refund policy?",
    retrieved_context=[
        "Policy v2 released last week.",
        "Refund window reduced to 14 days."
    ],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

---

### What Aegis does

* expand retrieval when needed
* filter irrelevant context
* rebalance context weighting
* improve grounding signals

---

### Inspecting RAG behavior

```python
print(result.scope_data)
```

Common fields may include:

* retrieval_expansion_triggered
* final_chunks
* removed_chunks
* before_after_metrics

---

### When NOT to use

* direct model calls
* workflow coordination

---

## Step Scope

### What it is

Stabilization for **workflow steps or agent coordination**.

---

### When to use

* agent loops
* multi-agent systems
* tool execution steps
* coordination instability

---

### Example

```python
result = client.auto().step(
    step_name="coordinator",
    step_input={
        "task": "resolve support ticket",
        "history": []
    },
    symptoms=["unstable_workflow"],
    severity="medium",
)
```

---

### What Aegis does

* reduce unnecessary retries
* prevent duplicate actions
* stabilize coordination behavior
* enforce structured execution

---

### Real usage pattern

Use at **execution boundaries**, not inside every micro-step.

---

### When NOT to use

* simple prompt calls
* retrieval pipelines

---

## Choosing the Right Scope

| Situation          | Scope |
| ------------------ | ----- |
| single model call  | llm   |
| retrieval pipeline | rag   |
| workflow or agent  | step  |

---

## Scope Behavior

Each scope maps to a backend endpoint:

* POST /v1/auto/llm
* POST /v1/auto/rag
* POST /v1/auto/step

Scopes are not just abstractions anymore. They define real runtime control boundaries.

---

## Required Inputs

All scopes require:

* `symptoms` — non-empty list
* `severity` — one of: low, medium, high

Example:

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

## Common Mistakes

### Using the wrong scope

```python
# ❌ too large
client.auto().step(...)  

# ✅ correct
client.auto().llm(...)
```

---

### Missing required fields

```python
# ❌ incorrect
client.auto().rag(query="...")

# ✅ correct
client.auto().rag(
    query="...",
    retrieved_context=[...],
    symptoms=["retrieval_drift"],
    severity="medium"
)
```

---

### Expecting execution

Aegis does not execute your system.

```python
# ❌ incorrect assumption
result = client.auto().llm(...)
print(result.final_answer)  # may be None
```

```python
# ✅ correct usage
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
```

---

## Summary

Scopes allow you to:

* target the correct layer of control
* apply minimal intervention
* stabilize systems efficiently

Use the **smallest effective scope** for best results.
