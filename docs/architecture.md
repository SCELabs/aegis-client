# Architecture

## Overview

Aegis is a **runtime control layer** for AI systems.

It stabilizes behavior at execution time by observing system outputs and applying minimal corrective actions.

Aegis consists of:

1. **Client SDK** (this repo)
2. **Backend Control Layer** (Aegis API)
3. **Your Runtime System** (LLMs, RAG, agents, workflows)

---

## Stack Position

Aegis sits **between your system and execution**:

```id="stack_diagram"
/Your App / Agent / Pipeline
            ↓
          Aegis
            ↓
     LLM / RAG / Tools
```

It does not replace your system.
It stabilizes how your system behaves.

---

## Client SDK

The client provides a **scope-first interface**:

```python id="sdk_usage"
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

Responsibilities:

* define scope-based calls
* construct request payloads
* send requests to backend
* normalize responses into `AegisResult`

The client **does not implement control logic**.

---

## Backend Control Layer

The backend is the **execution engine** of Aegis.

Responsibilities:

* interpret instability signals
* map symptoms → system state
* select corrective actions
* generate runtime control outputs

### Verified public routes

```id="backend_routes"
/v1/stabilize
/v1/plan
```

* `/v1/stabilize` → primary runtime stabilization endpoint
* `/v1/plan` → legacy / advanced planning interface

---

## Important: Scope Interface vs Backend Reality

The SDK exposes:

```id="sdk_scopes"
llm
rag
step
```

However, these are **not currently separate backend endpoints**.

Instead:

* the SDK **maps all scopes to the backend**
* execution is handled by `/v1/stabilize`

---

## Request Flow (Actual Behavior)

```id="flow_real"
client.auto().llm(...)
        ↓
client builds scope payload
        ↓
POST /v1/auto/llm   (attempt)
        ↓
fallback → POST /v1/stabilize
        ↓
backend executes stabilization
        ↓
response mapped to AegisResult
```

The `/v1/auto/<scope>` routes are **not guaranteed to exist**.

The client automatically falls back to `/v1/stabilize`.

---

## Control Model

Aegis operates using three inputs:

### Symptoms

Describe instability:

* `"inconsistent_outputs"`
* `"unstable_workflow"`
* `"agents_disagree"`
* `"retrieval_drift"`

---

### Severity

Defines intervention strength:

* `"low"`
* `"medium"`
* `"high"`

---

### Scope

Defines where control is applied:

* `llm` → model call
* `rag` → retrieval + generation
* `step` → workflow / coordination

Scope is a **client-side abstraction**, not a backend route boundary.

---

## Backend Execution Model

At `/v1/stabilize`, the backend:

1. Converts input → internal system state
2. Evaluates structural instability
3. Selects corrective plan
4. Maps plan → actions
5. Generates runtime controls

The response includes:

* `actions`
* `runtime_config`
* `confidence`
* `summary`
* optional prompt modifications

---

## Result Normalization

The client converts backend responses into:

```id="result_model"
AegisResult
```

Which exposes:

* `final_answer`
* `actions`
* `trace`
* `metrics`
* `scope_data`
* `used_fallback`
* `explanation`

---

## Observability Layer

Aegis is fully inspectable.

You can analyze:

```python id="debug_tools"
result.actions
result.trace
result.metrics
result.debug_summary()
```

This allows:

* debugging instability
* understanding decisions
* integrating adaptive control logic

---

## Compatibility Model

Aegis is designed for **forward compatibility**.

### SDK (stable interface)

```id="sdk_stable"
client.auto().<scope>()
```

### Backend (current reality)

```id="backend_current"
/v1/stabilize
```

The SDK abstracts backend differences so integrations remain stable.

---

## Key Design Constraints

### 1. No System Redesign

Aegis wraps your existing system.

---

### 2. Minimal Intervention

Only the smallest necessary actions are applied.

---

### 3. Runtime Only

No training, fine-tuning, or persistent system changes.

---

### 4. Model-Agnostic

Works with:

* OpenAI
* local LLMs
* any framework

---

## What Aegis Is Not

Aegis is not:

* a model
* a replacement for your pipeline
* a workflow engine

---

## What Aegis Is

Aegis is:

→ a **runtime stabilization layer for AI systems**

---

## Future Direction

The architecture is evolving toward:

* true scope-native backend endpoints
* multi-step workflow control
* full system-level coordination

But today, the stable surface is:

* `llm`
* `rag`
* `step`

mapped through `/v1/stabilize`.

---

## Summary

Aegis works by:

* observing runtime instability
* applying targeted corrections
* returning structured outputs

All without changing your system.