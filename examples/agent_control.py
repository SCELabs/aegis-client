from aegis import AegisClient


client = AegisClient()

result = client.auto().agent(
    goal="Resolve support ticket T-42 with a safe customer response.",
    steps=[
        {"name": "triage", "input": {"ticket_id": "T-42", "priority": "high"}},
        {"name": "draft_response", "input": {"channel": "email", "tone": "calm"}},
    ],
    tools=[],
    max_steps=4,
)

print(result.debug_summary())

scope_data = result.scope_data or {}
step_trace = scope_data.get("steps") or scope_data.get("step_trace") or []
tool_calls = scope_data.get("tool_calls") or []
stop_reason = scope_data.get("stop_reason")

print("step_count:", len(step_trace))
print("tool_call_count:", len(tool_calls))
print("stop_reason:", stop_reason)
