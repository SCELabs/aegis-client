from transformers import pipeline
from aegis import AegisClient

client = AegisClient()

pipe = pipeline("text-generation", model="gpt2")

plan = client.auto(
    system_type="single_agent",
    base_prompt="You are a support assistant.",
    symptoms=["inconsistent_outputs"],
    severity="medium",
)

cfg = plan.for_huggingface(
    prompt="Handle this support request clearly and decisively."
)

output = pipe(cfg["prompt"], **cfg["model_kwargs"])

print(output)
