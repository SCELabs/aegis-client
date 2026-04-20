# Aegis Client

**Runtime stabilization for AI systems.**

Aegis sits on top of your AI pipeline and ensures consistent, structured, and reliable behavior at runtime — without changing your models.

---

## Why Aegis

Modern AI systems fail in subtle but costly ways:

* inconsistent outputs across identical inputs
* unstable multi-step reasoning
* retrieval drift in RAG systems
* fragile agent execution loops

Aegis solves this by applying **runtime control and stabilization**, not retraining, prompt hacks, or model swaps.

---

## Core Idea

Instead of trying to make models *smarter*, Aegis makes systems **more stable, predictable, and efficient**.

```python
from aegis import AegisClient

client = AegisClient(api_key="YOUR_API_KEY")

result = client.auto().llm(...)
```

Aegis will:

* detect instability signals
* apply minimal corrective actions
* return structured results

---

## Installation

```bash
pip install scelabs-aegis
```

---

## You can use Aegis via a hosted API or run your own backend.

---

## 🔹 Get an API Key

### Hosted (recommended)

```bash
curl -X POST https://aegis-backend-production-4b47.up.railway.app/v1/onboard \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

---

### Local (optional)

```bash
curl -X POST http://localhost:8000/v1/onboard \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

This returns:

* `api_key`
* `base_url`
* example usage

---

## 🔹 Set Environment

### Hosted

```bash
export AEGIS_API_KEY=your_key_here
export AEGIS_BASE_URL=https://your-backend-url
```

---

### Local

```bash
export AEGIS_API_KEY=your_key_here
export AEGIS_BASE_URL=http://localhost:8000
```

---

## 🔹 First Call

```python
from aegis import AegisClient, AegisConfig

client = AegisClient(
    config=AegisConfig(mode="balanced"),
)

result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input="Explain recursion simply.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.final_answer)
print(result.actions)
```

---

## SDK Surface

Aegis uses a **scope-first runtime interface**:

```python
client.auto().llm(...)
client.auto().rag(...)
client.auto().step(...)
```

### Scopes

#### LLM — stabilize model calls

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

#### RAG — stabilize retrieval + generation

```python
result = client.auto().rag(
    query="What changed in the policy?",
    retrieved_context=["Policy updated last week."],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

---

#### Step — stabilize workflows / agents

```python
result = client.auto().step(
    step_name="coordinator",
    step_input={"task": "resolve ticket"},
    symptoms=["unstable_workflow"],
    severity="medium",
)
```

---

## AegisResult

Every call returns a structured result:

```python
result = client.auto().llm(...)
```

### Key fields

* `final_answer` — stabilized output
* `actions` — interventions applied
* `trace` — execution trace
* `metrics` — performance signals
* `used_fallback` — fallback indicator
* `scope_data` — scope-specific debug info
* `explanation` — reasoning summary

### Debugging

```python
print(result.debug_summary())
print(result.to_dict())
```

---

## Configuration

```python
from aegis import AegisConfig

config = AegisConfig(
    mode="balanced",              # light | balanced | aggressive
    max_interventions=3,
    allow_retries=True,
    allow_retrieval_expansion=True,
    allow_context_reduction=True,
    allow_prompt_shaping=True,
    fallback="baseline",          # safe | baseline | strict
    explain=False,
    emit_trace=False,
    policy=None,
    timeout_ms=30000,
)
```

---

## How It Works (High-Level)

1. You describe instability (`symptoms`, `severity`)
2. Aegis evaluates runtime behavior
3. It applies minimal corrections
4. Returns structured output (`AegisResult`)

---

## Backend Compatibility

The SDK is **scope-first**, but backend execution currently uses:

```text
/v1/stabilize
```

The client may attempt:

```text
/v1/auto/<scope>
```

If unavailable, it automatically falls back to `/v1/stabilize`.

---

## Design Principles

* runtime control over training
* minimal intervention
* observable behavior (trace + actions)
* model-agnostic integration

---

## Documentation

Full docs are available in `/docs`:

* architecture
* SDK usage
* scopes
* result model
* integration patterns
* demos
* migration guide

---

## Status

* Stable SDK
* Active scopes: `llm`, `rag`, `step`
* Backend evolving toward scope-native endpoints

---

## License

MIT
