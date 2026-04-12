from typing import Any, Dict, List, TypedDict


class RuntimeConfig(TypedDict, total=False):
    temperature: float
    top_p: float
    prompt_suffix: str


class Action(TypedDict, total=False):
    type: str
    label: str
    description: str
    expected_effect: str
    intensity: str
    runtime_targets: List[str]


class StabilizeResponse(TypedDict, total=False):
    status: str
    summary: str
    cause: str
    actions: List[Action]
    confidence: float
    runtime_config: RuntimeConfig
    prompt: str


class StabilizeRequest(TypedDict, total=False):
    system_type: str
    base_prompt: str
    symptoms: List[str]
    severity: str
    policy: str
    metadata: Dict[str, Any]
    include_runtime: bool
