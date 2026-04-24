# Result Model

## Overview

Every scope call returns an `AegisResult`.

This object is primarily control and observability output, not a downstream model answer.

---

## Core Fields

Typical fields include:

* `actions`
* `trace`
* `metrics`
* `used_fallback`
* `explanation`
* `scope`
* `scope_data`
* `output` (optional)
* `final_answer` (optional)

---

## Scope Field

`scope` identifies the applied control boundary:

* `llm`
* `rag`
* `step`
* `context`
* `agent`

---

## scope_data

`scope_data` is scope-specific structured payload returned by the backend.

### LLM Scope Data

Often includes controlled generation settings, for example:

* `runtime_config`
* `controlled_prompt`

### RAG Scope Data

Often includes retrieval-control information, for example:

* controlled/selected retrieved context
* before/after quality metrics
* retrieval decision metadata

### Step Scope Data

Often includes step-level control details, for example:

* step runtime adjustments
* action guidance for one workflow boundary

### Context Scope Data

Likely fields include:

* `cleaned_messages`
* `cleaned_tool_results`
* `carry_forward_context`
* `structured_carry_forward_context`
* `internal_controls.context`

### Agent Scope Data

Likely fields include:

* `agent_runtime`
* `steps`
* `tool_calls`
* `stop_reason`
* `carry_forward_context`
* `structured_carry_forward_context`

---

## output and final_answer

`output` and `final_answer` are optional.

General behavior:

* often `None` for pure control responses
* `context` and `agent` may populate `output` with cleaned context or run summary style data

Even when populated, these fields should be treated as control-surface output, not a substitute for your downstream model/tool execution.

---

## Usage Pattern

```python
result = client.auto().llm(...)

print(result.actions)
print(result.explanation)
print(result.trace)
print(result.scope_data)
```

Use returned controls to guide your own runtime execution.

---

## Principle

`AegisResult` is a control/observability contract. It is not the final answer contract for your application runtime.
