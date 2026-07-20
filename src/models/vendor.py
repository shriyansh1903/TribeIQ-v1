from pydantic import BaseModel, Field
from typing import Optional

class Vendor(BaseModel):
    vendor_id: str = Field(alias="Vendor ID")
    vendor_name: str = Field(alias="Vendor Name")
    vendor_category: str = Field(alias="Vendor Category")
    contact_person: Optional[str] = Field(None, alias="Contact Person")
    phone_number: Optional[str] = Field(None, alias="Phone Number")
    email_address: Optional[str] = Field(None, alias="Email Address")
    active_status: str = Field("Active", alias="Active / Inactive Status")
    base_amount: float = Field(0.0, alias="Base Amount")
    final_cost: float = Field(0.0, alias="Final Cost")

    class Config:
        populate_by_name = True
