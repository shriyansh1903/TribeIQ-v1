from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class Task(BaseModel):
    task_id: Optional[str] = Field(None, alias="Task ID")
    workspace_id: str = Field(alias="Workspace ID")
    event_id: str = Field(alias="Event ID")
    title: str = Field(alias="Title")
    description: Optional[str] = Field("", alias="Description")
    department: str = Field("Operations", alias="Department")
    assigned_user: str = Field("Unassigned", alias="Assigned User")
    due_date: str = Field(alias="Due Date")
    priority: str = Field("Medium", alias="Priority")
    status: str = Field("Pending", alias="Status")
    created_at: Optional[str] = Field(None, alias="Created At")

    class Config:
        populate_by_name = True
        extra = "allow"


class EventWorkspace(BaseModel):
    workspace_id: str = Field(alias="Workspace ID")
    event_id: str = Field(alias="Event ID")
    event_name: str = Field(alias="Event Name")
    category: str = Field("Social", alias="Category")
    property_name: str = Field("All Properties", alias="Property")
    date: str = Field(alias="Date")
    created_by: str = Field("System", alias="Created By")
    created_at: str = Field(alias="Created On")
    last_updated: str = Field(alias="Last Updated")
    status: str = Field("Approved", alias="Status")
    completion_percentage: float = Field(0.0, alias="Completion %")
    event_type: str = Field("Minor", alias="Event Type")
    community_manager: str = Field("Community Manager", alias="Community Manager")

    class Config:
        populate_by_name = True
        extra = "allow"


class RunOfShow(BaseModel):
    ros_id: Optional[str] = Field(None, alias="ROS ID")
    workspace_id: str = Field(alias="Workspace ID")
    event_id: str = Field(alias="Event ID")
    start_time: str = Field("18:00", alias="Start Time")
    activity: str = Field(alias="Activity")
    lead: str = Field("Manager", alias="Lead")
    notes: Optional[str] = Field("", alias="Notes")

    class Config:
        populate_by_name = True
        extra = "allow"
