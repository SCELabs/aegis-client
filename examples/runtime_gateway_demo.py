import os

from aegis import AegisClient


def baseline_call(base_prompt: str) -> None:
    print("=== BASELINE ===")
    print("Prompt:")
    print(base_prompt)
    print()
    print("Simulated model settings:")
    print({"temperature": 0.9, "top_p": 1.0})
    print()


def stabilized_call(client: AegisClient, base_prompt: str) -> None:
    print("=== AEGIS AUTO ===")
    result = client.auto(
        system_type="single_agent",
        base_prompt=base_prompt,
        symptoms=["inconsistent_tone", "instruction_drift"],
        severity="medium",
        policy="runtime_control",
    )

    print("Status:", result.get("status"))
    print("Summary:", result.get("summary"))
    print("Cause:", result.get("cause"))
    print("Confidence:", result.get("confidence"))
    print("Actions:", result.get("actions"))
    print("Runtime config:", result.get("runtime_config"))
    print("Prompt:", result.get("prompt"))
    print()


def main() -> None:
    base_prompt = "You are a support assistant. Be helpful, clear, and consistent."

    client = AegisClient(
        api_key=os.getenv("AEGIS_API_KEY", "demo-key"),
        base_url=os.getenv("AEGIS_BASE_URL", "http://127.0.0.1:8000"),
    )

    baseline_call(base_prompt)
    stabilized_call(client, base_prompt)


if __name__ == "__main__":
    main()
