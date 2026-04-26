from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TaskDef:
    id: str
    name: str
    phase: str
    agent: str
    description: str
    depends_on: list[str]
    inputs: dict
    outputs: list[dict]
    condition: str | None
    after_pr: dict
    task_type: str  # "agent" or "human_gate"
    gate: dict = field(default_factory=dict)  # config for human_gate tasks


@dataclass
class WorkflowDef:
    id: str
    slug: str
    name: str
    description: str
    phases: list[str]
    inputs: dict
    tasks: list[TaskDef]
    guardrails: dict
    triggers: list[dict]
    raw_yaml: str


# Sensible defaults keyed by workflow id keyword
_AFTER_PR_DEFAULTS: dict[str, dict] = {
    "soul": {"action": "agent_review", "reviewer": "reviewer"},
    "docs": {"action": "auto_merge"},
}
_AFTER_PR_FALLBACK = {"action": "human_review"}


def _default_after_pr(workflow_id: str) -> dict:
    for keyword, default in _AFTER_PR_DEFAULTS.items():
        if keyword in workflow_id:
            return default
    return _AFTER_PR_FALLBACK


def parse_workflow(yaml_path: str | Path) -> WorkflowDef:
    path = Path(yaml_path)
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    workflow_id = data["id"]
    tasks = []
    for t in data.get("tasks", []):
        task_type = t.get("type", "agent")
        after_pr = t.get("after_pr") or _default_after_pr(workflow_id)
        tasks.append(
            TaskDef(
                id=t["id"],
                name=t.get("name", t["id"]),
                phase=t.get("phase", "execute"),
                agent=t.get("agent", ""),
                description=t.get("description", ""),
                depends_on=t.get("depends_on", []),
                inputs=t.get("inputs", {}),
                outputs=t.get("outputs", []),
                condition=t.get("condition"),
                after_pr=after_pr,
                task_type=task_type,
                gate=t.get("gate", {}),
            )
        )

    return WorkflowDef(
        id=workflow_id,
        slug=workflow_id,
        name=data["name"],
        description=data.get("description", ""),
        phases=data.get("phases", ["execute"]),
        inputs=data.get("inputs", {}),
        tasks=tasks,
        guardrails=data.get("guardrails", {}),
        triggers=data.get("triggers", [{"type": "manual"}]),
        raw_yaml=raw,
    )


def resolve_inputs(task_inputs: dict, run_inputs: dict, task_outputs: dict[str, dict]) -> dict:
    """Resolve {{inputs.key}} and {{tasks.id.outputs.key}} template variables."""
    resolved = {}
    for k, v in task_inputs.items():
        if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
            ref = v[2:-2].strip()
            if ref.startswith("inputs."):
                key = ref[7:]
                resolved[k] = run_inputs.get(key, f"<missing input: {key}>")
            elif ref.startswith("tasks."):
                parts = ref.split(".")
                if len(parts) >= 4 and parts[2] == "outputs":
                    task_id, output_key = parts[1], parts[3]
                    resolved[k] = task_outputs.get(task_id, {}).get(output_key, f"<missing: {ref}>")
                else:
                    resolved[k] = f"<unresolved: {ref}>"
            else:
                resolved[k] = v
        else:
            resolved[k] = v
    return resolved
