<p align="center">
  <a href="https://github.com/SCELabs/aegis-client">
    <img src="assets/aegis_logo.png" width="260" alt="Aegis" />
  </a>
</p>

<h2 align="center">
  <strong>Runtime control for AI systems.</strong>
</h2>

Aegis sits on top of your AI pipeline and returns structured control decisions that stabilize behavior at runtime without replacing your model, agent, or retrieval system.

---

## Why Aegis

Modern AI systems often fail in subtle but costly ways:

* inconsistent outputs across similar inputs
* unstable multi-step reasoning
* retrieval drift in RAG systems
* fragile workflow and agent execution

Aegis addresses these problems with **runtime control**, not retraining, fine-tuning, or model swapping.

---

## Core Idea

Aegis is a **control layer**, not an execution layer.

```python
from aegis import AegisClient

client = AegisClient(api_key="YOUR_API_KEY")

result = client.auto().llm(...)
```

Aegis will:

* detect instability signals
* select minimal corrective actions
* return runtime controls and observability data

Aegis does **not** execute the downstream LLM call for you.

---

## Installation

```bash
pip install scelabs-aegis
```

---

## Get an API Key

```bash
curl -X POST https://aegis-backend-production-4b47.up.railway.app/v1/onboard \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

This returns:

* `api_key`
* `auto_llm_url`
* `auto_rag_url`
* `auto_step_url`
* example usage

---

## Set Environment

```bash
export AEGIS_API_KEY=your_key_here
export AEGIS_BASE_URL=https://aegis-backend-production-4b47.up.railway.app
```

---

## First Call

```python
from aegis import AegisClient, AegisConfig

client = AegisClient(
    config=AegisConfig(mode="balanced"),
)

result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input={"user_query": "Explain recursion simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.actions)
print(result.explanation)
print(result.scope_data)
```

---

## Scope-First API

Aegis uses a **scope-first runtime interface**:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

These calls map to first-class public backend routes:

* POST /v1/auto/llm
* POST /v1/auto/rag
* POST /v1/auto/step

---

## Scopes

### LLM

Use `llm` when you need stabilization around a direct model call.

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input={"user_query": "Explain recursion simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

### RAG

Use `rag` when instability appears in retrieval plus generation.

```python
result = client.auto().rag(
    query="What changed in the policy?",
    retrieved_context=[
        "Policy updated last week.",
        "Refund window reduced to 14 days."
    ],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

### What changed in RAG

Aegis no longer treats retrieval as a fixed input.

It **controls retrieval behavior at runtime**.

The RAG scope now:

* enforces **typed evidence coverage** (source, test, support)
* applies **relevant-file protection** (never drops critical context)
* performs **selective expansion** (not always-on)
* removes noise without losing required files
* uses **staged retrieval** only when ambiguity or gaps are detected
* applies **guided retrieval (intent + plan)** only when justified

This is not just ranking or filtering.

Aegis:

* evaluates the retrieved set
* diagnoses issues (missing support, ambiguity, distractors)
* applies minimal corrective actions
* returns a controlled context for downstream use

---

### How RAG control works

At runtime:

1. You pass query + retrieved context

2. Aegis evaluates:

   * missing required evidence
   * role imbalance (source/test/support)
   * distractor pressure
   * ambiguity / multi-branch cases

3. It decides whether to:

   * keep as-is
   * prune noise
   * expand retrieval
   * run a staged second pass
   * guide retrieval when needed

4. It enforces **relevant-file protection before final selection**

Everything is gated and minimal.

No always-on expansion. No blind pruning.

---

### Works with Agentic RAG

Yes.

Aegis sits above your agent system and stabilizes retrieval behavior.

It can:

* prevent agents from drifting due to poor context
* enforce evidence requirements before execution
* reduce retries and replans
* stabilize multi-step retrieval chains

Aegis does not replace your agents — it makes them more reliable.

---

### Step

Use `step` when you need stabilization for a workflow or agent step.

```python
result = client.auto().step(
    step_name="coordinator",
    step_input={"task": "resolve ticket"},
    symptoms=["unstable_workflow"],
    severity="medium",
)
```

---

## What Aegis Returns

Every call returns an `AegisResult`.

```python
result = client.auto().llm(...)
```

### Key fields

* `actions` — interventions Aegis selected
* `trace` — structured control trace
* `metrics` — runtime signals
* `used_fallback` — whether fallback behavior was used
* `explanation` — concise rationale
* `scope` — llm, rag, or step
* `scope_data` — scope-specific runtime data

---

### RAG Observability (new)

RAG responses now include richer runtime signals:

Inside `scope_data`:

* `public_rag_runtime` — high-level runtime info
* `retrieval_intent` — if guided retrieval was used
* `retrieval_plan` — structured retrieval guidance (when triggered)
* `initial_retrieved_chunks` — stage 1 candidates
* `stage2_retrieved_chunks` — staged retrieval results (if used)
* `before_after_metrics` — context quality changes

Inside `trace`:

* `decision.policy_path` includes:

  * expansion score / threshold
  * staged retrieval activation
  * intent / plan activation

* `changes` includes:

  * protected chunk IDs
  * relevant-file protection indicators

These are optional but useful for debugging pipeline behavior.

---

## Typical RAG Integration Pattern

```python
result = client.auto().rag(
    query="Why is retry failing?",
    retrieved_context=raw_context,
    symptoms=["retrieval_drift"],
    severity="medium",
)

controlled_context = result.scope_data.get("retrieved_context")
trace = result.trace

print(controlled_context)
print(result.actions)
print(trace)
```

You apply the returned controlled context in your downstream system.

---

## Example Result Shape

```json
{
  "actions": [...],
  "trace": [...],
  "scope": "rag",
  "scope_data": {
    "retrieved_context": [...],
    "public_rag_runtime": {...},
    "before_after_metrics": {...}
  }
}
```

---

## Debugging

```python
print(result.debug_summary())
print(result.to_dict())
```

Useful fields:

```python
print(result.actions)
print(result.explanation)
print(result.trace)
print(result.scope_data)
```

---

## Configuration

```python
from aegis import AegisConfig

config = AegisConfig(
    mode="balanced",
    max_interventions=3,
    allow_retries=True,
    allow_retrieval_expansion=True,
    allow_context_reduction=True,
    allow_prompt_shaping=True,
    fallback="baseline",
    explain=False,
    emit_trace=False,
    policy=None,
    timeout_ms=30000,
)
```

---

## Required Request Inputs

For scope calls, provide:

* `symptoms` — required, non-empty list
* `severity` — required, one of: low, medium, high

---

## Design Principles

* runtime control over training
* minimal intervention
* observable behavior through trace and actions
* model-agnostic integration

---

## Documentation

Docs in `/docs` explain:

* architecture
* scopes
* result behavior
* integration guidance
* migration and usage patterns

---

## Status

* Stable SDK surface
* Active scopes: llm, rag, step
* RAG scope now uses runtime-controlled retrieval behavior

---

## License

MIT
