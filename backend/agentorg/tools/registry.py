import asyncio
import functools
import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    handler: Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get_tools_for_agent(self, capabilities: list[str]) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for name, t in self._tools.items()
            if name in capabilities
        ]

    async def dispatch(self, name: str, input_data: dict, context: Any = None) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(context=context, **input_data)
            else:
                loop = asyncio.get_event_loop()
                fn = functools.partial(tool.handler, context=context, **input_data)
                result = await loop.run_in_executor(None, fn)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {e}"
