from src.repositories.base_repository import BaseRepository
from typing import Dict, Any, List, Optional
from datetime import datetime

class EventbriteEventRepository(BaseRepository):
    def __init__(self):
        super().__init__("eventbrite_events")

    def find_by_event_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"id": event_id})
        except Exception:
            return None

class EventbriteAttendeeRepository(BaseRepository):
    def __init__(self):
        super().__init__("eventbrite_attendees")

    def find_by_attendee_id(self, attendee_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"id": attendee_id})
        except Exception:
            return None

class EventbriteOrderRepository(BaseRepository):
    def __init__(self):
        super().__init__("eventbrite_orders")

    def find_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"id": order_id})
        except Exception:
            return None

class EventbriteWebhookRepository(BaseRepository):
    def __init__(self):
        super().__init__("eventbrite_webhooks")

    def find_by_api_url(self, api_url: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"api_url": api_url})
        except Exception:
            return None

class ProcessedWebhookRepository(BaseRepository):
    def __init__(self):
        super().__init__("processed_webhooks")

    def is_processed(self, webhook_id: str) -> bool:
        if self.collection is None:
            return False
        try:
            doc = self.collection.find_one({"webhook_id": webhook_id})
            return doc is not None
        except Exception:
            return False

    def mark_as_processed(self, webhook_id: str, action: str, api_url: str) -> None:
        if self.collection is None:
            return
        try:
            self.collection.insert_one({
                "webhook_id": webhook_id,
                "action": action,
                "api_url": api_url,
                "processed_at": datetime.utcnow() if "datetime" in globals() else None
            })
        except Exception:
            pass
