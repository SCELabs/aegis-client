# Legacy and Migration

## Overview

Aegis has evolved from a **plan-first system** to a **runtime stabilization system**.

This document explains:

* what changed
* what is deprecated
* how to migrate safely

---

## Old Model (Legacy)

The original Aegis design was:

```id="old_model"
AegisPlan → execute → apply controls
```

Characteristics:

* plan generated first
* execution followed plan
* control was precomputed
* API centered around `/v1/plan`

---

### Legacy Components

* `AegisPlan`
* `/v1/plan`
* plan-based execution flow

These are still present in the backend but are **not the primary integration path**.

---

## New Model (Current)

Aegis now operates as:

```id="new_model"
execute → observe → stabilize → return result
```

Characteristics:

* runtime control
* no pre-planning required
* scope-based interface
* structured result output

---

### Primary Interface

```python id="new_interface"
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

---

### Primary Output

```python id="result_interface"
AegisResult
```

---

## Key Shift

### From:

* planning-first
* static control
* plan execution

### To:

* runtime stabilization
* dynamic control
* observable execution

---

## What is Deprecated

### Plan-first usage

```python id="deprecated_plan"
# ❌ do not use
plan = client.plan(...)
```

---

### Direct reliance on `/v1/plan`

```id="deprecated_route"
/v1/plan
```

Still exists, but:

* legacy
* not recommended for new integrations

---

## What is Current

### Scope-first SDK

```python id="current_usage"
result = client.auto().llm(...)
```

---

### Runtime stabilization

* behavior controlled during execution
* no precomputed plan required

---

### Result-driven workflow

```python id="result_usage"
result.actions
result.trace
result.metrics
```

---

## Migration Guide

### Step 1: Remove plan usage

Before:

```python id="before_migration"
plan = client.plan(...)
execute(plan)
```

After:

```python id="after_migration"
result = client.auto().llm(...)
```

---

### Step 2: Replace plan outputs

Before:

```python id="before_outputs"
plan.controls
plan.actions
```

After:

```python id="after_outputs"
result.actions
result.trace
result.metrics
```

---

### Step 3: Use scopes correctly

| Old Concept       | New Scope |
| ----------------- | --------- |
| single agent      | `llm`     |
| retrieval system  | `rag`     |
| workflow / agents | `step`    |

---

### Step 4: Add symptoms + severity

Before:

```python id="before_inputs"
client.plan(base_prompt="...")
```

After:

```python id="after_inputs"
client.auto().llm(
    base_prompt="...",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

## Backend Reality

Even though the SDK is modern:

* `/v1/stabilize` is still the main backend route
* `/v1/plan` still exists

The SDK abstracts this difference.

---

## Mixed Environments

You may encounter:

* legacy backend deployments
* mixed API usage
* partial migrations

The SDK handles this via:

* automatic fallback
* response normalization

---

## When to Use `/v1/plan`

Only if:

* you are debugging backend behavior
* you need raw plan structures
* you are working on internal development

Not for standard integrations.

---

## Common Migration Mistakes

### Trying to replicate plans

Do NOT recreate:

* plan objects
* plan execution flows

---

### Over-engineering

Aegis no longer requires:

* multi-step orchestration
* manual control pipelines

---

### Ignoring result data

```python id="bad_migration"
# ❌ ignoring result
result = client.auto().llm(...)
return result.final_answer
```

Instead:

```python id="good_migration"
print(result.actions)
print(result.trace)
```

---

## Migration Summary

To migrate:

1. remove plan usage
2. switch to `client.auto()`
3. provide symptoms + severity
4. use `AegisResult`

---

## Final Takeaway

Aegis is no longer:

→ a planning system

It is now:

→ a **runtime stabilization layer**
