import asyncio
from dataclasses import dataclass


@dataclass
class GateResolution:
    action: str  # "approved" or "rejected"
    feedback: str | None = None


class GateManager:
    def __init__(self):
        self._events: dict[str, asyncio.Event] = {}
        self._resolutions: dict[str, GateResolution] = {}

    def create(self, gate_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[gate_id] = event
        return event

    async def wait(self, gate_id: str) -> GateResolution:
        event = self._events.get(gate_id)
        if event is None:
            raise KeyError(f"Gate '{gate_id}' not found")
        await event.wait()
        return self._resolutions[gate_id]

    def resolve(self, gate_id: str, action: str, feedback: str | None = None) -> bool:
        event = self._events.get(gate_id)
        if event is None or event.is_set():
            return False
        self._resolutions[gate_id] = GateResolution(action=action, feedback=feedback)
        event.set()
        return True

    def is_pending(self, gate_id: str) -> bool:
        event = self._events.get(gate_id)
        return event is not None and not event.is_set()


_manager: GateManager | None = None


def get_gate_manager() -> GateManager:
    global _manager
    if _manager is None:
        _manager = GateManager()
    return _manager
