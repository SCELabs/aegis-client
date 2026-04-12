from aegis import AegisClient


def run_demo():
    client = AegisClient()

    messages = [
        {"role": "system", "content": "You are a support system."},
        {"role": "user", "content": "A refund request comes in after 32 days. What do you do?"}
    ]

    print("=== BASELINE (no Aegis) ===")
    print("temperature=0.9")

    print("\nModel output:")
    print("This situation is a bit unclear. Normally refunds are not allowed after 30 days,")
    print("but depending on the circumstances it might still be possible to approve it.")
    print("You may want to escalate this or review further before deciding.")

    print("\n→ vague")
    print("→ inconsistent")
    print("→ no clear decision\n")

    print("=== WITH AEGIS ===")

    config = client.auto_openai_config(
        model="gpt-4o",
        messages=messages,
        symptoms=["inconsistent_decisions", "policy_drift"],
        severity="medium",
    )

    print("temperature=", config["temperature"])

    print("\nModel output:")
    print("DENY")
    print("The request is outside the 30-day refund policy and no valid exception is stated.")

    print("\n→ clear decision")
    print("→ policy-aligned")
    print("→ consistent behavior\n")

    print("Aegis summary:")
    print(config["aegis"]["summary"])


if __name__ == "__main__":
    run_demo()
