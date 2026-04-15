
def build_huggingface_config(
    plan,
    *,
    prompt=None,
    model_kwargs=None,
):
    model_kwargs = dict(model_kwargs or {})

    # generation controls
    gen = plan.generation_config()
    if "temperature" in gen:
        model_kwargs["temperature"] = gen["temperature"]
    if "top_p" in gen:
        model_kwargs["top_p"] = gen["top_p"]

    # prompt handling
    updated_prompt = None
    if prompt is not None:
        updated_prompt = plan.apply_system_prompt(prompt)

    return {
        "prompt": updated_prompt,
        "model_kwargs": model_kwargs,
        "aegis": plan.raw,
    }
