# Migration Guide

## Overview

This guide explains how to move from older Aegis usage patterns to the current **scope-first runtime control** model.

The current public contract is:

```python id="g8w2m1"
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

Aegis now maps these directly to public backend endpoints:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`

---

## What Changed

### Before

Older docs and examples could imply:

* fallback to `/v1/stabilize`
* fallback to `/v1/plan`
* scope was only a client-side abstraction
* Aegis returned something closer to a direct final answer

### Now

The current model is:

* scope-first public endpoints are real
* scopes are part of both the SDK and backend contract
* Aegis returns **control decisions**, not execution results
* `trace` is a **list of dict events**
* `symptoms` is required
* `severity` is required

---

## Migration Goal

Update your integration so that:

* you call `client.auto().<scope>(...)`
* you read `scope_data`
* you apply returned controls in your own system
* you do not expect Aegis to execute the downstream model call

---

## Migration Step 1: Update Mental Model

### Old assumption

```python id="g4d9q1"
result = client.auto().llm(...)
print(result.final_answer)
```

### New model

```python id="t7r2v8"
result = client.auto().llm(...)

runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
actions = result.actions
```

Aegis tells you **how to stabilize execution**.
Your system performs execution.

---

## Migration Step 2: Use Scope-First Calls

### LLM

```python id="m2k8p6"
result = client.auto().llm(
    base_prompt="You are a helpful assistant.",
    input={"user_query": "Explain recursion simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

### RAG

```python id="q5c1x7"
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

### Step

```python id="y8n4d2"
result = client.auto().step(
    step_name="coordinator",
    step_input={"task": "resolve support ticket"},
    symptoms=["unstable_workflow"],
    severity="medium",
)
```

---

## Migration Step 3: Stop Relying on Legacy Route Assumptions

Do not build around:

* `/v1/stabilize`
* `/v1/plan`

Do build around:

* `/v1/auto/llm`
* `/v1/auto/rag`
* `/v1/auto/step`

If you are using the SDK normally, this mostly means keeping the client updated and using the public scope methods consistently.

---

## Migration Step 4: Treat `trace` as a List

### Old assumption

```python id="r3w6n9"
decision = result.trace["decision"]
```

### Correct usage

```python id="u1m5k4"
decision = result.trace[0]["decision"]
```

Important:

* `trace` is a list
* each element is a decision event
* the first event is usually the one you inspect first

---

## Migration Step 5: Treat `final_answer` as Optional

### Old assumption

```python id="p9x2d8"
print(result.final_answer)
```

### Correct understanding

```python id="s4q7v1"
print(result.final_answer)  # may be None
print(result.output)        # may be None
print(result.scope_data)
```

If Aegis is acting purely as a control layer, `final_answer` and `output` may not be populated.

That is expected behavior.

---

## Migration Step 6: Use `scope_data` for Execution

### LLM migration pattern

```python id="v6t3m8"
result = client.auto().llm(
    base_prompt=prompt,
    input={"user_query": user_query},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

runtime_config = result.scope_data.get("runtime_config", {})
controlled_prompt = result.scope_data.get("controlled_prompt", prompt)

response = model.generate(
    controlled_prompt,
    temperature=runtime_config.get("temperature", 0.7),
    top_p=runtime_config.get("top_p", 1.0),
)
```

This is the key migration step for most users.

---

## Migration Step 7: Provide Required Inputs

The current contract expects:

* `symptoms` — required, non-empty list
* `severity` — required, one of: `low`, `medium`, `high`

### Invalid

```python id="c7n1p5"
result = client.auto().llm(
    base_prompt="You are helpful."
)
```

### Valid

```python id="k4v9m2"
result = client.auto().llm(
    base_prompt="You are helpful.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

## Common Migration Cases

### Case 1: Direct LLM wrapper

If you previously expected Aegis to behave like a model call wrapper, migrate to:

* call Aegis first
* extract controls
* execute your own model call second

---

### Case 2: RAG systems

If you previously treated Aegis as a passive RAG helper, migrate to:

* pass real `retrieved_context`
* inspect `scope_data`
* apply returned context/control signals before generation

---

### Case 3: Agent workflows

If you previously used ad hoc retry logic, migrate to:

* place Aegis at step boundaries
* use `result.actions`, `trace`, and `scope_data`
* stabilize coordination before executing the next step

---

## Quick Migration Checklist

Use this list to confirm you are aligned:

* using `client.auto().llm(...)`, `rag(...)`, or `step(...)`
* passing required `symptoms`
* passing required `severity`
* not depending on legacy route behavior
* reading `trace` as a list
* treating `final_answer` as optional
* applying `scope_data` in downstream execution

---

## Recommended Verification

After migration, check:

```python id="n2q8w6"
print(result.scope)
print(result.actions)
print(result.trace)
print(result.used_fallback)
print(result.scope_data)
```

Expected:

* correct scope name
* populated actions
* list-based trace
* `used_fallback` is usually `False`
* meaningful scope data

---

## Summary

Migration is complete when:

* you use scope-first calls
* you treat Aegis as a control layer
* you apply returned controls in your own system
* you stop expecting Aegis to be the execution engine

That is the stable public model going forward.
