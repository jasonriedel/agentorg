"""Polls GitHub for merged soul PRs and syncs local soul files + DB records."""
import asyncio
import logging
from pathlib import Path

from github import Github, GithubException
from sqlalchemy import select

from ..config import settings
from ..core.soul_manager import SoulManager
from ..database import AsyncSessionLocal
from ..models.agent import Agent, SoulVersion

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 60  # seconds
_SOUL_BRANCH_PREFIX = "soul/"


class SoulSyncService:
    def __init__(self):
        self._running = False
        self._seen_prs: set[int] = set()

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._poll_loop())
        logger.info("[soul_sync] started")

    async def stop(self) -> None:
        self._running = False

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._sync()
            except Exception as e:
                logger.warning(f"[soul_sync] poll error: {e}")
            await asyncio.sleep(_POLL_INTERVAL)

    async def _sync(self) -> None:
        loop = asyncio.get_event_loop()
        merged_prs = await loop.run_in_executor(None, self._fetch_merged_soul_prs)
        for pr in merged_prs:
            if pr["number"] not in self._seen_prs:
                await self._apply_soul_pr(pr)
                self._seen_prs.add(pr["number"])

    def _fetch_merged_soul_prs(self) -> list[dict]:
        """Return recently merged PRs whose head branch starts with 'soul/'."""
        try:
            gh = Github(settings.github_token)
            repo = gh.get_repo(settings.github_repo)
            results = []
            for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
                if pr.merged and pr.head.ref.startswith(_SOUL_BRANCH_PREFIX):
                    results.append({
                        "number": pr.number,
                        "head_branch": pr.head.ref,
                        "merge_commit_sha": pr.merge_commit_sha,
                        "url": pr.html_url,
                    })
                # Only scan the 20 most recent closed PRs
                if len(results) >= 20:
                    break
            return results
        except GithubException as e:
            logger.warning(f"[soul_sync] GitHub error: {e}")
            return []

    async def _apply_soul_pr(self, pr: dict) -> None:
        """Download the merged soul file and update DB + local disk."""
        branch = pr["head_branch"]
        # branch format: soul/{slug}/run-{id}
        parts = branch.split("/")
        if len(parts) < 2:
            return
        slug = parts[1]

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, self._download_soul_file, slug, pr["merge_commit_sha"])
        if not content:
            return

        # Write to local disk
        soul_path = Path(settings.souls_dir) / f"{slug}.soul.md"
        soul_path.write_text(content, encoding="utf-8")

        # Invalidate soul manager cache
        SoulManager(settings.souls_dir).invalidate(slug)

        # Update DB
        await self._upsert_soul_version(slug, content, pr["merge_commit_sha"], pr["url"])
        logger.info(f"[soul_sync] applied soul PR #{pr['number']} for '{slug}'")

    def _download_soul_file(self, slug: str, commit_sha: str) -> str | None:
        try:
            gh = Github(settings.github_token)
            repo = gh.get_repo(settings.github_repo)
            file_content = repo.get_contents(f"souls/{slug}.soul.md", ref=commit_sha)
            return file_content.decoded_content.decode("utf-8")
        except GithubException as e:
            logger.warning(f"[soul_sync] failed to download souls/{slug}.soul.md: {e}")
            return None

    async def _upsert_soul_version(self, slug: str, soul_md: str, commit_sha: str, pr_url: str) -> None:
        async with AsyncSessionLocal() as db:
            agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
            if not agent:
                return

            # Deactivate prior versions
            existing_versions = (await db.execute(
                select(SoulVersion).where(SoulVersion.agent_id == agent.id, SoulVersion.is_active.is_(True))
            )).scalars().all()
            for sv in existing_versions:
                sv.is_active = False

            import frontmatter
            meta = frontmatter.loads(soul_md).metadata
            version = str(meta.get("version", "1.0.0"))

            new_version = SoulVersion(
                agent_id=agent.id,
                version=version,
                soul_md=soul_md,
                commit_sha=commit_sha,
                pr_url=pr_url,
                is_active=True,
            )
            db.add(new_version)
            agent.current_soul_version = version
            await db.commit()


_service: SoulSyncService | None = None


def get_soul_sync_service() -> SoulSyncService:
    global _service
    if _service is None:
        _service = SoulSyncService()
    return _service
