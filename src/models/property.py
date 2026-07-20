from pydantic import BaseModel, Field

class Property(BaseModel):
    property_id: str = Field(alias="Property ID")
    property_name: str = Field(alias="Property Name")
    property_type: str = Field(alias="Property Type")
    city: str = Field(alias="City")
    capacity: int = Field(alias="Capacity")
    status: str = Field("Active", alias="Status")

    class Config:
        populate_by_name = True
