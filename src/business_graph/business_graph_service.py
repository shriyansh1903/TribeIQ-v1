import datetime
import uuid
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.database import db_manager
from src.config import logger
from src.business_graph.business_graph_repository import BusinessGraphRepository
from src.business_graph.graph_models import GraphEdge

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRAPH_CSV_PATH = PROJECT_ROOT / "data" / "business_graph_edges.csv"


class BusinessGraphService:
    """
    Centralized Business Graph Relationship & Intelligence Engine.
    Connects business entities (Residents, Events, Properties, Departments, Users,
    Tasks, Vendors, Materials, Recommendations, Budgets, Feedback, Categories)
    and exposes cross-module context aggregation APIs.
    """

    def __init__(self):
        self.repo = BusinessGraphRepository()

    # ===========================================================
    # RELATIONSHIP BUILDERS & PERSISTENCE
    # ===========================================================
    def add_relationship(
        self,
        source_id: str,
        source_type: str,
        relationship: str,
        target_id: str,
        target_type: str,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Adds or updates a deterministic relationship edge between two entities."""
        source_id = str(source_id).strip()
        target_id = str(target_id).strip()
        edge_id = f"EDGE-{source_id}-{relationship}-{target_id}".replace(" ", "_")
        now_str = datetime.datetime.now().isoformat()

        edge_data = {
            "edge_id": edge_id,
            "source_id": source_id,
            "source_type": source_type,
            "relationship": relationship,
            "target_id": target_id,
            "target_type": target_type,
            "weight": weight,
            "metadata": metadata or {},
            "created_at": now_str
        }

        # Model validation
        try:
            edge_model = GraphEdge(**edge_data)
            validated_edge = edge_model.model_dump(by_alias=False)
        except Exception as ve:
            logger.error(f"Graph edge validation notice: {ve}")
            validated_edge = edge_data

        # Persist to MongoDB
        if db_manager.ping_check():
            try:
                existing = self.repo.find_by_edge_id(edge_id)
                if existing:
                    self.repo.update(str(existing["_id"]), validated_edge)
                else:
                    self.repo.insert(validated_edge)
            except Exception as e:
                logger.error(f"Error persisting graph edge to Mongo: {e}")

        # Persist CSV fallback
        self._save_edge_csv(validated_edge)

        return edge_id

    def _save_edge_csv(self, edge_dict: Dict[str, Any]):
        """Saves edge to CSV fallback."""
        try:
            if GRAPH_CSV_PATH.exists():
                df = pd.read_csv(GRAPH_CSV_PATH)
                if not df.empty and "edge_id" in df.columns:
                    df = df[df["edge_id"] != edge_dict["edge_id"]]
                df = pd.concat([df, pd.DataFrame([edge_dict])], ignore_index=True)
            else:
                df = pd.DataFrame([edge_dict])
            df.to_csv(GRAPH_CSV_PATH, index=False)
        except Exception as e:
            logger.error(f"Error saving graph edge CSV: {e}")

    # ===========================================================
    # AUTOMATIC EVENT-DRIVEN GRAPH BUILDERS
    # ===========================================================
    def link_event_to_property(self, event_id: str, property_name: str):
        """Builds CONDUCTED_AT relationship."""
        self.add_relationship(event_id, "Event", "CONDUCTED_AT", property_name, "Property")

    def link_task_to_user_and_dept(self, task_id: str, assigned_user: str, department: str, event_id: str):
        """Builds ASSIGNED_TO, BELONGS_TO, and HAS_TASK relationships."""
        self.add_relationship(task_id, "Task", "BELONGS_TO_EVENT", event_id, "Event")
        if assigned_user and assigned_user.lower() != "unassigned":
            self.add_relationship(task_id, "Task", "ASSIGNED_TO", assigned_user, "User")
        if department:
            self.add_relationship(task_id, "Task", "BELONGS_TO_DEPT", department, "Department")

    def link_vendor_to_event(self, vendor_name: str, event_id: str, category: str = ""):
        """Builds SUPPORTED relationship."""
        self.add_relationship(vendor_name, "Vendor", "SUPPORTED", event_id, "Event", metadata={"category": category})

    def link_material_to_event(self, material_name: str, event_id: str):
        """Builds USED_IN relationship."""
        self.add_relationship(material_name, "Material", "USED_IN", event_id, "Event")

    def link_recommendation_to_event(self, recommendation_id: str, event_id: str):
        """Builds CREATED relationship."""
        self.add_relationship(recommendation_id, "Recommendation", "CREATED", event_id, "Event")

    def link_resident_attendance_and_feedback(self, resident_id: str, event_id: str, rating: float = 5.0):
        """Builds ATTENDED and GAVE_FEEDBACK relationships."""
        self.add_relationship(resident_id, "Resident", "ATTENDED", event_id, "Event")
        self.add_relationship(resident_id, "Resident", "GAVE_FEEDBACK", event_id, "Event", weight=rating)

    # ===========================================================
    # QUERY CAPABILITIES
    # ===========================================================
    def query_relationships(
        self,
        source_id: Optional[str] = None,
        relationship: Optional[str] = None,
        target_id: Optional[str] = None,
        source_type: Optional[str] = None,
        target_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries graph relationship edges based on dynamic filter criteria."""
        query_filter = {}
        if source_id: query_filter["source_id"] = str(source_id)
        if relationship: query_filter["relationship"] = relationship
        if target_id: query_filter["target_id"] = str(target_id)
        if source_type: query_filter["source_type"] = source_type
        if target_type: query_filter["target_type"] = target_type

        if db_manager.ping_check():
            try:
                edges = self.repo.find_relationships(query_filter)
                for e in edges:
                    e["_id"] = str(e["_id"])
                return edges
            except Exception as e:
                logger.error(f"Error querying graph edges from Mongo: {e}")

        # CSV Fallback
        if GRAPH_CSV_PATH.exists():
            try:
                df = pd.read_csv(GRAPH_CSV_PATH)
                if not df.empty:
                    for k, v in query_filter.items():
                        if k in df.columns:
                            df = df[df[k].astype(str) == str(v)]
                    return df.to_dict(orient="records")
            except Exception as e:
                logger.error(f"Error reading graph edges CSV: {e}")
        return []

    # ===========================================================
    # CROSS-MODULE CONTEXT AGGREGATION APIS
    # ===========================================================
    def get_event_context(self, event_id: str) -> Dict[str, Any]:
        """Aggregates all connected graph context for an event."""
        event_id = str(event_id).strip()
        edges_out = self.query_relationships(source_id=event_id)
        edges_in = self.query_relationships(target_id=event_id)

        vendors = [e["source_id"] for e in edges_in if e["relationship"] == "SUPPORTED"]
        materials = [e["source_id"] for e in edges_in if e["relationship"] == "USED_IN"]
        attendees = [e["source_id"] for e in edges_in if e["relationship"] == "ATTENDED"]
        tasks = [e["source_id"] for e in edges_in if e["relationship"] == "BELONGS_TO_EVENT"]
        properties = [e["target_id"] for e in edges_out if e["relationship"] == "CONDUCTED_AT"]

        return {
            "event_id": event_id,
            "property": properties[0] if properties else "N/A",
            "vendors_linked": list(set(vendors)),
            "materials_linked": list(set(materials)),
            "attendees_count": len(set(attendees)),
            "tasks_count": len(tasks)
        }

    def get_property_context(self, property_name: str) -> Dict[str, Any]:
        """Aggregates connected events and history by property."""
        property_name = str(property_name).strip()
        edges = self.query_relationships(target_id=property_name, relationship="CONDUCTED_AT")
        events_conducted = [e["source_id"] for e in edges]

        return {
            "property_name": property_name,
            "events_conducted_count": len(events_conducted),
            "events_list": events_conducted
        }

    def get_resident_context(self, resident_id: str) -> Dict[str, Any]:
        """Aggregates resident event attendance and feedback history."""
        resident_id = str(resident_id).strip()
        edges_attended = self.query_relationships(source_id=resident_id, relationship="ATTENDED")
        edges_feedback = self.query_relationships(source_id=resident_id, relationship="GAVE_FEEDBACK")

        events_attended = [e["target_id"] for e in edges_attended]
        avg_rating = 0.0
        if edges_feedback:
            avg_rating = round(sum(float(e.get("weight", 5.0)) for e in edges_feedback) / len(edges_feedback), 2)

        return {
            "resident_id": resident_id,
            "events_attended_count": len(events_attended),
            "events_attended": events_attended,
            "average_feedback_given": avg_rating
        }

    def get_vendor_context(self, vendor_name: str) -> Dict[str, Any]:
        """Aggregates vendor event support history."""
        vendor_name = str(vendor_name).strip()
        edges = self.query_relationships(source_id=vendor_name, relationship="SUPPORTED")
        events_supported = [e["target_id"] for e in edges]

        return {
            "vendor_name": vendor_name,
            "events_supported_count": len(events_supported),
            "events_supported": events_supported
        }

    def get_department_context(self, department_name: str) -> Dict[str, Any]:
        """Aggregates tasks and workload for a department."""
        department_name = str(department_name).strip()
        edges = self.query_relationships(target_id=department_name, relationship="BELONGS_TO_DEPT")
        tasks = [e["source_id"] for e in edges]

        return {
            "department_name": department_name,
            "total_tasks_assigned": len(tasks),
            "tasks_list": tasks
        }

business_graph_service = BusinessGraphService()
