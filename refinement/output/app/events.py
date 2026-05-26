import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Any], Any]]] = {}

    def subscribe(self, event_type: str, listener: Callable[[Any], Any]):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            logger.info(f"Subscribed listener to event: {event_type}")

    async def publish(self, event_type: str, data: Any):
        logger.info(f"Publishing event {event_type}")
        if event_type not in self._listeners:
            return
        
        tasks = []
        for listener in self._listeners[event_type]:
            if asyncio.iscoroutinefunction(listener):
                tasks.append(asyncio.create_task(listener(data)))
            else:
                try:
                    listener(data)
                except Exception as e:
                    logger.error(f"Error running sync listener for {event_type}: {e}", exc_info=True)
        
        if tasks:
            # Gather tasks and handle exceptions gracefully to prevent blocking publishers
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error running async listener for {event_type}: {res}", exc_info=res)

event_bus = EventBus()
