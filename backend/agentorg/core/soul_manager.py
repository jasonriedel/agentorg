from dataclasses import dataclass, field
from pathlib import Path

import frontmatter


@dataclass
class SoulDefinition:
    slug: str
    name: str
    version: str
    model: str
    max_tokens: int
    capabilities: list[str]
    system_prompt: str  # Markdown body with learnings appended (becomes the system prompt)
    self_improvement: dict
    cost_guardrails: dict
    raw_md: str  # original .soul.md content, used for soul PRs


class SoulManager:
    def __init__(self, souls_dir: str):
        self.souls_dir = Path(souls_dir)
        self._cache: dict[str, SoulDefinition] = {}

    def load(self, slug: str) -> SoulDefinition:
        if slug in self._cache:
            return self._cache[slug]
        soul = self._load_from_disk(slug)
        self._cache[slug] = soul
        return soul

    def invalidate(self, slug: str) -> None:
        self._cache.pop(slug, None)

    def list_slugs(self) -> list[str]:
        return [p.name.replace(".soul.md", "") for p in self.souls_dir.glob("*.soul.md")]

    def _load_from_disk(self, slug: str) -> SoulDefinition:
        soul_path = self.souls_dir / f"{slug}.soul.md"
        if not soul_path.exists():
            raise FileNotFoundError(f"Soul not found: {soul_path}")

        raw = soul_path.read_text(encoding="utf-8")
        post = frontmatter.loads(raw)
        meta = post.metadata
        body = post.content.strip()

        # Append learnings if they exist — these are injected before the cache breakpoint
        learnings_path = self.souls_dir / f"{slug}.learnings.md"
        if learnings_path.exists():
            learnings = learnings_path.read_text(encoding="utf-8").strip()
            if learnings:
                body = f"{body}\n\n## Learnings from Previous Runs\n\n{learnings}"

        return SoulDefinition(
            slug=slug,
            name=meta.get("id", slug),
            version=str(meta.get("version", "1.0.0")),
            model=meta.get("model", "claude-sonnet-4-6"),
            max_tokens=int(meta.get("max_tokens", 8192)),
            capabilities=meta.get("capabilities", []),
            system_prompt=body,
            self_improvement=meta.get("self_improvement", {}),
            cost_guardrails=meta.get("cost_guardrails", {}),
            raw_md=raw,
        )
