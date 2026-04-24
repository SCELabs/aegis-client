# OpenAI + Aegis LLM Control

This example shows a baseline OpenAI-style call and then an Aegis-controlled version.

## Baseline (no Aegis)

```python
from openai import OpenAI

client = OpenAI(api_key="OPENAI_API_KEY")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0.7,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize this incident report."},
    ],
)

print(response.choices[0].message.content)
```

## Aegis-Controlled Version

```python
from openai import OpenAI
from aegis import AegisClient

openai_client = OpenAI(api_key="OPENAI_API_KEY")
aegis_client = AegisClient()  # uses AEGIS_API_KEY / AEGIS_BASE_URL if set

base_prompt = "You are a helpful assistant."
user_query = "Summarize this incident report."

aegis_result = aegis_client.auto().llm(
    base_prompt=base_prompt,
    input={"user_query": user_query},
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

runtime_config = aegis_result.scope_data.get("runtime_config", {})
controlled_prompt = aegis_result.scope_data.get("controlled_prompt", base_prompt)

response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=runtime_config.get("temperature", 0.7),
    top_p=runtime_config.get("top_p", 1.0),
    messages=[
        {"role": "system", "content": controlled_prompt},
        {"role": "user", "content": user_query},
    ],
)

print(response.choices[0].message.content)
print(aegis_result.debug_summary())
```

Aegis controls runtime behavior; your app still executes the model call.
