from pathlib import Path

from .registry import ToolDefinition


def _read_file(path: str, context=None) -> str:
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading {path}: {e}"


def _write_file(path: str, content: str, context=None) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


def _list_files(directory: str = ".", pattern: str = "**/*", context=None) -> str:
    p = Path(directory)
    if not p.exists():
        return f"Directory not found: {directory}"
    files = sorted(str(f.relative_to(p)) for f in p.glob(pattern) if f.is_file())
    return "\n".join(files) if files else "(empty)"


READ_FILE = ToolDefinition(
    name="read_file",
    description="Read the full contents of a file at a given path",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"}
        },
        "required": ["path"],
    },
    handler=_read_file,
)

WRITE_FILE = ToolDefinition(
    name="write_file",
    description="Write content to a file, creating parent directories as needed",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
    handler=_write_file,
)

LIST_FILES = ToolDefinition(
    name="list_files",
    description="List files in a directory matching an optional glob pattern",
    input_schema={
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Directory path", "default": "."},
            "pattern": {"type": "string", "description": "Glob pattern", "default": "**/*"},
        },
    },
    handler=_list_files,
)
