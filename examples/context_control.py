from aegis import AegisClient


client = AegisClient()

result = client.auto().context(
    objective="Prepare a clean context packet for the next reply.",
    messages=[
        {"role": "user", "content": "Please summarize the current blockers."},
        {"role": "assistant", "content": "I can do that once I clean stale details."},
    ],
    tool_results=[
        {
            "tool": "ticket_lookup",
            "ok": True,
            "data": {"ticket_id": "T-42", "status": "open", "priority": "high"},
        }
    ],
    constraints=["Keep the summary brief", "Preserve ticket IDs"],
)

print(result.debug_summary())

scope_data = result.scope_data or {}
cleaned_messages = scope_data.get("cleaned_messages") or scope_data.get("messages") or []
cleaned_tool_results = scope_data.get("cleaned_tool_results") or scope_data.get("tool_results") or []
carry_forward = scope_data.get("carry_forward") or scope_data.get("carry_forward_context") or []

print("cleaned_messages:", cleaned_messages)
print("cleaned_tool_results:", cleaned_tool_results)
print("carry_forward_count:", len(carry_forward))
