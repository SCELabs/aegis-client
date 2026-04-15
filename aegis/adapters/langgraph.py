
def build_langgraph_config(
    plan,
    *,
    state=None,
    messages_key="messages",
    system_key="system_prompt",
):
    state = dict(state or {})

    # apply message updates
    if messages_key in state:
        state[messages_key] = plan.apply_messages(state[messages_key])

    # apply system prompt updates
    if system_key in state:
        state[system_key] = plan.apply_system_prompt(state[system_key])

    # generation config
    gen = plan.generation_config()

    return {
        "state": state,
        "model_kwargs": gen,
        "aegis": plan.raw,
        "prediction": plan.prediction,
        "actions": plan.actions,
    }
