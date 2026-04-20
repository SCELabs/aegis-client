# Integration Patterns

## Overview

Aegis integrates as a **control layer** on top of your existing system.

You do not replace your model, RAG pipeline, or agent.

You insert Aegis at the **execution boundary**, receive control decisions, and apply them before running your system.

---

## Core Pattern

All integrations follow the same structure:

```python id="z9k2x1"
result = client.auto().<scope>(...)

# extract control
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")

# execute your system using control
```

---

## Pattern 1: LLM Integration

### Goal

Stabilize a direct model call.

---

### Example

```python id="x3p7n4"
result = client.auto().llm(
    base_prompt="You are a helpful assistant.",
    input={"user_query": "Explain black holes simply."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

runtime_config = result.scope_data.get("runtime_config", {})
controlled_prompt = result.scope_data.get("controlled_prompt")

response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": controlled_prompt}],
    temperature=runtime_config.get("temperature", 0.7),
    top_p=runtime_config.get("top_p", 1.0),
)

print(response)
```

---

### Where Aegis helps

* reduces randomness
* enforces consistency
* stabilizes prompt behavior

---

## Pattern 2: RAG Integration

### Goal

Stabilize retrieval + generation pipelines.

---

### Example

```python id="y5m1d8"
result = client.auto().rag(
    query=user_query,
    retrieved_context=chunks,
    symptoms=["retrieval_drift"],
    severity="medium",
)

scope_data = result.scope_data

# use updated context or metadata if provided
final_context = scope_data.get("final_chunks", chunks)

prompt = build_prompt(user_query, final_context)

response = model.generate(prompt)
```

---

### Where Aegis helps

* expands retrieval when needed
* removes irrelevant chunks
* improves grounding

---

## Pattern 3: Step / Agent Integration

### Goal

Stabilize workflow or agent execution.

---

### Example

```python id="r8k6v2"
result = client.auto().step(
    step_name="planner",
    step_input={
        "task": "resolve support ticket",
        "history": state.history,
    },
    symptoms=["unstable_workflow"],
    severity="medium",
)

# inspect control actions
print(result.actions)

# adjust your workflow behavior accordingly
state = apply_controls(state, result)
```

---

### Where Aegis helps

* reduces loops
* prevents duplicate actions
* stabilizes coordination

---

## Pattern 4: Minimal Wrapper

### Goal

Drop Aegis into an existing system with minimal changes.

---

### Example

```python id="w2n4f9"
def stabilized_call(prompt):
    result = client.auto().llm(
        base_prompt=prompt,
        symptoms=["inconsistent_outputs"],
        severity="medium",
    )

    runtime_config = result.scope_data.get("runtime_config", {})
    controlled_prompt = result.scope_data.get("controlled_prompt", prompt)

    return model.generate(
        controlled_prompt,
        temperature=runtime_config.get("temperature", 0.7),
    )
```

---

## Pattern 5: Observability-First Integration

### Goal

Use Aegis for monitoring and debugging before enforcing changes.

---

### Example

```python id="v1c8j6"
result = client.auto().llm(
    base_prompt=prompt,
    symptoms=["inconsistent_outputs"],
    severity="low",
)

print(result.trace)
print(result.actions)
print(result.explanation)
```

---

### When to use

* diagnosing instability
* analyzing system behavior
* validating control strategies

---

## Where to Insert Aegis

Best insertion points:

* before LLM calls
* after retrieval, before generation
* at workflow step boundaries

Avoid:

* embedding inside every micro-step
* placing inside low-level utility functions

---

## Control vs Execution

Aegis provides:

* control decisions
* runtime configuration
* observability

Your system provides:

* execution
* model calls
* tool calls
* workflow state

---

## Common Mistakes

### Expecting Aegis to execute

```python id="m5k2x8"
# ❌ incorrect
result = client.auto().llm(...)
print(result.final_answer)
```

---

### Ignoring control outputs

```python id="n7p4v3"
# ❌ incomplete
result = client.auto().llm(...)
```

```python id="q2r8y1"
# ✅ correct
runtime_config = result.scope_data.get("runtime_config")
controlled_prompt = result.scope_data.get("controlled_prompt")
```

---

### Overusing high severity

```python id="k6j9p2"
# ❌ too aggressive
severity="high"
```

```python id="d3v7m1"
# ✅ better default
severity="medium"
```

---

## Integration Strategy

Start simple:

1. apply Aegis to one critical boundary
2. observe trace and actions
3. apply control outputs
4. expand gradually

---

## Summary

Aegis integrates by:

* sitting above execution
* returning control decisions
* letting your system execute

Use it to:

* stabilize behavior
* reduce variability
* improve reliability

without changing your core system.
