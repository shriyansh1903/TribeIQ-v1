"""
===========================================================
TribeIQ Executive Analytics & Operational Intelligence Core
===========================================================

Deterministic, rule-based aggregation engine surfacing executive KPIs,
performance metrics, department & user workloads, budget variance,
recommendation success feedback, health scores, trends, and intelligent alerts.
===========================================================
"""

import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.database import db_manager
from src.config import logger
from src.repositories import (
    EventsRepository, CalendarEventsRepository, RecommendationsRepository,
    EventWorkspacesRepository, TasksRepository, PropertiesRepository, UsersRepository
)
from src.services.master_planner_service import master_planner_service

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVENT_HISTORY_CSV = PROJECT_ROOT / "data" / "event_history.csv"
CALENDAR_CSV = PROJECT_ROOT / "data" / "planned_calendar.csv"
RECOMMENDATIONS_CSV = PROJECT_ROOT / "data" / "recommendation_history.csv"


class ExecutiveAnalyticsService:
    def __init__(self):
        self.events_repo = EventsRepository()
        self.calendar_repo = CalendarEventsRepository()
        self.recs_repo = RecommendationsRepository()
        self.workspaces_repo = EventWorkspacesRepository()
        self.tasks_repo = TasksRepository()
        self.props_repo = PropertiesRepository()
        self.users_repo = UsersRepository()

    # ===========================================================
    # DATA INGESTION & AGGREGATION HELPERS
    # ===========================================================
    def _load_history_df(self) -> pd.DataFrame:
        """Loads historical event logs (MongoDB with CSV fallback), strictly excluding unlogged recommendation stubs."""
        df = pd.DataFrame()
        if db_manager.ping_check():
            try:
                docs = self.events_repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
            except Exception as e:
                logger.error(f"Error loading events from Mongo: {e}")

        if df.empty and EVENT_HISTORY_CSV.exists():
            try:
                df = pd.read_csv(EVENT_HISTORY_CSV)
            except Exception:
                df = pd.DataFrame()

        if not df.empty and "Notes" in df.columns:
            df = df[~df["Notes"].astype(str).str.contains("Approved directly from Smart Recommendations", case=False, na=False)].copy()

        return df

    def _load_calendar_df(self) -> pd.DataFrame:
        """Loads calendar events dataframe."""
        if db_manager.ping_check():
            try:
                docs = self.calendar_repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error loading calendar events from Mongo: {e}")

        if CALENDAR_CSV.exists():
            try:
                return pd.read_csv(CALENDAR_CSV)
            except Exception:
                pass
        return pd.DataFrame()

    def _load_recommendations_df(self) -> pd.DataFrame:
        """Loads recommendation history log dataframe."""
        if db_manager.ping_check():
            try:
                docs = self.recs_repo.find_all()
                if docs:
                    df = pd.DataFrame(docs)
                    if "_id" in df.columns:
                        df = df.drop(columns=["_id"])
                    return df
            except Exception as e:
                logger.error(f"Error loading recommendations from Mongo: {e}")

        if RECOMMENDATIONS_CSV.exists():
            try:
                return pd.read_csv(RECOMMENDATIONS_CSV)
            except Exception:
                pass
        return pd.DataFrame()

    # ===========================================================
    # SECTION 1 — Executive Overview Dashboard KPIs
    # ===========================================================
    def get_executive_kpis(self) -> Dict[str, Any]:
        """Surfaces top-level executive KPIs with month-over-month comparisons."""
        df_cal = self._load_calendar_df()
        df_hist = self._load_history_df()
        df_recs = self._load_recommendations_df()
        all_tasks = master_planner_service.get_all_tasks()

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        curr_month = datetime.date.today().strftime("%Y-%m")
        prev_month = (datetime.date.today().replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")

        # 1. Events This Month
        events_this_month = 0
        events_prev_month = 0
        if not df_cal.empty:
            date_col = "Date" if "Date" in df_cal.columns else df_cal.columns[0]
            df_cal["month_str"] = df_cal[date_col].astype(str).str.slice(0, 7)
            events_this_month = len(df_cal[df_cal["month_str"] == curr_month])
            events_prev_month = len(df_cal[df_cal["month_str"] == prev_month])

        events_delta = events_this_month - events_prev_month

        # 2. Event Completion Rate
        total_sched = len(df_cal) if not df_cal.empty else 1
        completed_count = len(df_cal[df_cal.get("Status", "").isin(["Completed", "Finished"])]) if not df_cal.empty else 0
        completion_rate = round((completed_count / max(1, total_sched)) * 100.0, 1)

        # 3. Recommendation Acceptance Rate
        recs_generated = len(df_recs) if not df_recs.empty else 1
        recs_approved = len(df_recs[df_recs.get("Status", "").isin(["Approved", "Scheduled", "Completed"])]) if not df_recs.empty else 0
        acceptance_rate = round((recs_approved / max(1, recs_generated)) * 100.0, 1)

        # 4. Average Attendance & 5. Rating
        avg_attendance = 0.0
        avg_rating = 0.0
        if not df_hist.empty:
            att_col = "Actual Attendance" if "Actual Attendance" in df_hist.columns else ("Attendance" if "Attendance" in df_hist.columns else None)
            rate_col = "Average Feedback" if "Average Feedback" in df_hist.columns else ("Rating" if "Rating" in df_hist.columns else None)
            if att_col:
                avg_attendance = round(float(pd.to_numeric(df_hist[att_col], errors='coerce').fillna(0).mean()), 1)
            if rate_col:
                avg_rating = round(float(pd.to_numeric(df_hist[rate_col], errors='coerce').fillna(0).mean()), 2)

        # 6. Budget Utilization
        total_planned_budget = 0.0
        total_actual_spend = 0.0
        if not df_hist.empty:
            bp_col = "Budget Planned" if "Budget Planned" in df_hist.columns else ("Planned Budget" if "Planned Budget" in df_hist.columns else None)
            bs_col = "Budget Spent" if "Budget Spent" in df_hist.columns else ("Actual Budget" if "Actual Budget" in df_hist.columns else None)
            if bp_col:
                total_planned_budget = float(pd.to_numeric(df_hist[bp_col], errors='coerce').fillna(0).sum())
            if bs_col:
                total_actual_spend = float(pd.to_numeric(df_hist[bs_col], errors='coerce').fillna(0).sum())

        budget_utilization = round((total_actual_spend / max(1.0, total_planned_budget)) * 100.0, 1) if total_planned_budget > 0 else 100.0

        # 7. Overdue Tasks
        overdue_tasks = sum(1 for t in all_tasks if str(t.get("due_date", "")) < today_str and str(t.get("status", "")).strip().lower() != "completed")

        # 8. Best Performing Property
        best_prop = "N/A"
        if not df_hist.empty and "Property" in df_hist.columns:
            best_prop = str(df_hist["Property"].value_counts().idxmax())

        return {
            "events_this_month": events_this_month,
            "events_delta": events_delta,
            "completion_rate": completion_rate,
            "acceptance_rate": acceptance_rate,
            "avg_attendance": avg_attendance,
            "avg_rating": avg_rating,
            "budget_utilization": budget_utilization,
            "overdue_tasks": overdue_tasks,
            "best_property": best_prop
        }

    # ===========================================================
    # SECTION 2 — Event Performance Analytics
    # ===========================================================
    def get_event_performance_analytics(self) -> Dict[str, Any]:
        """Calculates top category performance, turnout trends, and ratings."""
        df_hist = self._load_history_df()
        if df_hist.empty:
            return {"by_category": pd.DataFrame(), "highest_events": pd.DataFrame(), "lowest_events": pd.DataFrame()}

        cat_col = "Category" if "Category" in df_hist.columns else df_hist.columns[0]
        att_col = "Actual Attendance" if "Actual Attendance" in df_hist.columns else ("Attendance" if "Attendance" in df_hist.columns else df_hist.columns[1])
        rate_col = "Average Feedback" if "Average Feedback" in df_hist.columns else ("Rating" if "Rating" in df_hist.columns else df_hist.columns[-1])

        df_hist[att_col] = pd.to_numeric(df_hist[att_col], errors='coerce').fillna(0)
        df_hist[rate_col] = pd.to_numeric(df_hist[rate_col], errors='coerce').fillna(0)

        by_cat = df_hist.groupby(cat_col).agg(
            total_events=(cat_col, "count"),
            avg_attendance=(att_col, "mean"),
            avg_rating=(rate_col, "mean")
        ).reset_index()

        by_cat["avg_attendance"] = by_cat["avg_attendance"].round(1)
        by_cat["avg_rating"] = by_cat["avg_rating"].round(2)

        highest = df_hist.sort_values(by=att_col, ascending=False).head(5)
        lowest = df_hist.sort_values(by=att_col, ascending=True).head(5)

        return {
            "by_category": by_cat,
            "highest_events": highest,
            "lowest_events": lowest
        }

    # ===========================================================
    # SECTION 3 — Property Performance Ranking
    # ===========================================================
    def get_property_performance_matrix(self) -> pd.DataFrame:
        """Ranks properties based on attendance, satisfaction, budget efficiency, and progress."""
        df_hist = self._load_history_df()
        if df_hist.empty or "Property" not in df_hist.columns:
            return pd.DataFrame()

        att_col = "Actual Attendance" if "Actual Attendance" in df_hist.columns else "Attendance"
        rate_col = "Average Feedback" if "Average Feedback" in df_hist.columns else "Rating"
        bp_col = "Budget Planned" if "Budget Planned" in df_hist.columns else "Planned Budget"

        df_hist[att_col] = pd.to_numeric(df_hist[att_col], errors='coerce').fillna(0)
        df_hist[rate_col] = pd.to_numeric(df_hist[rate_col], errors='coerce').fillna(0)
        df_hist[bp_col] = pd.to_numeric(df_hist[bp_col], errors='coerce').fillna(0)

        prop_df = df_hist.groupby("Property").agg(
            events_conducted=("Property", "count"),
            avg_attendance=(att_col, "mean"),
            resident_satisfaction=(rate_col, "mean"),
            avg_budget=(bp_col, "mean")
        ).reset_index()

        prop_df["avg_attendance"] = prop_df["avg_attendance"].round(1)
        prop_df["resident_satisfaction"] = prop_df["resident_satisfaction"].round(2)
        prop_df["avg_budget"] = prop_df["avg_budget"].round(0)

        # Deterministic Overall Property Score Formula
        # Overall Score = (Satisfaction * 15) + (Normalized Attendance * 0.25)
        prop_df["overall_score"] = ((prop_df["resident_satisfaction"] * 15) + (prop_df["avg_attendance"] * 0.3)).clip(0, 100).round(1)
        return prop_df.sort_values(by="overall_score", ascending=False)

    # ===========================================================
    # SECTION 4 — Department Performance
    # ===========================================================
    def get_department_performance(self) -> pd.DataFrame:
        """Aggregates departmental task completion, overdue rates, and productivity scores."""
        all_tasks = master_planner_service.get_all_tasks()
        if not all_tasks:
            return pd.DataFrame()

        df_tasks = pd.DataFrame(all_tasks)
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        dept_summary = []
        for dept_name, group in df_tasks.groupby("department"):
            total_assigned = len(group)
            completed = len(group[group["status"].astype(str).str.strip().str.lower() == "completed"])
            completion_pct = round((completed / total_assigned) * 100.0, 1)

            overdue = sum(1 for _, r in group.iterrows() if str(r.get("due_date", "")) < today_str and str(r.get("status", "")).strip().lower() != "completed")
            overdue_pct = round((overdue / total_assigned) * 100.0, 1)

            productivity_score = round(max(0, completion_pct - (overdue_pct * 0.5)), 1)
            dept_summary.append({
                "Department": dept_name,
                "Tasks Assigned": total_assigned,
                "Tasks Completed": completed,
                "Completion %": completion_pct,
                "Overdue %": overdue_pct,
                "Productivity Score": productivity_score
            })

        return pd.DataFrame(dept_summary).sort_values(by="Productivity Score", ascending=False)

    # ===========================================================
    # SECTION 5 — User Performance Summary (No Public Ranking)
    # ===========================================================
    def get_user_performance_summary(self) -> pd.DataFrame:
        """Surfaces user task contribution summaries without public competitive ranking."""
        all_tasks = master_planner_service.get_all_tasks()
        if not all_tasks:
            return pd.DataFrame()

        df_tasks = pd.DataFrame(all_tasks)
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        user_summary = []
        for user_name, group in df_tasks.groupby("assigned_user"):
            total = len(group)
            completed = len(group[group["status"].astype(str).str.strip().str.lower() == "completed"])
            pending = len(group[group["status"].astype(str).str.strip().str.lower() == "pending"])
            overdue = sum(1 for _, r in group.iterrows() if str(r.get("due_date", "")) < today_str and str(r.get("status", "")).strip().lower() != "completed")
            comp_rate = round((completed / total) * 100.0, 1)

            user_summary.append({
                "User": user_name,
                "Tasks Assigned": total,
                "Completed": completed,
                "Pending": pending,
                "Overdue": overdue,
                "Completion Rate %": comp_rate
            })

        return pd.DataFrame(user_summary)

    # ===========================================================
    # SECTION 7 — Budget Analytics
    # ===========================================================
    def get_budget_analytics(self) -> Dict[str, Any]:
        """Calculates planned vs actual spend, variance, and cost-per-attendee metrics."""
        df_hist = self._load_history_df()
        if df_hist.empty:
            return {"planned": 0.0, "actual": 0.0, "variance": 0.0, "cost_per_attendee": 0.0, "by_category": pd.DataFrame()}

        bp_col = "Budget Planned" if "Budget Planned" in df_hist.columns else "Planned Budget"
        bs_col = "Budget Spent" if "Budget Spent" in df_hist.columns else "Actual Budget"
        att_col = "Actual Attendance" if "Actual Attendance" in df_hist.columns else "Attendance"

        df_hist[bp_col] = pd.to_numeric(df_hist[bp_col], errors='coerce').fillna(0)
        df_hist[bs_col] = pd.to_numeric(df_hist[bs_col], errors='coerce').fillna(0)
        df_hist[att_col] = pd.to_numeric(df_hist[att_col], errors='coerce').fillna(0)

        planned = float(df_hist[bp_col].sum())
        actual = float(df_hist[bs_col].sum())
        variance = planned - actual

        total_att = float(df_hist[att_col].sum())
        cost_per_attendee = round(actual / max(1.0, total_att), 1)

        cat_budget = df_hist.groupby("Category").agg(
            planned_budget=(bp_col, "sum"),
            actual_spend=(bs_col, "sum")
        ).reset_index()

        return {
            "planned": planned,
            "actual": actual,
            "variance": variance,
            "cost_per_attendee": cost_per_attendee,
            "by_category": cat_budget
        }

    # ===========================================================
    # SECTION 8 — Recommendation Engine Performance
    # ===========================================================
    def get_recommendation_engine_performance(self) -> Dict[str, Any]:
        """Evaluates recommendation acceptance rates, approval ratios, and feedback quality."""
        df_recs = self._load_recommendations_df()
        if df_recs.empty:
            return {"generated": 0, "approved": 0, "rejected": 0, "success_rate": 0.0}

        generated = len(df_recs)
        status_col = "Status" if "Status" in df_recs.columns else df_recs.columns[-1]
        approved = len(df_recs[df_recs[status_col].astype(str).str.strip().isin(["Approved", "Confirmed", "Completed"])])
        rejected = generated - approved
        success_rate = round((approved / max(1, generated)) * 100.0, 1)

        return {
            "generated": generated,
            "approved": approved,
            "rejected": rejected,
            "success_rate": success_rate
        }

    # ===========================================================
    # SECTION 9 — Operational Health Score
    # ===========================================================
    def get_operational_health_score(self) -> Dict[str, Any]:
        """Calculates deterministic composite operational health score and recommendations."""
        kpis = self.get_executive_kpis()
        budget = self.get_budget_analytics()
        recs = self.get_recommendation_engine_performance()

        # Weighted Health Math
        completion_weight = kpis["completion_rate"] * 0.3
        satisfaction_weight = (kpis["avg_rating"] * 20.0) * 0.3
        recommendation_weight = recs["success_rate"] * 0.2
        budget_weight = min(100.0, max(0.0, 100.0 - abs(100.0 - kpis["budget_utilization"]))) * 0.2

        composite_score = round(completion_weight + satisfaction_weight + recommendation_weight + budget_weight, 1)

        confidence = "High" if kpis["events_this_month"] > 0 else "Medium"
        explanation = f"Calculated from Completion Rate ({kpis['completion_rate']}%), Satisfaction ({kpis['avg_rating']}/5), Rec Success ({recs['success_rate']}%), and Budget Discipline ({kpis['budget_utilization']}%)."

        recommendations = []
        if kpis["overdue_tasks"] > 3:
            recommendations.append("Clear overdue operational tasks in Master Event Planner to prevent execution delays.")
        if kpis["budget_utilization"] > 110.0:
            recommendations.append("Review material procurement spend to control budget overrun variance.")
        if recs["success_rate"] < 70.0:
            recommendations.append("Adjust smart recommendation parameters to improve manager acceptance rate.")

        if not recommendations:
            recommendations.append("Operations performing optimally across all properties.")

        return {
            "composite_score": composite_score,
            "confidence": confidence,
            "explanation": explanation,
            "contributing_factors": {
                "completion_component": round(completion_weight, 1),
                "satisfaction_component": round(satisfaction_weight, 1),
                "recommendation_component": round(recommendation_weight, 1),
                "budget_component": round(budget_weight, 1)
            },
            "recommendations": recommendations
        }

    # ===========================================================
    # SECTION 10 & 12 — AI Executive Insights & Intelligent Alerts
    # ===========================================================
    def get_executive_insights_and_alerts(self) -> Dict[str, Any]:
        """Generates deterministic rule-based executive insights and operational alerts."""
        kpis = self.get_executive_kpis()
        budget = self.get_budget_analytics()
        perf = self.get_event_performance_analytics()
        health = self.get_operational_health_score()

        insights = []
        alerts = []

        # Rule-Based Insights
        if kpis["avg_rating"] >= 4.5:
            insights.append({
                "statement": f"Resident satisfaction remains high with an average rating of {kpis['avg_rating']}/5.0.",
                "why": "Derived from positive resident feedback logs in recent event executions."
            })
        if not perf["by_category"].empty:
            top_cat = perf["by_category"].sort_values(by="avg_attendance", ascending=False).iloc[0]
            insights.append({
                "statement": f"'{top_cat['Category']}' events generate the highest resident attendance (avg {top_cat['avg_attendance']} turnouts).",
                "why": f"Evaluated against historic turnout data across {top_cat['total_events']} events."
            })

        # Rule-Based Alerts
        if kpis["overdue_tasks"] > 0:
            alerts.append({
                "severity": "WARNING",
                "message": f"⚠ {kpis['overdue_tasks']} tasks are overdue in Master Event Planner.",
                "action": "Open Master Event Planner to reassign or update task status."
            })
        if budget["variance"] < 0:
            alerts.append({
                "severity": "ALERT",
                "message": f"⚠ Budget spend exceeds planned allocation by ₹{abs(budget['variance']):,.0f}.",
                "action": "Review material procurement logs in Master Data."
            })
        if kpis["completion_rate"] < 70.0:
            alerts.append({
                "severity": "CRITICAL",
                "message": f"⚠ Event Completion Rate is currently at {kpis['completion_rate']}%.",
                "action": "Inspect property planning timelines."
            })

        if not alerts:
            alerts.append({
                "severity": "INFO",
                "message": "🟢 All operational metrics are operating within expected thresholds.",
                "action": "No immediate executive intervention required."
            })

        return {
            "insights": insights,
            "alerts": alerts
        }

executive_analytics_service = ExecutiveAnalyticsService()
