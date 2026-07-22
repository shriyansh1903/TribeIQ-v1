from src.repositories.base_repository import BaseRepository
from typing import Dict, Any, List, Optional
from datetime import datetime

class ExternalEventRepository(BaseRepository):
    def __init__(self):
        super().__init__("external_events")

    def find_by_event_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"id": event_id})
        except Exception:
            return None

    def upsert_external_event(self, event_data: Dict[str, Any]) -> bool:
        if self.collection is None:
            return False
        try:
            event_id = event_data.get("id")
            if not event_id:
                return False
            self.collection.update_one(
                {"id": event_id},
                {"$set": event_data},
                upsert=True
            )
            return True
        except Exception:
            return False

# Standby/Compatibility Repositories (To prevent other modules from breaking)
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
        return None

class ProcessedWebhookRepository(BaseRepository):
    def __init__(self):
        super().__init__("processed_webhooks")

    def is_processed(self, webhook_id: str) -> bool:
        return False

    def mark_as_processed(self, webhook_id: str, action: str, api_url: str) -> None:
        pass
