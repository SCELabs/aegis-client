# Architecture

## Overview

Aegis is a **runtime control layer** for AI systems.

It stabilizes behavior at execution time by observing system inputs and returning structured control decisions that guide how your system should operate.

Aegis consists of three parts:

1. **Client SDK** (this repo)
2. **Backend Control Layer** (Aegis API)
3. **Your Runtime System** (LLMs, RAG, agents, workflows)

---

## Stack Position

Aegis sits **between your system logic and execution**:

```
Your App / Agent / Pipeline
            ↓
          Aegis
            ↓
     LLM / RAG / Tools
```

Aegis does not replace your system.
It stabilizes how your system behaves at runtime.

---

## Core Principle

Aegis separates:

* **Decision layer** → what should happen
* **Execution layer** → your model, tools, or system

Aegis only operates in the decision layer.

---

## Client SDK

The client exposes a **scope-first interface**:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

Responsibilities:

* construct scope-based requests
* send requests to the backend
* normalize responses into `AegisResult`

The client does **not** implement control logic.

---

## Backend Control Layer

The backend is the **control engine** of Aegis.

Responsibilities:

* interpret instability signals
* evaluate system state
* select corrective actions
* produce runtime control outputs

### Public API (current)

```
POST /v1/auto/llm
POST /v1/auto/rag
POST /v1/auto/step
```

These are first-class endpoints.
There is no longer a dependency on `/v1/stabilize`.

---

## Request Flow

```
client.auto().llm(...)
        ↓
build scope request
        ↓
POST /v1/auto/llm
        ↓
backend evaluates state
        ↓
returns control decisions
        ↓
client maps to AegisResult
```

There is no fallback layer in the current architecture.

---

## Control Model

Aegis operates on three core inputs:

### Symptoms

Describe instability in the system:

* "inconsistent_outputs"
* "unstable_workflow"
* "retrieval_drift"
* "agents_disagree"

---

### Severity

Defines intervention strength:

* "low"
* "medium"
* "high"

---

### Scope

Defines where control is applied:

* `llm` → model call
* `rag` → retrieval + generation
* `step` → workflow / coordination

Scope is now both:

* a client abstraction
* a backend route boundary

---

## Backend Execution Model

For each scope route, the backend:

1. converts input into internal state
2. evaluates system stability
3. selects a corrective plan
4. maps plan → actions
5. generates runtime controls

The response includes:

* actions
* explanation
* runtime_config
* controlled_prompt (if applicable)
* trace
* metrics

---

## Result Model

All responses are normalized into:

```
AegisResult
```

Key fields:

* `actions`
* `trace` (list of decision events)
* `metrics`
* `used_fallback`
* `explanation`
* `scope`
* `scope_data`

### Important

Aegis returns **control outputs**, not model outputs.

That means:

* `final_answer` may be null
* `output` may be null

---

## Observability Layer

Aegis is fully inspectable.

You can analyze:

```python
result.actions
result.trace
result.metrics
result.scope_data
```

This allows:

* debugging instability
* understanding decisions
* building adaptive systems

---

## Execution Responsibility

Aegis does not execute:

* LLM calls
* tool calls
* workflows

Your system executes using:

* `scope_data.runtime_config`
* `scope_data.controlled_prompt`
* returned actions

---

## Design Constraints

### 1. No System Replacement

Aegis wraps your system, it does not replace it.

---

### 2. Minimal Intervention

Only the smallest necessary corrections are applied.

---

### 3. Runtime Only

No training, fine-tuning, or persistent modification.

---

### 4. Model-Agnostic

Works with:

* OpenAI
* local models
* any framework

---

## What Aegis Is Not

Aegis is not:

* a model
* a workflow engine
* a replacement for your system

---

## What Aegis Is

Aegis is:

→ a **runtime control layer for AI systems**

---

## Evolution Direction

The architecture now supports:

* scope-native backend endpoints
* structured control outputs
* observable decision traces

Future directions include:

* multi-step workflow control
* deeper system coordination
* richer trace analysis

---

## Summary

Aegis works by:

* observing instability
* selecting minimal corrections
* returning structured control decisions

All while keeping your system unchanged.
