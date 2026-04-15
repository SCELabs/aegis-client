from aegis import AegisClient

client = AegisClient()

messages = [
    {"role": "system", "content": "You are a support assistant."},
    {"role": "user", "content": "Can I get a refund after 40 days?"}
]

plan = client.auto(
    system_type="single_agent",
    base_prompt=messages[0]["content"],
    symptoms=["policy_drift"],
    severity="medium",
)

config = plan.for_openai(
    model="gpt-4o",
    messages=messages
)

print(config)
