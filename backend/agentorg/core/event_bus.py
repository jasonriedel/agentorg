import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RunEvent:
    run_id: str
    event_type: str
    payload: dict
    task_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def emit(self, event: RunEvent) -> None:
        for queue in list(self._subscribers.get(event.run_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow consumer — drop event rather than block

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=500)
        self._subscribers[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(run_id, [])
        try:
            subs.remove(queue)
        except ValueError:
            pass


# Module-level singleton — safe for single-process uvicorn
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
