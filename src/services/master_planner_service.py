import json
import uuid
import datetime
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.database import db_manager
from src.config import logger
from src.repositories import (
    EventWorkspacesRepository, TasksRepository, RunOfShowRepository
)
from src.models import Task, EventWorkspace, RunOfShow

TEMPLATES_JSON_PATH = Path(__file__).resolve().parents[1] / "intelligence" / "task_templates" / "default_templates.json"
WORKSPACES_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "event_workspaces.csv"
TASKS_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "tasks.csv"
RUN_OF_SHOW_CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "run_of_show.csv"

# ===========================================================
# Static Cache for Task Templates (Task 12 Performance Review)
# ===========================================================
@lru_cache(maxsize=1)
def load_task_templates_cached() -> Dict[str, List[Dict[str, Any]]]:
    """Caches static task templates JSON in memory to prevent repeated file read I/O."""
    if TEMPLATES_JSON_PATH.exists():
        try:
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading task templates JSON: {e}")
    return {}


class MasterPlannerService:
    """Single Orchestration Service for Master Event Planner Business Operations."""

    def __init__(self):
        self.workspace_repo = EventWorkspacesRepository()
        self.task_repo = TasksRepository()
        self.ros_repo = RunOfShowRepository()

    # ===========================================================
    # Dynamic Department Sourcing (Task 1)
    # ===========================================================
    def get_available_departments(self) -> List[str]:
        """Dynamically fetches department list from Master Data / User Management or system configuration."""
        departments = set(["Operations", "Logistics", "Technical", "Procurement", "Marketing", "Engagement", "Sports", "Health & Safety", "IT & Infra"])
        try:
            from src.integrations.master_data_db import get_vendor_categories_df, get_material_categories_df
            df_vc = get_vendor_categories_df()
            if not df_vc.empty and "Category" in df_vc.columns:
                departments.update([str(c).strip() for c in df_vc["Category"].dropna().unique()])
            df_mc = get_material_categories_df()
            if not df_mc.empty and "Category" in df_mc.columns:
                departments.update([str(c).strip() for c in df_mc["Category"].dropna().unique()])
        except Exception as e:
            logger.error(f"Notice fetching dynamic departments: {e}")

        return sorted([d for d in departments if d])

    # ===========================================================
    # Task Templates & Deep-Copy Template Cloning (Task 2)
    # ===========================================================
    def get_template_tasks_for_category(self, category: str) -> List[Dict[str, Any]]:
        """Retrieves and deep-copies template tasks based on category without altering source templates."""
        templates = load_task_templates_cached()
        matched_tasks = templates.get("Default", [])
        
        if category in templates:
            matched_tasks = templates[category]
        else:
            for cat, tasks in templates.items():
                if cat.lower() in category.lower() or category.lower() in cat.lower():
                    matched_tasks = tasks
                    break

        # Deep-copy to prevent any shared object mutation
        return [dict(t) for t in matched_tasks]

    # ===========================================================
    # Workspace Operations & Metadata Auto-Sync (Task 3 & 4)
    # ===========================================================
    def get_or_create_workspace(self, event_id: str, event_dict: Dict[str, Any], created_by: str = "System") -> Dict[str, Any]:
        """Finds existing event workspace or initializes a new workspace and clones AI task template."""
        event_id = str(event_id).strip()
        
        # 1. MongoDB Query
        if db_manager.ping_check():
            try:
                ws = self.workspace_repo.find_by_event_id(event_id)
                if ws:
                    ws["_id"] = str(ws["_id"])
                    return ws
            except Exception as e:
                logger.error(f"Error querying workspace in Mongo: {e}")

        # 2. CSV Query
        if WORKSPACES_CSV_PATH.exists():
            try:
                df_ws = pd.read_csv(WORKSPACES_CSV_PATH)
                if not df_ws.empty and "event_id" in df_ws.columns:
                    matched = df_ws[df_ws["event_id"].astype(str) == event_id]
                    if not matched.empty:
                        return matched.iloc[0].to_dict()
            except Exception as e:
                logger.error(f"Error reading workspace CSV: {e}")

        # 3. Create New Event Workspace instance
        workspace_id = f"WS-{uuid.uuid4().hex[:8].upper()}"
        now_str = datetime.datetime.now().isoformat()
        category = event_dict.get("Category", "Social")
        event_name = event_dict.get("Event Name", "Approved Event")
        property_name = event_dict.get("Property", "All Properties")
        event_date = event_dict.get("Date", datetime.date.today().strftime("%Y-%m-%d"))

        # Pydantic Model Validation
        workspace_model = EventWorkspace(
            workspace_id=workspace_id,
            event_id=event_id,
            event_name=event_name,
            category=category,
            property_name=property_name,
            date=event_date,
            created_by=created_by,
            created_at=now_str,
            last_updated=now_str,
            status=event_dict.get("Status", "Approved"),
            completion_percentage=0.0,
            event_type=event_dict.get("Event Type", "Minor"),
            community_manager=created_by if created_by != "System" else "Community Manager"
        )
        new_ws = workspace_model.model_dump(by_alias=False)

        # Persist Workspace
        if db_manager.ping_check():
            try:
                self.workspace_repo.insert(new_ws)
            except Exception as e:
                logger.error(f"Error saving workspace to Mongo: {e}")

        self._save_workspace_csv(new_ws)

        # Automatic Business Graph Relationship Builder
        try:
            from src.business_graph.business_graph_service import business_graph_service
            business_graph_service.link_event_to_property(event_id, property_name)
        except Exception as e_bg:
            logger.error(f"Business Graph linkage notice: {e_bg}")


        # 4. Task Template Cloning & Task Ownership Assignment (Task 2 & AI Intelligence Enrichment)
        try:
            from src.intelligence.event_planning_ai import event_planning_ai
            summary = event_planning_ai.generate_planning_summary(event_name, category, property_name, event_date)
            new_ws["planning_summary"] = summary
        except Exception as e_sum:
            logger.error(f"Error attaching planning summary: {e_sum}")

        template_tasks = self.get_template_tasks_for_category(category)
        for t_spec in template_tasks:
            raw_task = {
                "workspace_id": workspace_id,
                "event_id": event_id,
                "title": t_spec.get("title", "Untitled Task"),
                "description": t_spec.get("description", ""),
                "department": t_spec.get("department", "Operations"),
                "assigned_user": "Unassigned",
                "due_date": event_date,
                "priority": t_spec.get("priority", "Medium"),
                "status": "Pending"
            }
            try:
                from src.intelligence.event_planning_ai import event_planning_ai
                raw_task = event_planning_ai.enrich_task_with_intelligence(raw_task, event_date)
            except Exception:
                pass

            self.create_task(raw_task)

        return new_ws

    def delete_workspace_by_event_id(self, event_id: str) -> bool:
        """Deletes workspace, associated tasks, and run-of-show items for an event ID."""
        event_id = str(event_id).strip()
        try:
            if db_manager.ping_check():
                ws = self.workspace_repo.find_by_event_id(event_id)
                if ws:
                    ws_id = ws.get("workspace_id")
                    self.workspace_repo.collection.delete_one({"event_id": event_id})
                    if ws_id:
                        self.task_repo.collection.delete_many({"workspace_id": ws_id})
                        self.ros_repo.collection.delete_many({"workspace_id": ws_id})

            if WORKSPACES_CSV_PATH.exists():
                try:
                    df = pd.read_csv(WORKSPACES_CSV_PATH)
                    if not df.empty and "event_id" in df.columns:
                        df = df[df["event_id"].astype(str) != event_id]
                        df.to_csv(WORKSPACES_CSV_PATH, index=False)
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error(f"Error deleting workspace for event_id {event_id}: {e}")
            return False

    def update_workspace_metadata(self, workspace_id: str, updates: Optional[Dict[str, Any]] = None):
        """Recalculates completion % & updates last_updated timestamp on task state changes."""
        if updates is None:
            updates = {}

        prog = self.calculate_event_progress_by_workspace(workspace_id)
        updates["completion_percentage"] = prog["percentage"]
        updates["last_updated"] = datetime.datetime.now().isoformat()

        if db_manager.ping_check():
            try:
                ws = self.workspace_repo.find_by_workspace_id(workspace_id)
                if ws and "_id" in ws:
                    self.workspace_repo.update(str(ws["_id"]), updates)
                else:
                    self.workspace_repo.collection.update_one({"workspace_id": workspace_id}, {"$set": updates})
            except Exception as e:
                logger.error(f"Error updating workspace metadata in Mongo: {e}")

        # Update CSV
        if WORKSPACES_CSV_PATH.exists():
            try:
                df = pd.read_csv(WORKSPACES_CSV_PATH)
                if not df.empty and "workspace_id" in df.columns:
                    idx = df.index[df["workspace_id"] == workspace_id].tolist()
                    if idx:
                        for k, v in updates.items():
                            df.loc[idx[0], k] = v
                        df.to_csv(WORKSPACES_CSV_PATH, index=False)
            except Exception as e:
                logger.error(f"Error updating workspace CSV: {e}")

    def _save_workspace_csv(self, ws_dict: Dict[str, Any]):
        try:
            if WORKSPACES_CSV_PATH.exists():
                df = pd.read_csv(WORKSPACES_CSV_PATH)
                df = pd.concat([df, pd.DataFrame([ws_dict])], ignore_index=True)
            else:
                df = pd.DataFrame([ws_dict])
            df.to_csv(WORKSPACES_CSV_PATH, index=False)
        except Exception as e:
            logger.error(f"Error saving workspace CSV: {e}")

    # ===========================================================
    # Task Operations & Ownership Scoping (Task 2 & 10)
    # ===========================================================
    def get_tasks_for_workspace(self, workspace_id: str) -> List[Dict[str, Any]]:
        if db_manager.ping_check():
            try:
                tasks = self.task_repo.find_by_workspace(workspace_id)
                for t in tasks:
                    t["_id"] = str(t["_id"])
                return tasks
            except Exception as e:
                logger.error(f"Error fetching tasks from Mongo: {e}")

        if TASKS_CSV_PATH.exists():
            try:
                df = pd.read_csv(TASKS_CSV_PATH)
                if not df.empty and "workspace_id" in df.columns:
                    matched = df[df["workspace_id"] == workspace_id]
                    return matched.to_dict(orient="records")
            except Exception as e:
                logger.error(f"Error reading tasks CSV: {e}")
        return []

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        if db_manager.ping_check():
            try:
                tasks = self.task_repo.find_all()
                for t in tasks:
                    t["_id"] = str(t["_id"])
                return tasks
            except Exception as e:
                logger.error(f"Error querying all tasks from Mongo: {e}")

        if TASKS_CSV_PATH.exists():
            try:
                df = pd.read_csv(TASKS_CSV_PATH)
                return df.to_dict(orient="records")
            except Exception:
                pass
        return []

    def create_task(self, task_dict: Dict[str, Any]) -> str:
        if "task_id" not in task_dict or not task_dict["task_id"]:
            task_dict["task_id"] = f"TSK-{uuid.uuid4().hex[:8].upper()}"
        if "created_at" not in task_dict:
            task_dict["created_at"] = datetime.datetime.now().isoformat()
        if "workspace_id" not in task_dict or not task_dict["workspace_id"]:
            task_dict["workspace_id"] = "GENERAL_OPERATIONS"
        if "event_id" not in task_dict or task_dict["event_id"] is None:
            task_dict["event_id"] = "GENERAL"

        # Validate with Task Pydantic Model
        try:
            task_model = Task(
                task_id=task_dict["task_id"],
                workspace_id=task_dict["workspace_id"],
                event_id=str(task_dict["event_id"]),
                title=task_dict.get("title", "Untitled Task"),
                description=task_dict.get("description", ""),
                department=task_dict.get("department", "Operations"),
                assigned_user=task_dict.get("assigned_user", "Unassigned"),
                due_date=task_dict.get("due_date", datetime.date.today().strftime("%Y-%m-%d")),
                priority=task_dict.get("priority", "Medium"),
                status=task_dict.get("status", "Pending"),
                created_at=task_dict["created_at"]
            )
            validated_task = task_model.model_dump(by_alias=False)
        except Exception as ve:
            logger.error(f"Task model validation notice: {ve}")
            validated_task = task_dict

        if db_manager.ping_check():
            try:
                self.task_repo.insert(validated_task)
            except Exception as e:
                logger.error(f"Error inserting task into Mongo: {e}")

        # CSV fallback
        try:
            if TASKS_CSV_PATH.exists():
                df = pd.read_csv(TASKS_CSV_PATH)
                df = pd.concat([df, pd.DataFrame([validated_task])], ignore_index=True)
            else:
                df = pd.DataFrame([validated_task])
            df.to_csv(TASKS_CSV_PATH, index=False)
        except Exception as e:
            logger.error(f"Error saving task CSV: {e}")

        # Update metadata
        ws_id = validated_task.get("workspace_id")
        if ws_id and ws_id != "GENERAL_OPERATIONS":
            self.update_workspace_metadata(ws_id)

        # Automatic Business Graph Relationship Builder
        try:
            from src.business_graph.business_graph_service import business_graph_service
            business_graph_service.link_task_to_user_and_dept(
                validated_task["task_id"],
                validated_task.get("assigned_user", "Unassigned"),
                validated_task.get("department", "Operations"),
                validated_task.get("event_id", "")
            )
        except Exception as e_bg:
            logger.error(f"Business Graph task linkage notice: {e_bg}")

        return validated_task["task_id"]


    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        workspace_id = None
        if db_manager.ping_check():
            try:
                t = self.task_repo.find_by_task_id(task_id)
                if t:
                    workspace_id = t.get("workspace_id")
                    self.task_repo.update(str(t["_id"]), updates)
            except Exception as e:
                logger.error(f"Error updating task in Mongo: {e}")

        if TASKS_CSV_PATH.exists():
            try:
                df = pd.read_csv(TASKS_CSV_PATH)
                if not df.empty and "task_id" in df.columns:
                    idx = df.index[df["task_id"] == task_id].tolist()
                    if idx:
                        workspace_id = df.loc[idx[0], "workspace_id"]
                        for k, v in updates.items():
                            df.loc[idx[0], k] = v
                        df.to_csv(TASKS_CSV_PATH, index=False)
            except Exception as e:
                logger.error(f"Error updating task CSV: {e}")

        if workspace_id and workspace_id != "GENERAL_OPERATIONS":
            self.update_workspace_metadata(workspace_id)
        return True

    def delete_task(self, task_id: str) -> bool:
        workspace_id = None
        if db_manager.ping_check():
            try:
                t = self.task_repo.find_by_task_id(task_id)
                if t:
                    workspace_id = t.get("workspace_id")
                    self.task_repo.delete(str(t["_id"]))
            except Exception as e:
                logger.error(f"Error deleting task in Mongo: {e}")

        if TASKS_CSV_PATH.exists():
            try:
                df = pd.read_csv(TASKS_CSV_PATH)
                if not df.empty and "task_id" in df.columns:
                    idx = df.index[df["task_id"] == task_id].tolist()
                    if idx:
                        workspace_id = df.loc[idx[0], "workspace_id"]
                        df = df[df["task_id"] != task_id]
                        df.to_csv(TASKS_CSV_PATH, index=False)
            except Exception as e:
                logger.error(f"Error deleting task CSV: {e}")

        if workspace_id and workspace_id != "GENERAL_OPERATIONS":
            self.update_workspace_metadata(workspace_id)
        return True

    # ===========================================================
    # Centralized Progress Engine (Task 5)
    # ===========================================================
    def calculate_event_progress_by_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Calculates progress metrics for a workspace."""
        tasks = self.get_tasks_for_workspace(workspace_id)
        total = len(tasks)
        if total == 0:
            return {
                "total": 0, "completed": 0, "pending": 0, "in_progress": 0,
                "percentage": 0.0, "status_summary": "No tasks created"
            }

        completed = sum(1 for t in tasks if str(t.get("status")).strip().lower() == "completed")
        in_prog = sum(1 for t in tasks if str(t.get("status")).strip().lower() == "in progress")
        pending = total - completed - in_prog
        pct = round((completed / total) * 100.0, 1)

        summary = f"{completed}/{total} Completed ({pct}%)"
        return {
            "total": total,
            "completed": completed,
            "in_progress": in_prog,
            "pending": pending,
            "percentage": pct,
            "status_summary": summary
        }

    def calculate_event_progress(self, event_id: str) -> Dict[str, Any]:
        """Calculates progress metrics for an event by event_id."""
        event_id = str(event_id).strip()
        ws = None
        if db_manager.ping_check():
            ws = self.workspace_repo.find_by_event_id(event_id)
            
        if not ws and WORKSPACES_CSV_PATH.exists():
            try:
                df = pd.read_csv(WORKSPACES_CSV_PATH)
                if not df.empty and "event_id" in df.columns:
                    matched = df[df["event_id"].astype(str) == event_id]
                    if not matched.empty:
                        ws = matched.iloc[0].to_dict()
            except Exception:
                pass

        if ws and "workspace_id" in ws:
            return self.calculate_event_progress_by_workspace(ws["workspace_id"])

        return {
            "total": 0, "completed": 0, "pending": 0, "in_progress": 0,
            "percentage": 0.0, "status_summary": "Workspace unavailable"
        }

    # ===========================================================
    # Landing Page Summary Metrics (Task 7)
    # ===========================================================
    def get_landing_page_summary_metrics(self, df_calendar: pd.DataFrame) -> Dict[str, Any]:
        """Calculates landing page metrics."""
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        curr_month_prefix = datetime.date.today().strftime("%Y-%m")

        upcoming_count = 0
        ongoing_count = 0
        completed_month_count = 0

        if not df_calendar.empty:
            date_col = "Date" if "Date" in df_calendar.columns else df_calendar.columns[0]
            status_col = "Status" if "Status" in df_calendar.columns else df_calendar.columns[-1]

            for _, row in df_calendar.iterrows():
                ev_date = str(row.get(date_col, ""))
                ev_status = str(row.get(status_col, ""))

                if ev_status == "Completed" or (ev_date.startswith(curr_month_prefix) and ev_status in ["Completed", "Finished"]):
                    completed_month_count += 1
                elif ev_date == today_str or ev_status == "In Progress":
                    ongoing_count += 1
                elif ev_date > today_str or ev_status in ["Approved", "Confirmed"]:
                    upcoming_count += 1

        all_tasks = self.get_all_tasks()
        overdue_count = 0
        for t in all_tasks:
            due = str(t.get("due_date", ""))
            stat = str(t.get("status", "")).strip().lower()
            if due and due < today_str and stat != "completed":
                overdue_count += 1

        # Average Progress
        total_tasks = len(all_tasks)
        completed_tasks = sum(1 for t in all_tasks if str(t.get("status")).strip().lower() == "completed")
        avg_progress = round((completed_tasks / total_tasks * 100.0), 1) if total_tasks > 0 else 0.0

        return {
            "upcoming": upcoming_count,
            "ongoing": ongoing_count,
            "completed_this_month": completed_month_count,
            "avg_progress": avg_progress,
            "overdue_tasks": overdue_count
        }

    # ===========================================================
    # Run of Show Operations (Task 9 & 10)
    # ===========================================================
    def get_run_of_show(self, workspace_id: str) -> List[Dict[str, Any]]:
        if db_manager.ping_check():
            try:
                items = self.ros_repo.find_by_workspace(workspace_id)
                for i in items:
                    i["_id"] = str(i["_id"])
                return items
            except Exception as e:
                logger.error(f"Error loading run_of_show from Mongo: {e}")

        if RUN_OF_SHOW_CSV_PATH.exists():
            try:
                df = pd.read_csv(RUN_OF_SHOW_CSV_PATH)
                if not df.empty and "workspace_id" in df.columns:
                    matched = df[df["workspace_id"] == workspace_id]
                    return matched.sort_values(by="start_time").to_dict(orient="records")
            except Exception:
                pass
        return []

    def create_ros_item(self, ros_dict: Dict[str, Any]) -> str:
        if "ros_id" not in ros_dict or not ros_dict["ros_id"]:
            ros_dict["ros_id"] = f"ROS-{uuid.uuid4().hex[:8].upper()}"

        try:
            ros_model = RunOfShow(
                ros_id=ros_dict["ros_id"],
                workspace_id=ros_dict["workspace_id"],
                event_id=str(ros_dict["event_id"]),
                start_time=ros_dict.get("start_time", "18:00"),
                activity=ros_dict.get("activity", "Activity"),
                lead=ros_dict.get("lead", "Manager"),
                notes=ros_dict.get("notes", "")
            )
            validated_ros = ros_model.model_dump(by_alias=False)
        except Exception as ve:
            logger.error(f"ROS validation notice: {ve}")
            validated_ros = ros_dict

        if db_manager.ping_check():
            try:
                self.ros_repo.insert(validated_ros)
            except Exception as e:
                logger.error(f"Error inserting ROS into Mongo: {e}")

        try:
            if RUN_OF_SHOW_CSV_PATH.exists():
                df = pd.read_csv(RUN_OF_SHOW_CSV_PATH)
                df = pd.concat([df, pd.DataFrame([validated_ros])], ignore_index=True)
            else:
                df = pd.DataFrame([validated_ros])
            df.to_csv(RUN_OF_SHOW_CSV_PATH, index=False)
        except Exception as e:
            logger.error(f"Error saving ROS CSV: {e}")

        return validated_ros["ros_id"]

    def update_ros_item(self, ros_id: str, updates: Dict[str, Any]) -> bool:
        if db_manager.ping_check():
            try:
                items = self.ros_repo.find_all({"ros_id": ros_id})
                if items:
                    self.ros_repo.update(str(items[0]["_id"]), updates)
            except Exception as e:
                logger.error(f"Error updating ROS in Mongo: {e}")

        if RUN_OF_SHOW_CSV_PATH.exists():
            try:
                df = pd.read_csv(RUN_OF_SHOW_CSV_PATH)
                if not df.empty and "ros_id" in df.columns:
                    idx = df.index[df["ros_id"] == ros_id].tolist()
                    if idx:
                        for k, v in updates.items():
                            df.loc[idx[0], k] = v
                        df.to_csv(RUN_OF_SHOW_CSV_PATH, index=False)
            except Exception as e:
                logger.error(f"Error updating ROS CSV: {e}")
        return True

    def delete_ros_item(self, ros_id: str) -> bool:
        if db_manager.ping_check():
            try:
                items = self.ros_repo.find_all({"ros_id": ros_id})
                if items:
                    self.ros_repo.delete(str(items[0]["_id"]))
            except Exception as e:
                logger.error(f"Error deleting ROS in Mongo: {e}")

        if RUN_OF_SHOW_CSV_PATH.exists():
            try:
                df = pd.read_csv(RUN_OF_SHOW_CSV_PATH)
                if not df.empty and "ros_id" in df.columns:
                    df = df[df["ros_id"] != ros_id]
                    df.to_csv(RUN_OF_SHOW_CSV_PATH, index=False)
            except Exception as e:
                logger.error(f"Error deleting ROS CSV: {e}")
        return True

master_planner_service = MasterPlannerService()
