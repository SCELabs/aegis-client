# Result Model

## Overview

All Aegis calls return an **`AegisResult`**.

This is the primary interface for:

* consuming outputs
* understanding behavior
* debugging system instability

Aegis is designed to be **observable by default**.

---

## Basic Usage

```python id="result_basic"
result = client.auto().llm(...)

print(result.final_answer)
```

---

## Core Fields

### final_answer

The stabilized output of the system.

```python id="final_answer"
print(result.final_answer)
```

---

### output

The raw output returned by the backend.

```python id="raw_output"
print(result.output)
```

---

### actions

List of interventions Aegis applied.

```python id="actions"
print(result.actions)
```

Each action may include:

* `type`
* `intensity`
* `label`
* `description`

---

### trace

Detailed execution trace.

```python id="trace"
print(result.trace)
```

Represents:

* observations
* decisions
* applied changes

---

### metrics

Execution and behavior metrics.

```python id="metrics"
print(result.metrics)
```

May include:

* confidence
* performance indicators
* before/after comparisons

---

### explanation

Human-readable summary of what Aegis did.

```python id="explanation"
print(result.explanation)
```

---

### used_fallback

Indicates if fallback behavior was triggered.

```python id="fallback"
print(result.used_fallback)
```

---

### scope

Which scope was executed:

```python id="scope"
print(result.scope)  # llm / rag / step
```

---

### scope_data

Scope-specific debug information.

```python id="scope_data"
print(result.scope_data)
```

Examples:

* RAG: retrieval metrics
* Step: coordination signals
* LLM: generation hints

---

## Helper Methods

### debug_summary()

Quick summary of execution:

```python id="debug_summary"
print(result.debug_summary())
```

Example output:

```
scope=llm actions=2 trace_steps=5 used_fallback=no
```

---

### to_dict()

Convert result to dictionary:

```python id="to_dict"
data = result.to_dict()
```

---

### to_log_record()

Structured logging format:

```python id="to_log"
log = result.to_log_record()
```

---

## How to Use the Result

### 1. Use the output

```python id="use_output"
answer = result.final_answer
```

---

### 2. Inspect actions

```python id="inspect_actions"
for action in result.actions:
    print(action["type"])
```

---

### 3. Analyze trace

```python id="inspect_trace"
for step in result.trace:
    print(step)
```

---

### 4. Monitor behavior

```python id="monitor_metrics"
print(result.metrics)
```

---

## Common Patterns

### Early exit (agent systems)

```python id="early_exit"
if not result.used_fallback:
    return result.final_answer
```

---

### Adaptive control

```python id="adaptive"
if result.metrics.get("confidence", 1.0) < 0.7:
    # trigger additional validation
    pass
```

---

### Debugging instability

```python id="debugging"
print(result.explanation)
print(result.actions)
print(result.trace)
```

---

## Important Notes

### Not all fields are always populated

Depending on scope and backend response:

* some fields may be empty
* `scope_data` varies per use case

---

### `final_answer` vs `output`

* `final_answer` → cleaned / stable output
* `output` → raw backend result

---

### Observability is intentional

Aegis exposes internal decisions so you can:

* trust the system
* debug issues
* build adaptive logic

---

## What AegisResult Represents

It is not just a response.

It is:

→ a **structured record of system stabilization**

---

## Summary

`AegisResult` provides:

* output
* actions
* trace
* metrics
* explanation

Everything needed to:

* use results
* understand behavior
* improve systems
