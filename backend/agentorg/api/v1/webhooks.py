"""GitHub webhook receiver — POST /webhooks/github"""
import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from sqlalchemy import select

from ...config import settings
from ...core.workflow_parser import parse_workflow
from ...database import AsyncSessionLocal
from ...models.run import Run
from ...models.workflow import Workflow
from ...services.trigger_service import _execute_run_bg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_signature(body: bytes, signature: str | None) -> bool:
    """Validate GitHub HMAC-SHA256 signature if a secret is configured."""
    if not settings.github_webhook_secret:
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
):
    body = await request.body()

    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(401, "Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    event = x_github_event or "unknown"
    action = payload.get("action", "")
    event_key = f"{event}.{action}" if action else event

    logger.info(f"[webhook] received event: {event_key}")

    # Find workflows with matching webhook triggers
    workflows_path = __import__("pathlib").Path(settings.workflows_dir)
    triggered = 0

    for yaml_file in sorted(workflows_path.glob("*.yaml")):
        try:
            wf_def = parse_workflow(yaml_file)
            for trigger in wf_def.triggers:
                if trigger.get("type") != "webhook":
                    continue
                trigger_cfg = trigger.get("config", {})
                events = trigger_cfg.get("events", [])
                if event_key not in events and event not in events:
                    continue

                # Build inputs from GitHub payload
                inputs = _extract_inputs(payload, event)
                await _create_and_fire(wf_def, inputs, background_tasks)
                triggered += 1
        except Exception as e:
            logger.warning(f"[webhook] skipped {yaml_file.name}: {e}")

    return {"received": event_key, "triggered": triggered}


def _extract_inputs(payload: dict, event: str) -> dict:
    """Pull useful fields out of common GitHub event payloads."""
    inputs: dict = {"github_event": event}
    if "pull_request" in payload:
        pr = payload["pull_request"]
        inputs["pr_url"] = pr.get("html_url", "")
        inputs["pr_title"] = pr.get("title", "")
        inputs["pr_branch"] = pr.get("head", {}).get("ref", "")
        inputs["feature_description"] = pr.get("body", "") or pr.get("title", "")
    if "repository" in payload:
        inputs["repo_full_name"] = payload["repository"].get("full_name", "")
    return inputs


async def _create_and_fire(wf_def, inputs: dict, background_tasks: BackgroundTasks) -> None:
    from pathlib import Path

    async with AsyncSessionLocal() as db:
        wf_row = (await db.execute(
            select(Workflow).where(Workflow.slug == wf_def.slug)
        )).scalar_one_or_none()
        if not wf_row:
            return

        run = Run(
            workflow_id=wf_row.id,
            workflow_slug=wf_def.slug,
            trigger="webhook",
            trigger_payload={"inputs": inputs},
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

    background_tasks.add_task(_execute_run_bg, run.id, wf_def)
    logger.info(f"[webhook] triggered '{wf_def.slug}' run={run.id[:8]}")
