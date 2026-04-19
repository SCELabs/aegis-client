"""Legacy compatibility plan interface. Prefer AegisClient.auto().<scope>() returning AegisResult."""

class AegisPlan:
    def __init__(self, data: dict):
        self._data = data

        # backward compatibility: lift legacy runtime_config into controls
        runtime_config = self._data.get("runtime_config", {}) or {}
        controls = self._data.setdefault("controls", {})

        generation = controls.setdefault("generation", {})
        prompt = controls.setdefault("prompt", {})

        if "temperature" in runtime_config and "temperature" not in generation:
            generation["temperature"] = runtime_config["temperature"]
        if "top_p" in runtime_config and "top_p" not in generation:
            generation["top_p"] = runtime_config["top_p"]
        if "prompt_suffix" in runtime_config and "suffix" not in prompt:
            prompt["suffix"] = runtime_config["prompt_suffix"]

    # --- core access ---
    @property
    def raw(self):
        return self._data

    @property
    def prediction(self):
        return self._data.get("prediction")

    @property
    def controls(self):
        return self._data.get("controls", {})

    @property
    def actions(self):
        return self._data.get("actions", [])

    @property
    def status(self):
        return self._data.get("status")


    # --- core helpers ---

    def generation_config(self):
        return (self.controls.get("generation") or {})

    def retry_config(self):
        return (self.controls.get("retry") or {})

    def validation_config(self):
        return (self.controls.get("validation") or {})

    def coordination_config(self):
        return (self.controls.get("coordination") or {})

    def tool_config(self):
        return (self.controls.get("tools") or {})


        return (self.controls.get("tools") or {})

        return (self.controls.get("generation") or {})

    def apply_system_prompt(self, prompt: str):
        prompt_controls = self.controls.get("prompt", {}) or {}

        full_prompt = prompt_controls.get("full_prompt")
        suffix = prompt_controls.get("suffix")

        if full_prompt:
            return full_prompt

        if suffix:
            return (prompt or "") + " " + suffix

        return prompt

    def apply_messages(self, messages: list[dict]):
        updated = [dict(m) for m in messages]

        prompt_controls = self.controls.get("prompt", {}) or {}
        suffix = prompt_controls.get("suffix")

        if not suffix:
            return updated

        if updated and updated[0].get("role") == "system":
            updated[0]["content"] = updated[0]["content"] + " " + suffix
        else:
            # inject system message if missing
            updated.insert(0, {
                "role": "system",
                "content": suffix
            })

        return updated

    def get_full_prompt(self, base_prompt: str | None = None):
        prompt_controls = self.controls.get("prompt", {}) or {}

        if prompt_controls.get("full_prompt"):
            return prompt_controls["full_prompt"]

        if base_prompt:
            return self.apply_system_prompt(base_prompt)

        return None

    # --- adapters ---
    def for_openai(self, *, model: str, messages: list[dict]):
        gen = self.generation_config()
        updated_messages = self.apply_messages(messages)

        return {
            "model": model,
            "messages": updated_messages,
            "temperature": gen.get("temperature", 0.7),
            "top_p": gen.get("top_p", 1.0),
            "aegis": self._data,
        }



    def apply_to_state(
        self,
        state: dict,
        *,
        messages_key: str = "messages",
        system_key: str = "system_prompt",
    ):
        from aegis.adapters.langgraph import build_langgraph_config

        result = build_langgraph_config(
            self,
            state=state,
            messages_key=messages_key,
            system_key=system_key,
        )
        return result["state"]


    def for_huggingface(
        self,
        *,
        prompt=None,
        model_kwargs=None,
    ):
        from aegis.adapters.huggingface import build_huggingface_config

        return build_huggingface_config(
            self,
            prompt=prompt,
            model_kwargs=model_kwargs,
        )


    def for_langgraph(
        self,
        *,
        state=None,
        messages_key: str = "messages",
        system_key: str = "system_prompt",
    ):
        from aegis.adapters.langgraph import build_langgraph_config

        return build_langgraph_config(
            self,
            state=state,
            messages_key=messages_key,
            system_key=system_key,
        )


    def for_langchain(
        self,
        *,
        messages=None,
        system_prompt=None,
        model_kwargs=None,
    ):
        from aegis.adapters.langchain import build_langchain_config

        return build_langchain_config(
            self,
            messages=messages,
            system_prompt=system_prompt,
            model_kwargs=model_kwargs,
        )


    def simple_config(self):
        controls = self.controls
        return {
            "prompt": (controls.get("prompt", {}) or {}).get("full_prompt"),
            "temperature": (controls.get("generation", {}) or {}).get("temperature"),
        }

    # --- backwards compatibility ---
    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)