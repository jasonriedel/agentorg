"""ChromaDB-backed vector search tool for cross-run memory retrieval."""
import logging
from pathlib import Path

from .registry import ToolDefinition
from ..config import settings

logger = logging.getLogger(__name__)

_COLLECTION = "task_outputs"
_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
        db_dir = Path(settings.database_url.replace("sqlite+aiosqlite:///", "")).parent / "chroma"
        db_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(db_dir))
        _collection = _client.get_or_create_collection(
            _COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        return _collection
    except Exception as e:
        logger.warning(f"[search_tools] ChromaDB unavailable: {e}")
        return None


def index_task_output(
    task_id: str,
    run_id: str,
    agent_slug: str,
    workflow_slug: str,
    content: str,
) -> None:
    """Called by the orchestrator after each completed task to index its output."""
    if not content or not content.strip():
        return
    col = _get_collection()
    if col is None:
        return
    try:
        # Truncate to ChromaDB's 8192-char document limit
        col.upsert(
            ids=[task_id],
            documents=[content[:8000]],
            metadatas=[{
                "run_id": run_id,
                "agent_slug": agent_slug,
                "workflow_slug": workflow_slug,
            }],
        )
    except Exception as e:
        logger.warning(f"[search_tools] index failed for task {task_id}: {e}")


def _vector_search(query: str, limit: int = 5, agent_slug: str = "", context=None) -> str:
    col = _get_collection()
    if col is None:
        return "Vector search unavailable (ChromaDB not initialized)."

    try:
        where = {"agent_slug": agent_slug} if agent_slug else None
        results = col.query(
            query_texts=[query],
            n_results=min(limit, col.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        if not docs:
            return "No relevant memories found."

        lines = [f"Found {len(docs)} relevant memory/memories:\n"]
        for doc, meta, dist in zip(docs, metas, dists):
            similarity = round(1 - dist, 3)
            lines.append(
                f"[similarity={similarity} | workflow={meta.get('workflow_slug')} | agent={meta.get('agent_slug')}]\n"
                f"{doc[:600]}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


VECTOR_SEARCH = ToolDefinition(
    name="vector_search",
    description=(
        "Search past task outputs and memories using semantic similarity. "
        "Useful for finding how similar problems were solved in previous runs."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "limit": {"type": "integer", "description": "Max results to return (default 5)", "default": 5},
            "agent_slug": {"type": "string", "description": "Filter to outputs from a specific agent (optional)"},
        },
        "required": ["query"],
    },
    handler=_vector_search,
)
