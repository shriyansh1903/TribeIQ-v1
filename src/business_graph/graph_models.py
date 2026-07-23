from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class GraphNode(BaseModel):
    node_id: str = Field(alias="Node ID")
    entity_type: str = Field(alias="Entity Type")
    name: str = Field(alias="Name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="Metadata")

    class Config:
        populate_by_name = True
        extra = "allow"


class GraphEdge(BaseModel):
    edge_id: Optional[str] = Field(None, alias="Edge ID")
    source_id: str = Field(alias="Source ID")
    source_type: str = Field(alias="Source Type")
    relationship: str = Field(alias="Relationship")
    target_id: str = Field(alias="Target ID")
    target_type: str = Field(alias="Target Type")
    weight: Optional[float] = Field(1.0, alias="Weight")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="Metadata")
    created_at: Optional[str] = Field(None, alias="Created At")

    class Config:
        populate_by_name = True
        extra = "allow"
