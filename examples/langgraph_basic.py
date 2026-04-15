from aegis import AegisClient

client = AegisClient()

state = {
    "messages": [
        {"role": "system", "content": "You are a coordinator."},
        {"role": "user", "content": "Resolve agent disagreement."}
    ]
}

plan = client.auto(
    system_type="multi_agent",
    base_prompt="You are a coordination system.",
    symptoms=["agents_disagree"],
    severity="high",
)

new_state = plan.apply_to_state(state)

print(new_state)
