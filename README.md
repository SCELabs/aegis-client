# Aegis

Turn unstable AI into reliable systems.

Aegis is a drop-in control layer that stabilizes AI outputs at runtime — no retraining or prompt rewrites required.

---

## ⚡ Example

Without Aegis:  
"I understand the policy is 30 days, but we should approve this refund to maintain customer satisfaction." ❌  

With Aegis:  
"Deny the refund based on the 30-day policy, but offer store credit as an alternative." ✅  

Same model. Same prompt. Aegis makes it reliable.

---

## 🚀 10-second integration

    from aegis import AegisClient
    import openai

    client = AegisClient(api_key="your_api_key")

    response = openai.chat.completions.create(
        **client.auto_openai_config(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a support system."},
                {"role": "user", "content": "Handle this case."}
            ],
        )
    )

That’s it.

---

## 🧠 Local / Smaller Model Example

Use smaller or local models — Aegis makes them reliable.

Without Aegis, smaller models often produce:
- inconsistent reasoning  
- vague outputs  
- unstable structure  

With Aegis:

    response = openai.chat.completions.create(
        **client.auto_openai_config(
            model="gpt-3.5-turbo",  # or local / smaller model
            messages=[
                {"role": "system", "content": "Provide clear, structured reasoning."},
                {"role": "user", "content": "Explain this document."}
            ],
        )
    )

Result:

- clearer reasoning  
- more consistent outputs  
- fewer retries  

Use cheaper or local models without sacrificing reliability.

---

## 🛠 Tool Calling Example

Ensure your AI uses the correct tools.

Without Aegis:  
Model selects the wrong tool or responds without using one ❌  

With Aegis:

    response = openai.chat.completions.create(
        **client.auto_openai_config(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You must use available tools to complete tasks."},
                {"role": "user", "content": "Book a flight from NYC to SF tomorrow."}
            ],
        )
    )

Result:

- correct tool selection  
- higher task success rate  
- fewer failed executions  

---

## 💡 What Aegis does

Aegis analyzes instability and automatically adjusts:

- prompts  
- temperature  
- coordination behavior  
- runtime control signals  

Result:

- more consistent outputs  
- fewer retries  
- better decision-making  
- more reliable systems  

---

## 🔥 Why Aegis

- Works instantly with your existing setup  
- Reduces retries and debugging  
- Improves edge-case handling  
- Makes AI systems production-ready  

---

## 💰 Cost & Efficiency

Aegis improves first-pass success, which means:

- fewer retries  
- lower API costs  
- more predictable behavior  

In many cases:

Aegis pays for itself by reducing retries alone.

It can also help you:

Use cheaper or local models without sacrificing reliability.

---

## 🧠 Use Cases

### Customer Support
Handle edge cases consistently without breaking policy.

### Tool Calling / Agents
Ensure correct tool selection and execution.

### Structured Output
Reduce invalid responses and retry loops.

### Multi-Agent Systems
Prevent disagreement and coordination drift.

### Local / Smaller Models
Improve consistency and make them more usable.

---

## 📦 Installation

    pip install scelabs-aegis

---

## 🔑 Setup

    export AEGIS_API_KEY=your_api_key

---

## ⚙️ Optional: Local / Dev Config

    AEGIS_BASE_URL=http://127.0.0.1:8000

---

## 🧪 Example

    result = client.auto(
        system_type="multi_agent",
        base_prompt="You are a support coordination system.",
        symptoms=["agents_disagree"],
    )

    print(result["runtime_config"])

---

## 📊 Example Response

    {
      "status": "stable",
      "actions": [
        {
          "type": "adjust_flexibility",
          "description": "Loosen overly rigid behavior while preserving control."
        }
      ],
      "confidence": 0.78,
      "runtime_config": {
        "temperature": 0.3,
        "prompt_suffix": "Allow explicit exceptions only when supported by the case."
      }
    }

---

## 🧩 Design

Aegis is:

- thin  
- backend-driven  
- runtime-focused  
- production-oriented  

It does NOT:

- require retraining  
- replace your model  
- expose internal engine complexity  

---

## 🧪 Demos

    python examples/runtime_gateway_demo.py
    python examples/multi_agent_drift_demo.py

---

## License

MIT
