# Request Shapes

## Purpose

This guide shows exactly what developers send into each Aegis SDK scope and what to inspect in the returned `AegisResult`.

All calls follow:

```python
client.auto().<scope>(...)
```

---

## LLM: `client.auto().llm(...)`

### Request fields

* `base_prompt: str` (required)
* `input: Any` (optional)
* `symptoms: list[str]` (required)
* `severity: "low" | "medium" | "high"` (required)
* `metadata: dict` (optional)

### Minimal SDK example

```python
result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    input={"user_query": "Summarize the incident."},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)
```

### Best used when

* instability is in direct generation/model behavior
* you need runtime control before one model call

### Avoid using when

* instability is primarily retrieval/evidence quality
* you need multi-step loop coordination

### Key result fields to inspect

* `result.actions`
* `result.trace`
* `result.scope_data`

`input` can be a user query, task payload, or model-call state object.

---

## RAG: `client.auto().rag(...)`

### Request fields

* `query: str` (required)
* `retrieved_context: list[str]` (required)
* `symptoms: list[str]` (required)
* `severity: "low" | "medium" | "high"` (required)
* `metadata: dict` (optional)

### Minimal SDK example

```python
result = client.auto().rag(
    query="What changed in refund policy?",
    retrieved_context=[
        "Policy v3 was published last week.",
        "Refund window is now 14 days.",
    ],
    symptoms=["retrieval_drift"],
    severity="medium",
)
```

### Best used when

* called after retrieval and before generation
* you want Aegis to evaluate raw candidate chunks

### Avoid using when

* you are not using retrieval context
* the issue is purely a single model-call generation problem

### Key result fields to inspect

* `result.actions`
* `result.trace`
* `result.scope_data.get("retrieved_context")`
* `result.scope_data`

`metadata` can include richer chunk IDs/roles if supported by your backend.

---

## Step: `client.auto().step(...)`

### Request fields

* `step_name: str` (required)
* `step_input: Any` (required)
* `symptoms: list[str]` (required)
* `severity: "low" | "medium" | "high"` (required)
* `metadata: dict` (optional)

### Minimal SDK example

```python
result = client.auto().step(
    step_name="ticket_triage",
    step_input={"ticket_id": "T-42", "priority": "high"},
    symptoms=["routing_instability"],
    severity="high",
)
```

### Best used when

* you want control at one workflow/action boundary
* a single step needs runtime stabilization

### Avoid using when

* you only need information cleanup
* you want Aegis to coordinate a full multi-step loop

### Key result fields to inspect

* `result.actions`
* `result.trace`
* `result.scope_data`

`metadata` can include keys like `session_id`, `carry_forward_context`, and `tool_results`.

---

## Context: `client.auto().context(...)`

### Request fields

* `objective: str` (required)
* `messages: list[dict]` (optional, default `[]`)
* `tool_results: list[dict]` (optional, default `[]`)
* `constraints: list[str]` (optional, default `[]`)
* `symptoms: list[str]` (optional, default `["context_noise"]`)
* `severity: "low" | "medium" | "high"` (optional, default `"medium"`)
* `metadata: dict` (optional)

### Minimal SDK example

```python
result = client.auto().context(
    objective="Prepare context for the next response.",
    messages=[{"role": "user", "content": "Summarize blockers."}],
    tool_results=[{"id": "policy_lookup_1", "tool_name": "policy_lookup", "content": "..."},],
)
```

### Best used when

* you need to clean/prioritize information state
* message and tool-result context has noise or duplication

### Avoid using when

* the issue is generation behavior for one direct model call
* you need loop-level workflow coordination

### Key result fields to inspect

* `result.actions`
* `result.trace`
* `result.scope_data.get("cleaned_messages")`
* `result.scope_data.get("cleaned_tool_results")`
* `result.scope_data`

Message items should usually include `role` and `content`.
Tool results should include `content` and optional relevance/protected flags.

Example message item:

```json
{"role": "user", "content": "...", "protected": true, "relevance_score": 1.0}
```

Example tool result item:

```json
{"id": "policy_lookup_1", "tool_name": "policy_lookup", "content": "...", "relevance_score": 0.95, "protected": true}
```

---

## Agent: `client.auto().agent(...)`

### Request fields

* `goal: str` (required)
* `steps: list[dict]` (optional, default `[]`)
* `tools: list[dict]` (optional, default `[]`)
* `session_id: str` (optional)
* `max_steps: int` (optional)
* `symptoms: list[str]` (optional, default `["unstable_workflow"]`)
* `severity: "low" | "medium" | "high"` (optional, default `"medium"`)
* `metadata: dict` (optional)

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
    session_id="session-123",
)
```

### Best used when

* you need Aegis to control a multi-step workflow loop
* progression, retry, and stop/escalation decisions need stabilization

### Avoid using when

* you only need one action boundary (`step`)
* you only need context cleanup (`context`)

### Key result fields to inspect

* `result.actions`
* `result.trace`
* `result.scope_data.get("steps")`
* `result.scope_data.get("tool_calls")`
* `result.scope_data.get("stop_reason")`
* `result.scope_data`

`steps` should describe planned workflow steps.
`session_id` enables memory/carry-forward behavior.
Aegis controls loop/state decisions, not your actual external tools/models.

---

## Common metadata keys

* `session_id`
* `carry_forward_context`
* `tool_results`
* `retrieved_context_items`
* `required_chunk_ids`
* `acceptable_chunk_ids`
* `contradictory_chunk_ids`

---

## Result inspection cheat sheet

* `result.actions`
* `result.trace`
* `result.metrics`
* `result.scope_data`
* `result.debug_summary()`

---

## Choosing the smallest scope

* Use `context` when you only need information cleanup.
* Use `step` when you control one action.
* Use `agent` when you want Aegis to coordinate a loop.
* Use `rag` when the instability is retrieval/evidence.
* Use `llm` when the instability is generation/model behavior.
