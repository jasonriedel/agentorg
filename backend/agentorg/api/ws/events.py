import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from ...core.event_bus import get_event_bus
from ...database import AsyncSessionLocal
from ...models.event import RunEvent
from ...models.run import Run

router = APIRouter()


@router.websocket("/ws/runs/{run_id}/events")
async def stream_run_events(websocket: WebSocket, run_id: str):
    await websocket.accept()
    bus = get_event_bus()
    queue = bus.subscribe(run_id)

    try:
        # Replay existing events so reconnecting clients see the full history
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(RunEvent)
                .where(RunEvent.run_id == run_id)
                .order_by(RunEvent.created_at)
            )
            for event in result.scalars():
                await websocket.send_json({
                    "id": event.id,
                    "run_id": event.run_id,
                    "task_id": event.task_id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "created_at": event.created_at.isoformat(),
                })

        # Stream new events as they arrive
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                await websocket.send_json(event.to_dict())
            except asyncio.TimeoutError:
                await websocket.send_json({"event_type": "ping"})

    except WebSocketDisconnect:
        pass
    finally:
        bus.unsubscribe(run_id, queue)
