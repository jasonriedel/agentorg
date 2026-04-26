"""Tools for agents to read and update their persistent learnings files."""
from pathlib import Path

from .registry import ToolDefinition
from ..config import settings


def _get_learnings(context=None) -> str:
    if not context or not context.agent_slug:
        return "Error: agent context not available"
    learnings_path = Path(settings.souls_dir) / f"{context.agent_slug}.learnings.md"
    if not learnings_path.exists():
        return f"No learnings file yet for '{context.agent_slug}'. Call update_learnings to create one."
    content = learnings_path.read_text(encoding="utf-8").strip()
    return content if content else "Learnings file is empty."


def _update_learnings(content: str, context=None) -> str:
    """Append new learnings to the agent's persistent learnings file."""
    if not context or not context.agent_slug:
        return "Error: agent context not available"
    if not content or not content.strip():
        return "Error: content cannot be empty"

    slug = context.agent_slug
    learnings_path = Path(settings.souls_dir) / f"{slug}.learnings.md"

    existing = ""
    if learnings_path.exists():
        existing = learnings_path.read_text(encoding="utf-8").strip()

    run_id = context.run_context.run_id[:8] if context.run_context else "unknown"
    separator = f"\n\n---\n*Added after run {run_id}*\n\n"
    new_content = (existing + separator + content.strip()) if existing else content.strip()

    learnings_path.write_text(new_content, encoding="utf-8")
    return f"Learnings updated for '{slug}'. File now has {len(new_content)} characters."


GET_LEARNINGS = ToolDefinition(
    name="get_learnings",
    description="Read your persistent learnings file — accumulated lessons from past runs",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_get_learnings,
)

UPDATE_LEARNINGS = ToolDefinition(
    name="update_learnings",
    description=(
        "Append new learnings to your persistent memory file. "
        "Write concise, actionable lessons in Markdown. "
        "These will be injected into your system prompt on future runs."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Markdown text to append to your learnings file. Be specific and actionable.",
            },
        },
        "required": ["content"],
    },
    handler=_update_learnings,
)
