from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class User(BaseModel):
    user_id: str = Field(alias="User ID")
    username: str
    password_hash: str
    email: Optional[EmailStr] = None
    role: str = "Read Only"
    status: str = "Active"

    class Config:
        populate_by_name = True
