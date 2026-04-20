# Roadmap

## Overview

Aegis is evolving from a **runtime stabilization layer** into a broader **AI system control layer**.

This document outlines:

* current capabilities
* near-term expansion
* long-term direction

---

## Current State

### Stable SDK Surface

* `llm` — model call stabilization
* `rag` — retrieval + generation stabilization
* `step` — workflow / coordination stabilization

---

### Backend Reality

* primary execution via `/v1/stabilize`
* legacy support via `/v1/plan`
* scope-first interface handled by SDK

---

### Proven Capabilities

* reduce model calls
* eliminate retries and replans
* stabilize agent workflows
* improve consistency without changing models

---

## Near-Term Direction

### 1. Native Scope Endpoints

Goal:

```id="future_routes"
/v1/auto/llm
/v1/auto/rag
/v1/auto/step
```

Purpose:

* align backend with SDK
* remove fallback dependency
* improve clarity and performance

---

### 2. Enhanced Scope Intelligence

Each scope becomes more specialized:

* `llm` → deeper generation control
* `rag` → advanced retrieval shaping
* `step` → stronger coordination logic

---

### 3. Improved Observability

Planned additions:

* richer `trace` structure
* standardized metrics
* better debugging outputs

---

## Mid-Term Direction

### 1. Workflow Scope

New scope:

```python id="workflow_scope"
client.auto().workflow(...)
```

Purpose:

* stabilize multi-step pipelines
* coordinate across steps
* manage execution flow

---

### 2. System Scope

New scope:

```python id="system_scope"
client.auto().system(...)
```

Purpose:

* full system-level control
* cross-component coordination
* global stabilization

---

### 3. Adaptive Control

Future systems may:

* adjust behavior dynamically
* learn optimal intervention patterns
* refine control strategies over time

---

## Long-Term Vision

Aegis becomes:

→ a **universal control layer for AI systems**

---

### Capabilities

* control any AI pipeline
* stabilize multi-agent ecosystems
* manage system-level behavior
* provide structured execution guarantees

---

### Key Evolution

From:

* stabilizing individual calls

To:

* controlling entire systems

---

## Design Direction

### 1. Maintain Simplicity

Even as capabilities expand:

* SDK remains minimal
* interface remains scope-based

---

### 2. Preserve Drop-In Integration

Aegis should always:

* wrap existing systems
* avoid requiring rewrites

---

### 3. Keep Model-Agnostic

No dependency on:

* specific models
* specific frameworks

---

### 4. Expand Without Breaking

* backward compatibility maintained
* SDK remains stable
* backend evolves behind abstraction

---

## What Will NOT Change

* runtime-first philosophy
* minimal intervention approach
* observability as a core feature
* system-level focus over model-level tuning

---

## What to Expect Next

Short-term:

* backend alignment with SDK
* stronger scope behavior

Mid-term:

* workflow-level control
* expanded observability

Long-term:

* full system orchestration

---

## Final Takeaway

Aegis is moving toward:

→ controlling **how AI systems behave**, not just what they output
