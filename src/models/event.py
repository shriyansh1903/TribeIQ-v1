from pydantic import BaseModel, Field
from typing import Optional

class Event(BaseModel):
    event_id: str = Field(alias="Event ID")
    event_name: str = Field(alias="Event Name")
    property_name: str = Field(alias="Property")
    category: str = Field(alias="Category")
    date: str = Field(alias="Date")
    time: Optional[str] = Field("18:00", alias="Time")
    status: str = Field("AI Recommended", alias="Status")
    event_type: str = Field("Minor", alias="Event Type")
    budget_estimate: float = Field(3000.0, alias="Budget Estimate")
    predicted_attendance: Optional[int] = Field(0, alias="Predicted Attendance")
    expected_occupancy: Optional[float] = Field(0.0, alias="Expected Occupancy")

    class Config:
        populate_by_name = True
