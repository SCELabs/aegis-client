# Aegis

Turn unstable AI into reliable systems.

Aegis is a runtime control layer that predicts instability and returns control plans to stabilize AI behavior — no retraining or prompt rewrites required.

pip install scelabs-aegis

---

## ⚡ Example: Real Workflow Impact

This demo runs the same multi-agent workflow twice:

* once as baseline
* once with Aegis applied at runtime

Both reach the same correct final answers.

The difference is how efficiently they get there.

### 📊 Results

| Metric         | Baseline | Aegis     |
| -------------- | -------- | --------- |
| Final Accuracy | 1.0      | 1.0       |
| Lane Accuracy  | 0.83     | 1.0       |
| Efficiency     | 0.82     | 1.0       |
| LLM Calls      | 44       | 32        |
| Verifier Calls | 11       | 8         |
| Replans        | 5        | 2         |
| Cost           | $0.00583 | $0.003946 |

### 🔥 What changed

* Same outcomes
* Fewer steps
* Fewer retries
* Better routing
* Lower cost

### 🧠 Takeaway

Aegis does not change what your system decides.

It changes how your system behaves while deciding.

Same system.
Better execution.

---

## 🚀 10-second integration

```
from aegis import AegisClient
import openai

client = AegisClient(api_key="your_api_key")

plan = client.auto(
    system_type="multi_agent",
    base_prompt="You are a support system.",
    symptoms=["agents_disagree"],
    severity="medium",
)

response = openai.chat.completions.create(
    **plan.for_openai(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a support system."},
            {"role": "user", "content": "Handle this case."}
        ],
    )
)
```

That’s it.

---

## 🧠 What just happened

Aegis analyzed your system and returned a control plan:

* adjusted temperature
* stabilized prompt behavior
* improved coordination
* reduced variability

You didn’t rewrite anything.

---

## 🧠 Advanced usage (Plan API)

```
plan = client.plan(
    system_type="single_agent",
    base_prompt="You are a support assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

print(plan.prediction)
print(plan.controls)
```

---

## 📦 Installation

```
pip install scelabs-aegis
```

---

## 🔑 Onboarding

Create an Aegis account and get an API key.

### 1. Request an API key

```
curl -X POST "$AEGIS_URL/v1/onboard" \
  -H "Content-Type: application/json" \
  -d '{"account_name":"My Team","email":"you@example.com"}'
```

You will receive:

* account_id
* email
* plan
* monthly_request_limit
* api_key

---

### 2. Set your API key

```
export AEGIS_API_KEY=your_api_key
```

Optional:

```
export AEGIS_URL=https://your-aegis-url
```

---

### 3. You're ready

```
from aegis import AegisClient
import os

client = AegisClient(
    api_key=os.environ["AEGIS_API_KEY"],
    base_url=os.getenv("AEGIS_URL"),
)
```

---

## 🧠 Local / Smaller Model Example

Use smaller or local models — Aegis makes them reliable.

Without Aegis:

* inconsistent reasoning
* unstable outputs
* poor structure

With Aegis:

```
plan = client.auto(
    system_type="single_agent",
    base_prompt="Provide clear reasoning.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

response = openai.chat.completions.create(
    **plan.for_openai(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Provide clear reasoning."},
            {"role": "user", "content": "Explain this document."}
        ],
    )
)
```

Result:

* clearer reasoning
* more consistent outputs
* fewer retries

---

## 🛠 Tool Calling Example

Ensure your AI uses the correct tools.

Without Aegis:

* wrong tool selection
* skipped tools

With Aegis:

```
plan = client.auto(
    system_type="multi_agent",
    base_prompt="You must use tools correctly.",
    symptoms=["tool_misuse"],
    severity="medium",
)

response = openai.chat.completions.create(
    **plan.for_openai(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You must use tools."},
            {"role": "user", "content": "Book a flight."}
        ],
    )
)
```

Result:

* correct tool usage
* higher task success
* fewer failures

---

## 💡 What Aegis does

Aegis analyzes instability and returns a control plan that adjusts:

* prompts
* generation behavior
* coordination rules
* runtime control signals

Result:

* more consistent outputs
* fewer retries
* better decision-making
* more reliable systems

---

## 🔥 Why Aegis

* Works instantly with your existing setup
* No retraining required
* Reduces retries and debugging
* Improves edge-case handling
* Makes AI systems production-ready

---

## 💰 Cost & Efficiency

Aegis improves first-pass success:

* fewer retries
* lower API cost
* more predictable behavior

In many cases:

Aegis pays for itself by reducing retries alone.

---

## 🧠 Use Cases

### Customer Support

Handle edge cases consistently without breaking policy.

### Tool Calling / Agents

Ensure correct tool usage and execution.

### Structured Output

Reduce invalid responses and retry loops.

### Multi-Agent Systems

Prevent disagreement and coordination drift.

### Local / Smaller Models

Make them reliable and usable.

---

## 🧪 Demos

```
python examples/runtime_gateway_demo.py
python examples/multi_agent_drift_demo.py
```

---

## 🚀 Demo: Multi-Agent Workflow Stabilization

https://github.com/SCELabs/aegis-agent-workflow-demo

---

## 🧩 Design

Aegis is:

* thin
* backend-driven
* runtime-focused
* production-oriented

It does NOT:

* replace your model
* require retraining
* expose internal engine complexity

---

## License

MIT
