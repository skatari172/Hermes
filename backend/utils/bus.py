"""
Lightweight pub/sub message bus for agent communication.
Handles event routing between different agents in the system.
"""

import asyncio
from typing import Dict, List, Callable, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """Lightweight event bus for agent communication."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._middleware: List[Callable] = []
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event is emitted
        """
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Function to remove from subscribers
        """
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed {handler.__name__} from {event_type}")
    
    async def emit(self, event_type: str, data: Any = None):
        """
        Emit an event to all subscribers.
        
        Args:
            event_type: Type of event to emit
            data: Data to pass to event handlers
        """
        logger.debug(f"Emitting event {event_type} with data: {data}")
        
        # Apply middleware
        for middleware in self._middleware:
            data = await middleware(event_type, data)
        
        # Notify all subscribers
        handlers = self._subscribers.get(event_type, [])
        if handlers:
            tasks = []
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        tasks.append(handler(data))
                    else:
                        # Run sync handlers in thread pool
                        tasks.append(asyncio.get_event_loop().run_in_executor(None, handler, data))
                except Exception as e:
                    logger.error(f"Error in event handler {handler.__name__}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.debug(f"No subscribers for event {event_type}")
    
    def add_middleware(self, middleware: Callable):
        """
        Add middleware to process events before they reach subscribers.
        
        Args:
            middleware: Function that takes (event_type, data) and returns processed data
        """
        self._middleware.append(middleware)
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))
    
    def list_events(self) -> List[str]:
        """Get list of all event types with subscribers."""
        return list(self._subscribers.keys())
    
    def clear(self):
        """Clear all subscribers and middleware."""
        self._subscribers.clear()
        self._middleware.clear()
        logger.info("Event bus cleared")

# Global event bus instance
event_bus = EventBus()
