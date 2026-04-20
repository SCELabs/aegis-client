# Integration Patterns

## Overview

Aegis is designed to be **inserted into existing systems**, not replace them.

The core principle:

> **Do not redesign your system. Wrap it.**

---

## Pattern 1: Direct LLM Calls

### Before

```python id="before_llm"
response = model.invoke(prompt)
```

---

### After

```python id="after_llm"
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input=prompt,
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

response = result.final_answer
```

---

### When to use

* unstable outputs
* formatting inconsistencies
* reasoning drift

---

## Pattern 2: RAG Pipelines

### Before

```python id="before_rag"
documents = retriever(query)
response = model.invoke(documents)
```

---

### After

```python id="after_rag"
result = client.auto().rag(
    query=query,
    retrieved_context=documents,
    symptoms=["retrieval_drift"],
    severity="medium",
)

response = result.final_answer
```

---

### When to use

* missing context
* irrelevant retrieval
* inconsistent answers

---

## Pattern 3: Agent Step Stabilization

### Before

```python id="before_step"
decision = executor.run(step_input)
```

---

### After

```python id="after_step"
result = client.auto().step(
    step_name="executor_step",
    step_input=step_input,
    symptoms=["unstable_workflow"],
    severity="medium",
)

decision = result.final_answer
```

---

### When to use

* retries / loops
* coordination issues
* multi-agent instability

---

## Pattern 4: Multi-Agent Systems

Aegis should be inserted at the **coordination boundary**.

### Example

```python id="multi_agent"
result = client.auto().step(
    step_name="coordinator",
    step_input={
        "agents": ["planner", "executor", "validator"],
        "history": history,
    },
    symptoms=[
        "agents_disagree",
        "excessive_replans",
        "duplicate_work",
    ],
    severity="medium",
)
```

---

### What happens

Aegis:

* reduces retries
* suppresses duplicate work
* stabilizes termination

---

## Pattern 5: Early Exit Optimization

Use Aegis to stop unnecessary execution.

```python id="early_exit_pattern"
result = client.auto().llm(...)

if not result.used_fallback:
    return result.final_answer
```

---

### Effect

* fewer model calls
* faster execution
* same correctness

---

## Pattern 6: Observability Integration

Use Aegis results for monitoring.

```python id="logging_pattern"
log = result.to_log_record()
logger.info(log)
```

---

### Track

* action count
* fallback usage
* confidence
* trace depth

---

## Pattern 7: Adaptive Systems

Use Aegis output to guide behavior.

```python id="adaptive_pattern"
if result.metrics.get("confidence", 1.0) < 0.7:
    run_validation_pass()
```

---

### Effect

* dynamic system control
* smarter pipelines
* improved reliability

---

## Where to Insert Aegis

| Layer              | Scope  |
| ------------------ | ------ |
| LLM call           | `llm`  |
| Retrieval pipeline | `rag`  |
| Agent step         | `step` |
| Coordinator loop   | `step` |

---

## Where NOT to Insert Aegis

### ❌ Inside every function

Avoid over-wrapping.

---

### ❌ Deep inside model logic

Aegis works at boundaries, not internals.

---

### ❌ Without symptoms

```python id="bad_integration"
# ❌ wrong
client.auto().llm(base_prompt="...")

# ✅ correct
client.auto().llm(
    base_prompt="...",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

---

## Best Practices

### Use smallest effective scope

* don’t over-scale
* target instability precisely

---

### Keep integration simple

Aegis should feel like a wrapper, not a rewrite.

---

### Inspect results

```python id="inspect_pattern"
result.actions
result.trace
```

---

### Start with real problems

Add Aegis where instability exists.

---

## Key Insight

Aegis works best when:

* a system already exists
* inefficiencies or instability are present
* behavior needs to be controlled, not rebuilt

---

## Summary

Integration is:

* minimal
* non-invasive
* scope-based

Aegis enhances your system without changing it.
