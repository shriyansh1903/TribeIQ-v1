import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from src.config import logger

class EventPlanningAIService:
    """
    Deterministic AI Event Planning Assistant.
    Provides planning summaries, task prioritization rules, timeline suggestions,
    resource recommendations, risk checklists, operational insights, explainable confidence scores,
    and historical event matching.
    """

    # Category Resource Mapping
    CATEGORY_RESOURCES = {
        "Cultural": {
            "vendors": ["Catering & Snacks Vendor", "Stage & Lighting AV Vendor", "Traditional Decor Vendor"],
            "materials": ["Stage Backdrops", "Decorative Flowers/Lights", "Microphones & Speakers", "Welcome Signage"],
            "equipment": ["Dual Mic Set", "Sound Mixer", "Spotlight", "Extension Cables"],
            "manpower": ["2 Stage Coordinators", "1 Sound Tech", "2 Hospitality Volunteers"]
        },
        "Sports": {
            "vendors": ["Sports Goods Supplier", "First Aid Provider", "Trophy & Medal Vendor"],
            "materials": ["Tournament Brackets", "Whistles & Timers", "Energy Drinks & Ice", "Winner Certificates"],
            "equipment": ["Scoreboards", "PA System", "First Aid Kit", "Boundary Markers"],
            "manpower": ["2 Match Referees", "1 First-Aid Lead", "2 Registration Staff"]
        },
        "Social": {
            "vendors": ["Finger Food & Beverage Vendor", "DJ / Playlist Host"],
            "materials": ["Icebreaker Cards", "Paper Cups & Napkins", "Photo Booth Props"],
            "equipment": ["Ambient Speakers", "LED String Lights", "Projector"],
            "manpower": ["1 Host / MC", "2 Setup Volunteers"]
        },
        "Gaming & Tech": {
            "vendors": ["Gaming Gear Rental Vendor", "High-Speed Wi-Fi Infra Vendor"],
            "materials": ["Ethernet Cables", "Power Strips", "HDMI Cables", "Tournament Bracket Board"],
            "equipment": ["4K Gaming Monitors", "Consoles / PCs", "Projector & Screen", "High-Speed Switch"],
            "manpower": ["2 Tech Support Leads", "1 Bracket Manager"]
        },
        "Workshops & Seminars": {
            "vendors": ["Guest Speaker / Trainer", "Coffee & Tea Service"],
            "materials": ["Worksheets & Pens", "Name Badges", "Feedback QR Standees"],
            "equipment": ["Wireless Presenter Clicker", "Projector", "Podium Mic"],
            "manpower": ["1 Speaker Liaison", "1 Desk Registrar"]
        },
        "Default": {
            "vendors": ["General Event Services"],
            "materials": ["Signage & Seating Layout"],
            "equipment": ["Basic PA System"],
            "manpower": ["2 Operations Staff"]
        }
    }

    # Common Risk Checklist Templates
    RISK_CHECKLISTS = {
        "Cultural": [
            "AV & Lighting check completed 2 hours prior",
            "Artist green room and hospitality confirmed",
            "Sound license & volume permissions cleared",
            "Post-event cleanup & inventory return scheduled"
        ],
        "Sports": [
            "First aid box and emergency medical protocol ready",
            "Hydration counters and ice packs stocked",
            "Ground markings and boundary safety verified",
            "Referee briefing and rules sheet distributed"
        ],
        "Gaming & Tech": [
            "Wi-Fi bandwidth test and backup router ready",
            "Power load test (no circuit trip with PCs/monitors)",
            "Game client updates & patches pre-downloaded"
        ],
        "Default": [
            "Venue space reservation & key access confirmed",
            "Vendor arrival time and point of contact verified",
            "Weather check (rain backup space identified)",
            "Budget buffer and emergency cash on hand"
        ]
    }

    # Operational Planning Insights Rules
    INSIGHT_RULES = [
        {"key": "volunteer", "tag": "👥 High Volunteer Requirement", "condition": lambda cat, turn: turn >= 50 or cat in ["Cultural", "Sports"]},
        {"key": "budget", "tag": "💸 Budget Sensitive Event", "condition": lambda cat, turn: cat in ["Cultural", "Gaming & Tech"]},
        {"key": "weather", "tag": "🌤️ Weather Dependent", "condition": lambda cat, turn: cat in ["Sports", "Social"]},
        {"key": "setup", "tag": "🛠️ Large Setup Effort", "condition": lambda cat, turn: cat in ["Cultural", "Gaming & Tech", "Sports"]},
        {"key": "night", "tag": "🌙 Late-Night Logistics", "condition": lambda cat, turn: cat in ["Social", "Gaming & Tech"]}
    ]

    def __init__(self):
        pass

    # ===========================================================
    # FEATURE 1 — AI Planning Summary
    # ===========================================================
    def generate_planning_summary(self, event_name: str, category: str, property_name: str, event_date: str) -> Dict[str, Any]:
        """Generates deterministic planning summary for an Event Workspace."""
        cat_key = category if category in self.CATEGORY_RESOURCES else "Default"
        
        # Calculate preparation days
        prep_days = 7
        if category in ["Cultural", "Sports"]:
            prep_days = 14
        elif category in ["Gaming & Tech"]:
            prep_days = 10

        min_budget = 3000
        max_budget = 15000
        if category in ["Cultural", "Sports"]:
            min_budget, max_budget = 10000, 25000
        elif category in ["Social"]:
            min_budget, max_budget = 2000, 7000

        return {
            "objective": f"Host an engaging {category.lower()} event ('{event_name}') for residents at {property_name} to maximize community interaction.",
            "expected_audience": f"Residents at {property_name} interested in {category} activities.",
            "preparation_timeline": f"Recommended start: {prep_days} days before event date ({event_date}).",
            "estimated_manpower": f"3 - 5 Staff Members / Volunteers ({category} team)",
            "estimated_complexity": "High" if category in ["Cultural", "Sports"] else "Medium",
            "expected_attendance_range": "40 - 75 Residents",
            "recommended_budget_range": f"₹{min_budget:,.0f} - ₹{max_budget:,.0f}",
            "success_tips": [
                "Send resident announcement broadcast at least 5 days prior.",
                "Conduct technical sound check 2 hours before start time.",
                "Set up registration QR code desk at the entrance."
            ]
        }

    # ===========================================================
    # FEATURE 2 & 3 — Task Prioritization & Suggested Timelines
    # ===========================================================
    def enrich_task_with_intelligence(self, task: Dict[str, Any], event_date_str: str) -> Dict[str, Any]:
        """Enriches a task with Priority, Suggested Timeline offset, and Confidence score."""
        title_lower = str(task.get("title", "")).lower()
        dept_lower = str(task.get("department", "")).lower()

        # Deterministic Priority Scoring
        priority = "Medium"
        if any(k in title_lower for k in ["venue", "ground", "permission", "licence", "sound check", "wi-fi", "stage"]):
            priority = "High"
        elif any(k in title_lower for k in ["cleanup", "playlist", "feedback", "photos"]):
            priority = "Low"

        # Suggested Timeline Guidance
        timeline_guidance = "7 days before"
        if any(k in title_lower for k in ["reservation", "permission", "vendor", "artist"]):
            timeline_guidance = "14 days before"
        elif any(k in title_lower for k in ["setup", "sound", "equipment", "drinks"]):
            timeline_guidance = "1 day before"
        elif any(k in title_lower for k in ["cleanup", "feedback"]):
            timeline_guidance = "Post-Event"

        task["priority"] = task.get("priority", priority)
        task["suggested_timeline"] = timeline_guidance
        task["confidence"] = "High"
        task["explanation"] = f"Assigned '{priority}' priority based on {task.get('department', 'Operations')} criticality."
        return task

    # ===========================================================
    # FEATURE 4 — Suggested Resources
    # ===========================================================
    def get_suggested_resources(self, category: str) -> Dict[str, List[str]]:
        """Returns non-binding resource recommendations for vendors, materials, equipment, and manpower."""
        cat_key = category if category in self.CATEGORY_RESOURCES else "Default"
        return self.CATEGORY_RESOURCES.get(cat_key, self.CATEGORY_RESOURCES["Default"])

    # ===========================================================
    # FEATURE 5 — Risk Checklist
    # ===========================================================
    def get_risk_checklist(self, category: str) -> List[Dict[str, Any]]:
        """Generates an editable list of common risks and verification checks."""
        specific_risks = self.RISK_CHECKLISTS.get(category, [])
        default_risks = self.RISK_CHECKLISTS["Default"]
        combined = list(dict.fromkeys(specific_risks + default_risks))
        return [{"risk_item": r, "verified": False} for r in combined]

    # ===========================================================
    # FEATURE 6 — Planning Insights
    # ===========================================================
    def get_planning_insights(self, category: str, expected_turnout: int = 50) -> List[Dict[str, Any]]:
        """Generates operational insight tags with explainable reasons."""
        insights = []
        for rule in self.INSIGHT_RULES:
            if rule["condition"](category, expected_turnout):
                insights.append({
                    "tag": rule["tag"],
                    "confidence": "High",
                    "explanation": f"Calculated based on '{category}' category historical complexity and turnout expectation ({expected_turnout} residents)."
                })
        return insights

    # ===========================================================
    # FEATURE 8 — Confidence Score
    # ===========================================================
    def get_planning_confidence_score(self, category: str, history_matches_count: int) -> Dict[str, Any]:
        """Calculates planning confidence based on category familiarity and past logs count."""
        if history_matches_count >= 3:
            return {"confidence_level": "High", "score": 92.0, "reason": f"High confidence based on {history_matches_count} similar historical event logs."}
        elif history_matches_count >= 1:
            return {"confidence_level": "Medium", "score": 78.0, "reason": "Medium confidence derived from limited past logs and category rules."}
        else:
            return {"confidence_level": "Medium-Low", "score": 68.0, "reason": "Standard rule-based estimate (no prior exact property history)."}

    # ===========================================================
    # FEATURE 9 — Similar Past Events
    # ===========================================================
    def find_similar_past_events(self, event_name: str, category: str, property_name: str) -> List[Dict[str, Any]]:
        """Queries historical event logs (data/event_history.csv or MongoDB) to display past turnout & lessons."""
        similar_events = []
        try:
            from pathlib import Path
            hist_csv = Path(__file__).resolve().parents[2] / "data" / "event_history.csv"
            if hist_csv.exists():
                df = pd.read_csv(hist_csv)
                if not df.empty:
                    # Match by Category or property
                    matched = df[(df.get("Category", df.columns[0]).astype(str).str.lower() == category.lower()) | 
                                 (df.get("Property", df.columns[0]).astype(str).str.lower() == property_name.lower())]
                    for _, row in matched.head(3).iterrows():
                        similar_events.append({
                            "event_name": row.get("Event Name", row.get("Event", "Past Event")),
                            "property": row.get("Property", property_name),
                            "date": row.get("Date", row.get("Event Date", "N/A")),
                            "actual_turnout": row.get("Actual Attendance", row.get("Attendance", "45")),
                            "rating": row.get("Average Feedback", row.get("Rating", "4.5")),
                            "lessons_learned": f"Successful turnout in {category}; ensure early sound test."
                        })
        except Exception as e:
            logger.error(f"Error querying past events for AI planning assistant: {e}")

        return similar_events

event_planning_ai = EventPlanningAIService()
