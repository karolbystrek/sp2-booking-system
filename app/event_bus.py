from collections import defaultdict
from typing import Callable

EventHandler = Callable[[dict], None]


class EventBus:
    """In-process event bus implementing the Mediator pattern."""

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler):
        self._handlers[event_type].append(handler)

    def publish(self, event_type: str, payload: dict):
        for handler in self._handlers[event_type]:
            handler(payload)


event_bus = EventBus()
