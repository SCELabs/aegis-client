from aegis import AegisClient


client = AegisClient(api_key="YOUR_API_KEY")

result = client.auto().step(
    step_name="ticket_triage",
    step_input={"ticket_id": "T-42", "priority": "high"},
    symptoms=["routing_instability"],
    severity="high",
)

print(result.debug_summary())
print(result.used_fallback)
print(result.explanation)
