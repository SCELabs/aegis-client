# Aegis Client

Stabilize AI systems at runtime with one call.

Aegis is a lightweight middleware layer that improves consistency, coordination, and control in AI systems by automatically adjusting prompts and runtime parameters.

---

## 10-second integration

from aegis import AegisClient

client = AegisClient(api_key="your_api_key")

config = client.auto_openai_config(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a support system."},
        {"role": "user", "content": "Handle this case."}
    ],
    symptoms=["agents_disagree"],
    severity="medium",
)

# Drop into your OpenAI call
response = openai.chat.completions.create(**config)

---

## What Aegis does

Aegis analyzes instability and returns:

- stabilized prompt
- temperature adjustments
- coordination improvements
- runtime control signals

Typical use cases:

- inconsistent outputs
- prompt drift
- multi-agent disagreement
- unstable workflows
- brittle decision systems

---

## Installation

pip install -e .

---

## Environment

cp .env.example .env

Example:

AEGIS_API_KEY=your_api_key_here  
AEGIS_BASE_URL=http://127.0.0.1:8000

---

## Core usage

from aegis import AegisClient

client = AegisClient()

result = client.auto(
    system_type="multi_agent",
    base_prompt="You are a support coordination system.",
    symptoms=["agents_disagree", "unstable_workflow"],
    severity="medium",
    policy="multi_agent_alignment",
)

print(result["runtime_config"])
print(result["prompt"])

---

## OpenAI-ready usage

config = client.auto_openai_config(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a support system."},
        {"role": "user", "content": "Handle this case."}
    ],
    symptoms=["agents_disagree"],
    severity="medium",
)

print(config["messages"])
print(config["temperature"])

---

## API response (real example)

{
  "status": "stable",
  "summary": "Your system is stable under the recommended intervention, but it is still close to a watch-state boundary.",
  "cause": "The system appeared overly rigid and required controlled flexibility.",
  "actions": [
    {
      "type": "adjust_flexibility",
      "label": "Adjust system flexibility",
      "description": "Loosen overly rigid behavior enough to recover useful adaptability.",
      "expected_effect": "Less brittleness while preserving control.",
      "intensity": "medium"
    }
  ],
  "confidence": 0.78,
  "runtime_config": {
    "temperature": 0.3,
    "top_p": 1.0,
    "prompt_suffix": "Allow explicit exceptions only when they are directly supported by the case."
  }
}

---

## Demo

python examples/runtime_gateway_demo.py  
python examples/multi_agent_drift_demo.py  

---

## Design

Aegis is:

- thin
- backend-driven
- runtime-focused
- production-oriented

It does NOT:

- reimplement backend logic
- expose SCE internals
- run local optimization

---

## License

MIT
