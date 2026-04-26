from .registry import ToolDefinition


def _get_context(key: str, context=None) -> str:
    if context is None or not hasattr(context, "run_context"):
        return "No context available"
    value = context.run_context.shared_context.get(key)
    if value is None:
        return f"Key '{key}' not found in shared context"
    return str(value)


def _set_context(key: str, value: str, context=None) -> str:
    if context is None or not hasattr(context, "run_context"):
        return "No context available"
    context.run_context.shared_context[key] = value
    return f"Set '{key}' in shared context"


GET_CONTEXT = ToolDefinition(
    name="get_context",
    description="Retrieve a value from the shared workflow context set by a previous task",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Context key to retrieve"},
        },
        "required": ["key"],
    },
    handler=_get_context,
)

SET_CONTEXT = ToolDefinition(
    name="set_context",
    description="Store a value in the shared workflow context so subsequent tasks can access it",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Context key"},
            "value": {"type": "string", "description": "Value to store (will be converted to string)"},
        },
        "required": ["key", "value"],
    },
    handler=_set_context,
)
