from aegis import AegisClient, AegisConfig


client = AegisClient(
    api_key="YOUR_API_KEY",
    config=AegisConfig(mode="balanced", explain=True, emit_trace=True),
)

result = client.auto().llm(
    base_prompt="You are a careful assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(result.debug_summary())
print(result.actions)
print(result.trace)
