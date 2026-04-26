from dataclasses import dataclass, field

import anthropic

from ..config import settings
from ..core.soul_manager import SoulDefinition
from ..tools.registry import ToolRegistry

# Pricing per million tokens (claude-sonnet-4-6)
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0


@dataclass
class RunContext:
    run_id: str
    workflow_name: str
    phase: str
    shared_context: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)


@dataclass
class TaskToolContext:
    task_id: str
    run_context: RunContext
    agent_slug: str = ""


@dataclass
class TaskResult:
    task_id: str
    summary: str
    full_output: str
    outputs: dict
    tool_calls_made: list
    token_count: int
    cost_usd: float


class AgentRunner:
    def __init__(self, tool_registry: ToolRegistry):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.tool_registry = tool_registry

    async def run_task(
        self,
        task_id: str,
        task_name: str,
        task_description: str,
        agent_soul: SoulDefinition,
        run_context: RunContext,
        task_inputs: dict,
        event_bus=None,  # Optional[EventBus] — avoids circular import
    ) -> TaskResult:
        print(f"  [{agent_soul.slug}] {task_name}")

        system = [
            {
                "type": "text",
                "text": agent_soul.system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        tools = self.tool_registry.get_tools_for_agent(agent_soul.capabilities)
        messages = [{"role": "user", "content": self._build_message(task_name, task_description, run_context, task_inputs)}]
        tool_context = TaskToolContext(task_id=task_id, run_context=run_context, agent_slug=agent_soul.slug)

        all_tool_calls: list[dict] = []
        total_input_tokens = 0
        total_output_tokens = 0

        while True:
            response = await self.client.messages.create(
                model=agent_soul.model,
                max_tokens=agent_soul.max_tokens,
                system=system,
                messages=messages,
                tools=tools or [],
            )
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn" or not tools:
                break

            tool_results = []
            has_tool_use = False
            for block in response.content:
                if block.type == "tool_use":
                    has_tool_use = True
                    print(f"  [{agent_soul.slug}] → {block.name}({list(block.input.keys())})")

                    if event_bus:
                        from ..core.event_bus import RunEvent
                        await event_bus.emit(RunEvent(
                            run_id=run_context.run_id,
                            task_id=task_id,
                            event_type="tool_call",
                            payload={"tool": block.name, "input_keys": list(block.input.keys())},
                        ))

                    result = await self.tool_registry.dispatch(block.name, block.input, context=tool_context)
                    all_tool_calls.append({"tool": block.name, "input": block.input, "result": result[:300]})
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

            if not has_tool_use:
                break

            messages.append({"role": "user", "content": tool_results})

        final_text = "".join(block.text for block in response.content if hasattr(block, "text"))
        outputs = self._extract_outputs(final_text)
        cost_usd = (total_input_tokens * _INPUT_COST_PER_M + total_output_tokens * _OUTPUT_COST_PER_M) / 1_000_000
        token_count = total_input_tokens + total_output_tokens

        print(f"  [{agent_soul.slug}] done — {token_count} tokens (${cost_usd:.4f})")

        return TaskResult(
            task_id=task_id,
            summary=final_text[:500] + "..." if len(final_text) > 500 else final_text,
            full_output=final_text,
            outputs=outputs,
            tool_calls_made=all_tool_calls,
            token_count=token_count,
            cost_usd=cost_usd,
        )

    def _build_message(
        self,
        task_name: str,
        task_description: str,
        run_context: RunContext,
        task_inputs: dict,
    ) -> str:
        lines = [
            f"# Task: {task_name}",
            f"\n{task_description}" if task_description else "",
            f"\n## Workflow",
            f"- Name: {run_context.workflow_name}",
            f"- Phase: {run_context.phase}",
            f"- Run ID: {run_context.run_id}",
        ]
        if run_context.inputs:
            lines.append("\n## Workflow Inputs")
            lines.extend(f"- **{k}**: {v}" for k, v in run_context.inputs.items())
        if task_inputs:
            lines.append("\n## Task Inputs")
            lines.extend(f"- **{k}**: {v}" for k, v in task_inputs.items())
        if run_context.shared_context:
            lines.append("\n## Shared Context from Previous Tasks")
            for k, v in run_context.shared_context.items():
                lines.append(f"\n### {k}\n{v}")
        lines.append(
            "\n---\nComplete this task. When done, summarize what you accomplished. "
            "Use `OUTPUT key: value` lines for any values subsequent tasks will need "
            "(e.g. `OUTPUT branch_name: feature/xyz` or `OUTPUT pr_url: https://...`)."
        )
        return "\n".join(lines)

    def _extract_outputs(self, text: str) -> dict:
        outputs = {}
        for line in text.split("\n"):
            if line.startswith("OUTPUT ") and ": " in line:
                key, _, value = line[7:].partition(": ")
                outputs[key.strip()] = value.strip()
        return outputs
