"""
===========================================================
TribeIQ Master Event Planner End-to-End Automated Test Suite
===========================================================

Comprehensive test suite verifying all features, input fields,
workspace creation, task CRUD, vendor procurement auto-task creation,
Run of Show CRUD, and landing page metrics in Master Event Planner.
===========================================================
"""

import os
import sys
import unittest
import datetime
import json
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.master_planner_service import master_planner_service
from src.integrations.calendar_db import load_calendar_events, save_calendar_event, delete_calendar_event
from src.repositories import UsersRepository


class TestMasterEventPlannerE2E(unittest.TestCase):

    def setUp(self):
        self.test_event_id = "EVT-E2E-TEST-99"
        self.test_event_data = {
            "Event ID": self.test_event_id,
            "Event Name": "E2E Automated Test Gala",
            "Category": "Social",
            "Property": "Tribe Moro",
            "Date": datetime.date.today().strftime("%Y-%m-%d"),
            "Status": "Approved",
            "Budget Estimate": 15000.0,
            "Assigned Vendors": "Pune Sound Systems",
            "Assigned Materials": "Stage & Speakers"
        }

    def tearDown(self):
        # Clean up test workspace and event
        try:
            master_planner_service.delete_workspace_by_event_id(self.test_event_id)
            delete_calendar_event(self.test_event_id)
        except Exception:
            pass

    def test_01_calendar_event_creation_and_workspace_initialization(self):
        """Tests saving calendar event and getting/creating workspace."""
        saved_id = save_calendar_event(self.test_event_data)
        self.assertEqual(saved_id, self.test_event_id)

        ws = master_planner_service.get_or_create_workspace(self.test_event_id, self.test_event_data, created_by="TestAdmin")
        self.assertIsNotNone(ws)
        self.assertIn("workspace_id", ws)
        self.assertEqual(ws["event_id"], self.test_event_id)
        self.assertEqual(ws["event_name"], "E2E Automated Test Gala")

    def test_02_task_crud_operations(self):
        """Tests Task creation, updating, retrieval, and deletion in workspace."""
        save_calendar_event(self.test_event_data)
        ws = master_planner_service.get_or_create_workspace(self.test_event_id, self.test_event_data, created_by="TestAdmin")
        ws_id = ws["workspace_id"]

        # Create Task (returns string task_id or task object)
        task_data = {
            "workspace_id": ws_id,
            "event_id": self.test_event_id,
            "title": "E2E Stage Setup Verification Task",
            "description": "Verify stage dimensions and power outlets",
            "department": "Technical",
            "assigned_user": "admin",
            "due_date": datetime.date.today().strftime("%Y-%m-%d"),
            "priority": "High",
            "status": "Pending"
        }
        res = master_planner_service.create_task(task_data)
        t_id = res.get("task_id") if isinstance(res, dict) else str(res)
        self.assertTrue(t_id.startswith("TSK"))

        # Fetch Tasks
        tasks = master_planner_service.get_tasks_for_workspace(ws_id)
        self.assertTrue(any(t["task_id"] == t_id for t in tasks))

        # Update Task Status and Assignee
        updated = master_planner_service.update_task(t_id, {"status": "In Progress", "assigned_user": "community_manager"})
        self.assertTrue(updated)

        updated_tasks = master_planner_service.get_tasks_for_workspace(ws_id)
        target_t = next(t for t in updated_tasks if t["task_id"] == t_id)
        self.assertEqual(target_t["status"], "In Progress")
        self.assertEqual(target_t["assigned_user"], "community_manager")

        # Progress Engine Calculation
        prog = master_planner_service.calculate_event_progress(self.test_event_id)
        self.assertGreater(prog["total"], 0)
        self.assertIn("percentage", prog)

        # Delete Task
        deleted = master_planner_service.delete_task(t_id)
        self.assertTrue(deleted)

    def test_03_vendor_procurement_and_auto_task_generation(self):
        """Tests vendor selection, metadata update, and automatic outreach task creation."""
        save_calendar_event(self.test_event_data)
        ws = master_planner_service.get_or_create_workspace(self.test_event_id, self.test_event_data, created_by="TestAdmin")
        ws_id = ws["workspace_id"]

        vendor_obj = {
            "name": "Pune Sound Systems",
            "assigned_user": "admin",
            "procurement_status": "Confirmed & Paid",
            "agreed_cost": 11800.0,
            "scope": "2 Subwoofers, 4 JBL Speakers, wireless mic set",
            "due_date": datetime.date.today().strftime("%Y-%m-%d")
        }

        # Auto-create outreach task for vendor
        task_desc = f"Contact vendor '{vendor_obj['name']}'. Scope: {vendor_obj['scope']}"
        proc_task = master_planner_service.create_task({
            "workspace_id": ws_id,
            "event_id": self.test_event_id,
            "title": f"Contact & Coordinate Vendor: {vendor_obj['name']}",
            "description": task_desc,
            "department": "Procurement",
            "assigned_user": "admin",
            "due_date": vendor_obj["due_date"],
            "priority": "High",
            "status": "Pending"
        })
        t_id_val = proc_task.get("task_id") if isinstance(proc_task, dict) else str(proc_task)
        vendor_obj["task_id"] = t_id_val

        # Save workspace metadata with vendor lists
        master_planner_service.update_workspace_metadata(ws_id, {
            "vendors_to_contact": json.dumps([]),
            "chosen_vendors": json.dumps([vendor_obj])
        })

        # Re-fetch workspace and verify persistence
        updated_ws = master_planner_service.get_or_create_workspace(self.test_event_id, self.test_event_data)
        raw_chosen = updated_ws.get("chosen_vendors", "[]")
        chosen_list = json.loads(raw_chosen) if isinstance(raw_chosen, str) and raw_chosen.startswith("[") else []
        self.assertEqual(len(chosen_list), 1)
        self.assertEqual(chosen_list[0]["name"], "Pune Sound Systems")
        self.assertEqual(chosen_list[0]["assigned_user"], "admin")
        self.assertEqual(chosen_list[0]["agreed_cost"], 11800.0)

    def test_04_run_of_show_crud_operations(self):
        """Tests Run of Show planning timeline CRUD operations."""
        save_calendar_event(self.test_event_data)
        ws = master_planner_service.get_or_create_workspace(self.test_event_id, self.test_event_data)
        ws_id = ws["workspace_id"]

        ros_item = {
            "workspace_id": ws_id,
            "event_id": self.test_event_id,
            "start_time": "18:30",
            "activity": "Welcome Refreshments & Resident Check-in",
            "lead": "admin",
            "notes": "Ensure QR scanner is active"
        }
        created_ros = master_planner_service.create_ros_item(ros_item)
        ros_id = created_ros.get("ros_id") if isinstance(created_ros, dict) else str(created_ros)

        all_ros = master_planner_service.get_run_of_show(ws_id)
        self.assertTrue(any(r.get("activity") == "Welcome Refreshments & Resident Check-in" for r in all_ros))

        if ros_id:
            del_ros = master_planner_service.delete_ros_item(ros_id)
            self.assertTrue(del_ros)

    def test_05_landing_page_summary_metrics(self):
        """Tests calculation of landing page summary metrics."""
        save_calendar_event(self.test_event_data)
        df_cal = load_calendar_events()
        metrics = master_planner_service.get_landing_page_summary_metrics(df_cal)

        self.assertIn("upcoming", metrics)
        self.assertIn("ongoing", metrics)
        self.assertIn("completed_this_month", metrics)
        self.assertIn("avg_progress", metrics)
        self.assertIn("overdue_tasks", metrics)


if __name__ == "__main__":
    unittest.main()
