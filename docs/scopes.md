# Scopes

## Overview

Scopes define where Aegis applies runtime control.

All scopes use the same SDK shape:

```python
client.auto().<scope>(...)
```

Available scopes: `llm`, `rag`, `step`, `context`, `agent`.

For exact request payload fields/defaults, see [Request Shapes](./request-shapes.md).

---

## LLM Scope

### What it is

Control for direct model-call behavior.

### When to use

* inconsistent outputs
* formatting drift
* prompt instability

### Minimal SDK example

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

### What Aegis controls

* generation guardrails and shaping inputs
* runtime config hints (for example temperature/top_p policy)
* retry/escalation control actions where supported

### When not to use

* retrieval-quality problems
* multi-step workflow loops

---

## RAG Scope

### What it is

Control for retrieved evidence and grounded generation behavior.

### When to use

* weak or noisy retrieval sets
* grounding drift
* evidence coverage gaps

### Minimal SDK example

```python
result = client.auto().rag(
    query="What changed in refund policy?",
    retrieved_context=["Policy v3", "Refund window is 14 days"],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

### What Aegis controls

* retrieval-set quality checks
* context pruning and prioritization
* evidence-balancing decisions

### When not to use

* direct non-RAG generation tasks
* whole workflow orchestration

---

## Step Scope

### What it is

Control for one workflow/action boundary.

### When to use

* a single unstable action in a larger flow
* one coordinator/tool step needs runtime guardrails

### Minimal SDK example

```python
result = client.auto().step(
    step_name="ticket_triage",
    step_input={"ticket_id": "T-42"},
    symptoms=["routing_instability"],
    severity="high",
)
```

### What Aegis controls

* per-step retries/adjustments
* action-level stability decisions
* step-level traceable interventions

### When not to use

* broader multi-step loops
* message/tool-result state cleanup

---

## Context Scope

### What it is

Control for message and tool-result information state.

### When to use

* conversation state is noisy or stale
* tool results are verbose or mixed quality
* you need a clean carry-forward packet

### Minimal SDK example

```python
result = client.auto().context(
    objective="Prepare context for the next response.",
    messages=[{"role": "user", "content": "Summarize blockers"}],
    tool_results=[{"tool": "ticket_lookup", "ok": True, "data": {"id": "T-42"}}],
)
```

### What Aegis controls

* prioritizes relevant messages and tool results
* drops low-value/noisy context
* preserves protected context where supported
* returns cleaned messages/tool results, carry-forward context, trace/actions

### When not to use

* direct model-call tuning without context cleanup needs
* full workflow loop orchestration

---

## Agent Scope

### What it is

Control for multi-step workflow-loop behavior.

### When to use

* multi-step agent runs need runtime stabilization
* tool integration and carry-forward state need oversight
* stop/retry/escalation decisions should be controlled

### Minimal SDK example

```python
result = client.auto().agent(
    goal="Resolve support ticket safely.",
    steps=[
        {"name": "triage", "input": {"ticket_id": "T-42"}},
        {"name": "draft_response", "input": {"channel": "email"}},
    ],
    tools=[],
    max_steps=4,
)
```

### What Aegis controls

* loop-level runtime decisions across steps
* step progression with memory/carry-forward context
* tool-result integration
* stop/retry/escalation decisions where supported

### When not to use

* single-step calls where `step` is enough
* systems that need Aegis to execute tools directly

Aegis agent scope does not replace existing agent frameworks. It adds runtime control on top of them.

Useful patterns include agentic RAG, support workflows, coding agents, and research workflows.

---

## Choosing the Right Scope

| Situation                           | Scope     |
| ----------------------------------- | --------- |
| Direct model generation             | `llm`     |
| Retrieved evidence/context quality  | `rag`     |
| One workflow action                 | `step`    |
| Cleaning/prioritizing state         | `context` |
| Multi-step loop/workflow            | `agent`   |

---

## Endpoints

Each scope maps to a public route:

* `POST /v1/auto/llm`
* `POST /v1/auto/rag`
* `POST /v1/auto/step`
* `POST /v1/auto/context`
* `POST /v1/auto/agent`
