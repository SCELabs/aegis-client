# Scopes

## Overview

Scopes define **where Aegis applies control** in your system.

They are a **client-side abstraction** used to target stabilization at the correct layer of execution.

---

## Available Scopes

Aegis currently supports:

* `llm`
* `rag`
* `step`

All scopes use the same pattern:

```python id="scope_pattern"
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

```python id="llm_example"
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input="Explain recursion simply.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

### What Aegis may do

* reduce output variability
* adjust generation parameters
* apply prompt shaping
* enforce consistency

---

### When NOT to use

* full workflows
* multi-step agents
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

```python id="rag_example"
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

### What Aegis may do

* expand retrieval
* filter irrelevant context
* recover missing support
* rebalance context weighting

---

### Inspecting RAG behavior

```python id="rag_debug"
print(result.scope_data)
```

Common fields:

* `retrieval_expansion_triggered`
* `final_chunks`
* `removed_chunks`
* `before_after_metrics`

---

### When NOT to use

* direct LLM calls
* agent loops

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

```python id="step_example"
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

### What Aegis may do

* reduce retries
* prevent unnecessary replans
* suppress duplicate actions
* stabilize coordination behavior

---

### Real usage pattern

Used at **execution boundaries**, not inside every step.

---

### When NOT to use

* simple prompts
* retrieval pipelines

---

## Choosing the Right Scope

| Situation              | Scope  |
| ---------------------- | ------ |
| single model call      | `llm`  |
| retrieval pipeline     | `rag`  |
| workflow or agent step | `step` |

---

## Scope is NOT a Backend Boundary

Important:

Scopes do **not** correspond to backend endpoints.

They are:

* a **client abstraction**
* mapped internally to backend execution

---

## Common Mistakes

### Over-scaling scope

```python id="bad_scope"
# ❌ too large
client.auto().step(...)  # for simple prompt

# ✅ correct
client.auto().llm(...)
```

---

### Under-scaling scope

```python id="bad_scope2"
# ❌ too small
client.auto().llm(...)  # inside multi-agent loop

# ✅ correct
client.auto().step(...)
```

---

### Missing symptoms

```python id="bad_scope3"
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

## Future Scopes (Not Available Yet)

These are planned but not implemented:

* `workflow` → multi-step pipeline control
* `system` → full system orchestration

---

## Summary

Scopes let you:

* target the correct layer of control
* avoid unnecessary intervention
* stabilize systems efficiently

Use the **smallest effective scope**.