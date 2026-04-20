# Result Model

## Overview

Every Aegis call returns an `AegisResult`.

This object represents the **control decision output**, not the final execution of your system.

---

## Key Principle

Aegis returns:

* what to change
* how to stabilize
* why the decision was made

It does **not** return the executed model result.

---

## Structure

```python id="a1v0z2"
result = client.auto().llm(...)
```

Core fields:

* `actions`
* `trace`
* `metrics`
* `used_fallback`
* `explanation`
* `scope`
* `scope_data`
* `final_answer` (optional, often None)
* `output` (optional, often None)

---

## Field Breakdown

### actions

List of control interventions selected by Aegis.

```python id="9h2k1d"
print(result.actions)
```

Example:

```json id="l3x8y1"
[
  {
    "type": "reduce_variability",
    "intensity": "medium",
    "label": "Reduce output variability"
  }
]
```

---

### trace

A list of decision events describing how Aegis evaluated the system.

```python id="7s4m0p"
print(result.trace)
```

Important:

* always a **list**
* each entry represents a decision step

Example:

```json id="z8q1v4"
[
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
]
```

---

### metrics

Runtime signals describing the control decision.

```python id="k2p8n1"
print(result.metrics)
```

Example:

```json id="m4t9w6"
{
  "action_count": 2
}
```

---

### used_fallback

Indicates whether fallback behavior was triggered.

```python id="p5n2x0"
print(result.used_fallback)
```

Expected:

* `false` for normal operation

---

### explanation

Human-readable summary of the decision.

```python id="w1v9e7"
print(result.explanation)
```

Example:

```text
Selected because it achieved the highest overall score.
```

---

### scope

Indicates which control scope was used:

* `llm`
* `rag`
* `step`

```python id="t8j3r5"
print(result.scope)
```

---

### scope_data

Scope-specific runtime data used to apply control.

```python id="y2c6d9"
print(result.scope_data)
```

Common contents:

* `runtime_config`
* `controlled_prompt`
* scope-specific debug info

---

## LLM Scope Data

Typical fields:

```python id="g5r1n8"
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
```

Example:

```json id="q9u4c2"
{
  "runtime_config": {
    "temperature": 0.2,
    "top_p": 0.8
  },
  "controlled_prompt": "You are a helpful assistant..."
}
```

---

## RAG Scope Data

May include:

* retrieval_expansion_triggered
* final_chunks
* removed_chunks
* before_after_metrics

```python id="v6n0b3"
print(result.scope_data)
```

---

## Step Scope Data

Includes:

* original step input
* runtime decisions
* coordination adjustments

```python id="b3k7s1"
print(result.scope_data)
```

---

## final_answer and output

These fields may be:

```python id="n8d2x5"
print(result.final_answer)
print(result.output)
```

Important:

* often `None`
* not guaranteed to be populated

---

## Why They May Be Empty

Aegis is a control layer.

It does not:

* execute your model
* generate final outputs

It provides the **instructions and configuration** for your system to execute.

---

## Correct Usage Pattern

```python id="f1h8p6"
result = client.auto().llm(...)

runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")

# Use these in your model call
```

---

## Debugging Helpers

```python id="d7v4m2"
print(result.debug_summary())
print(result.to_dict())
```

Recommended inspection order:

```python id="c5r9z8"
print(result.actions)
print(result.explanation)
print(result.trace)
print(result.scope_data)
```

---

## Common Mistakes

### Expecting final output

```python id="x4n8j2"
# ❌ incorrect
print(result.final_answer)
```

### Ignoring scope_data

```python id="u9k3p7"
# ❌ incomplete usage
result = client.auto().llm(...)
```

```python id="r2v6q1"
# ✅ correct
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
```

---

## Summary

`AegisResult` gives you:

* control decisions
* runtime configuration
* observability
* structured trace

You use it to:

* stabilize your system
* guide execution
* improve consistency

It is not the final execution output.
