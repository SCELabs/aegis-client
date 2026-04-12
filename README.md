# Aegis Client

Public Python client for the hosted Aegis AI stability API.

Aegis is a runtime control layer for AI systems. It analyzes instability such as drift, disagreement, or coordination failure and returns stabilization guidance you can apply at runtime, including prompt shaping, temperature adjustment, and coordination rules.

This client is intentionally thin. It does not implement backend logic locally. It sends requests to the hosted Aegis API and returns structured results.

---

## What Aegis Does

Aegis helps stabilize AI systems by returning:

- status
- summary
- probable cause
- recommended actions
- runtime configuration
- optional rewritten prompt guidance

Typical use cases:

- single-agent prompt drift
- inconsistent assistant behavior
- multi-agent disagreement
- unstable workflow coordination
- runtime intervention before failure compounds

---

## Installation

pip install -e .

Or install dependencies manually:

pip install requests

---

## Environment

cp .env.example .env

Example values:

AEGIS_API_KEY=your_api_key_here  
AEGIS_BASE_URL=http://127.0.0.1:8000

Run backend locally in the separate backend repo:

uvicorn app.main:app --reload

---

## Quick Start

from aegis import AegisClient

client = AegisClient(api_key="your_api_key")

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

## Client Methods

stabilize()

result = client.stabilize(
    system_type="single_agent",
    base_prompt="You are a helpful assistant.",
    symptoms=["instruction_drift"],
    severity="low",
)

stabilize_with_runtime()

result = client.stabilize_with_runtime(
    system_type="single_agent",
    base_prompt="You are a helpful assistant.",
    symptoms=["inconsistent_tone"],
    severity="medium",
    policy="runtime_control",
)

auto()

result = client.auto(
    system_type="multi_agent",
    base_prompt="You are a coordination layer for agents.",
    symptoms=["agents_disagree", "handoff_instability"],
    severity="high",
    policy="multi_agent_alignment",
)

---

## API Response Shape

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
      "intensity": "medium",
      "runtime_targets": [
        "relax hard constraints slightly",
        "allow controlled exploration",
        "widen acceptable response space"
      ]
    }
  ],
  "confidence": 0.78,
  "runtime_config": {
    "temperature": 0.3,
    "top_p": 1.0,
    "prompt_suffix": "Allow explicit exceptions only when they are directly supported by the case."
  },
  "prompt": "Full prompt guidance returned by the API."
}

---

## Demo Scripts

python examples/runtime_gateway_demo.py

python examples/multi_agent_drift_demo.py

---

## Local Development

pip install -e .

python -m unittest discover -s tests -v

---

## Design Principles

- thin
- public-safe
- backend-driven
- easy to integrate
- production-oriented

This client does NOT:

- reimplement backend logic
- expose SCE internals
- run local optimization or policy logic

The backend remains the source of truth.

---

## License

MIT
