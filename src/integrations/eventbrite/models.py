from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class EventbriteWebhookPayload(BaseModel):
    api_url: str
    action: str
    config: Optional[Dict[str, Any]] = None

class EventbriteEventModel(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    status: str
    url: Optional[str] = None
    capacity: int = 100
    category: Optional[str] = "Tech Conferences"
    city: Optional[str] = "Pune"
    venue: Optional[str] = None
    organizer: Optional[str] = None

class EventbriteAttendeeModel(BaseModel):
    id: str
    event_id: str
    order_id: str
    name: str
    email: EmailStr
    ticket_class_name: str
    created_at: datetime
    status: str = "Attending"  # Attending, Cancelled, Checked-In

class EventbriteOrderModel(BaseModel):
    id: str
    event_id: str
    email: EmailStr
    name: str
    amount_paid: float = 0.0
    currency: str = "INR"
    created_at: datetime
    status: str = "Placed"
