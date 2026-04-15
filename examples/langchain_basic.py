from aegis import AegisClient

client = AegisClient()

messages = [
    {"role": "system", "content": "You are a support assistant."},
    {"role": "user", "content": "Handle this case clearly."}
]

plan = client.auto(
    system_type="single_agent",
    base_prompt=messages[0]["content"],
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

cfg = plan.for_langchain(
    messages=messages,
    model_kwargs={"temperature": 0.8}
)

print(cfg)
