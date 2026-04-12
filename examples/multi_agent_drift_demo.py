import os

from aegis import AegisClient


def simulate_baseline() -> None:
    print("=== BASELINE MULTI-AGENT SYSTEM ===")
    print("Symptoms:")
    print(["agents_disagree", "handoff_instability", "tool_overuse"])
    print()
    print("Observed behavior:")
    print("- Planner proposes one action")
    print("- Executor takes a conflicting action")
    print("- Reviewer escalates inconsistency")
    print()


def simulate_stabilized(client: AegisClient) -> None:
    print("=== AEGIS-STABILIZED MULTI-AGENT SYSTEM ===")
    result = client.auto(
        system_type="multi_agent",
        base_prompt="You are a support coordination system.",
        symptoms=["agents_disagree", "handoff_instability", "tool_overuse"],
        severity="high",
        policy="multi_agent_alignment",
        metadata={
            "agent_roles": ["planner", "executor", "reviewer"],
            "environment": "support_ops",
        },
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
    client = AegisClient(
        api_key=os.getenv("AEGIS_API_KEY", "demo-key"),
        base_url=os.getenv("AEGIS_BASE_URL", "http://127.0.0.1:8000"),
    )

    simulate_baseline()
    simulate_stabilized(client)


if __name__ == "__main__":
    main()
