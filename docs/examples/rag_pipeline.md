# RAG Pipeline with Aegis

This pattern places Aegis between retrieval and generation.

## Pipeline Shape

```text
retrieve -> Aegis rag control -> generate
```

## Example

```python
from aegis import AegisClient

client = AegisClient()

# 1) Retrieval step (your system)
def retrieve(query: str) -> list[str]:
    return [
        "Policy v3 released on April 1.",
        "Refund window reduced to 14 days.",
        "Legacy pricing details from 2022.",
    ]

query = "What changed in refund policy?"
raw_chunks = retrieve(query)

# 2) Aegis controls retrieved evidence/context
result = client.auto().rag(
    query=query,
    retrieved_context=raw_chunks,
    symptoms=["retrieval_drift"],
    severity="medium",
)

# 3) Build final context for generation
final_context = result.scope_data.get("retrieved_context", raw_chunks)

prompt = (
    "Answer using only the context below.\\n\\n"
    + "\\n".join(final_context)
)

# 4) Generation step (your system/model call)
# response = model.generate(prompt)
# print(response)

print("Final context:", final_context)
print(result.debug_summary())
```

Aegis does not replace retrieval or generation. It controls the handoff between them.
