# Agent Workflow with Aegis

This example shows Aegis controlling a simple multi-step loop.

## Example

```python
from aegis import AegisClient

client = AegisClient()

planned_steps = [
    {"name": "triage", "input": {"ticket_id": "T-42"}},
    {"name": "draft_response", "input": {"channel": "email"}},
]

result = client.auto().agent(
    goal="Resolve support ticket safely.",
    steps=planned_steps,
    tools=[],
    session_id="session-123",
    max_steps=4,
)

scope_data = result.scope_data or {}
executed_steps = scope_data.get("steps", [])
tool_calls = scope_data.get("tool_calls", [])
stop_reason = scope_data.get("stop_reason")

print("executed_steps:", executed_steps)
print("tool_calls:", tool_calls)
print("stop_reason:", stop_reason)
print(result.debug_summary())
```

Aegis controls loop/state decisions (progression, retry, stop/escalation). Your system still executes external tools and model calls.
