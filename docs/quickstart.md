# Quick Start

## Overview

This guide gets you from zero to a working Aegis integration in under 5 minutes.

---

## Step 1: Install

```bash
pip install scelabs-aegis
```

---

## Step 2: Get API Key

```bash
curl -X POST https://aegis-backend-production-4b47.up.railway.app/v1/onboard \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com"}'
```

Copy your `api_key`.

---

## Step 3: Set Environment

```bash
export AEGIS_API_KEY=your_key_here
export AEGIS_BASE_URL=https://aegis-backend-production-4b47.up.railway.app
```

---

## Step 4: Make First Call

```python
from aegis import AegisClient

client = AegisClient()

result = client.auto().llm(
    base_prompt="You are a helpful assistant.",
    input={"user_query": "Explain black holes simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.actions)
print(result.explanation)
```

---

## Step 5: Apply Control

```python
runtime_config = result.scope_data.get("runtime_config", {})
controlled_prompt = result.scope_data.get("controlled_prompt")

response = model.generate(
    controlled_prompt,
    temperature=runtime_config.get("temperature", 0.7),
)
```

---

## What Just Happened

Aegis:

* analyzed instability
* selected corrective actions
* returned runtime controls

Your system:

* executed using those controls

---

## That’s It

You now have:

* stabilized outputs
* structured control
* observable decisions

---

## Next Steps

* read `architecture.md`
* explore `scopes.md`
* inspect `result_model.md`
* apply Aegis to your workflow or agent system

---

## Summary

Aegis does not replace your model.

It stabilizes how your system behaves at runtime.

That’s the entire idea.
