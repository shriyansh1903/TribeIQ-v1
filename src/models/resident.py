from pydantic import BaseModel, Field
from typing import Optional

class Resident(BaseModel):
    resident_id: str = Field(alias="Resident ID")
    user_id: Optional[str] = Field(None, alias="User ID")
    booking_id: Optional[str] = Field(None, alias="Booking ID")
    name: str = Field(alias="Name")
    phone: Optional[str] = Field(None, alias="Phone")
    email: Optional[str] = Field(None, alias="Email")
    gender: Optional[str] = Field(None, alias="Gender")
    resident_type: Optional[str] = Field("Student", alias="Type")
    status: str = Field("Approved", alias="Status")
    property_name: str = Field(alias="Property")
    room_type: Optional[str] = Field(None, alias="Room Type")
    room: Optional[str] = Field(None, alias="Room")
    move_in_date: Optional[str] = Field(None, alias="Move In Date")
    move_out_date: Optional[str] = Field(None, alias="Move Out Date")

    class Config:
        populate_by_name = True
