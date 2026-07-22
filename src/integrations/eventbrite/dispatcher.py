from typing import Dict, Any, Callable
from src.config import logger
from src.integrations.eventbrite.handlers import EventbriteWebhookHandlers

class EventbriteWebhookDispatcher:
    def __init__(self):
        self.handlers = EventbriteWebhookHandlers()
        # Direct action mapping
        self.route_map: Dict[str, Callable[[str], None]] = {
            "event.published": self.handlers.handle_event_published,
            "event.updated": self.handlers.handle_event_updated,
            "event.published": self.handlers.handle_event_published,
            "event.unpublished": self.handlers.handle_event_unpublished,
            "order.placed": self.handlers.handle_order_placed,
            "attendee.updated": self.handlers.handle_attendee_updated
        }

    def dispatch(self, action: str, api_url: str) -> bool:
        """
        Dispatches a webhook action to the registered handler.
        """
        handler = self.route_map.get(action)
        if handler:
            try:
                logger.info(f"Dispatching action '{action}' to handler...")
                handler(api_url)
                return True
            except Exception as e:
                logger.error(f"Error executing handler for action '{action}': {str(e)}")
                return False
        else:
            logger.warning(f"No handler registered for Eventbrite action: {action}")
            return False
