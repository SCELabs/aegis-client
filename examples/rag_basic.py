from aegis import AegisClient, AegisConfig


client = AegisClient(
    api_key="YOUR_API_KEY",
    config=AegisConfig(mode="balanced", explain=True),
)

result = client.auto().rag(
    query="Summarize the updated support policy.",
    retrieved_context=[
        "Support policy v3: enterprise SLA updated to 2 hours.",
        "Billing disputes now route to the finance escalation queue.",
    ],
    symptoms=["hallucinated_references"],
    severity="medium",
)

print(result.debug_summary())
print(result.scope)
print(result.metrics)
