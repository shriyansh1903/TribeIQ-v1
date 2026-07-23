import unittest
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.models import Task, EventWorkspace, RunOfShow
from src.services.master_planner_service import master_planner_service
from src.intelligence.event_planning_ai import event_planning_ai
from src.analytics.executive_analytics import executive_analytics_service
from src.business_graph.business_graph_service import business_graph_service

class TestTribeIQCoreEngine(unittest.TestCase):

    def test_pydantic_models_validation(self):
        """Validates Task, EventWorkspace, and RunOfShow models."""
        task = Task(
            task_id="TSK-TEST1",
            workspace_id="WS-TEST1",
            event_id="EVT-101",
            title="Test Task",
            department="Operations",
            assigned_user="TestUser",
            due_date="2026-08-01",
            priority="High",
            status="Pending"
        )
        self.assertEqual(task.task_id, "TSK-TEST1")
        self.assertEqual(task.department, "Operations")

        ws = EventWorkspace(
            workspace_id="WS-TEST1",
            event_id="EVT-101",
            event_name="Test Event",
            category="Social",
            property_name="Tribe Moro",
            date="2026-08-01",
            created_by="Admin",
            created_at="2026-07-23T10:00:00",
            last_updated="2026-07-23T10:00:00",
            status="Approved",
            completion_percentage=0.0,
            event_type="Minor",
            community_manager="Admin"
        )
        self.assertEqual(ws.workspace_id, "WS-TEST1")
        self.assertEqual(ws.property_name, "Tribe Moro")

    def test_master_planner_service_and_progress_engine(self):
        """Tests MasterPlannerService workspace initialization and progress engine."""
        ev_dict = {
            "Event ID": "EVT-TEST-999",
            "Event Name": "UnitTest Cultural Night",
            "Category": "Cultural",
            "Property": "Tribe Vara",
            "Date": "2026-08-15",
            "Status": "Approved"
        }
        ws = master_planner_service.get_or_create_workspace("EVT-TEST-999", ev_dict, created_by="TestAdmin")
        self.assertIsNotNone(ws["workspace_id"])
        self.assertEqual(ws["event_name"], "UnitTest Cultural Night")

        tasks = master_planner_service.get_tasks_for_workspace(ws["workspace_id"])
        self.assertGreater(len(tasks), 0)

        prog = master_planner_service.calculate_event_progress("EVT-TEST-999")
        self.assertIn("percentage", prog)
        self.assertIn("status_summary", prog)

    def test_ai_planning_assistant(self):
        """Tests AI Event Planning Assistant deterministic logic."""
        summary = event_planning_ai.generate_planning_summary("Test Festival", "Cultural", "Tribe Moro", "2026-08-20")
        self.assertIn("objective", summary)
        self.assertIn("recommended_budget_range", summary)

        resources = event_planning_ai.get_suggested_resources("Cultural")
        self.assertIn("vendors", resources)

        risks = event_planning_ai.get_risk_checklist("Cultural")
        self.assertGreater(len(risks), 0)

    def test_executive_analytics_service(self):
        """Tests Executive Analytics Service KPI generation and health scores."""
        kpis = executive_analytics_service.get_executive_kpis()
        self.assertIn("events_this_month", kpis)
        self.assertIn("completion_rate", kpis)

        health = executive_analytics_service.get_operational_health_score()
        self.assertIn("composite_score", health)
        self.assertIn("confidence", health)

    def test_business_graph_service(self):
        """Tests Business Graph relationship building and context aggregation."""
        edge_id = business_graph_service.add_relationship(
            source_id="RES-UNITTEST-01",
            source_type="Resident",
            relationship="ATTENDED",
            target_id="EVT-TEST-999",
            target_type="Event"
        )
        self.assertIsNotNone(edge_id)

        ctx = business_graph_service.get_event_context("EVT-TEST-999")
        self.assertEqual(ctx["event_id"], "EVT-TEST-999")

    def test_user_permissions_management(self):
        """Tests effective permission calculation for roles and custom permission overrides."""
        from src.auth.session_manager import get_user_effective_permissions, ALL_SYSTEM_PERMISSIONS
        
        admin_user = {"role": "Admin"}
        self.assertEqual(len(get_user_effective_permissions(admin_user)), len(ALL_SYSTEM_PERMISSIONS))

        custom_user = {"role": "Community Manager", "permissions": ["Dashboard", "Analytics"]}
        self.assertEqual(get_user_effective_permissions(custom_user), ["Dashboard", "Analytics"])

        role_default_user = {"role": "Read Only"}
        self.assertEqual(get_user_effective_permissions(role_default_user), ["Dashboard", "Community Calendar", "Settings"])

if __name__ == "__main__":
    unittest.main()
