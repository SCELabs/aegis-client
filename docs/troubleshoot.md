# Troubleshooting

## Overview

This guide helps you diagnose common issues when integrating Aegis.

Aegis is a **control layer**, so most issues fall into one of three categories:

* request validation problems
* misunderstanding control vs execution
* integration misuse (not applying returned controls)

---

## Quick Debug Checklist

When something feels off, print:

```python id="d1q9w7"
print(result.scope)
print(result.actions)
print(result.trace)
print(result.explanation)
print(result.scope_data)
```

This gives you immediate visibility into what Aegis is doing.

---

## Issue: `final_answer` is None

### Cause

Aegis does not execute your model.

### Explanation

```python id="v7k2p3"
result = client.auto().llm(...)
print(result.final_answer)  # None
```

This is expected.

### Fix

Use `scope_data` to run your model:

```python id="c4m8t1"
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
```

---

## Issue: No visible change in behavior

### Cause

You are not applying control outputs.

### Incorrect

```python id="x2q7r9"
result = client.auto().llm(...)
# nothing else happens
```

### Correct

```python id="p6n3w5"
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")

response = model.generate(controlled_prompt)
```

---

## Issue: Request fails (422 error)

### Cause

Missing required fields.

### Required

* `symptoms` → non-empty list
* `severity` → low, medium, or high

### Example

```python id="n8k2t4"
result = client.auto().llm(
    base_prompt="You are helpful.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

## Issue: Request fails (401 error)

### Cause

Invalid or missing API key.

### Fix

Ensure:

```bash id="u9m3x8"
export AEGIS_API_KEY=your_key_here
```

Or pass explicitly:

```python id="b2k6p7"
client = AegisClient(api_key="your_key_here")
```

---

## Issue: `trace` is confusing

### Explanation

`trace` is a list of decision events.

```python id="r4w8p1"
event = result.trace[0]
print(event["decision"])
```

Each event contains:

* observation
* decision
* actions
* fallback
* changes
* upstream

---

## Issue: No actions returned

### Cause

System is already stable.

### Example

```json id="z5m1v2"
{
  "actions": [],
  "explanation": "System is stable."
}
```

### Meaning

No intervention was required.

---

## Issue: Too many actions

### Cause

Severity too high.

### Fix

```python id="q7p2n6"
severity="medium"  # instead of "high"
```

---

## Issue: Unexpected scope behavior

### Cause

Using wrong scope.

### Example

```python id="t3v9k2"
# ❌ wrong
client.auto().step(...)  # for simple prompt

# ✅ correct
client.auto().llm(...)
```

---

## Issue: RAG not improving

### Cause

Poor input context.

### Fix

Ensure:

* `retrieved_context` is relevant
* contains meaningful information
* not empty

---

## Issue: Step scope not affecting workflow

### Cause

You are not applying returned actions.

### Fix

```python id="w6p3k9"
result = client.auto().step(...)

apply_controls(state, result.actions)
```

---

## Issue: Backend returns empty scope_data

### Cause

Low-impact scenario or minimal intervention.

### Meaning

Aegis did not need to modify runtime behavior significantly.

---

## Issue: `used_fallback` is true

### Cause

Fallback behavior triggered.

### Expected

In normal operation:

```python id="g8k2v1"
result.used_fallback == False
```

If true:

* check backend deployment
* verify correct endpoint behavior

---

## Issue: Nothing changes in production

### Cause

You are not using the updated backend.

### Fix

* verify `AEGIS_BASE_URL`
* confirm deployment is current
* re-run onboarding if needed

---

## Debugging Strategy

### Step 1

Inspect trace:

```python id="y1m4q7"
print(result.trace)
```

---

### Step 2

Check actions:

```python id="d6k2n9"
print(result.actions)
```

---

### Step 3

Check scope_data:

```python id="u3p8v2"
print(result.scope_data)
```

---

### Step 4

Verify execution path

Ensure you are applying:

* controlled_prompt
* runtime_config

---

## When to Escalate

If all checks pass and behavior is still incorrect:

* log full `result.to_dict()`
* inspect upstream decision data
* verify system integration layer

---

## Summary

Most issues come from:

* expecting Aegis to execute
* ignoring control outputs
* missing required inputs

Fix these, and most integrations stabilize quickly.
