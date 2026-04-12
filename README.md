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

Run backend locally (separate repo):

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
  "summary": "System stabilized.",
  "cause": "Drift detected in coordination flow.",
  "actions": ["reduce_temperature", "tighten_prompt_scope"],
  "confidence": 0.82,
  "runtime_config": {
    "temperature": 0.6,
    "top_p": 0.9,
    "prompt_suffix": "Be more consistent and avoid speculative actions."
  },
  "prompt": "Optional rewritten prompt guidance"
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

---

## License

MIT
