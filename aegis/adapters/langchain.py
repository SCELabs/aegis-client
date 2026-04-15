
def build_langchain_config(plan, *, messages=None, system_prompt=None, model_kwargs=None):
    model_kwargs = dict(model_kwargs or {})

    # generation controls
    gen = plan.generation_config()
    if "temperature" in gen:
        model_kwargs["temperature"] = gen["temperature"]
    if "top_p" in gen:
        model_kwargs["top_p"] = gen["top_p"]

    # messages handling
    updated_messages = None
    if messages is not None:
        updated_messages = plan.apply_messages(messages)

    # system prompt handling
    updated_prompt = None
    if system_prompt is not None:
        updated_prompt = plan.apply_system_prompt(system_prompt)

    return {
        "messages": updated_messages,
        "system_prompt": updated_prompt,
        "model_kwargs": model_kwargs,
        "aegis": plan.raw,
    }
