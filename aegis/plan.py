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

    # --- adapters ---
    def for_openai(self, *, model: str, messages: list[dict]):
        controls = self.controls
        gen = controls.get("generation", {})
        prompt = controls.get("prompt", {})

        updated_messages = [dict(m) for m in messages]

        suffix = prompt.get("suffix")
        if suffix and updated_messages:
            if updated_messages[0].get("role") == "system":
                updated_messages[0]["content"] += " " + suffix

        return {
            "model": model,
            "messages": updated_messages,
            "temperature": gen.get("temperature", 0.7),
            "top_p": gen.get("top_p", 1.0),
            "aegis": self._data,
        }

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