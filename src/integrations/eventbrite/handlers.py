from datetime import datetime
from typing import Dict, Any
from src.config import logger
from src.integrations.eventbrite.client import EventbriteClient
from src.integrations.eventbrite.repository import (
    EventbriteEventRepository, EventbriteAttendeeRepository, EventbriteOrderRepository
)
from src.services.child_services import calendar_service, external_event_service

class EventbriteWebhookHandlers:
    def __init__(self):
        self.client = EventbriteClient()
        self.event_repo = EventbriteEventRepository()
        self.attendee_repo = EventbriteAttendeeRepository()
        self.order_repo = EventbriteOrderRepository()

    def handle_event_published(self, api_url: str) -> None:
        logger.info(f"Handling event.published from URL: {api_url}")
        try:
            data = self.client.get(api_url)
            if "error" in data:
                logger.error(f"Failed to fetch event data from Eventbrite: {data}")
                return
                
            event_id = data.get("id")
            event_doc = {
                "id": event_id,
                "name": data.get("name", {}).get("text", "Eventbrite Event"),
                "description": data.get("description", {}).get("text", ""),
                "start_date": data.get("start", {}).get("utc"),
                "end_date": data.get("end", {}).get("utc"),
                "status": "published",
                "url": data.get("url"),
                "capacity": data.get("capacity", 100),
                "category": "Tech Conferences",
                "city": "Pune",
                "venue_id": data.get("venue_id"),
                "updated_at": datetime.utcnow().isoformat()
            }
            # Update MongoDB Eventbrite specific collection
            self.event_repo.collection.update_one({"id": event_id}, {"$set": event_doc}, upsert=True)
            
            # Sync to Community Calendar
            start_dt = data.get("start", {}).get("utc", "")
            calendar_date = start_dt.split("T")[0] if "T" in start_dt else start_dt
            
            calendar_doc = {
                "Event ID": f"EB-{event_id}",
                "Event Name": event_doc["name"],
                "Category": event_doc["category"],
                "Date": calendar_date,
                "Time": start_dt.split("T")[1][:5] if "T" in start_dt else "18:00",
                "Status": "Approved",
                "Event Type": "Major",
                "Notes": "Synchronized from Eventbrite.",
                "Predicted Attendance": 50,
                "Expected Occupancy Impact": 85.0,
                "Recommendation Score": 90.0,
                "Recommended Date": calendar_date
            }
            calendar_service.save_calendar_event(calendar_doc)
            logger.info(f"Eventbrite Event '{event_id}' successfully synchronized to Community Calendar.")
            
            # Sync to External Events Catalogue (Shared service interface)
            external_event_doc = {
                "Event ID": f"EB-{event_id}",
                "Event Name": event_doc["name"],
                "Category": event_doc["category"],
                "Description": event_doc["description"],
                "City": event_doc["city"],
                "Area": "Viman Nagar",
                "Latitude": 18.5204,
                "Longitude": 73.8567,
                "Property Radius (km)": 5.0,
                "Start Date": calendar_date,
                "End Date": calendar_date,
                "Expected Footfall": event_doc["capacity"],
                "Target Audience": "Tech Professionals, Students",
                "Organizer": "Eventbrite",
                "Venue": event_doc["venue_id"] or "Eventbrite Venue",
                "Website": event_doc["url"],
                "Registration Link": event_doc["url"],
                "Free/Paid": "Paid",
                "Estimated Popularity": "High",
                "Expected Occupancy Impact": 10.0,
                "Expected Community Impact": "High",
                "Tags": "eventbrite, tech, external",
                "Status": "Active",
                "Created By": "Eventbrite Integration",
                "Last Updated": datetime.utcnow().isoformat()
            }
            external_event_service.save_external_event(external_event_doc)
            logger.info(f"Eventbrite Event '{event_id}' successfully synchronized to External Events Catalogue.")
            
        except Exception as e:
            logger.error(f"Error handling event.published: {str(e)}")

    def handle_event_updated(self, api_url: str) -> None:
        logger.info(f"Handling event.updated from URL: {api_url}")
        self.handle_event_published(api_url)  # Handled identically by fetching resource and upserting

    def handle_event_unpublished(self, api_url: str) -> None:
        logger.info(f"Handling event.unpublished from URL: {api_url}")
        try:
            event_id = api_url.split("/events/")[-1].split("/")[0]
            self.event_repo.collection.update_one({"id": event_id}, {"$set": {"status": "unpublished"}})
            
            # Remove from Community Calendar and External Events via Services
            calendar_service.delete_calendar_event(f"EB-{event_id}")
            external_event_service.delete_external_event(f"EB-{event_id}")
            logger.info(f"Eventbrite Event '{event_id}' set to unpublished and removed from services.")
        except Exception as e:
            logger.error(f"Error handling event.unpublished: {str(e)}")

    def handle_order_placed(self, api_url: str) -> None:
        logger.info(f"Handling order.placed from URL: {api_url}")
        try:
            data = self.client.get(api_url)
            if "error" in data:
                return
            order_id = data.get("id")
            order_doc = {
                "id": order_id,
                "event_id": data.get("event_id"),
                "email": data.get("email"),
                "name": data.get("name"),
                "amount_paid": float(data.get("costs", {}).get("gross", {}).get("value", 0.0)) / 100.0,
                "currency": data.get("costs", {}).get("gross", {}).get("currency", "INR"),
                "created_at": data.get("created"),
                "status": "Placed",
                "updated_at": datetime.utcnow().isoformat()
            }
            self.order_repo.collection.update_one({"id": order_id}, {"$set": order_doc}, upsert=True)
            logger.info(f"Eventbrite Order '{order_id}' processed.")
        except Exception as e:
            logger.error(f"Error handling order.placed: {str(e)}")

    def handle_attendee_updated(self, api_url: str) -> None:
        logger.info(f"Handling attendee.updated from URL: {api_url}")
        try:
            data = self.client.get(api_url)
            if "error" in data:
                return
            attendee_id = data.get("id")
            attendee_doc = {
                "id": attendee_id,
                "event_id": data.get("event_id"),
                "order_id": data.get("order_id"),
                "name": data.get("profile", {}).get("name", ""),
                "email": data.get("profile", {}).get("email", ""),
                "ticket_class_name": data.get("ticket_class_name", "General Admission"),
                "created_at": data.get("created"),
                "status": "Attending" if not data.get("cancelled") else "Cancelled",
                "checked_in": data.get("checked_in", False),
                "updated_at": datetime.utcnow().isoformat()
            }
            self.attendee_repo.collection.update_one({"id": attendee_id}, {"$set": attendee_doc}, upsert=True)
            logger.info(f"Eventbrite Attendee '{attendee_id}' updated.")
        except Exception as e:
            logger.error(f"Error handling attendee.updated: {str(e)}")
