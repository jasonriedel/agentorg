"""Claude Code session history reader.

Scans ~/.claude/projects/ and parses JSONL session files to surface
conversation history, sub-agents spawned, and resume commands.
"""
import ast
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claude-sessions", tags=["claude-sessions"])


# ── schema ──────────────────────────────────────────────────────────────

class AgentSpawn(BaseModel):
    description: str
    subagent_type: str


class SessionSummary(BaseModel):
    id: str
    project_dir: str
    project_path: str
    title: str
    cwd: str | None
    started_at: str | None
    last_active: str | None
    message_count: int
    agent_spawn_count: int
    first_message: str | None


class SessionMessage(BaseModel):
    role: str          # "user" | "assistant" | "tool_use" | "agent_spawn"
    content: str
    tool_name: str | None = None
    timestamp: str | None = None


class SessionDetail(SessionSummary):
    agent_spawns: list[AgentSpawn]
    messages: list[SessionMessage]
    resume_command: str


# ── path helpers ─────────────────────────────────────────────────────────

def _projects_dir() -> Path:
    return Path(settings.claude_projects_dir).expanduser()


def _decode_project_path(dirname: str) -> str:
    """Best-effort decode of directory name back to filesystem path.
    Claude encodes /Users/foo/bar as -Users-foo-bar.
    """
    if dirname.startswith("-"):
        return "/" + dirname[1:].replace("-", "/")
    return dirname


def _find_session_file(session_id: str) -> Path | None:
    projects = _projects_dir()
    if not projects.exists():
        return None
    for jsonl in projects.rglob(f"{session_id}.jsonl"):
        return jsonl
    return None


# ── parser ───────────────────────────────────────────────────────────────

def _safe_parse(raw: Any) -> Any:
    """Parse a field that might be a JSON-encoded dict stored as a string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return ast.literal_eval(raw)
        except Exception:
            pass
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}


def _extract_text(content: Any) -> str:
    """Pull plain text from message content (string or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, str):
                        parts.append(inner)
        return "\n".join(p for p in parts if p)
    return ""


def _parse_session_summary(jsonl_path: Path, project_dir: str) -> SessionSummary | None:
    """Fast parse: read only enough lines for the summary card."""
    title: str | None = None
    cwd: str | None = None
    session_id: str = jsonl_path.stem
    first_ts: str | None = None
    last_ts: str | None = None
    first_message: str | None = None
    message_count = 0
    agent_spawn_count = 0

    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                try:
                    rec = json.loads(raw_line)
                except Exception:
                    continue

                t = rec.get("type")

                if t == "custom-title":
                    title = rec.get("customTitle")
                    session_id = rec.get("sessionId", session_id)
                    continue

                ts = rec.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                if not cwd:
                    cwd = rec.get("cwd")

                if t == "user" and not rec.get("isMeta"):
                    msg = _safe_parse(rec.get("message", {}))
                    text = _extract_text(msg.get("content", ""))
                    if text and len(text) > 5 and not text.startswith("<"):
                        message_count += 1
                        if first_message is None:
                            first_message = text[:250]

                elif t == "assistant":
                    msg = _safe_parse(rec.get("message", {}))
                    for block in msg.get("content", []):
                        if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Agent":
                            agent_spawn_count += 1

    except Exception as e:
        logger.warning(f"[sessions] failed to parse {jsonl_path}: {e}")
        return None

    return SessionSummary(
        id=session_id,
        project_dir=project_dir,
        project_path=_decode_project_path(project_dir),
        title=title or session_id[:8],
        cwd=cwd,
        started_at=first_ts,
        last_active=last_ts,
        message_count=message_count,
        agent_spawn_count=agent_spawn_count,
        first_message=first_message,
    )


def _parse_session_detail(jsonl_path: Path, project_dir: str) -> SessionDetail | None:
    """Full parse for the detail view."""
    summary_data: dict = {}
    messages: list[SessionMessage] = []
    agent_spawns: list[AgentSpawn] = []
    title: str | None = None
    cwd: str | None = None
    session_id: str = jsonl_path.stem
    first_ts: str | None = None
    last_ts: str | None = None
    first_message: str | None = None
    message_count = 0

    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                try:
                    rec = json.loads(raw_line)
                except Exception:
                    continue

                t = rec.get("type")
                ts = rec.get("timestamp")

                if t == "custom-title":
                    title = rec.get("customTitle")
                    session_id = rec.get("sessionId", session_id)
                    continue

                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                if not cwd:
                    cwd = rec.get("cwd")

                if t == "user" and not rec.get("isMeta"):
                    msg = _safe_parse(rec.get("message", {}))
                    text = _extract_text(msg.get("content", ""))
                    if text and len(text) > 5 and not text.startswith("<"):
                        message_count += 1
                        if first_message is None:
                            first_message = text[:250]
                        messages.append(SessionMessage(
                            role="user",
                            content=text[:2000],
                            timestamp=ts,
                        ))

                elif t == "assistant":
                    msg = _safe_parse(rec.get("message", {}))
                    content_blocks = msg.get("content", [])
                    text_parts = []
                    for block in content_blocks:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            text_parts.append(block.get("text", ""))
                        elif btype == "tool_use":
                            tool_name = block.get("name", "")
                            inp = block.get("input", {})
                            if tool_name == "Agent":
                                desc = inp.get("description", "")
                                stype = inp.get("subagent_type", "general-purpose")
                                agent_spawns.append(AgentSpawn(
                                    description=desc[:200],
                                    subagent_type=stype,
                                ))
                                messages.append(SessionMessage(
                                    role="agent_spawn",
                                    content=desc[:400],
                                    tool_name=stype,
                                    timestamp=ts,
                                ))
                            else:
                                # Other tool calls
                                inp_preview = json.dumps(inp)[:200]
                                messages.append(SessionMessage(
                                    role="tool_use",
                                    content=inp_preview,
                                    tool_name=tool_name,
                                    timestamp=ts,
                                ))

                    combined = "\n".join(p for p in text_parts if p.strip())
                    if combined.strip():
                        messages.append(SessionMessage(
                            role="assistant",
                            content=combined[:3000],
                            timestamp=ts,
                        ))

    except Exception as e:
        logger.warning(f"[sessions] detail parse failed {jsonl_path}: {e}")
        return None

    return SessionDetail(
        id=session_id,
        project_dir=project_dir,
        project_path=_decode_project_path(project_dir),
        title=title or session_id[:8],
        cwd=cwd,
        started_at=first_ts,
        last_active=last_ts,
        message_count=message_count,
        agent_spawn_count=len(agent_spawns),
        first_message=first_message,
        agent_spawns=agent_spawns,
        messages=messages,
        resume_command=f"claude --resume {session_id}",
    )


# ── endpoints ─────────────────────────────────────────────────────────────

@router.get("/", response_model=list[SessionSummary])
async def list_sessions(limit: int = 100):
    """List all Claude Code sessions across all projects, sorted by last active."""
    projects_path = _projects_dir()
    if not projects_path.exists():
        return []

    summaries: list[SessionSummary] = []
    for project_dir in sorted(projects_path.iterdir()):
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            s = _parse_session_summary(jsonl_file, project_dir.name)
            if s:
                summaries.append(s)

    # Sort by last_active descending
    summaries.sort(key=lambda s: s.last_active or "", reverse=True)
    return summaries[:limit]


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """Full session detail with all messages and agent spawns."""
    jsonl = _find_session_file(session_id)
    if not jsonl:
        raise HTTPException(404, f"Session '{session_id}' not found")

    project_dir = jsonl.parent.name
    detail = _parse_session_detail(jsonl, project_dir)
    if not detail:
        raise HTTPException(500, f"Failed to parse session '{session_id}'")
    return detail
